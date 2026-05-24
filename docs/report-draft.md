# VeriTool: Synthesizing Provably Safer Agent Tools with Counterexample-Guided Verification

## Abstract

Autonomous coding agents are often given broad access to tools such as file readers, SQL clients, HTTP callers, scratchpad loggers, and evaluators. VeriTool proposes a safer interface boundary: instead of trusting the agent, synthesize narrowly scoped tools under explicit safety invariants and reject unsafe candidates with counterexamples. The prototype implements a shared CEGIS-style loop with a live OpenAI-compatible provider, six micro-tool tracks, and bounded verifiers tailored to each tool. Across four completed live runs on the same six-tool suite, the artifact records 15 converged tool runs out of 24, with the best model reaching 5 of 6 verified tools. The result is a bounded but concrete demonstration that verifier-guided repair can expose real differences in model behavior under the same safety constraints.

Word count: 149

## Introduction

The practical problem for agent safety is not only what a model thinks, but what interfaces it can act through. A model with unrestricted access to the filesystem, network, databases, and evaluators inherits the full hazard surface of those tools. Alignment-style claims about reasoning are difficult to validate. Interface contracts are narrower and therefore more tractable.

VeriTool takes this latter route. Rather than proving that an agent is safe in the large, it shrinks the environment into micro-tools with explicit contracts and verifies those contracts before the tool is admitted. The core hypothesis is:

1. many agent capabilities can be decomposed into smaller tools with crisp safety invariants,
2. those invariants are easier to validate than a general agent policy,
3. and counterexample-guided synthesis provides a practical way to search for safe implementations while keeping the process inspectable.

This project targets the Secure Program Synthesis Hackathon track **Spec-Driven Development & Evaluation (Vericoding)**.

## Related Work

VeriTool sits at the intersection of:

- counterexample-guided inductive synthesis, where failed candidates are refined using concrete witnesses;
- vericoding workflows, where a specification acts as the evaluator rather than only the generator prompt;
- executable oracle approaches to AI coding, where the model's degrees of freedom are constrained by external checks;
- and safe tool/interface design for agent systems, where capability boundaries matter more than unconstrained generality.

The distinctive contribution here is the environment-first framing: the repository treats safe agent tooling as the synthesis target itself, rather than verifying downstream business logic after the fact.

## Methodology

### Shared Loop

VeriTool implements one shared runtime for six tool classes. Each run follows the same loop:

1. define a micro-tool, function signature, and primary safety invariant;
2. construct a prompt that includes the tool contract and prior counterexamples;
3. request a candidate implementation from either a replay provider or a live OpenAI-compatible endpoint;
4. run AST guards and a tool-specific bounded verifier;
5. if verification fails, record the counterexample and feed it into the next generation attempt;
6. accept only the first candidate that satisfies the bounded verifier suite.

The runtime is implemented in `src/veritool/runtime.py`, with provider adapters in `src/veritool/llm.py`, casefile generation in `src/veritool/demo_bundle.py`, and the verifier registry in `src/veritool/tools.py`.

### Tool Set

The artifact covers six tool tracks:

- `Local Context Reader`
  - invariant: normalized path must remain inside the safe base directory and end in `.txt`
  - evidence lane: AST guard plus bounded adversarial path coverage

- `Bounded SQL Querier`
  - invariant: only a tiny SELECT-only grammar is allowed
  - evidence lane: AST guard plus oracle-matched execution over safe and unsafe queries

- `Safe API Caller`
  - invariant: only HTTPS GET requests to explicit public hosts are allowed
  - evidence lane: URL policy oracle covering scheme, host, IP, and method restrictions

- `Append-Only Logger`
  - invariant: previous state remains an exact prefix of the new state and the byte budget is never exceeded
  - evidence lane: prefix-preservation and bounded-growth checks

- `PII Masker`
  - invariant: output contains no configured email, phone, SSN, or card regex matches
  - evidence lane: bounded fixture suite plus residual-regex checks

- `Compute-Bounded Evaluator`
  - invariant: only a small arithmetic AST whitelist is accepted and semantics must match the reference interpreter on bounded inputs
  - evidence lane: AST whitelist plus bounded oracle equivalence

### Replay And Live Modes

The repository supports two provider modes:

- `replay`: deterministic, no credentials required
- `openai-compatible`: live generation through `OPENAI_API_KEY` and `OPENAI_BASE_URL`

