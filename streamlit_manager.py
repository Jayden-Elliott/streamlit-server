import json
import socket
import os
import threading
import subprocess
import logging
import pathlib
import sys


STREAMLIT_LOG_DIR = pathlib.Path(
    "/home/elliotjd/streamlit_manager/streamlit_logs")


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


class App:
    def start(self):
        if check_port(self.port):
            print(f"{self.name} could not start. Port {self.port} already in use.\n")
            send_tcp(
                f"{self.name} could not start. Port {self.port} already in use.\n", self.controller_socket_path)
            return False
        venv_bin = f"/home/shared/venv/{self.venv}/bin"
        command = [f"{venv_bin}/python",
                   f"{venv_bin}/streamlit", "run", self.path]
        command += ["--server.port", str(self.port)]
        streamlit_log = open(f"{STREAMLIT_LOG_DIR / self.name}.log", "a")
        self.pid = subprocess.Popen(
            command, stdout=streamlit_log, stderr=streamlit_log).pid
        print(f"{self.name} started with PID {self.pid}")
        send_tcp(json.dumps({"message_type": "pid_update",
                 "name": self.name, "pid": self.pid}), self.manager_socket_path)
        return True

    def main_loop(self):
        try:
            os.unlink(self.socket_path)
        except OSError:
            if os.path.exists(self.socket_path):
                raise

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.bind(self.socket_path)
            sock.listen()
            sock.settimeout(5)
            while True:
                pids = subprocess.check_output(
                    ["pgrep", "python"]).splitlines()
                pids = [int(pid) for pid in pids]
                if self.pid not in pids:
                    self.start()

                try:
                    client, addr = sock.accept()
                    data = client.recv(4096)
                except socket.timeout:
                    continue

                try:
                    msg = json.loads(data)
                except json.decoder.JSONDecodeError:
                    continue

                if msg is None or "message_type" not in msg:
                    continue

                try:
                    match msg["message_type"]:
                        case "stop":
                            if self.pid is not None:
                                os.kill(self.pid, 9)
                                self.pid = None
                            print(f"{self.name} stopped")
                            return
                except Exception as e:
                    print(e)

    def __init__(self, name, info, manager_socket_path, controller_socket_path):
        self.name = name
        self.path = info["path"]
        self.venv = info["venv"]
        self.port = info["port"]
        self.socket_path = f"/tmp/streamlit-{self.name}.sock"
        self.manager_socket_path = manager_socket_path
        self.controller_socket_path = controller_socket_path
        self.pid = None

        if not self.start():
            return
        self.main_loop()


class Manager:
    def start_app(self, name, info):
        self.apps[name] = info
        app_thread = threading.Thread(
            target=App, args=(name, info, self.socket_path, self.controller_socket_path))
        app_thread.start()
        self.apps[name]["thread"] = app_thread
        self.apps[name]["socket"] = f"/tmp/streamlit-{name}.sock"
        self.apps[name]["pid"] = None

    def start(self):
        with open("apps.json") as f:
            starting_apps = json.load(f)

        for name, info in starting_apps.items():
            self.start_app(name, info)

    def stop(self):
        for info in self.apps.values():
            send_tcp(json.dumps({"message_type": "stop"}), info["socket"])
            info["thread"].join()

    def main_loop(self):
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
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

                match msg["message_type"]:
                    case "start":
                        self.start()

                    case "stop":
                        self.stop()
                        print("Manager stopped")
                        exit(0)

                    case "refresh":
                        print("Refreshing")
                        with open("apps.json") as f:
                            new_apps = json.load(f)
                        for name, info in new_apps.items():
                            if name not in self.apps:
                                self.start_app(name, info)
                            elif self.apps[name]["path"] == info["path"] and self.apps[name]["venv"] == info["venv"] and self.apps[name]["port"] == info["port"]:
                                continue
                            else:
                                send_tcp(json.dumps(
                                    {"message_type": "stop"}), self.apps[name]["socket"])
                                self.apps[name]["thread"].join()
                                self.start_app(name, info)

                    case "status":
                        pids = {name: info["pid"]
                                for name, info in self.apps.items()}
                        send_tcp(json.dumps(
                            {"message_type": "status", "pids": pids}), msg["socket"])

                    case "pid_update":
                        if msg["name"] not in self.apps:
                            continue
                        self.apps[msg["name"]]["pid"] = msg["pid"]

                    case "app_stopped":
                        if msg["name"] not in self.apps:
                            break
                        self.apps.pop(msg["name"])

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
