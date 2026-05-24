from __future__ import annotations

import ast
import ipaddress
import posixpath
import re
from dataclasses import dataclass
from typing import Any, Callable
from urllib import parse as urllib_parse

from veritool.models import Counterexample, VerificationResult


SAFE_GLOBALS: dict[str, Any] = {
    "__builtins__": {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "Exception": Exception,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "range": range,
        "reversed": reversed,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "ValueError": ValueError,
    },
    "ast": ast,
    "ipaddress": ipaddress,
    "posixpath": posixpath,
    "re": re,
    "urllib_parse": urllib_parse,
}

FORBIDDEN_NAMES = {"__import__", "compile", "eval", "exec", "input", "open"}
FORBIDDEN_MODULE_TERMS = ("socket", "subprocess", "requests", "pathlib", "os.", "sys.")


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    name: str
    function_name: str
    signature: str
    task: str
    primary_invariant: str
    constraints: tuple[str, ...]
    verifier: Callable[[Callable[..., Any], ast.Module], VerificationResult]

    def verify_candidate(self, code: str) -> VerificationResult:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return VerificationResult(
                passed=False,
                summary=f"candidate code did not parse: {exc.msg}",
                evidence_level="syntax",
                counterexample=Counterexample(
                    title="syntax_error",
                    description="The candidate could not be parsed as Python.",
                    payload={"line": exc.lineno, "offset": exc.offset, "message": exc.msg},
                ),
            )

        generic_failure = _check_generic_ast(tree, code)
        if generic_failure is not None:
            return generic_failure

        try:
            function = _load_function(code, self.function_name)
        except Exception as exc:
            return VerificationResult(
                passed=False,
                summary=f"candidate failed to load: {exc}",
                evidence_level="loader",
                counterexample=Counterexample(
                    title="load_failure",
                    description="The candidate did not expose the requested function cleanly.",
                    payload={"function_name": self.function_name, "error": str(exc)},
                ),
            )
        return self.verifier(function, tree)


def list_tool_specs() -> tuple[ToolSpec, ...]:
    return (
        _local_context_reader_spec(),
        _bounded_sql_querier_spec(),
        _safe_api_caller_spec(),
        _append_only_logger_spec(),
        _pii_masker_spec(),
        _compute_bounded_evaluator_spec(),
    )


def get_tool_spec(tool_id: str) -> ToolSpec:
    for spec in list_tool_specs():
        if spec.tool_id == tool_id:
            return spec
    raise KeyError(f"unknown tool id: {tool_id}")


def _check_generic_ast(tree: ast.Module, code: str) -> VerificationResult | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return VerificationResult(
                passed=False,
                summary="imports are not allowed in candidate tools",
                evidence_level="ast-guard",
                counterexample=Counterexample(
                    title="forbidden_import",
                    description="Candidates must stay within the provided runtime and cannot import modules.",
                    payload={"node_type": type(node).__name__},
                ),
            )
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return VerificationResult(
                passed=False,
                summary="global or nonlocal state is not allowed",
                evidence_level="ast-guard",
                counterexample=Counterexample(
                    title="forbidden_state",
                    description="Candidate attempted to use global or nonlocal state.",
                    payload={"node_type": type(node).__name__},
                ),
            )
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return VerificationResult(
                passed=False,
                summary=f"forbidden builtin used: {node.id}",
                evidence_level="ast-guard",
                counterexample=Counterexample(
                    title="forbidden_builtin",
                    description="Candidate called a builtin that escapes the constrained environment.",
                    payload={"name": node.id},
                ),
            )
    lowered = code.lower()
    for term in FORBIDDEN_MODULE_TERMS:
        if term in lowered:
            return VerificationResult(
                passed=False,
                summary=f"forbidden capability reference detected: {term}",
                evidence_level="ast-guard",
                counterexample=Counterexample(
                    title="forbidden_capability",
                    description="Candidate referenced a module or capability that is outside the safe micro-tool model.",
                    payload={"term": term},
                ),
            )
    return None


