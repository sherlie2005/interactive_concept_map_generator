def canonicalize(text):
    return text.strip().lower()


def normalize_display_form(text):
    """
    Standardize display form:
    - Title Case
    - Preserve internal casing for acronyms
    """
    words = text.strip().split()
    return " ".join(w.capitalize() if w.islower() else w for w in words)


def build_document_graph(sentence_graphs):

    node_map = {}
    canonical_display = {}
    edge_map = {}

    for sentence in sentence_graphs:

        # ---------------- NODE MERGING ----------------
        for node in sentence["nodes"]:

            canonical_id = canonicalize(node["id"])

            # Decide display form deterministically
            if canonical_id not in canonical_display:
                canonical_display[canonical_id] = normalize_display_form(node["id"])

            display_id = canonical_display[canonical_id]

            if canonical_id not in node_map:
                node_map[canonical_id] = {
                    "id": display_id,
                    "frequency": 1,
                    "descriptions": list(node.get("descriptions", []))
                }
            else:
                node_map[canonical_id]["frequency"] += 1

                for desc in node.get("descriptions", []):
                    if desc not in node_map[canonical_id]["descriptions"]:
                        node_map[canonical_id]["descriptions"].append(desc)

                # ---------------- EDGE MERGING ----------------
                for edge in sentence["edges"]:

                    source_key = canonicalize(edge["source"])
                    target_key = canonicalize(edge["target"])

                    # 🔹 Ensure nodes exist (graph invariant)
                    for key, raw_text in [(source_key, edge["source"]),
                                        (target_key, edge["target"])]:

                        if key not in canonical_display:
                            canonical_display[key] = normalize_display_form(raw_text)

                        if key not in node_map:
                            node_map[key] = {
                                "id": canonical_display[key],
                                "frequency": 1,
                                "descriptions": []
                            }

                    source_display = canonical_display[source_key]
                    target_display = canonical_display[target_key]

                    edge_key = (
                        source_key,
                        target_key,
                        edge["relation"],
                        edge["negated"]
                    )

                    if edge_key not in edge_map:
                        edge_map[edge_key] = {
                            "source": source_display,
                            "target": target_display,
                            "relation": edge["relation"],
                            "weight": 1,
                            "negated": edge["negated"]
                        }
                    else:
                        edge_map[edge_key]["weight"] += 1

    return {
        "nodes": list(node_map.values()),
        "edges": list(edge_map.values())
    }