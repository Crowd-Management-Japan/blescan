from config import Config, read_config, read_last_updated, read_id
import requests
import logging
import sys
import os
import shutil
from datetime import datetime

WRAPPER_CONFIG_PATH = "./wrapper/config.ini"
BLESCAN_CONFIG_PATH = "./etc/blescan_conf.ini"

config_found = True

def main():
    read_config(WRAPPER_CONFIG_PATH)

    if Config.upload_last_config:
        upload_logfile()

    if Config.local_installation:
        logging.info("RUNNING LOCAL INSTALLATION. Quitting Wrapper and start blescan")
        sys.exit(50)


    try:
        if is_update_needed() or is_different_id():
            logging.info("update needed, downloading new config")
            get_new_config()
        else:
            logging.info("config is up-to-date")
            
        # give callback that this device is ready to use
        requests.post(get_url("setup/completed_{}"), timeout=5)

    except requests.RequestException:
        logging.info("No internet connection, starting with existing config")
    except ValueError as e:
        logging.error("Value error %s", e)
        if config_found:
            logging.info("Using old config")
        else:
            logging.info("No config found and can't get new one")
            # exit with error code, just that start.sh knows to use default fallback config
            sys.exit(-1)

    logging.info("--- starting blescan ---")
    # the actual start is done by the start.sh script, so just exit
    sys.exit(0)

def is_different_id():
    wrapper = read_id(WRAPPER_CONFIG_PATH)
    blescan = read_id(BLESCAN_CONFIG_PATH)

    logging.debug("comparing devIDs (local <> requested): %d <> %d", blescan, wrapper)

    return wrapper != blescan

def is_update_needed():
    if Config.do_not_update:
        logging.info("Ignoring update due to config")
        return False

    request = requests.get(get_url("setup/last_updated/{}"), timeout=5)
    remote_timestamp = request.json()['last_changed']

    local_timestamp = read_last_updated(BLESCAN_CONFIG_PATH)
    if local_timestamp < 0:
        global config_found
        config_found = False

    logging.debug("last updated (local <> remote) %d <> %d", local_timestamp, remote_timestamp)

    return local_timestamp < remote_timestamp



def get_url(endpoint):
    """
    Helper function / shortcut for server url.
    use {} in url to autofill own ID
    """
    end = str.format(endpoint, Config.id)
    
    return f"http://{Config.url}/{end}"

def get_new_config():
    logging.info("--- updating config --- ")
    url = get_url("setup/config_{}")

    request = requests.get(url)
    config = request.text

    if request.status_code != 200:
        raise ValueError(f'Getting config return error code {request.status_code}. {config}')


    
    with open(BLESCAN_CONFIG_PATH, "w") as file:
        file.write(config)
    
    logging.info("done")
    

def response_done():
    # give callback that this device is ready to use
    requests.post(get_url("setup/completed_{}"))

def upload_logfile():
    logging.debug("uploading logfile")
    if Config.local_installation:
        logging.debug("Cannot upload logfile with local installation")
        return
    

    file = "logs/log_upload.txt"
    endpoint = f"log/upload_{Config.id}"

    files = {"log": open(file, "rb")}

    response = requests.post(get_url(endpoint), files=files)

    if response.status_code == 200:
        logging.info("logfile upload succeeded")


def delete_old_logs(num_to_keep=5):
    # TODO
    pass

    

def save_last_log():
    lastlog = f"logs/log_newest.txt"
    if not os.path.exists(lastlog):
        return
    today = datetime.now()
    datestr = f"{today.day:02}"
    filename = f"logs/log_{datestr}.txt"
    upload = f"logs/log_upload.txt"
    shutil.copy(lastlog, upload)

    with open(lastlog, "r") as last:
        lines = last.readlines()
    with open(filename, "a") as file:
        file.writelines(lines)

    # afterwards truncate the last one
    with open(lastlog, "w"):
        pass

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    save_last_log()
    filename = f"logs/log_newest.txt"
    logging.getLogger().setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s")
    rootLogger = logging.getLogger()
    fileHandler = logging.FileHandler(filename)
    fileHandler.setFormatter(file_formatter)
    consoleHandler = logging.StreamHandler()
    rootLogger.addHandler(consoleHandler)
    rootLogger.addHandler(fileHandler)

if __name__ == "__main__":

    if len(sys.argv) > 1:
        WRAPPER_CONFIG_PATH = sys.argv[1]
        if len(sys.argv) > 2:
            BLESCAN_CONFIG_PATH = sys.argv[2]


    setup_logger()
    

    logging.info("----------------------------------------")
    logging.info(f"## blescan wrapper starting ##")
    logging.info("----------------------------------------")

    pwd = os.getcwd()

    logging.info("Wrapper config: %s/%s", pwd, WRAPPER_CONFIG_PATH)
    logging.info("Blescan config: %s/%s", pwd, BLESCAN_CONFIG_PATH)

    main()