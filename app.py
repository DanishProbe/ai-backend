import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from openai import OpenAI
import time

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rules.db"
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

@app.before_request
def ensure_db():
    db.create_all()

@app.route("/prompt", methods=["GET", "POST"])
def handle_prompt():
    if request.method == "GET":
        p = Prompt.query.first()
        return jsonify({"text": p.text if p else ""})
    else:
        data = request.json
        db.session.query(Prompt).delete()
        db.session.add(Prompt(text=data["text"]))
        db.session.commit()
        return jsonify({"message": "Gemt"})

jobs = {}

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files["file"]
    prompt = request.form.get("prompt", "")
    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing"}

    from threading import Thread
    Thread(target=process_job, args=(job_id, path, prompt)).start()

    return jsonify({"job_id": job_id}), 202

def process_job(job_id, filepath, prompt):
    try:
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        start = time.time()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du er juridisk assistent med speciale i familieret."},
                {"role": "user", "content": f"{prompt}\n\n{text[:4000]}"}
            ],
            temperature=0.2,
            max_tokens=1500
        )
        duration = time.time() - start
        dkk_price = (response.usage.total_tokens / 1000) * 0.09
        report = response.choices[0].message.content.strip()
        jobs[job_id] = {"status": "done", "result": f"{report}\n\nAI-analysepris baseret på tokenforbrug: {dkk_price:.2f} DKK"}
    except Exception as e:
        jobs[job_id] = {"status": "error", "result": str(e)}

@app.route("/result/<job_id>")
def result(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Ugyldigt job ID"}), 404
    return jsonify(job)
