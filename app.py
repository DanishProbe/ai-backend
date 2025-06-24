
import os
import zipfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PyPDF2 import PdfReader
from fpdf import FPDF

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rules.db'
db = SQLAlchemy(app)

class Rule(db.Model): id = db.Column(db.Integer, primary_key=True); text = db.Column(db.Text, nullable=False)
class Law(db.Model): id = db.Column(db.Integer, primary_key=True); name = db.Column(db.String(255), nullable=False)
class Keyword(db.Model): id = db.Column(db.Integer, primary_key=True); text = db.Column(db.Text, nullable=False)

with app.app_context(): db.create_all()

@app.route("/rules", methods=["GET", "POST", "DELETE"])
def rules(): data = request.json; 
 if request.method=="GET": return jsonify([{"id": r.id, "text": r.text} for r in Rule.query.all()])
 elif request.method=="POST": db.session.add(Rule(text=data["text"])); db.session.commit(); return jsonify({"message": "Rule added"})
 elif request.method=="DELETE": Rule.query.filter_by(id=data["id"]).delete(); db.session.commit(); return jsonify({"message": "Rule deleted"})

@app.route("/laws", methods=["GET", "POST", "DELETE"])
def laws(): data = request.json;
 if request.method=="GET": return jsonify([{"id": l.id, "name": l.name} for l in Law.query.all()])
 elif request.method=="POST": db.session.add(Law(name=data["name"])); db.session.commit(); return jsonify({"message": "Law added"})
 elif request.method=="DELETE": Law.query.filter_by(id=data["id"]).delete(); db.session.commit(); return jsonify({"message": "Law deleted"})

@app.route("/keywords", methods=["GET", "POST", "DELETE"])
def keywords(): data = request.json;
 if request.method=="GET": return jsonify([{"id": k.id, "text": k.text} for k in Keyword.query.all()])
 elif request.method=="POST": db.session.add(Keyword(text=data["text"])); db.session.commit(); return jsonify({"message": "Keyword added"})
 elif request.method=="DELETE": Keyword.query.filter_by(id=data["id"]).delete(); db.session.commit(); return jsonify({"message": "Keyword deleted"})

@app.route("/analyze", methods=["POST"])
def analyze():
 file = request.files.get("file"); filename = file.filename
 if not file or not filename: return jsonify({"error": "No file uploaded"}), 400
 file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename); file.save(file_path)
 texts = []
 if filename.endswith(".zip"):
  with zipfile.ZipFile(file_path, 'r') as z: z.extractall("uploads/tmp")
  for name in z.namelist():
   if name.endswith(".pdf"):
    p = PdfReader(f"uploads/tmp/{name}")
    text = "".join([pg.extract_text() or "" for pg in p.pages])
    texts.append((name, text[:2000]))
 elif filename.endswith(".pdf"):
  p = PdfReader(file_path); text = "".join([pg.extract_text() or "" for pg in p.pages])
  texts.append((filename, text[:2000]))
 else: return jsonify({"error": "Kun PDF og ZIP understøttes"}), 400

 combined = ""; pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=12)
 for name, txt in texts:
  combined += f"--- {name} ---\n{txt}\n\n"
 for line in combined.split("\n"): pdf.multi_cell(0, 10, line)
 out = "uploads/rapport.pdf"; pdf.output(out)
 return send_file(out, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
