import bluepy
import device
from typing import List

class Scanner:
    """encapsulates the ble scanning logic"""

    def __init__(self):
        self.bluepy_scanner = bluepy.btle.Scanner(0)

    def scan(self, duration=1) -> List[device.Device]:

        bluepy_devices = self.bluepy_scanner.scan(duration)
        return device.transform_bluepy_results(bluepy_devices)
