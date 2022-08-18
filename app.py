from flask import Flask
from datetime import datetime
from web.app import web_bp
from web.app import web_bundle
from crawler.app import crawler_bp
from crawler.app import crawler_bundle
#from web.app import bundles as web_bundles
from flask_assets import Environment, Bundle
from string import Template

app = Flask(__name__, instance_relative_config=True)
# app.config.from_object("web.default_config")
app.config.from_pyfile("config.cfg", silent=False)

VERSION = app.config["VERSION"] = "1.3.1"
RESULT_LIMIT = app.config["RESULT_LIMIT"]

REPORT_SHOW_URL = app.config["REPORT_SHOW_URL"]
# SHOW_DOWNLOAD_OPTIONS = app.config["SHOW_DOWNLOAD_OPTIONS"]
# SHOW_TRANSFER_TARGETS = app.config["SHOW_TRANSFER_TARGETS"]
TRANSFER_TARGETS = app.config["TRANSFER_TARGETS"]

RECEIVER_URL = app.config["RECEIVER_URL"]
RECEIVER_DASHBOARD_URL = app.config["RECEIVER_DASHBOARD_URL"]
RECEIVER_DOWNLOAD_URL = app.config["RECEIVER_DOWNLOAD_URL"]
RECEIVER_TRANSFER_URL = app.config["RECEIVER_TRANSFER_URL"]
ZFP_VIEWER = app.config["ZFP_VIEWER"]

app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.template_filter("to_date")
def to_date(date_as_int):
    if date_as_int:
        return datetime.strptime(str(date_as_int), "%Y%m%d").strftime("%d.%m.%Y")
    return ""


@app.template_filter("zfp_url")
def create_zfp_url(accession_number):
    s = Template(ZFP_VIEWER)
    x = s.substitute(accession_number=accession_number)
    return x


app.register_blueprint(web_bp, url_prefix="/web")
app.register_blueprint(crawler_bp, url_prefix="/crawler")
assets = Environment(app)
assets.register(web_bundle)
assets.register(crawler_bundle)

