
import os
import uuid
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import openai

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

class ResultStore:
    def __init__(self):
        self.store = {}

    def set(self, job_id, value):
        self.store[job_id] = value

    def get(self, job_id):
        return self.store.get(job_id, {"status": "processing"})

results = ResultStore()

@app.before_request
def create_tables():
    db.create_all()

@app.route("/prompt", methods=["GET", "POST"])
def handle_prompt():
    if request.method == "GET":
        with app.app_context():
            existing = Prompt.query.first()
            return jsonify({"text": existing.text if existing else ""})
    else:
        data = request.get_json()
        with app.app_context():
            Prompt.query.delete()
            db.session.add(Prompt(text=data["text"]))
            db.session.commit()
        return jsonify({"message": "Gemt"})

def analyze_text(job_id, text, prompt):
    try:
        full_prompt = f"{prompt}\n\n{text[:4000]}"
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Du er en juridisk ekspert."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=2000
        )
        answer = response.choices[0].message.content
        price = 0.01  # dummy price
        result = f"{answer}\n\nAI-analysepris baseret på tokenforbrug: {price:.2f} DKK"
        results.set(job_id, {"status": "done", "result": result})
    except Exception as e:
        results.set(job_id, {"status": "error", "error": str(e)})

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(f.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    f.save(file_path)

    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        text = file.read()

    with app.app_context():
        prompt_obj = Prompt.query.first()
        if not prompt_obj:
            return jsonify({"error": "Ingen prompt gemt"}), 500
        prompt = prompt_obj.text

    job_id = str(uuid.uuid4())
    threading.Thread(target=analyze_text, args=(job_id, text, prompt)).start()
    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>")
def get_result(job_id):
    return jsonify(results.get(job_id))

if __name__ == "__main__":
    print("Starter backend på port 10000...")
    app.run(host="0.0.0.0", port=10000, debug=True)
