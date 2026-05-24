# VeriTool Run Report

- Provider: `openai-compatible`
- Started: `2026-05-24T21:58:58+00:00`
- Finished: `2026-05-24T22:28:11+00:00`

## Aggregate Metrics

- `tool_count`: 6
- `passed_tools`: 2
- `failed_tools`: 4
- `success_rate`: 0.333
- `total_iterations`: 22
- `average_iterations`: 3.67

## Tool Results

### Local Context Reader

- Status: `failed`
- Iterations: `4`
- Evidence level: `ast-guard`
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; forbidden capability reference detected: os.
  - Iteration 3: fail; reader crashed on a valid safe path
  - Iteration 4: fail; forbidden capability reference detected: os.

### Bounded SQL Querier

- Status: `passed`
- Iterations: `3`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 7
- `total_cases`: 7
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; candidate code did not parse: unterminated string literal (detected at line 6)
  - Iteration 3: pass; query runner preserves the SELECT-only grammar on bounded safe and adversarial examples

### Safe API Caller

- Status: `failed`
- Iterations: `4`
- Evidence level: `ast-guard`
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; candidate code did not parse: unterminated string literal (detected at line 14)
  - Iteration 3: fail; forbidden capability reference detected: requests
  - Iteration 4: fail; forbidden capability reference detected: requests

### Append-Only Logger

- Status: `passed`
- Iterations: `3`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 5
- `total_cases`: 5
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; invalid append request was accepted
  - Iteration 3: pass; logger preserves prefix monotonicity and bounded growth on bounded adversarial cases

### PII Masker

- Status: `failed`
- Iterations: `4`
- Evidence level: `syntax`
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; masker did not produce the expected stable redaction
  - Iteration 3: fail; imports are not allowed in candidate tools
  - Iteration 4: fail; candidate code did not parse: unterminated string literal (detected at line 6)

### Compute-Bounded Evaluator

- Status: `failed`
- Iterations: `4`
- Evidence level: `ast-guard`
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; imports are not allowed in candidate tools
  - Iteration 3: fail; imports are not allowed in candidate tools
  - Iteration 4: fail; imports are not allowed in candidate tools
