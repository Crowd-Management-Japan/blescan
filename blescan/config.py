import configparser
from typing import List

import storage
import logging

logger = logging.getLogger('blescan.config')

class Config:

    inifile: configparser.ConfigParser = None
    serial_number: int = None

    led: bool = True
    scantime: int = 1

    use_location: bool = False
    longitude: float = None
    latitude: float = None

    class Counting:
        rssi_threshold: int = -100
        rssi_close_threshold: int = rssi_threshold
        delta: int = 10
        static_ratio: float = 0.7
        storage: List = []
        use_internet: bool = False
        internet_url: str = None

    class XBee:
        use_xbee: bool = False
        internet_ids: List[str] = []

        pan: int = 1

        port: str = "auto"
        baud_rate: int = 9600
        is_coordinator: bool = True
        my_label: str = " "

    class Beacon:
        target_id: str = ''
        scans: int = 10
        threshold: int = 3
        storage: List = []
        shutdown_on_scan: bool = False
        shutdown_id: str = None

    class Transit:
        delta: int = 5
        enabled: bool = False
        internet_url: str = None

    @staticmethod
    def check_integrity():
        """
        Check integrity for config values and throw an error if problems occur
        """
        if Config.serial_number == None:
            raise ValueError("Serial number is not set (required value)!")

        if Config.Counting.use_internet and Config.Counting.internet_url == None:
            raise ValueError(f"Using internet for counting without defining url!")
        
        if Config.Transit.enabled and Config.Transit.internet_url == None:
            raise ValueError(f"Using internet for transit without defining url!")
        
        if Config.XBee.use_xbee and not Config.XBee.internet_ids:
            raise ValueError("Using XBee, but no internet nodes set")
        
        if not Config.Counting.storage and not Config.Beacon.storage and not Config.Counting.use_internet and not Config.Transit.enabled:
            raise ValueError("Not storing any counting, beacon or transit data!")

def _get_storage_paths(inifile, section, key):
    """retrieve a list of defined storage places"""
    paths = inifile['STORAGE PATHS']

    keys = [_.strip() for _ in section.get(key, '').split(',')]

    stors = []

    for stor in keys:
        if stor == '':
            continue
        path = paths.get(stor, None)
        if path == None:
            logger.error(f"No path definition for storage {stor}! Ignoring")
            continue

        try:

            stors.append(storage.Storage(path))
        except PermissionError:
            logger.error("No permissions for storage %s. Ignoring", path)

    return stors

def _parse_transit_settings(inifile):
    logger.debug("parsing transit time config")
    section = inifile['TRANSIT']
    Config.Transit.delta = int(section.get('delta', 5))
    Config.Transit.enabled = bool(int(section.get('transit_enabled', '0')))
    Config.Transit.internet_url = section.get('url', None)

def _parse_counting_settings(inifile):
    logger.debug("parsing counting config")
    section = inifile['COUNTING']
    Config.Counting.rssi_threshold = int(section.get('rssi_threshold', -100))
    Config.Counting.rssi_close_threshold = int(section.get('rssi_close_threshold', Config.Counting.rssi_threshold))
    Config.Counting.delta = int(section.get('delta', 10))
    Config.Counting.static_ratio = float(section.get('static_ratio', 0.7))
    Config.Counting.storage += _get_storage_paths(inifile, section, 'storage')
    
    # return value is string. bool of non empty string ('0' aswell) results in True
    # therefore we need to cast to int first
    Config.Counting.use_internet = bool(int(section.get('internet_for_counting', '0')))
    Config.Counting.internet_url = section.get('url', None)
    

def _parse_xbee_settings(inifile):
    section = inifile["ZIGBEE"]
    Config.XBee.use_xbee = bool(int(section.get('use_zigbee', '0')))
    if not Config.XBee.use_xbee:
        return
    
    Config.XBee.pan = int(section.get('pan', '99'))
    
    Config.XBee.port = section.get('port', '/dev/ttyUSB0')
    Config.XBee.baud_rate = int(section.get('baud_rate', 9600))
    Config.XBee.is_coordinator = bool(int(section.get('is_coordinator', '0')))
    Config.XBee.my_label = section.get('my_label', ' ')

    nodes = section.get('internet_nodes')
    Config.XBee.internet_ids = [_.strip() for _ in nodes.split(',')]


def _parse_beacon_settings(inifile):
    logger.debug("parsing beacon config")
    section = inifile['BEACON']
    Config.Beacon.target_id = section.get('target_id', '')
    Config.Beacon.scans = int(section.get('scans', 8))
    Config.Beacon.threshold = int(section.get('threshold', 3))
    Config.Beacon.storage += _get_storage_paths(inifile, section,'storage')

    Config.Beacon.shutdown_id = section.get('shutdown_on_target', None)
    if Config.Beacon.shutdown_id:
        Config.Beacon.shutdown_on_scan = True

def _parse_user_settings(inifile):
    logger.debug("parsing user config")
    section = inifile['USER']

    Config.serial_number = int(section.get('devID', 0))
    Config.led = bool(int(section.get('led', '1')))
    Config.scantime = int(section.get('scantime', 1))

    location = section.get('location', '0').split(",")
    Config.use_location = len(location) == 2
    if Config.use_location:
        Config.latitude = float(location[0].strip())
        Config.longitude = float(location[1].strip())


def parse_ini(path='config.ini'):
    """
    Parse the given ini-file and set corresponding values.
    See sample ini-file for reference of possible values.
    """
    logger.info(f"Parsing ini file {path}")
    inifile = configparser.ConfigParser()
    inifile.read(path)

    Config.inifile = inifile

    _parse_user_settings(inifile)
    _parse_counting_settings(inifile)
    _parse_xbee_settings(inifile)
    _parse_beacon_settings(inifile)
    _parse_transit_settings(inifile)

    Config.check_integrity()





    
