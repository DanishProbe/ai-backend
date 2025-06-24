import os
import zipfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PyPDF2 import PdfReader
from fpdf import FPDF

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
db = SQLAlchemy(app)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

@app.route("/rules", methods=["GET", "POST", "DELETE"])
def manage_rules():
    if request.method == "GET":
        return jsonify([{"id": r.id, "text": r.text} for r in Rule.query.all()])
    elif request.method == "POST":
        data = request.json
        rule = Rule(text=data["text"])
        db.session.add(rule)
        db.session.commit()
        return jsonify({"message": "Rule added"})
    elif request.method == "DELETE":
        data = request.json
        Rule.query.filter_by(id=data["id"]).delete()
        db.session.commit()
        return jsonify({"message": "Rule deleted"})

@app.route("/laws", methods=["GET", "POST", "DELETE"])
def manage_laws():
    if request.method == "GET":
        return jsonify([{"id": l.id, "name": l.name} for l in Law.query.all()])
    elif request.method == "POST":
        data = request.json
        law = Law(name=data["name"])
        db.session.add(law)
        db.session.commit()
        return jsonify({"message": "Law added"})
    elif request.method == "DELETE":
        data = request.json
        Law.query.filter_by(id=data["id"]).delete()
        db.session.commit()
        return jsonify({"message": "Law deleted"})

@app.route("/keywords", methods=["GET", "POST", "DELETE"])
def manage_keywords():
    if request.method == "GET":
        return jsonify([{"id": k.id, "text": k.text} for k in Keyword.query.all()])
    elif request.method == "POST":
        data = request.json
        keyword = Keyword(text=data["text"])
        db.session.add(keyword)
        db.session.commit()
        return jsonify({"message": "Keyword added"})
    elif request.method == "DELETE":
        data = request.json
        Keyword.query.filter_by(id=data["id"]).delete()
        db.session.commit()
        return jsonify({"message": "Keyword deleted"})

@app.route("/analyze-zip", methods=["POST"])
def analyze_zip():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file or not file.filename.endswith(".zip"):
        return jsonify({"error": "Only .zip files are supported"}), 400

    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(zip_path)

    extracted_texts = []
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        extract_dir = os.path.join(app.config['UPLOAD_FOLDER'], "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        zip_ref.extractall(extract_dir)

        for name in zip_ref.namelist():
            if name.lower().endswith(".pdf"):
                try:
                    pdf_path = os.path.join(extract_dir, name)
                    reader = PdfReader(pdf_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() or ""
                    extracted_texts.append((name, text[:2000]))
                except Exception as e:
                    extracted_texts.append((name, f"Fejl ved læsning: {str(e)}"))

    combined_report = ""
    for fname, content in extracted_texts:
        combined_report += f"--- {fname} ---\n{content}\n\n"

    # Save PDF report
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in combined_report.split("\n"):
        pdf.multi_cell(0, 10, line)
    output_pdf = os.path.join(app.config['UPLOAD_FOLDER'], "analyserapport.pdf")
    pdf.output(output_pdf)

    return send_file(output_pdf, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)