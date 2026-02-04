import spacy

nlp = spacy.load("en_core_web_sm")

def extract_relations(sentence):
    doc = nlp(sentence)
    relations = []

    for token in doc:
        if token.pos_ == "VERB":
            subject = None
            obj = None

            for child in token.children:
                if child.dep_ in ("nsubj", "nsubjpass"):
                    subject = child.text
                if child.dep_ in ("dobj", "pobj", "attr"):
                    obj = child.text

            if subject and obj:
                relations.append({
                    "source": subject,
                    "target": obj,
                    "relation": token.lemma_
                })

    return relations
