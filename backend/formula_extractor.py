import re

def extract_formulas(text: str):
    """
    Extract mathematical formulas from raw text.
    General patterns only — works for ANY academic document.
    Catches equations, sqrt, argmax, vectors, Big-O, LaTeX-style, etc.
    """
    # Normalize
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    formulas = []

    patterns = [
        # General equations with = 
        r"[A-Za-z0-9_() ]+\s*=\s*[^\n=]{5,120}",
        
        # sqrt expressions (with or without ...)
        r"[A-Za-z0-9_() ]+\s*=\s*sqrt\s*\([^\)]+\)",
        
        # argmax / summation style
        r"[a-z_]+\s*=\s*argmax",
        
        # Function calls like f(x), P(x,y)
        r"[A-Za-z_][A-Za-z0-9_]*\s*\([^\)]*\)",
        
        # Big-O notation
        r"O\s*\([^\)]+\)",
        
        # Vector / array style
        r"\[[^\]]+\]",
        
        # Any math with ^ or powers
        r"[A-Za-z0-9_]+\s*\^\s*\d+",
        
        # LaTeX-style (for safety)
        r"\\[a-zA-Z]+\{[^}]*\}"
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            m = m.strip()
            if 8 < len(m) < 180 and m not in formulas:
                formulas.append(m)

    return formulas