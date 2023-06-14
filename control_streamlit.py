import click
import json
from streamlit_manager import send_tcp
import socket
import subprocess
import os
import time

MANAGER_SOCKET_PATH = "/tmp/streamlit-manager.sock"
CONTROLLER_SOCKET_PATH = "/tmp/streamlit-manager-controls.sock"
CONTROLLER_LOG_PATH = "/home/elliotjd/streamlit_manager/control_streamlit.log"


def get_response():
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
        while time.time() - start_time < 1:
            try:
                client, addr = sock.accept()
                response += client.recv(4096).decode()
            except socket.timeout:
                pass
    if response == "":
        response = "All apps started successfully"
    return response


@click.command()
@click.argument("operation", type=click.Choice(["start", "stop", "status", "refresh"]))
def main(operation):
    match operation:
        case "start":
            if subprocess.call(["pgrep", "-f", "streamlit_manager.py"], stdout=subprocess.DEVNULL) == 0:
                print("Manager already running")
                exit(1)
            log = open(CONTROLLER_LOG_PATH, "a")
            pid = subprocess.Popen(
                ["python3.11", "-u", "streamlit_manager.py", MANAGER_SOCKET_PATH, CONTROLLER_SOCKET_PATH], stdout=log).pid
            log.write(f"Manager started with PID {pid}\n")
            print(get_response())
            exit(0)

        case "stop":
            if subprocess.call(["pgrep", "-f", "streamlit_manager.py"], stdout=subprocess.DEVNULL) != 0:
                print("Manager not running")
                exit(1)
            send_tcp(json.dumps({"message_type": "stop"}), MANAGER_SOCKET_PATH)
            exit(0)

        case "status":
            if subprocess.call(["pgrep", "-f", "streamlit_manager.py"], stdout=subprocess.DEVNULL) != 0:
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

                send_tcp(json.dumps(
                    {"message_type": "status", "socket": CONTROLLER_SOCKET_PATH}), MANAGER_SOCKET_PATH)

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

                print("App: PID")
                for name, pid in msg["pids"].items():
                    print(f"{name}: {pid}")
            exit(0)

        case "refresh":
            if subprocess.call(["pgrep", "-f", "streamlit_manager.py"], stdout=subprocess.DEVNULL) != 0:
                print("Manager not running")
                exit(1)

            send_tcp(json.dumps({"message_type": "refresh"}),
                     MANAGER_SOCKET_PATH)
            print(get_response())
            exit(0)


if __name__ == "__main__":
    main()
