import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PyPDF2 import PdfReader
from fpdf import FPDF
from werkzeug.utils import secure_filename
from openai import OpenAI
import tempfile
import zipfile
import shutil

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

@app.route("/analyze", methods=["POST"])
def analyze_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)

    if filename.endswith(".zip"):
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, filename)
        file.save(zip_path)

        extracted_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extracted_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_dir)

        texts = []
        for root, _, files in os.walk(extracted_dir):
            for f in files:
                if f.endswith(".pdf"):
                    path = os.path.join(root, f)
                    reader = PdfReader(path)
                    text = "".join([page.extract_text() or "" for page in reader.pages])
                    texts.append(f"Fil: {f}\n{text.strip()}")

        full_text = "\n\n".join(texts)
        shutil.rmtree(temp_dir)
    else:
        reader = PdfReader(file)
        full_text = "".join([page.extract_text() or "" for page in reader.pages])

    keywords = [k.text for k in Keyword.query.all()]
    rules = [r.text for r in Rule.query.all()]
    laws = [l.name for l in Law.query.all()]

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du er en juridisk assistent med speciale i familieret."},
                {"role": "user", "content": f"Analyser følgende tekst:

"
                                            f"1. Er følgende nøgleord nævnt: {', '.join(keywords)}
"
                                            f"2. Er følgende regler nævnt eller overtrådt: {', '.join(rules)}
"
                                            f"3. Er følgende love nævnt, fulgt eller brudt: {', '.join(laws)}
"
                                            f"4. Giv en kort opsummering på dansk om overholdelse af lovgivning og evt. forskelsbehandling.

"
                                            f"Tekst:
{full_text[:4000]}"}
            ],
            max_tokens=1000
        )
        answer = response.choices[0].message.content
        usage = response.usage.total_tokens
        price_dkk = usage * 0.00032  # fx 0.32 øre per token
        full_result = f"{answer.strip()}

AI-analysepris baseret på tokenforbrug: {price_dkk:.2f} DKK"
        return jsonify({"result": full_result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=10000, debug=True)
