import re

def canonicalize(text):
    text = text.strip().lower()
    text = re.sub(r'^(the|a|an)\s+', '', text)
    return text


def normalize_display_form(text):

    # Remove leading articles
    text = re.sub(r'^(the|a|an)\s+', '', text.strip(), flags=re.IGNORECASE)

    words = text.split()

    return " ".join(
        w.capitalize() if w.islower() else w
        for w in words
    )


def build_document_graph(sentence_graphs):

    node_map = {}
    edges = []

    for sentence in sentence_graphs:

        for node in sentence["nodes"]:
            nid = node["id"]

            if nid not in node_map:
                node_map[nid] = {
                    "id": nid,
                    "frequency": 1,
                    "descriptions": node.get("descriptions", [])
                }
            else:
                node_map[nid]["frequency"] += 1

        for edge in sentence["edges"]:
            edges.append(edge)

    return {
        "nodes": list(node_map.values()),
        "edges": edges
    }