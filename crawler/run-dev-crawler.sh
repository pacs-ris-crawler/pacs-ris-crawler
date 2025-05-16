#!/bin/sh
echo "Starting crawler on port 9009"
flask --app "crawler/app.py:create_app()"  run --debug --host 0.0.0.0 --port 9009