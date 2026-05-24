from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


JsonMap = dict[str, Any]


@dataclass(frozen=True)
class Counterexample:
    title: str
    description: str
    payload: JsonMap

    def to_dict(self) -> JsonMap:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    summary: str
    evidence_level: str
    counterexample: Counterexample | None = None
    metrics: JsonMap = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def to_dict(self) -> JsonMap:
        data = asdict(self)
        if self.counterexample is None:
            data["counterexample"] = None
        return data


@dataclass(frozen=True)
class CandidateArtifact:
    prompt: str
    code: str
    raw_response: str
    provider: str
    iteration: int
    cache_key: str
    generated_at: str

    def to_dict(self) -> JsonMap:
        return asdict(self)


@dataclass(frozen=True)
class VerificationTrace:
    iteration: int
    passed: bool
    summary: str
    evidence_level: str
    counterexample: JsonMap | None
    metrics: JsonMap

    def to_dict(self) -> JsonMap:
        return asdict(self)


@dataclass(frozen=True)
class ToolRunSummary:
    tool_id: str
    tool_name: str
    passed: bool
    iterations: int
    provider: str
    evidence_level: str
    accepted_code: str | None
    traces: tuple[VerificationTrace, ...]
    accepted_metrics: JsonMap = field(default_factory=dict)
    replay_source: str | None = None

    def to_dict(self) -> JsonMap:
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "passed": self.passed,
            "iterations": self.iterations,
            "provider": self.provider,
            "evidence_level": self.evidence_level,
            "accepted_code": self.accepted_code,
            "accepted_metrics": self.accepted_metrics,
            "traces": [trace.to_dict() for trace in self.traces],
            "replay_source": self.replay_source,
        }


@dataclass(frozen=True)
class RunArtifact:
    suite_name: str
    provider: str
    started_at: str
    finished_at: str
    tools: tuple[ToolRunSummary, ...]
    aggregate_metrics: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "suite_name": self.suite_name,
            "provider": self.provider,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "tools": [tool.to_dict() for tool in self.tools],
            "aggregate_metrics": self.aggregate_metrics,
        }


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
