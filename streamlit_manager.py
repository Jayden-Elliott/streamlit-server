import json
import socket
import os
import threading
import subprocess
import pathlib
import sys
import time

DIR = pathlib.Path(__file__).parent.absolute()


def send_tcp(msg, socket_path):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(socket_path)
        except:
            return False
        sock.sendall(msg.encode())
        return True


def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("localhost", port)) == 0


class Manager:
    def manage_app(self, name):
        if not os.path.exists(DIR / pathlib.Path("streamlit_logs")):
            os.mkdir(DIR / pathlib.Path("streamlit_logs"))
        streamlit_log = open(
            DIR / pathlib.Path(f"streamlit_logs/{name}.log"), "a")
        if check_port(self.apps[name]["port"]):
            with streamlit_log as f:
                f.write(
                    f"{name} could not start. Port {self.apps[name]['port']} already in use.\n")
            send_tcp(
                f"{name} could not start. Port {self.apps[name]['port']} already in use.\n",
                self.controller_socket_path)
            return
        venv_bin = pathlib.Path(self.apps[name]["venv"]) / pathlib.Path("bin")
        command = [f"{venv_bin}/python", f"{venv_bin}/streamlit", "run",
                   self.apps[name]["path"]]
        command += ["--server.port", str(self.apps[name]["port"])]
        app_dir = pathlib.Path(self.apps[name]["path"]).parent
        self.apps[name]["pid"] = subprocess.Popen(
            command, stdout=streamlit_log, stderr=streamlit_log, cwd=app_dir).pid
        print(f"{name} started with PID {self.apps[name]['pid']}")
        send_tcp(
            f"{name} started on port {self.apps[name]['port']} with PID {self.apps[name]['pid']}.\n",
            self.controller_socket_path)

        while not self.apps[name]["stopped"]:
            pids = subprocess.check_output(["pgrep", "python"]).splitlines()
            pids = [int(pid) for pid in pids]
            if self.apps[name]["pid"] not in pids:
                self.apps[name]["pid"] = subprocess.Popen(
                    command, stdout=streamlit_log, stderr=streamlit_log).pid
                print(f"{name} restarted with PID {self.apps[name]['pid']}")
            time.sleep(1)

        if self.apps[name]["pid"] is not None:
            os.kill(self.apps[name]["pid"], 9)
            self.apps[name]["pid"] = None
        print(f"{name} stopped")

    def start_app(self, name):
        self.apps[name]["pid"] = None
        self.apps[name]["stopped"] = False
        self.apps[name]["thread"] = threading.Thread(
            target=self.manage_app, args=(name,))
        self.apps[name]["thread"].start()

    def start(self):
        with open(DIR / pathlib.Path("apps.json"), "r") as f:
            starting_apps = json.load(f)

        for name, info in starting_apps.items():
            self.apps[name] = info
            self.start_app(name)

    def stop(self):
        for vals in self.apps.values():
            vals["stopped"] = True
            if vals["pid"] is not None:
                os.kill(vals["pid"], 9)
            if vals["thread"].is_alive():
                vals["thread"].join()

    def restart_app(self, name):
        self.apps[name]["stopped"] = True
        if "thread" in self.apps[name] and self.apps[name]["thread"].is_alive():
            self.apps[name]["thread"].join()
        time.sleep(0.5)
        self.start_app(name)

    def refresh(self):
        with open("apps.json") as f:
            new_apps = json.load(f)
            for name, info in new_apps.items():
                if name not in self.apps:
                    self.apps[name] = info
                    self.start_app(name)
                elif self.apps[name]["path"] == info["path"] \
                        and self.apps[name]["venv"] == info["venv"] \
                        and self.apps[name]["port"] == info["port"]:
                    continue
                else:
                    self.apps[name] = info
                    self.restart_app(name)

        for name, vals in self.apps.items():
            if not vals["thread"].is_alive():
                self.start_app(name)

    def status(self):
        app_status = {name: {"pid": info["pid"],
                             "port": info["port"]} for name,
                      info in self.apps.items()}
        send_tcp(
            json.dumps(
                {"message_type": "status", "apps": app_status}),
            self.controller_socket_path)

    def main_loop(self):
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(self.socket_path)
                sock.listen()
                sock.settimeout(5)
                while True:
                    try:
                        client, addr = sock.accept()
                        data = client.recv(4096)
                    except socket.timeout:
                        continue

                    try:
                        msg = json.loads(data)
                    except json.decoder.JSONDecodeError:
                        continue

                    if msg["message_type"] == "start":
                        self.start()

                    elif msg["message_type"] == "stop":
                        self.stop()
                        print("Manager stopped")
                        exit(0)

                    elif msg["message_type"] == "refresh":
                        print("Refreshing")
                        self.refresh()

                    elif msg["message_type"] == "status":
                        self.status()

                    elif msg["message_type"] == "restart":
                        self.restart_app(msg["app"])
            except Exception as e:
                print(e)
                self.stop()
                print("Manager stopped")
                exit(0)

    def __init__(self, socket_path, controller_socket_path):
        self.socket_path = socket_path
        self.controller_socket_path = controller_socket_path
        self.apps = {}

        self.start()
        self.main_loop()


if __name__ == "__main__":
    socket_path = sys.argv[1]
    controller_socket_path = sys.argv[2]
    Manager(socket_path, controller_socket_path)
