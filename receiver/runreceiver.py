"""
Module to run the application. Defines also logging configuration.
"""
import os
import logging
import daiquiri

from mova.app import app

LOG_DIR = 'logs'

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

daiquiri.setup(level=logging.DEBUG,
    outputs=(
        daiquiri.output.File('logs/mova-errors.log', level=logging.ERROR),
        daiquiri.output.RotatingFile(
            'logs/mova-debug.log',
            level=logging.DEBUG,
            # 10 MB
            max_size_bytes=10000000)
    ))
app.run(host='0.0.0.0', port=9001)

