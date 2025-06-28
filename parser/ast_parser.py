"""
AST-парсер для анализа структуры исходного кода.
Поддерживает извлечение классов, функций, импортов и зависимостей.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .language_support import LanguageSupport


@dataclass
class CodeFunction:
    """Представление функции в коде."""
    name: str
    line_start: int
    line_end: int
    parameters: List[str]
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    complexity: int = 1
    is_method: bool = False
    visibility: str = "public"  # public, private, protected


@dataclass
class CodeClass:
    """Представление класса в коде."""
    name: str
    line_start: int
    line_end: int
    methods: List[CodeFunction]
    properties: List[str]
    inheritance: List[str]
    docstring: Optional[str] = None
    visibility: str = "public"


@dataclass
class CodeStructure:
    """Структура кода файла."""
    file_path: str
    language: str
    imports: List[str]
    classes: List[CodeClass]
    functions: List[CodeFunction]
    global_variables: List[str]
    dependencies: List[str]
    total_lines: int
    complexity_score: int


class ASTParser:
    """Парсер исходного кода для извлечения структурной информации."""
    
    def __init__(self):
        self.language_support = LanguageSupport()
    
    def parse_file(self, file_path: str) -> Optional[CodeStructure]:
        """Парсинг файла и извлечение структуры."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            language = self.language_support.detect_language(file_path)
            if not language:
                return None
            
            # Пытаемся использовать специализированный парсер для языка
            if language == 'python':
                return self._parse_python(file_path, content)
            elif language in ['javascript', 'typescript']:
                return self._parse_javascript(file_path, content, language)
            elif language == 'java':
                return self._parse_java(file_path, content)
            elif language in ['cpp', 'c']:
                return self._parse_cpp(file_path, content, language)
            else:
                # Для остальных языков используем общий подход
                return self._parse_generic(file_path, content, language)
                
        except Exception as e:
            print(f"Ошибка при парсинге файла {file_path}: {e}")
            return None
    
    def _parse_python(self, file_path: str, content: str) -> CodeStructure:
        """Парсинг Python файла с использованием AST."""
        try:
            tree = ast.parse(content)
            
            imports = self._extract_python_imports(tree)
            classes = self._extract_python_classes(tree, content.split('\n'))
            functions = self._extract_python_functions(tree, content.split('\n'))
            global_vars = self._extract_python_globals(tree)
            
            # Вычисляем зависимости на основе импортов
            dependencies = self._extract_dependencies_from_imports(imports)
            
            return CodeStructure(
                file_path=file_path,
                language='python',
                imports=imports,
                classes=classes,
                functions=functions,
                global_variables=global_vars,
                dependencies=dependencies,
                total_lines=len(content.split('\n')),
                complexity_score=self._calculate_complexity(classes, functions)
            )
            
        except SyntaxError:
            # Если не удается парсить, используем регулярные выражения
            return self._parse_generic(file_path, content, 'python')
    
    def _extract_python_imports(self, tree: ast.AST) -> List[str]:
        """Извлечение импортов из Python AST."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    if alias.name == '*':
                        imports.append(f"from {module} import *")
                    else:
                        imports.append(f"from {module} import {alias.name}")
        
        return imports
    
    def _extract_python_classes(self, tree: ast.AST, lines: List[str]) -> List[CodeClass]:
        """Извлечение классов из Python AST."""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                properties = []
                
                # Извлекаем методы класса
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method = self._ast_function_to_code_function(item, lines, is_method=True)
                        methods.append(method)
                    elif isinstance(item, ast.Assign):
                        # Пытаемся найти свойства класса
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                properties.append(target.id)
                
                # Извлекаем наследование
                inheritance = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        inheritance.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        inheritance.append(ast.unparse(base) if hasattr(ast, 'unparse') else str(base))
                
                # Извлекаем docstring
                docstring = ast.get_docstring(node)
                
                classes.append(CodeClass(
                    name=node.name,
                    line_start=node.lineno,
                    line_end=getattr(node, 'end_lineno', node.lineno),
                    methods=methods,
                    properties=properties,
                    inheritance=inheritance,
                    docstring=docstring
                ))
        
        return classes
    
    def _extract_python_functions(self, tree: ast.AST, lines: List[str]) -> List[CodeFunction]:
        """Извлечение функций из Python AST."""
        functions = []
        
        # Извлекаем только функции верхнего уровня (не методы)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                function = self._ast_function_to_code_function(node, lines)
                functions.append(function)
        
        return functions
    
    def _ast_function_to_code_function(self, node: ast.FunctionDef, lines: List[str], is_method: bool = False) -> CodeFunction:
        """Преобразование AST узла функции в CodeFunction."""
        # Извлекаем параметры
        parameters = []
        for arg in node.args.args:
            param_name = arg.arg
            if arg.annotation:
                # Пытаемся получить аннотацию типа
                try:
                    type_hint = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                    param_name += f": {type_hint}"
                except:
                    pass
            parameters.append(param_name)
        
        # Извлекаем тип возвращаемого значения
        return_type = None
        if node.returns:
            try:
                return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
            except:
                pass
        
        # Извлекаем docstring
        docstring = ast.get_docstring(node)
        
        # Вычисляем сложность (упрощенная метрика)
        complexity = self._calculate_function_complexity(node)
        
        return CodeFunction(
            name=node.name,
            line_start=node.lineno,
            line_end=getattr(node, 'end_lineno', node.lineno),
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            complexity=complexity,
            is_method=is_method,
            visibility="private" if node.name.startswith('_') else "public"
        )
    
    def _extract_python_globals(self, tree: ast.AST) -> List[str]:
        """Извлечение глобальных переменных из Python AST."""
        globals_vars = []
        
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        globals_vars.append(target.id)
        
        return globals_vars
    
    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Упрощенное вычисление цикломатической сложности."""
        complexity = 1  # Базовая сложность
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _parse_javascript(self, file_path: str, content: str, language: str) -> CodeStructure:
        """Парсинг JavaScript/TypeScript файла с использованием регулярных выражений."""
        lines = content.split('\n')
        
        # Извлекаем импорты/require
        imports = self._extract_js_imports(content)
        
        # Извлекаем функции
        functions = self._extract_js_functions(content, lines)
        
        # Извлекаем классы
        classes = self._extract_js_classes(content, lines)
        
        # Глобальные переменные
        global_vars = self._extract_js_globals(content)
        
        dependencies = self._extract_dependencies_from_imports(imports)
        
        return CodeStructure(
            file_path=file_path,
            language=language,
            imports=imports,
            classes=classes,
            functions=functions,
            global_variables=global_vars,
            dependencies=dependencies,
            total_lines=len(lines),
            complexity_score=self._calculate_complexity(classes, functions)
        )
    
    def _extract_js_imports(self, content: str) -> List[str]:
        """Извлечение импортов из JavaScript/TypeScript."""
        imports = []
        
        # import statements
        import_pattern = r"import\s+.*?from\s+['\"]([^'\"]+)['\"]"
        imports.extend(re.findall(import_pattern, content))
        
        # require statements
        require_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
        imports.extend(re.findall(require_pattern, content))
        
        return imports
    
    def _extract_js_functions(self, content: str, lines: List[str]) -> List[CodeFunction]:
        """Извлечение функций из JavaScript/TypeScript."""
        functions = []
        
        # Регулярные выражения для разных типов функций
        patterns = [
            r"function\s+(\w+)\s*\(([^)]*)\)",  # function declaration
            r"const\s+(\w+)\s*=\s*\([^)]*\)\s*=>",  # arrow function
            r"(\w+)\s*:\s*function\s*\([^)]*\)",  # object method
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                function_name = match.group(1)
                start_line = content[:match.start()].count('\n') + 1
                
                # Простое определение конца функции (может быть неточным)
                end_line = start_line + 10  # Приблизительная оценка
                
                functions.append(CodeFunction(
                    name=function_name,
                    line_start=start_line,
                    line_end=end_line,
                    parameters=[],  # Упрощено
                    complexity=1
                ))
        
        return functions
    
    def _extract_js_classes(self, content: str, lines: List[str]) -> List[CodeClass]:
        """Извлечение классов из JavaScript/TypeScript."""
        classes = []
        
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{"
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(1)
            inheritance = [match.group(2)] if match.group(2) else []
            start_line = content[:match.start()].count('\n') + 1
            
            classes.append(CodeClass(
                name=class_name,
                line_start=start_line,
                line_end=start_line + 10,  # Приблизительная оценка
                methods=[],
                properties=[],
                inheritance=inheritance
            ))
        
        return classes
    
    def _extract_js_globals(self, content: str) -> List[str]:
        """Извлечение глобальных переменных из JavaScript/TypeScript."""
        globals_vars = []
        
        # var, let, const declarations
        patterns = [
            r"(?:var|let|const)\s+(\w+)",
        ]
        
        for pattern in patterns:
            globals_vars.extend(re.findall(pattern, content))
        
        return globals_vars
    
    def _parse_java(self, file_path: str, content: str) -> CodeStructure:
        """Парсинг Java файла."""
        return self._parse_generic(file_path, content, 'java')
    
    def _parse_cpp(self, file_path: str, content: str, language: str) -> CodeStructure:
        """Парсинг C/C++ файла."""
        return self._parse_generic(file_path, content, language)
    
    def _parse_generic(self, file_path: str, content: str, language: str) -> CodeStructure:
        """Общий парсер для языков без специализированной поддержки."""
        lines = content.split('\n')
        
        # Простое извлечение на основе регулярных выражений
        imports = self._extract_generic_imports(content, language)
        functions = self._extract_generic_functions(content, language)
        classes = self._extract_generic_classes(content, language)
        global_vars = []  # Сложно определить без специализированного парсера
        
        dependencies = self._extract_dependencies_from_imports(imports)
        
        return CodeStructure(
            file_path=file_path,
            language=language,
            imports=imports,
            classes=classes,
            functions=functions,
            global_variables=global_vars,
            dependencies=dependencies,
            total_lines=len(lines),
            complexity_score=len(functions) + len(classes)
        )
    
    def _extract_generic_imports(self, content: str, language: str) -> List[str]:
        """Общее извлечение импортов."""
        imports = []
        
        patterns = {
            'java': [r"import\s+([^;]+);"],
            'cpp': [r"#include\s+[<\"]([^>\"]+)[>\"]"],
            'c': [r"#include\s+[<\"]([^>\"]+)[>\"]"],
            'go': [r"import\s+\"([^\"]+)\""],
            'rust': [r"use\s+([^;]+);"],
            'csharp': [r"using\s+([^;]+);"]
        }
        
        for pattern in patterns.get(language, []):
            imports.extend(re.findall(pattern, content))
        
        return imports
    
    def _extract_generic_functions(self, content: str, language: str) -> List[CodeFunction]:
        """Общее извлечение функций."""
        functions = []
        
        # Упрощенные паттерны для функций
        patterns = {
            'java': r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(",
            'cpp': r"(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{",
            'c': r"(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{",
            'go': r"func\s+(\w+)\s*\(",
            'rust': r"fn\s+(\w+)\s*\(",
            'csharp': r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\("
        }
        
        pattern = patterns.get(language, r"(\w+)\s*\([^)]*\)\s*\{")
        
        for match in re.finditer(pattern, content, re.MULTILINE):
            function_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            functions.append(CodeFunction(
                name=function_name,
                line_start=start_line,
                line_end=start_line + 5,  # Приблизительная оценка
                parameters=[],
                complexity=1
            ))
        
        return functions
    
    def _extract_generic_classes(self, content: str, language: str) -> List[CodeClass]:
        """Общее извлечение классов."""
        classes = []
        
        patterns = {
            'java': r"(?:public|private)?\s*class\s+(\w+)",
            'cpp': r"class\s+(\w+)",
            'csharp': r"(?:public|private|internal)?\s*class\s+(\w+)"
        }
        
        pattern = patterns.get(language)
        if not pattern:
            return classes
        
        for match in re.finditer(pattern, content, re.MULTILINE):
            class_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            classes.append(CodeClass(
                name=class_name,
                line_start=start_line,
                line_end=start_line + 10,  # Приблизительная оценка
                methods=[],
                properties=[],
                inheritance=[]
            ))
        
        return classes
    
    def _extract_dependencies_from_imports(self, imports: List[str]) -> List[str]:
        """Извлечение зависимостей из импортов."""
        dependencies = []
        
        for imp in imports:
            # Извлекаем только имя модуля/пакета
            if 'from' in imp and 'import' in imp:
                # from module import something
                module = imp.split('from')[1].split('import')[0].strip()
                dependencies.append(module)
            elif imp.startswith('/') or imp.startswith('./') or imp.startswith('../'):
                # Локальные файлы
                dependencies.append(imp)
            else:
                # Прямые импорты
                dependencies.append(imp.split('.')[0])  # Берем корневой модуль
        
        return list(set(dependencies))  # Убираем дубликаты
    
    def _calculate_complexity(self, classes: List[CodeClass], functions: List[CodeFunction]) -> int:
        """Вычисление общей сложности файла."""
        total_complexity = 0
        
        for cls in classes:
            total_complexity += len(cls.methods) + 1
        
        for func in functions:
            total_complexity += func.complexity
        
        return total_complexity
    
    def extract_code_fragments(self, file_path: str, max_lines: int = 50) -> List[Tuple[str, int, int]]:
        """Извлечение фрагментов кода для анализа LLM."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            structure = self.parse_file(file_path)
            if not structure:
                return []
            
            fragments = []
            
            # Добавляем функции как фрагменты
            for func in structure.functions:
                start = max(0, func.line_start - 1)
                end = min(len(lines), func.line_end)
                
                if end - start <= max_lines:
                    fragment = ''.join(lines[start:end])
                    fragments.append((fragment, start + 1, end))
            
            # Добавляем классы как фрагменты
            for cls in structure.classes:
                start = max(0, cls.line_start - 1)
                end = min(len(lines), cls.line_end)
                
                if end - start <= max_lines:
                    fragment = ''.join(lines[start:end])
                    fragments.append((fragment, start + 1, end))
            
            return fragments
            
        except Exception as e:
            print(f"Ошибка при извлечении фрагментов из {file_path}: {e}")
            return []
