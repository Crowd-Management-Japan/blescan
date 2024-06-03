import logging
from datetime import datetime, timedelta
import os

# setup logging (before any imports use it)

if not os.path.exists("logs"):
    os.mkdir("logs")
    
filename = f"logs/log_{str(datetime.now().day).zfill(2)}.txt"
logging.getLogger('blescan').setLevel(logging.DEBUG)
file_formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
fileHandler = logging.FileHandler(filename)
fileHandler.setFormatter(file_formatter)

logging.basicConfig(level=logging.ERROR, 
                    format=('%(name)s %(levelname)s %(filename)s: %(lineno)d:\t%(message)s'))
logging.getLogger('blescan').setLevel(logging.DEBUG)
logger = logging.getLogger('blescan')
logger.addHandler(fileHandler)



from scanning import Scanner
from BleCount import BleCount
from BleBeacon import BleBeacon
from storage import Storage
from led import LEDCommunicator, LEDState
import util

import sys
from config import Config, parse_ini

from network import InternetStorage, InternetController

from xbee import decode_data, XBeeStorage, XBeeController

import time

led_communicator = LEDCommunicator()
internet = InternetController(led_communicator=led_communicator)
xbee = XBeeController(led_communicator=led_communicator)


CODE_SHUTDOWN_DEVICE = 100

def main(config_path: str='./config.ini'):
    parse_ini(config_path)
    led_communicator.start()

    if Config.Counting.use_internet:
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
    counter = BleCount(threshold, close_threshold, delta, counting_storage)

    scanner = Scanner()


    exit_code = 0
    running = True

    logger.info("--- Startup complete. Begin scanning ---")

    led_communicator.disable_state(LEDState.SETUP)

    while running:
        before = datetime.now()
        devices = scanner.scan(.97)

        scanend = datetime.now()

        scantime = scanend - before

        if scantime - timedelta(seconds=1) > timedelta(seconds=0.05):
            logger.warning(f"scanning time is more than 5% from target (1s) {scantime}")

        logger.debug(f"scantime: {scantime}")


        counter.process_scan(devices)
        beacon.process_scan(devices)
        after = datetime.now()
        #logger.debug(f"processing took {after - before}")

        if beacon.stop_call:
            logger.info("Shutdown beacon scanned. Shutting down blescan.")
            running = False
            exit_code = CODE_SHUTDOWN_DEVICE

    return exit_code


def shutdown_blescan():
    logger.info("--- stopping daemons ---")
    internet.stop()
    xbee.stop()
    
    led_communicator.stop()

def setup_internet():
    logger.debug("Setting up internet")

    internet.set_url(Config.Counting.internet_url)

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
