import spacy

nlp = spacy.load("en_core_web_sm")

def extract_concepts(sentence):
    doc = nlp(sentence)
    concepts = set()

    for chunk in doc.noun_chunks:
        text = chunk.text.strip()
        if len(text.split()) <= 4:
            concepts.add(text)

    return list(concepts)
