from flask import Flask, request, jsonify
import uuid
import threading
import time

app = Flask(__name__)
jobs = {}
job_results = {}

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files["file"]
    job_id = str(uuid.uuid4())
    jobs[job_id] = True
    threading.Thread(target=process_job, args=(job_id, file.read().decode("utf-8"))).start()
    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>")
def result(job_id):
    if job_id not in job_results:
        return "", 202
    return job_results.pop(job_id), 200

@app.route("/stop/<job_id>", methods=["POST"])
def stop(job_id):
    jobs[job_id] = False
    return "", 200

def process_job(job_id, content):
    for _ in range(5):
        if not jobs.get(job_id):
            return
        time.sleep(2)
    if jobs.get(job_id):
        job_results[job_id] = "Analyse baseret på indhold: " + content[:100]

if __name__ == "__main__":
    app.run(debug=True, port=10000)
