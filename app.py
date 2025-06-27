
import os
import uuid
import threading
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from openai import OpenAI
import time

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

analysis_jobs = {}
prompt_storage = {"prompt": ""}

@app.route("/prompt", methods=["GET", "POST"])
def prompt():
    if request.method == "GET":
        return jsonify({"prompt": prompt_storage["prompt"]})
    if request.method == "POST":
        data = request.get_json()
        prompt_storage["prompt"] = data.get("prompt", "")
        return jsonify({"message": "Prompt gemt"})

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    job_id = str(uuid.uuid4())
    analysis_jobs[job_id] = {"status": "pending", "result": ""}

    prompt = prompt_storage["prompt"]

    thread = threading.Thread(target=analyze_file, args=(job_id, file_path, prompt))
    thread.start()

    return jsonify({"job_id": job_id}), 202

@app.route("/result/<job_id>", methods=["GET"])
def result(job_id):
    job = analysis_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id):
    if job_id in analysis_jobs and analysis_jobs[job_id]["status"] == "pending":
        analysis_jobs[job_id]["status"] = "cancelled"
        analysis_jobs[job_id]["result"] = "Analysis was cancelled by user."
        return jsonify({"message": f"Job {job_id} cancelled."})
    return jsonify({"error": "Job not found or already completed"}), 404

def analyze_file(job_id, file_path, prompt):
    with app.app_context():
        try:
            print(f"[{job_id}] Starting analysis...")
            pdf = PdfReader(file_path)
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

            print(f"[{job_id}] Extracted {len(text)} characters of text")

            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Du er en juridisk ekspert i familieret."},
                    {"role": "user", "content": f"{prompt}\n\n{text[:4000]}"}
                ],
                max_tokens=1500
            )
            answer = completion.choices[0].message.content
            analysis_jobs[job_id]["status"] = "done"
            analysis_jobs[job_id]["result"] = answer
            print(f"[{job_id}] Analysis complete")

        except Exception as e:
            analysis_jobs[job_id]["status"] = "error"
            analysis_jobs[job_id]["result"] = str(e)
            print(f"[{job_id}] Error: {e}")

if __name__ == "__main__":
    print("Starter backend på port 10000...")
    app.run(host="0.0.0.0", port=10000, debug=True)
