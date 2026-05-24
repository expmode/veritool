from __future__ import annotations

from pathlib import Path

from veritool.runtime import ProviderConfig, run_tool, run_tool_suite
from veritool.tools import get_tool_spec, list_tool_specs


ROOT = Path(__file__).resolve().parents[1]
REPLAYS = ROOT / "replays"


def test_replay_suite_passes_all_tools() -> None:
    artifact = run_tool_suite(provider_config=ProviderConfig(provider="replay", replay_root=REPLAYS), max_iterations=4)
    assert artifact.aggregate_metrics["passed_tools"] == 6
    assert artifact.aggregate_metrics["failed_tools"] == 0
    assert artifact.aggregate_metrics["tool_count"] == 6
    assert all(tool.passed for tool in artifact.tools)
    assert all(tool.iterations == 2 for tool in artifact.tools)


def test_each_tool_has_a_passing_replay() -> None:
    for tool in list_tool_specs():
        summary = run_tool(tool.tool_id, provider_config=ProviderConfig(provider="replay", replay_root=REPLAYS), max_iterations=4)
        assert summary.passed, tool.tool_id
        assert summary.accepted_code
        assert summary.traces[0].passed is False
        assert summary.traces[-1].passed is True


def test_forbidden_imports_are_rejected() -> None:
    spec = get_tool_spec("safe_api_caller")
    result = spec.verify_candidate(
        "import os\n"
        "def safe_api_call(url, method, allowlist, responses):\n"
        "    return 'bad'\n"
    )
    assert result.passed is False
    assert result.counterexample is not None
    assert result.counterexample.title == "forbidden_import"
