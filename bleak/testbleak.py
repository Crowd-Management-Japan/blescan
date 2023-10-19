import bleak
import asyncio

import aiohttp

from bleak.backends.bluezdbus.scanner import BleakScannerBlueZDBus

MAC1 = "EC:96:18:3A:8E:D4"

URL = "http://www.claudiofeliciani.online/ble_system/get_count.php"

async def main():


    target_data = '1233aacc0dc140a78085303a6d64ddb5'
    service_uuid = '9b12a001-68f0-e742-228a-cba37cbb671f'


    timeout = aiohttp.ClientTimeout(1)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(URL) as res:
            print(res.status)



if __name__ == "__main__":
    asyncio.run(main())