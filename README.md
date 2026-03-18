# Interactive Concept Map Generator using CS-CME

**CS-CME** = Context-Sensitive Concept Map Extraction Engine

Automatically generates interactive concept maps (mind maps / knowledge graphs) from text or PDF documents using Natural Language Processing.

---

## Features

- **NLP-powered concept extraction** using spaCy dependency parsing
- **Context-aware relation extraction** with pronoun resolution
- **Hierarchical heading detection** for document structure
- **15 semantic relation types** (is_a, contains, uses, produces, etc.)
- **PageRank-style concept importance ranking**
- **Louvain community detection** for concept clustering
- **Interactive D3.js visualization** with:
  - Zoom and pan
  - Node search
  - Node tooltips
  - Description panel
  - Edge labels
  - Mini-map navigation
  - Dark / light theme
  - Export JSON
  - Export PNG
  - Physics toggle
- **Evaluation module** with Precision, Recall, F1 Score

---

## Project Structure

```
interactive_concept_map_generator/
├── backend/
│   ├── cs_cme_engine.py           # Main engine + Flask server
│   ├── concept_extractor.py       # Concept extraction & normalization
│   ├── meaning_analyzer.py        # Relation extraction & context tracking
│   ├── heading_segmenter.py       # Heading detection & hierarchy
│   ├── graph_builder.py           # Graph construction, PageRank, Louvain
│   ├── document_graph_builder.py  # Pipeline orchestrator
│   ├── preprocessor.py            # Text cleaning & PDF extraction
│   └── utils.py                   # Constants & utility functions
├── frontend/
│   ├── index.html                 # Main page
│   ├── script.js                  # D3.js visualization
│   └── styles.css                 # Styles (dark/light theme)
├── evaluation/
│   ├── evaluate.py                # Evaluation script
│   ├── gold/                      # Gold-standard annotations
│   └── predictions/               # Predicted outputs
├── test_inputs/                   # Sample input documents
├── outputs/                       # Generated outputs
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Download the spaCy English model

```bash
python -m spacy download en_core_web_sm
```

---

## Usage

### Web Server (recommended)

Start the Flask web server:

```bash
cd backend
python cs_cme_engine.py --serve
```

Open your browser to **http://localhost:5000**.

You can:
- Paste text directly
- Upload a `.txt` or `.pdf` file
- View and interact with the generated concept map
- Export as JSON or PNG

### Command Line

Process a text file:

```bash
cd backend
python cs_cme_engine.py --input ../test_inputs/sample_ai.txt --output ../outputs/output.json
```

Process direct text:

```bash
cd backend
python cs_cme_engine.py --text "Machine learning is a subset of artificial intelligence."
```

### API

Send a POST request:

```bash
curl -X POST http://localhost:5000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Machine learning is a subset of artificial intelligence."}'
```

Upload a file:

```bash
curl -X POST http://localhost:5000/api/extract \
  -F "file=@../test_inputs/sample_ai.txt"
```

---

## Evaluation

Run the evaluation script to compare predicted relations against gold-standard annotations:

```bash
cd evaluation
python evaluate.py
```

Or evaluate specific files:

```bash
python evaluate.py --gold gold/sample_ai.json --pred predictions/sample_ai.json
```

### Target Performance

| Metric    | Target |
|-----------|--------|
| Precision | >= 0.75 |
| Recall    | >= 0.70 |
| F1 Score  | >= 0.72 |

---

## Input Limits

| Limit          | Value   |
|----------------|---------|
| Max characters | 15,000  |
| Max words      | 2,000   |
| Max PDF pages  | 10      |

---

## Technologies

- **Backend:** Python, spaCy, NLTK, Flask
- **Frontend:** HTML, CSS, JavaScript, D3.js
- **Graph analysis:** NetworkX, python-louvain

---

## Output Format

```json
{
  "nodes": [
    {
      "id": "Machine Learning",
      "frequency": 4,
      "descriptions": ["Machine learning is a subset of artificial intelligence."],
      "formulas": [],
      "cluster": 0
    }
  ],
  "edges": [
    {
      "source": "Machine Learning",
      "target": "Artificial Intelligence",
      "relation": "is_a",
      "negated": false
    }
  ]
}
```

---

## License

This project is provided for academic and educational purposes.
