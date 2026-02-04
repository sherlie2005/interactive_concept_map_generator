def normalize_text(text):
    return text.lower().strip()


def map_token_to_chunk(token, noun_chunks):
    for chunk in noun_chunks:
        if token.text in chunk.text:
            return chunk.text
    return token.text


def resolve_pronoun(token, last_subject):
    if token.pos_ == "PRON" and last_subject:
        return last_subject
    return token.text


def normalize_relation(verb):
    return verb.lemma_.lower()


def unique_nodes(nodes):
    seen = set()
    unique = []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            unique.append(n)
    return unique


def filter_relations(relations, threshold=0.6):
    return [r for r in relations if r.get("confidence", 1.0) >= threshold]
