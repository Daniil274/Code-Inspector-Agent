#!/usr/bin/env python3
"""
Тесты для агентов CodeInspector.
Проверяет работу исправленных агентов на тестовом проекте.
"""

import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# Добавляем путь к модулям src
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "..", "..", "src")
sys.path.insert(0, src_path)

# Добавляем путь к модулям CodeInspector
sys.path.insert(0, current_dir)

from agents.master_agent import MasterAgent
from agents.file_analysis_agent import FileAnalysisAgent
from agents.writer_agent import WriterAgent
from core.knowledge_base import KnowledgeBase, FileAnalysisReport


class TestCodeInspectorAgents:
    """Тесты для агентов CodeInspector."""
    
    def __init__(self):
        self.test_project_path = "test_project"
        self.temp_output_dir = None
    
    def setup_test_environment(self):
        """Настройка тестового окружения."""
        # Создаем временную директорию для результатов
        self.temp_output_dir = tempfile.mkdtemp(prefix="codeinspector_test_")
        
        # Создаем тестовую конфигурацию
        self.create_test_config()
        
        print(f"[Test] Тестовое окружение настроено: {self.temp_output_dir}")
    
    def create_test_config(self):
        """Создание тестовой конфигурации."""
        if not self.temp_output_dir:
            raise ValueError("temp_output_dir не инициализирован")
            
        config_dir = Path(self.temp_output_dir) / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Создаем models.yaml
        models_config = {
            "models": {
                "master_agent": {
                    "provider": "openrouter",
                    "model": "gpt-4o-mini",
                    "settings": {"temperature": 0.1, "max_tokens": 2000}
                },
                "file_analysis_agent": {
                    "provider": "openrouter",
                    "model": "gpt-3.5-turbo",
                    "settings": {"temperature": 0.3, "max_tokens": 4000}
                },
                "writer_agent": {
                    "provider": "openrouter",
                    "model": "gpt-4o-mini",
                    "settings": {"temperature": 0.3, "max_tokens": 4000}
                }
            }
        }
        
        with open(config_dir / "models.yaml", 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(models_config, f, default_flow_style=False)
        
        # Создаем settings.yaml
        settings_config = {
            "ignore_directories": ["__pycache__", ".git", "node_modules"],
            "ignore_files": ["*.pyc", "*.log"],
            "analysis": {
                "max_depth": 5,
                "max_file_size_kb": 1000,
                "max_concurrent_agents": 3,
                "max_files_per_batch": 10
            }
        }
        
        with open(config_dir / "settings.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(settings_config, f, default_flow_style=False)
    
    async def test_file_analysis_agent(self):
        """Тест FileAnalysisAgent."""
        print("\n[Test] Тестирование FileAnalysisAgent...")
        
        try:
            # Создаем агента
            config = {
                "provider": "openrouter",
                "model": "gpt-3.5-turbo",
                "settings": {"temperature": 0.3, "max_tokens": 1000}
            }
            
            agent = FileAnalysisAgent(config)
            
            # Тестируем на основном файле
            test_file = os.path.join(self.test_project_path, "main.py")
            if os.path.exists(test_file):
                report = await agent.analyze_file(test_file)
                
                if report:
                    print(f"[Test] ✓ FileAnalysisAgent успешно проанализировал {test_file}")
                    print(f"[Test]   - Язык: {report.language}")
                    print(f"[Test]   - Строк: {report.size_lines}")
                    print(f"[Test]   - Классов: {len(report.classes)}")
                    print(f"[Test]   - Функций: {len(report.functions)}")
                    print(f"[Test]   - Проблем: {len(report.issues)}")
                    print(f"[Test]   - Заметок о сложности: {len(report.complexity_notes)}")
                    
                    # Проверяем, что issues заполнены
                    if report.issues:
                        print(f"[Test] ✓ Issues обнаружены: {report.issues[:2]}")
                    else:
                        print(f"[Test] ⚠ Issues не обнаружены")
                    
                    return True
                else:
                    print(f"[Test] ✗ FileAnalysisAgent не смог проанализировать {test_file}")
                    return False
            else:
                print(f"[Test] ✗ Тестовый файл не найден: {test_file}")
                return False
                
        except Exception as e:
            print(f"[Test] ✗ Ошибка в FileAnalysisAgent: {e}")
            return False
    
    async def test_writer_agent(self):
        """Тест WriterAgent."""
        print("\n[Test] Тестирование WriterAgent...")
        
        try:
            # Создаем тестовую базу знаний
            kb = KnowledgeBase()
            
            # Добавляем тестовые данные
            test_report = FileAnalysisReport(
                file_path="test_file.py",
                language="python",
                size_lines=100,
                classes=[{"name": "TestClass", "description": "Тестовый класс"}],
                functions=[{"name": "test_function", "description": "Тестовая функция"}],
                imports=["os", "sys"],
                dependencies=["test_dep"],
                summary="Тестовый файл для демонстрации",
                complexity_notes=["Файл имеет среднюю сложность"],
                issues=["Функция слишком длинная"]
            )
            
            kb.add_file_report("test_file.py", test_report)
            
            # Создаем агента
            config = {
                "provider": "openrouter",
                "model": "gpt-4o-mini",
                "settings": {"temperature": 0.3, "max_tokens": 2000}
            }
            
            composer = WriterAgent(config)
            
            # Генерируем документацию
            documentation = await composer.write_documentation(kb)
            
            if documentation:
                print(f"[Test] ✓ WriterAgent успешно создал документацию")
                print(f"[Test]   - Длина документации: {len(documentation)} символов")
                
                # Проверяем наличие ключевых разделов
                required_sections = [
                    "## Обзор проекта",
                    "## Статистика", 
                    "## Архитектура",
                    "## Модули и компоненты",
                    "## Рекомендации",
                    "## Поддерживаемые языки",
                    "## Конфигурация анализа"
                ]
                
                missing_sections = []
                for section in required_sections:
                    if section not in documentation:
                        missing_sections.append(section)
                
                if missing_sections:
                    print(f"[Test] ⚠ Отсутствуют разделы: {missing_sections}")
                else:
                    print(f"[Test] ✓ Все необходимые разделы присутствуют")
                
                return True
            else:
                print(f"[Test] ✗ WriterAgent не смог создать документацию")
                return False
                
        except Exception as e:
            print(f"[Test] ✗ Ошибка в WriterAgent: {e}")
            return False
    
    async def test_master_agent_config_loading(self):
        """Тест загрузки конфигурации MasterAgent."""
        print("\n[Test] Тестирование загрузки конфигурации MasterAgent...")
        
        try:
            # Создаем MasterAgent с тестовой конфигурацией
            master = MasterAgent(config_path=self.temp_output_dir)
            
            # Проверяем, что конфигурация загружена
            if master.config.get('models') and master.config.get('settings'):
                print(f"[Test] ✓ Конфигурация MasterAgent загружена успешно")
                print(f"[Test]   - Модели: {list(master.config['models'].keys())}")
                print(f"[Test]   - Настройки: {list(master.config['settings'].keys())}")
                return True
            else:
                print(f"[Test] ✗ Конфигурация MasterAgent не загружена")
                return False
                
        except Exception as e:
            print(f"[Test] ✗ Ошибка при загрузке конфигурации MasterAgent: {e}")
            return False
    
    async def test_integration(self):
        """Интеграционный тест всех агентов."""
        print("\n[Test] Интеграционный тест...")
        
        try:
            # Создаем MasterAgent
            master = MasterAgent(config_path=self.temp_output_dir)
            
            # Запускаем анализ тестового проекта
            print(f"[Test] Запуск анализа проекта: {self.test_project_path}")
            
            # Примечание: для полного теста нужен API ключ
            # Здесь тестируем только инициализацию и планирование
            project_files = await master._scan_project(self.test_project_path)
            
            if project_files:
                print(f"[Test] ✓ Сканирование проекта успешно: найдено {len(project_files)} файлов")
                
                # Тестируем планирование
                plan = await master._create_analysis_plan(self.test_project_path, project_files)
                
                if plan:
                    print(f"[Test] ✓ Планирование успешно")
                    print(f"[Test]   - Приоритетных файлов: {len(plan['priority_files'])}")
                    print(f"[Test]   - Групп файлов: {len(plan['file_groups'])}")
                    return True
                else:
                    print(f"[Test] ✗ Планирование не удалось")
                    return False
            else:
                print(f"[Test] ✗ Сканирование проекта не удалось")
                return False
                
        except Exception as e:
            print(f"[Test] ✗ Ошибка в интеграционном тесте: {e}")
            return False
    
    def cleanup(self):
        """Очистка тестового окружения."""
        if self.temp_output_dir and os.path.exists(self.temp_output_dir):
            shutil.rmtree(self.temp_output_dir)
            print(f"[Test] Тестовое окружение очищено: {self.temp_output_dir}")
    
    async def run_all_tests(self):
        """Запуск всех тестов."""
        print("=" * 60)
        print("ТЕСТИРОВАНИЕ АГЕНТОВ CODEINSPECTOR")
        print("=" * 60)
        
        self.setup_test_environment()
        
        results = {}
        
        # Тесты отдельных агентов
        results['file_analysis_agent'] = await self.test_file_analysis_agent()
        results['writer_agent'] = await self.test_writer_agent()
        results['master_agent_config'] = await self.test_master_agent_config_loading()
        results['integration'] = await self.test_integration()
        
        # Вывод результатов
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✓ ПРОЙДЕН" if result else "✗ ПРОВАЛЕН"
            print(f"{test_name:25} {status}")
            if result:
                passed += 1
        
        print(f"\nИтого: {passed}/{total} тестов пройдено")
        
        if passed == total:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        else:
            print("⚠ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        
        self.cleanup()
        return passed == total


async def main():
    """Главная функция тестирования."""
    tester = TestCodeInspectorAgents()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ Все исправления работают корректно!")
        return 0
    else:
        print("\n❌ Некоторые исправления требуют доработки")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 