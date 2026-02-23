def normalize_text(text):
    return text.lower().strip()


def map_token_to_chunk(token_or_text, noun_chunks):
    # If already a string (from context memory), return directly
    if isinstance(token_or_text, str):
        return token_or_text

    # Else, it's a spaCy token
    token = token_or_text

    for chunk in noun_chunks:
        if token.i >= chunk.start and token.i < chunk.end:
            return chunk.text.strip()
        
    # Fallback to full subtree (for rare parsing cases)
    subtree = list(token.subtree)
    if len(subtree) > 1:
        return " ".join([t.text for t in subtree]).strip()

    return token.text.strip()



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
