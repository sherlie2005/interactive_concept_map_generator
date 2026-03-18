"""
Meaning Analyzer module for the CS-CME engine.

Responsibilities:
  - Context-aware sentence parsing (pronoun resolution)
  - Relation extraction (SVO triples mapped to allowed relation types)
  - Relative-clause resolution
  - Multi-relation sentence handling
  - Description fallback (store sentence on node when relation is uncertain)
  - Formula detection
"""

from typing import Dict, List, Optional, Set, Tuple

import spacy
from spacy.tokens import Doc, Token

from utils import (
    ALLOWED_RELATIONS,
    VERB_RELATION_MAP,
    PREP_RELATION_MAP,
    normalize_concept,
    is_valid_concept,
    detect_formulas,
)
from concept_extractor import extract_concepts_from_doc


# ---------------------------------------------------------------------------
# Context tracker
# ---------------------------------------------------------------------------

class ContextTracker:
    """Track discourse-level context variables for pronoun resolution."""

    def __init__(self):
        self.last_subject: Optional[str] = None
        self.paragraph_topic: Optional[str] = None
        self.global_concepts: Set[str] = set()

    def update_subject(self, subject: str):
        self.last_subject = subject

    def update_paragraph_topic(self, topic: str):
        self.paragraph_topic = topic

    def add_global_concept(self, concept: str):
        self.global_concepts.add(concept)

    def resolve_pronoun(self, pronoun_text: str) -> Optional[str]:
        """Resolve an anaphoric pronoun to the most recent subject.
        Only resolves true anaphoric pronouns, NOT relative pronouns."""
        low = pronoun_text.lower().strip()
        if low in ("it", "this", "its"):
            return self.last_subject
        if low in ("they", "these", "those", "them", "their"):
            return self.last_subject
        return None


# ---------------------------------------------------------------------------
# Relation extraction helpers
# ---------------------------------------------------------------------------

def _find_subject(verb: Token) -> Optional[Token]:
    """Find the nominal subject of a verb."""
    for child in verb.children:
        if child.dep_ in ("nsubj", "nsubjpass"):
            return child
    # If verb is in a relative clause, walk up
    if verb.dep_ == "relcl":
        return verb.head
    return None


def _find_objects(verb: Token) -> List[Token]:
    """Find direct / prepositional objects of a verb."""
    objs: List[Token] = []
    for child in verb.children:
        if child.dep_ in ("dobj", "attr", "oprd"):
            objs.append(child)
        elif child.dep_ == "prep":
            for grandchild in child.children:
                if grandchild.dep_ == "pobj":
                    objs.append(grandchild)
    return objs


def _get_full_phrase(token: Token) -> str:
    """Reconstruct the full noun-phrase around *token* using its subtree."""
    # Use the noun chunk that contains this token if available
    doc = token.doc
    for chunk in doc.noun_chunks:
        if chunk.start <= token.i < chunk.end:
            return chunk.text

    # Fallback: collect compound + amod children on the left + token
    parts = []
    for child in token.children:
        if child.dep_ in ("compound", "amod") and child.i < token.i:
            parts.append(child.text)
    parts.append(token.text)
    # right compounds (rare)
    for child in token.children:
        if child.dep_ == "compound" and child.i > token.i:
            parts.append(child.text)
    return " ".join(parts)


def _map_verb_to_relation(verb: Token) -> Optional[str]:
    """Map a verb token to one of the allowed relation types."""
    lemma = verb.lemma_.lower()
    return VERB_RELATION_MAP.get(lemma)


def _check_copula_pattern(verb: Token, doc: Doc) -> Optional[Tuple[str, str, str]]:
    """
    Detect copula / "is a" patterns:
      - X is a Y                    → is_a
      - X is a type/subset/branch of Y → is_a / part_of / …
    Returns (source, relation, target) or None.
    """
    if verb.lemma_ != "be":
        return None

    subj_tok = _find_subject(verb)
    if subj_tok is None:
        return None

    source_phrase = _get_full_phrase(subj_tok)

    # Look for attr / acomp child
    for child in verb.children:
        if child.dep_ in ("attr", "acomp", "oprd"):
            # Check for prep pattern: "a type of Y"
            for prep in child.children:
                if prep.dep_ == "prep" and prep.text.lower() in ("of", "in", "for"):
                    for pobj in prep.children:
                        if pobj.dep_ == "pobj":
                            prep_phrase = child.lemma_.lower() + " " + prep.text.lower()
                            target_phrase = _get_full_phrase(pobj)
                            relation = PREP_RELATION_MAP.get(prep_phrase, "is_a")
                            return (source_phrase, relation, target_phrase)

            # Simple: "X is a Y"
            target_phrase = _get_full_phrase(child)
            return (source_phrase, "is_a", target_phrase)

    return None


