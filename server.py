from flask import Flask, send_from_directory

app = Flask(__name__)


@app.route("/")
def index():
    return send_from_directory(".", "main.html")


@app.route("/htmx/htmx.min.js")
def htmx_js():
    return send_from_directory("htmx", "htmx.min.js")


@app.route("/ping")
def ping():
    return "<p style='color: green; font-weight: bold;'>Flask + HTMX connected successfully!</p>"


if __name__ == "__main__":
    app.run(debug=True, port=5000)