The live runner supports `.env` loading and maps `OPENROUTER_API_KEY` into the OpenAI-compatible client path; the completed runs reported below used OpenRouter-compatible endpoints for `claude-sonnet-4`, `gpt-4o`, `deepseek-v3.2-exp`, and `gemini-2.5-pro`.

### Implementation Details

The important methodological choice is that VeriTool does not claim a universal verifier for arbitrary Python. Instead, each tool defines:

- a narrow function signature,
- a bounded state or input domain,
- an explicit policy oracle,
- and a verifier that converts unsafe behavior into a structured counterexample.

This is enough to produce a genuine Vericoding loop while staying within an honest evidence surface.

## Results

The repository includes four completed live-model runs on the same benchmark:

- `anthropic/claude-sonnet-4`: 5 of 6 tools converged in 17 total iterations
- `openai/gpt-4o`: 4 of 6 tools converged in 21 total iterations
- `deepseek/deepseek-v3.2-exp`: 4 of 6 tools converged in 20 total iterations
- `google/gemini-2.5-pro`: 2 of 6 tools converged in 22 total iterations

Aggregate across completed runs:

- total tool runs: 24
- converged tool runs: 15
- aggregate convergence rate: 62.5%
- mean iterations per tool: 3.33

Examples:

- `Local Context Reader`
  - first failure: valid nested path crashed because the candidate failed to canonicalize `./nested/../nested/notes.txt`
  - accepted result: bounded safe-path and extension invariants hold across 7/7 checked cases

- `Bounded SQL Querier`
  - first failure: candidate returned all rows rather than respecting the WHERE clause
  - accepted result: safe queries match the reference interpreter and unsafe SQL is rejected across 7/7 checked cases

- `PII Masker`
  - first failure: candidate masked only emails, leaving phone and card patterns intact
  - accepted result: all configured PII classes are removed across the bounded fixture suite

- `Compute-Bounded Evaluator`
  - first failure: exponentiation was accepted even though it lies outside the allowed grammar
  - accepted result: the evaluator matches the reference interpreter and rejects unsupported syntax across 12/12 checked cases

Artifacts generated from the live run:

- `artifacts/live/run.json`
- `artifacts/live/run.md`
- `artifacts/live/demo-bundle.json`

## Discussion

The strongest outcome is not merely the count of converged tools. The more important artifact is the recorded transition from unsafe to accepted candidates under real models. One can inspect the first failure, read the exact counterexample payload, compare it to the accepted repair, and also see where the loop exhausts its budget without converging.

VeriTool also demonstrates a useful design principle for agent systems: safe capability growth should happen through small, inspectable interfaces rather than by handing an agent general-purpose power and hoping downstream monitoring catches misuse. The spread from 2 of 6 to 5 of 6 converged tools is useful because it is a real-model measurement rather than a synthetic demonstration.

## What Is New Hackathon Work

All contents under `veritool/` are new work for the Secure Program Synthesis Hackathon, including:

- the shared synthesis runtime,
- replay and live provider adapters,
- the six verifier lanes and accepted candidate traces,
- the evidence bundle generation pipeline,
- the demo website,
- and the report/demo materials in `docs/`.

## Limitations And Dual-Use Considerations

### Limitations

The current artifact is bounded and deliberately micro-scoped. It does not provide a full symbolic semantics for arbitrary Python candidates. The evidence surface is a combination of AST guards, policy fixtures, regex checks, and bounded executable oracles rather than universal proofs. Live API mode depends on external model behavior, credentials, and endpoint quirks. The live run itself is mixed: two tool tracks fail within the budget, showing that the generator is still brittle even under narrow contracts. The tool contracts are intentionally small; a production system would need richer invariants, broader domain coverage, and stronger solver-backed reasoning for more complex interfaces.

### Dual-Use Risks

A synthesis-and-verification loop can be used offensively if the target policy is malicious. For example, one could search for code that satisfies a harmful operational objective while evading a weak safety oracle. The repository should therefore be described as a defensive safe-tool prototype, not as a general verified code synthesis engine.

### Responsible Use

When adapting these methods to real systems, the policy oracles, bounds, and residual risks should be disclosed explicitly. If a tool contract reveals a real vulnerability in a deployed system, disclosure should happen privately with reproduction details before any public claim.

### Future Work

The most valuable next steps are:

- replace some bounded executable lanes with stronger symbolic or solver-backed semantics,
- broaden the tool grammar for SQL and evaluator tracks while preserving tractable verification,
- add richer stateful tools such as file appenders with more explicit transition systems,
- and run a larger live-model benchmark comparing how different providers respond to counterexample feedback.
