from dataclasses import dataclass

@dataclass
class ModelSettings:
    temperature: float = 0.0
    max_tokens: int = 0
    stream: bool = False
