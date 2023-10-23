import asyncio

from scanning import Scanner
from BleCount import BleCount
from BleBeacon import BleBeacon
from storage import Storage
from led import LEDCommunicator
from datetime import datetime

import sys
from config import Config

from network import Upstream


comm = LEDCommunicator()



async def main():


    url = Config.Storage.internet_url



    upstream = Upstream(url)


    comm.start_in_thread()

    # setting up beacon functionality
    beacon_storage = Config.Storage.beacon
    beacon_target = Config.beacon_target_id
    beacon = BleBeacon(beacon_id=beacon_target, storage=beacon_storage, name='beacon')

    # setting up counting functionality
    counting_storage = Config.Storage.counting
    threshold = Config.rssi_threshold
    close_threshold = Config.rssi_close_threshold
    counter = BleCount(threshold, close_threshold, storage=counting_storage, name='counting')


    scanner = Scanner()
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
