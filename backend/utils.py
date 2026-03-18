"""
Utility functions and constants for the CS-CME engine.
"""

import re

# ---------------------------------------------------------------------------
# Input limits
# ---------------------------------------------------------------------------
MAX_CHARACTERS = 15000
MAX_WORDS = 2000
MAX_PDF_PAGES = 10
MAX_CONCEPTS = 60

# ---------------------------------------------------------------------------
# Meaningless / stop concepts
# ---------------------------------------------------------------------------
MEANINGLESS_CONCEPTS = {
    "thing", "things", "stuff", "others", "this stage", "all others",
    "example", "examples", "way", "ways", "case", "cases", "kind", "kinds",
    "form", "forms", "sort", "sorts", "lot", "lots", "bit", "bits",
    "number", "numbers", "amount", "amounts", "result", "results",
    "it", "they", "them", "he", "she", "we", "you", "i", "me",
    "something", "anything", "nothing", "everything",
    "someone", "anyone", "no one", "everyone",
    "this", "that", "these", "those",
    "here", "there", "where", "when", "how", "why", "what", "which", "who",
    "one", "ones", "other", "another", "itself", "themselves",
    "many", "much", "few", "several", "some", "any", "none",
    "use", "purpose", "reason", "fact", "idea", "concept", "term",
    "following", "above", "below", "section", "figure", "table",
}

# Single generic words that are too vague to be concepts on their own
GENERIC_SINGLE_WORDS = {
    "method", "approach",
    "time", "set", "value", "level", "state", "order", "point",
    "line", "step", "end", "side", "base", "class", "field",
    "part", "function",
    "element", "operation", "input", "output", "user",
    "problem", "solution", "feature", "property", "service",
    "component", "module", "unit", "group", "phase", "stage",
    "area", "range", "rule", "format", "mode",
    "source", "target", "key", "index", "record", "entry", "item",
    "way", "result", "kind", "sort", "lot", "bit", "number", "amount",
}

# ---------------------------------------------------------------------------
# Allowed relation types
# ---------------------------------------------------------------------------
ALLOWED_RELATIONS = {
    "is_a", "contains", "uses", "produces", "stores",
    "improves", "reduces", "represents", "requires", "enables",
    "performs", "analyzes", "depends_on", "part_of", "connected_to",
}

# ---------------------------------------------------------------------------
# Verb lemma  ->  relation type
# ---------------------------------------------------------------------------
VERB_RELATION_MAP = {
    # is_a  (handled specially via copula patterns)
    # contains
    "contain": "contains", "include": "contains", "have": "contains",
    "comprise": "contains", "consist": "contains", "encompass": "contains",
    "incorporate": "contains", "embed": "contains",
    # uses
    "use": "uses", "utilize": "uses", "employ": "uses", "apply": "uses",
    "leverage": "uses", "adopt": "uses", "exploit": "uses",
    # produces
    "produce": "produces", "generate": "produces", "create": "produces",
    "yield": "produces", "output": "produces", "build": "produces",
    "develop": "produces", "construct": "produces", "compose": "produces",
    "derive": "produces", "synthesize": "produces",
    # stores
    "store": "stores", "save": "stores", "keep": "stores",
    "maintain": "stores", "hold": "stores", "retain": "stores",
    "cache": "stores", "persist": "stores", "preserve": "stores",
    # improves
    "improve": "improves", "enhance": "improves", "optimize": "improves",
    "boost": "improves", "increase": "improves", "upgrade": "improves",
    "augment": "improves", "refine": "improves", "strengthen": "improves",
    # reduces
    "reduce": "reduces", "decrease": "reduces", "minimize": "reduces",
    "lower": "reduces", "diminish": "reduces", "lessen": "reduces",
    "shrink": "reduces", "compress": "reduces", "simplify": "reduces",
    # represents
    "represent": "represents", "denote": "represents", "symbolize": "represents",
    "indicate": "represents", "depict": "represents", "describe": "represents",
    "define": "represents", "model": "represents", "illustrate": "represents",
    "characterize": "represents", "encode": "represents",
    # requires
    "require": "requires", "need": "requires", "demand": "requires",
    "necessitate": "requires", "expect": "requires",
    # enables
    "enable": "enables", "allow": "enables", "permit": "enables",
    "facilitate": "enables", "support": "enables", "help": "enables",
    "empower": "enables", "provide": "enables",
    # performs
    "perform": "performs", "execute": "performs", "carry": "performs",
    "conduct": "performs", "run": "performs", "implement": "performs",
    "accomplish": "performs", "achieve": "performs", "handle": "performs",
    # analyzes
    "analyze": "analyzes", "analyse": "analyzes", "examine": "analyzes",
    "study": "analyzes", "investigate": "analyzes", "evaluate": "analyzes",
    "assess": "analyzes", "process": "analyzes", "parse": "analyzes",
    "inspect": "analyzes", "monitor": "analyzes", "measure": "analyzes",
    "compute": "analyzes", "calculate": "analyzes",
    # depends_on
    "depend": "depends_on", "rely": "depends_on", "hinge": "depends_on",
    # part_of
    "belong": "part_of",
    # connected_to
    "connect": "connected_to", "relate": "connected_to", "link": "connected_to",
    "associate": "connected_to", "interact": "connected_to",
    "communicate": "connected_to", "integrate": "connected_to",
    "map": "connected_to", "transform": "connected_to", "convert": "connected_to",
    "translate": "connected_to", "transfer": "connected_to",
    "send": "connected_to", "receive": "connected_to",
    "call": "connected_to", "invoke": "connected_to",
    "access": "connected_to", "query": "connected_to",
    "fetch": "connected_to", "retrieve": "connected_to",
    "load": "connected_to", "read": "connected_to", "write": "connected_to",
    "show": "represents",
    "prove": "represents",
    "explain": "represents",
    "form": "is_a",
    "consist": "contains",
    "indicate": "represents",
}

