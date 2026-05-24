from __future__ import annotations

import json
import re
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    live_root = root / "artifacts" / "live"
    models = []
    for model_dir in sorted(path for path in live_root.iterdir() if path.is_dir()):
        run_path = model_dir / "run.json"
        trajectory_path = model_dir / "trajectories.json"
        if not run_path.exists() or not trajectory_path.exists():
            continue
        run_payload = json.loads(run_path.read_text(encoding="utf-8"))
        trajectory_payload = json.loads(trajectory_path.read_text(encoding="utf-8"))
        models.append(
            {
                "model": trajectory_payload["model"],
                "model_key": model_dir.name,
                "aggregate_metrics": run_payload["aggregate_metrics"],
                "tools": trajectory_payload["tools"],
            }
        )

    models.sort(key=lambda item: (-item["aggregate_metrics"]["passed_tools"], item["aggregate_metrics"]["average_iterations"], item["model"]))
    public_payload = {"models": models}
    output_path = root / "demo-site" / "all-models.json"
    output_path.write_text(json.dumps(public_payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote multi-model site data to {output_path}")


if __name__ == "__main__":
    main()
