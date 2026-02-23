import spacy
from utils import (
    map_token_to_chunk,
    resolve_pronoun,
    normalize_relation
)

nlp = spacy.load("en_core_web_sm")


# ---------------- RELATIVE CLAUSE ----------------
def resolve_relative_clause(token, noun_chunks):
    """
    Rebind relative clause subjects (that/which/who)
    to their governing noun.
    """
    for child in token.children:
        if child.dep_ == "nsubj" and child.text.lower() in ("that", "which", "who"):
            head = token.head
            if head.pos_ in ("NOUN", "PROPN"):
                return map_token_to_chunk(head, noun_chunks)
    return None


# ---------------- COPULAR HIERARCHY ----------------
def detect_copular_hierarchy(token, noun_chunks):
    """
    Detect:
    X is Y
    X is a type of Y
    X and Z are types of Y
    """

    subjects = []
    parent = None

    # Collect subjects (handle conjunctions)
    for child in token.children:
        if child.dep_ in ("nsubj", "nsubjpass"):
            subjects.append(map_token_to_chunk(child, noun_chunks))
            for conj in child.conjuncts:
                subjects.append(map_token_to_chunk(conj, noun_chunks))

    if not subjects:
        return None, None

    # Find attribute
    for child in token.children:
        if child.dep_ == "attr":
            candidate = child
            parent = map_token_to_chunk(candidate, noun_chunks)

            # Handle "type of Y" pattern
            for sub in candidate.children:
                if sub.dep_ == "prep" and sub.text.lower() == "of":
                    for pobj in sub.children:
                        if pobj.dep_ == "pobj":
                            parent = map_token_to_chunk(pobj, noun_chunks)

    if subjects and parent:
        return subjects, parent

    return None, None


# ---------------- SUBJECT NORMALIZATION ----------------
def normalize_subject(subject, noun_chunks):
    if not subject:
        return None

    for chunk in noun_chunks:
        if subject == chunk.text:
            return chunk.text

    for chunk in noun_chunks:
        if subject in chunk.text:
            return chunk.text

    return subject


# ---------------- MAIN EXTRACTION ----------------
def extract_relations(sentence, context):

    doc = nlp(sentence)
    relations = []
    noun_chunks = list(doc.noun_chunks)
    """
    print("---- DEBUG ----")
    for token in doc:
        print(token.text, token.dep_, token.head.text, token.pos_)
    print("--------------")
    """ 
    for token in doc:

        if token.pos_ not in ("VERB", "AUX"):
            continue

        # ==================================================
        # 1️⃣ STRICT COPULAR HIERARCHY (ROOT ONLY)
        # ==================================================
        if token.lemma_ == "be" and token.dep_ == "ROOT":

            subjects, parent = detect_copular_hierarchy(token, noun_chunks)

            if subjects and parent:
                for subj in subjects:
                    subj = normalize_subject(subj, noun_chunks)
                    parent_norm = normalize_subject(parent, noun_chunks)

                    relation_tuple = (subj, parent_norm, "is_a")

                    if relation_tuple not in {
                        (r["source"], r["target"], r["relation"]) for r in relations
                    }:
                        relations.append({
                            "source": subj,
                            "target": parent_norm,
                            "relation": "is_a",
                            "negated": any(c.dep_ == "neg" for c in token.children)
                        })

                    context["last_subject"] = subj

                continue  # prevent normal verb processing

        # ==================================================
        # 2️⃣ NORMAL VERB PROCESSING
        # ==================================================
        subject = None
        relation = normalize_relation(token)
        objects = []

        # -------- SUBJECT --------
        for child in token.children:
            if child.dep_ in ("nsubj", "nsubjpass"):

                # Relative clause rebinding
                if child.text.lower() in ("that", "which", "who"):
                    relative_subject = resolve_relative_clause(token, noun_chunks)
                    if relative_subject:
                        subject = relative_subject
                        break

                resolved = resolve_pronoun(child, context.get("last_subject"))
                subject = map_token_to_chunk(resolved, noun_chunks)

        # Fallback to context
        if not subject:
            subject = context.get("last_subject") or context.get("paragraph_topic")

        subject = normalize_subject(subject, noun_chunks)

        if subject and subject.lower() in ("it", "they", "this", "that"):
            subject = context.get("last_subject")

        if not subject:
            continue
        # ---------------- CONTROL / COMPLEMENT CLAUSE HANDLING ----------------
        for child in token.children:
            if child.dep_ in ("xcomp", "ccomp"):
                for subchild in child.subtree:
                    if subchild.dep_ in ("nsubj", "nsubjpass"):
                        obj = map_token_to_chunk(subchild, noun_chunks)

                        relation_tuple = (subject, obj, relation)

                        if relation_tuple not in {
                            (r["source"], r["target"], r["relation"]) for r in relations
                        }:
                            relations.append({
                                "source": subject,
                                "target": obj,
                                "relation": relation,
                                "negated": any(c.dep_ == "neg" for c in token.children)
                            })
        # -------- OBJECT EXTRACTION --------
        for child in token.children:

            # Direct object (enable → computers)
            if child.dep_ == "dobj":
                obj = map_token_to_chunk(child, noun_chunks)
                objects.append(obj)

                for conj in child.conjuncts:
                    objects.append(map_token_to_chunk(conj, noun_chunks))

            # Attribute for non-copular verbs
            if child.dep_ == "attr" and token.lemma_ != "be":
                obj = map_token_to_chunk(child, noun_chunks)
                objects.append(obj)

            # Prepositional objects
            if child.dep_ == "prep":
                for pobj in child.children:
                    if pobj.dep_ == "pobj":
                        obj = map_token_to_chunk(pobj, noun_chunks)
                        objects.append(obj)
                        relation = f"{relation}_{child.text}"

                        for conj in pobj.conjuncts:
                            objects.append(map_token_to_chunk(conj, noun_chunks))

        objects = list(set(objects))

        # -------- CREATE RELATIONS --------
        for obj in objects:

            if not obj:
                continue

            if obj.lower() in {"a lot", "lot"}:
                continue

            relation_tuple = (subject, obj, relation)

            if relation_tuple not in {
                (r["source"], r["target"], r["relation"]) for r in relations
            }:
                relations.append({
                    "source": subject,
                    "target": obj,
                    "relation": relation,
                    "negated": any(c.dep_ == "neg" for c in token.children)
                })

        context["last_subject"] = subject

    return relations