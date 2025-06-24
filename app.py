import os
import uuid
import tempfile
import threading
import zipfile
import shutil
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PyPDF2 import PdfReader
from openai import OpenAI

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
results = {}

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)

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

def process_analysis(job_id, file_storage):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, file_storage.filename)
            file_storage.save(path)

            if zipfile.is_zipfile(path):
                extracted_dir = os.path.join(tmpdir, "extracted")
                os.makedirs(extracted_dir, exist_ok=True)
                with zipfile.ZipFile(path, "r") as z:
                    z.extractall(extracted_dir)

                texts = []
                for root, _, files in os.walk(extracted_dir):
                    for f in files:
                        if f.lower().endswith(".pdf"):
                            try:
                                reader = PdfReader(os.path.join(root, f))
                                text = "".join([p.extract_text() or "" for p in reader.pages])
                                texts.append(f"Fil: {f}\n{text.strip()}")
                            except Exception as e:
                                texts.append(f"Fil: {f}\nFejl: {str(e)}")
                full_text = "\n\n".join(texts)
            else:
                reader = PdfReader(path)
                full_text = "".join([p.extract_text() or "" for p in reader.pages])

        with app.app_context():
            keywords = [k.text for k in Keyword.query.all()]
            rules = [r.text for r in Rule.query.all()]
            laws = [l.name for l in Law.query.all()]

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du er en juridisk assistent med speciale i familieret."},
                {"role": "user", "content": f"""Analyser følgende tekst:

1. Er følgende nøgleord nævnt: {", ".join(keywords)}
2. Er følgende regler nævnt eller overtrådt: {", ".join(rules)}
3. Er følgende love nævnt, fulgt eller brudt: {", ".join(laws)}
4. Giv en kort opsummering på dansk om overholdelse af lovgivning og evt. forskelsbehandling.

Tekst:
{full_text[:4000]}
"""}
            ],
            max_tokens=1000
        )

        answer = response.choices[0].message.content
        usage = response.usage.total_tokens
        price_dkk = usage * 0.00032
        result = f"{answer.strip()}\n\nAI-analysepris baseret på tokenforbrug: {price_dkk:.2f} DKK"
        results[job_id] = result
    except Exception as e:
        results[job_id] = f"Fejl under analyse: {str(e)}"

@app.route("/analyze", methods=["POST"])
def analyze_async():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    job_id = str(uuid.uuid4())
    threading.Thread(target=process_analysis, args=(job_id, file)).start()
    return jsonify({"job_id": job_id, "message": "Analyse igangsat – vent venligst ..."})

@app.route("/result/<job_id>", methods=["GET"])
def get_result(job_id):
    if job_id not in results:
        return jsonify({"status": "pending"})
    return jsonify({"status": "done", "result": results[job_id]})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=10000, debug=True)
