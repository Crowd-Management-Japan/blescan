import configparser
import logging

class Config:

    id = 0
    url = ''
    do_not_update = 0

def read_config(path='./config.ini'):
    logging.debug(f"Parsing ini file {path}")
    inifile = configparser.ConfigParser()
    inifile.read(path)

    section = inifile["USER"]

    Config.id = section.get('devID')
    Config.url = section.get('url')

    Config.do_not_update = int(section.get('ignore_config_update', '0')) == 1

    logging.debug("parsing complete")

def read_id(path):
    try:
        inifile = configparser.ConfigParser()
        inifile.read(path)
        section = inifile['USER']

        return int(section.get('devID', 0))
    except KeyError:
        logging.error("cannot read id from given inifile %s", path)
        return 0

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