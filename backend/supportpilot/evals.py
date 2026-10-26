"""Deterministic evals against evals/golden.jsonl.

  uv run python -m supportpilot.evals retrieval   # retrieval only: vector vs hybrid x k, no LLM
  uv run python -m supportpilot.evals robustness  # retrieval only: same intents, different phrasing
  uv run python -m supportpilot.evals agent       # full agent: citations, abstention, tools, answers

Each run prints Markdown tables (for the README) and writes per-case details to evals/results/.
"""

import asyncio
import json
import sys

from supportpilot import config
from supportpilot.agent import answer
from supportpilot.retrieval import build_retriever
from supportpilot.test_issuer import TestIssuer, linked_subjects, mcp_server

EVALS_DIR = config.REPO_ROOT / "evals"
RESULTS_DIR = EVALS_DIR / "results"
K_VALUES = [1, 2, 4, 8]
MODES = ["vector", "hybrid"]


def load_cases() -> list[dict]:
    with open(EVALS_DIR / "golden.jsonl") as f:
        return [json.loads(line) for line in f if line.strip()]


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def recall(retrieved: list[str], expected: list[str]) -> float:
    return len(set(retrieved) & set(expected)) / len(expected)


def run_retrieval(cases: list[dict]) -> None:
    # Retrieval is only scored on cases that have expected chunks.
    scored = [c for c in cases if c["expected_ids"]]
    rows, details = [], []
    for mode in MODES:
        row: dict = {"mode": mode}
        for k in K_VALUES:
            retriever = build_retriever(k=k, mode=mode)
            per_case = []
            for case in scored:
                ids = [r.node.node_id for r in retriever.retrieve(case["question"])]
                per_case.append(recall(ids, case["expected_ids"]))
                details.append({"mode": mode, "k": k, "id": case["id"], "retrieved": ids,
                                "recall": per_case[-1]})
            row[k] = mean(per_case)
        rows.append(row)

    write_details("retrieval.json", details)
    print(f"Recall@k over {len(scored)} golden cases with expected chunks:\n")
    print("| Retrieval | " + " | ".join(f"recall@{k}" for k in K_VALUES) + " |")
    print("|---|" + "---|" * len(K_VALUES))
    for row in rows:
        print(f"| {row['mode']} | " + " | ".join(f"{row[k]:.2f}" for k in K_VALUES) + " |")


def run_robustness(k: int = 4) -> None:
    """Same intents phrased differently (e.g. with typos): which retrieval mode holds up?"""
    with open(EVALS_DIR / "robustness.jsonl") as f:
        cases = [json.loads(line) for line in f if line.strip()]
    variants = list(dict.fromkeys(c["variant"] for c in cases))

    details = []
    print(f"Recall@{k} by phrasing variant ({len(cases) // len(variants)} intents each):\n")
    print("| Retrieval | " + " | ".join(variants) + " |")
    print("|---|" + "---|" * len(variants))
    for mode in MODES:
        retriever = build_retriever(k=k, mode=mode)
        by_variant: dict[str, list[float]] = {v: [] for v in variants}
        for case in cases:
            ids = [r.node.node_id for r in retriever.retrieve(case["question"])]
            by_variant[case["variant"]].append(recall(ids, case["expected_ids"]))
            details.append({"mode": mode, **case, "retrieved": ids, "recall": by_variant[case["variant"]][-1]})
        print(f"| {mode} | " + " | ".join(f"{mean(by_variant[v]):.2f}" for v in variants) + " |")
    write_details("robustness.json", details)


def check_answer(text: str, case: dict) -> bool:
    text = text.lower()
    return all(s.lower() in text for s in case["must_include"]) and not any(
        s.lower() in text for s in case["must_not_include"]
    )


async def run_agent(cases: list[dict]) -> None:
    # Each case's customer asks with a token from a throwaway issuer, through the real token check.
    with (
        TestIssuer() as issuer,
        mcp_server(issuer) as url,
        linked_subjects({c["customer_id"] for c in cases}) as subs,
    ):
        config.MCP_URL = url
        details = []
        for case in cases:
            details.append(await run_agent_case(case, issuer.mint(subs[case["customer_id"]])))
    report_agent(details)


async def run_agent_case(case: dict, token: str) -> dict:
    result = await answer(case["question"], token)
    expected, cited = set(case["expected_ids"]), set(result.citations)
    detail = {
        **case,
        **result.model_dump(),
        "answer_pass": check_answer(result.answer, case),
        "tools_pass": set(case["expected_tools"]) <= set(result.tools_called),
        # Citation precision only applies where the case has a correct source to cite.
        "citation_precision": len(cited & expected) / len(cited) if expected and cited else None,
        "cited_expected": bool(cited & expected) if expected else None,
        # No-info cases pass only if the agent cites nothing.
        "abstention_pass": not cited if case["category"] == "no-info" else None,
    }
    print(f"{case['id']}: answer={detail['answer_pass']} tools={detail['tools_pass']} "
          f"cited={result.citations}", file=sys.stderr)
    return detail


def report_agent(details: list[dict]) -> None:
    write_details("agent.json", details)

    def rate(key: str) -> str:
        values = [d[key] for d in details if d[key] is not None]
        return f"{mean([float(v) for v in values]):.2f} (n={len(values)})"

    print(f"\nAgent results over {len(details)} golden cases:\n")
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Citation precision (cited ids that are expected) | {rate('citation_precision')} |")
    print(f"| Cited at least one expected chunk | {rate('cited_expected')} |")
    print(f"| Abstention on no-info questions | {rate('abstention_pass')} |")
    print(f"| Tool accuracy (expected tools were called) | {rate('tools_pass')} |")
    print(f"| Answer checks (must / must not include) | {rate('answer_pass')} |")
    print(f"| Invalid citations (not retrieved) | {sum(len(d['invalid_citations']) for d in details)} |")

    print("\nFailures:")
    for d in details:
        failed = [k for k in ("answer_pass", "tools_pass", "cited_expected", "abstention_pass") if d[k] is False]
        if failed:
            print(f"- {d['id']} ({d['category']}): {', '.join(failed)}")


def write_details(name: str, details: list[dict]) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / name).write_text(json.dumps(details, indent=2, default=str))


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "retrieval"
    if command == "retrieval":
        run_retrieval(load_cases())
    elif command == "robustness":
        run_robustness()
    elif command == "agent":
        asyncio.run(run_agent(load_cases()))
    else:
        sys.exit(f"Unknown command: {command}")
