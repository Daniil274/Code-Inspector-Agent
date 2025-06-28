"""
Тесты для основного модуля тестового проекта
"""
import pytest
from .main import main
from .utils import calculate_fibonacci, validate_email, process_data


def test_calculate_fibonacci():
    """Тест функции вычисления чисел Фибоначчи"""
    assert calculate_fibonacci(0) == 0
    assert calculate_fibonacci(1) == 1
    assert calculate_fibonacci(5) == 5
    assert calculate_fibonacci(10) == 55


def test_validate_email():
    """Тест функции валидации email"""
    assert validate_email("test@example.com") == True
    assert validate_email("invalid-email") == False
    assert validate_email("user@domain.org") == True
    assert validate_email("") == False


def test_process_data():
    """Тест функции обработки данных"""
    assert process_data([1, 2, 3, 4, 5]) == [2, 4, 6, 8, 10]
    assert process_data([-1, 0, 1, 2]) == [2, 4]
    assert process_data([]) == []


def test_main_function():
    """Тест основной функции"""
    # Проверяем, что функция выполняется без ошибок
    try:
        main()
        assert True
    except Exception as e:
        pytest.fail(f"main() вызвала исключение: {e}") 