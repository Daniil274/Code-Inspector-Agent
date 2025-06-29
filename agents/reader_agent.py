"""
Агент для чтения и парсинга файлов исходного кода.
Предоставляет простой интерфейс вокруг ASTParser.
"""

from __future__ import annotations

from typing import Optional

from src.agents import function_tool
from parser.ast_parser import ASTParser, CodeStructure


class ReaderAgent:
    """Обертка над :class:`ASTParser` для получения структуры кода."""

    def __init__(self) -> None:
        self.ast_parser = ASTParser()

    @function_tool
    def read_file(self, file_path: str) -> Optional[CodeStructure]:
        """Прочитать файл и вернуть его структуру."""
        return self.ast_parser.parse_file(file_path)
