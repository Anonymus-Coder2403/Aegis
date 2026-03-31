from dataclasses import dataclass
from typing import Any

from ...config import settings


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: dict[str, int]


class GeminiLLM:
    def __init__(
        self,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        self.model = model or settings.llm_model
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.temperature = temperature or settings.llm_temperature
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                import google.genai as genai

                genai.configure(api_key=settings.gemini_api_key)
                self.client = genai
            except ImportError:
                raise ImportError(
                    "google-genai not installed. Install with: pip install google-genai"
                )
        return self.client

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        client = self._get_client()

        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        try:
            model = client.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt,
            )

            generation_config = {
                "max_output_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
            }

            response = model.generate_content(
                prompt,
                generation_config=generation_config,
            )

            return LLMResponse(
                text=response.text,
                model=self.model,
                usage={
                    "prompt_tokens": getattr(response, "prompt_token_count", 0),
                    "completion_tokens": getattr(response, "candidates_token_count", 0),
                },
            )

        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {str(e)}")

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )


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
        )

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        return self.generate(prompt, system_prompt, max_tokens, temperature)


def get_llm(use_mock: bool = False) -> GeminiLLM | MockLLM:
    if use_mock or not settings.gemini_api_key:
        return MockLLM()
    return GeminiLLM()
