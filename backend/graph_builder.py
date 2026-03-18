"""
Graph Builder module for the CS-CME engine.

Responsibilities:
  - Build a NetworkX directed graph from extracted relations
  - Apply PageRank-style importance scoring
  - Apply Louvain community detection for clustering
  - Keep top-N concepts
  - Produce the final JSON structure
"""

from typing import Dict, List, Optional, Set

import networkx as nx

try:
    import community as community_louvain  # python-louvain
except ImportError:
    community_louvain = None

from utils import MAX_CONCEPTS, ALLOWED_RELATIONS


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(
    relations: List[Dict],
    frequency: Dict[str, int],
    descriptions: Dict[str, List[str]],
    formulas: Dict[str, List[str]],
    heading_edges: Optional[List[Dict]] = None,
) -> nx.DiGraph:
    """
    Build a directed graph from extracted relations.

    Parameters
    ----------
    relations : list[dict]
        Each dict has keys: source, target, relation, negated.
    frequency : dict[str, int]
        Concept -> occurrence count.
    descriptions : dict[str, list[str]]
        Concept -> descriptive sentences.
    formulas : dict[str, list[str]]
        Concept -> formula strings.
    heading_edges : list[dict] | None
        Edges from heading hierarchy (source, target, relation).

    Returns a NetworkX DiGraph.
    """
    G = nx.DiGraph()

    # --- Add relation edges ---
    for rel in relations:
        src = rel["source"]
        tgt = rel["target"]
        relation = rel["relation"]
        negated = rel.get("negated", False)

        if relation not in ALLOWED_RELATIONS:
            continue

        # Ensure nodes exist
        for n in (src, tgt):
            if n not in G:
                G.add_node(n, frequency=frequency.get(n, 1),
                           descriptions=[], formulas=[], cluster=-1)

        G.add_edge(src, tgt, relation=relation, negated=negated)

    # --- Add heading hierarchy edges ---
    if heading_edges:
        for he in heading_edges:
            src = he["source"]
            tgt = he["target"]
            relation = he.get("relation", "contains")
            for n in (src, tgt):
                if n not in G:
                    G.add_node(n, frequency=frequency.get(n, 1),
                               descriptions=[], formulas=[], cluster=-1)
            if not G.has_edge(src, tgt):
                G.add_edge(src, tgt, relation=relation, negated=False)

    # --- Attach descriptions and formulas ---
    for concept, desc_list in descriptions.items():
        if concept in G:
            existing = G.nodes[concept].get("descriptions", [])
            # Deduplicate
            seen = set(existing)
            for d in desc_list:
                if d not in seen:
                    existing.append(d)
                    seen.add(d)
            G.nodes[concept]["descriptions"] = existing

    for concept, form_list in formulas.items():
        if concept in G:
            existing = G.nodes[concept].get("formulas", [])
            seen = set(existing)
            for f in form_list:
                if f not in seen:
                    existing.append(f)
                    seen.add(f)
            G.nodes[concept]["formulas"] = existing

    # --- Update frequency on nodes ---
    for concept, freq in frequency.items():
        if concept in G:
            G.nodes[concept]["frequency"] = freq

    return G

# ---------------------------------------------------------------------------
# Remove weak / isolated nodes
# ---------------------------------------------------------------------------

def filter_low_value_nodes(
    G: nx.DiGraph,
    frequency: Dict[str, int],
    freq_threshold: int = 3,
    document_title: str = "Document Overview",  # <--- NEW parameter
) -> nx.DiGraph:
    """
    Keep:
        - nodes that participate in relations
        - standalone nodes only if frequency >= threshold
    """
    nodes_to_keep = set()

    for node in list(G.nodes):
        # Always keep the dynamic root
        if node == document_title:
            nodes_to_keep.add(node)
            continue

        degree = G.degree(node)
        freq = frequency.get(node, 1)

        if degree > 0:
            nodes_to_keep.add(node)
        elif freq >= freq_threshold:
            nodes_to_keep.add(node)

    nodes_to_remove = [n for n in G.nodes if n not in nodes_to_keep]

    pruned = G.copy()
    pruned.remove_nodes_from(nodes_to_remove)

    return pruned

# ---------------------------------------------------------------------------
# Concept importance ranking (PageRank-style)
# ---------------------------------------------------------------------------

