import logging
import os
import sys
from datetime import datetime, timedelta

import requests

from config import Config, read_config, read_last_updated, read_id

WRAPPER_CONFIG_PATH = "./wrapper/config.ini"
BLESCAN_CONFIG_PATH = "./etc/blescan_conf.ini"
RESTART_COUNTER_PATH = "./etc/counter.txt"

RESTART_LIMIT = 3000

config_found = True

def main():
    # count the number of times the code has been restarted
    # when the number of restarts has been exceeded a complete reboot is triggered
    # this is to fix hardware or rare issues which is typically solved through a reboot
    if file_exists(RESTART_COUNTER_PATH):
        with open(RESTART_COUNTER_PATH, 'r') as file:
            content = file.read().strip()
            restart_counter = int(content) + 1
            if restart_counter >= RESTART_LIMIT:
                os.system('sudo shutdown -r now')
        with open(RESTART_COUNTER_PATH, 'w') as file:
            file.write(str(restart_counter))
    else:
        with open(RESTART_COUNTER_PATH, 'w') as file:
            file.write("0")

    read_config(WRAPPER_CONFIG_PATH)

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

def file_exists(file_path):
    return os.path.exists(file_path)

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

def setup_logger():
    if not os.path.exists("logs"):
        os.mkdir("logs")

    previous_month = datetime.now() - timedelta(days=30)
    old_filename = f"logs/log_{previous_month.strftime('%m%d')}.txt"
    new_filename = f"logs/log_{datetime.now().strftime('%m%d')}.txt"

    if os.path.exists(old_filename):
        os.remove(old_filename)

    logging.getLogger().setLevel(logging.ERROR)
    file_formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    rootLogger = logging.getLogger()
    fileHandler = logging.FileHandler(new_filename)
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

    logging.info("--- starting blescan wrapper ---")

    pwd = os.getcwd()

    logging.info("Wrapper config: %s/%s", pwd, WRAPPER_CONFIG_PATH)
    logging.info("Blescan config: %s/%s", pwd, BLESCAN_CONFIG_PATH)

    main()
