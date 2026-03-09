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

NOISE_WORDS = {"lot", "a lot"}


def extract_concepts(sentence):

    doc = nlp(sentence)

    # Collect raw noun chunks
    raw_chunks = []

    for chunk in doc.noun_chunks:

        text = chunk.text.strip()
        lower = text.lower()

        if lower in RELATIVE_PRONOUNS:
            continue

        if lower in HIERARCHY_STOP_WORDS:
            continue

        if lower.startswith("a ") and lower[2:] in HIERARCHY_STOP_WORDS:
            continue

        if lower in NOISE_WORDS:
            continue

        if chunk.root.pos_ == "PRON":
            continue

        if chunk.root.pos_ not in ("NOUN", "PROPN"):
            continue

        raw_chunks.append((chunk.start, chunk.end, text))

    # Sort by phrase length (longest first)
    raw_chunks.sort(key=lambda x: (x[1] - x[0]), reverse=True)

    selected = []
    occupied = set()

    for start, end, text in raw_chunks:

        overlap = False

        for i in range(start, end):
            if i in occupied:
                overlap = True
                break

        if not overlap:
            selected.append(text)

            for i in range(start, end):
                occupied.add(i)

    ABSTRACT_HEADS = {
    "type", "types",
    "kind", "kinds",
    "form", "forms",
    "category", "categories",
    "subset",
    "branch",
    "part"
}

    cleaned = []

    for c in selected:
        words = c.lower().split()

        if words[-1] in ABSTRACT_HEADS:
            continue

        cleaned.append(c)

    return list(set(cleaned))