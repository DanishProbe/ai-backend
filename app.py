import os
import json
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai

# Initialiser Flask
app = Flask(__name__)
CORS(app)

# Indsæt din OpenAI nøgle
openai.api_key = os.getenv("OPENAI_API_KEY")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def screen_with_gpt3(text):
    """Brug GPT-3.5 Turbo til visitering"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Du er en juridisk visitator for familieret."},
                {"role": "user", "content": f"Vurder om der i denne tekst er indikationer på forskelsbehandling, psykisk vold, eller manglende overholdelse af familieretlige love:

{text[:3000]}"}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"GPT-3.5 fejl: {str(e)}"

def analyze_with_gpt4(text):
    """Brug GPT-4 Turbo til dybdeanalyse"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Du er en juridisk ekspert i dansk familieret og menneskerettigheder."},
                {"role": "user", "content": f"Analyser følgende dokument og identificer eventuelle overtrædelser af Forældreansvarsloven, Ligestillingsloven, Barnets Lov, Forvaltningsloven, Børnekonventionen og EMRK. Returnér en rapport og forslag til klageudkast:

{text[:6000]}"}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"GPT-4 fejl: {str(e)}"

@app.route("/analyze", methods=["POST"])
def analyze_pdf():
    file = request.files.get("pdf")
    if not file:
        return jsonify({"error": "Ingen fil modtaget"}), 400

    filename = f"{uuid.uuid4()}.pdf"
    filepath = os.path.join("uploads", filename)
    file.save(filepath)

    # Simpel tekstudtræk (placeholder)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)
        text = "
".join([page.get_text() for page in doc])
    except Exception as e:
        return jsonify({"error": f"Kunne ikke læse PDF: {str(e)}"}), 500

    # Først: GPT-3.5 screening
    screen_result = screen_with_gpt3(text)

    # Kun kør GPT-4 hvis visitering indikerer behov
    if "ingen indikation" in screen_result.lower():
        report = screen_result
    else:
        report = analyze_with_gpt4(text)

    # Gem rapport
    report_path = os.path.join("uploads", f"{filename}_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return jsonify({"visitering": screen_result, "analyse": report})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)