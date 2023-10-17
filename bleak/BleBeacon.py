from typing import Dict, List, Union
from device import Device
from storage import Storage

class BleBeacon:
    """
    Class that analyses the beacons.

    The BleBeacon works by only storing informations about near bluetooth beacons with a specific uuid.
    In every 1s scan interval beacons are detected.
    For every completed round of scans, a threshold determines wether a beacon is considered close or not.
    For example we do 8 1s scans. If a beacon is detected more than 4 times, it is considered present in this area.
    """

    def __init__(self, service_uuid: str, scans: int = 8, threshold: int = 5, storage:Union[Storage, List[Storage]] = [], name: str = ''):
        """
        Construct an instance of the Beacon Analysis.

        Keyword arguments:
        service_uuid -- the uuid to filter devices for. All devices with a different service_uuid will be ignored.

        scans -- the amount of scans to keep track of.

        threshold -- if a device is in more or equal scans detected, it is considered present. 

        storage -- storage -- a single or a list of storage instances to save the data to. 
                    Multiple storage instances could be used for saving to USB and to SDcard as backup.
                    This class uses the save_beacon function to save the data.

        name -- a name used for printing messages to the console
        """
        if type(storage) is not list: storage = [storage]
        self.scanned_devices = {}
        self.service_uuid = service_uuid
        self.threshold = threshold
        self.name = name
        self.scans = scans
        self.devices = {_: [] for _ in range(scans)}
        self.current_scan = 0
        self.matches = []
        self.storage = storage

    
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
        """ detect devices that are detected more often or equal to the threshold amount"""
        self.matches = [dev for dev, count in accumulation.items() if count >= self.threshold]

    def update(self, scanned_devices):
        """update the list of devices. Will add devices to the current timestep and then increase the timestep by one"""
        self.devices[self.current_scan] = scanned_devices
        self.current_scan = (self.current_scan + 1) % self.scans
        #self.print(self.devices)



    def filter_devices(self, devices: List[Device]) -> List[Device]:
        """ filter devices for given service_uuid"""
        return [dev for dev in devices if self.service_uuid in dev.get_service_uuids()]

    def process_scan(self, devices: List[Device]):
        """process a single 1s scan interval"""

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
        """store results into all given storage instances"""
        self.print("storing beacons")
        self.print(f"beacons found: {len(self.matches)}")