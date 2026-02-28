"""
AgriSense RAG Pipeline Evaluation Script
=========================================
Runs the 100-case gold-standard test suite against the RAG pipeline and computes
research metrics for the Results & Discussion section:

Metrics computed:
  1. Grounded Response Rate (GRR) — % of responses that cite ≥1 doc_id
  2. Citation Precision (CP)        — % of sources citing actual KB documents
  3. Hallucination Rate (HR)        — % of responses containing hallucination keywords
  4. Keyword Hit Rate (KHR)         — % of expected keywords found in response
  5. Latency (P50, P95, Mean)       — per-component and total
  6. Ablation: +Reranker vs −Reranker
  7. Ablation: RAG vs LLM-only

Usage:
  # Full evaluation (RAG + reranker) — default
  python eval/run_evaluation.py

  # Ablation: no reranker
  python eval/run_evaluation.py --no-reranker

  # Ablation: LLM-only (no RAG retrieval)
  python eval/run_evaluation.py --no-rag

  # Run all 3 configurations automatically
  python eval/run_evaluation.py --all

  # Limit to N cases (for quick testing)
  python eval/run_evaluation.py --limit 10

Output:
  eval/results_<config>_<timestamp>.json   — per-case results
  eval/summary_<config>_<timestamp>.json   — aggregate metrics
  eval/results_comparison_<timestamp>.json  — side-by-side ablation (--all mode)

Requires: GROQ_API_KEY environment variable set.
"""

import os
import sys
import json
import time
import argparse
import statistics
from datetime import datetime
from pathlib import Path

