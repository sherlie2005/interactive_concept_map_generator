def build_graph(sentence_id, concepts, relations, descriptions=None):
    nodes = []

    for c in concepts:
        node = {
            "id": c,
            "sentence_id": sentence_id
        }

        # 🔹 Attach descriptive sentences if available
        if descriptions and c in descriptions:
            node["descriptions"] = descriptions[c]

        nodes.append(node)

    return {
        "sentence_id": sentence_id,
        "nodes": nodes,
        "edges": relations
    }