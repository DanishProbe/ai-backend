import os
import uuid
import zipfile
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PyPDF2 import PdfReader
from openai import OpenAI
import threading
import time

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Result store for background analysis
results = {}

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

@app.before_request
def create_tables():
    db.create_all()

@app.route("/prompt", methods=["GET", "POST"])
def handle_prompt():
    if request.method == "GET":
        prompt = Prompt.query.first()
        return jsonify({"text": prompt.text if prompt else ""})
    elif request.method == "POST":
        data = request.json
        Prompt.query.delete()
        db.session.add(Prompt(text=data["text"]))
        db.session.commit()
        return jsonify({"message": "Prompt saved"})

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    job_id = str(uuid.uuid4())
    results[job_id] = "Analyzing..."

    def analyze_job(job_id, file):
        with app.app_context():
            try:
                temp_dir = tempfile.mkdtemp()
                file_path = os.path.join(temp_dir, file.filename)
                file.save(file_path)

                text = ""
                if zipfile.is_zipfile(file_path):
                    with zipfile.ZipFile(file_path) as z:
                        for name in z.namelist():
                            if name.lower().endswith(".pdf"):
                                with z.open(name) as pdf_file:
                                    reader = PdfReader(pdf_file)
                                    for page in reader.pages:
                                        text += page.extract_text() or ""
                else:
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        text += page.extract_text() or ""

                prompt_entry = Prompt.query.first()
                if not prompt_entry:
                    results[job_id] = "Fejl: Ingen prompt gemt"
                    return

                prompt = prompt_entry.text.strip()
                full_prompt = f"{prompt}

PDF tekst:
{text[:8000]}"

                start_time = time.time()
                completion = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{"role": "user", "content": full_prompt}],
                    max_tokens=2000
                )
                duration = time.time() - start_time
                tokens_used = completion.usage.total_tokens
                cost = round(tokens_used * 0.0003, 2)  # Example DKK cost

                response_text = completion.choices[0].message.content.strip()
                results[job_id] = f"{response_text}

Tid: {round(duration, 1)} sekunder – Pris: {cost} DKK"
            except Exception as e:
                results[job_id] = f"Fejl ved behandling: {str(e)}"

    thread = threading.Thread(target=analyze_job, args=(job_id, file))
    thread.start()

    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>")
def get_result(job_id):
    result = results.get(job_id)
    if result is None:
        return jsonify({"error": "Ugyldigt job ID"}), 404
    elif result == "Analyzing...":
        return "", 202
    return jsonify({"result": result})

if __name__ == "__main__":
    print("Starter backend på port 10000...")
    app.run(host="0.0.0.0", port=10000, debug=True)