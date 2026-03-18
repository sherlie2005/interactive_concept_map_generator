"""
Document Graph Builder – orchestrates the full CS-CME pipeline.

Pipeline:
  Input text
    → Preprocessing
    → Heading detection
    → Concept extraction
    → Context-aware meaning analysis (relation extraction)
    → Graph construction
    → Importance ranking & pruning
    → Community detection
    → JSON output
"""

from typing import Dict, List, Optional, Tuple

import spacy

from preprocessor import preprocess, extract_text_from_pdf
from heading_segmenter import segment_by_headings, get_heading_edges, HeadingNode
from concept_extractor import extract_concepts
from meaning_analyzer import MeaningAnalyzer
from formula_extractor import extract_formulas
from graph_builder import (
    build_graph,
    rank_concepts,
    prune_graph,
    detect_communities,
    connect_to_root,
    graph_to_json,
    filter_low_value_nodes,
)
from utils import MAX_CONCEPTS


def _load_nlp():
    """Load the spaCy English model."""
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        from spacy.cli import download
        download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")
    # Increase max length for longer documents
    nlp.max_length = 2_000_000
    return nlp


# Module-level lazy loader
_nlp_instance = None


def get_nlp():
    global _nlp_instance
    if _nlp_instance is None:
        _nlp_instance = _load_nlp()
    return _nlp_instance


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_text(raw_text: str) -> Dict:
    """
    Run the full CS-CME pipeline on raw text.

    Returns
    -------
    dict with keys:
        concept_map : dict   – the final JSON (nodes + edges)
        warnings    : list[str]
        stats       : dict   – summary statistics
    """
    nlp = get_nlp()

    # 1. Preprocess
    prep = preprocess(raw_text, nlp)
    cleaned_text = prep["cleaned_text"]
    warnings = list(prep["warnings"])

    # NEW: extract formulas from the entire document
    document_formulas = extract_formulas(cleaned_text)

    # 2. Heading segmentation (separates headings from body sentences)
    root_node, flat_headings = segment_by_headings(cleaned_text)
    heading_edges = get_heading_edges(root_node)

    # Collect only non-heading sentences from the heading tree
    # This prevents heading text from being merged into adjacent sentences
    def _collect_sentences(node: HeadingNode) -> list:
        sents = []
        for s in node.sentences:
            sents.append(s)
        for child in node.children:
            sents.extend(_collect_sentences(child))
        return sents

    raw_body_sentences = _collect_sentences(root_node)

    # Re-segment each line through spaCy for proper sentence boundaries
    sentences = []
    for line in raw_body_sentences:
        doc = nlp(line)
        for sent in doc.sents:
            s = sent.text.strip()
            if s:
                sentences.append(s)

    if not sentences:
        return {
            "concept_map": {"nodes": [], "edges": []},
            "warnings": warnings + ["No sentences found in input."],
            "stats": {},
        }

    # 3. Concept extraction
    concepts, frequency = extract_concepts(sentences, nlp)

    # Also count heading concepts in frequency
    for h in flat_headings:
        frequency[h] = frequency.get(h, 0) + 2  # heading boost

    # === NEW: Dynamic Document Title (your #4 request) ===
    if flat_headings:
        document_title = flat_headings[0]
    elif concepts:
        document_title = max(concepts, key=lambda c: frequency.get(c, 0))
    else:
        document_title = "Document Overview"

    # Update root and rebuild edges
    root_node.title = document_title
    heading_edges = get_heading_edges(root_node)

    # Also boost frequency of the title
    frequency[document_title] = frequency.get(document_title, 0) + 5

    # 4. Context-aware meaning analysis
    analyzer = MeaningAnalyzer(nlp)
    relations, descriptions, formulas = analyzer.analyze_sentences(sentences)

    # Merge regex-detected formulas so none are missed
    for f in document_formulas:
        added = False
        for concept in list(formulas.keys()):
            if concept.lower() in f.lower():
                formulas.setdefault(concept, []).append(f)
                added = True
        if not added:
            formulas.setdefault(document_title, []).append(f)

    # 5. Build graph
    graph = build_graph(relations, frequency, descriptions, formulas, heading_edges)

    # 6. Also add concepts that have no relations but are significant
    # 6. Add standalone concepts ONLY if frequency is high
    FREQ_THRESHOLD = 3

    for concept in concepts:
        if concept not in graph and frequency.get(concept, 0) >= FREQ_THRESHOLD:
            graph.add_node(
                concept,
                frequency=frequency.get(concept, 1),
                descriptions=descriptions.get(concept, []),
                formulas=formulas.get(concept, []),
                cluster=-1,
            )

    #7. Remove weak isolated nodes
    graph = filter_low_value_nodes(graph, frequency, freq_threshold=3, document_title=document_title)

    # 8. Connect orphans to document_root
    graph = connect_to_root(graph, document_title)

    # 9. Importance ranking
    scores = rank_concepts(graph, heading_concepts=flat_headings)

    # 10. Prune to top N concepts
    graph = prune_graph(graph, scores, max_concepts=MAX_CONCEPTS, document_title=document_title)

    # Re-connect after pruning
    graph = connect_to_root(graph, document_title)

    # Ensure the dynamic title keeps detected formulas
    if document_title in graph and document_title in formulas:
        graph.nodes[document_title]["formulas"] = formulas[document_title]
        
    # 11. Community detection
    clusters = detect_communities(graph)
    for node, cluster_id in clusters.items():
        if node in graph:
            graph.nodes[node]["cluster"] = cluster_id

    # 12. Generate JSON
    concept_map = graph_to_json(graph)

    # Stats
    stats = {
        "total_sentences": len(sentences),
        "total_concepts_extracted": len(concepts),
        "total_relations_extracted": len(relations),
        "concepts_in_map": len(concept_map["nodes"]),
        "edges_in_map": len(concept_map["edges"]),
        "communities_detected": len(set(clusters.values())) if clusters else 0,
        "headings_found": len(flat_headings),
    }

    return {
        "concept_map": concept_map,
        "warnings": warnings,
        "stats": stats,
    }


def process_pdf(pdf_bytes: bytes) -> Dict:
    """
    Extract text from a PDF and run the CS-CME pipeline.
    """
    text, pdf_warnings = extract_text_from_pdf(pdf_bytes)
    if not text.strip():
        return {
            "concept_map": {"nodes": [], "edges": []},
            "warnings": pdf_warnings + ["Could not extract text from PDF."],
            "stats": {},
        }

    result = process_text(text)
    result["warnings"] = pdf_warnings + result.get("warnings", [])
    return result
