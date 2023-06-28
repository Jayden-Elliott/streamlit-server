import flask
import json
from pathlib import Path
import streamlit_site as site

ROOT = site.app.config["ROOT"]


@site.app.route("/")
def show_index():
    apps = json.load(open(ROOT / Path("config.json"), "r"))["apps"]
    status = json.load(open(
        ROOT / Path("streamlit_controls/status.json"), "r"))
    for name, vals in apps.items():
        if name not in status:
            vals["running"] = False
        vals["running"] = True if status[name]["pid"] else False
    context = {
        "apps": sorted(apps.values(), key=lambda x: x["name"])
    }
    return flask.render_template("index.html", **context)
