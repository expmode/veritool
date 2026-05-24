from __future__ import annotations

import json
from pathlib import Path

from veritool.models import RunArtifact


def write_json_report(artifact: RunArtifact, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def to_markdown(artifact: RunArtifact) -> str:
    lines = [
        "# VeriTool Run Report",
        "",
        f"- Provider: `{artifact.provider}`",
        f"- Started: `{artifact.started_at}`",
        f"- Finished: `{artifact.finished_at}`",
        "",
        "## Aggregate Metrics",
        "",
    ]
    for key, value in artifact.aggregate_metrics.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Tool Results", ""])
    for tool in artifact.tools:
        lines.append(f"### {tool.tool_name}")
        lines.append("")
        lines.append(f"- Status: `{'passed' if tool.passed else 'failed'}`")
        lines.append(f"- Iterations: `{tool.iterations}`")
        lines.append(f"- Evidence level: `{tool.evidence_level}`")
        for key, value in tool.accepted_metrics.items():
            lines.append(f"- `{key}`: {value}")
        if tool.traces:
            lines.append("- Trace:")
            for trace in tool.traces:
                line = f"  - Iteration {trace.iteration}: {'pass' if trace.passed else 'fail'}; {trace.summary}"
                lines.append(line)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(artifact: RunArtifact, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(to_markdown(artifact), encoding="utf-8")
