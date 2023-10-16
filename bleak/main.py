import bleak
import asyncio

from scanning import Scanner
from BleCount import BleCount
from BleBeacon import BleBeacon

from led import LEDCommunicator

async def main():
    scanner = Scanner()

    #counter = BleCount(name="counter 1")
    #counter2 = BleCount(name="delta 5")

    beacon = BleBeacon(service_uuid = '9b12a001-68f0-e742-228a-cba37cbb671f')

    comm = LEDCommunicator()
    comm.start_in_thread()

    try:
        while True:
            devices = await scanner.scan()

            #counter.process_scan(devices)
            #counter2.process_scan(devices)
            beacon.process_scan(devices)
    except KeyboardInterrupt as e:
        print("stopping application")
    finally:
        comm.stop()


if __name__ == "__main__":
    asyncio.run(main())