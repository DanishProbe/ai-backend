from flask import Flask, request, make_response
from flask_cors import CORS
import dropbox
from datetime import datetime
import os
import io
import csv

app = Flask(__name__)
CORS(app)

DROPBOX_APP_KEY = "segxw8de2kw88nz"
DROPBOX_APP_SECRET = "5cwhm3rijw41v3o"
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

def create_dropbox_client():
    return dropbox.Dropbox(
        app_key=DROPBOX_APP_KEY,
        app_secret=DROPBOX_APP_SECRET,
        oauth2_refresh_token=DROPBOX_REFRESH_TOKEN
    )

@app.route("/upload", methods=["POST"])
def upload_files():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    analysevalg = request.form.get("analysevalg")
    sagstyper = request.form.getlist("sagstype")
    consent_gdpr = request.form.get("consent_gdpr")

    file_pdf = request.files.get("file_pdf")
    file_zip = request.files.get("file_zip")

    if not name or not email or not consent_gdpr:
        return "<p>Fejl: Alle påkrævede felter skal udfyldes.</p>", 400

    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    folder = f"/{timestamp}"
    log_path = "/upload_log.csv"

    dbx = create_dropbox_client()

    try:
        if analysevalg == "pdf" and file_pdf and file_pdf.filename.endswith(".pdf"):
            file_path = f"{folder}/{file_pdf.filename}"
            dbx.files_upload(file_pdf.read(), file_path, mute=True)
            upload_type = "afgørelse"
            file_uploaded = file_pdf.filename
        elif analysevalg == "zip" and file_zip and file_zip.filename.endswith(".zip"):
            file_path = f"{folder}/{file_zip.filename}"
            dbx.files_upload(file_zip.read(), file_path, mute=True)
            upload_type = "AI analyse"
            file_uploaded = file_zip.filename
        else:
            return "<p>Fejl: Ugyldig filtype eller manglende upload.</p>", 400

        try:
            md, res = dbx.files_download(log_path)
            existing_lines = res.content.decode("utf-8").splitlines()
        except dropbox.exceptions.ApiError:
            existing_lines = ["timestamp;name;email;analysevalg;sagstyper;filename"]

        sagstype_str = ", ".join(sagstyper)
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        for line in existing_lines:
            writer.writerow(line.split(";"))
        writer.writerow([timestamp, name, email, upload_type, sagstype_str, file_uploaded])
        dbx.files_upload(output.getvalue().encode("utf-8"), log_path, mode=dropbox.files.WriteMode.overwrite)

    except Exception as e:
        return f"<p>Fejl ved upload til Dropbox: {e}</p>", 500

    return "<p style='font-family: Arial; font-weight: bold;'>Gennemført – tak for din upload.</p>"