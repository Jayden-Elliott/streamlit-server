import flask
import json
from pathlib import Path
import streamlit_site as site

ROOT = site.app.config["ROOT"]


@site.app.route("/<streamlit_app_url>/")
def show_app(streamlit_app_url):
    apps = json.load(open(ROOT / Path("config.json"), "r"))["apps"]
    context = None
    for app, info in apps.items():
        if info["url"] == f"/{streamlit_app_url}/":
            context = {
                "name": info["name"],
                "port": info["port"]
            }
    else:
        if context is None:
            return flask.abort(404)

    return flask.render_template("app.html", **context)
