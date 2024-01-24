import asyncio

import logging
# setup logging
logging.basicConfig(level=logging.ERROR, 
                    format=('%(name)s %(levelname)s %(filename)s: %(lineno)d:\t%(message)s'))
logging.getLogger('blescan').setLevel(logging.DEBUG)
logger = logging.getLogger('blescan')



from scanning import Scanner
from BleCount import BleCount
import BleBeacon
from storage import Storage
from led import LEDCommunicator
from datetime import datetime

import sys
from config import Config, parse_ini

from network import InternetCommunicator, Upstream

from xbee import XBeeCommunication, XBee, get_configuration, decode_data, ZigbeeStorage, auto_find_port

comm = LEDCommunicator()
internet = InternetCommunicator(Config.Counting.internet_url)
xbee = XBeeCommunication()

RUNNING = True

PROGRAM_EXIT_CODE = 0

CODE_SHUTDOWN_DEVICE = 100

async def main(config_path: str='./config.ini'):
    parse_ini(config_path)
    #comm.start_in_thread()

    if Config.Counting.use_internet:
        setup_internet()

    if Config.Zigbee.use_zigbee:
        setup_zigbee()

    # setting up beacon functionality
    beacon_storage = Config.Beacon.storage
    beacon_target = Config.Beacon.target_id
    beacon_scans = Config.Beacon.scans
    beacon_threshold = Config.Beacon.threshold
    beacon = BleBeacon.BleBeacon(beacon_target,beacon_scans, beacon_threshold, beacon_storage)

    # setting up counting functionality
    counting_storage = Config.Counting.storage
    threshold = Config.Counting.rssi_threshold
    close_threshold = Config.Counting.rssi_close_threshold
    delta = Config.Counting.delta
    counter = BleCount(threshold, close_threshold, delta, counting_storage)

    scanner = Scanner()

    logger.info("--- Startup complete. Begin scanning ---")

    global RUNNING
    while RUNNING:
        devices = await scanner.scan()

        before = datetime.now()
        await counter.process_scan(devices)

        beacon.process_scan(devices)
        after = datetime.now()
        logger.debug(f"processing took {after - before}")

        if beacon.stop_call:
            exit_and_shutdown()

    logger.debug("======= while exited")


def shutdown_blescan():
    logger.info("--- stopping daemons ---")
    comm.stop()
    xbee.stop()
    internet.stop()

def setup_internet():
    logger.debug("Setting up internet")
    global internet
    internet = InternetCommunicator(Config.Counting.internet_url)

    up = Upstream(internet)
    Config.Counting.storage.append(up)

    internet.start_thread()

def receive_zigbee_message(sender, text):
    logger.debug(f"received message from zigbee {sender}")
    decoded = decode_data(text)
    internet.enqueue_send_message(decoded)


def setup_zigbee():
    logger.info("Setting up zigbee")

    if Config.Zigbee.port == "auto":
        Config.Zigbee.port = auto_find_port()

    device = XBee(Config.Zigbee.port)

    conf = get_configuration(1, Config.Zigbee.is_coordinator, Config.Zigbee.my_label)

    device.configure(conf)

    logger.info(f"Zigbee: port {Config.Zigbee.port} - configuration: {conf}")

    xbee.set_sender(device)
    xbee.add_targets(Config.Zigbee.internet_ids)

    if Config.Zigbee.my_label in Config.Zigbee.internet_ids:
        logger.info("Setting up zigbee as receiver")
        device.add_receive_callback(receive_zigbee_message)
    else:
        logger.info("Setting up zigbee as sender")
        stor = ZigbeeStorage(xbee)
        Config.Counting.storage.append(stor)
        xbee.start_sending_thread()


def exit_and_shutdown():
    global RUNNING
    global PROGRAM_EXIT_CODE
    RUNNING = False
    PROGRAM_EXIT_CODE = CODE_SHUTDOWN_DEVICE
    logger.info("--- preparing exit with system shutdown ---")


if __name__ == "__main__":

    config_path = './config.ini'

    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    try:
        asyncio.run(main(config_path))
    except KeyboardInterrupt:
        pass

    logger.info("--- shutting down blescan ---")
    shutdown_blescan()
    
    sys.exit(PROGRAM_EXIT_CODE)
