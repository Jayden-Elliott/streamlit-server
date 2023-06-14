import socket
import os
import logging
import subprocess
import json
import pathlib
from utils import get_msg, send_tcp

LOGGER = logging.getLogger(__name__)
MANAGER_SOCK = "/tmp/streamlit-manager.sock"


class App:
    def socket_listener(self):
        try:
            os.unlink(self.socket_path)
        except OSError:
            if os.path.exists(self.socket_path):
                raise

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.bind(self.socket_path)
            sock.listen()
            sock.settimeout(1)
            while True:
                try:
                    clientsock = sock.accept()[0]
                except socket.timeout:
                    continue

                msg = get_msg(clientsock)
                try:
                    msg = json.loads(msg)
                except json.decoder.JSONDecodeError:
                    continue

                match msg["message_type"]:
                    case "stop":
                        if self.pid is not None:
                            os.kill(self.pid, 9)
                            self.pid = None
                        send_tcp("stopped", MANAGER_SOCK)
                        exit(0)

    def __init__(self, name, path, venv, port=None):
        self.socket_path = f"/tmp/streamlit-{name}.sock"
        self.pid = None

        venv_bin = f"/home/shared/venv/{venv}/bin"
        command = f"{venv_bin}/python {venv_bin}/streamlit run {path}"
        if "port" is not None:
            command += f" --server.port {port}"
        log_path = pathlib.Path(__file__).parent.absolute() / "streamlit_logs"
        command += f" >> {log_path / name.replace(' ', '_')}.log 2>&1"
        self.pid = subprocess.Popen(command, shell=True).pid + 1
        print(f"Started {name} with pid {self.pid}")

        self.socket_listener(self.socket_path)


def track_processes(apps):
    while True:
        pids = subprocess.check_output(["pgrep", "python"]).splitlines()
        pids = [int(pid) for pid in pids]

        for app in apps:
            if "pid" in app and app["pid"] in pids:
                continue
            venv_bin = f"/home/shared/venv/{app['venv']}/bin"
            command = f"{venv_bin}/python {venv_bin}/streamlit run {app['path']}"
            if "port" in app:
                command += f" --server.port {app['port']}"
            command += f" >> logs/{app['name'].replace(' ', '_')}.log 2>&1"
            app["pid"] = subprocess.Popen(command, shell=True).pid + 1
            print(f"Started {app['name']} with pid {app['pid']}")

        time.sleep(10)


def main():

    with open("apps.json") as f:
        apps = json.load(f)

    while True:
        pids = subprocess.check_output(["pgrep", "python"]).splitlines()
        pids = [int(pid) for pid in pids]

        for app in apps:
            if "pid" in app and app["pid"] in pids:
                continue
            venv_bin = f"/home/shared/venv/{app['venv']}/bin"
            command = f"{venv_bin}/python {venv_bin}/streamlit run {app['path']}"
            if "port" in app:
                command += f" --server.port {app['port']}"
            command += f" >> logs/{app['name'].replace(' ', '_')}.log 2>&1"
            app["pid"] = subprocess.Popen(command, shell=True).pid + 1
            print(f"Started {app['name']} with pid {app['pid']}")

        time.sleep(10)


if __name__ == "__main__":
    main()
