from ...config import settings
from .types import LLMResponse, MockLLM


class GroqLLM:
    def __init__(
        self,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        self.model = model or settings.groq_model or settings.llm_model
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.temperature = temperature or settings.llm_temperature
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                from groq import AsyncGroq

                self.client = AsyncGroq(api_key=settings.groq_api_key)
            except ImportError:
                raise ImportError("groq not installed. Install with: pip install groq")
        return self.client

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        client = self._get_client()

        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
            )

            return LLMResponse(
                text=response.choices[0].message.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens
                    if response.usage
                    else 0,
                    "completion_tokens": response.usage.completion_tokens
                    if response.usage
                    else 0,
                },
                reasoning=getattr(
                    response.choices[0].message, "reasoning_content", None
                ),
            )

        except Exception as e:
            raise RuntimeError(f"Groq generation failed: {str(e)}")

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            raise RuntimeError(
                "Cannot use synchronous generate() in async context. Use generate_async() instead."
            )
        except RuntimeError:
            pass

        return asyncio.run(
            self.generate_async(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        )


def get_llm(use_mock: bool = False) -> GroqLLM | MockLLM:
    if use_mock or not settings.groq_api_key:
        return MockLLM()
    return GroqLLM()
