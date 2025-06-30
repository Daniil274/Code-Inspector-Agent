#!/usr/bin/env python3
"""
Главная точка входа системы CodeInspector.
Мультиагентная система анализа программного кода.
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent))

from ci_agents.master_agent import MasterAgent
# Импортируем трассировку из основной библиотеки
from src.agents.tracing import set_trace_processors
from src.agents.tracing.processors import ConsoleSpanExporter, BatchTraceProcessor


async def main():
    """Главная функция приложения."""
    parser = argparse.ArgumentParser(
        description="CodeInspector - мультиагентная система анализа кода",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py /path/to/project
  python main.py --config custom_config /path/to/project
  python main.py --output custom_output /path/to/project

Переменные окружения:
  OPENROUTER_API_KEY - API ключ для OpenRouter (обязательно)
  LMSTUDIO_BASE_URL  - URL для LM Studio (по умолчанию: http://localhost:1234/v1)
        """
    )
    
    parser.add_argument(
        'project_path',
        help='Путь к анализируемому проекту'
    )
    
    parser.add_argument(
        '--config',
        default='config',
        help='Путь к директории с конфигурациями (по умолчанию: config)'
    )
    
    parser.add_argument(
        '--output',
        default='output',
        help='Путь к директории для сохранения результатов (по умолчанию: output)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод'
    )
    
    args = parser.parse_args()
    
    # Включаем логгирование трассировки в консоль
    console_exporter = ConsoleSpanExporter()
    console_processor = BatchTraceProcessor(
        exporter=console_exporter,
        max_batch_size=1,
        schedule_delay=1.0,
    )
    set_trace_processors([console_processor])
    print("✅ Включено логгирование трассировки в консоль")
    
    # Проверяем существование проекта
    if not os.path.exists(args.project_path):
        print(f"Ошибка: Путь к проекту не существует: {args.project_path}")
        sys.exit(1)
    
    if not os.path.isdir(args.project_path):
        print(f"Ошибка: Указанный путь не является директорией: {args.project_path}")
        sys.exit(1)
    
    # Проверяем API ключ
    # if not os.getenv('OPENROUTER_API_KEY') and not os.getenv('LMSTUDIO_BASE_URL'):
    #     print("Ошибка: Не установлен API ключ для OpenRouter или URL для LM Studio")
    #     print("Установите переменную окружения OPENROUTER_API_KEY или LMSTUDIO_BASE_URL")
    #     sys.exit(1)
    
    # Создаем директорию для вывода
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    try:
        print("=" * 60)
        print("🔍 CodeInspector - Мультиагентная система анализа кода")
        print("=" * 60)
        print(f"📁 Проект: {args.project_path}")
        print(f"⚙️  Конфигурация: {args.config}")
        print(f"📄 Результаты: {args.output}")
        print("=" * 60)
        
        # Изменяем рабочую директорию на директорию скрипта
        os.chdir(current_dir)
        
        # Создаем мастер-агента
        master_agent = MasterAgent(config_path=args.config, output_dir=args.output)
        
        # Запускаем анализ
        result = await master_agent.analyze_project(args.project_path)
        
        # Сохраняем результат
        result_file = output_dir / "analysis_report.md"
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(result)
        
        print("=" * 60)
        print("✅ Анализ завершен успешно!")
        print(f"📄 Отчет сохранен: {result_file}")
        
        # Показываем дополнительные файлы
        json_file = Path("knowledge_base.json")
        if json_file.exists():
            print(f"💾 База знаний: {json_file}")
        
        markdown_file = Path("project_analysis.md")
        if markdown_file.exists():
            print(f"📝 Markdown отчет: {markdown_file}")
        
        print("=" * 60)
        
        if args.verbose:
            print("\nПревью результата:")
            print("-" * 40)
            lines = result.split('\n')
            for line in lines[:20]:  # Показываем первые 20 строк
                print(line)
            if len(lines) > 20:
                print(f"... (ещё {len(lines) - 20} строк)")
        
    except KeyboardInterrupt:
        print("\n❌ Анализ прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при выполнении анализа: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def check_dependencies():
    """Проверка зависимостей."""
    try:
        import yaml
        import tree_sitter
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        return False


if __name__ == "__main__":
    print("🚀 Запуск CodeInspector...")
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Запускаем основную функцию
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
