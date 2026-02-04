def build_graph(sentence_id, concepts, relations):
    nodes = []
    edges = []

    for c in concepts:
        nodes.append({
            "id": c,
            "sentence_id": sentence_id
        })

    for r in relations:
        edges.append(r)

    return {
        "sentence_id": sentence_id,
        "nodes": nodes,
        "edges": edges
    }
