from __future__ import annotations

import json
import re
from pathlib import Path

from veritool.tools import list_tool_specs


FUNCTION_RE = re.compile(r"Write Python code for the function `([^`]+)`\.")


def build_trajectory_bundle(root: Path, *, run_path: Path, cache_dir: Path, model_slug: str) -> dict:
    run_payload = json.loads(run_path.read_text(encoding="utf-8"))
    cache_entries = [_load_cache(path) for path in sorted(cache_dir.glob("*.json"))]

    specs_by_function = {spec.function_name: spec for spec in list_tool_specs()}
    caches_by_function: dict[str, list[dict]] = {}
    for entry in cache_entries:
        match = FUNCTION_RE.search(entry["prompt"])
        if not match:
            continue
        function_name = match.group(1)
        caches_by_function.setdefault(function_name, []).append(entry)

    tools = []
    for tool in run_payload["tools"]:
        traces = tool["traces"]
        function_name = _function_name_for_tool(tool["tool_id"], specs_by_function)
        cache_items = sorted(caches_by_function.get(function_name, []), key=lambda item: item["iteration"])
        iterations = []
        for trace in traces:
            cache_item = next((item for item in cache_items if item["iteration"] == trace["iteration"]), None)
            iterations.append(
                {
                    "iteration": trace["iteration"],
                    "passed": trace["passed"],
                    "summary": trace["summary"],
                    "evidence_level": trace["evidence_level"],
                    "counterexample": trace["counterexample"],
                    "prompt": cache_item["prompt"] if cache_item else None,
                    "raw_response": cache_item["raw_response"] if cache_item else None,
                    "code": cache_item["code"] if cache_item else None,
                }
            )
        tools.append(
            {
                "tool_id": tool["tool_id"],
                "tool_name": tool["tool_name"],
                "function_name": function_name,
                "passed": tool["passed"],
                "iterations": iterations,
                "accepted_code": tool["accepted_code"],
                "accepted_metrics": tool["accepted_metrics"],
            }
        )

    return {
        "model": model_slug,
        "provider": run_payload["provider"],
        "aggregate_metrics": run_payload["aggregate_metrics"],
        "tool_count": len(tools),
        "tools": tools,
    }


def _load_cache(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _function_name_for_tool(tool_id: str, specs_by_function: dict[str, object]) -> str:
    for function_name, spec in specs_by_function.items():
        if spec.tool_id == tool_id:
            return function_name
    raise KeyError(f"unable to resolve function name for tool {tool_id}")
