import bleak
import asyncio

from bleak.backends.bluezdbus.scanner import BleakScannerBlueZDBus

MAC1 = "EC:96:18:3A:8E:D4"

async def main():


    target_data = '1233aacc0dc140a78085303a6d64ddb5'
    service_uuid = '9b12a001-68f0-e742-228a-cba37cbb671f'

    sc = bleak.BleakScanner()

    while True:
        devices = await sc.discover(1, return_adv=True)

    #print(devices)

        b = [dev for dev in devices.values() if 'Beacon' in dev[0].name]

        print(b)



if __name__ == "__main__":
    asyncio.run(main())