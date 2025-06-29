"""
Мастер-агент системы CodeInspector.
Координирует анализ проекта, управляет другими агентами и собирает результаты.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import ast

import yaml
from src.agents import Agent, Runner, RunConfig, function_tool
from src.agents.models.openrouter_provider import OpenRouterProvider
from src.agents.models.lmstudio_provider import LMStudioProvider
from src.agents.model_settings import ModelSettings

from core.knowledge_base import KnowledgeBase, ProjectAnalysis
from parser.language_support import LanguageSupport, scan_directory, filter_code_files
from agents.file_analysis_agent import FileAnalysisAgent
from agents.writer_agent import WriterAgent


class MasterAgent:
    """Главный агент системы CodeInspector."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config"
        self.config = self._load_config()
        self.knowledge_base = KnowledgeBase()
        self.language_support = LanguageSupport()
        
        # Создаем планирующего агента
        self.planning_agent = Agent(
            name="CodeAnalysisPlanner",
            instructions="""
            Ты - опытный системный аналитик и архитектор ПО. Твоя задача - планировать анализ кодовой базы.

            ЦЕЛЬ: Создать план эффективного анализа проекта для максимального понимания архитектуры и логики.

            ПРИНЦИПЫ:
            1. Приоритизируй файлы по важности (точки входа, основные модули, конфигурация)
            2. Группируй связанные файлы для лучшего понимания контекста
            3. Определяй оптимальную последовательность анализа
            4. Учитывай размер и сложность файлов
            5. Фокусируйся на архитектурно значимых компонентах

            ОТВЕТ на русском языке, структурированно и конкретно.
            """,
            tools=[
                function_tool(self._get_project_structure),
                function_tool(self._analyze_file_importance)
            ]  # type: ignore
        )
    
    def _load_config(self) -> Dict:
        """Загрузка конфигурации с обработкой ошибок."""
        config = {
            'models': {},
            'settings': {},
            'providers': {},
            'fallback_configs': {}
        }
        
        try:
            # Загружаем конфигурацию моделей
            models_config_path = Path(self.config_path) / "models.yaml"
            if models_config_path.exists():
                with open(models_config_path, 'r', encoding='utf-8') as f:
                    models_yaml = yaml.safe_load(f)
                    if models_yaml:
                        config['models'] = models_yaml.get('models', {})
                        config['providers'] = models_yaml.get('providers', {})
                        config['fallback_configs'] = models_yaml.get('fallback_configs', {})
                        print(f"[MasterAgent] Загружена конфигурация моделей из {models_config_path}")
                    else:
                        print(f"[MasterAgent] Предупреждение: файл {models_config_path} пуст или некорректен")
            else:
                print(f"[MasterAgent] Предупреждение: файл конфигурации моделей не найден: {models_config_path}")
        
        except Exception as e:
            print(f"[MasterAgent] Ошибка при загрузке конфигурации моделей: {e}")
        
        try:
            # Загружаем общие настройки
            settings_config_path = Path(self.config_path) / "settings.yaml"
            if settings_config_path.exists():
                with open(settings_config_path, 'r', encoding='utf-8') as f:
                    settings_yaml = yaml.safe_load(f)
                    if settings_yaml:
                        config['settings'] = settings_yaml
                        print(f"[MasterAgent] Загружена конфигурация настроек из {settings_config_path}")
                    else:
                        print(f"[MasterAgent] Предупреждение: файл {settings_config_path} пуст или некорректен")
            else:
                print(f"[MasterAgent] Предупреждение: файл настроек не найден: {settings_config_path}")
        
        except Exception as e:
            print(f"[MasterAgent] Ошибка при загрузке настроек: {e}")
        
        # Устанавливаем значения по умолчанию
        self._set_default_config(config)
        
        return config
    
    def _set_default_config(self, config: Dict) -> None:
        """Установка значений по умолчанию для конфигурации."""
        # Настройки по умолчанию для моделей
        if not config.get('models'):
            config['models'] = {
                'master_agent': {
                    'provider': 'openrouter',
                    'model': 'gpt-4o-mini',
                    'settings': {'temperature': 0.1, 'max_tokens': 2000}
                },
                'file_analysis_agent': {
                    'provider': 'openrouter',
                    'model': 'gpt-3.5-turbo',
                    'settings': {'temperature': 0.3, 'max_tokens': 4000}
                },
                'writer_agent': {
                    'provider': 'openrouter',
                    'model': 'gpt-4o-mini',
                    'settings': {'temperature': 0.3, 'max_tokens': 4000}
                }
            }
        
        # Настройки по умолчанию
        if not config.get('settings'):
            config['settings'] = {
                'ignore_directories': ['__pycache__', '.git', 'node_modules', '.venv', 'dist', 'build'],
                'ignore_files': ['*.pyc', '*.log', '.DS_Store'],
                'analysis': {
                    'max_depth': 10,
                    'max_file_size_kb': 500,
                    'max_concurrent_agents': 5,
                    'max_files_per_batch': 50
                }
            }
        
        print("[MasterAgent] Использованы настройки по умолчанию")
    
    async def analyze_project(self, project_path: str) -> str:
        """Полный анализ проекта."""
        start_time = time.time()
        
        try:
            print(f"[MasterAgent] Начинаю анализ проекта: {project_path}")
            
            # 1. Инициализация базы знаний
            self.knowledge_base.clear()
            self.knowledge_base.analysis_metadata["timestamp"] = datetime.now().isoformat()
            
            # 2. Сканирование проекта
            print("[MasterAgent] Сканирую структуру проекта...")
            project_files = await self._scan_project(project_path)
            
            if not project_files:
                return "Не найдено файлов для анализа в указанной директории."
            
            print(f"[MasterAgent] Найдено {len(project_files)} файлов для анализа")
            
            # 3. Планирование анализа
            print("[MasterAgent] Планирую стратегию анализа...")
            analysis_plan = await self._create_analysis_plan(project_path, project_files)
            
            # 4. Выполнение анализа файлов
            print("[MasterAgent] Выполняю анализ файлов...")
            await self._execute_file_analysis(analysis_plan)
            
            # 5. Анализ зависимостей и создание общего анализа проекта
            print("[MasterAgent] Анализирую архитектуру проекта...")
            await self._analyze_project_architecture(project_path, project_files)
            
            # 6. Генерация документации
            print("[MasterAgent] Генерирую документацию...")
            documentation = await self._generate_documentation()
            
            # 7. Сохранение результатов
            self.knowledge_base.analysis_metadata["analysis_duration"] = time.time() - start_time
            self.knowledge_base.save_to_json()
            self.knowledge_base.save_markdown_report()
            
            print(f"[MasterAgent] Анализ завершен за {time.time() - start_time:.2f} секунд")
            return documentation
            
        except Exception as e:
            print(f"[MasterAgent] Ошибка при анализе проекта: {e}")
            return f"Ошибка при анализе проекта: {e}"
    
    async def _scan_project(self, project_path: str) -> List[str]:
        """Сканирование проекта и поиск файлов для анализа."""
        settings = self.config.get('settings', {})
        analysis_settings = settings.get('analysis', {})
        
        # Параметры сканирования
        max_depth = analysis_settings.get('max_depth', 10)
        ignore_dirs = settings.get('ignore_directories', [])
        ignore_files = settings.get('ignore_files', [])
        max_file_size = analysis_settings.get('max_file_size_kb', 500) * 1024
        
        # Сканируем директорию
        all_files = scan_directory(project_path, max_depth, ignore_dirs)
        
        # Фильтруем файлы
        code_files = filter_code_files(all_files, ignore_files)
        
        # Фильтруем по размеру
        filtered_files = []
        for file_path in code_files:
            try:
                if os.path.getsize(file_path) <= max_file_size:
                    filtered_files.append(file_path)
                else:
                    print(f"[MasterAgent] Пропускаю большой файл: {file_path}")
            except OSError:
                continue
        
        return filtered_files
    
    async def _create_analysis_plan(self, project_path: str, files: List[str]) -> Dict:
        """Создание плана анализа с помощью планирующего агента."""
        try:
            # Подготавливаем контекст для планирования
            file_info = []
            for file_path in files[:20]:  # Ограничиваем для анализа
                rel_path = os.path.relpath(file_path, project_path)
                file_size = os.path.getsize(file_path)
                language = self.language_support.detect_language(file_path)
                
                file_info.append({
                    "path": rel_path,
                    "size": file_size,
                    "language": language,
                    "is_entry_point": self.language_support.is_entry_point_file(file_path)
                })
            
            # Запрос к планирующему агенту
            planning_prompt = f"""
            Проанализируй структуру проекта и создай план анализа:

            Путь проекта: {project_path}
            Всего файлов: {len(files)}
            
            Примеры файлов:
            {self._format_file_info(file_info)}

            Создай план анализа, определив:
            1. Приоритетные файлы для анализа (порядок важности)
            2. Группировку файлов по модулям/компонентам
            3. Рекомендации по стратегии анализа

            Отвечай структурированно на русском языке.
            """
            
            plan_result = await self._run_planning_agent(planning_prompt)
            
            # Создаем структурированный план
            plan = {
                "priority_files": self._extract_priority_files(files),
                "file_groups": self._group_files_by_modules(files),
                "strategy": plan_result or "Последовательный анализ файлов по приоритету",
                "total_files": len(files)
            }
            
            return plan
            
        except Exception as e:
            print(f"[MasterAgent] Ошибка при планировании: {e}")
            # Возвращаем базовый план
            return {
                "priority_files": files,
                "file_groups": {"main": files},
                "strategy": "Базовый последовательный анализ",
                "total_files": len(files)
            }
    
    def _extract_priority_files(self, files: List[str]) -> List[str]:
        """Определение приоритетных файлов."""
        priority_files = []
        regular_files = []
        
        for file_path in files:
            filename = os.path.basename(file_path).lower()
            
            # Высокий приоритет
            if any(name in filename for name in ['main', 'index', 'app', 'server', 'cli', '__init__']):
                priority_files.append(file_path)
            # Конфигурационные файлы
            elif any(name in filename for name in ['config', 'settings', 'setup']):
                priority_files.append(file_path)
            # Точки входа
            elif self.language_support.is_entry_point_file(file_path):
                priority_files.append(file_path)
            else:
                regular_files.append(file_path)
        
        return priority_files + regular_files
    
    def _group_files_by_modules(self, files: List[str]) -> Dict[str, List[str]]:
        """Группировка файлов по модулям."""
        modules = {}
        
        for file_path in files:
            # Группируем по директориям
            dir_name = os.path.dirname(file_path)
            if not dir_name:
                dir_name = "root"
            
            if dir_name not in modules:
                modules[dir_name] = []
            modules[dir_name].append(file_path)
        
        return modules
    
    async def _execute_file_analysis(self, plan: Dict) -> None:
        """Выполнение анализа файлов согласно плану."""
        files_to_analyze = plan["priority_files"]
        max_concurrent = self.config.get('settings', {}).get('analysis', {}).get('max_concurrent_agents', 5)
        max_files = self.config.get('settings', {}).get('analysis', {}).get('max_files_per_batch', 50)
        
        # Ограничиваем количество файлов
        if len(files_to_analyze) > max_files:
            print(f"[MasterAgent] Ограничиваю анализ до {max_files} файлов (из {len(files_to_analyze)})")
            files_to_analyze = files_to_analyze[:max_files]
        
        # Создаем агента для анализа файлов
        file_agent_config = self.config.get('models', {}).get('file_analysis_agent', {})
        
        # Группируем файлы для параллельной обработки
        file_batches = [files_to_analyze[i:i + max_concurrent] 
                       for i in range(0, len(files_to_analyze), max_concurrent)]
        
        total_processed = 0
        for batch_idx, batch in enumerate(file_batches):
            print(f"[MasterAgent] Обрабатываю батч {batch_idx + 1}/{len(file_batches)} ({len(batch)} файлов)")
            
            # Создаем задачи для параллельного выполнения
            tasks = []
            for file_path in batch:
                # Исправление: передаем file_agent_config явно
                agent = FileAnalysisAgent(file_agent_config)
                task = asyncio.create_task(agent.analyze_file(file_path))
                tasks.append((file_path, task))
            
            # Ждем завершения всех задач в батче
            for file_path, task in tasks:
                try:
                    result = await task
                    if result:
                        self.knowledge_base.add_file_report(file_path, result)
                        # Добавляем зависимости в граф
                        for dep in result.dependencies:
                            self.knowledge_base.add_dependency(file_path, dep)
                        total_processed += 1
                    else:
                        print(f"[MasterAgent] Не удалось проанализировать файл: {file_path}")
                        
                except Exception as e:
                    print(f"[MasterAgent] Ошибка при анализе файла {file_path}: {e}")
            
            print(f"[MasterAgent] Батч завершен. Обработано файлов: {total_processed}")
    
    async def _analyze_project_architecture(self, project_path: str, files: List[str]) -> None:
        """Анализ архитектуры проекта."""
        try:
            # Создаем общий анализ проекта
            total_lines = sum(report.size_lines for report in self.knowledge_base.file_reports.values())
            languages = self.knowledge_base.get_language_stats()
            
            # Определяем точки входа
            entry_points = []
            for file_path, report in self.knowledge_base.file_reports.items():
                if self.language_support.is_entry_point_file(file_path):
                    entry_points.append(file_path)
            
            # Определяем основные модули
            main_modules = list(self.knowledge_base.get_language_stats().keys())
            
            # Генерируем архитектурное описание с помощью планирующего агента
            architecture_prompt = f"""
            Проанализируй архитектуру проекта на основе собранных данных:

            Общая статистика:
            - Файлов проанализировано: {len(self.knowledge_base.file_reports)}
            - Общее количество строк: {total_lines:,}
            - Языки: {', '.join(languages.keys())}
            - Точки входа: {', '.join([os.path.basename(f) for f in entry_points])}

            Основные модули: {', '.join(main_modules)}
            
            Создай краткое описание архитектуры проекта (2-3 предложения).
            """
            
            architecture_summary = await self._run_planning_agent(architecture_prompt)
            
            project_analysis = ProjectAnalysis(
                project_path=project_path,
                total_files=len(files),
                total_lines=total_lines,
                languages={lang: stats['files'] for lang, stats in languages.items()},
                entry_points=entry_points,
                main_modules=main_modules,
                architecture_summary=architecture_summary or "Многомодульный проект с разделением по функциональности.",
                dependency_graph=self.knowledge_base.dependency_graph
            )
            
            self.knowledge_base.set_project_analysis(project_analysis)
            
        except Exception as e:
            print(f"[MasterAgent] Ошибка при анализе архитектуры: {e}")
    
    async def _generate_documentation(self) -> str:
        """Генерация финальной документации."""
        try:
            composer_config = self.config.get('models', {}).get('writer_agent', {})
            composer = WriterAgent(composer_config)

            documentation = await composer.write_documentation(self.knowledge_base)
            return documentation
            
        except Exception as e:
            print(f"[MasterAgent] Ошибка при генерации документации: {e}")
            # Возвращаем базовую документацию
            return self.knowledge_base.generate_markdown_report()
    
    def _format_file_info(self, file_info: List[Dict]) -> str:
        """Форматирование информации о файлах."""
        lines = []
        for info in file_info:
            size_kb = info['size'] // 1024
            entry_mark = " (точка входа)" if info['is_entry_point'] else ""
            lines.append(f"- {info['path']} ({info['language']}, {size_kb}KB){entry_mark}")
        return "\n".join(lines)
    
    async def _run_planning_agent(self, prompt: str) -> Optional[str]:
        """Запуск планирующего агента."""
        try:
            master_config = self.config.get('models', {}).get('master_agent', {})
            provider = self._create_model_provider(master_config)
            model_settings = ModelSettings(
                temperature=master_config.get('settings', {}).get('temperature', 0.1),
                max_tokens=master_config.get('settings', {}).get('max_tokens', 2000)
            )
            
            result = await Runner.run(
                self.planning_agent,
                prompt,
                run_config=RunConfig(
                    model_provider=provider,
                    model=master_config.get('model', 'gpt-4o-mini'),
                    model_settings=model_settings
                )
            )
            
            return result.final_output.strip() if result.final_output else None
            
        except Exception as e:
            print(f"[MasterAgent] Ошибка при выполнении планирования: {e}")
            return None
    
    def _create_model_provider(self, model_config: Dict):
        """Создание провайдера модели."""
        provider_type = model_config.get('provider', 'openrouter')
        
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
    
    @function_tool
    def _get_project_structure(self, path: str) -> str:
        """Получение структуры проекта для планирующего агента."""
        try:
            files = scan_directory(path, max_depth=3)
            structure = {}
            
            for file_path in files[:20]:  # Ограничиваем для обзора
                rel_path = os.path.relpath(file_path, path)
                dir_name = os.path.dirname(rel_path) or "root"
                
                if dir_name not in structure:
                    structure[dir_name] = []
                structure[dir_name].append(os.path.basename(rel_path))
            
            result = []
            for dir_name, files_list in structure.items():
                result.append(f"{dir_name}/: {', '.join(files_list[:5])}")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"Ошибка при получении структуры: {e}"
    
    @function_tool
    def _analyze_file_importance(self, file_path: str) -> str:
        """Анализ важности файла для планирующего агента."""
        try:
            filename = os.path.basename(file_path).lower()
            
            if any(name in filename for name in ['main', 'index', 'app']):
                return "Высокая важность - точка входа"
            elif any(name in filename for name in ['config', 'settings']):
                return "Высокая важность - конфигурация"
            elif filename.startswith('test_') or 'test' in filename:
                return "Средняя важность - тестовый файл"
            elif filename.startswith('__init__'):
                return "Высокая важность - инициализация модуля"
            else:
                return "Обычная важность - модуль"
                
        except Exception as e:
            return f"Ошибка при анализе важности: {e}"
    
    async def _analyze_project_goals(self, project_path: str) -> None:
        """
        Анализирует README.md и docstring главных файлов для извлечения целей и миссии проекта.
        Сохраняет результат в knowledge_base.analysis_metadata['project_goals'].
        """
        goals = []
        # 1. Анализ README.md
        readme_path = os.path.join(project_path, 'README.md')
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_text = f.read()
                # Промпт для LLM
                prompt = f"""
                Проанализируй следующий текст README.md и выдели основные цели, задачи и миссию проекта. Ответь кратко на русском языке списком.

                ---
                {readme_text[:3000]}
                ---
                """
                result = await self._run_planning_agent(prompt)
                if result:
                    goals.append(result.strip())
            except Exception as e:
                print(f"[MasterAgent] Ошибка при анализе README.md: {e}")
        # 2. Анализ docstring главных файлов (main.py, __init__.py)
        for fname in ['main.py', '__init__.py']:
            main_path = os.path.join(project_path, fname)
            if os.path.exists(main_path):
                try:
                    with open(main_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    module = ast.parse(source)
                    docstring = ast.get_docstring(module) or ''
                    if docstring:
                        prompt = f"""
                        Проанализируй следующий docstring и выдели цели и задачи этого модуля. Ответь кратко на русском языке списком.
                        ---
                        {docstring}
                        ---
                        """
                        result = await self._run_planning_agent(prompt)
                        if result:
                            goals.append(result.strip())
                except Exception as e:
                    print(f"[MasterAgent] Ошибка при анализе docstring {fname}: {e}")
        # Сохраняем результат
        self.knowledge_base.analysis_metadata['project_goals'] = '\n'.join(goals) if goals else 'Цели проекта не определены.'
