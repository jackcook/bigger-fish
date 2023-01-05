from flask import Flask, send_from_directory

app = Flask(__name__)

@app.route("/")
def root():
    return send_from_directory("attacker", "index.html")

@app.route("/<path:path>")
def static_dir(path):
    resp = send_from_directory("attacker", path)
    if "worker.js" in path:
        resp.headers['Content-Type'] = 'text/javascript'
    return resp