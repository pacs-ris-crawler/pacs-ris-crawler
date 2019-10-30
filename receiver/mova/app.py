import json
import logging
import os
from datetime import datetime, timedelta

import rq_dashboard
from flask import Flask, jsonify, render_template, request
from flask_assets import Bundle, Environment

from mova.config import dcmtk_config, pacs_config
from mova.job import download_series, transfer_series

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('mova.default_config')
app.config.from_pyfile('config.cfg')
version = app.config['VERSION'] = '1.0.1'

app.config.from_object(rq_dashboard.default_settings)
app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")



@app.route('/')
def main():
    return "receiver is running"


@app.route('/download', methods=['POST'])
def download():
    """ Post to download series of images. """
    app.logger.info("download called")
    data = request.get_json(force=True)
    series_list = data.get('data')
    dir_name = data.get('dir')
    length = download_series(app.config, series_list, dir_name)
    return json.dumps({'status': 'OK', 'series_length': length})


@app.route('/transfer', methods=['POST'])
def transfer():
    """ Post to transfer series of images to another PACS node. """
    data = request.get_json(force=True)
    target = data.get('target', '')
    series_list = data.get('data', '')
    app.logger.info("transfer called and sending to %s", target)
    length = transfer_series(app.config, series_list, target)
    return json.dumps({'status': 'OK', 'series_length': length})
