
import os
import tempfile
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from PyPDF2 import PdfReader
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# Databasekonfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
db = SQLAlchemy(app)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

# Initialiser databasen
with app.app_context():
    db.create_all()

# Tilføj regel/lov
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
        return jsonify([{'id': l.id, 'name': l.name} for l in Law.query.all()])
    elif request.method == 'POST':
        name = request.json.get('name')
        db.session.add(Law(name=name))
        db.session.commit()
        return jsonify({'status': 'added'})
    elif request.method == 'DELETE':
        id = request.json.get('id')
        Law.query.filter_by(id=id).delete()
        db.session.commit()
        return jsonify({'status': 'deleted'})

# PDF-analyse og AI-kald
@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files['file']
    temp = tempfile.NamedTemporaryFile(delete=False)
    file.save(temp.name)

    reader = PdfReader(temp.name)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    # Hent alle regler og love fra databasen
    rules = [r.text for r in Rule.query.all()]
    laws = [l.name for l in Law.query.all()]

    # Check for matches i tekst
    rule_matches = [r for r in rules if r.lower() in text.lower()]
    law_mentions = [l for l in laws if l.lower() in text.lower()]

    # AI-analyse (OpenAI 1.0.0+ klient)
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    ai_prompt = (
        "Vurder om der i denne tekst er indikationer på:
"
        "- Forskelsbehandling i forhold til køn, bopæl, samvær
"
        "- Psykisk vold
"
        "- Overtrædelse af familieretlige love

"
        f"Tekst:
{text[:3000]}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": ai_prompt}],
            temperature=0.2,
        )
        summary = response.choices[0].message.content
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'result': summary,
        'rule_matches': rule_matches,
        'law_mentions': law_mentions
    })

if __name__ == '__main__':
    app.run(debug=True, port=10000)