def rank_concepts(
    G: nx.DiGraph,
    heading_concepts: Optional[List[str]] = None,
) -> Dict[str, float]:
    """
    Score every concept using a weighted PageRank that considers:
      - Link structure (PageRank)
      - Concept frequency
      - Whether it appeared as a heading (heading boost)

    Returns dict: concept -> importance score.
    """
    if len(G) == 0:
        return {}

    heading_set = set(heading_concepts) if heading_concepts else set()

    # Compute PageRank on the undirected projection
    undirected = G.to_undirected()
    try:
        pr = nx.pagerank(undirected, alpha=0.85, max_iter=100)
    except nx.PowerIterationFailedConvergence:
        pr = {n: 1.0 / len(G) for n in G.nodes}

    scores: Dict[str, float] = {}
    for node in G.nodes:
        freq = G.nodes[node].get("frequency", 1)
        pagerank_score = pr.get(node, 0)
        degree = G.degree(node)

        # Combined score
        score = (
            0.4 * pagerank_score * 100
            + 0.3 * (freq / max(1, max(f for f in (G.nodes[n].get("frequency", 1) for n in G.nodes))))
            + 0.2 * (degree / max(1, max(G.degree(n) for n in G.nodes)))
            + (0.1 if node in heading_set else 0.0)
        )
        scores[node] = score

    return scores


def prune_graph(
    G: nx.DiGraph,
    scores: Dict[str, float],
    max_concepts: int = MAX_CONCEPTS,
    document_title: str = "Document Overview",  # <--- NEW parameter
) -> nx.DiGraph:
    """
    Keep only the top *max_concepts* nodes (by importance score).
    Always keep document_root if present.
    """
    if len(G) <= max_concepts:
        return G

    # Always keep the dynamic title
    protected = {document_title}

    sorted_nodes = sorted(scores.items(), key=lambda x: -x[1])
    keep: Set[str] = set()
    for node, _ in sorted_nodes:
        if len(keep) >= max_concepts:
            break
        keep.add(node)
    keep.update(protected & set(G.nodes))

    remove = set(G.nodes) - keep
    pruned = G.copy()
    pruned.remove_nodes_from(remove)

    return pruned


# ---------------------------------------------------------------------------
# Community detection (Louvain)
# ---------------------------------------------------------------------------

def detect_communities(G: nx.DiGraph) -> Dict[str, int]:
    """
    Apply Louvain community detection on the undirected projection.
    Returns dict: concept -> cluster_id.
    """
    if community_louvain is None or len(G) < 2:
        return {n: 0 for n in G.nodes}

    undirected = G.to_undirected()
    try:
        partition = community_louvain.best_partition(undirected)
    except Exception:
        partition = {n: 0 for n in G.nodes}

    return partition


# ---------------------------------------------------------------------------
# Connect orphans to document_root
# ---------------------------------------------------------------------------

def connect_to_root(G: nx.DiGraph, document_title: str = "Document Overview") -> nx.DiGraph:  # <--- NEW parameter
    """
    Ensure every node is reachable from document_root.
    Add 'connected_to' edges from document_root to any disconnected
    top-level concepts.
    """
    root = document_title
    if root not in G:
        G.add_node(root, frequency=0, descriptions=[], formulas=[], cluster=-1)

    # Find nodes with no incoming edges (except root itself)
    for node in list(G.nodes):
        if node == root:
            continue
        if G.in_degree(node) == 0 and not G.has_edge(root, node):
            G.add_edge(root, node, relation="contains", negated=False)

    return G


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def graph_to_json(G: nx.DiGraph) -> Dict:
    """
    Convert the graph to the required JSON format:
    {
      "nodes": [{"id": ..., "frequency": ..., "descriptions": [...], "formulas": [...], "cluster": ...}],
      "edges": [{"source": ..., "target": ..., "relation": ..., "negated": ...}]
    }
    """
    nodes = []
    for node in G.nodes:
        data = G.nodes[node]
        nodes.append({
            "id": node,
            "frequency": data.get("frequency", 1),
            "descriptions": data.get("descriptions", []),
            "formulas": data.get("formulas", []),
            "cluster": data.get("cluster", -1),
        })

    edges = []
    seen_edges = set()
    for u, v, data in G.edges(data=True):
        edge_key = (u, v, data.get("relation", "connected_to"))
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        edges.append({
            "source": u,
            "target": v,
            "relation": data.get("relation", "connected_to"),
            "negated": data.get("negated", False),
        })

    all_formulas = []

    for node in G.nodes:
        fs = G.nodes[node].get("formulas", [])
        for f in fs:
            if f not in all_formulas:
                all_formulas.append(f)

    return {
        "nodes": nodes,
        "edges": edges,
        "document_formulas": all_formulas
    }