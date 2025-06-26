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

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)

@app.route("/")
def healthcheck():
    return "Backend kører OK"

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
                keywords = [k.text for k in Keyword.query.all()]
                rules = [r.text for r in Rule.query.all()]
                laws = [l.name for l in Law.query.all()]

                base_prompt = (
                    f"Analyser følgende tekst:\n"
                    f"1. Findes nogen af følgende nøgleord: {', '.join(keywords)}\n"
                    f"2. Findes eller overtrædes nogen af følgende regler: {', '.join(rules)}\n"
                    f"3. Nævnes, følges eller brydes nogen af følgende love: {', '.join(laws)}\n"
                    f"Svar meget kort med 'ja' eller 'nej' for hver kategori.\n"
                    f"Tekst: {full_content[:4000]}"
                )
                step1 = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Du er en juridisk assistent."},
                        {"role": "user", "content": base_prompt}
                    ],
                    max_tokens=300
                )
                s1_result = step1.choices[0].message.content.lower()
                token1 = step1.usage.total_tokens
                if "ja" not in s1_result:
                    result_store[job_id] = f"Intet relevant fundet. (Brugt: {token1} tokens ≈ {token1 * 0.00012:.2f} DKK)"
                    return

                full_prompt = f"""Du er juridisk assistent med speciale i familieret. Lav en grundig analyse af følgende dokumenttekst i følgende struktur:

1. Resume:
   - Kort opsummering af indholdet (2-4 linjer)

2. Nøgleord:
   - Angiv hvilke af følgende søgeord der er nævnt (ja/nej): {', '.join(keywords)}

3. Regler:
   - Angiv hvilke af følgende regler der er nævnt eller overtrådt (ja/nej): {', '.join(rules)}

4. Lovgivning:
   - Nævn hvilke af følgende love der omtales, følges eller brydes (ja/nej og paragrafangivelse hvis muligt): {', '.join(laws)}
   - Vurder også om der er overtrædelse af centrale paragraffer som:
     - Straffeloven § 260 (ulovlig tvang)
     - Straffeloven § 152 (brud på tavshedspligt)
     - Manglende høring eller partsindsigt (fx i sager med krisecenter, kommune eller familieret)
   - Vurder om der mangler saglig og objektiv vurdering i sagsbehandlingen

5. Retssikkerhed:
   - Vurder om grundlæggende retssikkerhedsprincipper er overholdt, herunder partshøring, inddragelse, begrundelse og klagemulighed
   - Angiv eventuelle tegn på brud på god forvaltningsskik

6. Forskelsbehandling:
   - Vurder om der i dokumentet sker forskelsbehandling på baggrund af familieform, køn, eller forældrerolle (bopæl/samvær)
   - Check både i det konkrete indhold og i den måde myndigheder henviser til lovgivningen
   - Brug både generel lovgivning og den lovgivning som er angivet af brugeren

7. Konklusion:
   - Giv en samlet juridisk vurdering om overholdelse af lovgivning og menneskerettigheder
   - Angiv tydeligt hvis der er risiko for eller tegn på lovbrud eller forskelsbehandling

Tekst: {full_content[:8000]}
"""  

                step2 = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "Du er en juridisk assistent."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=1000
                )
                token2 = step2.usage.total_tokens
                total_price = token1 * 0.00012 + token2 * 0.00032
                final_result = step2.choices[0].message.content
                result_store[job_id] = f"{final_result.strip()}\n\nAI-analysepris: {total_price:.2f} DKK"
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
    with app.app_context():
        db.create_all()
    print("Starter backend på port 10000...")
    app.run(host="0.0.0.0", port=10000, debug=True)
