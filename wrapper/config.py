import configparser
import logging

class Config:

    id = 0
    url = ''

def read_config(path='./config.ini'):
    logging.debug(f"Parsing ini file {path}")
    inifile = configparser.ConfigParser()
    inifile.read(path)

    section = inifile["BASE"]

    Config.id = section.get('id')
    Config.url = section.get('url')

    logging.debug("parsing complete")


def read_last_updated(path='../bleak/config.ini'):
    try:
        inifile = configparser.ConfigParser()
        inifile.read(path)
        section = inifile["USER"]

        return int(section.get('last_updated', 0))
    except FileNotFoundError:
        logging.error("Configfile not found")
        return -1
    except KeyError:
        logging.error("Config file in wrong format.")
        return -1