import spacy
from utils import (
    map_token_to_chunk,
    resolve_pronoun,
    normalize_relation
)

nlp = spacy.load("en_core_web_sm")


# ---------------- RELATIVE CLAUSE ----------------
def resolve_relative_clause(token, noun_chunks):
    for child in token.children:
        if child.dep_ == "nsubj" and child.text.lower() in ("that", "which", "who"):
            head = token.head
            if head.pos_ in ("NOUN", "PROPN"):
                return map_token_to_chunk(head, noun_chunks)
    return None


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

    for token in doc:

        # ---------------- COPULAR HIERARCHY ----------------
        if token.lemma_ == "be":

            subject = None
            parent = None

            for child in token.children:
                if child.dep_ in ("nsubj", "nsubjpass"):
                    subject = map_token_to_chunk(child, noun_chunks)

            for child in token.children:

                if child.dep_ in ("attr", "acomp"):

                    parent = map_token_to_chunk(child, noun_chunks)

                    for sub in child.children:
                        if sub.dep_ == "prep" and sub.text.lower() == "of":
                            for pobj in sub.children:
                                if pobj.dep_ == "pobj":
                                    parent = map_token_to_chunk(pobj, noun_chunks)

            if subject and parent:

                relations.append({
                    "source": subject,
                    "target": parent,
                    "relation": "is_a",
                    "negated": False
                })

                context["last_subject"] = subject

        # ---------------- PROCESS ONLY VERBS ----------------
        if token.pos_ not in ("VERB", "AUX"):
            continue

        relation = normalize_relation(token)

        WEAK_RELATIONS = {"as", "through"}

        if relation in WEAK_RELATIONS:
            continue

        subjects = []
        objects = []

        # ---------------- SUBJECT EXTRACTION ----------------
        for child in token.children:

            if child.dep_ in ("nsubj", "nsubjpass"):

                resolved = resolve_pronoun(child, context.get("last_subject"))

                subj = map_token_to_chunk(resolved, noun_chunks)
                subjects.append(subj)

                for conj in child.conjuncts:
                    subjects.append(map_token_to_chunk(conj, noun_chunks))

        if not subjects:

            if token.dep_ == "conj":
                head = token.head

                for child in head.children:
                    if child.dep_ in ("nsubj", "nsubjpass"):
                        subjects.append(map_token_to_chunk(child, noun_chunks))

        if not subjects:

            fallback = context.get("last_subject") or context.get("paragraph_topic")

            if fallback:
                subjects = [fallback]

        if not subjects:
            continue

        # ---------------- OBJECT EXTRACTION ----------------
        for child in token.children:

            if child.dep_ == "dobj":

                obj = map_token_to_chunk(child, noun_chunks)
                objects.append(obj)

                for conj in child.conjuncts:
                    objects.append(map_token_to_chunk(conj, noun_chunks))

            if child.dep_ == "attr" and token.lemma_ != "be":

                obj = map_token_to_chunk(child, noun_chunks)
                objects.append(obj)

            if child.dep_ == "prep":

                for pobj in child.children:

                    if pobj.dep_ == "pobj":

                        obj = map_token_to_chunk(pobj, noun_chunks)
                        objects.append(obj)

                        relation = f"{relation}_{child.text}"

                        for conj in pobj.conjuncts:
                            objects.append(map_token_to_chunk(conj, noun_chunks))

        # =====================================================
        # PATTERN LAYER (GENERALIZED)
        # =====================================================

        # convert A into B
        if token.lemma_ in ("convert", "transform"):

            source = None
            target = None

            for child in token.children:

                if child.dep_ == "dobj":
                    source = map_token_to_chunk(child, noun_chunks)

                if child.dep_ == "prep" and child.text == "into":

                    for pobj in child.children:
                        if pobj.dep_ == "pobj":
                            target = map_token_to_chunk(pobj, noun_chunks)

            if source and target:

                if source == target:
                    continue

                relations.append({
                    "source": source,
                    "target": target,
                    "relation": "convert_into",
                    "negated": False
                })

        # consist of / contain
        # consist of / contain / include
            if token.lemma_ in ("consist", "contain", "include"):

                expanded_objects = []

                for obj in objects:
                    expanded_objects.append(obj)

                # capture enumerations like "A, B and C"
                for child in token.children:
                    if child.dep_ == "prep":
                        for pobj in child.children:
                            if pobj.dep_ == "pobj":
                                expanded_objects.append(map_token_to_chunk(pobj, noun_chunks))

                                for conj in pobj.conjuncts:
                                    expanded_objects.append(map_token_to_chunk(conj, noun_chunks))

                expanded_objects = list(set(expanded_objects))

                for subject in subjects:
                    for obj in expanded_objects:

                        if subject == obj:
                            continue

                        relations.append({
                            "source": subject,
                            "target": obj,
                            "relation": "consist_of",
                            "negated": False
                        })

                    # produce / generate
                    if token.lemma_ in ("produce", "generate"):

                        for subject in subjects:
                            for obj in objects:

                                relations.append({
                                    "source": subject,
                                    "target": obj,
                                    "relation": "produce",
                                    "negated": False
                                })

        # used to pattern
        if token.lemma_ == "use":

            for child in token.children:

                if child.dep_ == "xcomp":

                    for subject in subjects:

                        relations.append({
                            "source": subject,
                            "target": child.lemma_,
                            "relation": "used_for",
                            "negated": False
                        })

        # such as / including pattern
        if token.lemma_ in ("include", "contain"):

            for subject in subjects:
                for obj in objects:

                    if subject == obj:
                        continue

                    relations.append({
                        "source": subject,
                        "target": obj,
                        "relation": "include",
                        "negated": False
                    })

        # =====================================================

        objects = list(set(objects))


        # ---------------- CREATE RELATIONS ----------------
        for subject in subjects:

            for obj in objects:

                # remove self relations
                if subject == obj:
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

        context["last_subject"] = subjects[0]

    unique = {}
    for r in relations:
        key = (r["source"], r["relation"], r["target"])
        unique[key] = r

    relations = list(unique.values())

    return relations