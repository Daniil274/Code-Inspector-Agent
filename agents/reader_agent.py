"""ReaderAgent для получения структурного представления исходного кода."""
from __future__ import annotations

from typing import Optional

from parser.ast_parser import ASTParser, CodeStructure


class ReaderAgent:
    """Агент для чтения исходного кода и извлечения структуры."""

    def __init__(self) -> None:
        self.ast_parser = ASTParser()

    async def read_file(self, file_path: str) -> Optional[CodeStructure]:
        """Возвращает структуру файла."""
        return self.ast_parser.parse_file(file_path)
