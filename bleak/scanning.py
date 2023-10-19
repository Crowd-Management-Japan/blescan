import bleak
import asyncio
import device
from typing import List

class Scanner:
    """encapsulates the bleak scanning logic"""

    def __init__(self):
        self.scanner = bleak.BleakScanner()


    async def scan(self, duration=1) -> List[device.Device]:
        """
        Running the scanning process. The bleak scanner returns a dictionary with devices. It is formatted like: {MAC: data}, 
        where data is a tuple (bledevice, advertisement_data).
        The bledevice itself contains again the MAC-address and the local name of the device.
        The advertisement data is a named tuple with local_name, manufacturer_data, service_uuids, tx_power and rssi.
        """
        print("scanning")
        devices = await self.scanner.discover(duration, return_adv=True)

        return device.transform_scan_results(devices)