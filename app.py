
import os
import fitz  # PyMuPDF
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import openai

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)

openai.api_key = os.environ.get("OPENAI_API_KEY")


class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500))

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500))

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(100))


def extract_text_from_pdf(file_storage):
    text = ""
    with fitz.open(stream=file_storage.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text


def get_ai_judgment(text, laws):
    law_names = ", ".join(laws)
    prompt = f"""
Du er en juridisk AI-specialist. Analyser nedenstående familieretslige afgørelse og vurder:

1. Om følgende love er overholdt: {law_names}
2. Om der forekommer forskelsbehandling baseret på køn, bopæl eller samværsforælder
3. Om der mangler eller misbruges dokumentation (fx krisecentererklæringer)
4. Om barnets ret til kontakt med begge forældre er sikret
5. Giv kort vurdering med eksempler fra teksten.

Afgørelse:
{text[:4000]}...
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"AI-fejl: {str(e)}"


@app.route('/analyze', methods=['POST'])
def analyze():
    files = request.files.getlist("documents")
    results = []

    rules = [r.text for r in Rule.query.all()]
    laws = [l.text for l in Law.query.all()]
    keywords = [k.text for k in Keyword.query.all()]

    for file in files:
        text = extract_text_from_pdf(file)
        result = {
            "filename": file.filename,
            "rule_matches": [r for r in rules if r.lower() in text.lower()],
            "law_mentions": [l for l in laws if l.lower() in text.lower()],
            "contains_7_7": "7/7" in text,
            "contains_psykisk_vold": "psykisk vold" in text.lower(),
            "ai_assessment": get_ai_judgment(text, laws)
        }
        results.append(result)

    return jsonify({"result": results})


@app.route('/rules', methods=['GET', 'POST', 'DELETE'])
def manage_rules():
    if request.method == 'GET':
        return jsonify([{'id': r.id, 'text': r.text} for r in Rule.query.all()])
    elif request.method == 'POST':
        text = request.json.get('text')
        db.session.add(Rule(text=text))
        db.session.commit()
        return jsonify({'status': 'added'})
    elif request.method == 'DELETE':
        id = request.json.get('id')
        Rule.query.filter_by(id=id).delete()
        db.session.commit()
        return jsonify({'status': 'deleted'})


@app.route('/laws', methods=['GET', 'POST', 'DELETE'])
def manage_laws():
    if request.method == 'GET':
        return jsonify([{'id': l.id, 'text': l.text} for l in Law.query.all()])
    elif request.method == 'POST':
        text = request.json.get('text')
        db.session.add(Law(text=text))
        db.session.commit()
        return jsonify({'status': 'added'})
    elif request.method == 'DELETE':
        id = request.json.get('id')
        Law.query.filter_by(id=id).delete()
        db.session.commit()
        return jsonify({'status': 'deleted'})


@app.route('/keywords', methods=['GET', 'POST', 'DELETE'])
def manage_keywords():
    if request.method == 'GET':
        return jsonify([{'id': k.id, 'text': k.text} for k in Keyword.query.all()])
    elif request.method == 'POST':
        text = request.json.get('text')
        db.session.add(Keyword(text=text))
        db.session.commit()
        return jsonify({'status': 'added'})
    elif request.method == 'DELETE':
        id = request.json.get('id')
        Keyword.query.filter_by(id=id).delete()
        db.session.commit()
        return jsonify({'status': 'deleted'})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
