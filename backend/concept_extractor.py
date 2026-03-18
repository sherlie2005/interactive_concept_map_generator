"""
Concept Extractor module for the CS-CME engine.

Responsibilities:
  - Extract noun-phrase concepts from spaCy-parsed sentences
  - Keep the longest overlapping noun phrase
  - Normalize and filter concepts
  - Track concept frequency
"""

from typing import Dict, List, Set, Tuple

import spacy
from spacy.tokens import Doc, Span

from utils import normalize_concept, is_valid_concept


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def _get_noun_phrases(doc: Doc) -> List[Span]:
    """Return all noun chunks from the document."""
    return list(doc.noun_chunks)


def _get_compound_phrases(doc: Doc) -> List[str]:
    """
    Walk the dependency tree to build compound noun phrases that spaCy's
    noun_chunks might miss (e.g. "entity relationship diagram").
    """
    phrases: List[str] = []
    seen_indices: Set[int] = set()

    for token in doc:
        if token.dep_ in ("compound", "amod") and token.head.pos_ in ("NOUN", "PROPN"):
            if token.i in seen_indices:
                continue
            # Collect the full compound chain
            chain = _collect_compound_chain(token.head)
            if len(chain) > 1:
                phrase_text = " ".join(t.text for t in chain)
                phrases.append(phrase_text)
                for t in chain:
                    seen_indices.add(t.i)

    return phrases


def _collect_compound_chain(head_token) -> list:
    """
    Given a head noun, collect all its left-side compound / amod children
    plus the head itself, in document order.
    """
    children = []
    for child in head_token.children:
        if child.dep_ in ("compound", "amod") and child.i < head_token.i:
            # Recursively collect compounds of compounds
            children.extend(_collect_compound_chain(child))
    children.append(head_token)
    # Also collect right-side compound (rare but possible)
    for child in head_token.children:
        if child.dep_ in ("compound",) and child.i > head_token.i:
            children.append(child)
    children.sort(key=lambda t: t.i)
    return children


def _keep_longest_phrases(raw_phrases: List[str]) -> List[str]:
    """
    Remove shorter phrases that are substrings of longer ones.
    Also filters obvious fragments (What", The, Also Referred, etc.)
    """
    # Normalise for comparison
    normed = [(p, p.lower()) for p in raw_phrases]
    # Sort longest first
    normed.sort(key=lambda x: -len(x[1]))

    kept: List[str] = []
    kept_lower: List[str] = []
    for original, lower in normed:
        # Skip obvious noisy fragments (general rule)
        if lower in {"what", "the", "also", "referred", "to", "common", "tool", "type", "upfront"}:
            continue

        # Check if this phrase is a substring of an already-kept phrase
        is_sub = False
        for kl in kept_lower:
            if lower in kl and lower != kl:
                is_sub = True
                break
        if not is_sub:
            kept.append(original)
            kept_lower.append(lower)

    return kept


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_concepts(
    sentences: List[str],
    nlp: spacy.language.Language,
) -> Tuple[List[str], Dict[str, int]]:
    """
    Extract and normalise concepts from a list of sentences.

    Returns
    -------
    concepts : list[str]
        Unique normalised concept strings.
    frequency : dict[str, int]
        Concept -> occurrence count.
    """
    raw_phrases: List[str] = []

    for sent_text in sentences:
        doc = nlp(sent_text)

        # 1. spaCy noun chunks
        for chunk in _get_noun_phrases(doc):
            raw_phrases.append(chunk.text)

        # 2. Compound phrases from dependency tree
        raw_phrases.extend(_get_compound_phrases(doc))

    # Normalize all phrases
    normed_map: Dict[str, str] = {}  # normalised -> first raw
    for rp in raw_phrases:
        n = normalize_concept(rp)
        if n and is_valid_concept(n):
            normed_map.setdefault(n, rp)

    # Count frequencies (case-insensitive)
    freq: Dict[str, int] = {}
    for rp in raw_phrases:
        n = normalize_concept(rp)
        if n and n in normed_map:
            freq[n] = freq.get(n, 0) + 1

    # Keep longest non-overlapping phrases
    unique_concepts = _keep_longest_phrases(list(normed_map.keys()))

    # General cleanup - remove very short or quoted fragments
    unique_concepts = [c for c in unique_concepts if len(c) > 4 and not c.startswith('"')]

    # Rebuild freq dict with only kept concepts
    final_freq = {c: freq.get(c, 1) for c in unique_concepts}

    return unique_concepts, final_freq


def extract_concepts_from_doc(
    doc: Doc,
) -> List[str]:
    """
    Extract concept strings from a single spaCy Doc (used by meaning_analyzer).
    Returns raw normalised concept strings found in the doc.
    """
    phrases: List[str] = []
    for chunk in doc.noun_chunks:
        n = normalize_concept(chunk.text)
        if n and is_valid_concept(n):
            phrases.append(n)

    for phrase_text in _get_compound_phrases(doc):
        n = normalize_concept(phrase_text)
        if n and is_valid_concept(n):
            if n not in phrases:
                phrases.append(n)

    return phrases
