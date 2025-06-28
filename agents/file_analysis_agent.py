"""
Агент для анализа отдельных файлов исходного кода.
Выполняет структурный анализ с помощью AST и семантический анализ с помощью LLM.
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Dict, List, Optional

from src.agents import Agent, Runner, RunConfig, function_tool
from src.agents.models.openrouter_provider import OpenRouterProvider
from src.agents.models.lmstudio_provider import LMStudioProvider
from src.agents.models.multi_provider import MultiProvider
from src.agents.model_settings import ModelSettings

from core.knowledge_base import FileAnalysisReport
from parser.ast_parser import ASTParser, CodeStructure
from parser.language_support import LanguageSupport


class FileAnalysisAgent:
    """Агент для анализа отдельного файла исходного кода."""
    
    def __init__(self, model_config: Dict):
        self.model_config = model_config
        self.ast_parser = ASTParser()
        self.language_support = LanguageSupport()
        
        # Создаем агента для семантического анализа
        self.semantic_agent = Agent(
            name="FileSemanticAnalyzer",
            instructions="""
            Ты - эксперт по анализу исходного кода. Твоя задача - понять и объяснить назначение и логику кода.

            ВАЖНЫЕ ПРАВИЛА:
            1. Отвечай ТОЛЬКО на русском языке
            2. Будь точным и исчерпывающим
            3. Фокусируйся на НАЗНАЧЕНИИ и ЛОГИКЕ, а не на синтаксисе
            4. Используй технические термины, но объясняй просто
            5. Если код сложный, выдели ключевые моменты

            ФОРМАТ ОТВЕТА:
            - Для функций: объясни что делает, основной алгоритм, особенности
            - Для классов: назначение класса, основные методы, паттерны
            - Для модулей: общая цель, архитектурная роль
            """,
            tools=[]
        )
    
    async def analyze_file(self, file_path: str) -> Optional[FileAnalysisReport]:
        """Полный анализ файла: структурный + семантический."""
        try:
            print(f"[FileAnalysisAgent] Анализирую файл: {file_path}")
            
            # 1. Проверяем, что файл поддерживается
            if not self.language_support.is_supported(file_path):
                print(f"[FileAnalysisAgent] Файл {file_path} не поддерживается")
                return None
            
            # 2. Структурный анализ с помощью AST
            structure = self.ast_parser.parse_file(file_path)
            if not structure:
                print(f"[FileAnalysisAgent] Не удалось разобрать структуру файла {file_path}")
                return None
            
            print(f"[FileAnalysisAgent] Структурный анализ завершен. Найдено: {len(structure.classes)} классов, {len(structure.functions)} функций")
            
            # 3. Семантический анализ с помощью LLM
            file_summary = await self._analyze_file_purpose(file_path, structure)
            enriched_classes = await self._analyze_classes(structure.classes, file_path)
            enriched_functions = await self._analyze_functions(structure.functions, file_path)
            
            # 4. Анализ качества кода и выявление проблем
            issues = self._analyze_code_quality(file_path, structure, enriched_classes, enriched_functions)
            
            # 5. Формируем отчет
            report = FileAnalysisReport(
                file_path=file_path,
                language=structure.language,
                size_lines=structure.total_lines,
                classes=enriched_classes,
                functions=enriched_functions,
                imports=structure.imports,
                dependencies=structure.dependencies,
                summary=file_summary,
                complexity_notes=self._generate_complexity_notes(structure),
                issues=issues
            )
            
            print(f"[FileAnalysisAgent] Анализ файла {file_path} завершен")
            return report
            
        except Exception as e:
            print(f"[FileAnalysisAgent] Ошибка при анализе файла {file_path}: {e}")
            return None
    
    async def _analyze_file_purpose(self, file_path: str, structure: CodeStructure) -> str:
        """Определение общего назначения файла."""
        try:
            # Формируем контекст для анализа
            context = []
            context.append(f"Файл: {os.path.basename(file_path)}")
            context.append(f"Язык: {structure.language}")
            context.append(f"Строк кода: {structure.total_lines}")
            
            # Проверяем, является ли файл тестовым
            is_test_file = self._is_test_file(file_path)
            if is_test_file:
                context.append("Тип: Тестовый файл")
            
            if structure.imports:
                context.append(f"Основные импорты: {', '.join(structure.imports[:5])}")
            
            if structure.classes:
                class_names = [cls.name for cls in structure.classes[:3]]
                context.append(f"Классы: {', '.join(class_names)}")
            
            if structure.functions:
                func_names = [func.name for func in structure.functions[:5]]
                context.append(f"Функции: {', '.join(func_names)}")
            
            prompt = f"""
            Проанализируй следующую информацию о файле исходного кода и определи его назначение:

            {chr(10).join(context)}

            Опиши кратко (1-2 предложения), что делает этот файл и какую роль играет в проекте.
            """
            
            result = await self._run_semantic_analysis(prompt)
            return result or "Файл содержит программный код"
            
        except Exception as e:
            print(f"[FileAnalysisAgent] Ошибка при анализе назначения файла: {e}")
            return "Не удалось определить назначение файла"
    
    async def _analyze_classes(self, classes: List, file_path: str) -> List[Dict]:
        """Семантический анализ классов."""
        enriched_classes = []
        
        for cls in classes:
            try:
                # Получаем код класса из файла
                class_code = self._extract_class_code(file_path, cls)
                docstring = cls.docstring if hasattr(cls, 'docstring') else ''
                
                if class_code and len(class_code) < 2000:  # Ограничиваем размер
                    description = await self._analyze_code_fragment(
                        class_code, 
                        f"класс {cls.name}"
                    )
                else:
                    # Анализируем по метаданным
                    description = await self._analyze_class_metadata(cls)
                
                # Новый этап: анализ паттерна
                pattern = await self._analyze_design_patterns(class_code or '', docstring, 'класс', cls.name)
                
                enriched_classes.append({
                    "name": cls.name,
                    "line_start": cls.line_start,
                    "line_end": cls.line_end,
                    "description": description,
                    "methods_count": len(cls.methods),
                    "inheritance": cls.inheritance,
                    "visibility": cls.visibility,
                    "pattern": pattern
                })
                
            except Exception as e:
                print(f"[FileAnalysisAgent] Ошибка при анализе класса {cls.name}: {e}")
                enriched_classes.append({
                    "name": cls.name,
                    "description": "Ошибка анализа",
                    "methods_count": len(cls.methods),
                    "inheritance": cls.inheritance,
                    "pattern": "Паттерн не обнаружен"
                })
        
        return enriched_classes
    
    async def _analyze_functions(self, functions: List, file_path: str) -> List[Dict]:
        """Семантический анализ функций."""
        enriched_functions = []
        
        for func in functions:
            try:
                # Получаем код функции из файла
                func_code = self._extract_function_code(file_path, func)
                docstring = func.docstring if hasattr(func, 'docstring') else ''
                
                if func_code and len(func_code) < 1500:  # Ограничиваем размер
                    description = await self._analyze_code_fragment(
                        func_code, 
                        f"функцию {func.name}"
                    )
                else:
                    # Анализируем по метаданным
                    description = await self._analyze_function_metadata(func)
                
                # Новый этап: анализ паттерна
                pattern = await self._analyze_design_patterns(func_code or '', docstring, 'функция', func.name)
                
                enriched_functions.append({
                    "name": func.name,
                    "line_start": func.line_start,
                    "line_end": func.line_end,
                    "description": description,
                    "parameters": func.parameters,
                    "return_type": func.return_type,
                    "complexity": func.complexity,
                    "is_method": func.is_method,
                    "visibility": func.visibility,
                    "pattern": pattern
                })
                
            except Exception as e:
                print(f"[FileAnalysisAgent] Ошибка при анализе функции {func.name}: {e}")
                enriched_functions.append({
                    "name": func.name,
                    "description": "Ошибка анализа",
                    "parameters": func.parameters,
                    "complexity": func.complexity,
                    "pattern": "Паттерн не обнаружен"
                })
        
        return enriched_functions
    
    def _analyze_code_quality(self, file_path: str, structure: CodeStructure, 
                            classes: List[Dict], functions: List[Dict]) -> List[str]:
        """Анализ качества кода и выявление проблем."""
        issues = []
        
        # Анализ размера файла
        if structure.total_lines > 500:
            issues.append("Файл слишком большой - рекомендуется разбить на модули")
        
        # Анализ классов
        for cls in classes:
            if cls.get('methods_count', 0) > 20:
                issues.append(f"Класс '{cls['name']}' содержит слишком много методов ({cls['methods_count']})")
            
            class_size = cls.get('line_end', 0) - cls.get('line_start', 0)
            if class_size > 200:
                issues.append(f"Класс '{cls['name']}' слишком большой ({class_size} строк)")
        
        # Анализ функций
        for func in functions:
            func_size = func.get('line_end', 0) - func.get('line_start', 0)
            if func_size > 50:
                issues.append(f"Функция '{func['name']}' слишком длинная ({func_size} строк)")
            
            if func.get('complexity', 0) > 10:
                issues.append(f"Функция '{func['name']}' слишком сложная (сложность: {func['complexity']})")
            
            # Анализ параметров
            params = func.get('parameters', [])
            if len(params) > 7:
                issues.append(f"Функция '{func['name']}' имеет слишком много параметров ({len(params)})")
        
        # Анализ импортов
        if len(structure.imports) > 20:
            issues.append("Слишком много импортов - возможно, файл делает слишком много")
        
        # Анализ дублирования (базовый)
        function_names = [f['name'] for f in functions]
        if len(function_names) != len(set(function_names)):
            issues.append("Обнаружены функции с одинаковыми именами")
        
        # Анализ тестовых файлов
        if self._is_test_file(file_path):
            if not functions and not classes:
                issues.append("Тестовый файл не содержит тестовых функций или классов")
        
        # Анализ документации
        if not structure.classes and not structure.functions:
            issues.append("Файл не содержит классов или функций")
        
        return issues
    
    def _is_test_file(self, file_path: str) -> bool:
        """Определение, является ли файл тестовым."""
        filename = os.path.basename(file_path).lower()
        return (filename.startswith('test_') or 
                filename.endswith('_test.py') or 
                'test' in filename or
                'spec' in filename)
    
    async def _analyze_code_fragment(self, code: str, element_type: str) -> str:
        """Анализ фрагмента кода с помощью LLM."""
        try:
            prompt = f"""
            Проанализируй следующий {element_type} и объясни его назначение и логику работы:

            ```
            {code}
            ```

            Опиши кратко (1-2 предложения): что делает, основной алгоритм, особенности.
            """
            
            result = await self._run_semantic_analysis(prompt)
            return result or f"Код {element_type}"
            
        except Exception as e:
            print(f"[FileAnalysisAgent] Ошибка при анализе фрагмента кода: {e}")
            return f"Не удалось проанализировать {element_type}"
    
    async def _analyze_class_metadata(self, cls) -> str:
        """Анализ класса по метаданным (без кода)."""
        try:
            prompt = f"""
            Проанализируй класс по его метаданным:
            
            Имя: {cls.name}
            Методы: {len(cls.methods)} ({', '.join([m.name for m in cls.methods[:5]])})
            Наследование: {', '.join(cls.inheritance) if cls.inheritance else 'Нет'}
            Docstring: {cls.docstring or 'Отсутствует'}
            
            Определи назначение этого класса в 1-2 предложениях.
            """
            
            result = await self._run_semantic_analysis(prompt)
            return result or f"Класс {cls.name}"
            
        except Exception as e:
            print(f"[FileAnalysisAgent] Ошибка при анализе метаданных класса: {e}")
            return f"Класс {cls.name}"
    
    async def _analyze_function_metadata(self, func) -> str:
        """Анализ функции по метаданным (без кода)."""
        try:
            prompt = f"""
            Проанализируй функцию по её метаданным:
            
            Имя: {func.name}
            Параметры: {', '.join(func.parameters) if func.parameters else 'Нет'}
            Возвращает: {func.return_type or 'Не указано'}
            Сложность: {func.complexity}
            Docstring: {func.docstring or 'Отсутствует'}
            
            Определи назначение этой функции в 1-2 предложениях.
            """
            
            result = await self._run_semantic_analysis(prompt)
            return result or f"Функция {func.name}"
            
        except Exception as e:
            print(f"[FileAnalysisAgent] Ошибка при анализе метаданных функции: {e}")
            return f"Функция {func.name}"
    
    def _extract_class_code(self, file_path: str, cls) -> Optional[str]:
        """Извлечение кода класса из файла."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            start = max(0, cls.line_start - 1)
            end = min(len(lines), cls.line_end)
            
            return ''.join(lines[start:end])
            
        except Exception:
            return None
    
    def _extract_function_code(self, file_path: str, func) -> Optional[str]:
        """Извлечение кода функции из файла."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            start = max(0, func.line_start - 1)
            end = min(len(lines), func.line_end)
            
            return ''.join(lines[start:end])
            
        except Exception:
            return None
    
    def _generate_complexity_notes(self, structure: CodeStructure) -> List[str]:
        """Генерация заметок о сложности кода."""
        notes = []
        
        if structure.complexity_score > 20:
            notes.append("Высокая сложность кода - рекомендуется рефакторинг")
        
        complex_functions = [f for f in structure.functions if f.complexity > 10]
        if complex_functions:
            func_names = [f.name for f in complex_functions[:3]]
            notes.append(f"Сложные функции: {', '.join(func_names)}")
        
        if len(structure.classes) > 10:
            notes.append("Много классов в одном файле - возможно стоит разделить")
        
        if structure.total_lines > 500:
            notes.append("Большой файл - рекомендуется разбить на модули")
        
        # Добавляем рекомендации по рефакторингу
        if structure.complexity_score > 15:
            notes.append("Рекомендуется упростить логику и разбить на более мелкие функции")
        
        if len(structure.imports) > 15:
            notes.append("Много импортов - рассмотрите возможность разделения ответственности")
        
        return notes
    
    async def _run_semantic_analysis(self, prompt: str) -> Optional[str]:
        """Выполнение семантического анализа с помощью LLM."""
        try:
            # Создаем провайдера модели на основе конфигурации
            provider = self._create_model_provider()
            model_settings = ModelSettings(
                temperature=self.model_config.get('settings', {}).get('temperature', 0.2),
                max_tokens=self.model_config.get('settings', {}).get('max_tokens', 1000)
            )
            
            # Выполняем запрос
            result = await Runner.run(
                self.semantic_agent,
                prompt,
                run_config=RunConfig(
                    model_provider=provider,
                    model=self.model_config.get('model', 'gpt-3.5-turbo'),
                    model_settings=model_settings
                )
            )
            
            return result.final_output.strip() if result.final_output else None
            
        except Exception as e:
            print(f"[FileAnalysisAgent] Ошибка при выполнении семантического анализа: {e}")
            return None
    
    def _create_model_provider(self):
        """Создание провайдера модели на основе конфигурации."""
        provider_type = self.model_config.get('provider', 'openrouter')
        
        if provider_type == 'openrouter':
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is required")
            return OpenRouterProvider(api_key=api_key)
        
        elif provider_type == 'lmstudio':
            base_url = os.getenv('LMSTUDIO_BASE_URL', 'http://localhost:1234/v1')
            return LMStudioProvider(base_url=base_url)
        
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider_type}")

    async def _analyze_design_patterns(self, code: str, docstring: str, element_type: str, name: str) -> str:
        """
        Анализирует docstring и код на предмет наличия паттернов проектирования.
        Возвращает строку с описанием найденного паттерна (или "Паттерн не обнаружен").
        """
        try:
            prompt = f"""
            Проанализируй следующий {element_type} с именем '{name}' и его docstring на предмет наличия паттернов проектирования (например, Singleton, Factory, Manager, Adapter, Facade, Observer и др.).

            Docstring:
            """
            {docstring or 'Отсутствует'}
            """

            Код:
            ```python
            {code[:1500]}
            ```

            Если реализован какой-либо паттерн проектирования, определи его и объясни почему. Если нет — напиши "Паттерн не обнаружен".
            Ответь кратко на русском языке.
            """
            result = await self._run_semantic_analysis(prompt)
            return result or "Паттерн не обнаружен"
        except Exception as e:
            print(f"[FileAnalysisAgent] Ошибка при анализе паттерна {element_type} {name}: {e}")
            return "Паттерн не обнаружен"
