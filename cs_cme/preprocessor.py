import re

def preprocess_document(text):

    # 1️⃣ Remove enumeration like "1. "
    text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)

    # 2️⃣ Remove standalone numeric lines
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    # 3️⃣ Normalize slash-separated systems (robust)
    # Handles: X/Y System or X/Y Systems
    # 3️⃣ Normalize slash-separated systems (case-insensitive)

    def expand_slash(match):
        first = match.group(1)
        second = match.group(2)
        system_word = match.group(3)
        return f"{first} {system_word} and {second} {system_word}"

    text = re.sub(
        r'\b([A-Za-z]+)\/([A-Za-z]+)\s+(System|Systems)\b',
        expand_slash,
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(
        r'\b([A-Za-z]+)\/([A-Za-z]+)\s+(System|Systems)\b',
        expand_slash,
        text
    )

    # 4️⃣ Normalize whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()