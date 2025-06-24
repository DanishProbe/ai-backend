import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PyPDF2 import PdfReader
import zipfile
import tempfile

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)

@app.before_first_request
def create_tables():
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
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, file.filename)
        file.save(path)

        texts = []
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, "r") as z:
                for name in z.namelist():
                    if name.lower().endswith(".pdf"):
                        with z.open(name) as f:
                            reader = PdfReader(f)
                            for page in reader.pages:
                                texts.append(page.extract_text() or "")
        else:
            reader = PdfReader(path)
            for page in reader.pages:
                texts.append(page.extract_text() or "")

        combined_text = "\n".join(texts).lower()

        keywords = [k.text.lower() for k in Keyword.query.all()]
        rules = [r.text.lower() for r in Rule.query.all()]
        laws = [l.name.lower() for l in Law.query.all()]

        result = "📄 ANALYSERAPPORT\n\n"

        found_keywords = [k for k in keywords if k in combined_text]
        found_rules = [r for r in rules if r in combined_text]
        found_laws = [l for l in laws if l in combined_text]

        result += "🔹 Fundne Søgeord:\n" + "\n".join(f"- {k}" for k in found_keywords) + "\n\n"
        result += "🔹 Regler Nævnt/Overtrådt:\n" + "\n".join(f"- {r}" for r in found_rules) + "\n\n"
        result += "🔹 Love Nævnt:\n" + "\n".join(f"- {l}" for l in found_laws) + "\n\n"

        result += "📝 Samlet Vurdering:\n"
        if not (found_keywords or found_rules or found_laws):
            result += "Ingen nøglepunkter, regler eller love fundet i dokumentet.\n"
        else:
            result += "Der er fundet indhold, der bør vurderes i forhold til gældende lovgivning og praksis.\n"

        return jsonify({"result": result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
