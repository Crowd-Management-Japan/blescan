


import bleak
import asyncio

from scanning import Scanner
from BleCount import BleCount
from BleBeacon import BleBeacon
from storage import Storage
from led import LEDCommunicator
from datetime import datetime

import sys
import config

config.BEACON_UUID = '9b12a001-68f0-e742-228a-cba37cbb671f'

# TODO read from ini file
config.SERIAL_NUMBER = 45

async def main():

    # TODO read ini file



    storage = Storage("/home/blescan/data/test")

    comm = LEDCommunicator()
    comm.start_in_thread()

    scanner = Scanner()


    #beacon = BleBeacon(service_uuid = BEACON_UUID)
    counter = BleCount(delta=10, storage=storage)


    try:
        while True:
            devices = await scanner.scan()

            before = datetime.now()
            counter.process_scan(devices)
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