def _check_prep_relation(verb: Token) -> List[Tuple[str, str, str]]:
    """
    Check for prepositional relation patterns like 'based on', 'part of', etc.
    """
    results = []
    subj_tok = _find_subject(verb)
    if subj_tok is None:
        return results

    source_phrase = _get_full_phrase(subj_tok)

    for child in verb.children:
        if child.dep_ == "prep":
            prep_text = verb.lemma_.lower() + " " + child.text.lower()
            # Also check: "verb + particle + prep" (e.g. "relied on")
            for particle in verb.children:
                if particle.dep_ == "prt":
                    prep_text = verb.lemma_.lower() + " " + particle.text.lower()

            relation = None
            # Try full verb+prep
            for pattern, rel in PREP_RELATION_MAP.items():
                if prep_text.endswith(pattern) or pattern in prep_text:
                    relation = rel
                    break

            if relation is None:
                # Fallback: just the verb
                relation = _map_verb_to_relation(verb)

            if relation:
                for pobj in child.children:
                    if pobj.dep_ == "pobj":
                        target_phrase = _get_full_phrase(pobj)
                        results.append((source_phrase, relation, target_phrase))

    return results


# ---------------------------------------------------------------------------
# Relative-clause handling
# ---------------------------------------------------------------------------

def _extract_relcl_relations(doc: Doc) -> List[Tuple[str, str, str]]:
    """
    Handle relative clauses like:
      "tasks that require human intelligence"
      → Tasks  →  require  →  Human Intelligence
    """
    relations = []
    for token in doc:
        if token.dep_ == "relcl":
            verb = token
            # The head of the relcl is the noun being modified
            antecedent = verb.head
            antecedent_phrase = _get_full_phrase(antecedent)

            relation = _map_verb_to_relation(verb)
            if relation is None:
                continue

            # Find the object(s) of the relative-clause verb
            objs = _find_objects(verb)
            for obj in objs:
                obj_phrase = _get_full_phrase(obj)
                relations.append((antecedent_phrase, relation, obj_phrase))

    return relations


# ---------------------------------------------------------------------------
# Conjunction handling (multi-relation)
# ---------------------------------------------------------------------------

def _expand_conjunctions(relations: List[Tuple[str, str, str]], doc: Doc) -> List[Tuple[str, str, str]]:
    """
    Expand conjunct verbs.  E.g.:
      "ML algorithms analyze data and improve performance."
      → (ML algorithms, analyze, data), (ML algorithms, improve, performance)
    """
    expanded = list(relations)

    for token in doc:
        if token.dep_ == "conj" and token.head.pos_ == "VERB" and token.pos_ == "VERB":
            conj_verb = token
            parent_verb = token.head

            # Inherit the subject from the parent verb
            subj = _find_subject(parent_verb)
            if subj is None:
                continue
            source_phrase = _get_full_phrase(subj)

            relation = _map_verb_to_relation(conj_verb)
            if relation is None:
                continue

            objs = _find_objects(conj_verb)
            for obj in objs:
                obj_phrase = _get_full_phrase(obj)
                triple = (source_phrase, relation, obj_phrase)
                if triple not in expanded:
                    expanded.append(triple)

    return expanded


# ---------------------------------------------------------------------------
# Negation detection
# ---------------------------------------------------------------------------

