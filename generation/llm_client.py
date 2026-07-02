"""
llm_client.py — LLM abstraction over Ollama and the Anthropic API.

Exposes a small, provider-agnostic interface:
  - chat(system, messages)        → full response text
  - stream_chat(system, messages) → generator yielding text chunks

Provider and model are read from the environment (see .env):
  LLM_PROVIDER     "ollama" | "anthropic"
  OLLAMA_BASE_URL  e.g. http://localhost:11434
  OLLAMA_MODEL     e.g. qwen2.5:7b
  OLLAMA_KEEP_ALIVE  how long Ollama keeps the model resident (e.g. 30m); avoids cold reloads
  OLLAMA_NUM_PREDICT max output tokens per generation (caps runaway responses)
  OLLAMA_NUM_CTX     context window in tokens
  ANTHROPIC_API_KEY
  ANTHROPIC_MODEL  e.g. claude-sonnet-4-6
"""
from __future__ import annotations

import os
from collections.abc import Iterator

DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"

# Ollama runtime tuning (all overridable via env). keep_alive keeps the model
# resident between requests so it isn't reloaded from disk on every call; the
# num_* caps bound generation length and context to keep latency/RAM in check.
DEFAULT_OLLAMA_KEEP_ALIVE = "30m"
DEFAULT_OLLAMA_NUM_PREDICT = 512
DEFAULT_OLLAMA_NUM_CTX = 4096


class LLMClient:
    """Unified client switching between Ollama (local) and Anthropic (API)."""

    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)).lower()
        if self.provider == "ollama":
            self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
            self.base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
            self._init_ollama()
        elif self.provider == "anthropic":
            self.model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
            self._init_anthropic()
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{self.provider}'. Use 'ollama' or 'anthropic'."
            )

    # ── Initialization ──────────────────────────────────────────────────
    def _init_ollama(self) -> None:
        import ollama

        self._client = ollama.Client(host=self.base_url)
        self._keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", DEFAULT_OLLAMA_KEEP_ALIVE)
        self._options = {
            "num_predict": int(
                os.getenv("OLLAMA_NUM_PREDICT", DEFAULT_OLLAMA_NUM_PREDICT)
            ),
            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", DEFAULT_OLLAMA_NUM_CTX)),
        }

    def _init_anthropic(self) -> None:
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set but LLM_PROVIDER=anthropic."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    # ── Public API ──────────────────────────────────────────────────────
    def chat(self, system: str, messages: list[dict]) -> str:
        """Return the full assistant response as a single string."""
        return "".join(self.stream_chat(system, messages))

    def stream_chat(self, system: str, messages: list[dict]) -> Iterator[str]:
        """Yield response text chunks as they are generated."""
        if self.provider == "ollama":
            yield from self._stream_ollama(system, messages)
        else:
            yield from self._stream_anthropic(system, messages)

    # ── Ollama backend ──────────────────────────────────────────────────
    def _stream_ollama(self, system: str, messages: list[dict]) -> Iterator[str]:
        payload = [{"role": "system", "content": system}, *messages]
        stream = self._client.chat(
            model=self.model,
            messages=payload,
            stream=True,
            keep_alive=self._keep_alive,
            options=self._options,
        )
        for part in stream:
            chunk = part.get("message", {}).get("content", "")
            if chunk:
                yield chunk

    # ── Anthropic backend ───────────────────────────────────────────────
    def _stream_anthropic(self, system: str, messages: list[dict]) -> Iterator[str]:
        with self._client.messages.stream(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text

    # ── Diagnostics ─────────────────────────────────────────────────────
    def health(self) -> bool:
        """Return True if the backend is reachable and the model is available."""
        try:
            if self.provider == "ollama":
                models = self._client.list().get("models", [])
                names = {m.get("model") or m.get("name") for m in models}
                # Accept an exact match or a tag-prefixed match.
                return any(
                    self.model == n or (n and n.startswith(self.model))
                    for n in names
                )
            # Anthropic: a constructed client with a key is considered ready.
            return True
        except Exception:
            return False


if __name__ == "__main__":
    client = LLMClient()
    print(f"Provider: {client.provider} | Model: {client.model}")
    print(f"Healthy: {client.health()}")
    for chunk in client.stream_chat(
        "You are concise.", [{"role": "user", "content": "Say hello in one word."}]
    ):
        print(chunk, end="", flush=True)
    print()
