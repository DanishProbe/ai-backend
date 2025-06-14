import os
from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import fitz  # PyMuPDF
import openai

app = Flask(__name__)
CORS(app)

# DB opsætning
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
db = SQLAlchemy(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)

with app.app_context():
    db.create_all()

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    pdf = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in pdf:
        text += page.get_text()

    rules = [r.text for r in Rule.query.all()]
    laws = [l.text for l in Law.query.all()]
    keywords = [k.word for k in Keyword.query.all()]

    joined_rules = "\n- " + "\n- ".join(rules) if rules else "Ingen"
    joined_laws = "\n- " + "\n- ".join(laws) if laws else "Ingen"

    prompt = f"""Vurder om der i denne tekst er indikationer på:
- forskelsbehandling
- psykisk vold
- manglende overholdelse af familieretlige love

Sammenlign med følgende regler:
{joined_rules}

Og følgende love:
{joined_laws}

Tekst:
{text}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du er en juridisk assistent, der vurderer tekster i forhold til dansk familielovgivning."},
                {"role": "user", "content": prompt}
            ]
        )
        result = response.choices[0].message.content
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/rules", methods=["GET", "POST", "DELETE"])
def manage_rules():
    if request.method == "GET":
        return jsonify([{"id": r.id, "text": r.text} for r in Rule.query.all()])
    elif request.method == "POST":
        text = request.json.get("text")
        rule = Rule(text=text)
        db.session.add(rule)
        db.session.commit()
        return jsonify({"status": "added"})
    elif request.method == "DELETE":
        id = request.json.get("id")
        Rule.query.filter_by(id=id).delete()
        db.session.commit()
        return jsonify({"status": "deleted"})

@app.route("/laws", methods=["GET", "POST", "DELETE"])
def manage_laws():
    if request.method == "GET":
        return jsonify([{"id": l.id, "text": l.text} for l in Law.query.all()])
    elif request.method == "POST":
        text = request.json.get("text")
        law = Law(text=text)
        db.session.add(law)
        db.session.commit()
        return jsonify({"status": "added"})
    elif request.method == "DELETE":
        id = request.json.get("id")
        Law.query.filter_by(id=id).delete()
        db.session.commit()
        return jsonify({"status": "deleted"})

@app.route("/keywords", methods=["GET", "POST", "DELETE"])
def manage_keywords():
    if request.method == "GET":
        return jsonify([{"id": k.id, "word": k.word} for k in Keyword.query.all()])
    elif request.method == "POST":
        word = request.json.get("word")
        keyword = Keyword(word=word)
        db.session.add(keyword)
        db.session.commit()
        return jsonify({"status": "added"})
    elif request.method == "DELETE":
        id = request.json.get("id")
        Keyword.query.filter_by(id=id).delete()
        db.session.commit()
        return jsonify({"status": "deleted"})

@app.route("/")
def home():
    return "AI Analyse API kører."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
