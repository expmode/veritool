# VeriTool Results

## Completed Live Runs

The completed comparison set currently includes four real live-model runs, each evaluated on the same six-tool suite with the same 4-iteration budget per tool.

### Per-Model Summary

- `anthropic/claude-sonnet-4`
  - converged tools: `5/6`
  - total synthesis iterations: `17`
  - average iterations per tool: `2.83`

- `openai/gpt-4o`
  - converged tools: `4/6`
  - total synthesis iterations: `21`
  - average iterations per tool: `3.50`

- `deepseek/deepseek-v3.2-exp`
  - converged tools: `4/6`
  - total synthesis iterations: `20`
  - average iterations per tool: `3.33`

- `google/gemini-2.5-pro`
  - converged tools: `2/6`
  - total synthesis iterations: `22`
  - average iterations per tool: `3.67`

## Aggregate Summary

- total tool runs evaluated: `24`
- converged tool runs: `15`
- aggregate convergence rate: `62.5%`
- mean iterations per tool across completed runs: `3.33`

## Observed Pattern

Across the completed runs, bounded logging, local file reads, and small SQL fragments were generally easier for models to repair after verifier feedback. The hardest tracks were outbound API policy enforcement and the tiny arithmetic evaluator, where small structural mistakes repeatedly triggered AST or policy failures.

The strongest result is not only the final accepted code. The more useful evidence is the recorded repair process: first failure, counterexample payload, subsequent attempts, and final acceptance or budget exhaustion.

## Evidence Files

- website comparison bundle: `demo-site/all-models.json`
- per-model machine-readable reports: `artifacts/live/<model-key>/run.json`
- per-model markdown summaries: `artifacts/live/<model-key>/run.md`
- per-model trajectory bundles: `artifacts/live/<model-key>/trajectories.json`
