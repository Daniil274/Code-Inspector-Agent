#!/usr/bin/env python3
"""
Основной модуль тестового проекта для CodeInspector
"""
from .utils import calculate_fibonacci, validate_email, process_data


def main():
    """Основная функция приложения"""
    print("Тестовое приложение CodeInspector")
    
    # Тестирование функций
    result = calculate_fibonacci(10)
    print(f"Fibonacci(10) = {result}")
    
    is_valid = validate_email("test@example.com")
    print(f"Email validation: {is_valid}")
    
    data = [1, 2, 3, 4, 5]
    processed = process_data(data)
    print(f"Processed data: {processed}")


if __name__ == "__main__":
    main() 