def _load_function(code: str, function_name: str) -> Callable[..., Any]:
    namespace = dict(SAFE_GLOBALS)
    exec(compile(code, filename="<candidate>", mode="exec"), namespace, namespace)
    function = namespace.get(function_name)
    if not callable(function):
        raise ValueError(f"callable {function_name} not found")
    return function


def _local_context_reader_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="local_context_reader",
        name="Local Context Reader",
        function_name="read_local_context",
        signature="read_local_context(base_dir: str, requested_path: str, file_map: dict[str, str]) -> str",
        task="Normalize a user-requested relative path, reject traversal or non-.txt access, and read the content from the provided in-memory file map.",
        primary_invariant="A request may only read `.txt` files that remain inside the declared safe base directory after normalization.",
        constraints=(
            "Reject absolute paths and any normalized path outside the base directory.",
            "Reject files whose normalized path does not end in .txt.",
            "Do not touch the real filesystem; use only the provided file_map.",
        ),
        verifier=_verify_local_context_reader,
    )


def _verify_local_context_reader(function: Callable[..., Any], tree: ast.Module) -> VerificationResult:
    file_map = {
        "/safe_env/docs/ch1.txt": "chapter one",
        "/safe_env/docs/nested/notes.txt": "nested notes",
    }
    base_dir = "/safe_env/docs"
    valid_cases = [
        ("ch1.txt", "chapter one"),
        ("nested/notes.txt", "nested notes"),
        ("./nested/../nested/notes.txt", "nested notes"),
    ]
    invalid_cases = ["../secret.txt", "/etc/passwd", "notes.md", "../../../secret.txt"]
    passed = 0
    for requested_path, expected in valid_cases:
        succeeded, actual = _invoke_candidate(function, base_dir, requested_path, dict(file_map))
        if not succeeded:
            return VerificationResult(
                passed=False,
                summary="reader crashed on a valid safe path",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="reader_exception",
                    description="A valid path should not crash the synthesized reader.",
                    payload={"requested_path": requested_path, "error": str(actual)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_cases) + len(invalid_cases)},
            )
        if actual != expected:
            return VerificationResult(
                passed=False,
                summary="valid safe path produced the wrong file content",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="safe_path_mismatch",
                    description="A valid in-scope path did not resolve to the expected file contents.",
                    payload={"requested_path": requested_path, "expected": expected, "actual": actual},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_cases) + len(invalid_cases)},
            )
        passed += 1
    for requested_path in invalid_cases:
        try:
            function(base_dir, requested_path, dict(file_map))
        except ValueError:
            passed += 1
            continue
        except Exception as exc:
            return VerificationResult(
                passed=False,
                summary="reader raised the wrong error type for an unsafe path",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="unsafe_path_wrong_error",
                    description="Unsafe paths should deterministically raise ValueError.",
                    payload={"requested_path": requested_path, "error": str(exc)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_cases) + len(invalid_cases)},
            )
        return VerificationResult(
            passed=False,
            summary="unsafe path was accepted",
            evidence_level="bounded-execution",
            counterexample=Counterexample(
                title="unsafe_path_accepted",
                description="A path outside the safe environment should have raised ValueError.",
                payload={"requested_path": requested_path},
            ),
            metrics={"passed_cases": passed, "total_cases": len(valid_cases) + len(invalid_cases)},
        )
    return VerificationResult(
        passed=True,
        summary="reader enforces normalized safe-path and extension invariants on bounded adversarial cases",
        evidence_level="bounded-execution + ast-guard",
        metrics={"passed_cases": passed, "total_cases": len(valid_cases) + len(invalid_cases)},
    )


def _bounded_sql_querier_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="bounded_sql_querier",
        name="Bounded SQL Querier",
        function_name="run_bounded_sql",
        signature="run_bounded_sql(query: str, rows: list[dict[str, int]]) -> list[dict[str, int]]",
        task="Execute a tiny SELECT-only SQL fragment over an in-memory table of rows.",
        primary_invariant="Only a safe SELECT grammar is allowed; mutating SQL or multi-statement queries must be rejected.",
        constraints=(
            "Support only SELECT <columns> FROM rows [WHERE <column> <op> <int>] [LIMIT <int>].",
            "Reject DELETE, UPDATE, INSERT, DROP, ALTER, CREATE, PRAGMA, semicolons, and unknown columns.",
            "Treat the input `rows` as the only table.",
        ),
        verifier=_verify_bounded_sql_querier,
    )


