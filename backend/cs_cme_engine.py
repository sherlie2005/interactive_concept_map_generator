"""
CS-CME Engine – Flask web server for the Interactive Concept Map Generator.

Endpoints
---------
GET  /                  Serve the frontend
POST /api/extract       Accept text / file, return concept-map JSON
GET  /api/health        Health check
"""

import os
import sys
import json

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Ensure sibling modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_graph_builder import process_text, process_pdf, get_nlp
from utils import MAX_CHARACTERS, MAX_WORDS, MAX_PDF_PAGES

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend"),
    static_url_path="",
)
CORS(app)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the main frontend page."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """Serve other static frontend files."""
    return send_from_directory(app.static_folder, path)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/extract", methods=["POST"])
def extract():
    """
    Accept text or file upload and return the concept map.

    Supported content types:
      - application/json  → {"text": "..."}
      - multipart/form-data → file upload (txt or pdf) OR text field
    """
    try:
        raw_text = None
        pdf_bytes = None

        if request.content_type and "application/json" in request.content_type:
            data = request.get_json(force=True)
            raw_text = data.get("text", "")
        else:
            # Multipart form
            if "file" in request.files:
                uploaded = request.files["file"]
                filename = uploaded.filename.lower() if uploaded.filename else ""
                if filename.endswith(".pdf"):
                    pdf_bytes = uploaded.read()
                elif filename.endswith(".txt"):
                    raw_text = uploaded.read().decode("utf-8", errors="replace")
                else:
                    return jsonify({
                        "error": "Unsupported file type. Please upload a .txt or .pdf file."
                    }), 400
            elif "text" in request.form:
                raw_text = request.form["text"]
            else:
                return jsonify({
                    "error": "No input provided. Send JSON with 'text' key, "
                             "or upload a file via 'file' field, "
                             "or send text via 'text' form field."
                }), 400

        # Process
        if pdf_bytes:
            result = process_pdf(pdf_bytes)
        elif raw_text:
            result = process_text(raw_text)
        else:
            return jsonify({"error": "Empty input."}), 400

        return jsonify(result)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Save output helper
# ---------------------------------------------------------------------------

def save_output(result: dict, output_path: str):
    """Save the concept map JSON to a file."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Output saved to {output_path}")


# ---------------------------------------------------------------------------
# CLI mode
# ---------------------------------------------------------------------------

def main():
    """Run as CLI or start web server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CS-CME Engine – Interactive Concept Map Generator"
    )
    parser.add_argument(
        "--serve", action="store_true",
        help="Start the Flask web server (default: port 5000)"
    )
    parser.add_argument(
        "--port", type=int, default=5000,
        help="Port for the web server"
    )
    parser.add_argument(
        "--input", "-i", type=str,
        help="Path to input file (txt or pdf)"
    )
    parser.add_argument(
        "--text", "-t", type=str,
        help="Direct text input"
    )
    parser.add_argument(
        "--output", "-o", type=str,
        default=os.path.join(os.path.dirname(__file__), "..", "outputs", "output.json"),
        help="Path to save the output JSON"
    )

    args = parser.parse_args()

    if args.serve:
        print(f"Starting CS-CME web server on http://localhost:{args.port}")
        print("Loading NLP model...")
        get_nlp()  # Pre-load
        print("NLP model loaded. Server ready.")
        app.run(host="0.0.0.0", port=args.port, debug=False)
        return

    # CLI processing
    if args.input:
        filepath = args.input
        if filepath.lower().endswith(".pdf"):
            with open(filepath, "rb") as f:
                result = process_pdf(f.read())
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                result = process_text(f.read())
    elif args.text:
        result = process_text(args.text)
    else:
        print("No input provided. Use --serve to start the web server,")
        print("or provide --input <file> or --text '<text>'.")
        print()
        parser.print_help()
        return

    # Print summary
    stats = result.get("stats", {})
    print(f"\n--- CS-CME Results ---")
    print(f"Sentences processed: {stats.get('total_sentences', 0)}")
    print(f"Concepts extracted:  {stats.get('total_concepts_extracted', 0)}")
    print(f"Relations found:     {stats.get('total_relations_extracted', 0)}")
    print(f"Nodes in map:        {stats.get('concepts_in_map', 0)}")
    print(f"Edges in map:        {stats.get('edges_in_map', 0)}")
    print(f"Communities:         {stats.get('communities_detected', 0)}")

    warnings = result.get("warnings", [])
    if warnings:
        print(f"\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    # Save
    save_output(result, args.output)


if __name__ == "__main__":
    main()
