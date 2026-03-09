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

def normalize_to_concept(term, concepts):
    term_lower = term.lower()

    for c in concepts:
        if term_lower == c.lower():
            return c

    for c in concepts:
        if term_lower in c.lower():
            return c

    for c in concepts:
        if c.lower() in term_lower:
            return c

    return term

def run_cs_cme(text):

    # 🔹 Preprocessing Layer
    text = preprocess_document(text)

    canonical_map = {}
    paragraphs = text.split("\n\n")
    full_graph = []
    all_nodes = {}
    all_edges = []

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
                    # 🔹 Remove invalid relation targets
                    clean_relations = []
                    for r in relations:
                        if r["target"].lower() not in {"which", "that", "who", "whom", "whose"}:
                            clean_relations.append(r)
                    
                    relations = clean_relations
                    # 🔹 IMPORTANT FIX:
                    # Add targets as concepts so edges survive merging
                    concepts = [term] + [r["target"] for r in relations]

                    graph = build_graph(
                        sentence_id=f"{p_id}_{s_id}",
                        concepts=concepts,
                        relations=relations,
                        descriptions=node_descriptions
                    )

                    # merge nodes
                    for node in graph["nodes"]:
                        nid = node["id"]

                        if nid not in all_nodes:
                            all_nodes[nid] = node
                        else:
                            all_nodes[nid]["frequency"] = all_nodes[nid].get("frequency",1) + 1

                    # merge edges
                    for edge in graph["edges"]:
                        all_edges.append(edge)
                    continue  # Skip normal processing

            # ==================================================
            # 🔹 PARENTHESIS ALIAS HANDLER (INTEGRATED)
            # ==================================================
            import re

            alias_pattern = re.findall(r'([A-Za-z0-9\s]+)\s*\(([^)]+)\)', sentence)

            alias_relations = []
            alias_concepts = []

            for main_term, alias in alias_pattern:

                main_term = main_term.strip()
                alias = alias.strip()

                # Remove leading articles
                main_term = re.sub(r'^(The|A|An)\s+', '', main_term, flags=re.IGNORECASE)

                alias_relations.append({
                    "source": main_term,
                    "target": alias,
                    "relation": "alias_of",
                    "negated": False
                })

                alias_concepts.extend([main_term, alias])

            # ==================================================
            # 🔹 NORMAL PROCESSING
            # ==================================================

            concepts = extract_concepts(sentence)

            # Paragraph topic initialization
            if s_id == 0 and concepts:
                context["paragraph_topic"] = concepts[0]
                context["last_subject"] = concepts[0]

            relations = extract_relations(sentence, context)

            # Merge alias concepts and relations
            concepts.extend(alias_concepts)
            relations.extend(alias_relations)

            # 🔹 Normalize relation nodes to existing concepts
            normalized_relations = []

            for r in relations:

                src = normalize_to_concept(r["source"], concepts)
                tgt = normalize_to_concept(r["target"], concepts)

                r["source"] = src
                r["target"] = tgt

                normalized_relations.append(r)

            relations = normalized_relations

            # If descriptive sentence (no relations but has concepts)
            if not relations and concepts:
                for c in concepts:
                    node_descriptions.setdefault(c, []).append(sentence)

                graph = build_graph(
                    sentence_id=f"{p_id}_{s_id}",
                    concepts=concepts,
                    relations=[],
                    descriptions=node_descriptions
                )

                full_graph.append(graph)
                continue

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

            # -------------------------------------------------
            # Normalize relation nodes using canonical mapping
            # -------------------------------------------------

            for r in relations:

                src_key = r["source"].lower()
                tgt_key = r["target"].lower()

                if src_key in canonical_map:
                    r["source"] = canonical_map[src_key]

                if tgt_key in canonical_map:
                    r["target"] = canonical_map[tgt_key]

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