import click
import json
from streamlit_manager import send_tcp
import socket
import subprocess
import os
import time
from pathlib import Path

DIR = Path(__file__).parent.parent.absolute()
MANAGER_SOCKET_PORT = 8499
CONTROLLER_SOCKET_PORT = 8500
START_PORT = 8501
CONTROLLER_LOG_PATH = DIR / Path("logs/controller.log")


# Get response from manager to print
def get_response(timeout):
    start_time = time.time()
    response = ""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", CONTROLLER_SOCKET_PORT))
        sock.listen()
        sock.settimeout(2)
        while time.time() - start_time < timeout:
            try:
                client, addr = sock.accept()
                response += client.recv(4096).decode()
            except socket.timeout:
                pass
    return response


# Get next open port starting from START_PORT and not in used_ports
def get_open_port(used_ports=[]):
    # Check if port is open
    def is_open(port):
        if port in used_ports:
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(("localhost", port)) != 0

    # Find open port
    start = START_PORT
    while not is_open(start):
        start += 1
    return start


# Update config file with new apps and update app config files with correct port and url path
def update_config():
    # Create config file if it doesn't exist
    if not os.path.exists(DIR / Path("config.json")):
        os.system(f"touch {DIR / Path('config.json')}")
    config = json.load(open(DIR / Path("config.json"), "r"))

    # Create apps object in config file if it doesn't exist
    if "apps" not in config:
        config["apps"] = {}
    apps = config["apps"]
    if not os.path.exists(DIR / Path("apps/")):
        os.mkdir(DIR / Path("apps/"))

    # Get ports of existing apps in config.json
    used_ports = [app["port"] for app in apps.values()]

    # Add new apps in apps directory to config file with default values
    for app in os.listdir(DIR / Path("apps/")):
        if app in apps:
            continue
        venv = ""
        if os.path.exists(DIR / Path(f"apps/{app}/env")):
            venv = f"{DIR / Path(f'apps/{app}/env')}"
        if not os.path.exists(DIR / Path(f"apps/{app}/app.py")):
            print(
                f"Streamlit file for {app} not found. Please provide it in the app directory in a file named \"app.py\".")
            continue
        port = get_open_port(used_ports)
        used_ports.append(port)
        apps[app] = {
            "name": app,
            "url": f"/{app}/",
            "dir": f"{DIR / Path('apps')}/{app}",
            "venv": venv,
            "port": port,
            "description": "",
            "restart_on_crash": True
        }

    # Write changes to config.json
    config["apps"] = apps
    json.dump(config, open(DIR / Path("config.json"), "w"), indent=4)


# Check if manager is running
def manager_running(exit_if_running=False):
    running = subprocess.call(
        ["pgrep", "-f", "streamlit_manager.py"],
        stdout=subprocess.DEVNULL) == 0

    if exit_if_running and running:
        print("Manager already running")
        exit(1)

    if not exit_if_running and not running:
        print("Manager not running")
        exit(1)

# Update config.json with new apps and start manager


def start():
    # Update config.son with new apps
    update_config()

    # Check if manager is running
    manager_running(exit_if_running=True)

    # Create log file if it doesn't exist
    if not os.path.exists(CONTROLLER_LOG_PATH):
        open(CONTROLLER_LOG_PATH, "w").close()
        os.chmod(CONTROLLER_LOG_PATH, 0o777)
    log = open(CONTROLLER_LOG_PATH, "a")

    # Start manager process
    pid = subprocess.Popen(
        ["python", "-u",
         (DIR / Path("streamlit_controls/streamlit_manager.py")).as_posix(),
         str(MANAGER_SOCKET_PORT),
         str(CONTROLLER_SOCKET_PORT)],
        stdout=log).pid
    log.write(f"Manager started with PID {pid}\n")
    print(get_response(1), end="")
    exit(0)


# Stop manager and all running apps
def stop():
    # Check if manager is running
    manager_running()

    # Send stop message to manager
    send_tcp(json.dumps({"message_type": "stop"}), MANAGER_SOCKET_PORT)
    exit(0)


# Get status of manager and all running apps
def status():
    # Check if manager is running
    manager_running()

    # Read status from status.json
    status = json.load(open(DIR / Path("streamlit_controls/status.json"), "r"))

    # Print status
    longest_name = max([len(name) for name in status])
    print(f"{'Name': <{longest_name}}    PID")
    for name, vals in status.items():
        pid = vals["pid"] if vals["pid"] else "Stopped"
        print(
            f"{name: <{longest_name}}    {pid}")
    exit(0)


# Refresh manager with changes to config file
def refresh():
    # Update config.json with new apps
    update_config()

    # Check if manager is running
    manager_running()

    # Send refresh message to manager
    send_tcp(json.dumps({"message_type": "refresh"}),
             MANAGER_SOCKET_PORT)
    print(get_response(2), end="")
    exit(0)


# Restart a specific app
def restart(app_name):
    # Check if app name argument was provided
    if app_name is None:
        print("App name required for restart")
        exit(1)

    # Check if manager is running
    manager_running()

    # Send restart message to manager
    send_tcp(
        json.dumps({"message_type": "restart", "app": app_name}),
        MANAGER_SOCKET_PORT)
    print(get_response(2), end="")
    exit(0)


# Stop a specific app
def stop_app(app_name):
    # Check if app name argument was provided
    if app_name is None:
        print("App name required for stop")
        exit(1)

    # Check if manager is running
    manager_running()

    # Send stop message to manager
    send_tcp(
        json.dumps({"message_type": "stop_app", "app": app_name}),
        MANAGER_SOCKET_PORT)
    print(get_response(2), end="")
    exit(0)


@click.command()
@click.argument("operation", type=click.Choice(
    ["start", "stop", "status", "refresh", "restart"]))
@click.argument("app_name", required=False)
def main(operation, app_name):
    """
    Control running streamlit apps

    \b
    Argument 1 is the operation to perform
    start:   Start process manager, all apps, and website
    stop:    Stop process manager, all running apps, and website
    stop <app-key>: Stop a specific app
    status:  Show status of running apps
    refresh: Refresh from changes in config.json
    restart <app-key>: Restart a specific app
    """

    config = json.load(open(DIR / Path("config.json"), "r"))

    if operation == "start":
        start()

    elif operation == "stop":
        if app_name is not None:
            stop_app(app_name)
        else:
            stop()

    elif operation == "status":
        status()

    elif operation == "refresh":
        refresh()

    elif operation == "restart":
        restart(app_name)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
