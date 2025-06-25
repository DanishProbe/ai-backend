import os
import threading
import uuid
import tempfile
import zipfile
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

result_store = {}

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

def run_analysis(job_id, content):
    keywords = [k.text for k in Keyword.query.all()]
    rules = [r.text for r in Rule.query.all()]
    laws = [l.name for l in Law.query.all()]

    try:
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
{content[:4000]}
"""}
            ],
            max_tokens=1000
        )
        answer = response.choices[0].message.content
        usage = response.usage.total_tokens
        price_dkk = usage * 0.00032
        result_store[job_id] = f"{answer.strip()}\n\nAI-analysepris baseret på tokenforbrug: {price_dkk:.2f} DKK"
    except Exception as e:
        result_store[job_id] = f"Fejl i analyse: {str(e)}"

@app.route("/analyze", methods=["POST"])
def analyze_background():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = file.filename
    if not filename:
        return jsonify({"error": "No selected file"}), 400

    job_id = str(uuid.uuid4())
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    temp_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{job_id}_{filename}")
    file.save(temp_path)

    def extract_and_analyze():
        try:
            texts = []
            if filename.endswith(".zip"):
                with zipfile.ZipFile(temp_path, "r") as zip_ref:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        zip_ref.extractall(tmpdir)
                        for root, _, files in os.walk(tmpdir):
                            for name in files:
                                if name.endswith(".pdf"):
                                    path = os.path.join(root, name)
                                    reader = PdfReader(path)
                                    text = "".join([page.extract_text() or "" for page in reader.pages])
                                    texts.append(text)
            else:
                reader = PdfReader(temp_path)
                texts = [page.extract_text() or "" for page in reader.pages]

            full_content = "\n\n".join(texts)
            run_analysis(job_id, full_content)
        except Exception as e:
            result_store[job_id] = f"Fejl ved behandling: {str(e)}"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    threading.Thread(target=extract_and_analyze).start()
    return jsonify({"job_id": job_id, "message": "Analyse igangsat – vent venligst ..."}), 202

@app.route("/result/<job_id>")
def get_result(job_id):
    result = result_store.get(job_id)
    if not result:
        return jsonify({"status": "pending"})
    return jsonify({"result": result})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=10000, debug=True)
