
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import PyPDF2

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)

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

@app.route('/analyze', methods=['POST'])
def analyze_documents():
    files = request.files.getlist("documents")
    findings = []

    rules = Rule.query.all()
    laws = Law.query.all()

    for file in files:
        if file and file.filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            rule_matches = [r.text for r in rules if r.text.lower() in text.lower()]
            law_mentions = [l.text for l in laws if l.text.lower() in text.lower()]

            findings.append({
                "filename": file.filename,
                "length": len(text),
                "contains_7_7": "7/7" in text,
                "contains_psykisk_vold": "psykisk vold" in text.lower(),
                "rule_matches": rule_matches,
                "law_mentions": law_mentions
            })

    return jsonify({"result": findings})

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)
