from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, uuid, threading, time

app = Flask(__name__)
CORS(app)

JOBS = {}
STOP_FLAGS = {}
PROMPT_PATH = "prompt.txt"

@app.route("/prompt", methods=["GET", "POST"])
def handle_prompt():
    if request.method == "POST":
        text = request.json.get("text", "")
        with open(PROMPT_PATH, "w", encoding="utf-8") as f:
            f.write(text)
        return jsonify({"message": "Prompt gemt."}), 200
    else:
        if os.path.exists(PROMPT_PATH):
            with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                return jsonify({"text": f.read()}), 200
        return jsonify({"text": ""}), 200

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return "No file uploaded", 400
    file = request.files["file"]
    job_id = str(uuid.uuid4())
    file_path = f"uploads/{job_id}_{file.filename}"
    os.makedirs("uploads", exist_ok=True)
    file.save(file_path)

    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        prompt_text = f.read()

    thread = threading.Thread(target=analyze_document, args=(job_id, file_path, prompt_text))
    thread.start()

    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>")
def get_result(job_id):
    job = JOBS.get(job_id)
    if not job:
        return "Job not found", 404
    if job["status"] == "done":
        return jsonify({"done": True, "result": job["result"]}), 200
    if job["status"] == "stopped":
        return jsonify({"done": True, "result": "Analysen blev stoppet af brugeren."}), 200
    return jsonify({"done": False}), 202

@app.route("/stop/<job_id>", methods=["POST"])
def stop_analysis(job_id):
    STOP_FLAGS[job_id] = True
    return "Analysis stop requested.", 200

def analyze_document(job_id, filepath, prompt_text):
    time.sleep(3)  # simulate work
    if STOP_FLAGS.get(job_id):
        JOBS[job_id] = {"status": "stopped", "result": ""}
        return
    result = f"Analyzed {os.path.basename(filepath)} with prompt:
{prompt_text}"
    JOBS[job_id] = {"status": "done", "result": result}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)