# Add backend to path so we can import rag_agent directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# CRITICAL: prevent TF import chain deadlock
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['USE_TF'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CREWAI_TELEMETRY_OPT_OUT'] = 'true'
os.environ['OTEL_SDK_DISABLED'] = 'true'

from rag_agent import get_agri_advice


# ─── Metric helpers ──────────────────────────────────────────────────────

def check_keywords(text: str, keywords: list[str]) -> tuple[int, int, list[str]]:
    """Return (hits, total, matched_list)."""
    text_lower = text.lower()
    matched = [kw for kw in keywords if kw.lower() in text_lower]
    return len(matched), len(keywords), matched


def compute_hallucination_hits(text: str, hallucination_keywords: list[str]) -> tuple[int, list[str]]:
    """Return (count, matched_list) of hallucination keywords found."""
    text_lower = text.lower()
    matched = [kw for kw in hallucination_keywords if kw.lower() in text_lower]
    return len(matched), matched


def has_grounded_citation(sources: list[dict]) -> bool:
    """True if at least one source has a non-default doc_id."""
    for s in sources:
        doc_id = s.get("doc_id", "unknown")
        if doc_id and doc_id != "unknown":
            return True
    return False


def citation_precision(sources: list[dict]) -> float:
    """Fraction of source citations that have a real doc_id."""
    if not sources:
        return 0.0
    valid = sum(1 for s in sources if s.get("doc_id", "unknown") != "unknown")
    return valid / len(sources)


# ─── Single-case runner ──────────────────────────────────────────────────

def run_single_case(
    case: dict,
    rag_enabled: bool = True,
    use_reranker: bool = True,
) -> dict:
    """Run one test case and return result dict."""
    case_id = case["id"]
    disease = case["disease"]
    query = case["query"]

    print(f"  [{case_id}] {disease}: {query[:60]}...", end=" ", flush=True)

    try:
        result = get_agri_advice(
            disease_name=disease,
            weather_condition="Partly Cloudy",
            weather_forecast=None,
            rag_enabled=rag_enabled,
            use_reranker=use_reranker,
            use_cache=False,       # Always bypass cache for evaluation
        )

        # Build full text for keyword matching
        full_text = " ".join([
            result.get("action_plan", ""),
            result.get("safety_warning", ""),
            result.get("weather_advisory", ""),
            result.get("severity", ""),
        ])

        # Expected keyword analysis
        exp_hits, exp_total, exp_matched = check_keywords(full_text, case["expected_keywords"])
        khr = exp_hits / exp_total if exp_total else 1.0

        # Hallucination analysis
        hal_count, hal_matched = compute_hallucination_hits(full_text, case.get("hallucination_keywords", []))
        has_hal = hal_count > 0

        # Grounding / citation analysis
        sources = result.get("sources", [])
        grounded = has_grounded_citation(sources)
        cp = citation_precision(sources)

        # Latency
        latency = result.get("latency_breakdown", {})

        status = "pass" if khr >= 0.5 and not has_hal else "fail"
        symbol = "✅" if status == "pass" else "❌"
        print(f"{symbol}  KHR={khr:.0%}  HAL={hal_count}  latency={latency.get('total_ms', 0):.0f}ms")

        return {
            "case_id": case_id,
            "disease": disease,
            "category": case.get("category", ""),
            "status": status,
            "keyword_hit_rate": round(khr, 4),
            "expected_keywords_matched": exp_matched,
            "expected_keywords_missed": [k for k in case["expected_keywords"] if k not in exp_matched],
            "hallucination_count": hal_count,
            "hallucination_keywords_found": hal_matched,
            "grounded": grounded,
            "citation_precision": round(cp, 4),
            "num_sources": len(sources),
            "sources": sources,
            "latency": latency,
            "rag_enabled": result.get("rag_enabled", False),
            "severity_expected": case.get("expected_severity", ""),
            "severity_actual": result.get("severity", "Unknown"),
            "action_plan_preview": result.get("action_plan", "")[:200],
        }

    except Exception as e:
        print(f"💥 ERROR: {e}")
        return {
            "case_id": case_id,
            "disease": disease,
            "category": case.get("category", ""),
            "status": "error",
            "error": str(e),
            "keyword_hit_rate": 0.0,
            "hallucination_count": 0,
            "grounded": False,
            "citation_precision": 0.0,
            "num_sources": 0,
            "latency": {},
            "rag_enabled": False,
        }


# ─── Aggregate metrics ──────────────────────────────────────────────────

def compute_summary(results: list[dict], config_name: str) -> dict:
    """Compute aggregate metrics from a list of per-case results."""
    n = len(results)
    if n == 0:
        return {"config": config_name, "n": 0}

    # Filter out error cases for metric computation
    valid = [r for r in results if r["status"] != "error"]
    n_valid = len(valid)
    n_errors = n - n_valid

    # 1. Grounded Response Rate
    grounded_count = sum(1 for r in valid if r["grounded"])
    grr = grounded_count / n_valid if n_valid else 0

    # 2. Citation Precision (macro average)
    cp_values = [r["citation_precision"] for r in valid if r["num_sources"] > 0]
    cp_mean = statistics.mean(cp_values) if cp_values else 0

    # 3. Hallucination Rate
    hal_count = sum(1 for r in valid if r["hallucination_count"] > 0)
    hr = hal_count / n_valid if n_valid else 0

    # 4. Keyword Hit Rate (macro average)
    khr_values = [r["keyword_hit_rate"] for r in valid]
    khr_mean = statistics.mean(khr_values) if khr_values else 0

    # 5. Pass rate
    pass_count = sum(1 for r in valid if r["status"] == "pass")
    pass_rate = pass_count / n_valid if n_valid else 0

    # 6. Latency stats
    total_latencies = [r["latency"].get("total_ms", 0) for r in valid if r["latency"]]
    retrieval_latencies = [r["latency"].get("retrieval_ms", 0) for r in valid if r["latency"]]
    rerank_latencies = [r["latency"].get("rerank_ms", 0) for r in valid if r["latency"]]
    gen_latencies = [r["latency"].get("generation_ms", 0) for r in valid if r["latency"]]

    def lat_stats(values):
        if not values:
            return {"mean": 0, "p50": 0, "p95": 0, "min": 0, "max": 0}
        s = sorted(values)
        p95_idx = min(int(0.95 * len(s)), len(s) - 1)
        p50_idx = len(s) // 2
        return {
            "mean": round(statistics.mean(s), 1),
            "p50": round(s[p50_idx], 1),
            "p95": round(s[p95_idx], 1),
            "min": round(s[0], 1),
            "max": round(s[-1], 1),
        }

    # 7. Per-disease breakdown
    disease_breakdown = {}
    for r in valid:
        d = r["disease"]
        if d not in disease_breakdown:
            disease_breakdown[d] = {"n": 0, "pass": 0, "khr_sum": 0, "hal": 0, "grounded": 0}
        disease_breakdown[d]["n"] += 1
        disease_breakdown[d]["pass"] += 1 if r["status"] == "pass" else 0
        disease_breakdown[d]["khr_sum"] += r["keyword_hit_rate"]
        disease_breakdown[d]["hal"] += 1 if r["hallucination_count"] > 0 else 0
        disease_breakdown[d]["grounded"] += 1 if r["grounded"] else 0

    for d, v in disease_breakdown.items():
        v["pass_rate"] = round(v["pass"] / v["n"], 4) if v["n"] else 0
        v["khr_mean"] = round(v["khr_sum"] / v["n"], 4) if v["n"] else 0
        v["hal_rate"] = round(v["hal"] / v["n"], 4) if v["n"] else 0
        v["grr"] = round(v["grounded"] / v["n"], 4) if v["n"] else 0
        del v["khr_sum"]

    # 8. Per-category breakdown
    category_breakdown = {}
    for r in valid:
        c = r.get("category", "unknown")
        if c not in category_breakdown:
            category_breakdown[c] = {"n": 0, "pass": 0, "khr_sum": 0}
        category_breakdown[c]["n"] += 1
        category_breakdown[c]["pass"] += 1 if r["status"] == "pass" else 0
        category_breakdown[c]["khr_sum"] += r["keyword_hit_rate"]

    for c, v in category_breakdown.items():
        v["pass_rate"] = round(v["pass"] / v["n"], 4) if v["n"] else 0
        v["khr_mean"] = round(v["khr_sum"] / v["n"], 4) if v["n"] else 0
        del v["khr_sum"]

    return {
        "config": config_name,
        "timestamp": datetime.utcnow().isoformat(),
        "total_cases": n,
        "valid_cases": n_valid,
        "error_cases": n_errors,
        "aggregate_metrics": {
            "grounded_response_rate": round(grr, 4),
            "citation_precision_mean": round(cp_mean, 4),
            "hallucination_rate": round(hr, 4),
            "keyword_hit_rate_mean": round(khr_mean, 4),
            "pass_rate": round(pass_rate, 4),
        },
        "latency": {
            "total": lat_stats(total_latencies),
            "retrieval": lat_stats(retrieval_latencies),
            "rerank": lat_stats(rerank_latencies),
            "generation": lat_stats(gen_latencies),
        },
        "per_disease": disease_breakdown,
        "per_category": category_breakdown,
    }


# ─── Main runner ─────────────────────────────────────────────────────────

def run_evaluation(
    test_cases: list[dict],
    config_name: str,
    rag_enabled: bool = True,
    use_reranker: bool = True,
    limit: int | None = None,
) -> tuple[list[dict], dict]:
    """Run full evaluation and return (per_case_results, summary)."""
    cases = test_cases[:limit] if limit else test_cases
    n = len(cases)

    print(f"\n{'='*70}")
    print(f"  AgriSense RAG Evaluation — {config_name}")
    print(f"  Cases: {n}  |  RAG: {rag_enabled}  |  Reranker: {use_reranker}")
    print(f"{'='*70}\n")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{n}]", end=" ")
        result = run_single_case(case, rag_enabled=rag_enabled, use_reranker=use_reranker)
        results.append(result)

        # Rate-limit: avoid Groq quota (30 req/min on free tier)
        if i < n:
            time.sleep(2.5)

    summary = compute_summary(results, config_name)

    # Print summary
    agg = summary["aggregate_metrics"]
    lat = summary["latency"]["total"]
    print(f"\n{'─'*70}")
    print(f"  SUMMARY — {config_name}")
    print(f"{'─'*70}")
    print(f"  Grounded Response Rate (GRR) : {agg['grounded_response_rate']:.1%}")
    print(f"  Citation Precision (CP)      : {agg['citation_precision_mean']:.1%}")
    print(f"  Hallucination Rate (HR)      : {agg['hallucination_rate']:.1%}")
    print(f"  Keyword Hit Rate (KHR)       : {agg['keyword_hit_rate_mean']:.1%}")
    print(f"  Pass Rate                    : {agg['pass_rate']:.1%}")
    print(f"  Latency Total (P50/P95)      : {lat['p50']:.0f}ms / {lat['p95']:.0f}ms")
    print(f"  Errors                       : {summary['error_cases']}/{summary['total_cases']}")
    print(f"{'─'*70}\n")

    return results, summary


