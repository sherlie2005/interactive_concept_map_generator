import re

def preprocess_document(text):
    # 1️⃣ Remove enumeration like "1. ", "2. "
    text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)

    # 2️⃣ Remove standalone numbers
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    # 3️⃣ Normalize slash-separated systems
    text = re.sub(
        r'(\b[A-Za-z]+)\/([A-Za-z]+)(\s+System\b)',
        r'\1 System and \2 System',
        text
    )

    # 4️⃣ Normalize whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()