def _verify_bounded_sql_querier(function: Callable[..., Any], tree: ast.Module) -> VerificationResult:
    rows = [
        {"id": 1, "score": 7, "owner": 1},
        {"id": 2, "score": 3, "owner": 2},
        {"id": 3, "score": 10, "owner": 1},
    ]
    valid_queries = [
        "SELECT * FROM rows",
        "SELECT id,score FROM rows WHERE score >= 7",
        "SELECT owner FROM rows WHERE id = 2 LIMIT 1",
    ]
    invalid_queries = [
        "DELETE FROM rows",
        "SELECT * FROM rows; DROP TABLE rows",
        "SELECT secret FROM rows",
        "UPDATE rows SET score = 0",
    ]
    passed = 0
    for query in valid_queries:
        succeeded, actual = _invoke_candidate(function, query, [dict(row) for row in rows])
        if not succeeded:
            return VerificationResult(
                passed=False,
                summary="valid SELECT query crashed the candidate",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="sql_exception",
                    description="A safe query should execute cleanly in the bounded runner.",
                    payload={"query": query, "error": str(actual)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_queries) + len(invalid_queries)},
            )
        expected = _sql_oracle(query, rows)
        if actual != expected:
            return VerificationResult(
                passed=False,
                summary="valid SELECT query disagreed with the bounded SQL oracle",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="sql_oracle_mismatch",
                    description="A safe query should match the reference interpreter exactly.",
                    payload={"query": query, "expected": expected, "actual": actual},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_queries) + len(invalid_queries)},
            )
        passed += 1
    for query in invalid_queries:
        try:
            function(query, [dict(row) for row in rows])
        except ValueError:
            passed += 1
            continue
        except Exception as exc:
            return VerificationResult(
                passed=False,
                summary="unsafe query raised the wrong error type",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="unsafe_sql_wrong_error",
                    description="Unsafe queries should raise ValueError rather than crash unpredictably.",
                    payload={"query": query, "error": str(exc)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_queries) + len(invalid_queries)},
            )
        return VerificationResult(
            passed=False,
            summary="unsafe SQL query was accepted",
            evidence_level="bounded-execution",
            counterexample=Counterexample(
                title="unsafe_sql_accepted",
                description="A query outside the allowlisted grammar should have raised ValueError.",
                payload={"query": query},
            ),
            metrics={"passed_cases": passed, "total_cases": len(valid_queries) + len(invalid_queries)},
        )
    return VerificationResult(
        passed=True,
        summary="query runner preserves the SELECT-only grammar on bounded safe and adversarial examples",
        evidence_level="bounded-execution + ast-guard",
        metrics={"passed_cases": passed, "total_cases": len(valid_queries) + len(invalid_queries)},
    )


def _safe_api_caller_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="safe_api_caller",
        name="Safe API Caller",
        function_name="safe_api_call",
        signature="safe_api_call(url: str, method: str, allowlist: list[str], responses: dict[str, str]) -> str",
        task="Validate an outbound API request against a strict allowlist and return a mocked response body.",
        primary_invariant="Only HTTPS GET requests to explicitly allowlisted public hosts are permitted.",
        constraints=(
            "Reject localhost, private IPs, bare IP hosts, and non-HTTPS schemes.",
            "Only the GET method is allowed.",
            "Look up the final response in the provided responses map using the key '<METHOD> <URL>'.",
        ),
        verifier=_verify_safe_api_caller,
    )


