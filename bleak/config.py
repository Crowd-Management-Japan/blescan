import configparser

import storage


class Config:

    inifile = None
    serial_number = None

    class Counting:
        rssi_threshold = -100
        rssi_close_threshold = rssi_threshold
        delta = 10
        storage = []
        use_internet = False
        internet_url = None

    class Zigbee:
        use_zigbee = False
        internet_ids = []

        port = "/dev/TTYUSB0"
        baud_rate = 9600
        coordinator = False
        my_label = "42"

    class Beacon:
        target_id = ''
        scans = 8
        threshold = 3
        storage = []

    @staticmethod
    def check_integrity():
        """
        Check integrity for config values and throw an error if problems occur
        """
        if Config.serial_number == None:
            raise ValueError("Serial number is not set (required value)!")

        if Config.Counting.use_internet and Config.Counting.internet_url == None:
            raise ValueError(f"Using internet without defining url!")
        
        if Config.Zigbee.use_zigbee and not Config.Zigbee.internet_ids:
            raise ValueError("Using Zigbee, but no internet nodes set")
        
        if not Config.Counting.storage and not Config.Beacon.storage:
            raise ValueError("Not storing any counting or beacon data!")

def _get_storage_paths(inifile, section, key):
    """retrieve a list of defined storage places"""
    paths = inifile['STORAGE PATHS']

    keys = [_.strip() for _ in section.get(key, '').split(',')]

    stors = []

    for stor in keys:
        path = paths.get(stor, None)
        if path == None:
            raise ValueError(f"No path definition for storage {stor}! exiting")

        stors.append(storage.Storage(path))

    return stors

def _parse_counting_settings(inifile):
    section = inifile['COUNTING']
    Config.Counting.rssi_threshold = int(section.get('rssi_threshold', -100))
    Config.Counting.rssi_close_threshold = int(section.get('rssi_close_threshold', Config.Counting.rssi_threshold))
    Config.Counting.delta = int(section.get('delta', 10))
    Config.Counting.storage += _get_storage_paths(inifile, section, 'storage')
    
    # return value is string. bool of non empty string ('0' aswell) results in True
    # therefore we need to cast to int first
    Config.Counting.use_internet = bool(int(section.get('internet_for_counting', '0')))
    Config.Counting.internet_url = section.get('url', None)
    

def _parse_zigbee_settings(inifile):
    section = inifile["ZIGBEE"]
    Config.Zigbee.use_zigbee = bool(int(section.get('use_zigbee', '0')))
    nodes = section.get('internet_nodes')
    Config.Zigbee.internet_ids = [_.strip() for _ in nodes.split(',')]


def _parse_beacon_settings(inifile):
    section = inifile['BEACON']
    Config.Beacon.target_id = section.get('target_id', '')
    Config.Beacon.scans = int(section.get('scans', 8))
    Config.Beacon.threshold = int(section.get('threshold', 3))
    Config.Beacon.storage += _get_storage_paths(inifile, section,'storage')


def parse_ini(path='config.ini'):
    """
    Parse the given ini-file and set corresponding values.
    See sample ini-file for reference of possible values.
    """
    print(f"Parsing ini file {path}")
    inifile = configparser.ConfigParser()
    inifile.read(path)

    Config.inifile = inifile

    Config.serial_number = inifile['USER']['devID']

    _parse_counting_settings(inifile)
    _parse_zigbee_settings(inifile)
    _parse_beacon_settings(inifile)

    Config.check_integrity()





    