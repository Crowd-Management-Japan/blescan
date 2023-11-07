from config import Config, read_config, read_last_updated
import requests

WRAPPER_CONFIG_PATH = "./config.ini"
BLESCAN_CONFIG_PATH = "./blescan_conf.ini"

def main():
    read_config(WRAPPER_CONFIG_PATH)

    try:

        request = requests.get(f"http://{Config.url}/setup/last_updated/{Config.id}")

        remote_timestamp = request.json()['last_changed']

        print(remote_timestamp)

        local_timestamp = read_last_updated(BLESCAN_CONFIG_PATH)

        if local_timestamp < remote_timestamp:
            get_new_config()

    except requests.RequestException:
        print("No internet connection, starting with existing config")

    print("--- starting blescan ---")



def get_new_config():
    print("--- updating config --- ")
    url = f"http://{Config.url}/setup/config_{Config.id}"

    request = requests.get(url)
    config = request.text

    with open(BLESCAN_CONFIG_PATH, "w") as file:
        file.write(config)

if __name__ == "__main__":
    main()