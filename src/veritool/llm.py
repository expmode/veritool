from __future__ import annotations

import hashlib
import json
import os
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib import error, request

import certifi

from veritool.models import CandidateArtifact, utc_now_iso


class LLMError(RuntimeError):
    """Raised when generation fails."""


class LLMClient(Protocol):
    name: str

    def generate(self, *, tool_id: str, prompt: str, iteration: int) -> CandidateArtifact:
        ...


def extract_python_code(raw_text: str) -> str:
    fence = "```python"
    start = raw_text.find(fence)
    if start != -1:
        start += len(fence)
        end = raw_text.find("```", start)
        if end != -1:
            return raw_text[start:end].strip()
    start = raw_text.find("```")
    if start != -1:
        start += 3
        end = raw_text.find("```", start)
        if end != -1:
            return raw_text[start:end].strip()
    return raw_text.strip()


def build_cache_key(tool_id: str, prompt: str, provider: str, iteration: int) -> str:
    material = json.dumps(
        {"tool_id": tool_id, "prompt": prompt, "provider": provider, "iteration": iteration},
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


@dataclass
class ReplayLLMClient:
    replay_root: Path
    name: str = "replay"

    def generate(self, *, tool_id: str, prompt: str, iteration: int) -> CandidateArtifact:
        raw_response = self._read_replay_response(tool_id, iteration)
        cache_key = build_cache_key(tool_id, prompt, self.name, iteration)
        return CandidateArtifact(
            prompt=prompt,
            code=extract_python_code(raw_response),
            raw_response=raw_response,
            provider=self.name,
            iteration=iteration,
            cache_key=cache_key,
            generated_at=utc_now_iso(),
        )

    def _read_replay_response(self, tool_id: str, iteration: int) -> str:
        replay_dir = self.replay_root / tool_id
        if replay_dir.is_dir():
            numbered = sorted(replay_dir.glob("*.py"))
            if not numbered:
                raise LLMError(f"replay directory for {tool_id} is empty: {replay_dir}")
            file_index = min(iteration, len(numbered)) - 1
            return numbered[file_index].read_text(encoding="utf-8")

        path = self.replay_root / f"{tool_id}.json"
        if not path.exists():
            raise LLMError(f"missing replay fixture for tool {tool_id}: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidates = payload["candidates"]
        index = min(iteration - 1, len(candidates) - 1)
        return str(candidates[index]["response"])


@dataclass
class OpenAICompatibleClient:
    model: str
    api_key_env: str = "OPENAI_API_KEY"
    base_url_env: str = "OPENAI_BASE_URL"
    cache_dir: Path | None = None
    name: str = "openai-compatible"

    def __post_init__(self) -> None:
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, *, tool_id: str, prompt: str, iteration: int) -> CandidateArtifact:
        cache_key = build_cache_key(tool_id, prompt, f"{self.name}:{self.model}", iteration)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise LLMError(f"missing environment variable {self.api_key_env}")
        base_url = os.environ.get(self.base_url_env, "https://api.openai.com/v1")
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You write only Python code for a single function and any helpers it needs."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(
            url=f"{base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=90, context=_ssl_context()) as response:
                raw_json = response.read().decode("utf-8")
        except error.HTTPError as exc:  # pragma: no cover - exercised only against live APIs
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMError(f"HTTP {exc.code} from LLM provider: {detail}") from exc
        except error.URLError as exc:  # pragma: no cover - exercised only against live APIs
            raise LLMError(f"unable to reach LLM provider: {exc.reason}") from exc

        raw_response = _extract_assistant_content(raw_json)
        artifact = CandidateArtifact(
            prompt=prompt,
            code=extract_python_code(raw_response),
            raw_response=raw_response,
            provider=self.name,
            iteration=iteration,
            cache_key=cache_key,
            generated_at=utc_now_iso(),
        )
        self._write_cache(artifact)
        return artifact

    def _cache_path(self, cache_key: str) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / f"{cache_key}.json"

    def _read_cache(self, cache_key: str) -> CandidateArtifact | None:
        path = self._cache_path(cache_key)
        if path is None or not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CandidateArtifact(**payload)

    def _write_cache(self, artifact: CandidateArtifact) -> None:
        path = self._cache_path(artifact.cache_key)
        if path is None:
            return
        path.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def _extract_assistant_content(raw_json: str) -> str:
    payload = json.loads(raw_json)
    choices = payload.get("choices") or []
    if not choices:
        raise LLMError("LLM response did not contain any choices")
    choice = choices[0]
    message = choice.get("message") or {}

    direct_candidates = [
        message.get("content"),
        choice.get("text"),
        message.get("text"),
        message.get("parts"),
    ]
    for candidate in direct_candidates:
        extracted = _coerce_text(candidate)
        if extracted:
            return extracted

    fallback = _coerce_text(choice)
    if fallback:
        return fallback
    preview = raw_json[:500].replace("\n", " ")
    raise LLMError(f"LLM response did not contain assistant content: {preview}")


def _coerce_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [_coerce_text(item) for item in value]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(value, dict):
        preferred_keys = ("text", "content", "parts", "output_text")
        for key in preferred_keys:
            extracted = _coerce_text(value.get(key))
            if extracted:
                return extracted
        nested_parts = []
        for nested_value in value.values():
            extracted = _coerce_text(nested_value)
            if extracted:
                nested_parts.append(extracted)
        return "\n".join(nested_parts).strip()
    return ""


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())
