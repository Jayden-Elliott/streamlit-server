import json
import socket
import os
import threading
import subprocess
from pathlib import Path
import sys
import time

DIR = Path(__file__).parent.parent.absolute()


def send_tcp(msg, socket_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(("localhost", socket_port))
        except:
            return False
        sock.sendall(msg.encode())
        return True


def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("localhost", port)) == 0


class Manager:
    # Write PID to status.json
    def write_status(self, name, pid):
        self.lock.acquire()
        status = json.load(open(
            DIR / Path("streamlit_controls/status.json"), "r"))
        if name not in status:
            status[name] = {}
        status[name]["pid"] = pid
        json.dump(status, open(
            DIR / Path("streamlit_controls/status.json"), "w"), indent=4)
        self.lock.release()

    # Write PID to status.json
    def write_pid_status(self, name):
        self.write_status(name, self.apps[name]["pid"])

    # Write None to status.json
    def write_stop_status(self, name):
        self.write_status(name, None)

    # Write message to log file and send to controller
    def log_and_send(self, logfile_path, message):
        with open(logfile_path, "a") as f:
            f.write(message)
        send_tcp(message, self.controller_socket_port)

    # Print message and send to controller
    def print_and_send(self, message):
        print(message, end="")
        send_tcp(message, self.controller_socket_port)

    def manage_app(self, name):
        # Create log file for app if it doesn't exist
        if not os.path.exists(DIR / Path("logs")):
            os.mkdir(DIR / Path("logs"))
        streamlit_log_path = DIR / Path(f"logs/{name}.log")
        if not os.path.exists(streamlit_log_path):
            open(streamlit_log_path, "w").close()
            os.chmod(streamlit_log_path, 0o777)

        # Check if app port is available and return if not
        if check_port(self.apps[name]["port"]):
            message = f"{name} could not start. Port {self.apps[name]['port']} already in use.\n"
            self.log_and_send(streamlit_log_path, message)
            self.write_stop_status(name)
            return

        # Check if virtual environment exists and return if not
        if not os.path.exists(
                Path(self.apps[name]["venv"]) / Path("bin")):
            message = f"{name} could not start. Virtual environment {self.apps[name]['venv']} not found.\n"
            if self.apps[name]["venv"] == "":
                message = f"{name} could not start. Please provide a virtual environment in \"config.json\".\n"
            self.log_and_send(streamlit_log_path, message)
            self.write_pid_status(name)
            return

        # Start app process and redirect stdout and stderr to log file
        venv_bin = Path(self.apps[name]["venv"]) / Path("bin")
        app_dir = Path(self.apps[name]["dir"])
        command = [f"{venv_bin}/python", f"{venv_bin}/streamlit", "run",
                   app_dir / Path("app.py")]
        command += ["--server.port", str(self.apps[name]["port"])]
        streamlit_log = open(streamlit_log_path, "a")
        self.apps[name]["pid"] = subprocess.Popen(
            command, stdout=streamlit_log, stderr=streamlit_log, cwd=app_dir).pid
        self.write_pid_status(name)
        message = f"{name} started at URL path {self.apps[name]['url']} with PID {self.apps[name]['pid']}.\n"
        self.print_and_send(message)

        # Main loop: if app crashes and restart_on_crash is True, restart it
        while not self.apps[name]["stopped"]:
            pids = subprocess.check_output(["pgrep", "python"]).splitlines()
            pids = [int(pid) for pid in pids]
            if self.apps[name]["pid"] not in pids and self.apps[name][
                    "restart_on_crash"]:
                self.apps[name]["pid"] = subprocess.Popen(
                    command, stdout=streamlit_log, stderr=streamlit_log).pid
                self.write_pid_status(name)
                print(f"{name} restarted with PID {self.apps[name]['pid']}")
            time.sleep(5)

        # After stop message is received, kill app process
        if self.apps[name]["pid"] is not None:
            try:
                os.kill(self.apps[name]["pid"], 9)
            except ProcessLookupError:
                pass
            self.apps[name]["pid"] = None
            self.write_pid_status(name)
        print(f"{name} stopped")

    # Start app process in a new thread
    def start_app(self, name):
        self.apps[name]["pid"] = None
        self.apps[name]["stopped"] = False
        self.apps[name]["thread"] = threading.Thread(
            target=self.manage_app, args=(name,))
        self.apps[name]["thread"].start()

    # Start website process
    def start_site(self):
        # Get website port from config.json
        port = json.load(open(DIR / Path("config.json"), "r"))["website_port"]

        # Create log file for website if it doesn't exist
        streamlit_site_log_path = DIR / Path("logs/streamlit_site.log")
        if not os.path.exists(streamlit_site_log_path):
            open(streamlit_site_log_path, "w").close()
            os.chmod(streamlit_site_log_path, 0o777)

        # Start website process and redirect stdout and stderr to log file
        streamlit_site_log = open(streamlit_site_log_path, "a")
        self.site_process = subprocess.Popen(
            ["flask", "--app", "streamlit_site", "run", "--host", "0.0.0.0",
             "--port", str(port)],
            cwd=DIR / Path("streamlit_site"),
            stdout=streamlit_site_log, stderr=streamlit_site_log)
        message = f"Streamlit site started at http://127.0.0.1:{port}.\n"
        self.print_and_send(message)

    # Start all apps and website
    def start(self):
        with open(DIR / Path("config.json"), "r") as f:
            config = json.load(f)
            starting_apps = config["apps"]
        for name, info in starting_apps.items():
            self.apps[name] = info
            self.start_app(name)
        self.start_site()

    # Join app management thread and kill app process
    def stop_app(self, name):
        self.apps[name]["stopped"] = True
        if "thread" in self.apps[name] and self.apps[name]["thread"].is_alive():
            self.apps[name]["thread"].join()
        if self.apps[name]["pid"] is not None:
            os.kill(self.apps[name]["pid"], 9)

    # Kill website process
    def stop_site(self):
        if self.site_process is not None:
            self.site_process.kill()

    # Stop all apps and website
    def stop(self):
        for app in self.apps:
            self.stop_app(app)
        self.stop_site()

    # Restart app process
    def restart_app(self, name):
        self.apps[name]["stopped"] = True
        if "thread" in self.apps[name] and self.apps[name]["thread"].is_alive():
            self.apps[name]["thread"].join()
        time.sleep(0.5)
        self.start_app(name)

    # Apply changes in config.json
    def refresh(self):
        with open("config.json") as f:
            new_config = json.load(f)
            new_apps = new_config["apps"]
            for name, info in new_apps.items():
                # Start new apps
                if name not in self.apps:
                    self.apps[name] = info
                    self.start_app(name)
                    continue

                # Skip apps with no changes
                if self.apps[name]["port"] == info["port"] \
                        and self.apps[name]["dir"] == info["dir"] \
                        and self.apps[name]["venv"] == info["venv"]:
                    continue

                # Restart apps with changes
                self.apps[name] = info
                self.restart_app(name)

            # Restart website if port has changed
            if "website_port" in new_config and \
                    new_config["website_port"] != self.site_port:
                self.stop_site()
                self.site_port = new_config["website_port"]
                self.start_site()

        # Start any apps that have stopped
        for name, vals in self.apps.items():
            if not vals["thread"].is_alive():
                self.start_app(name)

    # Main loop for receiving messages from controller script
    def main_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("localhost", self.socket_port))
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
                        break

                    elif msg["message_type"] == "refresh":
                        print("Refreshing")
                        self.refresh()

                    elif msg["message_type"] == "restart":
                        self.restart_app(msg["app"])

                    elif msg["message_type"] == "stop_app":
                        self.stop_app(msg["app"])

            except Exception as e:
                print(e)
                self.stop()
                print("Manager stopped")
                exit(0)

    def __init__(self, socket_port, controller_socket_port):
        self.socket_port = socket_port
        self.controller_socket_port = controller_socket_port
        self.apps = {}
        self.site_process = None
        self.site_port = None
        self.lock = threading.Lock()

        self.start()
        self.main_loop()


if __name__ == "__main__":
    socket_port = int(sys.argv[1])
    controller_socket_port = int(sys.argv[2])
    Manager(socket_port, controller_socket_port)
