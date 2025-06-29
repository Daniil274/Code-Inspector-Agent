"""Minimal stub implementations of the OpenAI Agents SDK used for tests."""
from dataclasses import dataclass
from typing import Any, Callable, List


def function_tool(func: Callable) -> Callable:
    """Mark a function as a tool."""
    func.is_tool = True
    return func


@dataclass
class RunConfig:
    model_provider: Any = None
    model: str | None = None
    model_settings: Any = None


@dataclass
class ModelSettings:
    temperature: float = 0.3
    max_tokens: int = 1000


class Agent:
    """Simple agent placeholder."""

    def __init__(self, name: str, instructions: str, tools: List[Callable] | None = None):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []


class Runner:
    """Minimal runner that returns stubbed output."""

    @staticmethod
    async def run(agent: Agent, prompt: str, run_config: RunConfig | None = None):
        class Result:
            def __init__(self, out):
                self.final_output = out

        return Result(f"stub:{prompt[:20]}")
