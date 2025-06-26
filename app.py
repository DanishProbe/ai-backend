from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def healthcheck():
    return "Backend test OK"

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=10000, debug=True)
