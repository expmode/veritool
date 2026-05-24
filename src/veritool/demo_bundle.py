from __future__ import annotations

from typing import Any

from veritool.models import RunArtifact
from veritool.tools import get_tool_spec


CASEFILE_NOTES: dict[str, dict[str, str]] = {
    "local_context_reader": {
        "thesis": "The reader must treat path normalization as a safety boundary rather than a convenience feature.",
        "verification_lane": "AST guard plus bounded adversarial path coverage over normalized in-memory file access.",
    },
    "bounded_sql_querier": {
        "thesis": "A tiny SELECT-only fragment is easier to verify and still useful for agent retrieval.",
        "verification_lane": "AST guard plus oracle-matched execution over safe and unsafe query fixtures.",
    },
    "safe_api_caller": {
        "thesis": "The network boundary belongs in the tool contract, not in the model's intentions.",
        "verification_lane": "URL policy oracle covering scheme, host, IP, and method restrictions.",
    },
    "append_only_logger": {
        "thesis": "Scratchpad memory is safest when writes become monotonic state transitions.",
        "verification_lane": "Prefix-preservation checks and bounded byte-budget enforcement.",
    },
    "pii_masker": {
        "thesis": "Sanitization should fail closed on known high-risk PII classes before context leaves the host.",
        "verification_lane": "Regex-backed fixture suite with stable placeholder expectations.",
    },
    "compute_bounded_evaluator": {
        "thesis": "If the evaluator language is tiny, the verifier can exhaustively compare semantics on bounded cases.",
        "verification_lane": "AST whitelist plus bounded arithmetic equivalence against a reference interpreter.",
    },
}


def build_demo_bundle(artifact: RunArtifact) -> dict[str, Any]:
    casefiles = []
    for tool in artifact.tools:
        spec = get_tool_spec(tool.tool_id)
        notes = CASEFILE_NOTES[tool.tool_id]
        failing_trace = tool.traces[0]
        passing_trace = tool.traces[-1]
        casefiles.append(
            {
                "id": tool.tool_id,
                "name": tool.tool_name,
                "function_name": spec.function_name,
                "signature": spec.signature,
                "task": spec.task,
                "primary_invariant": spec.primary_invariant,
                "constraints": list(spec.constraints),
                "thesis": notes["thesis"],
                "verification_lane": notes["verification_lane"],
                "iterations": tool.iterations,
                "status": "verified" if tool.passed else "failed",
                "evidence_level": tool.evidence_level,
                "failing_attempt": {
                    "summary": failing_trace.summary,
                    "counterexample": failing_trace.counterexample,
                },
                "accepted_attempt": {
                    "summary": passing_trace.summary,
                    "metrics": tool.accepted_metrics,
                    "code": tool.accepted_code,
                },
            }
        )
    return {
        "title": "VeriTool",
        "tagline": "CEGIS for synthesizing safe agent tools under explicit environment invariants.",
        "provider": artifact.provider,
        "aggregate_metrics": artifact.aggregate_metrics,
        "timeline": [
            "Specify a micro-scoped tool and its primary invariant.",
            "Generate a candidate implementation through the synthesis interface.",
            "Run AST guards and bounded executable verifiers.",
            "Feed the counterexample back into the next generation attempt.",
            "Accept only the first candidate that satisfies the bounded verifier suite.",
        ],
        "casefiles": casefiles,
    }
