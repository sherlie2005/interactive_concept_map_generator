import json
import os


def load_edges(file_path):
    """
    Load relations from a graph JSON file.
    Works for both outputs and gold files.
    """

    relations = set()

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for edge in data.get("edges", []):
        relations.add((
            edge["source"].strip().lower(),
            edge["relation"].split("_")[0].strip().lower(),
            edge["target"].strip().lower()
        ))

    return relations


def evaluate_all(outputs_dir, gold_dir):

    total_tp = 0
    total_fp = 0
    total_fn = 0

    for file in os.listdir(outputs_dir):

        if not file.endswith(".json"):
            continue

        output_file = os.path.join(outputs_dir, file)
        gold_file = os.path.join(gold_dir, file)

        if not os.path.exists(gold_file):
            print(f"Skipping {file} (no gold file)")
            continue

        extracted = load_edges(output_file)
        gold = load_edges(gold_file)

        tp = extracted & gold
        fp = extracted - gold
        fn = gold - extracted

        total_tp += len(tp)
        total_fp += len(fp)
        total_fn += len(fn)

        precision = len(tp) / len(extracted) if extracted else 0
        recall = len(tp) / len(gold) if gold else 0
        f1 = (2 * precision * recall / (precision + recall)
              if precision + recall else 0)

        print(f"\n===== {file} =====")
        print("True Positives:", len(tp))
        print("False Positives:", len(fp))
        print("False Negatives:", len(fn))
        print("Precision:", round(precision, 3))
        print("Recall:", round(recall, 3))
        print("F1 Score:", round(f1, 3))

    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0
    overall_f1 = (2 * overall_precision * overall_recall /
                  (overall_precision + overall_recall)
                  if overall_precision + overall_recall else 0)

    print("\n===== OVERALL METRICS =====")
    print("Overall Precision:", round(overall_precision, 3))
    print("Overall Recall:", round(overall_recall, 3))
    print("Overall F1 Score:", round(overall_f1, 3))


if __name__ == "__main__":

    outputs_dir = "../outputs"
    gold_dir = "../gold"

    evaluate_all(outputs_dir, gold_dir)