def _verify_safe_api_caller(function: Callable[..., Any], tree: ast.Module) -> VerificationResult:
    allowlist = ["api.safe.test", "docs.safe.test"]
    responses = {
        "GET https://api.safe.test/v1/summary": '{"status":"ok"}',
        "GET https://docs.safe.test/readme": "docs",
    }
    valid_requests = [
        ("https://api.safe.test/v1/summary", "GET"),
        ("https://docs.safe.test/readme", "get"),
    ]
    invalid_requests = [
        ("http://api.safe.test/v1/summary", "GET"),
        ("https://localhost/admin", "GET"),
        ("https://127.0.0.1/debug", "GET"),
        ("https://10.0.0.7/private", "GET"),
        ("https://evil.test/phish", "GET"),
        ("https://api.safe.test/v1/summary", "POST"),
    ]
    passed = 0
    for url, method in valid_requests:
        succeeded, actual = _invoke_candidate(function, url, method, list(allowlist), dict(responses))
        if not succeeded:
            return VerificationResult(
                passed=False,
                summary="safe request crashed the candidate",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="api_exception",
                    description="An allowlisted safe request should not crash the candidate.",
                    payload={"url": url, "method": method, "error": str(actual)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_requests) + len(invalid_requests)},
            )
        expected = _api_oracle(url, method, allowlist, responses)
        if actual != expected:
            return VerificationResult(
                passed=False,
                summary="safe request did not match mocked API oracle output",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="api_oracle_mismatch",
                    description="An allowlisted public request should return the same mocked body as the reference policy.",
                    payload={"url": url, "method": method, "expected": expected, "actual": actual},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_requests) + len(invalid_requests)},
            )
        passed += 1
    for url, method in invalid_requests:
        try:
            function(url, method, list(allowlist), dict(responses))
        except ValueError:
            passed += 1
            continue
        except Exception as exc:
            return VerificationResult(
                passed=False,
                summary="unsafe request raised the wrong error type",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="unsafe_request_wrong_error",
                    description="Unsafe requests should raise ValueError under the policy.",
                    payload={"url": url, "method": method, "error": str(exc)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_requests) + len(invalid_requests)},
            )
        return VerificationResult(
            passed=False,
            summary="unsafe API request was accepted",
            evidence_level="bounded-execution",
            counterexample=Counterexample(
                title="unsafe_request_accepted",
                description="A request outside the allowlist or scheme/method policy should have raised ValueError.",
                payload={"url": url, "method": method},
            ),
            metrics={"passed_cases": passed, "total_cases": len(valid_requests) + len(invalid_requests)},
        )
    return VerificationResult(
        passed=True,
        summary="API caller enforces scheme, host, and method restrictions on bounded adversarial cases",
        evidence_level="bounded-execution + ast-guard",
        metrics={"passed_cases": passed, "total_cases": len(valid_requests) + len(invalid_requests)},
    )


def _append_only_logger_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="append_only_logger",
        name="Append-Only Logger",
        function_name="append_only_log",
        signature="append_only_log(existing: str, new_entry: str, max_bytes: int = 4096) -> str",
        task="Append a new log entry without mutating existing bytes and enforce a hard output-size cap.",
        primary_invariant="The previous log must remain a prefix of the new log; size must never exceed the configured bound.",
        constraints=(
            "Preserve the full previous log exactly as a prefix.",
            "If the existing log is non-empty and does not end with a newline, insert one before the new entry.",
            "Reject outputs whose byte length would exceed max_bytes.",
        ),
        verifier=_verify_append_only_logger,
    )


