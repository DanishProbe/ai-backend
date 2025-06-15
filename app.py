from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF
import os
import openai

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")  # Set securely in environment

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "Ingen fil modtaget"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "Kun PDF-filer tilladt"}), 400

    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()

    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Du er en juridisk assistent, der vurderer overholdelse af familieretlige love i Danmark."
                },
                {
                    "role": "user",
                    "content": f"Vurder om der i denne tekst er indikationer på:\n"
                               f"- forskelsbehandling (køn, bopæl, samværsforælder)\n"
                               f"- psykisk vold\n"
                               f"- manglende overholdelse af lovgivning som Forældreansvarsloven, Barnets Lov, EMRK, mv.\n\n"
                               f"Tekst:\n{text}"
                }
            ]
        )
        result = completion.choices[0].message.content.strip()
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)