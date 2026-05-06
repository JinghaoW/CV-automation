"""Centralized LLM abstraction for multiple providers.

Supported providers:
- OpenAI
- DeepSeek
- Gemini
- OpenRouter
- Ollama

The public surface intentionally mirrors a small subset of the OpenAI-style
chat API for compatibility, while business logic can use ``generate_text`` and
``generate_json`` for structured outputs.
"""

from __future__ import annotations

import json
import importlib
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - fallback for OpenAI-compatible behavior
    from openai import OpenAI as _OpenAI_SDK
except Exception:  # pragma: no cover
    _OpenAI_SDK = None

try:  # pragma: no cover - config may be unavailable in some contexts
    import config as _config
except Exception:  # pragma: no cover
    _config = None

_LOGGER = logging.getLogger(__name__)

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "gemini": "gemini-2.0-flash",
    "openrouter": "openrouter/openai/gpt-4o-mini",
    "ollama": "ollama/llama3.1",
}

_PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": "OLLAMA_API_KEY",
}

_PROVIDER_BASE_URL_ENV = {
    "openrouter": "OPENROUTER_BASE_URL",
    "ollama": "OLLAMA_BASE_URL",
}

_PROVIDER_DEFAULT_BASE_URL = {
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
}

_PROVIDER_REQUIRES_KEY = {"openai", "deepseek", "gemini", "openrouter"}

_LITELLM_COMPLETION: Any = None


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    api_key: str | None
    base_url: str | None
    timeout: float
    max_retries: int
    temperature: float


@dataclass(frozen=True)
class _Message:
    content: str | None


@dataclass(frozen=True)
class _Choice:
    message: _Message


@dataclass(frozen=True)
class _Response:
    choices: list[_Choice]