def _verify_append_only_logger(function: Callable[..., Any], tree: ast.Module) -> VerificationResult:
    valid_cases = [
        ("", "first event", 64),
        ("seed", "next event", 64),
        ("seed\nline", "tail", 64),
    ]
    passed = 0
    for existing, new_entry, max_bytes in valid_cases:
        succeeded, actual = _invoke_candidate(function, existing, new_entry, max_bytes)
        if not succeeded:
            return VerificationResult(
                passed=False,
                summary="valid append request crashed the candidate",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="append_exception",
                    description="A legal append should execute cleanly.",
                    payload={"existing": existing, "new_entry": new_entry, "error": str(actual)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_cases) + 2},
            )
        expected = _append_oracle(existing, new_entry, max_bytes)
        if actual != expected:
            return VerificationResult(
                passed=False,
                summary="append-only logger disagreed with the reference append semantics",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="append_mismatch",
                    description="The logger must preserve the prior log exactly while appending one new entry.",
                    payload={
                        "existing": existing,
                        "new_entry": new_entry,
                        "expected": expected,
                        "actual": actual,
                    },
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_cases) + 2},
            )
        if not actual.startswith(existing):
            return VerificationResult(
                passed=False,
                summary="existing log is not preserved as a prefix",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="prefix_violation",
                    description="Append-only state requires the old log to remain an exact prefix.",
                    payload={"existing": existing, "new_entry": new_entry, "actual": actual},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_cases) + 2},
            )
        passed += 1
    for existing, new_entry, max_bytes in [("seed", "x" * 80, 16), ("", "abc\0def", 64)]:
        try:
            function(existing, new_entry, max_bytes)
        except ValueError:
            passed += 1
            continue
        except Exception as exc:
            return VerificationResult(
                passed=False,
                summary="invalid append raised the wrong error type",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="invalid_append_wrong_error",
                    description="Rejected append cases should raise ValueError.",
                    payload={"existing": existing, "new_entry": new_entry, "error": str(exc)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(valid_cases) + 2},
            )
        return VerificationResult(
            passed=False,
            summary="invalid append request was accepted",
            evidence_level="bounded-execution",
            counterexample=Counterexample(
                title="invalid_append_accepted",
                description="Oversized writes and NUL bytes should be rejected.",
                payload={"existing": existing, "new_entry": new_entry, "max_bytes": max_bytes},
            ),
            metrics={"passed_cases": passed, "total_cases": len(valid_cases) + 2},
        )
    return VerificationResult(
        passed=True,
        summary="logger preserves prefix monotonicity and bounded growth on bounded adversarial cases",
        evidence_level="bounded-execution + ast-guard",
        metrics={"passed_cases": passed, "total_cases": len(valid_cases) + 2},
    )


def _pii_masker_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="pii_masker",
        name="PII Masker",
        function_name="mask_pii",
        signature="mask_pii(text: str) -> str",
        task="Redact common PII patterns before text is sent to an LLM.",
        primary_invariant="Masked output must not contain emails, US phone numbers, SSNs, or 16-digit card numbers recognized by the repository regex suite.",
        constraints=(
            "Replace matches with stable placeholders rather than deleting all surrounding context.",
            "Handle multiple PII categories in one string.",
            "Do not introduce new digits that recreate a banned pattern.",
        ),
        verifier=_verify_pii_masker,
    )


def _verify_pii_masker(function: Callable[..., Any], tree: ast.Module) -> VerificationResult:
    cases = [
        (
            "Alice alice@example.com called 555-123-4567 with card 4111-1111-1111-1111.",
            "Alice [EMAIL] called [PHONE] with card [CARD].",
        ),
        ("SSN 123-45-6789 must be scrubbed.", "SSN [SSN] must be scrubbed."),
        ("No secrets here.", "No secrets here."),
    ]
    patterns = _pii_patterns()
    passed = 0
    for text, expected in cases:
        succeeded, actual = _invoke_candidate(function, text)
        if not succeeded:
            return VerificationResult(
                passed=False,
                summary="PII masking candidate crashed on bounded fixture text",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="masker_exception",
                    description="The masker should handle each fixture string without crashing.",
                    payload={"text": text, "error": str(actual)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(cases)},
            )
        if actual != expected:
            return VerificationResult(
                passed=False,
                summary="masker did not produce the expected stable redaction",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="masking_mismatch",
                    description="The masker should preserve context while replacing the matched PII token with the expected placeholder.",
                    payload={"text": text, "expected": expected, "actual": actual},
                ),
                metrics={"passed_cases": passed, "total_cases": len(cases)},
            )
        for label, pattern in patterns.items():
            if pattern.search(actual):
                return VerificationResult(
                    passed=False,
                    summary="masked output still contains a banned PII pattern",
                    evidence_level="bounded-execution",
                    counterexample=Counterexample(
                        title="residual_pii",
                        description="A verified masking pass must remove every configured regex match class.",
                        payload={"label": label, "text": text, "actual": actual},
                    ),
                    metrics={"passed_cases": passed, "total_cases": len(cases)},
                )
        passed += 1
    return VerificationResult(
        passed=True,
        summary="masker removes all configured PII classes on bounded fixture coverage",
        evidence_level="bounded-execution + regex-check",
        metrics={"passed_cases": passed, "total_cases": len(cases)},
    )


