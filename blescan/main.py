import asyncio

from scanning import Scanner
from BleCount import BleCount
from BleBeacon import BleBeacon
from storage import Storage
from led import LEDCommunicator
from datetime import datetime

import sys
from config import Config, parse_ini

from network import InternetCommunicator, Upstream

from xbee import XBeeCommunication, XBee, get_configuration, decode_data, ZigbeeStorage

comm = LEDCommunicator()
internet = InternetCommunicator(Config.Counting.internet_url)
xbee = XBeeCommunication()


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
    beacon = BleBeacon(beacon_target,beacon_scans, beacon_threshold, beacon_storage, name='beacon')

    # setting up counting functionality
    counting_storage = Config.Counting.storage
    threshold = Config.Counting.rssi_threshold
    close_threshold = Config.Counting.rssi_close_threshold
    delta = Config.Counting.delta
    counter = BleCount(threshold, close_threshold, delta, counting_storage, name='counting')


    scanner = Scanner()
    try:
        while True:
            devices = await scanner.scan()

            before = datetime.now()
            await counter.process_scan(devices)

            #beacon.process_scan(devices)
            after = datetime.now()
            #print(f"processing took {after - before}")
    except KeyboardInterrupt as e:
        print("stopping application")
    finally:
        comm.stop()
        xbee.stop()
        internet.stop()


def setup_internet():
    print("Setting up internet")
    global internet
    internet = InternetCommunicator(Config.Counting.internet_url)

    up = Upstream(internet)
    Config.Counting.storage.append(up)

    internet.start_thread()

def print_zigbee_message(sender, text):
    print(f"received message from zigbee {sender}")
    decoded = decode_data(text)
    internet.enqueue_send_message(decoded)


def setup_zigbee():
    print("Setting up zigbee")
    device = XBee(Config.Zigbee.port)

    conf = get_configuration(1, Config.Zigbee.coordinator, Config.Zigbee.my_label)

    device.configure(conf)

    print(f"Zigbee: port {Config.Zigbee.port} - configuration: {conf}")

    xbee.set_sender(device)
    xbee.add_targets(Config.Zigbee.internet_ids)

    if Config.Zigbee.my_label in Config.Zigbee.internet_ids:
        print("Setting up zigbee as receiver")
        device.add_receive_callback(print_zigbee_message)
    else:
        print("Setting up zigbee as sender")
        stor = ZigbeeStorage(xbee)
        Config.Counting.storage.append(stor)
        xbee.start_sending_thread()

if __name__ == "__main__":

    config_path = './config.ini'

    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    asyncio.run(main(config_path))