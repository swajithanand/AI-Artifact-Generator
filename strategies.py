# strategies.py — provider registry for bring-your-own-key (BYOK) generation.
#
# SECURITY CONTRACT: user API keys arrive per-request, live only in memory for
# the duration of that request, and are NEVER logged or persisted anywhere.

import os
import re
from abc import ABC, abstractmethod
from typing import Optional

from fastapi import HTTPException

from models import ArtifactRequest

# Server-side fallback key (optional). If unset, users must bring their own key.
SERVER_GEMINI_KEY = os.getenv("GEMINI_API_KEY")

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5",
}

MAX_KEY_LENGTH = 256
MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


class ProviderAuthError(Exception):
    """The provider rejected the API key."""


class ProviderRateLimitError(Exception):
    """The provider rate-limited or exhausted the key's quota."""


class AIProviderStrategy(ABC):
    provider_id: str = ""

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or DEFAULT_MODELS[self.provider_id]

    @abstractmethod
    def generate(self, inputs: ArtifactRequest) -> str:
        """Returns the raw text of the generated artifact."""

    @abstractmethod
    def validate(self) -> None:
        """Cheap call that raises ProviderAuthError if the key is bad."""

    def _construct_prompt(self, inputs: ArtifactRequest) -> str:
        prompt = f"""
        You are an expert Agile Product Owner. Your task is to generate a comprehensive {inputs.artifact_type}
        based on the provided details. Output the artifact in a format that is easy to parse.

        [INSTRUCTIONS]
        - Title: Be concise and descriptive.
        - For a User Story: Use the format "As a... I want... so that..." and separate Acceptance Criteria (AC).
        - The response MUST start with a line containing the artifact's Title (e.g., "# Epic Title: ...")

        [USER INPUTS]
        - ARTIFACT TYPE: {inputs.artifact_type}
        - BUSINESS CASE: {inputs.business_use_case}
        - PERSONA: {inputs.persona}
        - TECHNICAL CONTEXT: {inputs.technical_info}
        """
        return prompt


def _classify_status(status_code: Optional[int]) -> Optional[Exception]:
    if status_code in (401, 403):
        return ProviderAuthError()
    if status_code == 429:
        return ProviderRateLimitError()
    return None


class GeminiProvider(AIProviderStrategy):
    provider_id = "gemini"

    def _client(self):
        from google import genai
        return genai.Client(api_key=self.api_key)

    def _translate(self, e: Exception) -> Exception:
        from google.genai.errors import APIError
        if isinstance(e, APIError):
            # Google reports invalid keys as HTTP 400 API_KEY_INVALID, not 401
            message = str(e)
            if "API_KEY_INVALID" in message or "API key not valid" in message:
                return ProviderAuthError()
            mapped = _classify_status(getattr(e, "code", None) or getattr(e, "status_code", None))
            if mapped:
                return mapped
        return e

    def generate(self, inputs: ArtifactRequest) -> str:
        try:
            response = self._client().models.generate_content(
                model=self.model,
                contents=self._construct_prompt(inputs),
            )
            return response.text
        except Exception as e:
            raise self._translate(e) from None

    def validate(self) -> None:
        try:
            self._client().models.get(model=self.model)
        except Exception as e:
            raise self._translate(e) from None


class OpenAIProvider(AIProviderStrategy):
    provider_id = "openai"

    def _client(self):
        import openai
        return openai.OpenAI(api_key=self.api_key)

    def _translate(self, e: Exception) -> Exception:
        import openai
        if isinstance(e, openai.AuthenticationError) or isinstance(e, openai.PermissionDeniedError):
            return ProviderAuthError()
        if isinstance(e, openai.RateLimitError):
            return ProviderRateLimitError()
        return e

    def generate(self, inputs: ArtifactRequest) -> str:
        try:
            response = self._client().chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": self._construct_prompt(inputs)}],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise self._translate(e) from None

    def validate(self) -> None:
        try:
            self._client().models.retrieve(self.model)
        except Exception as e:
            raise self._translate(e) from None


class AnthropicProvider(AIProviderStrategy):
    provider_id = "anthropic"

    def _client(self):
        import anthropic
        return anthropic.Anthropic(api_key=self.api_key)

    def _translate(self, e: Exception) -> Exception:
        import anthropic
        if isinstance(e, anthropic.AuthenticationError) or isinstance(e, anthropic.PermissionDeniedError):
            return ProviderAuthError()
        if isinstance(e, anthropic.RateLimitError):
            return ProviderRateLimitError()
        return e

    def generate(self, inputs: ArtifactRequest) -> str:
        try:
            message = self._client().messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": self._construct_prompt(inputs)}],
            )
            return "".join(block.text for block in message.content if block.type == "text")
        except Exception as e:
            raise self._translate(e) from None

    def validate(self) -> None:
        try:
            self._client().models.retrieve(self.model)
        except Exception as e:
            raise self._translate(e) from None


PROVIDERS = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def build_provider(
    provider_id: Optional[str],
    model: Optional[str],
    api_key: Optional[str],
) -> AIProviderStrategy:
    """
    Builds the provider for one request. User-supplied key wins; otherwise the
    optional server-side Gemini key is used; otherwise the request is rejected.
    """
    if api_key:
        api_key = api_key.strip()
        if not api_key or len(api_key) > MAX_KEY_LENGTH:
            raise HTTPException(status_code=400, detail="The API key looks malformed.")
        pid = (provider_id or "gemini").strip().lower()
        provider_cls = PROVIDERS.get(pid)
        if not provider_cls:
            raise HTTPException(status_code=400, detail=f"Unknown provider '{pid}'.")
        if model:
            model = model.strip()
            if not MODEL_NAME_PATTERN.match(model):
                raise HTTPException(status_code=400, detail="The model name looks malformed.")
        return provider_cls(api_key=api_key, model=model or None)

    if SERVER_GEMINI_KEY:
        return GeminiProvider(api_key=SERVER_GEMINI_KEY)

    raise HTTPException(
        status_code=401,
        detail="No API key configured. Open Settings (gear icon) and add your LLM API key.",
    )