# Prepositional / copula phrase -> relation
PREP_RELATION_MAP = {
    "subset of": "is_a",
    "type of": "is_a",
    "branch of": "is_a",
    "form of": "is_a",
    "kind of": "is_a",
    "subclass of": "is_a",
    "subtype of": "is_a",
    "instance of": "is_a",
    "specialization of": "is_a",
    "extension of": "is_a",
    "variation of": "is_a",
    "variant of": "is_a",
    "category of": "contains",
    "part of": "part_of",
    "component of": "part_of",
    "element of": "part_of",
    "member of": "part_of",
    "portion of": "part_of",
    "aspect of": "part_of",
    "feature of": "part_of",
    "based on": "depends_on",
    "built on": "depends_on",
    "derived from": "is_a",
    "evolved from": "is_a",
    "used in": "connected_to",
    "used for": "connected_to",
    "used by": "connected_to",
    "responsible for": "performs",
    "capable of": "performs",
    "designed for": "connected_to",
    "related to": "connected_to",
    "connected to": "connected_to",
    "known as": "is_a",
    "referred to as": "is_a",
    "called": "is_a",
    "similar to": "connected_to",
    "equivalent to": "is_a",
    "applied to": "connected_to",
    "combined with": "connected_to",
}

# ---------------------------------------------------------------------------
# Determiners / pronouns to strip from the start of phrases
# ---------------------------------------------------------------------------
STRIP_PREFIXES = [
    "the ", "a ", "an ", "this ", "that ", "these ", "those ",
    "my ", "your ", "his ", "her ", "its ", "our ", "their ",
    "some ", "any ", "each ", "every ", "all ", "many ", "few ",
    "several ", "most ", "such ", "what ", "which ", "whose ",
    "certain ", "various ", "different ", "specific ", "particular ",
]

# ---------------------------------------------------------------------------
# Formula patterns
# ---------------------------------------------------------------------------
FORMULA_PATTERN = re.compile(
    r"(?:"
    r"[A-Za-z0-9_]+\s*[=<>!]+\s*.+"                    # X = Y, A >= B, etc.
    r"|[A-Za-z0-9_]+\s*(?:→|->)\s*.+"                 # arrows
    r"|[A-Za-z0-9_]+\s*\([^)]*\)"                     # f(x), P(x,y)
    r"|\$[^$]+\$"                                     # $LaTeX$
    r"|\\[a-zA-Z]+\{[^}]*\}"                          # \frac{a}{b}
    r"|[A-Za-z0-9_]+\s*[\+\-\*/\^]\s*[A-Za-z0-9_]+"   # a + b, x^2
    r"|\[[^\]]+\]"                                    # vectors [1,2,3]
    r"|O\s*\([^\)]+\)"                                # Big-O notation
    r")",
    re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def normalize_concept(text: str) -> str:
    """Normalize a concept phrase: strip determiners, title-case, clean up."""
    if not text:
        return ""

    text = text.strip()
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Strip leading determiners / pronouns (case-insensitive)
    lower = text.lower()
    changed = True
    while changed:
        changed = False
        for prefix in STRIP_PREFIXES:
            if lower.startswith(prefix):
                text = text[len(prefix):]
                lower = text.lower()
                changed = True

    text = text.strip()
    if not text:
        return ""

    # Title-case each word
    words = text.split()
    result = " ".join(w.capitalize() for w in words)
    return result


def is_valid_concept(text: str) -> bool:
    """Return True if *text* is a meaningful concept worth keeping."""
    if not text or len(text.strip()) < 2:
        return False

    lower = text.lower().strip()

    if lower in MEANINGLESS_CONCEPTS:
        return False

    # Must contain at least one alphabetic character
    if not any(c.isalpha() for c in text):
        return False

    # Reject single generic words
    if len(lower.split()) == 1 and lower in GENERIC_SINGLE_WORDS:
        return False

    return True


def detect_formulas(text: str) -> list:
    """Return a list of formula strings found in *text*."""
    return FORMULA_PATTERN.findall(text)


def validate_input(text: str) -> dict:
    """Validate input text against limits. Return dict with status & message."""
    if not text or not text.strip():
        return {"valid": False, "message": "Input text is empty."}

    char_count = len(text)
    word_count = len(text.split())

    warnings = []
    if char_count > MAX_CHARACTERS:
        warnings.append(
            f"Text exceeds {MAX_CHARACTERS} character limit "
            f"({char_count} characters). It will be truncated."
        )
    if word_count > MAX_WORDS:
        warnings.append(
            f"Text exceeds {MAX_WORDS} word limit "
            f"({word_count} words). It will be truncated."
        )

    if warnings:
        return {"valid": True, "warnings": warnings}

    return {"valid": True, "warnings": []}


def truncate_text(text: str) -> str:
    """Truncate text to stay within limits."""
    words = text.split()
    if len(words) > MAX_WORDS:
        words = words[:MAX_WORDS]
        text = " ".join(words)

    if len(text) > MAX_CHARACTERS:
        text = text[:MAX_CHARACTERS]

    return text