def _is_negated(verb: Token) -> bool:
    """Check if a verb has a negation modifier."""
    for child in verb.children:
        if child.dep_ == "neg":
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class MeaningAnalyzer:
    """
    Analyse sentences to extract semantic relations and concept descriptions.
    """

    def __init__(self, nlp: spacy.language.Language):
        self.nlp = nlp
        self.context = ContextTracker()

    def analyze_sentences(
        self,
        sentences: List[str],
    ) -> Tuple[List[Dict], Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Analyse a list of sentences.

        Returns
        -------
        relations : list[dict]
            Each dict: {source, target, relation, negated}
        descriptions : dict[str, list[str]]
            Concept -> list of descriptive sentences.
        formulas : dict[str, list[str]]
            Concept -> list of formula strings found near the concept.
        """
        all_relations: List[Dict] = []
        descriptions: Dict[str, List[str]] = {}
        formulas: Dict[str, List[str]] = {}

        for sent_text in sentences:
            # Detect paragraph boundaries (crude: blank-line separated)
            if not sent_text.strip():
                continue

            doc = self.nlp(sent_text)

            # --- Pronoun resolution ---
            resolved_text = self._resolve_pronouns(doc)
            if resolved_text != sent_text:
                doc = self.nlp(resolved_text)

            # --- Formula detection ---
            found_formulas = detect_formulas(sent_text)

            # --- Extract relations from this sentence ---
            sent_relations = self._extract_relations(doc)

            # --- Relative-clause relations ---
            relcl_rels = _extract_relcl_relations(doc)
            sent_relations.extend(relcl_rels)

            # --- Expand conjunctions ---
            sent_relations = _expand_conjunctions(sent_relations, doc)

            # --- Normalise & validate ---
            valid_rels = []
            seen_rels = set()
            for src, rel, tgt in sent_relations:
                src_n = normalize_concept(src)
                tgt_n = normalize_concept(tgt)
                if (
                    src_n
                    and tgt_n
                    and is_valid_concept(src_n)
                    and is_valid_concept(tgt_n)
                    and src_n.lower() != tgt_n.lower()
                    and rel in ALLOWED_RELATIONS
                ):
                    dedup_key = (src_n.lower(), rel, tgt_n.lower())
                    if dedup_key not in seen_rels:
                        seen_rels.add(dedup_key)
                        valid_rels.append({
                            "source": src_n,
                            "target": tgt_n,
                            "relation": rel,
                            "negated": False,
                        })

            # Check negation for each relation
            for token in doc:
                if token.pos_ == "VERB" and _is_negated(token):
                    # Mark any relation whose verb matches as negated
                    rel_type = _map_verb_to_relation(token)
                    if rel_type:
                        for r in valid_rels:
                            if r["relation"] == rel_type:
                                r["negated"] = True

            all_relations.extend(valid_rels)

            # --- Description fallback ---
            concepts_in_sent = extract_concepts_from_doc(doc)
            if not valid_rels and concepts_in_sent:
                # No relations extracted → store sentence as description
                for concept in concepts_in_sent:
                    descriptions.setdefault(concept, []).append(sent_text)
            elif valid_rels:
                # Also store sentence as description for involved concepts
                involved = set()
                for r in valid_rels:
                    involved.add(r["source"])
                    involved.add(r["target"])
                for concept in involved:
                    descriptions.setdefault(concept, []).append(sent_text)

            # --- Formulas: attach to concepts in sentence ---
            if found_formulas and concepts_in_sent:
                for concept in concepts_in_sent:
                    formulas.setdefault(concept, []).extend(found_formulas)

            # --- Update context ---
            if concepts_in_sent:
                self.context.update_subject(concepts_in_sent[0])
                for c in concepts_in_sent:
                    self.context.add_global_concept(c)

        return all_relations, descriptions, formulas

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_pronouns(self, doc: Doc) -> str:
        """Replace anaphoric pronouns with the last known subject.
        Does NOT resolve relative pronouns ('that', 'which') inside clauses."""
        tokens = list(doc)
        replacements: Dict[int, str] = {}

        for token in tokens:
            if token.pos_ == "PRON" and token.dep_ in ("nsubj", "nsubjpass"):
                # Skip relative pronouns inside relative clauses
                if token.text.lower() in ("that", "which", "who", "whom", "whose"):
                    continue
                resolved = self.context.resolve_pronoun(token.text)
                if resolved:
                    replacements[token.i] = resolved

        if not replacements:
            return doc.text

        parts = []
        for token in tokens:
            if token.i in replacements:
                # Preserve original trailing whitespace
                ws = token.whitespace_
                parts.append(replacements[token.i] + ws)
            else:
                parts.append(token.text_with_ws)

        return "".join(parts).strip()

    def _extract_relations(self, doc: Doc) -> List[Tuple[str, str, str]]:
        """Extract (source, relation, target) triples from a doc."""
        relations: List[Tuple[str, str, str]] = []

        for token in doc:
            # Process both VERB and AUX tokens (AUX handles copula "is")
            if token.pos_ not in ("VERB", "AUX"):
                continue
            # Skip auxiliary verbs that are helpers, not the main predicate
            if token.dep_ in ("aux", "auxpass"):
                continue

            # 1. Check copula / "is a" pattern
            copula = _check_copula_pattern(token, doc)
            if copula:
                relations.append(copula)
                continue

            # 2. Check prepositional relation patterns
            prep_rels = _check_prep_relation(token)
            if prep_rels:
                relations.extend(prep_rels)
                continue

            # 3. Standard SVO
            subj = _find_subject(token)
            if subj is None:
                continue

            relation = _map_verb_to_relation(token)
            if relation is None:
                continue

            source_phrase = _get_full_phrase(subj)
            objs = _find_objects(token)
            for obj in objs:
                target_phrase = _get_full_phrase(obj)
                relations.append((source_phrase, relation, target_phrase))

        return relations
