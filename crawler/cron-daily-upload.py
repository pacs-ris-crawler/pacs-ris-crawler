from calendar import week
from datetime import datetime

import datetime
import requests
import click


@click.command()
@click.option("--host", help="Hostname to connect to, defaults to localhost")
@click.option("--port", help="Port to connect to ")
def upload(host, port):
    print(f"Calling url: http://{host}:{port}")
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    week_ago_str = week_ago.strftime("%Y-%m-%d")
    payload = {"from-date": week_ago_str, "to-date": week_ago_str}
    print(f"Payload is: {payload}")
    r = requests.get(f"http://{host}:{port}/batch-upload", params=payload)
    r.raise_for_status()
    print(r.json())


if __name__ == "__main__":
    upload()
