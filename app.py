
import os
import time
from flask import Flask, request, jsonify

app = Flask(__name__)
jobs = {}
stop_flags = {}

@app.route("/analyze", methods=["POST"])
def analyze():
    job_id = os.urandom(8).hex()
    file = request.files["file"]
    prompt = request.form.get("prompt", "")
    filepath = os.path.join("/tmp", file.filename)
    file.save(filepath)
    stop_flags[job_id] = False
    jobs[job_id] = {"status": "processing", "result": ""}
    from threading import Thread
    Thread(target=analyze_document, args=(job_id, filepath, prompt)).start()
    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>", methods=["GET"])
def get_result(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/stop/<job_id>", methods=["POST"])
def stop_job(job_id):
    stop_flags[job_id] = True
    return jsonify({"status": "stopping"}), 200

def analyze_document(job_id, filepath, prompt_text):
    time.sleep(3)  # simulate processing time
    if stop_flags.get(job_id):
        jobs[job_id] = {"status": "stopped", "result": ""}
        return
    result = f"Analyzed {os.path.basename(filepath)} with prompt:\n{prompt_text}"
    jobs[job_id] = {"status": "done", "result": result}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