def save_results(results: list[dict], summary: dict, config_name: str, eval_dir: Path):
    """Save per-case results and summary JSON files."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    results_path = eval_dir / f"results_{config_name}_{ts}.json"
    summary_path = eval_dir / f"summary_{config_name}_{ts}.json"

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"  📄 Results: {results_path}")
    print(f"  📄 Summary: {summary_path}")
    
    return results_path, summary_path


def main():
    parser = argparse.ArgumentParser(description="AgriSense RAG Evaluation")
    parser.add_argument("--no-reranker", action="store_true", help="Ablation: disable cross-encoder reranking")
    parser.add_argument("--no-rag", action="store_true", help="Ablation: disable RAG retrieval (LLM-only)")
    parser.add_argument("--all", action="store_true", help="Run all 3 configs (full, no-reranker, no-rag)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases to run")
    parser.add_argument("--test-suite", type=str, default=None, help="Path to test suite JSON")
    args = parser.parse_args()

    # Check GROQ_API_KEY
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not set. Export it before running.")
        sys.exit(1)

    # Locate test suite
    eval_dir = Path(__file__).resolve().parent
    suite_path = Path(args.test_suite) if args.test_suite else eval_dir / "test_suite.json"
    
    if not suite_path.exists():
        print(f"❌ Test suite not found: {suite_path}")
        sys.exit(1)

    with open(suite_path, "r", encoding="utf-8") as f:
        suite = json.load(f)
    
    test_cases = suite["test_cases"]
    print(f"📋 Loaded {len(test_cases)} test cases from {suite_path.name}")

    if args.all:
        # Run all three configurations
        configs = [
            ("rag_full", True, True),
            ("rag_no_reranker", True, False),
            ("llm_only", False, True),
        ]
        all_summaries = {}
        for config_name, rag_on, rerank_on in configs:
            results, summary = run_evaluation(
                test_cases, config_name, 
                rag_enabled=rag_on, use_reranker=rerank_on,
                limit=args.limit,
            )
            save_results(results, summary, config_name, eval_dir)
            all_summaries[config_name] = summary["aggregate_metrics"]
            all_summaries[f"{config_name}_latency"] = summary["latency"]

        # Save comparison
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        comparison_path = eval_dir / f"results_comparison_{ts}.json"
        with open(comparison_path, "w", encoding="utf-8") as f:
            json.dump(all_summaries, f, indent=2, ensure_ascii=False)
        
        # Print comparison table
        print(f"\n{'='*70}")
        print(f"  ABLATION COMPARISON")
        print(f"{'='*70}")
        print(f"  {'Metric':<30} {'RAG+Reranker':>14} {'RAG Only':>14} {'LLM Only':>14}")
        print(f"  {'─'*72}")
        for metric in ["grounded_response_rate", "citation_precision_mean", "hallucination_rate", "keyword_hit_rate_mean", "pass_rate"]:
            vals = [all_summaries.get(c, {}).get(metric, 0) for c, _, _ in configs]
            label = metric.replace("_", " ").title()
            print(f"  {label:<30} {vals[0]:>13.1%} {vals[1]:>13.1%} {vals[2]:>13.1%}")
        
        for lat_key in ["total", "retrieval", "rerank", "generation"]:
            vals = [all_summaries.get(f"{c}_latency", {}).get(lat_key, {}).get("p50", 0) for c, _, _ in configs]
            label = f"Latency P50 {lat_key}"
            print(f"  {label:<30} {vals[0]:>12.0f}ms {vals[1]:>12.0f}ms {vals[2]:>12.0f}ms")

        print(f"\n  📄 Comparison: {comparison_path}")

    else:
        # Single configuration
        if args.no_rag:
            config_name = "llm_only"
            rag_enabled, use_reranker = False, True
        elif args.no_reranker:
            config_name = "rag_no_reranker"
            rag_enabled, use_reranker = True, False
        else:
            config_name = "rag_full"
            rag_enabled, use_reranker = True, True

        results, summary = run_evaluation(
            test_cases, config_name,
            rag_enabled=rag_enabled, use_reranker=use_reranker,
            limit=args.limit,
        )
        save_results(results, summary, config_name, eval_dir)


if __name__ == "__main__":
    main()
