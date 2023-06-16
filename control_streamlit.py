import click
import json
from streamlit_manager import send_tcp
import socket
import subprocess
import os
import time
import pathlib

DIR = pathlib.Path(__file__).parent.absolute()
MANAGER_SOCKET_PATH = "/tmp/streamlit-manager_test.sock"
CONTROLLER_SOCKET_PATH = "/tmp/streamlit-manager-controls_test.sock"
CONTROLLER_LOG_PATH = DIR / pathlib.Path("controller.log")


def get_response(timeout):
    start_time = time.time()
    response = ""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
            os.unlink(CONTROLLER_SOCKET_PATH)
        except:
            pass
        sock.bind(CONTROLLER_SOCKET_PATH)
        sock.listen()
        sock.settimeout(2)
        while time.time() - start_time < timeout:
            try:
                client, addr = sock.accept()
                response += client.recv(4096).decode()
            except socket.timeout:
                pass
    return response


def start():
    if subprocess.call(
        ["pgrep", "-f", "streamlit_manager.py"],
            stdout=subprocess.DEVNULL) == 0:
        print("Manager already running")
        exit(1)
    log = open(CONTROLLER_LOG_PATH, "a")
    pid = subprocess.Popen(
        ["python", "-u", "streamlit_manager.py",
            MANAGER_SOCKET_PATH, CONTROLLER_SOCKET_PATH],
        stdout=log).pid
    log.write(f"Manager started with PID {pid}\n")
    print(get_response(1), end="")
    exit(0)


def stop():
    if subprocess.call(
        ["pgrep", "-f", "streamlit_manager.py"],
            stdout=subprocess.DEVNULL) != 0:
        print("Manager not running")
        exit(1)
    send_tcp(json.dumps({"message_type": "stop"}), MANAGER_SOCKET_PATH)
    exit(0)


def status():
    if subprocess.call(
        ["pgrep", "-f", "streamlit_manager.py"],
            stdout=subprocess.DEVNULL) != 0:
        print("Manager not running")
        exit(1)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
            os.unlink(CONTROLLER_SOCKET_PATH)
        except:
            pass
        sock.bind(CONTROLLER_SOCKET_PATH)
        sock.listen()
        sock.settimeout(5)

        send_tcp(
            json.dumps(
                {"message_type": "status",
                    "socket": CONTROLLER_SOCKET_PATH}),
            MANAGER_SOCKET_PATH)

        client, addr = sock.accept()
        data = client.recv(4096)

        try:
            msg = json.loads(data)
        except json.decoder.JSONDecodeError as e:
            print(e)
            exit(1)

        if msg["message_type"] != "status":
            print("Unexpected message type")
            exit(1)

        print(f"{'PID': <12} {'Port': <8} {'Name': <25}")
        for name, vals in msg["apps"].items():
            pid = vals["pid"] if vals["pid"] else "Not running"
            port = vals["port"] if vals["port"] else ""
            print(f"{pid: <12} {port: <8} {name: <30}")
    exit(0)


def refresh():
    if subprocess.call(
        ["pgrep", "-f", "streamlit_manager.py"],
            stdout=subprocess.DEVNULL) != 0:
        print("Manager not running")
        exit(1)

    send_tcp(json.dumps({"message_type": "refresh"}),
             MANAGER_SOCKET_PATH)
    print(get_response(2), end="")
    exit(0)


def restart(app_name):
    if app_name is None:
        print("App name required for restart")
        exit(1)

    send_tcp(
        json.dumps({"message_type": "restart", "app": app_name}),
        MANAGER_SOCKET_PATH)
    print(get_response(2), end="")
    exit(0)


@click.command()
@click.argument("operation", type=click.Choice(
    ["start", "stop", "status", "refresh", "restart"]))
@click.argument("app_name", required=False)
def main(operation, app_name):
    if operation == "start":
        start()

    elif operation == "stop":
        stop()

    elif operation == "status":
        status()

    elif operation == "refresh":
        refresh()

    elif operation == "restart":
        restart(app_name)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
