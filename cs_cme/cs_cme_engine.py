import os
import json
import nltk
from concept_extractor import extract_concepts
from meaning_analyzer import extract_relations
from graph_builder import build_graph

nltk.download('punkt')
from nltk.tokenize import sent_tokenize

# 🔹 BASE DIRECTORY = cs_cme folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(BASE_DIR, "test_input.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "output.json")

def run_cs_cme(text):
    sentences = sent_tokenize(text)
    full_graph = []

    for idx, sentence in enumerate(sentences):
        concepts = extract_concepts(sentence)
        relations = extract_relations(sentence)
        graph = build_graph(idx, concepts, relations)
        full_graph.append(graph)

    return full_graph


if __name__ == "__main__":
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    result = run_cs_cme(text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print("✅ CS-CME processing completed. Output saved to cs_cme/output.json")
