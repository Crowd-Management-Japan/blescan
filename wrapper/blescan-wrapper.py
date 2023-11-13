from config import Config, read_config, read_last_updated
import requests
import logging

WRAPPER_CONFIG_PATH = "./config.ini"
BLESCAN_CONFIG_PATH = "./blescan_conf.ini"

def main():
    read_config(WRAPPER_CONFIG_PATH)

    logging.info("--- starting blescan wrapper ---")

    try:
        if is_update_needed():
            logging.info("update needed, downloading new config")
            get_new_config()
        else:
            logging.info("config is up-to-date")

    except requests.RequestException:
        logging.info("No internet connection, starting with existing config")

    logging.info("--- starting blescan ---")

    # TODO actually start blescan
    # how? 1) through python -> maybe problems with asyncio
    # 2) python cmd tool?
    # 3) from start.sh -> just update config here

def is_update_needed():
    request = requests.get(get_url("setup/last_updated/{}"))
    remote_timestamp = request.json()['last_changed']

    local_timestamp = read_last_updated(BLESCAN_CONFIG_PATH)

    return local_timestamp < remote_timestamp



def get_url(endpoint):
    """
    Helper function / shortcut for server url.
    use {} in url to autofill own ID
    """
    end = str.format(endpoint, Config.id)
    
    return f"http://{Config.url}/{end}"

def get_new_config():
    print("--- updating config --- ")
    url = get_url("setup/config_{}")

    request = requests.get(url)
    config = request.text

    
    with open(BLESCAN_CONFIG_PATH, "w") as file:
        file.write(config)
    
    # give callback that this device is ready to use
    requests.post(get_url("setup_completed_{}"))
    

if __name__ == "__main__":
    main()