from flask import Flask, render_template, send_from_directory, abort, url_for, request, redirect
from pymongo import MongoClient
from markupsafe import Markup
import markdown
import os
import sys
import time
from fw_logic_and_launch import WF_RULES, build_and_submit
import wholecell.utils.filepath as fp
from fireworks import LaunchPad
from runscripts.manual.analysis_interactive import create_app, AnalysisInteractive
import dash

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
mongoclient = MongoClient("mongodb://172.17.0.1:27017/")
# mongodb comments collection
webdocs_db = mongoclient["wcecoli_webdocs"]
comments_collection = webdocs_db["comments"]
# fireworks collection
fw_db = mongoclient["wcm_user"]
fw_collection = fw_db["fireworks"]
wf_collection = fw_db["workflows"]
launch_collection = fw_db["launches"]

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

# Initialising the launchpad file
home = os.environ["HOME"]
user = "wcm_user"
print("Entering launchpad info")
logdir_launchpad = os.path.join(home, "fw", "logs", "launchpad")
logdir_qadapter = os.path.join(home, "fw", "logs", "qadapter")
db_host = "172.17.0.1"
db_port = "27017"
db_name = user
db_username = ""
db_password = ""
wcecoli_path = os.environ["PYTHONPATH"]
template_my_launchpad = os.path.join(
    wcecoli_path,
    "wholecell", "fireworks", "templates", "my_launchpad.yaml"
)
my_launchpad = os.path.join(wcecoli_path,"my_launchpad.yaml")
fp.makedirs(logdir_launchpad)
fp.makedirs(logdir_qadapter)
with open(template_my_launchpad, "r") as f:
	t = f.read()
my_launchpad_text = t.format(
    LOGDIR_LAUNCHPAD=logdir_launchpad,
    DB_HOST=db_host,
    DB_NAME=db_name,
    DB_USERNAME=db_username or 'null',
    DB_PASSWORD=db_password or 'null',
    DB_PORT=db_port
)
with open(my_launchpad, "w") as f:
	f.write(my_launchpad_text)
template_my_qadapter = os.path.join(wcecoli_path, "wholecell", "fireworks", "templates", "my_qadapter.yaml")
my_qadapter = os.path.join(wcecoli_path, "my_qadapter.yaml")
with open(template_my_qadapter, "r") as f:
    t = f.read()
my_qadapter_text = t.format(
    LOGDIR_QADAPTER=logdir_qadapter,
    LAUNCHPAD_PATH=my_launchpad,
    WCECOLI_PATH=wcecoli_path,
    )
with open(my_qadapter, "w") as f:
    f.write(my_qadapter_text)
print("")
print("Created {} with the information provided.".format(my_launchpad))
print("Created {} with the information provided.".format(my_qadapter))
lpad = LaunchPad.from_file(my_launchpad)
lpad.reset("", require_password=False)  # Clear existing data for a clean slate


# Home page
@app.route("/")
def home():
    # Load markdown content
    background_html = render_markdown("background.md")
    comments = list(
        comments_collection.find({"page_id": "home"}).sort("timestamp", -1)
    )
    
    return render_template(
        "wiki_page.html",
        title="Home",
        heading="Whole Cell Model of E. coli",
        content=background_html,
        image_file=url_for("static",filename="wcEcoli_flowchart.png"),
        see_also=["processes", "listeners"],
        references=[],
        further_reading=[],
        page_id="home",
        comments=comments
    )

# Placeholder pages
@app.route("/listeners")
def listeners():
    comments = list(
        comments_collection.find({"page_id": "listeners"}).sort("timestamp", -1)
    )
    return render_template(
        "wiki_page.html",
        page_title="Listeners",
        heading="Listeners",
        content=Markup("<p>Listeners page content coming soon.</p>"),
        image_file=None,
        see_also=["processes", "listeners"],
        references=[],
        further_reading=[],
        page_id="listeners",
        comments=comments
    )

# Processes index page
@app.route("/processes")
def processes():
    pdf_dir = os.path.join(BASE_DIR, "processes")
    pdfs = []
    comments = list(
        comments_collection.find({"page_id": "processes"}).sort("timestamp", -1)
    )

    for filename in sorted(os.listdir(pdf_dir)):
        if filename.lower().endswith(".pdf"):
            pdfs.append({
                "title": filename[:-4].replace('_', ' ').title(),
                "file": os.path.join(pdf_dir,filename),
                "url": url_for("serve_process_pdf", pdf_file=filename)
            })

    return render_template(
        "wiki_page.html",
        page_title="Processes",
        heading="Processes",
        content=render_markdown(os.path.join(BASE_DIR, "processes","README.md")),
        processes=pdfs,
        image_file=None,
        see_also=["processes", "listeners"],
        references=[],
        further_reading=[],
        page_id="processes",
        comments=comments
    )

# Route to serve PDFs from the processes folder
@app.route("/processes/files/<path:pdf_file>")
def get_process_pdf(pdf_file):
    pdf_dir = os.path.join(BASE_DIR, "processes")
    return send_from_directory(pdf_dir, pdf_file)

