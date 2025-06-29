from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from uuid import uuid4
import os, threading, time
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
RESULTS_FOLDER = "results"
PROMPT_FILE = "prompt.txt"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULTS_FOLDER"] = RESULTS_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

jobs = {}
stop_flags = {}

def analyze_document(job_id, filepath, prompt):
    time.sleep(3)  # simulate time
    if stop_flags.get(job_id):
        jobs[job_id] = {"status": "stopped", "result": ""}
        return
	result = f"Analyzed {os.path.basename(filepath)} with prompt:\n{prompt_text}"

{prompt}"
    jobs[job_id] = {"status": "done", "result": result}

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt = f.read()

    job_id = str(uuid4())
    jobs[job_id] = {"status": "running", "result": ""}
    stop_flags[job_id] = False
    threading.Thread(target=analyze_document, args=(job_id, filepath, prompt)).start()
    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>")
def result(job_id):
    job = jobs.get(job_id)
    if not job:
        return "Invalid job ID", 404
    if job["status"] == "running":
        return "", 202
    return jsonify(job)

@app.route("/stop/<job_id>", methods=["POST"])
def stop(job_id):
    stop_flags[job_id] = True
    return "", 200

@app.route("/prompt", methods=["GET", "POST"])
def handle_prompt():
    if request.method == "POST":
        with open(PROMPT_FILE, "w", encoding="utf-8") as f:
            f.write(request.get_data(as_text=True))
        return "", 200
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read(), 200
    return "Ingen prompt gemt", 404

@app.route("/")
def index():
    return send_from_directory(".", "index.html")
