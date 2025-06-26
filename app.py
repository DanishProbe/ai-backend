from flask import Flask
app = Flask(__name__)

@app.route("/")
def healthcheck():
    return "Backend kører OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
