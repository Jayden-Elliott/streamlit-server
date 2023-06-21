# Streamlit Server  <!-- omit from toc -->

Streamlit Server provides a way to run and manage many [Streamlit](https://streamlit.io/) apps in the background and host them all together on a convenient website. Since Streamlit requires separate processes for each app bound to different ports, Streamlit Server runs each app process in the background and embeds them in a Flask website run on a single port.


## Get started  <!-- omit from toc -->

- [Installation](#installation)
- [Adding Streamlit apps](#adding-streamlit-apps)
- [Running the Server](#running-the-server)
- [Configuration](#configuration)
- [Other features](#other-features)

### Installation

Ensure you have [Python 3.8+](https://www.python.org/downloads/) installed. Then clone this repository and enter the directory.
    
```shell
git clone https://github.com/Jayden-Elliott/streamlit-server.git
cd streamlit-server
```

Create a virtual environment and install the dependencies.

```shell
python3 -m venv env
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Install the [Flask](https://github.com/pallets/flask) app for the website from source using pip.

```shell
cd streamlit_site
pip install -e .
```

### Adding Streamlit apps

Streamlit apps can be automatically added to the server by adding a directory for each app to the `apps` directory. Each app must have an `app.py` file to be run by streamlit and a `venv` directory if it requires a virtual environment.

```
├── apps
│   ├── <app-key1>
│   │   ├── venv
│   │   ├── app.py
│   │   └── ...
│   ├── <app-key2>
│   │   ├── venv
│   │   ├── app.py
│   │   └── ...   
```

App directories and virtual environments located in other places can also be added to the server by manually providing them in `config.py`. However, the app to be run must still be named `app.py`.

### Running the Server

Run the server from the project root directory.

```shell
./streamlit_controller start
```
This will add all new apps from the `apps` directory to `config.py`, start the process manager and all apps in the background, and start the website on the specified port. The website is be available at `http://127.0.0.1:5000/` by default.

The `streamlit_controller` script takes the following arguments for controlling the server:

* `start`: Starts the server, process manager, all apps, and website.
* `stop`: Stops the server, process manager, all apps, and website.
* `refresh`: Restarts website or any apps that have with changes in `config.py` or that have stopped.
* `status`: Prints all running Streamlit apps and their PIDs or whether they are stopped.
* `stop <app-key>`: Stops the app specified by the key `app-key` (name of app directory) in `config.py`.
* `restart <app-key>`: Restarts the app specified by the key `app-key` in `config.py`.

### Configuration

The website port and the attributes of any apps can be changed in `config.json`, which must have the following structure:


```json
{
    "website_port": <int port to run website on>,
    "apps": {
        <app-key>: {
            "name": <name to appear on website>,
            "url": <url path to app>,
            "dir": <full path to app directory containing app.py>,
            "venv": <full path to virtual environment directory>,
            "port": <int port to run app on>,
            "description": <description of app to appear on website>,
            "restart_on_crash": <true or false whether to restart app if it crashes>
        } ...
    }
}
```

Automatically added apps will have the `name` and `url` attributes will assigned value `app_key`, the `port` attribute assigned the next available port starting from 8501, `restart_on_crash` assigned `true`, and `description` assigned an empty string.

By default, the controller and process manager will communicate via TCP over ports `8499` and `8500`, and new streamlit apps added automatically will be given open ports increasing from `8501`. If you wish to change these ports, edit the constants at the top of `streamlit-controls/controller.py`. 

> **Note**
> 
> Stop the server before changing these ports. Changing the ports while the server is running will leave the process manager running in the background and inaccessible.

### Other features

Log files for each app are stored in `logs/<app-key>.log` and store the command line output of the app. The log files for the controller/process manager and website are stored in `logs/controller.log` and `logs/website.log` respectively.