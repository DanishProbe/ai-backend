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

@app.route("/analyze", methods=["POST"])
def analyze_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    filename = file.filename
    if not filename:
        return jsonify({"error": "No selected file"}), 400

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    texts = []
    if filename.lower().endswith(".zip"):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            extract_dir = os.path.join(app.config['UPLOAD_FOLDER'], "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            zip_ref.extractall(extract_dir)
            for name in zip_ref.namelist():
                if name.lower().endswith(".pdf"):
                    try:
                        reader = PdfReader(os.path.join(extract_dir, name))
                        content = ""
                        for page in reader.pages:
                            content += page.extract_text() or ""
                        texts.append((name, content[:2000]))
                    except Exception as e:
                        texts.append((name, f"Fejl ved læsning: {str(e)}"))
    elif filename.lower().endswith(".pdf"):
        reader = PdfReader(file_path)
        content = ""
        for page in reader.pages:
            content += page.extract_text() or ""
        texts.append((filename, content[:2000]))
    else:
        return jsonify({"error": "Kun PDF og ZIP understøttes"}), 400

    combined_report = ""
    for fname, content in texts:
        combined_report += f"--- {fname} ---\n{content}\n\n"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in combined_report.split("\n"):
        pdf.multi_cell(0, 10, line)
    output_pdf = os.path.join(app.config['UPLOAD_FOLDER'], "rapport.pdf")
    pdf.output(output_pdf)

    return send_file(output_pdf, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)