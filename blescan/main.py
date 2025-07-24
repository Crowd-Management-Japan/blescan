from datetime import datetime, timedelta
from statistics import mean
import logging
import os
import sys

# setup logging (before any imports use it)
if not os.path.exists("logs"):
    os.mkdir("logs")
    
filename = f"logs/log_{datetime.now().strftime('%m%d')}.txt"
logging.getLogger('blescan').setLevel(logging.ERROR)
logging.basicConfig(level=logging.ERROR, 
                    format=('%(name)s %(levelname)s %(filename)s: %(lineno)d:\t%(message)s'))
file_formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
fileHandler = logging.FileHandler(filename)
fileHandler.setFormatter(file_formatter)
logger = logging.getLogger('blescan')
logger.addHandler(fileHandler)

from scanning import Scanner
from BleCount import BleCount
from BleBeacon import BleBeacon
from storage import Storage
from led import LEDCommunicator, LEDState
from config import Config, parse_ini
from network import InternetStorage, InternetController
from xbee import decode_data, XBeeStorage, XBeeController

led_communicator = LEDCommunicator()
internet = InternetController(led_communicator=led_communicator)
xbee = XBeeController(led_communicator=led_communicator)


CODE_SHUTDOWN_DEVICE = 100
SCANTIME_VALUE = "./etc/scantime.txt"
SCANTIME_PARAMETERS = [15,2]
LED_CONFIG_PATH = "./etc/led.txt"

def main(config_path: str='./config.ini'):
    parse_ini(config_path)
    if Config.led:
        led_communicator.start()

    if Config.Counting.use_internet or Config.Transit.use_internet:
        setup_internet()

    if Config.XBee.use_xbee:
        setup_xbee()

    logger.debug("setup BleBeacon")

    # setting up beacon functionality
    beacon_storage = Config.Beacon.storage
    beacon_target = Config.Beacon.target_id
    beacon_scans = Config.Beacon.scans
    beacon_threshold = Config.Beacon.threshold
    beacon = BleBeacon(beacon_target,beacon_scans, beacon_threshold, beacon_storage)

    logger.debug("setup BleCount")
    # setting up counting functionality
    counting_storage = Config.Counting.storage
    threshold = Config.Counting.rssi_threshold
    close_threshold = Config.Counting.rssi_close_threshold
    delta = Config.Counting.delta
    static_ratio = Config.Counting.static_ratio
    counter = BleCount(threshold, close_threshold, static_ratio, counting_storage)

    # hardcode LED setting to be used in future startups
    with open(LED_CONFIG_PATH, 'w') as file:
        file.write(str(int(Config.led)))

    logger.debug("reconstructing old files (if any)")
    # stitch files from previous days
    storage_key = 'Storage: '
    for storage in beacon_storage:
        if storage_key in str(storage):
            storage_path = str(storage)
            Storage.reconstruct_files(storage_path.replace(storage_key,''))
    for storage in counting_storage:
        if storage_key in str(storage):
            storage_path = str(storage)
            Storage.reconstruct_files(storage_path.replace(storage_key,''))

    scantime = adjust_scantime()
    scantime_list = []
    scanner = Scanner()

    exit_code = 0
    running = True

    logger.info("--- Startup complete. Begin scanning ---")

    if Config.led:
        led_communicator.disable_state(LEDState.SETUP)

    while running:
        # scan for BLE devices 
        scanstart = datetime.now()
        devices = scanner.scan(scantime)
        scanend = datetime.now()
        totaltime = (scanend - scanstart).total_seconds()

        # adjust scanning time with minimal steps
        if totaltime > Config.scantime:
            scantime -= 0.001 * Config.scantime
        elif totaltime < Config.scantime:
            scantime += 0.001 * Config.scantime
        logger.debug(f"scantime: {totaltime}")

        # eventually store scantime to have better setting at startup
        scantime_list.append(scantime)
        if len(scantime_list)>100:
            with open(SCANTIME_VALUE, 'w') as file:
                file.write(str(mean(scantime_list)))
            scantime_list.clear()

        # process scan  
        counter.process_scan(devices, totaltime)
        beacon.process_scan(devices)

        if beacon.stop_call:
            logger.info("Shutdown beacon scanned. Shutting down blescan.")
            running = False
            exit_code = CODE_SHUTDOWN_DEVICE

    if exit_code == CODE_SHUTDOWN_DEVICE:
        logger.info("All processes stopped, shutting down device now.")

    return exit_code

def adjust_scantime():
    """search for a scan time configuration which is valid for any hardware"""
    if file_exists(SCANTIME_VALUE):
        # scanning time was already determined for this device
        with open(SCANTIME_VALUE, 'r') as file:
            scantime = float(file.read().strip())
    else:
        scantime = Config.scantime

    if abs(1 - (scantime / Config.scantime)) > 0.05:
        # need to determine scanning time to ensure real time is as close as possible to 1 s
        logger.info("--- Determining optimal scanning time configuration ---")
        scantime = Config.scantime / 2   
        step = scantime / 5
        for i in range(SCANTIME_PARAMETERS[0]):
            # peform a scan and check how long it takes
            scanstart = datetime.now()
            Scanner().scan(scantime)
            scanend = datetime.now()
            totaltime = (scanend - scanstart).total_seconds()

            # if larger than 1.0 s reduce step and retry
            if totaltime==Config.scantime:
                break
            elif totaltime < Config.scantime:
                scantime += step
            else:
                scantime -= step
                step /= SCANTIME_PARAMETERS[1]

            # save settings to ensure faster startup the next time
            with open(SCANTIME_VALUE, 'w') as file:
                file.write(str(scantime))

    return scantime

def file_exists(file_path):
    return os.path.exists(file_path)

def shutdown_blescan():
    logger.info("--- stopping daemons ---")
    internet.stop()
    xbee.stop()
    
    if Config.led:
        led_communicator.stop()

def setup_internet():
    logger.debug("Setting up internet")

    internet.set_count_url(Config.Counting.internet_url)
    internet.set_transit_url(Config.Transit.internet_url)

    up = InternetStorage(internet)
    Config.Counting.storage.append(up)

    internet.start()

def receive_xbee_message(sender, text):
    decoded = decode_data(text)
    logger.debug(f"received message from xbee {sender}, decoded: {decoded}")
    internet.enqueue_message(decoded)


def setup_xbee():
    logger.info("Setting up xbee")
    xbee.set_message_received_callback(receive_xbee_message)
    xbee.start()
    
    if xbee.is_sender:
        logger.debug("appending xbee storage")
        stor = XBeeStorage(xbee)
        Config.Counting.storage.append(stor)
    else:
        logger.debug("setting message callback")


if __name__ == "__main__":

    config_path = './config.ini'

    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    exit_code = 1

    try:
        exit_code = main(config_path)
    except KeyboardInterrupt:
        pass

    logger.info("--- shutting down blescan ---")
    shutdown_blescan()
    
    sys.exit(exit_code)
