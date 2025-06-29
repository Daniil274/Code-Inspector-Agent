"""
Центральная база знаний для хранения результатов анализа кода.
Управляет агрегацией данных от разных агентов и экспортом в Markdown.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class FileAnalysisReport:
    """Отчет об анализе одного файла."""
    file_path: str
    language: str
    size_lines: int
    classes: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    summary: str = ""
    complexity_notes: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


@dataclass
class ProjectAnalysis:
    """Общий анализ проекта."""
    project_path: str
    total_files: int
    total_lines: int
    languages: Dict[str, int] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    main_modules: List[str] = field(default_factory=list)
    architecture_summary: str = ""
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)


class KnowledgeBase:
    """Центральная база знаний системы CodeInspector."""
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Основные данные
        self.file_reports: Dict[str, FileAnalysisReport] = {}
        self.project_analysis: Optional[ProjectAnalysis] = None
        self.dependency_graph: Dict[str, List[str]] = {}
        
        # Метаданные
        self.analysis_metadata = {
            "timestamp": None,
            "agent_versions": {},
            "model_configs": {},
            "analysis_duration": None
        }
    
    def add_file_report(self, file_path: str, report: FileAnalysisReport) -> None:
        """Добавить отчет об анализе файла."""
        self.file_reports[file_path] = report
    
    def get_file_report(self, file_path: str) -> Optional[FileAnalysisReport]:
        """Получить отчет по файлу."""
        return self.file_reports.get(file_path)
    
    def set_project_analysis(self, analysis: ProjectAnalysis) -> None:
        """Установить общий анализ проекта."""
        self.project_analysis = analysis
    
    def add_dependency(self, from_file: str, to_file: str) -> None:
        """Добавить зависимость между файлами."""
        if from_file not in self.dependency_graph:
            self.dependency_graph[from_file] = []
        if to_file not in self.dependency_graph[from_file]:
            self.dependency_graph[from_file].append(to_file)
    
    def get_module_files(self, module_pattern: str) -> List[str]:
        """Получить файлы, относящиеся к модулю."""
        matching_files = []
        for file_path in self.file_reports.keys():
            if module_pattern in file_path:
                matching_files.append(file_path)
        return matching_files
    
    def get_language_stats(self) -> Dict[str, Dict[str, Any]]:
        """Получить статистику по языкам."""
        stats = {}
        for report in self.file_reports.values():
            lang = report.language
            if lang not in stats:
                stats[lang] = {
                    "files": 0,
                    "total_lines": 0,
                    "classes": 0,
                    "functions": 0
                }
            
            stats[lang]["files"] += 1
            stats[lang]["total_lines"] += report.size_lines
            stats[lang]["classes"] += len(report.classes)
            stats[lang]["functions"] += len(report.functions)
        
        return stats
    
    def save_to_json(self, filename: str = "analysis_data.json") -> None:
        """Сохранить базу знаний в JSON."""
        data = {
            "file_reports": {
                path: {
                    "file_path": report.file_path,
                    "language": report.language,
                    "size_lines": report.size_lines,
                    "classes": report.classes,
                    "functions": report.functions,
                    "imports": report.imports,
                    "dependencies": report.dependencies,
                    "summary": report.summary,
                    "complexity_notes": report.complexity_notes,
                    "issues": report.issues
                }
                for path, report in self.file_reports.items()
            },
            "project_analysis": {
                "project_path": self.project_analysis.project_path,
                "total_files": self.project_analysis.total_files,
                "total_lines": self.project_analysis.total_lines,
                "languages": self.project_analysis.languages,
                "entry_points": self.project_analysis.entry_points,
                "main_modules": self.project_analysis.main_modules,
                "architecture_summary": self.project_analysis.architecture_summary,
                "dependency_graph": self.project_analysis.dependency_graph
            } if self.project_analysis else None,
            "dependency_graph": self.dependency_graph,
            "metadata": self.analysis_metadata
        }
        
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_json(self, filename: str = "analysis_data.json") -> None:
        """Загрузить базу знаний из JSON."""
        input_path = self.output_dir / filename
        if not input_path.exists():
            return
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Восстановить отчеты по файлам
        for path, report_data in data.get("file_reports", {}).items():
            report = FileAnalysisReport(**report_data)
            self.file_reports[path] = report
        
        # Восстановить общий анализ
        if data.get("project_analysis"):
            self.project_analysis = ProjectAnalysis(**data["project_analysis"])
        
        # Восстановить граф зависимостей
        self.dependency_graph = data.get("dependency_graph", {})
        self.analysis_metadata = data.get("metadata", {})
    
    def generate_markdown_report(self) -> str:
        """Сгенерировать главный отчет в формате Markdown."""
        lines = []
        
        # Заголовок
        lines.append("# Анализ проекта - CodeInspector")
        lines.append("")
        
        if self.analysis_metadata.get("timestamp"):
            lines.append(f"*Анализ выполнен: {self.analysis_metadata['timestamp']}*")
            lines.append("")
        
        # Общая информация о проекте
        if self.project_analysis:
            lines.append("## Обзор проекта")
            lines.append("")
            lines.append(f"- **Путь**: {self.project_analysis.project_path}")
            lines.append(f"- **Всего файлов**: {self.project_analysis.total_files}")
            lines.append(f"- **Всего строк кода**: {self.project_analysis.total_lines:,}")
            lines.append("")
            
            if self.project_analysis.architecture_summary:
                lines.append("### Архитектура")
                lines.append("")
                lines.append(self.project_analysis.architecture_summary)
                lines.append("")
        
        # Статистика по языкам
        lang_stats = self.get_language_stats()
        if lang_stats:
            lines.append("## Статистика по языкам")
            lines.append("")
            lines.append("| Язык | Файлов | Строк | Классов | Функций |")
            lines.append("|------|--------|-------|---------|---------|")
            
            for lang, stats in sorted(lang_stats.items()):
                lines.append(f"| {lang} | {stats['files']} | {stats['total_lines']:,} | {stats['classes']} | {stats['functions']} |")
            lines.append("")
        
        # Граф зависимостей
        if self.dependency_graph:
            lines.append("## Граф зависимостей")
            lines.append("")
            lines.append("```mermaid")
            lines.append("graph TD")
            
            # Создаем узлы и связи
            for from_file, to_files in self.dependency_graph.items():
                from_node = self._sanitize_node_name(from_file)
                for to_file in to_files:
                    to_node = self._sanitize_node_name(to_file)
                    lines.append(f"    {from_node} --> {to_node}")
            
            lines.append("```")
            lines.append("")
        
        # Детальный анализ файлов
        lines.append("## Анализ файлов")
        lines.append("")
        
        for file_path, report in sorted(self.file_reports.items()):
            lines.append(f"### {file_path}")
            lines.append("")
            lines.append(f"- **Язык**: {report.language}")
            lines.append(f"- **Размер**: {report.size_lines} строк")
            
            if report.summary:
                lines.append(f"- **Описание**: {report.summary}")
            
            if report.classes:
                lines.append("")
                lines.append("**Классы:**")
                for cls in report.classes:
                    lines.append(f"- `{cls.get('name', 'Unknown')}`: {cls.get('description', 'Без описания')}")
            
            if report.functions:
                lines.append("")
                lines.append("**Функции:**")
                for func in report.functions[:10]:  # Ограничиваем вывод
                    lines.append(f"- `{func.get('name', 'Unknown')}`: {func.get('description', 'Без описания')}")
                
                if len(report.functions) > 10:
                    lines.append(f"- *...и еще {len(report.functions) - 10} функций*")
            
            if report.imports:
                lines.append("")
                lines.append("**Импорты:**")
                for imp in report.imports[:5]:  # Показываем только первые 5
                    lines.append(f"- {imp}")
                if len(report.imports) > 5:
                    lines.append(f"- *...и еще {len(report.imports) - 5} импортов*")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _sanitize_node_name(self, file_path: str) -> str:
        """Очистить имя файла для использования в диаграммах."""
        # Убираем путь и расширение, заменяем спецсимволы
        name = Path(file_path).stem
        name = name.replace("-", "_").replace(".", "_")
        return f"node_{name}"
    
    def save_markdown_report(self, filename: str = "README_ANALYSIS.md") -> None:
        """Сохранить отчет в Markdown файл."""
        content = self.generate_markdown_report()
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def clear(self) -> None:
        """Очистить базу знаний."""
        self.file_reports.clear()
        self.project_analysis = None
        self.dependency_graph.clear()
        self.analysis_metadata.clear()

    def merge(self, other: "KnowledgeBase") -> None:
        """Merge another KnowledgeBase into this one."""
        for path, report in other.file_reports.items():
            self.file_reports[path] = report
        for src, deps in other.dependency_graph.items():
            for dep in deps:
                self.add_dependency(src, dep)
