# VeriTool Run Report

- Provider: `openai-compatible`
- Started: `2026-05-24T21:49:28+00:00`
- Finished: `2026-05-24T21:52:10+00:00`

## Aggregate Metrics

- `tool_count`: 6
- `passed_tools`: 5
- `failed_tools`: 1
- `success_rate`: 0.833
- `total_iterations`: 17
- `average_iterations`: 2.83

## Tool Results

### Local Context Reader

- Status: `passed`
- Iterations: `3`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 7
- `total_cases`: 7
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; reader crashed on a valid safe path
  - Iteration 3: pass; reader enforces normalized safe-path and extension invariants on bounded adversarial cases

### Bounded SQL Querier

- Status: `passed`
- Iterations: `2`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 7
- `total_cases`: 7
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: pass; query runner preserves the SELECT-only grammar on bounded safe and adversarial examples

### Safe API Caller

- Status: `passed`
- Iterations: `3`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 8
- `total_cases`: 8
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; safe request crashed the candidate
  - Iteration 3: pass; API caller enforces scheme, host, and method restrictions on bounded adversarial cases

### Append-Only Logger

- Status: `passed`
- Iterations: `2`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 5
- `total_cases`: 5
- Trace:
  - Iteration 1: fail; invalid append request was accepted
  - Iteration 2: pass; logger preserves prefix monotonicity and bounded growth on bounded adversarial cases

### PII Masker

- Status: `failed`
- Iterations: `4`
- Evidence level: `ast-guard`
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; imports are not allowed in candidate tools
  - Iteration 3: fail; masker did not produce the expected stable redaction
  - Iteration 4: fail; imports are not allowed in candidate tools

### Compute-Bounded Evaluator

- Status: `passed`
- Iterations: `3`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 12
- `total_cases`: 12
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; imports are not allowed in candidate tools
  - Iteration 3: pass; evaluator matches the bounded arithmetic oracle and rejects unsupported syntax
