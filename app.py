
import os
import uuid
import shutil
import zipfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
import openai
import time

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI()

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

analysis_results = {}

@app.route("/prompt", methods=["GET", "POST"])
def prompt_handler():
    if request.method == "GET":
        prompt = Prompt.query.first()
        return jsonify({"prompt": prompt.text if prompt else ""})
    elif request.method == "POST":
        data = request.json
        Prompt.query.delete()
        db.session.add(Prompt(text=data.get("prompt", "")))
        db.session.commit()
        return jsonify({"message": "Prompt gemt"})

def extract_text_from_pdf(path):
    reader = PdfReader(path)
    return "\n".join([page.extract_text() or "" for page in reader.pages])

def analyze_text_with_openai(prompt_text, document_text):
    messages = [
        {"role": "system", "content": "Du er en juridisk assistent med speciale i familieret."},
        {"role": "user", "content": f"{prompt_text}\n\nDokument:\n{document_text[:10000]}"}
    ]
    start = time.time()
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,
        max_tokens=2000
    )
    duration = round(time.time() - start, 1)
    tokens_used = response.usage.total_tokens
    cost_dkk = round(tokens_used * 0.0003, 2)
    return response.choices[0].message.content + f"\n\nTid brugt: {duration} sekunder\nAI-analysepris: {cost_dkk} DKK"

@app.route("/analyze", methods=["POST"])
def analyze_file():
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": "Ingen fil modtaget"}), 400

    job_id = str(uuid.uuid4())
    analysis_results[job_id] = {"status": "processing"}

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(uploaded.filename))
    uploaded.save(file_path)

    from threading import Thread
    def background_analysis():
        try:
            prompt = Prompt.query.first().text if Prompt.query.first() else "Analyser dette dokument."
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
                    os.makedirs(zip_folder, exist_ok=True)
                    zip_ref.extractall(zip_folder)

                result_text = ""
                for fname in os.listdir(zip_folder):
                    if fname.lower().endswith(".pdf"):
                        fpath = os.path.join(zip_folder, fname)
                        doc_text = extract_text_from_pdf(fpath)
                        result_text += f"\n\n--- Analyse af {fname} ---\n"
                        result_text += analyze_text_with_openai(prompt, doc_text)

                shutil.rmtree(zip_folder)
                analysis_results[job_id] = {"status": "done", "result": result_text}
            else:
                text = extract_text_from_pdf(file_path)
                result = analyze_text_with_openai(prompt, text)
                analysis_results[job_id] = {"status": "done", "result": result}
            os.remove(file_path)
        except Exception as e:
            analysis_results[job_id] = {"status": "error", "error": str(e)}

    Thread(target=background_analysis).start()
    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>", methods=["GET"])
def get_result(job_id):
    result = analysis_results.get(job_id)
    if not result:
        return jsonify({"status": "not_found"}), 404
    return jsonify(result)

if __name__ == "__main__":
    print("Starter backend på port 10000...")
    app.run(host="0.0.0.0", port=10000, debug=True)
