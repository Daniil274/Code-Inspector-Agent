"""ProcessorAgent выполняет семантическую обработку структуры кода."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.agents import Agent, Runner, RunConfig, function_tool
from src.agents.models.openrouter_provider import OpenRouterProvider
from src.agents.models.lmstudio_provider import LMStudioProvider
from src.agents.model_settings import ModelSettings

from parser.ast_parser import CodeStructure


class ProcessorAgent:
    """Агент, отвечающий за суммаризацию и определение зависимостей."""

    def __init__(self, model_config: Dict) -> None:
        self.model_config = model_config
        self.agent = Agent(
            name="StructureProcessor",
            instructions="""
            Ты анализируешь структурное представление исходного файла и кратко
            описываешь его назначение. Отвечай строго на русском языке.
            """,
            tools=[function_tool(self.process_structure)]  # type: ignore
        )

    @function_tool
    async def process_structure(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Суммаризация и извлечение зависимостей."""
        summary = await self._summarize(structure)
        dependencies = structure.get("dependencies", [])
        return {"summary": summary or "", "dependencies": dependencies}

    async def _summarize(self, structure: Dict[str, Any]) -> Optional[str]:
        """Запрос к LLM для генерации краткого описания файла."""
        context: List[str] = [
            f"Файл: {os.path.basename(structure.get('file_path', ''))}",
            f"Язык: {structure.get('language', '')}",
            f"Строк кода: {structure.get('total_lines', 0)}",
        ]
        classes = structure.get("classes")
        if classes:
            context.append("Классы: " + ", ".join(c.get("name") for c in classes[:3]))
        functions = structure.get("functions")
        if functions:
            context.append("Функции: " + ", ".join(f.get("name") for f in functions[:5]))
        prompt = (
            "Проанализируй структуру файла и опиши его назначение в одном-двух "
            "предложениях.\n" + "\n".join(context)
        )
        provider = self._create_model_provider()
        model_settings = ModelSettings(
            temperature=self.model_config.get("settings", {}).get("temperature", 0.3),
            max_tokens=self.model_config.get("settings", {}).get("max_tokens", 1000),
        )
        result = await Runner.run(
            self.agent,
            prompt,
            run_config=RunConfig(
                model_provider=provider,
                model=self.model_config.get("model", "gpt-3.5-turbo"),
                model_settings=model_settings,
            ),
        )
        return result.final_output.strip() if result.final_output else None

    def _create_model_provider(self):
        provider_type = self.model_config.get("provider", "openrouter")
        if provider_type == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is required")
            return OpenRouterProvider(api_key=api_key)
        elif provider_type == "lmstudio":
            base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
            return LMStudioProvider(base_url=base_url)
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider_type}")
