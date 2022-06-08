import datetime
from datetime import datetime

import click
import requests


@click.command()
@click.option("--host", help="Hostname to connect to, defaults to localhost")
@click.option("--port", help="Port to connect to ")
@click.option("--day", help="Specific day to upload, format is: YYYY-mm-dd")
def upload(host, port, day):
    print(f"Calling url: http://{host}:{port}")
    if not day:
        today = datetime.date.today()
        week_ago = today - datetime.timedelta(days=7)
        week_ago_str = week_ago.strftime("%Y-%m-%d")
    else:
        week_ago_str = day
    payload = {"from-date": week_ago_str, "to-date": week_ago_str}
    print(f"Payload is: {payload}")
    r = requests.get(f"http://{host}:{port}/batch-upload", params=payload)
    r.raise_for_status()
    print(r.json())


if __name__ == "__main__":
    upload()
