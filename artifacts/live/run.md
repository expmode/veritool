# VeriTool Run Report

- Provider: `openai-compatible`
- Started: `2026-05-24T20:43:12+00:00`
- Finished: `2026-05-24T20:43:12+00:00`

## Aggregate Metrics

- `tool_count`: 6
- `passed_tools`: 4
- `failed_tools`: 2
- `success_rate`: 0.667
- `total_iterations`: 19
- `average_iterations`: 3.17

## Tool Results

### Local Context Reader

- Status: `passed`
- Iterations: `3`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 7
- `total_cases`: 7
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; unsafe path was accepted
  - Iteration 3: pass; reader enforces normalized safe-path and extension invariants on bounded adversarial cases

### Bounded SQL Querier

- Status: `passed`
- Iterations: `3`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 7
- `total_cases`: 7
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; valid SELECT query crashed the candidate
  - Iteration 3: pass; query runner preserves the SELECT-only grammar on bounded safe and adversarial examples

### Safe API Caller

- Status: `failed`
- Iterations: `4`
- Evidence level: `bounded-execution`
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; unsafe API request was accepted
  - Iteration 3: fail; safe request crashed the candidate
  - Iteration 4: fail; safe request crashed the candidate

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

- Status: `passed`
- Iterations: `3`
- Evidence level: `bounded-execution + regex-check`
- `passed_cases`: 3
- `total_cases`: 3
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; masker did not produce the expected stable redaction
  - Iteration 3: pass; masker removes all configured PII classes on bounded fixture coverage

### Compute-Bounded Evaluator

- Status: `failed`
- Iterations: `4`
- Evidence level: `ast-guard`
- Trace:
  - Iteration 1: fail; imports are not allowed in candidate tools
  - Iteration 2: fail; candidate failed to load: __build_class__ not found
  - Iteration 3: fail; imports are not allowed in candidate tools
  - Iteration 4: fail; imports are not allowed in candidate tools
