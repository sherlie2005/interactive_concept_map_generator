"""
Heading Segmenter module for the CS-CME engine.

Detects document headings and builds a hierarchical structure used to
organise concepts into a tree under document_root.
"""

import re
from typing import Dict, List, Optional, Tuple

from utils import normalize_concept


# --------------------------------------------------------------------------- 
# Heading detection heuristics (GENERALISED for academic PDFs)
# --------------------------------------------------------------------------- 

# Numbered heading patterns (expanded)
_NUMBERED_RE = re.compile(
    r"^(?:" 
    r"(?:unit|chapter|section|part|module)\s*[-:]?\s*\d+" 
    r"|\d+(?:\.\d+)*\.?\s"
    r"|[A-Z][A-Za-z\s]+:\s"          # catches "Cassandra Architecture:"
    r")",
    re.IGNORECASE,
)

# ALL-CAPS or Title-Case with colon (common in architecture sections)
_ALLCAPS_RE = re.compile(r"^[A-Z][A-Z\s\-:]{5,}$")
_TITLECASE_RE = re.compile(
    r"^(?:[A-Z][a-z]+(?:\s+(?:and|or|of|the|in|for|to|a|an|with|on|by|is|as|at))?)+(?:\s+[A-Z][a-z]+)*$"
)

def is_heading(line: str) -> bool:
    """Heuristically decide whether *line* looks like a heading."""
    line = line.strip()
    if not line or len(line) > 250:          # relaxed length limit
        return False

    if line.endswith(".") and len(line.split()) > 12:
        return False

    # Numbered / colon style (UNIT-4, Cassandra Architecture:)
    if _NUMBERED_RE.match(line):
        return True

    # ALL CAPS
    if _ALLCAPS_RE.match(line):
        return True

    # Title-Case (≤ 12 words)
    words = line.split()
    if 1 <= len(words) <= 12:
        caps = sum(1 for w in words if w and w[0].isupper())
        if caps / len(words) >= 0.5 and not any(c in line for c in ".;,!?"):
            return True

    return False


def clean_heading(raw: str) -> str:
    """Strip numbering and normalise a heading string."""
    h = raw.strip()
    h = _NUMBERED_RE.sub("", h).strip()
    h = h.rstrip(":")
    return h.strip()


# --------------------------------------------------------------------------- 
# INFER LEVEL + HEADING NODE + SEGMENTATION (unchanged from your original)
# --------------------------------------------------------------------------- 

def _infer_level(line: str) -> int:
    """Infer a rough nesting level from a heading line."""
    line = line.strip()

    # Numbered: count dots
    m = re.match(r"^(\d+(?:\.\d+)*)", line)
    if m:
        return m.group(1).count(".") + 1

    # Chapter / Section keywords
    if re.match(r"^chapter\s", line, re.IGNORECASE):
        return 1
    if re.match(r"^section\s", line, re.IGNORECASE):
        return 2

    # ALL CAPS → level 1
    if _ALLCAPS_RE.match(line):
        return 1

    # Default Title Case → level 2
    return 2


class HeadingNode:
    """A node in the heading hierarchy."""

    def __init__(self, title: str, level: int, parent: Optional["HeadingNode"] = None):
        self.title = title
        self.level = level
        self.parent = parent
        self.children: List["HeadingNode"] = []
        self.sentences: List[str] = []

    def add_child(self, child: "HeadingNode"):
        child.parent = self
        self.children.append(child)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "level": self.level,
            "children": [c.to_dict() for c in self.children],
            "sentence_count": len(self.sentences),
        }


def segment_by_headings(text: str) -> Tuple[HeadingNode, List[str]]:
    """
    Parse *text* into a heading hierarchy.
    """
    root = HeadingNode("Document_Root", level=0)
    current_node = root
    flat_headings: List[str] = []

    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if is_heading(stripped):
            level = _infer_level(stripped)
            heading_text = clean_heading(stripped)
            if not heading_text:
                continue
            heading_text = normalize_concept(heading_text)
            flat_headings.append(heading_text)

            node = HeadingNode(heading_text, level)

            # Walk up from current_node to find appropriate parent
            parent = current_node
            while parent.level >= level and parent.parent is not None:
                parent = parent.parent
            parent.add_child(node)
            current_node = node
        else:
            # Regular sentence → attach to current section
            current_node.sentences.append(stripped)

    return root, flat_headings


def get_heading_edges(root: HeadingNode) -> List[Dict]:
    """
    Walk the heading tree and produce edges of the form:
        {"source": parent_heading, "target": child_heading, "relation": "contains"}
    """
    edges: List[Dict] = []

    def _walk(node: HeadingNode):
        for child in node.children:
            edges.append({
                "source": node.title,
                "target": child.title,
                "relation": "contains",
            })
            _walk(child)

    _walk(root)
    return edges