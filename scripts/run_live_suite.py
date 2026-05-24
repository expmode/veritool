from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from veritool.demo_bundle import build_demo_bundle
from veritool.reporting import write_json_report, write_markdown_report
from veritool.runtime import ProviderConfig, run_tool_suite
from veritool.trajectory_bundle import build_trajectory_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the live VeriTool suite for a specific model.")
    parser.add_argument("--model", default="openai/gpt-4o")
    parser.add_argument("--publish-site", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    _load_dotenv(root / ".env")
    _configure_openrouter_fallbacks()
    model_key = _model_key(args.model)
    artifact = run_tool_suite(
        provider_config=ProviderConfig(
            provider="openai-compatible",
            model=args.model,
            cache_dir=root / ".cache" / model_key,
        ),
        max_iterations=4,
    )
    output_dir = root / "artifacts" / "live" / model_key
    demo_bundle = build_demo_bundle(artifact)
    write_json_report(artifact, output_dir / "run.json")
    write_markdown_report(artifact, output_dir / "run.md")
    (output_dir / "demo-bundle.json").write_text(json.dumps(demo_bundle, indent=2, sort_keys=True), encoding="utf-8")
    trajectory_bundle = build_trajectory_bundle(
        root,
        run_path=output_dir / "run.json",
        cache_dir=root / ".cache" / model_key,
        model_slug=args.model,
    )
    (output_dir / "trajectories.json").write_text(json.dumps(trajectory_bundle, indent=2, sort_keys=True), encoding="utf-8")
    if args.publish_site:
        public_dir = root / "demo-site"
        public_dir.mkdir(parents=True, exist_ok=True)
        (public_dir / "demo-bundle.json").write_text(json.dumps(demo_bundle, indent=2, sort_keys=True), encoding="utf-8")
        (public_dir / "live-demo-bundle.json").write_text(json.dumps(demo_bundle, indent=2, sort_keys=True), encoding="utf-8")
        (public_dir / "live-trajectories.json").write_text(json.dumps(trajectory_bundle, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote live run reports to {output_dir}")


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def _configure_openrouter_fallbacks() -> None:
    if "OPENAI_API_KEY" not in os.environ and "OPENROUTER_API_KEY" in os.environ:
        os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
    os.environ.setdefault("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")


def _model_key(model_slug: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", model_slug).strip("-").lower()


if __name__ == "__main__":
    main()
