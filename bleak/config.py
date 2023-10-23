import configparser

from storage import Storage

INIFILE = 0
SERIAL_NUMBER = -1
BEACON_TARGET_ID = '1233aacc0dc140a78085303a6d64ddb5'
BEACON_SERVICE_UUID = '9b12a001-68f0-e742-228a-cba37cbb671f'


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
        if Config.serial_number == None:
            raise ValueError("Serial number is not set (required value)!")

        if Config.Storage.use_internet and Config.Storage.internet_url == None:
            raise ValueError(f"Using internet without defining url!")

        return True

def _parse_settings_section(inifile):
    section = inifile['SETTINGS']

    Config.rssi_threshold = int(section.get('rssi_threshold', -100))
    Config.rssi_close_threshold = int(section.get('rssi_close_threshold', Config.rssi_threshold))
    

def _get_storage_paths(inifile, key):
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
    section = inifile['STORAGE']

    beacon_stors = _get_storage_paths(inifile, 'beacon')
    Config.Storage.beacon += beacon_stors

    counting_stors = _get_storage_paths(inifile, 'counting')
    Config.Storage.counting += counting_stors


    # return value is string. bool of non empty string ('0' aswell) results in True
    # therefore we need to cast to int first
    Config.Storage.use_internet = bool(int(section.get('internet_for_counting', '0')))
    Config.Storage.internet_url = section.get('url', None)


def parse_ini(path='config.ini'):
    inifile = configparser.ConfigParser()
    inifile.read(path)

    Config.inifile = inifile

    Config.serial_number = inifile['USER']['devID']

    _parse_settings_section(inifile)
    _parse_storage_section(inifile)

    print(Config.Storage.use_internet)

    Config.check_integrity()





    