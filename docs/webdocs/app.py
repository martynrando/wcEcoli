from flask import Flask, render_template, send_from_directory, abort, url_for
from markupsafe import Markup
import markdown
import os

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# Path to files
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # docs/
#STATIC_FOLDER = BASE_DIR
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
@app.route("/")
def home():
    # Load markdown content
    background_html = render_markdown("background.md")
    
    return render_template(
        "wiki_page.html",
        title="Home",
        heading="Whole Cell Model of E. coli",
        content=background_html,
        image_file=url_for("static",filename="wcEcoli_flowchart.png")
    )

# Placeholder pages
@app.route("/listeners")
def listeners():
    return render_template(
        "wiki_page.html",
        page_title="Listeners",
        heading="Listeners",
        content=Markup("<p>Listeners page content coming soon.</p>"),
        image_file=None,
    )

# Processes index page
@app.route("/processes")
def processes():
    pdf_dir = os.path.join('..', "processes")
    pdfs = []

    for filename in sorted(os.listdir(pdf_dir)):
        if filename.lower().endswith(".pdf"):
            pdfs.append({
                "title": filename[:-4].replace('_', ' ').title(),
                "file": filename,
                "url": url_for("serve_process_pdf", pdf_file=filename)
            })

    return render_template(
        "wiki_page.html",
        page_title="Processes",
        heading="Processes",
        content=Markup("<p>Select a process to view its documentation.</p>"),
        processes=pdfs,
        image_file=None,
    )

@app.route("/processes/<path:pdf_file>")
def serve_process_pdf(pdf_file):
    pdf_dir = os.path.join('..', "processes")
    path = os.path.join(pdf_dir, pdf_file)

    if not os.path.exists(path):
        abort(404)
    
    title = pdf_file[:-4].replace('_', ' ').title()
    return render_template(
        "wiki_page.html",
        page_title=title,
        heading=title,
        content=Markup(f'<embed src="{url_for("static", filename=os.path.join("..", "processes", pdf_file))}" type="application/pdf" width="100%" height="800px" />'),
        image_file=None,
    )

if __name__ == "__main__":
    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
