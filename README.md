# VeriTool

[Technical Report](https://sauravpanigrahi.com/artifact/veritool)

<img width="2278" height="816" alt="image" src="https://github.com/user-attachments/assets/b82e130e-431b-42d2-aef1-ad2aa09d37ef" />

VeriTool is a Vericoding artifact for synthesizing narrowly scoped agent tools under explicit safety invariants. Instead of trying to prove that an autonomous agent will behave safely in the large, VeriTool constrains the environment the agent is allowed to act through: path readers, SQL accessors, API callers, loggers, maskers, and evaluators.

The repository implements a shared CEGIS-style loop:

1. define a micro-tool and its primary invariant,
2. generate Python code through a provider interface,
3. run AST guards plus bounded executable verifiers,
4. feed the counterexample back into the next generation attempt,
5. accept only the first candidate that passes the bounded verifier suite.

## Current Artifact Claim

The current artifact includes:

- a reusable synthesis runtime with replay and live OpenAI-compatible providers,
- six micro-scoped tool tracks with bounded verifiers and adversarial fixtures,
- completed live runs for `claude-sonnet-4`, `gpt-4o`, `deepseek-v3.2-exp`, and `gemini-2.5-pro`,
- generated evidence bundles for the report and website,
- and a static website for comparing benchmark outcomes and inspecting trajectories.

This is intentionally a bounded claim. VeriTool does not prove arbitrary Python programs correct. It verifies a narrow family of safe-tool contracts with a mix of AST guards, bounded executable oracles, regex checks, and policy fixtures.

## Quick Start

### Python artifact

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
PYTHONPATH=src python scripts/run_replay_suite.py
PYTHONPATH=src python -m pytest tests/test_replay_suite.py
```

Live outputs land in `artifacts/live/`.

### Demo site

```bash
cd demo-site
python3 -m http.server 4175
```

Then open `http://127.0.0.1:4175`.

## Live API Mode

For live generation with an OpenAI-compatible endpoint:

```bash
# either export OPENAI_API_KEY directly
# or place OPENROUTER_API_KEY in veritool/.env
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
PYTHONPATH=src python scripts/run_live_suite.py --model "openai/gpt-4o"
```

`scripts/run_live_suite.py` loads `veritool/.env`, maps `OPENROUTER_API_KEY` into the OpenAI-compatible client when needed, supports `--model`, and caches completions under `.cache/<model-key>/`.

To rebuild the website comparison bundle after completed runs:

```bash
PYTHONPATH=src python scripts/build_multi_model_site_data.py
```

## Tool Set

- `Local Context Reader`: safe path normalization plus `.txt` restriction inside a bounded in-memory file map.
- `Bounded SQL Querier`: a SELECT-only SQL fragment over an in-memory table.
- `Safe API Caller`: HTTPS GET requests to explicit public allowlists only.
- `Append-Only Logger`: monotonic scratchpad writes with byte-budget enforcement.
- `PII Masker`: redacts emails, phones, SSNs, and 16-digit card numbers.
- `Compute-Bounded Evaluator`: a tiny arithmetic language with AST and node-budget limits.

## Evidence Snapshot

Completed live runs currently included in the website comparison:

- `anthropic/claude-sonnet-4`: `5/6` tools converged, `17` total iterations
- `openai/gpt-4o`: `4/6` tools converged, `21` total iterations
- `deepseek/deepseek-v3.2-exp`: `4/6` tools converged, `20` total iterations
- `google/gemini-2.5-pro`: `2/6` tools converged, `22` total iterations

Aggregate across completed runs:

- `15/24` tool runs converged
- `62.5%` aggregate convergence rate
- `3.33` mean iterations per tool

## Repository Layout

- `src/veritool/`: synthesis runtime, provider adapters, reporting, verifier registry
- `replays/`: deterministic candidate sequences for each tool
- `tests/`: replay-suite regression tests
- `scripts/`: evaluation entry points and site-data builders
- `artifacts/`: generated evidence bundles
- `artifacts/live/`: completed live-model outputs
- `docs/`: report draft and results summary
- `demo-site/`: static website for benchmark and trajectory inspection

## Limitations

- Verification is bounded and domain-specific rather than universal.
- Candidate code is checked by policy fixtures and executable oracles, not by a full symbolic semantics for arbitrary Python.
- The live API path depends on external model behavior, credentials, and provider stability.
- Completed live runs span outcomes from `2/6` to `5/6` converged tools, which is useful evidence of real model differences but still shows substantial brittleness.
- The tool contracts are intentionally micro-scoped to keep verification inspectable and tractable.
