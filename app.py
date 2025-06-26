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

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

@app.before_request
def reset_db():
    db.drop_all()
    db.create_all()

@app.route("/")
def healthcheck():
    return "Backend kører OK"

@app.route("/prompt", methods=["GET", "POST"])
def manage_prompt():
    if request.method == "GET":
        prompt = Prompt.query.first()
        return jsonify({"text": prompt.text if prompt else ""})
    else:
        data = request.json
        Prompt.query.delete()
        db.session.add(Prompt(text=data["text"]))
        db.session.commit()
        return jsonify({"message": "Prompt gemt"})

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
        with app.app_context():
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

                base = Prompt.query.first()
                prompt_text = base.text if base else "Analyser venligst følgende tekst:"
                full_prompt = f"{prompt_text}\n\n{full_content[:8000]}"

                step = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "Du er en juridisk assistent."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=1500
                )
                token_use = step.usage.total_tokens
                result = step.choices[0].message.content
                result_store[job_id] = f"{result}\n\nAI-analysepris: {token_use * 0.00032:.2f} DKK"
            except Exception as e:
                result_store[job_id] = f"Fejl i analyse: {str(e)}"
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
    print("Starter backend på port 10000...")
    app.run(host="0.0.0.0", port=10000, debug=True)
