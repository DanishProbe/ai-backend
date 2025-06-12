
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import fitz  # PyMuPDF
import os

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500))

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500))

@app.before_first_request
def create_tables():
    db.create_all()

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

def extract_text_from_pdf(file_storage):
    doc = fitz.open(stream=file_storage.read(), filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

def analyze_text(text, rules, laws):
    matches = [r.text for r in rules if r.text.lower() in text.lower()]
    mentions = [l.text for l in laws if l.text.lower() in text.lower()]
    contains_7_7 = "7/7" in text
    psykisk_vold = "psykisk vold" in text.lower()

    summary = "AI-vurdering placeholder:\n\nFølgende love nævnes i dokumentet og bør vurderes:\n"
    summary += "\n".join(f"- {law.text}" for law in laws if law.text.lower() in text.lower())

    return matches, mentions, contains_7_7, psykisk_vold, summary

@app.route('/analyze', methods=['POST'])
def analyze_documents():
    files = request.files.getlist("documents")
    rules = Rule.query.all()
    laws = Law.query.all()

    results = []

    for f in files:
        text = extract_text_from_pdf(f)
        matches, mentions, contains_7_7, psykisk_vold, ai_assessment = analyze_text(text, rules, laws)
        results.append({
            'filename': f.filename,
            'length': len(text),
            'rule_matches': matches,
            'law_mentions': mentions,
            'contains_7_7': contains_7_7,
            'contains_psykisk_vold': psykisk_vold,
            'ai_assessment': ai_assessment
        })

    return jsonify({'result': results})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
