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

@app.route("/")
def healthcheck():
    return "Backend kører OK"

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
    print(f"[{job_id}] Fil gemt: {temp_path}")

    def extract_and_analyze():
        with app.app_context():
            try:
                print(f"[{job_id}] Start analyse")
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
                keywords = [k.text for k in Keyword.query.all()]
                rules = [r.text for r in Rule.query.all()]
                laws = [l.name for l in Law.query.all()]
                print(f"[{job_id}] Nøgleord: {keywords}")
                print(f"[{job_id}] Regler: {rules}")
                print(f"[{job_id}] Love: {laws}")

                base_prompt = (
                    f"Analyser følgende tekst:\n"
                    f"1. Findes nogen af følgende nøgleord: {', '.join(keywords)}\n"
                    f"2. Findes eller overtrædes nogen af følgende regler: {', '.join(rules)}\n"
                    f"3. Nævnes, følges eller brydes nogen af følgende love: {', '.join(laws)}\n"
                    f"Svar meget kort med 'ja' eller 'nej' for hver kategori.\n"
                    f"Tekst: {full_content[:4000]}"
                )
                print(f"[{job_id}] Prompt step 1:
{base_prompt[:1000]}...")

                step1 = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Du er en juridisk assistent."},
                        {"role": "user", "content": base_prompt}
                    ],
                    max_tokens=300
                )
                s1_result = step1.choices[0].message.content.lower()
                token1 = step1.usage.total_tokens
                print(f"[{job_id}] Svar step 1: {s1_result}")
                if "ja" not in s1_result:
                    result_store[job_id] = f"Intet relevant fundet. (Brugt: {token1} tokens ≈ {token1 * 0.00012:.2f} DKK)"
                    print(f"[{job_id}] Analyse stoppet – intet fundet.")
                    return

                full_prompt = (
                    f"Du er juridisk assistent med speciale i familieret. Lav en struktureret analyse som følger:\n"
                    f"- Kort resume af dokumentet (2-3 linjer)\n"
                    f"- Nøgleord fundet (ja/nej for hver): {', '.join(keywords)}\n"
                    f"- Regler nævnt eller overtrådt (ja/nej for hver): {', '.join(rules)}\n"
                    f"- Love nævnt/fulgt/brudt (ja/nej og evt. §-henvisninger): {', '.join(laws)}\n"
                    f"- Konklusion om overholdelse af lovgivning og forskelsbehandling\n"
                    f"Tekst: {full_content[:8000]}"
                )
                print(f"[{job_id}] Prompt step 2 (forkortet): {full_prompt[:400]}...")
                step2 = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "Du er en juridisk assistent."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=1000
                )
                token2 = step2.usage.total_tokens
                total_price = token1 * 0.00012 + token2 * 0.00032
                final_result = step2.choices[0].message.content
                result_store[job_id] = f"{final_result.strip()}\n\nAI-analysepris: {total_price:.2f} DKK"
                print(f"[{job_id}] Analyse færdig – result gemt.")
            except Exception as e:
                result_store[job_id] = f"Fejl i analyse: {str(e)}"
                print(f"[{job_id}] Fejl i analyse: {str(e)}")
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
    print("Starter backend på port 10000...")
    app.run(host="0.0.0.0", port=10000, debug=True)
