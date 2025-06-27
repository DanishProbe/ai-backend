import os
import uuid
import shutil
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from openai import OpenAI

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rules.db"
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
db = SQLAlchemy(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

class JobResult:
    data = {}

@app.route("/prompt", methods=["GET", "POST"])
def manage_prompt():
    if request.method == "GET":
        prompt = Prompt.query.first()
        return jsonify({"prompt": prompt.content if prompt else ""})
    else:
        data = request.json
        Prompt.query.delete()
        db.session.commit()
        db.session.add(Prompt(content=data["prompt"]))
        db.session.commit()
        return jsonify({"message": "Prompt gemt"})

@app.route("/analyze", methods=["POST"])
def analyze_file():
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": "Ingen fil modtaget"}), 400

    job_id = str(uuid.uuid4())
    upload_path = os.path.join(app.config["UPLOAD_FOLDER"], job_id)
    os.makedirs(upload_path, exist_ok=True)

    if uploaded.filename.endswith(".zip"):
        zip_path = os.path.join(upload_path, secure_filename(uploaded.filename))
        uploaded.save(zip_path)
        shutil.unpack_archive(zip_path, upload_path)
        os.remove(zip_path)
        files = [os.path.join(upload_path, f) for f in os.listdir(upload_path) if f.endswith(".pdf")]
    else:
        file_path = os.path.join(upload_path, secure_filename(uploaded.filename))
        uploaded.save(file_path)
        files = [file_path]

    JobResult.data[job_id] = {"status": "processing"}
    from threading import Thread
    Thread(target=run_analysis, args=(files, job_id)).start()
    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>")
def get_result(job_id):
    result = JobResult.data.get(job_id)
    if not result:
        return jsonify({"error": "Ukendt job ID"}), 404
    return jsonify(result)

def run_analysis(files, job_id):
    try:
        texts = []
        for file_path in files:
            reader = PdfReader(file_path)
            text = "
".join(page.extract_text() or "" for page in reader.pages)
            texts.append(text)

        full_text = "

---

".join(texts)
        short_text = full_text[:12000]  # begrænsning for token-hensyn

        prompt_obj = Prompt.query.first()
        prompt = prompt_obj.content if prompt_obj else "Du er juridisk assistent. Analyser følgende dokument."
        messages = [
            {"role": "system", "content": "Du er en juridisk ekspert i familieret."},
            {"role": "user", "content": f"{prompt}

Dokument:
{short_text}"}
        ]

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            temperature=0.3,
            max_tokens=1800
        )

        content = response.choices[0].message.content
        tokens = response.usage.total_tokens
        price_dkk = round(tokens * 0.000265, 2)  # cirka pris
        JobResult.data[job_id] = {
            "status": "done",
            "result": content.strip() + f"\n\nAI-analysepris baseret på tokenforbrug: {price_dkk} DKK"
        }
    except Exception as e:
        JobResult.data[job_id] = {"status": "error", "error": str(e)}

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    print("Starter backend på port 10000...")
    app.run(host="0.0.0.0", port=10000, debug=True)