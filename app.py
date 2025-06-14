
import os
import fitz  # PyMuPDF
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def screen_with_gpt3(text):
    prompt = (
        "Vurder om der i denne tekst er indikationer på:
"
        "- forskelsbehandling
"
        "- psykisk vold
"
        "- manglende overholdelse af forældreansvarsloven, forvaltningsloven, barnets lov, "
        "straffeloven, ligestillingsloven, børnebidragsloven, FN børnekonventionen og EMRK.

"
        "Returnér kortfattet vurdering på dansk med ja/nej og årsag(e).

"
        f"Tekst:
{text}"
    )
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def analyze_with_gpt4(text):
    prompt = (
        "Foretag en juridisk analyse af følgende tekst. Identificer overtrædelser af:
"
        "- Forældreansvarsloven
"
        "- Barnets Lov
"
        "- Ligestillingsloven
"
        "- Forvaltningsloven
"
        "- EMRK og FN Børnekonventionen

"
        "Opret en udkast til klage, hvis muligt.

"
        f"Tekst:
{text}"
    )
    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        file = request.files["pdf"]
        if not file:
            return jsonify({"error": "Ingen fil modtaget"}), 400
        filepath = "/tmp/temp.pdf"
        file.save(filepath)

        text = extract_text_from_pdf(filepath)
        screen_result = screen_with_gpt3(text)

        if "ja" in screen_result.lower():
            analysis = analyze_with_gpt4(text)
        else:
            analysis = "Ingen videre analyse udført. Visitering gav ikke røde flag."

        return jsonify({
            "visitering": screen_result,
            "analyse": analysis
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
