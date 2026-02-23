import os
import json
import nltk
import spacy

from concept_extractor import extract_concepts
from meaning_analyzer import extract_relations
from graph_builder import build_graph
from document_graph_builder import build_document_graph
from preprocessor import preprocess_document

nltk.download("punkt")
from nltk.tokenize import sent_tokenize

nlp = spacy.load("en_core_web_sm")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_INPUT_DIR = os.path.join(BASE_DIR, "test_inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_cs_cme(text):

    # 🔹 Preprocessing Layer
    text = preprocess_document(text)

    canonical_map = {}
    paragraphs = text.split("\n\n")
    full_graph = []

    # 🔹 Global description store
    node_descriptions = {}

    for p_id, paragraph in enumerate(paragraphs):

        context = {
            "last_subject": None,
            "paragraph_topic": None,
            "global_concepts": set()
        }

        sentences = sent_tokenize(paragraph)

        for s_id, sentence in enumerate(sentences):

            # ==================================================
            # 🔹 COLON DEFINITION HANDLER
            # ==================================================
            if ":" in sentence:
                left, right = sentence.split(":", 1)

                term = left.strip()
                definition = right.strip()

                # Only treat as definition if left side is short
                if len(term.split()) <= 5:

                    # Store definition
                    node_descriptions.setdefault(term, []).append(definition)

                    # Extract relations from definition
                    relations = extract_relations(definition, context)

                    # 🔹 Force subject to term
                    for r in relations:
                        r["source"] = term

                    # 🔹 IMPORTANT FIX:
                    # Add targets as concepts so edges survive merging
                    concepts = [term] + [r["target"] for r in relations]

                    graph = build_graph(
                        sentence_id=f"{p_id}_{s_id}",
                        concepts=concepts,
                        relations=relations,
                        descriptions=node_descriptions
                    )

                    full_graph.append(graph)
                    continue  # Skip normal processing


            # ==================================================
            # 🔹 NORMAL PROCESSING
            # ==================================================

            concepts = extract_concepts(sentence)

            # Paragraph topic initialization
            if s_id == 0 and concepts:
                context["paragraph_topic"] = concepts[0]
                context["last_subject"] = concepts[0]

            relations = extract_relations(sentence, context)

            # If descriptive sentence (no relations but has concepts)
            if not relations and concepts:
                for c in concepts:
                    node_descriptions.setdefault(c, []).append(sentence)

            # Canonical mapping
            normalized_concepts = []
            for concept in concepts:
                key = concept.lower()
                if key in canonical_map:
                    normalized_concepts.append(canonical_map[key])
                else:
                    canonical_map[key] = concept
                    normalized_concepts.append(concept)

            concepts = normalized_concepts

            graph = build_graph(
                sentence_id=f"{p_id}_{s_id}",
                concepts=concepts,
                relations=relations,
                descriptions=node_descriptions
            )

            full_graph.append(graph)

    return full_graph


if __name__ == "__main__":

    for file_name in sorted(os.listdir(TEST_INPUT_DIR)):
        if file_name.endswith(".txt"):

            input_path = os.path.join(TEST_INPUT_DIR, file_name)

            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()

            sentence_graph = run_cs_cme(text)
            document_graph = build_document_graph(sentence_graph)

            output_file = file_name.replace(".txt", ".json")
            output_path = os.path.join(OUTPUT_DIR, output_file)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(document_graph, f, indent=4)

            print(f"✅ Processed {file_name} → outputs/{output_file}")