def _compute_bounded_evaluator_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="compute_bounded_evaluator",
        name="Compute-Bounded Evaluator",
        function_name="bounded_evaluate",
        signature="bounded_evaluate(expression: str, variables: dict[str, int], max_nodes: int = 32) -> int",
        task="Evaluate a tiny arithmetic expression language with explicit resource bounds.",
        primary_invariant="Only a bounded whitelist of arithmetic AST nodes is allowed, and evaluation must reject unsupported or oversized expressions.",
        constraints=(
            "Support integers, variables, parentheses, unary minus, +, -, *, and //.",
            "Reject function calls, attributes, exponentiation, unknown variables, and expressions with more than max_nodes AST nodes.",
            "Return the same result as the reference interpreter on bounded inputs.",
        ),
        verifier=_verify_compute_bounded_evaluator,
    )


def _verify_compute_bounded_evaluator(function: Callable[..., Any], tree: ast.Module) -> VerificationResult:
    environments = [
        {"x": 3, "y": 2, "z": -1},
        {"x": -4, "y": 5, "z": 1},
    ]
    expressions = [
        "x + y * 2",
        "(x - y) // 2",
        "-z + x * y",
        "x // (y + 1)",
    ]
    passed = 0
    for env in environments:
        for expression in expressions:
            succeeded, actual = _invoke_candidate(function, expression, dict(env), 32)
            if not succeeded:
                return VerificationResult(
                    passed=False,
                    summary="supported expression crashed the candidate",
                    evidence_level="bounded-execution",
                    counterexample=Counterexample(
                        title="evaluator_exception",
                        description="A supported bounded expression should evaluate without crashing.",
                        payload={"expression": expression, "variables": env, "error": str(actual)},
                    ),
                    metrics={"passed_cases": passed, "total_cases": len(expressions) * len(environments) + 4},
                )
            expected = _bounded_eval_oracle(expression, env, 32)
            if actual != expected:
                return VerificationResult(
                    passed=False,
                    summary="bounded evaluator disagreed with the reference arithmetic interpreter",
                    evidence_level="bounded-execution",
                    counterexample=Counterexample(
                        title="evaluator_mismatch",
                        description="The evaluator must match the reference arithmetic semantics on bounded expressions.",
                        payload={"expression": expression, "variables": env, "expected": expected, "actual": actual},
                    ),
                    metrics={"passed_cases": passed, "total_cases": len(expressions) * len(environments) + 4},
                )
            passed += 1
    for expression in ["x ** 2", "abs(x)", "__import__('os')", "x + unknown"]:
        try:
            function(expression, {"x": 2}, 32)
        except ValueError:
            passed += 1
            continue
        except Exception as exc:
            return VerificationResult(
                passed=False,
                summary="unsupported expression raised the wrong error type",
                evidence_level="bounded-execution",
                counterexample=Counterexample(
                    title="unsupported_expression_wrong_error",
                    description="Unsupported syntax should raise ValueError rather than another exception.",
                    payload={"expression": expression, "error": str(exc)},
                ),
                metrics={"passed_cases": passed, "total_cases": len(expressions) * len(environments) + 4},
            )
        return VerificationResult(
            passed=False,
            summary="unsupported expression was accepted",
            evidence_level="bounded-execution",
            counterexample=Counterexample(
                title="unsupported_expression",
                description="The evaluator must reject syntax outside the approved grammar.",
                payload={"expression": expression},
            ),
            metrics={"passed_cases": passed, "total_cases": len(expressions) * len(environments) + 4},
        )
    return VerificationResult(
        passed=True,
        summary="evaluator matches the bounded arithmetic oracle and rejects unsupported syntax",
        evidence_level="bounded-execution + ast-guard",
        metrics={"passed_cases": passed, "total_cases": len(expressions) * len(environments) + 4},
    )


