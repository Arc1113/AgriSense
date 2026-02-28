from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(r"c:\Users\LENOVO\AgriSense\backend\models")
RESULTS_DIR = ROOT / "Agrisense_Results"
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_benchmark_records() -> Tuple[pd.DataFrame, pd.DataFrame]:
    records_summary: List[dict] = []
    records_raw: List[dict] = []

    benchmark_files = sorted(RESULTS_DIR.glob("**/benchmark_study_*.json"))
    for bf in benchmark_files:
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)

        run_label = bf.parent.name if bf.parent != RESULTS_DIR else "CPU"
        device_name = data.get("device_info", {}).get("model", "UnknownDevice")

        for row in data.get("results", []):
            model = row.get("model_name")
            variant = row.get("model_variant")
            delegate = row.get("delegate_type", "cpu")
            mean_ms = float(row["inference"]["mean_ms"])

            records_summary.append(
                {
                    "run_label": run_label,
                    "device": device_name,
                    "model": model,
                    "variant": variant,
                    "delegate": delegate,
                    "config": f"{model}-{variant}-{delegate}",
                    "mean_ms": mean_ms,
                }
            )

            for v in row.get("raw_inference_times_ms", []):
                records_raw.append(
                    {
                        "run_label": run_label,
                        "device": device_name,
                        "model": model,
                        "variant": variant,
                        "delegate": delegate,
                        "config": f"{model}-{variant}-{delegate}",
                        "inference_ms": float(v),
                    }
                )

    return pd.DataFrame(records_summary), pd.DataFrame(records_raw)


def load_test_eval_macro_f1() -> pd.DataFrame:
    eval_records: List[dict] = []
    eval_files = sorted(RESULTS_DIR.glob("**/test_eval_*.json"))

    for ef in eval_files:
        with open(ef, "r", encoding="utf-8") as f:
            data = json.load(f)

        run_label = ef.parent.name if ef.parent != RESULTS_DIR else "CPU"
        total_images = int(data.get("total_images", 0))

        eval_records.append(
            {
                "run_label": run_label,
                "model": data.get("model_name"),
                "variant": data.get("model_variant", "fp32"),
                "delegate": data.get("delegate_type", "cpu"),
                "macro_f1": float(data.get("macro_f1", 0.0)),
                "total_images": total_images,
                "is_valid": total_images > 0,
            }
        )

    return pd.DataFrame(eval_records)


def generate_figure9_boxplot(raw_df: pd.DataFrame) -> Path:
    out = FIG_DIR / "latency_boxplots.png"
    if raw_df.empty:
        plt.figure(figsize=(10, 4))
        plt.text(0.5, 0.5, "No benchmark raw latency data found", ha="center", va="center")
        plt.axis("off")
        plt.savefig(out, dpi=300, bbox_inches="tight")
        plt.close()
        return out

    order = (
        raw_df.groupby("config")["inference_ms"].mean().sort_values().index.tolist()
    )

    fig, ax = plt.subplots(figsize=(14, 6))
    box_data = [raw_df.loc[raw_df["config"] == c, "inference_ms"].tolist() for c in order]
    ax.boxplot(box_data, labels=order, showfliers=True)
    ax.set_title("Warm Inference Latency by Model/Variant/Delegate")
    ax.set_ylabel("Inference Latency (ms)")
    ax.set_xlabel("Configuration")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def generate_figure10_tradeoff(summary_df: pd.DataFrame, eval_df: pd.DataFrame) -> Path:
    out = FIG_DIR / "accuracy_latency_tradeoff.png"

    if summary_df.empty or eval_df.empty:
        plt.figure(figsize=(8, 5))
        plt.text(0.5, 0.5, "Missing benchmark or test-eval data", ha="center", va="center")
        plt.axis("off")
        plt.savefig(out, dpi=300, bbox_inches="tight")
        plt.close()
        return out

    merged = summary_df.merge(
        eval_df,
        on=["run_label", "model", "variant", "delegate"],
        how="inner",
        suffixes=("_bench", "_eval"),
    )

    valid = merged[merged["is_valid"]].copy()

    fig, ax = plt.subplots(figsize=(10, 6))

    if valid.empty:
        ax.text(
            0.5,
            0.5,
            "No valid test-set accuracy results yet\n(all exports currently have total_images = 0)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_xlabel("Mean Inference Latency (ms)")
        ax.set_ylabel("Macro-F1")
        ax.set_title("Trade-off: Macro-F1 vs Mean Inference Latency")
    else:
        for _, r in valid.iterrows():
            label = f"{r['model']}-{r['variant']}-{r['delegate']} ({r['run_label']})"
            ax.scatter(r["mean_ms"], r["macro_f1"], s=80)
            ax.annotate(label, (r["mean_ms"], r["macro_f1"]), xytext=(5, 4), textcoords="offset points", fontsize=8)

        ax.set_xlabel("Mean Inference Latency (ms)")
        ax.set_ylabel("Macro-F1")
        ax.set_title("Trade-off: Macro-F1 vs Mean Inference Latency")
        ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    summary_df, raw_df = load_benchmark_records()
    eval_df = load_test_eval_macro_f1()

    f9 = generate_figure9_boxplot(raw_df)
    f10 = generate_figure10_tradeoff(summary_df, eval_df)

    print(f"Generated: {f9}")
    print(f"Generated: {f10}")


if __name__ == "__main__":
    main()
