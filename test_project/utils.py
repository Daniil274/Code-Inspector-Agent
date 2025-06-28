"""
Утилиты для тестового проекта CodeInspector
"""
from typing import List, Union
import re


def calculate_fibonacci(n: int) -> int:
    """Вычисляет n-ое число Фибоначчи"""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


def validate_email(email: str) -> bool:
    """Проверяет корректность email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def process_data(data: List[Union[int, float]]) -> List[Union[int, float]]:
    """Обрабатывает список данных"""
    return [item * 2 for item in data if item > 0] 