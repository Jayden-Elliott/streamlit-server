# Streamlit Server

Streamlit server provides a way to run and manage many streamlit apps in the background and host them all together on a convenient website.

## Get Started

1. [Clone the repository](#clone-the-repository)
2. [Install the dependencies](#install-the-dependencies)
3. [Install the Flask app](#install-the-flask-app)
4. [Update configuration](#update-configuration)
5. [Add Streamlit apps](#add-streamlit-apps)
6. [Run the server](#run-the-server)
7. [Control the server](#control-the-server)
8. [Customize apps](#customize-apps)

### Clone the Repository

Ensure you have Python 3.8+ installed. Then clone this repository and enter the directory.
    
```bash
git clone https://github.com/Jayden-Elliott/streamlit-server.git
cd streamlit-server
```

### Install the Dependencies
Create a virtual environment and install the dependencies.

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Install the Flask App
Install the Flask app for the website from source using pip.

```bash
cd streamlit_site
pip install -e .
```

### Update Configuration
Open the `config.json` file and update the default port for the website if you wish. By default the website will run on port 5000.

By default, the controller and process manager will communicate via TCP over ports 8499 and 8500, and new streamlit apps will be run on open ports increasing from 8501. If you wish to change these ports, edit the constants at the top of `streamlit-controls/controller.py`. 
> **Note**
>
> Stop the server before changing these ports. Changing the ports while the server is running will leave the process manager running in the background and inaccessible.

### Add Streamlit apps
Streamlit apps can be automatically added to the server by adding a directory for each app to the `apps` directory. Each app must have an `app.py` file to be run by streamlit and a `venv` directory if it requires a virtual environment.

```
├── apps
│   ├── app1
│   │   ├── app.py
│   │   └── venv
│   ├── app2
│   │   ├── app.py
│   │   └── venv    
```

App directories and virtual environments located in other places can also be added to the server by manually providing them in `config.py`. However, the app to be run must still be named `app.py`.

### Run the Server
Run the server from the project root directory.

```bash
./streamlit_controller start
```
This will add all new apps from the `apps` directory to `config.py`, start the process manager and all apps in the background, and start the website on the specified port. The website is be available at `http://localhost:5000` by default.

### Control the Server
The following arguments can be used after the `./control_streamlit` script to control the server.

* `start`: Starts the server, process manager, all apps, and website.
* `stop`: Stops the server, process manager, all apps, and website.
* `refresh`: Applies any changes to `config.py` with a restart to any app with changes or the website.
* `status`: Prints all running Streamlit apps and their PIDs or whether they are stopped.
* `stop <app-key>`: Stops the app specified by the key `app-key` (name of app directory) in `config.py`.
* `restart <app-key>`: Restarts the app specified by the key `app-key` in `config.py`.
