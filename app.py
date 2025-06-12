
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

import PyPDF2
from flask import request

import os

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///admin_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(256), nullable=False)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(256), nullable=False)

class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(256), nullable=False)

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

    for file in files:
        if file and file.filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            findings.append({
                "filename": file.filename,
                "length": len(text),
                "contains_7_7": "7/7" in text,
                "contains_psykisk_vold": "psykisk vold" in text.lower()
            })

    return jsonify({"result": findings})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