class _ChatCompletions:
    def __init__(self, client: "LLMClient") -> None:
        self._client = client

    def create(
        self,
        *,
        model: str | None = None,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        timeout: float | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> _Response:
        content = self._client._generate_content(
            model=model,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
            response_format=response_format,
            **kwargs,
        )
        return _Response(choices=[_Choice(message=_Message(content=content))])


class _ChatNamespace:
    def __init__(self, client: "LLMClient") -> None:
        self.completions = _ChatCompletions(client)


class LLMClient:
    """Provider-agnostic chat client with retries and structured output helpers."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        provider: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        temperature: float | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = self._resolve_settings(
            api_key=api_key,
            provider=provider,
            model=model,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            temperature=temperature,
        )
        self.logger = logger or _LOGGER
        self.chat = _ChatNamespace(self)

    @classmethod
    def from_config(cls) -> "LLMClient":
        return cls()

    def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        **kwargs: Any,
    ) -> str:
        messages = self._build_messages(prompt, system_prompt)
        response = self.chat.completions.create(
            messages=messages,
            temperature=temperature,
            timeout=timeout,
            **kwargs,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM returned no content (content was None)")
        return content

    def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        content = self.generate_text(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
            response_format={"type": "json_object"},
            **kwargs,
        )
        return self._parse_json(content)

    def _generate_content(
        self,
        *,
        model: str | None = None,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        timeout: float | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        settings = self.settings
        model_name = str(model or settings.model)
        request_temperature = float(settings.temperature if temperature is None else temperature)
        request_timeout = float(settings.timeout if timeout is None else timeout)
        max_retries = int(settings.max_retries)

        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            started = time.perf_counter()
            try:
                self.logger.debug(
                    "LLM request start",
                    extra={
                        "provider": settings.provider,
                        "model": model_name,
                        "attempt": attempt,
                        "timeout": request_timeout,
                    },
                )
                provider_fn: Any = self._invoke_provider
                content = provider_fn(
                    model_name=model_name,
                    messages=messages,
                    temperature=request_temperature,
                    timeout=request_timeout,
                    response_format=response_format,
                    **kwargs,
                )
                elapsed_ms = float(round((time.perf_counter() - started) * 1000, 2))
                self.logger.info(
                    "LLM request succeeded",
                    extra={
                        "provider": settings.provider,
                        "model": model_name,
                        "attempt": attempt,
                        "elapsed_ms": elapsed_ms,
                    },
                )
                return content
            except Exception as exc:  # noqa: BLE001 - provider errors are heterogeneous
                last_exc = exc
                elapsed_ms = float(round((time.perf_counter() - started) * 1000, 2))
                self.logger.warning(
                    "LLM request failed",
                    extra={
                        "provider": settings.provider,
                        "model": model_name,
                        "attempt": attempt,
                        "elapsed_ms": elapsed_ms,
                        "error": str(exc),
                    },
                )
                if attempt >= max_retries:
                    break
                time.sleep(self._backoff_seconds(attempt))

        raise RuntimeError(
            f"LLM request failed after {max_retries} attempts using provider={settings.provider!r}, model={model_name!r}"
        ) from last_exc

    def _invoke_provider(
        self,
        *,
        model_name: str,
        messages: list[dict[str, Any]],
        temperature: float,
        timeout: float,
        response_format: dict[str, Any] | None,
        **kwargs: Any,
    ) -> str:
        settings = self.settings

        litellm_completion = self._get_litellm_completion()
        if callable(litellm_completion):
            provider_kwargs: dict[str, Any] = {
                "model": model_name,
                "messages": cast(Any, messages),
                "temperature": temperature,
                "timeout": timeout,
                "api_key": settings.api_key,
                "api_base": settings.base_url,
                "response_format": response_format,
            }
            provider_kwargs.update(kwargs)
            response = cast(Any, litellm_completion)(**provider_kwargs)
            return self._extract_content(response)

        if settings.provider == "openai" and _OpenAI_SDK is not None:
            sdk_kwargs: dict[str, Any] = {
                "api_key": settings.api_key,
            }
            if settings.base_url:
                sdk_kwargs["base_url"] = settings.base_url
            openai_client: Any = _OpenAI_SDK(**sdk_kwargs)
            provider_kwargs: dict[str, Any] = {
                "model": model_name,
                "messages": cast(Any, messages),
                "temperature": temperature,
                "timeout": timeout,
                "response_format": response_format,
            }
            provider_kwargs.update(kwargs)
            response = cast(Any, openai_client.chat.completions.create)(**provider_kwargs)
            return self._extract_content(response)

        raise RuntimeError(
            "No supported LLM backend is available. Install 'litellm' to enable provider abstraction."
        )

    @staticmethod
    def _get_litellm_completion():
        global _LITELLM_COMPLETION
        if _LITELLM_COMPLETION is not None:
            return _LITELLM_COMPLETION

        try:
            module = importlib.import_module("litellm")
            _LITELLM_COMPLETION = getattr(module, "completion", None)
        except Exception:  # pragma: no cover - optional dependency
            _LITELLM_COMPLETION = None
        return _LITELLM_COMPLETION

    @staticmethod
    def _extract_content(response: Any) -> str:
        try:
            content = response.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Unexpected LLM response shape") from exc
        if content is None:
            raise ValueError("LLM returned no content (content was None)")
        return str(content)

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        cleaned = LLMClient._strip_code_fences(content).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {cleaned}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("LLM JSON output must be an object")
        return parsed

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        stripped = content.strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, flags=re.DOTALL | re.IGNORECASE)
        if fence:
            return fence.group(1)
        return stripped

    @staticmethod
    def _build_messages(prompt: str, system_prompt: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        return min(2.0**attempt, 10.0)

    @staticmethod
    def _resolve_settings(
        *,
        api_key: str | None,
        provider: str | None,
        model: str | None,
        base_url: str | None,
        timeout: float | None,
        max_retries: int | None,
        temperature: float | None,
    ) -> LLMSettings:
        provider_name = (
            provider
            or os.environ.get("LLM_PROVIDER")
            or getattr(_config, "LLM_PROVIDER", None)
            or "openai"
        ).strip().lower()

        model_name = (
            model
            or os.environ.get("LLM_MODEL")
            or getattr(_config, "LLM_MODEL", None)
            or _DEFAULT_MODELS.get(provider_name, "gpt-4o-mini")
        )

        api_key_value = LLMClient._resolve_api_key(provider_name, api_key)
        base_url_value = (
            base_url
            or os.environ.get("LLM_BASE_URL")
            or getattr(_config, "LLM_BASE_URL", None)
            or os.environ.get(_PROVIDER_BASE_URL_ENV.get(provider_name, ""), "")
            or getattr(_config, _PROVIDER_BASE_URL_ENV.get(provider_name, ""), "")
            or _PROVIDER_DEFAULT_BASE_URL.get(provider_name, "")
            or None
        )

        timeout_value = float(
            timeout
            if timeout is not None
            else os.environ.get("LLM_TIMEOUT")
            or getattr(_config, "LLM_TIMEOUT", 60)
        )
        max_retries_value = int(
            max_retries
            if max_retries is not None
            else os.environ.get("LLM_MAX_RETRIES")
            or getattr(_config, "LLM_MAX_RETRIES", 3)
        )
        temperature_value = float(
            temperature
            if temperature is not None
            else os.environ.get("LLM_TEMPERATURE")
            or getattr(_config, "LLM_TEMPERATURE", 0.2)
        )

        return LLMSettings(
            provider=provider_name,
            model=model_name,
            api_key=api_key_value,
            base_url=base_url_value,
            timeout=timeout_value,
            max_retries=max_retries_value,
            temperature=temperature_value,
        )

    @staticmethod
    def _resolve_api_key(provider: str, api_key: str | None) -> str | None:
        if api_key:
            return api_key

        generic = os.environ.get("LLM_API_KEY") or getattr(_config, "LLM_API_KEY", "")
        if generic:
            return generic

        env_name = _PROVIDER_KEY_ENV.get(provider)
        if env_name:
            env_value = os.environ.get(env_name) or getattr(_config, env_name, "")
            if env_value:
                return env_value

        # Backwards compatibility for existing OpenAI-only configuration.
        if provider == "openai":
            legacy = os.environ.get("OPENAI_API_KEY") or getattr(_config, "OPENAI_API_KEY", "")
            if legacy:
                return legacy

        return None

    def require_configured(self) -> None:
        """Validate that the client has the credentials needed for the provider."""
        if self.settings.provider in _PROVIDER_REQUIRES_KEY and not self.settings.api_key:
            env_name = _PROVIDER_KEY_ENV.get(self.settings.provider, "LLM_API_KEY")
            raise EnvironmentError(
                f"{env_name} is not set. Add it to config.py or export it as an environment variable."
            )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"LLMClient(provider={self.settings.provider!r}, model={self.settings.model!r}, "
            f"timeout={self.settings.timeout!r}, max_retries={self.settings.max_retries!r})"
        )


# Backwards-compatible alias so call sites can keep using the familiar name
# while the implementation remains provider-agnostic.
OpenAI = LLMClient


def validate_llm_configuration(
    *,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
    temperature: float | None = None,
) -> LLMSettings:
    """Resolve settings and raise a helpful error if a required key is missing."""
    settings = LLMClient._resolve_settings(
        api_key=api_key,
        provider=provider,
        model=model,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        temperature=temperature,
    )
    if settings.provider in _PROVIDER_REQUIRES_KEY and not settings.api_key:
        env_name = _PROVIDER_KEY_ENV.get(settings.provider, "LLM_API_KEY")
        raise EnvironmentError(
            f"{env_name} is not set. Add it to config.py or export it as an environment variable."
        )
    return settings


__all__ = ["LLMClient", "OpenAI", "LLMSettings", "validate_llm_configuration"]

