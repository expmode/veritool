from __future__ import annotations

import argparse
from pathlib import Path

from veritool.reporting import write_json_report, write_markdown_report
from veritool.runtime import ProviderConfig, run_tool, run_tool_suite
from veritool.tools import list_tool_specs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the VeriTool synthesis and verification pipeline.")
    parser.add_argument("--provider", choices=("replay", "openai-compatible"), default="replay")
    parser.add_argument("--tool", choices=tuple(tool.tool_id for tool in list_tool_specs()))
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--max-iterations", type=int, default=4)
    parser.add_argument("--replay-root", default="replays")
    parser.add_argument("--cache-dir", default=".cache")
    parser.add_argument("--json-out", default="artifacts/latest/run.json")
    parser.add_argument("--markdown-out", default="artifacts/latest/run.md")
    args = parser.parse_args()

    provider_config = ProviderConfig(
        provider=args.provider,
        replay_root=Path(args.replay_root),
        model=args.model,
        cache_dir=Path(args.cache_dir),
    )
    if args.tool:
        tool_summary = run_tool(args.tool, provider_config=provider_config, max_iterations=args.max_iterations)
        from veritool.models import RunArtifact, utc_now_iso

        artifact = RunArtifact(
            suite_name=f"VeriTool single tool: {tool_summary.tool_name}",
            provider=args.provider,
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            tools=(tool_summary,),
            aggregate_metrics={
                "tool_count": 1,
                "passed_tools": 1 if tool_summary.passed else 0,
                "failed_tools": 0 if tool_summary.passed else 1,
                "success_rate": 1.0 if tool_summary.passed else 0.0,
                "total_iterations": tool_summary.iterations,
                "average_iterations": float(tool_summary.iterations),
            },
        )
    else:
        artifact = run_tool_suite(provider_config=provider_config, max_iterations=args.max_iterations)

    write_json_report(artifact, Path(args.json_out))
    write_markdown_report(artifact, Path(args.markdown_out))


if __name__ == "__main__":
    main()
