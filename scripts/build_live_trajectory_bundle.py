from __future__ import annotations

import json
import re
from pathlib import Path

from veritool.trajectory_bundle import build_trajectory_bundle


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    model_slug = "openai/gpt-4o"
    model_key = _model_key(model_slug)
    bundle = build_trajectory_bundle(
        root,
        run_path=root / "artifacts" / "live" / model_key / "run.json",
        cache_dir=root / ".cache" / model_key,
        model_slug=model_slug,
    )
    output_path = root / "demo-site" / "live-trajectories.json"
    output_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote trajectory bundle to {output_path}")


def _model_key(model_slug: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", model_slug).strip("-").lower()


if __name__ == "__main__":
    main()
