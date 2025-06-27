
import os
import uuid
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

@app.route("/prompt", methods=["GET", "POST"])
def handle_prompt():
    if request.method == "GET":
        prompt = Prompt.query.first()
        return jsonify({"text": prompt.text if prompt else ""})
    elif request.method == "POST":
        data = request.json
        prompt = Prompt.query.first()
        if prompt:
            prompt.text = data["text"]
        else:
            prompt = Prompt(text=data["text"])
            db.session.add(prompt)
        db.session.commit()
        return jsonify({"message": "Gemt"})

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    job_id = str(uuid.uuid4())
    result_path = os.path.join(app.config['RESULTS_FOLDER'], f"{job_id}.txt")
    with open(result_path, "w") as f:
        f.write("Mock result – real analysis not implemented here.")

    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>")
def get_result(job_id):
    result_path = os.path.join(app.config['RESULTS_FOLDER'], f"{job_id}.txt")
    if os.path.exists(result_path):
        with open(result_path, "r") as f:
            return jsonify({"result": f.read()})
    return jsonify({"status": "Processing..."}), 202

if __name__ == "__main__":
    print("Starter backend på port 10000...")
    app.run(host="0.0.0.0", port=10000, debug=True)
