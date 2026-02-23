import spacy

nlp = spacy.load("en_core_web_sm")

RELATIVE_PRONOUNS = {"that", "which", "who", "whom", "whose"}

HIERARCHY_STOP_WORDS = {
    "type", "types",
    "branch", "branches",
    "form", "forms",
    "kind", "kinds",
    "category", "categories"
}

NOISE_WORDS = {
    "lot", "a lot"
}


def extract_concepts(sentence):
    doc = nlp(sentence)
    concepts = set()

    for chunk in doc.noun_chunks:
        text = chunk.text.strip()
        lower = text.lower()

        # Remove pure relative pronouns
        if lower in RELATIVE_PRONOUNS:
            continue

        # Remove structural hierarchy placeholders
        if lower in HIERARCHY_STOP_WORDS:
            continue

        if lower.startswith("a ") and lower[2:] in HIERARCHY_STOP_WORDS:
            continue

        # Remove noisy phrases
        if lower in NOISE_WORDS:
            continue

        # Avoid very short meaningless chunks
        if len(lower) <= 2:
            continue

        if chunk.root.pos_ == "PRON":
            continue
        
        if lower in {"which", "that", "who", "whom", "whose"}:
            continue

        if lower.isdigit():
            continue

        if chunk.root.pos_ not in ("NOUN", "PROPN"):
            continue

        if len(lower.split()) == 1 and chunk.root.pos_ == "VERB":
            continue

        concepts.add(text)

    return list(concepts)