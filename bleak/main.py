import asyncio

from scanning import Scanner
from BleCount import BleCount
from BleBeacon import BleBeacon
from storage import Storage
from led import LEDCommunicator
from datetime import datetime

import sys
import config

from network import Upstream

config.BEACON_UUID = '9b12a001-68f0-e742-228a-cba37cbb671f'

# TODO read from ini file
config.SERIAL_NUMBER = 45

comm = LEDCommunicator()



async def main():

    # TODO read ini file

    url = "http://www.claudiofeliciani.online/ble_system/get_count.php"


    upstream = Upstream(url)

    sdStorage = Storage("/home/blescan/data/test")
    usbStorage = Storage("/media/usb0/test")

    comm.start_in_thread()

    scanner = Scanner()


    #beacon = BleBeacon(service_uuid = config.BEACON_SERVICE_UUID, beacon_id=config.BEACON_TARGET_ID, storage=sdStorage, scans=5, threshold=3)
    counter = BleCount(delta=10, storage=[upstream, sdStorage])


    try:
        while True:
            devices = await scanner.scan()

            before = datetime.now()
            await counter.process_scan(devices)
            #counter2.process_scan(devices)
            #beacon.process_scan(devices)
            after = datetime.now()
            print(f"processing took {after - before}")
    except KeyboardInterrupt as e:
        print("stopping application")
    finally:
        comm.stop()


if __name__ == "__main__":
    asyncio.run(main())