# Route to display PDF in a wiki page
@app.route("/processes/<path:pdf_file>")
def serve_process_pdf(pdf_file):
    pdf_dir = os.path.join(BASE_DIR, "processes")
    path = os.path.join(pdf_dir, pdf_file)

    if not os.path.exists(path):
        abort(404)
    
    title = pdf_file[:-4].replace('_', ' ').title()
    comments = list(
        comments_collection.find({"page_id": f"process::{pdf_file}"}).sort("timestamp", -1)
    )
    
    # Use the new route to get the PDF URL
    pdf_url = url_for("get_process_pdf", pdf_file=pdf_file)
    
    return render_template(
        "wiki_page.html",
        page_title=title,
        heading=title,
        content=Markup(f'<embed src="{pdf_url}" type="application/pdf" width="100%" height="800px" />'),
        image_file=None,
        see_also=["processes", "listeners"],
        references=[],
        further_reading=[],
        page_id=f"process::{pdf_file}",
        comments=comments
    )


@app.route("/control", methods=["GET"])
def control():
    """
    Render the workflow control form dynamically from WF_RULES.
    """
    params = []
    WF_RULES["LAUNCHPAD_FILE"]["default"] = "my_launchpad.yaml"

    for name, rule in WF_RULES.items():
        param_type = rule.get("type", None)
        default = rule.get("default", None)
        description = rule.get("description", "")
        allowed_set = rule.get("allowed_set", None)
        allowed = rule.get("allowed", None)

        # classify each param so template can choose the correct input
        if param_type == int:
            field_type = "number"
        elif param_type == str:
            field_type = "text"
        elif param_type == list:
            field_type = "list"
        elif param_type == bool or (param_type == int and rule.get("allowed") == [0,1]):
            field_type = "bool"
        else:
            field_type = "text"

        params.append({
            "name": name,
            "type": field_type,
            "default": default,
            "description": description,
            "allowed_set": allowed_set,
            "allowed": allowed,
        })

    return render_template("control_page.html", params=params)


# Comments submission route
@app.route("/submit_comment/<page_id>", methods=["POST"])
def submit_comment(page_id):
    """
    Submit comment and save to MongoDB.
    """
    data = request.form
    comments_collection.insert_one({
        "page_id": page_id,
        "username": data.get("username"),
        "comment": data.get("comment"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    })

    return redirect(request.referrer or url_for("home"))


@app.route("/submit", methods=["POST"])
def submit_workflow():
    user_params = {}

    for name, rule in WF_RULES.items():
        raw_value = request.form.get(name)
        if raw_value is not None:
            user_params[name] = raw_value
        else:
            user_params[name] = rule["default"]
        user_params[name] = rule["type"](user_params[name])
    build_and_submit(user_params=user_params)
    return redirect(url_for("status"))


@app.route("/status", methods=["GET"])
def status():
    """
    Display the status of each running workflow.
    """
    # Placeholder: In a real implementation, fetch workflow statuses from the database or workflow manager
    workflow_statuses = []
    for wf_doc in wf_collection.find():
        print(wf_doc.keys(), flush=True, file=sys.stderr)
        wf_id = wf_doc.get("wf_id")
        wf_name = wf_doc.get("name", f"Workflow {wf_id}")
        if wf_name == 'unnamed WF':
            wf_name = f"Workflow {wf_id}"
        wf_spec = wf_doc.get("spec", {})
        wf_notes = wf_doc.get("notes", "")
        fws = []
        total_count = 0
        completed_count = 0

        fw_docs = fw_collection.find({"wf_id": wf_id}).sort("created_on", 1)
        for fw_doc in fw_docs:
            if total_count == 0:
                print(fw_doc.keys(), flush=True, file=sys.stderr)
            if fw_doc.get("state") == "COMPLETED":
                completed_count += 1
            total_count += 1
            fws.append({
                "fw_id": str(fw_doc["_id"]),
                "name": fw_doc.get("name", f"FW {fw_doc['_id']}"),
                "state": fw_doc.get("state", {}),
                "host": fw_doc.get("host", "N/A"),
                "priority": fw_doc.get("_priority", "N/A"),
                "created_on": fw_doc.get("created_on"),
                "updated_on": fw_doc.get("updated_on"),
            })
        workflow_statuses.append({
            "workflow_id": str(wf_doc["_id"]),
            "name": wf_name,
            "notes": wf_notes,
            "spec": wf_spec,
            "fireworks": fws,
            "progress": (completed_count / total_count * 100) if total_count > 0 else 0,
            "progress_string": f"{completed_count}/{total_count} tasks completed"
        })
    workflow_statuses.sort(key=lambda x: x["workflow_id"])
    return render_template(
        "running.html",
        workflows=workflow_statuses,
        title="status",
        page_id="status"
    )

dash_data = AnalysisInteractive().parse_data_structure(
    path = '/user/out'# simulation output path
)
dash_app = create_app(
    data_structure=dash_data,
    app=dash.Dash(__name__, server=app, url_base_pathname='/analysis/')
)
if __name__ == "__main__":
    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
