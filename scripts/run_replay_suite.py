from __future__ import annotations

import json
from pathlib import Path

from veritool.demo_bundle import build_demo_bundle
from veritool.reporting import write_json_report, write_markdown_report
from veritool.runtime import ProviderConfig, run_tool_suite


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    artifact = run_tool_suite(provider_config=ProviderConfig(provider="replay", replay_root=root / "replays"), max_iterations=4)
    output_dir = root / "artifacts" / "latest"
    demo_bundle = build_demo_bundle(artifact)
    write_json_report(artifact, output_dir / "run.json")
    write_markdown_report(artifact, output_dir / "run.md")
    (output_dir / "demo-bundle.json").write_text(
        json.dumps(demo_bundle, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    public_dir = root / "demo-site" / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "demo-bundle.json").write_text(json.dumps(demo_bundle, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote reports to {output_dir}")


if __name__ == "__main__":
    main()
