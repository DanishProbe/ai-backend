import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PyPDF2 import PdfReader
import openai

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

with app.app_context():
    db.create_all()

@app.route("/rules", methods=["GET", "POST", "DELETE"])
def manage_rules():
    if request.method == "GET":
        return jsonify([{"id": r.id, "text": r.text} for r in Rule.query.all()])
    elif request.method == "POST":
        data = request.json
        rule = Rule(text=data["text"])
        db.session.add(rule)
        db.session.commit()
        return jsonify({"message": "Rule added"})
    elif request.method == "DELETE":
        data = request.json
        Rule.query.filter_by(id=data["id"]).delete()
        db.session.commit()
        return jsonify({"message": "Rule deleted"})

@app.route("/laws", methods=["GET", "POST", "DELETE"])
def manage_laws():
    if request.method == "GET":
        return jsonify([{"id": l.id, "name": l.name} for l in Law.query.all()])
    elif request.method == "POST":
        data = request.json
        law = Law(name=data["name"])
        db.session.add(law)
        db.session.commit()
        return jsonify({"message": "Law added"})
    elif request.method == "DELETE":
        data = request.json
        Law.query.filter_by(id=data["id"]).delete()
        db.session.commit()
        return jsonify({"message": "Law deleted"})

@app.route("/analyze", methods=["POST"])
def analyze_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    pdf = PdfReader(file_path)
    full_text = ""
    for page in pdf.pages:
        full_text += page.extract_text() or ""

    rules = [r.text for r in Rule.query.all()]
    laws = [l.name for l in Law.query.all()]

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Du er en juridisk assistent med speciale i familieret."},
                {"role": "user", "content": f"Analyser denne tekst fra en PDF for at vurdere:\n\n"
                                            f"1. Om følgende regler nævnes eller overtrædes: {', '.join(rules)}\n"
                                            f"2. Om følgende love nævnes, følges eller ikke følges: {', '.join(laws)}\n"
                                            f"3. Giv en kort opsummering på dansk om overholdelse af lovgivning og evt. forskelsbehandling.\n\n"
                                            f"PDF Tekst:\n{full_text[:4000]}"}
            ],
            max_tokens=1000
        )
        answer = response.choices[0].message.content
        return jsonify({"result": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)