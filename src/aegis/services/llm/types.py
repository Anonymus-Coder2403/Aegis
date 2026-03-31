from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: dict[str, int]
    reasoning: str | None = None


class MockLLM:
    def __init__(self, model: str = "mock"):
        self.model = model

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        return LLMResponse(
            text=f"[Mock Response] This is a placeholder response for prompt: {prompt[:100]}...",
            model=self.model,
            usage={"prompt_tokens": 100, "completion_tokens": 50},
            reasoning=None,
        )

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        return self.generate(prompt, system_prompt, max_tokens, temperature)
