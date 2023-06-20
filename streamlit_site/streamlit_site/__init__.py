import flask
from pathlib import Path

app = flask.Flask(__name__)
app.config.from_object("streamlit_site.config")

import streamlit_site.pages  # noqa: E402
