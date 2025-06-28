"""
Поддержка различных языков программирования для анализа кода.
Определяет маппинг расширений файлов на языки и их парсеры.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pathlib import Path


class LanguageSupport:
    """Управляет поддержкой различных языков программирования."""
    
    # Маппинг расширений файлов на языки
    EXTENSION_MAPPING = {
        '.py': 'python',
        '.pyw': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.mjs': 'javascript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.cxx': 'cpp',
        '.cc': 'cpp',
        '.c': 'c',
        '.hpp': 'cpp',
        '.h': 'c',
        '.go': 'go',
        '.rs': 'rust',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.kt': 'kotlin',
        '.swift': 'swift',
        '.scala': 'scala',
        '.clj': 'clojure',
        '.hs': 'haskell',
        '.ml': 'ocaml',
        '.elm': 'elm',
        '.lua': 'lua',
        '.dart': 'dart',
        '.r': 'r',
        '.jl': 'julia',
        '.nim': 'nim',
        '.zig': 'zig',
        '.v': 'vlang',
    }
    
    # Информация о языках
    LANGUAGE_INFO = {
        'python': {
            'name': 'Python',
            'tree_sitter_name': 'python',
            'comment_style': '#',
            'supports_classes': True,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['main()', 'if __name__ == "__main__"']
        },
        'javascript': {
            'name': 'JavaScript',
            'tree_sitter_name': 'javascript', 
            'comment_style': '//',
            'supports_classes': True,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['main()', 'function main']
        },
        'typescript': {
            'name': 'TypeScript',
            'tree_sitter_name': 'typescript',
            'comment_style': '//',
            'supports_classes': True,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['main()', 'function main']
        },
        'java': {
            'name': 'Java',
            'tree_sitter_name': 'java',
            'comment_style': '//',
            'supports_classes': True,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['public static void main']
        },
        'cpp': {
            'name': 'C++',
            'tree_sitter_name': 'cpp',
            'comment_style': '//',
            'supports_classes': True,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['int main(', 'void main(']
        },
        'c': {
            'name': 'C',
            'tree_sitter_name': 'c',
            'comment_style': '//',
            'supports_classes': False,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['int main(', 'void main(']
        },
        'go': {
            'name': 'Go',
            'tree_sitter_name': 'go',
            'comment_style': '//',
            'supports_classes': False,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['func main()']
        },
        'rust': {
            'name': 'Rust',
            'tree_sitter_name': 'rust',
            'comment_style': '//',
            'supports_classes': False,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['fn main()']
        },
        'csharp': {
            'name': 'C#',
            'tree_sitter_name': 'c_sharp',
            'comment_style': '//',
            'supports_classes': True,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['static void Main']
        },
        'php': {
            'name': 'PHP',
            'tree_sitter_name': 'php',
            'comment_style': '//',
            'supports_classes': True,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['<?php']
        },
        'ruby': {
            'name': 'Ruby',
            'tree_sitter_name': 'ruby',
            'comment_style': '#',
            'supports_classes': True,
            'supports_functions': True,
            'supports_imports': True,
            'entry_point_patterns': ['def main', 'if __FILE__ == $0']
        }
    }
    
    @classmethod
    def detect_language(cls, file_path: str) -> Optional[str]:
        """Определить язык программирования по расширению файла."""
        path = Path(file_path)
        extension = path.suffix.lower()
        return cls.EXTENSION_MAPPING.get(extension)
    
    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Получить список поддерживаемых языков."""
        return list(cls.LANGUAGE_INFO.keys())
    
    @classmethod
    def get_language_info(cls, language: str) -> Optional[Dict]:
        """Получить информацию о языке."""
        return cls.LANGUAGE_INFO.get(language)
    
    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """Проверить, поддерживается ли файл."""
        return cls.detect_language(file_path) is not None
    
    @classmethod
    def get_tree_sitter_name(cls, language: str) -> Optional[str]:
        """Получить имя языка для tree-sitter."""
        info = cls.get_language_info(language)
        return info.get('tree_sitter_name') if info else None
    
    @classmethod
    def supports_feature(cls, language: str, feature: str) -> bool:
        """Проверить, поддерживает ли язык определенную функцию."""
        info = cls.get_language_info(language)
        if not info:
            return False
        return info.get(f'supports_{feature}', False)
    
    @classmethod
    def get_files_by_language(cls, file_paths: List[str]) -> Dict[str, List[str]]:
        """Сгруппировать файлы по языкам."""
        language_files = {}
        
        for file_path in file_paths:
            language = cls.detect_language(file_path)
            if language:
                if language not in language_files:
                    language_files[language] = []
                language_files[language].append(file_path)
        
        return language_files
    
    @classmethod
    def is_entry_point_file(cls, file_path: str, content: str = None) -> bool:
        """Определить, является ли файл точкой входа в программу."""
        language = cls.detect_language(file_path)
        if not language:
            return False
        
        info = cls.get_language_info(language)
        if not info or not content:
            # Эвристика по имени файла
            file_name = Path(file_path).stem.lower()
            return file_name in ['main', 'index', 'app', 'server', 'cli']
        
        # Проверка по паттернам в содержимом
        entry_patterns = info.get('entry_point_patterns', [])
        content_lower = content.lower()
        
        for pattern in entry_patterns:
            if pattern.lower() in content_lower:
                return True
        
        return False
    
    @classmethod
    def get_comment_prefix(cls, language: str) -> str:
        """Получить префикс комментария для языка."""
        info = cls.get_language_info(language)
        return info.get('comment_style', '//') if info else '//'


# Утилиты для работы с файлами

def filter_code_files(file_paths: List[str], 
                     ignore_patterns: List[str] = None) -> List[str]:
    """Отфильтровать только файлы исходного кода."""
    if ignore_patterns is None:
        ignore_patterns = [
            '*.pyc', '*.pyo', '*.pyd', '*.so', '*.dll', '*.exe',
            '*.class', '*.jar', '*.war', '*.min.js', '*.min.css'
        ]
    
    code_files = []
    
    for file_path in file_paths:
        # Проверяем, что файл поддерживается
        if not LanguageSupport.is_supported(file_path):
            continue
        
        # Проверяем игнорируемые паттерны
        file_name = Path(file_path).name
        should_ignore = False
        
        for pattern in ignore_patterns:
            if pattern.startswith('*') and file_name.endswith(pattern[1:]):
                should_ignore = True
                break
            elif pattern in file_name:
                should_ignore = True
                break
        
        if not should_ignore:
            code_files.append(file_path)
    
    return code_files


def scan_directory(directory: str,
                  max_depth: int = 10,
                  ignore_dirs: List[str] = None) -> List[str]:
    """Сканировать директорию на предмет файлов исходного кода."""
    if ignore_dirs is None:
        ignore_dirs = [
            '__pycache__', 'node_modules', '.git', '.svn',
            'dist', 'build', 'target', '.pytest_cache', 
            '.coverage', 'venv', 'env', '.env'
        ]
    
    found_files = []
    directory_path = Path(directory)
    
    def _scan_recursive(current_path: Path, current_depth: int):
        if current_depth > max_depth:
            return
        
        try:
            for item in current_path.iterdir():
                if item.is_file():
                    if LanguageSupport.is_supported(str(item)):
                        found_files.append(str(item))
                elif item.is_dir():
                    dir_name = item.name
                    if dir_name not in ignore_dirs and not dir_name.startswith('.'):
                        _scan_recursive(item, current_depth + 1)
        except PermissionError:
            # Игнорируем файлы/папки без прав доступа
            pass
    
    _scan_recursive(directory_path, 0)
    return found_files
