from flask import Flask, render_template, Markup, send_from_directory
import markdown
import os

app = Flask(__name__)

# Path to files
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # docs/
STATIC_FOLDER = BASE_DIR
MARKDOWN_FOLDER = BASE_DIR

# Helper function to load markdown file and convert to HTML
def render_markdown(filename):
    path = os.path.join(MARKDOWN_FOLDER, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return Markup(markdown.markdown(text))
    return Markup("<p>Content not found.</p>")

# Home page
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_FOLDER, filename)

def home():
    # Load markdown content
    background_html = render_markdown("background.md")
    
    return render_template(
        "templates/base.html",
        page_title="Whole Cell Model - E. coli",
        heading="Whole Cell Model - E. coli",
        content=background_html,
        image_file="wcEcoli_flowchart.png",
    )

# Placeholder pages
@app.route("/listeners")
def listeners():
    return render_template(
        "templates/base.html",
        page_title="Listeners - WCM E. coli",
        heading="Listeners",
        content=Markup("<p>Listeners page content coming soon.</p>"),
        image_file=None,
    )

@app.route("/processes")
def processes():
    return render_template(
        "templates/base.html",
        page_title="Processes - WCM E. coli",
        heading="Processes",
        content=Markup("<p>Processes page content coming soon.</p>"),
        image_file=None,
    )

if __name__ == "__main__":
    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
