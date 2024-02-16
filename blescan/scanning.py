import bluepy
import device
from typing import List
from datetime import datetime

class Scanner:
    """encapsulates the ble scanning logic"""

    def __init__(self):
        self.bluepy_scanner = bluepy.btle.Scanner(0)

    def scan(self, duration=1) -> List[device.Device]:
        before = datetime.now()
        bluepy_devices = self.bluepy_scanner.scan(duration)
        after = datetime.now()
        print(f"raw scanning time: {after - before}")


        return device.transform_bluepy_results(bluepy_devices)