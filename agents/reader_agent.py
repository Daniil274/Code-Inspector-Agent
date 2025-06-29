from __future__ import annotations

import asyncio


class ReaderAgent:
    """Agent that asynchronously reads file contents."""

    async def read(self, file_path: str) -> str:
        """Read file content asynchronously."""
        return await asyncio.to_thread(self._read_sync, file_path)

    def _read_sync(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
