import spacy
from utils import (
    map_token_to_chunk,
    resolve_pronoun,
    normalize_relation
)

nlp = spacy.load("en_core_web_sm")


def extract_relations(sentence, context):
    """
    Extract semantic relations from a sentence using context memory.
    Context keys expected:
      - last_subject
      - paragraph_topic
    """
    doc = nlp(sentence)
    relations = []

    noun_chunks = list(doc.noun_chunks)

    for token in doc:
        if token.pos_ != "VERB":
            continue

        subject = None
        obj = None
        relation = normalize_relation(token)

        # ---------- SUBJECT RESOLUTION ----------
        for child in token.children:
            if child.dep_ in ("nsubj", "nsubjpass"):
                # resolve pronoun using context
                resolved = resolve_pronoun(child, context.get("last_subject"))

                # map to full noun phrase if possible
                subject = map_token_to_chunk(resolved, noun_chunks)

        # fallback: if no subject found, use paragraph topic
        if not subject:
            subject = context.get("last_subject") or context.get("paragraph_topic")

        # ---------- OBJECT RESOLUTION ----------
        objects=[]
        for child in token.children:

            # direct object
            if child.dep_ in ("dobj", "attr"):
                obj = map_token_to_chunk(child, noun_chunks)

            for conj in child.conjuncts:
                objects.append(map_token_to_chunk(conj, noun_chunks))

            # prepositional object: VERB → prep → pobj
            if child.dep_ == "prep":
                for pobj in child.children:
                    if pobj.dep_ == "pobj":
                        obj = map_token_to_chunk(pobj, noun_chunks)
                        relation = f"{relation}_{child.text}"
                        
            for conj in pobj.conjuncts:
                    objects.append(map_token_to_chunk(conj, noun_chunks))

        # ---------- CREATE RELATION ----------
        for obj in objects:
            relations.append({
                "source": subject,
                "target": obj,
                "relation": relation,
                "negated": any(c.dep_ == "neg" for c in token.children)
            })

        context["last_subject"] = subject


    return relations
