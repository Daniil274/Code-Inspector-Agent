"""
Агент-композитор для генерации финальной документации проекта.
Агрегирует результаты анализа и создает связные документы в Markdown.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional

from agents import Agent, Runner, RunConfig
from agents.models.openai_provider import OpenAIProvider
from agents.model_settings import ModelSettings

from core.knowledge_base import KnowledgeBase, ProjectAnalysis


class ComposerAgent:
    """Агент для композиции документации проекта."""
    
    def __init__(self, model_config: Dict):
        self.model_config = model_config
        
        # Создаем агента для генерации документации
        self.documentation_agent = Agent(
            name="DocumentationComposer",
            instructions="""
            Ты - технический писатель, специализирующийся на документации программного обеспечения.
            Твоя задача - создавать ясную, структурированную и полезную документацию.

            ВАЖНЫЕ ПРАВИЛА:
            1. Пиши ТОЛЬКО на русском языке
            2. Используй ясную структуру с заголовками и списками
            3. Будь точным и информативным
            4. Используй техническую терминологию правильно
            5. Делай акцент на архитектуре и взаимосвязях
            6. Включай диаграммы в формате Mermaid где это уместно

            СТИЛЬ:
            - Профессиональный, но доступный
            - Структурированный с четкой иерархией
            - Фокус на практической пользе для разработчиков
            """,
            tools=[]
        )
    
    async def compose_documentation(self, knowledge_base: KnowledgeBase) -> str:
        """Создание полной документации проекта."""
        try:
            print("[ComposerAgent] Начинаю композицию документации...")
            
            # Генерируем различные секции документации
            overview = await self._generate_project_overview(knowledge_base)
            architecture = await self._generate_architecture_section(knowledge_base)
            modules = await self._generate_modules_section(knowledge_base)
            recommendations = await self._generate_recommendations_section(knowledge_base)
            supported_languages = self._generate_supported_languages_section(knowledge_base)
            configuration = self._generate_configuration_section()
            
            # Собираем финальный документ
            documentation = self._assemble_final_document(
                overview, architecture, modules, recommendations, 
                supported_languages, configuration, knowledge_base
            )
            
            print("[ComposerAgent] Документация создана успешно")
            return documentation
            
        except Exception as e:
            print(f"[ComposerAgent] Ошибка при создании документации: {e}")
            return self._generate_fallback_documentation(knowledge_base)
    
    async def _generate_project_overview(self, kb: KnowledgeBase) -> str:
        """Генерация обзора проекта."""
        try:
            # Собираем статистику
            total_files = len(kb.file_reports)
            total_lines = sum(report.size_lines for report in kb.file_reports.values())
            languages = kb.get_language_stats()
            context = [
                f"Проект содержит {total_files} файлов",
                f"Общее количество строк кода: {total_lines:,}",
                f"Языки программирования: {', '.join(languages.keys())}",
            ]
            if kb.project_analysis:
                context.append(f"Путь к проекту: {kb.project_analysis.project_path}")
                if kb.project_analysis.entry_points:
                    context.append(f"Точки входа: {', '.join(kb.project_analysis.entry_points)}")
                if kb.project_analysis.main_modules:
                    context.append(f"Основные модули: {', '.join(kb.project_analysis.main_modules)}")
            sample_files = list(kb.file_reports.keys())[:5]
            context.append(f"Примеры файлов: {', '.join([os.path.basename(f) for f in sample_files])}")
            # Новый контекст: цели и задачи
            project_goals = kb.analysis_metadata.get('project_goals')
            if project_goals:
                context.append(f"Цели проекта: {project_goals}")
            # Новый контекст: паттерны проектирования
            patterns = []
            for report in kb.file_reports.values():
                for cls in report.classes:
                    if isinstance(cls, dict) and cls.get('pattern') and cls['pattern'] != 'Паттерн не обнаружен':
                        patterns.append(f"Класс {cls['name']}: {cls['pattern']}")
                for func in report.functions:
                    if isinstance(func, dict) and func.get('pattern') and func['pattern'] != 'Паттерн не обнаружен':
                        patterns.append(f"Функция {func['name']}: {func['pattern']}")
            if patterns:
                context.append("Обнаруженные паттерны проектирования:\n" + '\n'.join(patterns[:5]))
            prompt = f"""
            На основе следующей информации:
            {chr(10).join(context)}

            Составь глубокий обзор проекта, обязательно:
            1. Определи назначение и миссию проекта (если есть)
            2. Выдели архитектурные паттерны, слои и связи между компонентами
            3. Оцени масштаб, сложность, уникальные особенности
            4. Сделай выводы о сильных и слабых сторонах архитектуры
            5. Дай рекомендации по развитию
            Пиши профессионально, структурированно, на русском языке.
            """
            result = await self._run_documentation_generation(prompt)
            return result or "Проект представляет собой программное решение."
        except Exception as e:
            print(f"[ComposerAgent] Ошибка при генерации обзора: {e}")
            return "Не удалось сгенерировать обзор проекта."
    
    async def _generate_architecture_section(self, kb: KnowledgeBase) -> str:
        """Генерация раздела об архитектуре."""
        try:
            if kb.project_analysis and kb.project_analysis.architecture_summary:
                architecture_summary = kb.project_analysis.architecture_summary
            else:
                modules_info = []
                languages = kb.get_language_stats()
                for lang, stats in languages.items():
                    modules_info.append(f"- {lang}: {stats['files']} файлов, {stats['classes']} классов, {stats['functions']} функций")
                dependencies_info = []
                for file_path, report in list(kb.file_reports.items())[:10]:
                    if report.dependencies:
                        deps = ', '.join(report.dependencies[:3])
                        dependencies_info.append(f"- {os.path.basename(file_path)}: {deps}")
                # Новый контекст: паттерны проектирования
                patterns = []
                for report in kb.file_reports.values():
                    for cls in report.classes:
                        if isinstance(cls, dict) and cls.get('pattern') and cls['pattern'] != 'Паттерн не обнаружен':
                            patterns.append(f"Класс {cls['name']}: {cls['pattern']}")
                    for func in report.functions:
                        if isinstance(func, dict) and func.get('pattern') and func['pattern'] != 'Паттерн не обнаружен':
                            patterns.append(f"Функция {func['name']}: {func['pattern']}")
                context = [
                    "СТРУКТУРА ПО ЯЗЫКАМ:",
                    *modules_info,
                    "",
                    "ОСНОВНЫЕ ЗАВИСИМОСТИ:",
                    *dependencies_info[:5],
                ]
                if patterns:
                    context.append("")
                    context.append("Обнаруженные паттерны проектирования:")
                    context.extend(patterns[:5])
                prompt = f"""
                Проанализируй архитектуру проекта и создай раздел документации:
                {chr(10).join(context)}

                Напиши раздел "Архитектура" включающий:
                1. Общую структуру и слои проекта
                2. Ключевые компоненты и их роли
                3. Основные зависимости и взаимосвязи
                4. Архитектурные паттерны (если видны)
                5. Сделай выводы о сильных и слабых сторонах архитектуры
                Добавь Mermaid диаграмму если это поможет визуализации.
                Ответь на русском языке.
                """
                result = await self._run_documentation_generation(prompt)
                architecture_summary = result or "## Архитектура\n\nАрхитектура проекта включает несколько основных компонентов."
            return architecture_summary
        except Exception as e:
            print(f"[ComposerAgent] Ошибка при генерации архитектуры: {e}")
            return "## Архитектура\n\nОшибка при анализе архитектуры."
    
    async def _generate_modules_section(self, kb: KnowledgeBase) -> str:
        """Генерация раздела о модулях (только реальные директории и содержимое)."""
        try:
            modules = {}
            for file_path, report in kb.file_reports.items():
                dir_name = os.path.dirname(file_path) or "root"
                if dir_name not in modules:
                    modules[dir_name] = []
                modules[dir_name].append(report)
            modules_analysis = []
            for module_name, files in modules.items():
                file_count = len(files)
                total_functions = sum(len(f.functions) for f in files)
                total_classes = sum(len(f.classes) for f in files)
                modules_analysis.append(
                    f"**{module_name}**: {file_count} файлов, {total_classes} классов, {total_functions} функций"
                )
            context = ["АНАЛИЗ МОДУЛЕЙ:", *modules_analysis]
            return "## Модули и компоненты\n\n" + "\n".join(context)
        except Exception as e:
            print(f"[ComposerAgent] Ошибка при генерации модулей: {e}")
            return "## Модули и компоненты\n\nОшибка при анализе модулей."
    
    async def _generate_recommendations_section(self, kb: KnowledgeBase) -> str:
        """Генерация раздела с рекомендациями (группировка по файлам, конкретика)."""
        try:
            recommendations = []
            for file_path, report in kb.file_reports.items():
                file_issues = []
                if report.complexity_notes:
                    file_issues.extend([f"Заметка: {note}" for note in report.complexity_notes])
                if report.issues:
                    file_issues.extend([f"Проблема: {issue}" for issue in report.issues])
                if file_issues:
                    recommendations.append(f"### {os.path.basename(file_path)}\n" + "\n".join(f"- {issue}" for issue in file_issues))
            if not recommendations:
                return "## Рекомендации\n\nОсобых рекомендаций по улучшению кода не выявлено."
            return "## Рекомендации\n\n" + "\n\n".join(recommendations)
        except Exception as e:
            print(f"[ComposerAgent] Ошибка при генерации рекомендаций: {e}")
            return "## Рекомендации\n\nОшибка при анализе рекомендаций."
    
    def _generate_supported_languages_section(self, kb: KnowledgeBase) -> str:
        """Генерация раздела о реально используемых языках."""
        lang_stats = kb.get_language_stats()
        if not lang_stats:
            return "## Поддерживаемые языки\n\nНе обнаружено поддерживаемых языков."
        lines = ["## Поддерживаемые языки", ""]
        for lang in lang_stats:
            lines.append(f"- **{lang.capitalize()}**")
        return "\n".join(lines)
    
    def _generate_configuration_section(self) -> str:
        """Генерация раздела о конфигурации анализа."""
        config_info = [
            "## Конфигурация анализа",
            "",
            "### Модели и провайдеры",
            f"- **Master Agent**: {self.model_config.get('master_agent', {}).get('model', 'Не указано')}",
            f"- **File Analysis Agent**: {self.model_config.get('file_analysis_agent', {}).get('model', 'Не указано')}",
            f"- **Composer Agent**: {self.model_config.get('composer_agent', {}).get('model', 'Не указано')}",
            "",
            "### Настройки анализа",
            "- **Максимальная глубина сканирования**: 10 уровней",
            "- **Максимальный размер файла**: 500KB",
            "- **Максимум параллельных агентов**: 5",
            "- **Максимум файлов в батче**: 50"
        ]
        
        return "\n".join(config_info)
    
    def _assemble_final_document(self, overview: str, architecture: str, 
                                modules: str, recommendations: str,
                                supported_languages: str, configuration: str,
                                kb: KnowledgeBase) -> str:
        """Сборка финального документа."""
        lines = []
        project_name = "Анализ проекта"
        if kb.project_analysis:
            project_name = os.path.basename(kb.project_analysis.project_path) or "Анализ проекта"
        lines.append(f"# {project_name}")
        lines.append("")
        lines.append(f"*Анализ выполнен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        lines.append("## Обзор проекта")
        lines.append("")
        lines.append(overview)
        # Новая секция: цели и задачи
        project_goals = kb.analysis_metadata.get('project_goals')
        if project_goals:
            lines.append("")
            lines.append("## Цели и задачи проекта")
            lines.append("")
            lines.append(project_goals)
        lines.append("")
        lines.append("## Статистика")
        lines.append("")
        lang_stats = kb.get_language_stats()
        if lang_stats:
            lines.append("| Язык | Файлов | Строк | Классов | Функций |")
            lines.append("|------|--------|-------|---------|---------|")
            for lang, stats in sorted(lang_stats.items()):
                lines.append(f"| {lang} | {stats['files']} | {stats['total_lines']:,} | {stats['classes']} | {stats['functions']} |")
            lines.append("")
        lines.append(architecture)
        lines.append("")
        lines.append(modules)
        lines.append("")
        if kb.dependency_graph:
            lines.append("## Граф зависимостей")
            lines.append("")
            lines.append("```mermaid")
            lines.append("graph TD")
            count = 0
            for from_file, to_files in kb.dependency_graph.items():
                if count >= 20:
                    break
                from_node = self._sanitize_node_name(from_file)
                for to_file in to_files[:3]:
                    to_node = self._sanitize_node_name(to_file)
                    lines.append(f"    {from_node} --> {to_node}")
                    count += 1
            lines.append("```")
            lines.append("")
        lines.append("## Детальный анализ файлов")
        lines.append("")
        interesting_files = []
        for file_path, report in kb.file_reports.items():
            score = len(report.classes) * 2 + len(report.functions)
            interesting_files.append((score, file_path, report))
        interesting_files.sort(reverse=True)
        for _, file_path, report in interesting_files[:10]:
            lines.append(f"### {os.path.basename(file_path)}")
            lines.append("")
            lines.append(f"- **Путь**: `{file_path}`")
            lines.append(f"- **Язык**: {report.language}")
            lines.append(f"- **Размер**: {report.size_lines} строк")
            if report.summary:
                lines.append(f"- **Описание**: {report.summary}")
            if report.classes:
                lines.append("")
                lines.append("**Классы:**")
                for cls in report.classes[:5]:
                    lines.append(f"- `{cls.get('name', 'Unknown')}`: {cls.get('description', 'Без описания')}")
            if report.functions:
                lines.append("")
                lines.append("**Функции:**")
                for func in report.functions[:5]:
                    lines.append(f"- `{func.get('name', 'Unknown')}`: {func.get('description', 'Без описания')}")
            if report.complexity_notes:
                lines.append("")
                lines.append("**Заметки о сложности:**")
                for note in report.complexity_notes:
                    lines.append(f"- {note}")
            if report.issues:
                lines.append("")
                lines.append("**Проблемы:**")
                for issue in report.issues:
                    lines.append(f"- {issue}")
            lines.append("")
        lines.append(recommendations)
        lines.append("")
        lines.append(supported_languages)
        lines.append("")
        lines.append(configuration)
        lines.append("")
        return "\n".join(lines)
    
    def _sanitize_node_name(self, file_path: str) -> str:
        """Очистка имени файла для использования в диаграммах."""
        name = os.path.basename(file_path).replace('.', '_').replace('-', '_')
        return f"node_{name}"
    
    def _generate_fallback_documentation(self, kb: KnowledgeBase) -> str:
        """Генерация базовой документации при ошибках."""
        try:
            # Пытаемся использовать метод из KnowledgeBase
            if hasattr(kb, 'generate_markdown_report'):
                return kb.generate_markdown_report()
            else:
                # Создаем базовую документацию
                lines = []
                lines.append("# Анализ проекта")
                lines.append("")
                lines.append(f"*Анализ выполнен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
                lines.append("")
                lines.append("## Обзор")
                lines.append("")
                lines.append(f"Проанализировано файлов: {len(kb.file_reports)}")
                if kb.project_analysis:
                    lines.append(f"Путь к проекту: {kb.project_analysis.project_path}")
                lines.append("")
                lines.append("## Файлы")
                lines.append("")
                for file_path, report in kb.file_reports.items():
                    lines.append(f"- `{file_path}` ({report.language}, {report.size_lines} строк)")
                return "\n".join(lines)
        except Exception as e:
            print(f"[ComposerAgent] Ошибка при создании fallback документации: {e}")
            return "# Анализ проекта\n\nОшибка при создании документации."
    
    async def _run_documentation_generation(self, prompt: str) -> Optional[str]:
        """Выполнение генерации документации с помощью LLM."""
        try:
            provider = self._create_model_provider()
            model_settings = ModelSettings(
                temperature=self.model_config.get('settings', {}).get('temperature', 0.3),
                max_tokens=self.model_config.get('settings', {}).get('max_tokens', 4000)
            )
            
            result = await Runner.run(
                self.documentation_agent,
                prompt,
                run_config=RunConfig(
                    model_provider=provider,
                    model=self.model_config.get('model', 'gpt-4o-mini'),
                    model_settings=model_settings
                )
            )
            
            return result.final_output.strip() if result.final_output else None
            
        except Exception as e:
            print(f"[ComposerAgent] Ошибка при генерации документации: {e}")
            return None
    
    def _create_model_provider(self):
        """Создание провайдера модели."""
        provider_type = self.model_config.get('provider', 'openai')

        if provider_type in ('openai', 'openrouter', 'lmstudio'):
            api_key = os.getenv('OPENAI_API_KEY', os.getenv('OPENROUTER_API_KEY'))
            base_url = os.getenv('OPENAI_BASE_URL', os.getenv('LMSTUDIO_BASE_URL'))
            return OpenAIProvider(api_key=api_key, base_url=base_url)

        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider_type}")
