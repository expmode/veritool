from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from veritool.llm import LLMClient, OpenAICompatibleClient, ReplayLLMClient
from veritool.models import Counterexample, RunArtifact, ToolRunSummary, VerificationTrace, utc_now_iso
from veritool.tools import ToolSpec, get_tool_spec, list_tool_specs


SAFE_BUILTINS = MappingProxyType(
    {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "Exception": Exception,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "range": range,
        "reversed": reversed,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "ValueError": ValueError,
    }
)


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    replay_root: Path | None = None
    model: str = "gpt-4.1-mini"
    cache_dir: Path | None = None


def build_llm_client(config: ProviderConfig) -> LLMClient:
    if config.provider == "replay":
        if config.replay_root is None:
            raise ValueError("replay_root is required for replay provider")
        return ReplayLLMClient(replay_root=config.replay_root)
    if config.provider == "openai-compatible":
        return OpenAICompatibleClient(model=config.model, cache_dir=config.cache_dir)
    raise ValueError(f"unsupported provider: {config.provider}")


def run_tool(
    tool_id: str,
    *,
    provider_config: ProviderConfig,
    max_iterations: int = 4,
) -> ToolRunSummary:
    tool = get_tool_spec(tool_id)
    client = build_llm_client(provider_config)
    traces: list[VerificationTrace] = []
    accepted_code: str | None = None
    accepted_metrics: dict[str, Any] = {}
    evidence_level = "failed"

    feedback: list[Counterexample] = []
    for iteration in range(1, max_iterations + 1):
        prompt = _build_prompt(tool, feedback)
        artifact = client.generate(tool_id=tool.tool_id, prompt=prompt, iteration=iteration)
        verification = tool.verify_candidate(artifact.code)
        traces.append(
            VerificationTrace(
                iteration=iteration,
                passed=verification.passed,
                summary=verification.summary,
                evidence_level=verification.evidence_level,
                counterexample=verification.counterexample.to_dict() if verification.counterexample else None,
                metrics=dict(verification.metrics),
            )
        )
        if verification.passed:
            accepted_code = artifact.code
            accepted_metrics = dict(verification.metrics)
            evidence_level = verification.evidence_level
            break
        if verification.counterexample:
            feedback.append(verification.counterexample)
            evidence_level = verification.evidence_level

    passed = accepted_code is not None
    return ToolRunSummary(
        tool_id=tool.tool_id,
        tool_name=tool.name,
        passed=passed,
        iterations=len(traces),
        provider=client.name,
        evidence_level=evidence_level,
        accepted_code=accepted_code,
        traces=tuple(traces),
        accepted_metrics=accepted_metrics,
        replay_source=_resolve_replay_source(provider_config, tool_id),
    )


def run_tool_suite(
    *,
    provider_config: ProviderConfig,
    tool_ids: list[str] | None = None,
    max_iterations: int = 4,
) -> RunArtifact:
    started_at = utc_now_iso()
    chosen = tool_ids or [tool.tool_id for tool in list_tool_specs()]
    tools = tuple(run_tool(tool_id, provider_config=provider_config, max_iterations=max_iterations) for tool_id in chosen)
    passed_tools = sum(1 for tool in tools if tool.passed)
    total_iterations = sum(tool.iterations for tool in tools)
    aggregate_metrics = {
        "tool_count": len(tools),
        "passed_tools": passed_tools,
        "failed_tools": len(tools) - passed_tools,
        "success_rate": round(passed_tools / len(tools), 3) if tools else 0.0,
        "total_iterations": total_iterations,
        "average_iterations": round(total_iterations / len(tools), 2) if tools else 0.0,
    }
    return RunArtifact(
        suite_name="VeriTool Full Suite",
        provider=provider_config.provider,
        started_at=started_at,
        finished_at=utc_now_iso(),
        tools=tools,
        aggregate_metrics=aggregate_metrics,
    )


def load_candidate_function(code: str, function_name: str):
    tree = ast.parse(code)
    globals_dict: dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    locals_dict: dict[str, Any] = {}
    exec(compile(tree, filename="<candidate>", mode="exec"), globals_dict, locals_dict)
    function = locals_dict.get(function_name) or globals_dict.get(function_name)
    if not callable(function):
        raise ValueError(f"candidate did not define callable {function_name}")
    return function


def _build_prompt(tool: ToolSpec, feedback: list[Counterexample]) -> str:
    lines = [
        f"Write Python code for the function `{tool.function_name}`.",
        f"Tool name: {tool.name}",
        f"Signature: {tool.signature}",
        f"Task: {tool.task}",
        f"Primary invariant: {tool.primary_invariant}",
        "Constraints:",
    ]
    lines.extend(f"- {constraint}" for constraint in tool.constraints)
    if feedback:
        lines.append("Counterexamples from previous failed attempts:")
        for item in feedback:
            lines.append(f"- {item.title}: {item.description}")
            lines.append(f"  Payload: {json.dumps(item.payload, sort_keys=True)}")
    lines.append("Return only valid Python code with the requested function and any helper functions it needs.")
    return "\n".join(lines)


def _resolve_replay_source(provider_config: ProviderConfig, tool_id: str) -> str | None:
    if provider_config.provider != "replay" or provider_config.replay_root is None:
        return None
    replay_dir = provider_config.replay_root / tool_id
    if replay_dir.exists():
        return str(replay_dir)
    return str(provider_config.replay_root / f"{tool_id}.json")