def _normalize_safe_path(base_dir: str, requested_path: str) -> str:
    if requested_path.startswith("/"):
        raise ValueError("absolute paths are forbidden")
    normalized_base = posixpath.normpath(base_dir)
    normalized_path = posixpath.normpath(posixpath.join(normalized_base, requested_path))
    if normalized_path != normalized_base and not normalized_path.startswith(normalized_base + "/"):
        raise ValueError("path escapes base directory")
    if not normalized_path.endswith(".txt"):
        raise ValueError("only .txt files are allowed")
    return normalized_path


def _invoke_candidate(function: Callable[..., Any], *args: Any) -> tuple[bool, Any]:
    try:
        return True, function(*args)
    except Exception as exc:  # noqa: BLE001 - verifier wants the concrete failure
        return False, exc


SQL_PATTERN = re.compile(
    r"^SELECT\s+(?P<columns>\*|[a-z_,\s]+)\s+FROM\s+rows(?:\s+WHERE\s+(?P<where_column>[a-z_]+)\s*(?P<where_op>=|>=|<=|>|<)\s*(?P<where_value>-?\d+))?(?:\s+LIMIT\s+(?P<limit>\d+))?$",
    re.IGNORECASE,
)


def _sql_oracle(query: str, rows: list[dict[str, int]]) -> list[dict[str, int]]:
    lowered = query.lower()
    if ";" in query or any(keyword in lowered for keyword in ("delete", "update", "insert", "drop", "alter", "create", "pragma")):
        raise ValueError("mutating or multi-statement SQL is forbidden")
    match = SQL_PATTERN.fullmatch(query.strip())
    if not match:
        raise ValueError("query does not match the supported grammar")
    columns_text = match.group("columns")
    columns = list(rows[0]) if columns_text == "*" else [column.strip() for column in columns_text.split(",")]
    for column in columns:
        if column not in rows[0]:
            raise ValueError("unknown selected column")
    filtered = [dict(row) for row in rows]
    where_column = match.group("where_column")
    if where_column:
        if where_column not in rows[0]:
            raise ValueError("unknown where column")
        where_value = int(match.group("where_value"))
        op = match.group("where_op")
        filtered = [row for row in filtered if _compare(row[where_column], op, where_value)]
    limit_text = match.group("limit")
    if limit_text is not None:
        filtered = filtered[: int(limit_text)]
    return [{column: row[column] for column in columns} for row in filtered]


def _compare(left: int, op: str, right: int) -> bool:
    if op == "=":
        return left == right
    if op == ">=":
        return left >= right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    if op == "<":
        return left < right
    raise ValueError(f"unsupported operator: {op}")


def _api_oracle(url: str, method: str, allowlist: list[str], responses: dict[str, str]) -> str:
    method = method.upper()
    if method != "GET":
        raise ValueError("only GET is allowed")
    parsed = urllib_parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("only https is allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("missing host")
    if host == "localhost":
        raise ValueError("localhost is forbidden")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError("private or loopback IP is forbidden")
        raise ValueError("bare IP hosts are forbidden")
    if host not in allowlist:
        raise ValueError("host is not on the allowlist")
    key = f"{method} {url}"
    if key not in responses:
        raise ValueError("no mocked response for request")
    return responses[key]


def _append_oracle(existing: str, new_entry: str, max_bytes: int) -> str:
    if "\0" in new_entry:
        raise ValueError("NUL bytes are forbidden")
    result = existing
    if result and not result.endswith("\n"):
        result += "\n"
    result += new_entry
    if len(result.encode("utf-8")) > max_bytes:
        raise ValueError("result exceeds byte budget")
    return result


def _pii_patterns() -> dict[str, re.Pattern[str]]:
    return {
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "phone": re.compile(r"\b\d{3}[- ]\d{3}[- ]\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "card": re.compile(r"\b(?:\d{4}-){3}\d{4}\b"),
    }


def _bounded_eval_oracle(expression: str, variables: dict[str, int], max_nodes: int) -> int:
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > max_nodes:
        raise ValueError("expression exceeds node budget")
    return _eval_node(tree.body, variables)


def _eval_node(node: ast.AST, variables: dict[str, int]) -> int:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise ValueError("unknown variable")
        return int(variables[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand, variables)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv)):
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise ValueError("division by zero")
        return left // right
    raise ValueError("unsupported syntax")
