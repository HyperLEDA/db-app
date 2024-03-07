import subprocess
from time import sleep
import requests


def test_startup():
    process = subprocess.Popen(["python", "main.py", "runserver"])
    sleep(0.5)

    response = requests.get("http://localhost:8080/ping", timeout=2)
    data = response.json()

    process.kill()

    assert data == {"ping": "pong"}
