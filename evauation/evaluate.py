"""
Evaluation module for the CS-CME engine.

Compares predicted concept-map relations against gold-standard annotations
and computes Precision, Recall, and F1 Score.

Usage:
    python evaluate.py
    python evaluate.py --gold gold/sample.json --pred predictions/sample.json
"""

import json
import os
import sys
import argparse
from typing import Dict, List, Set, Tuple


def load_relations(filepath: str) -> Set[Tuple[str, str, str]]:
    """
    Load relations from a JSON file.

    Expected format (same as concept_map output):
    {
      "edges": [
        {"source": "...", "target": "...", "relation": "..."},
        ...
      ]
    }

    Returns a set of (source_lower, relation, target_lower) tuples.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support both top-level edges and nested concept_map.edges
    edges = data.get("edges", [])
    if not edges and "concept_map" in data:
        edges = data["concept_map"].get("edges", [])

    relations: Set[Tuple[str, str, str]] = set()
    for edge in edges:
        src = edge.get("source", "").strip().lower()
        tgt = edge.get("target", "").strip().lower()
        rel = edge.get("relation", "").strip().lower()
        if src and tgt and rel:
            # Skip structural root edges – they are auto-generated, not semantic
            if src in ("document_root", "document root"):
                continue
            relations.add((src, rel, tgt))

    return relations


def evaluate(
    gold_relations: Set[Tuple[str, str, str]],
    pred_relations: Set[Tuple[str, str, str]],
) -> Dict:
    """
    Compute evaluation metrics.

    Returns dict with: TP, FP, FN, Precision, Recall, F1.
    """
    true_positives  = gold_relations & pred_relations
    false_positives = pred_relations - gold_relations
    false_negatives = gold_relations - pred_relations

    tp = len(true_positives)
    fp = len(false_positives)
    fn = len(false_negatives)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "tp_details": sorted(true_positives),
        "fp_details": sorted(false_positives),
        "fn_details": sorted(false_negatives),
    }


def print_report(metrics: Dict):
    """Pretty-print the evaluation report."""
    print("=" * 50)
    print("  CS-CME Evaluation Report")
    print("=" * 50)
    print(f"  True Positives:  {metrics['true_positives']}")
    print(f"  False Positives: {metrics['false_positives']}")
    print(f"  False Negatives: {metrics['false_negatives']}")
    print("-" * 50)
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1 Score:  {metrics['f1_score']:.4f}")
    print("=" * 50)

    if metrics["tp_details"]:
        print("\n  Correct relations (True Positives):")
        for src, rel, tgt in metrics["tp_details"]:
            print(f"    {src}  --[{rel}]-->  {tgt}")

    if metrics["fp_details"]:
        print("\n  Spurious relations (False Positives):")
        for src, rel, tgt in metrics["fp_details"]:
            print(f"    {src}  --[{rel}]-->  {tgt}")

    if metrics["fn_details"]:
        print("\n  Missing relations (False Negatives):")
        for src, rel, tgt in metrics["fn_details"]:
            print(f"    {src}  --[{rel}]-->  {tgt}")


def run_all_evaluations(gold_dir: str, pred_dir: str):
    """
    Evaluate all matching files in gold/ and predictions/ directories.
    """
    gold_files = sorted(f for f in os.listdir(gold_dir) if f.endswith(".json"))
    if not gold_files:
        print(f"No gold-standard JSON files found in {gold_dir}/")
        return

    total_tp = 0
    total_fp = 0
    total_fn = 0

    for gf in gold_files:
        gold_path = os.path.join(gold_dir, gf)
        pred_path = os.path.join(pred_dir, gf)

        if not os.path.exists(pred_path):
            print(f"\n[SKIP] No prediction file for {gf}")
            continue

        print(f"\n--- Evaluating: {gf} ---")
        gold_rels = load_relations(gold_path)
        pred_rels = load_relations(pred_path)

        metrics = evaluate(gold_rels, pred_rels)
        print_report(metrics)

        total_tp += metrics["true_positives"]
        total_fp += metrics["false_positives"]
        total_fn += metrics["false_negatives"]

    # Aggregate
    if total_tp + total_fp + total_fn > 0:
        agg_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        agg_recall    = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        agg_f1        = (2 * agg_precision * agg_recall / (agg_precision + agg_recall)
                         if (agg_precision + agg_recall) > 0 else 0.0)

        print("\n" + "=" * 50)
        print("  AGGREGATE RESULTS")
        print("=" * 50)
        print(f"  Total TP: {total_tp}  |  Total FP: {total_fp}  |  Total FN: {total_fn}")
        print(f"  Precision: {agg_precision:.4f}")
        print(f"  Recall:    {agg_recall:.4f}")
        print(f"  F1 Score:  {agg_f1:.4f}")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="CS-CME Evaluation Script")
    parser.add_argument("--gold", type=str, help="Path to gold-standard JSON file")
    parser.add_argument("--pred", type=str, help="Path to prediction JSON file")
    parser.add_argument(
        "--gold-dir", type=str,
        default=os.path.join(os.path.dirname(__file__), "gold"),
        help="Directory with gold-standard files (default: gold/)"
    )
    parser.add_argument(
        "--pred-dir", type=str,
        default=os.path.join(os.path.dirname(__file__), "predictions"),
        help="Directory with prediction files (default: predictions/)"
    )

    args = parser.parse_args()

    if args.gold and args.pred:
        # Single-file evaluation
        gold_rels = load_relations(args.gold)
        pred_rels = load_relations(args.pred)
        metrics = evaluate(gold_rels, pred_rels)
        print_report(metrics)
    else:
        # Batch evaluation
        run_all_evaluations(args.gold_dir, args.pred_dir)


if __name__ == "__main__":
    main()
