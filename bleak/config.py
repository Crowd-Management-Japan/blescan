import configparser

from storage import Storage
from network import Upstream


class Config:

    inifile = None
    serial_number = None

    rssi_threshold = -100
    rssi_close_threshold = rssi_threshold

    beacon_target_id = '1233aacc0dc140a78085303a6d64ddb5'

    class Storage:

        beacon = []
        counting = []

        use_internet = False
        internet_url = None

        use_zigbee = False

    @staticmethod
    def check_integrity():
        """
        Check integrity for config values and throw an error if problems occur
        """
        if Config.serial_number == None:
            raise ValueError("Serial number is not set (required value)!")

        if Config.Storage.use_internet and Config.Storage.internet_url == None:
            raise ValueError(f"Using internet without defining url!")

def _parse_settings_section(inifile):
    """subfunction for parsing the SETTINGS section"""
    section = inifile['SETTINGS']

    Config.rssi_threshold = int(section.get('rssi_threshold', -100))
    Config.rssi_close_threshold = int(section.get('rssi_close_threshold', Config.rssi_threshold))
    Config.beacon_target_id = section.get('beacon_target_id', '')
    

def _get_storage_paths(inifile, key):
    """retrieve a list of defined storage places"""
    section = inifile['STORAGE']
    paths = inifile['STORAGE PATHS']

    keys = [_.strip() for _ in section.get(key, '').split(',')]

    stors = []

    for stor in keys:
        path = paths.get(stor, None)
        if path == None:
            raise ValueError(f"No path definition for storage {stor}! exiting")

        stors.append(Storage(path))

    return stors

def _parse_storage_section(inifile):
    """subfunction for parsing the STORAGE section"""
    section = inifile['STORAGE']

    beacon_stors = _get_storage_paths(inifile, 'beacon')
    Config.Storage.beacon += beacon_stors

    counting_stors = _get_storage_paths(inifile, 'counting')
    Config.Storage.counting += counting_stors


    # return value is string. bool of non empty string ('0' aswell) results in True
    # therefore we need to cast to int first
    Config.Storage.use_internet = bool(int(section.get('internet_for_counting', '0')))
    Config.Storage.internet_url = section.get('url', None)

    if Config.Storage.use_internet:
        up = Upstream(Config.Storage.internet_url)
        Config.Storage.counting.append(up)


def parse_ini(path='config.ini'):
    """
    Parse the given ini-file and set corresponding values.
    See sample ini-file for reference of possible values.
    """
    inifile = configparser.ConfigParser()
    inifile.read(path)

    Config.inifile = inifile

    Config.serial_number = inifile['USER']['devID']

    _parse_settings_section(inifile)
    _parse_storage_section(inifile)

    Config.check_integrity()





    