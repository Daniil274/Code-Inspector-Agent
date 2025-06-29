"""Minimal stub of OpenAI Agents SDK for tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional


def function_tool(func: Callable) -> Callable:
    """Decorator stub that returns the function unchanged."""
    return func


class Agent:
    def __init__(self, name: str, instructions: str, tools: Optional[List[Callable]] = None):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []


@dataclass
class RunConfig:
    model_provider: Any = None
    model: Optional[str] = None
    model_settings: Any = None


class Runner:
    @staticmethod
    async def run(agent: Agent, prompt: str, run_config: RunConfig | None = None):
        class Result:
            final_output = ""
        return Result()


# Simple provider stubs
class OpenRouterProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key


class LMStudioProvider:
    def __init__(self, base_url: str):
        self.base_url = base_url


class MultiProvider:
    def __init__(self, providers: List[Any]):
        self.providers = providers


@dataclass
class ModelSettings:
    temperature: float = 0.0
    max_tokens: int = 0
    stream: bool = False
