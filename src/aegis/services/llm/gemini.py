from ...config import settings
from .types import LLMResponse, MockLLM


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
                from google import genai

                self.client = genai.Client(api_key=settings.gemini_api_key)
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
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "max_output_tokens": max_tokens or self.max_tokens,
                    "temperature": temperature or self.temperature,
                    "system_instruction": system_prompt or "",
                },
            )

            response_text = response.text if response.text else ""

            return LLMResponse(
                text=response_text,
                model=self.model,
                usage={
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                },
                reasoning=None,
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


def get_llm(use_mock: bool = False) -> GeminiLLM | MockLLM:
    from ...config import settings

    if use_mock or not settings.gemini_api_key:
        return MockLLM()
    return GeminiLLM()


def get_llm_provider(use_mock: bool = False):
    from ...config import settings

    provider = settings.llm_provider.lower() if settings.llm_provider else "gemini"

    if use_mock:
        return MockLLM()

    if provider == "groq":
        from .groq import GroqLLM

        if not settings.groq_api_key:
            return MockLLM()
        return GroqLLM()

    if not settings.gemini_api_key:
        return MockLLM()
    return GeminiLLM()
