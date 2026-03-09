from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from cs_cme_engine import run_cs_cme
from document_graph_builder import build_document_graph

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return render_template("index.htm")


def extract_pdf_text(file_storage):
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF support is not installed. Run: pip install pypdf") from exc

    reader = PdfReader(file_storage.stream)
    parts = []

    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(text)

    return "\n".join(parts)


def read_input_text():
    content_type = request.content_type or ""

    if content_type.startswith("multipart/form-data"):
        typed_text = (request.form.get("text") or "").strip()
        uploaded_pdf = request.files.get("pdf")

        if uploaded_pdf and uploaded_pdf.filename:
            filename = uploaded_pdf.filename.lower()
            if not filename.endswith(".pdf"):
                return None, (jsonify({"error": "Only PDF files are supported for upload."}), 400)

            try:
                pdf_text = extract_pdf_text(uploaded_pdf)
            except RuntimeError as exc:
                return None, (jsonify({"error": str(exc)}), 400)
            except Exception:
                return None, (jsonify({"error": "Unable to read PDF content."}), 400)

            merged = f"{typed_text}\n{pdf_text}".strip()
            return merged, None

        return typed_text, None

    if content_type.startswith("application/x-www-form-urlencoded"):
        return (request.form.get("text") or "").strip(), None

    data = request.get_json(silent=True) or {}
    return (data.get("text") or "").strip(), None


@app.route("/generate", methods=["POST"])
def generate():
    text, error_response = read_input_text()
    if error_response:
        return error_response

    if not text:
        return jsonify({"error": "Provide text input or upload a PDF."}), 400

    try:
        sentence_graph = run_cs_cme(text)
        document_graph = build_document_graph(sentence_graph)
    except Exception:
        return jsonify({"error": "Failed to generate graph from the provided input."}), 500

    return jsonify(document_graph)



if __name__ == "__main__":
    app.run(debug=True)
