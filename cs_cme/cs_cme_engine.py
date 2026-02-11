import os
import json
import nltk
from concept_extractor import extract_concepts
from meaning_analyzer import extract_relations
from graph_builder import build_graph

nltk.download("punkt")
from nltk.tokenize import sent_tokenize


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_INPUT_DIR = os.path.join(BASE_DIR, "test_inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_cs_cme(text):
    paragraphs = text.split("\n\n")
    full_graph = []

    for p_id, paragraph in enumerate(paragraphs):
        context = {
            "last_subject": None,
            "paragraph_topic": None,
            "global_concepts": set()
        }

        sentences = sent_tokenize(paragraph)

        for s_id, sentence in enumerate(sentences):
            concepts = extract_concepts(sentence)

            # paragraph topic initialization
            if s_id == 0 and concepts:
                context["paragraph_topic"] = concepts[0]
                context["last_subject"] = concepts[0]

            relations = extract_relations(sentence, context)

            graph = build_graph(
                f"{p_id}_{s_id}",
                concepts,
                relations
            )

            full_graph.append(graph)

    return full_graph


if __name__ == "__main__":
    for file_name in sorted(os.listdir(TEST_INPUT_DIR)):
        if file_name.endswith(".txt"):
            input_path = os.path.join(TEST_INPUT_DIR, file_name)

            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()

            result = run_cs_cme(text)

            output_file = file_name.replace(".txt", ".json")
            output_path = os.path.join(OUTPUT_DIR, output_file)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4)

            print(f"✅ Processed {file_name} → outputs/{output_file}")
