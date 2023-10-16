from typing import Dict, List
from device import Device

class BleBeacon:
    """
    Class that analyses the beacons
    """

    def __init__(self, service_uuid: str, threshold: int = 5, scans: int = 8, name: str = ''):
        self.scanned_devices = {}
        self.service_uuid = service_uuid
        self.threshold = threshold
        self.name = name
        self.scans = scans
        self.devices = {_: [] for _ in range(scans)}
        self.current_scan = 0
        self.matches = []

    
    def accumulate(self) -> Dict[str, int]:
        """
        Accumulate all scanned devices and get a list of devices and amount of scans they appeared
        """
        acc = {}
        for devs in self.devices.values():
            for dev in devs:
                mac = dev.get_mac()
                if mac not in acc:
                    acc[mac] = 1
                else:
                    acc[mac] += 1
        return acc


    def detect_matches(self, accumulation: Dict[Device, int]) -> List[Device]:
        self.matches = [dev for dev, count in accumulation.items() if count > self.threshold]

    def update(self, scanned_devices):
        self.devices[self.current_scan] = scanned_devices
        self.current_scan = (self.current_scan + 1) % self.scans
        #self.print(self.devices)



    def filter_devices(self, devices: List[Device]) -> List[Device]:
        return [dev for dev in devices if self.service_uuid in dev.get_service_uuids()]

    def process_scan(self, devices: List[Device]):

        #self.print(devices)

        # filter devices above treshold
        filtered = self.filter_devices(devices)

        self.update(filtered)
        acc = self.accumulate()

        self.print(acc)

        self.detect_matches(acc)

        if len(self.matches) > 0:
            self.store_devices()

    def __str__(self) -> str:
        return self.name

    def print(self, text: str):
        print(f"BleBeacon {self}: {text}")

    def store_devices(self):
        self.print("storing beacons")
        self.print(f"beacons found: {len(self.matches)}")