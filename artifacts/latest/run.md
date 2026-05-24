# VeriTool Run Report

- Provider: `replay`
- Started: `2026-05-24T19:19:08+00:00`
- Finished: `2026-05-24T19:19:08+00:00`

## Aggregate Metrics

- `tool_count`: 6
- `passed_tools`: 6
- `failed_tools`: 0
- `success_rate`: 1.0
- `total_iterations`: 12
- `average_iterations`: 2.0

## Tool Results

### Local Context Reader

- Status: `passed`
- Iterations: `2`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 7
- `total_cases`: 7
- Trace:
  - Iteration 1: fail; reader crashed on a valid safe path
  - Iteration 2: pass; reader enforces normalized safe-path and extension invariants on bounded adversarial cases

### Bounded SQL Querier

- Status: `passed`
- Iterations: `2`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 7
- `total_cases`: 7
- Trace:
  - Iteration 1: fail; valid SELECT query disagreed with the bounded SQL oracle
  - Iteration 2: pass; query runner preserves the SELECT-only grammar on bounded safe and adversarial examples

### Safe API Caller

- Status: `passed`
- Iterations: `2`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 8
- `total_cases`: 8
- Trace:
  - Iteration 1: fail; unsafe request raised the wrong error type
  - Iteration 2: pass; API caller enforces scheme, host, and method restrictions on bounded adversarial cases

### Append-Only Logger

- Status: `passed`
- Iterations: `2`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 5
- `total_cases`: 5
- Trace:
  - Iteration 1: fail; append-only logger disagreed with the reference append semantics
  - Iteration 2: pass; logger preserves prefix monotonicity and bounded growth on bounded adversarial cases

### PII Masker

- Status: `passed`
- Iterations: `2`
- Evidence level: `bounded-execution + regex-check`
- `passed_cases`: 3
- `total_cases`: 3
- Trace:
  - Iteration 1: fail; masker did not produce the expected stable redaction
  - Iteration 2: pass; masker removes all configured PII classes on bounded fixture coverage

### Compute-Bounded Evaluator

- Status: `passed`
- Iterations: `2`
- Evidence level: `bounded-execution + ast-guard`
- `passed_cases`: 12
- `total_cases`: 12
- Trace:
  - Iteration 1: fail; unsupported expression was accepted
  - Iteration 2: pass; evaluator matches the bounded arithmetic oracle and rejects unsupported syntax
