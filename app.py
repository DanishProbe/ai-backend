import os
import time
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

jobs = {}
stop_flags = {}
PROMPT_FILE = "prompt.txt"

@app.route("/prompt", methods=["GET", "POST"])
def prompt():
    if request.method == "GET":
        if os.path.exists(PROMPT_FILE):
            with open(PROMPT_FILE, "r", encoding="utf-8") as f:
                return jsonify({"text": f.read()}), 200
        return jsonify({"text": ""}), 200
    else:
        try:
            data = request.get_json()
            with open(PROMPT_FILE, "w", encoding="utf-8") as f:
                f.write(data.get("text", ""))
            return jsonify({"message": "Prompt gemt"}), 200
        except Exception as e:
            return jsonify({"message": f"Kunne ikke gemme prompt: {str(e)}"}), 500

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]
    job_id = str(uuid.uuid4())
    os.makedirs("uploads", exist_ok=True)
    filepath = os.path.join("uploads", f"{job_id}_{file.filename}")
    try:
        file.save(filepath)
    except Exception as e:
        return f"Kunne ikke gemme fil: {str(e)}", 500

    stop_flags[job_id] = False
    jobs[job_id] = {"status": "processing", "result": ""}

    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            prompt_text = f.read()
    else:
        prompt_text = ""

    import threading
    thread = threading.Thread(target=analyze_document, args=(job_id, filepath, prompt_text))
    thread.start()

    return jsonify({"job_id": job_id}), 202

@app.route("/stop/<job_id>", methods=["POST"])
def stop(job_id):
    stop_flags[job_id] = True
    return "Analysis stop requested", 200

@app.route("/result/<job_id>")
def result(job_id):
    job = jobs.get(job_id)
    if not job:
        return "Job not found", 404
    return jsonify(job), 200

def analyze_document(job_id, filepath, prompt_text):
    for i in range(5):
        if stop_flags.get(job_id):
            jobs[job_id] = {"status": "stopped", "result": ""}
            return
        time.sleep(1)
    result = f"✅ Filen '{os.path.basename(filepath)}' er analyseret med prompt:

{prompt_text or '(ingen prompt)'}"
    jobs[job_id] = {"status": "done", "result": result}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
