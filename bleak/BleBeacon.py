from typing import Dict, List, Union
from device import Device
from storage import Storage
from numpy import mean
from datetime import datetime


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
        self.staying_time = {}
        self.current_scan = 0
        self.matches = []
        self.storages = storage
        self.macs = {} 

    
    def accumulate(self) -> Dict[Device, int]:
        """
        Accumulate all scanned devices and get a list of devices and amount of scans they appeared
        """
        acc = {}
        for devs in self.devices.values():
            for dev in devs:
                mac = dev.get_mac()
                if mac not in acc.keys():
                    acc[mac] = 1
                else:
                    acc[mac] += 1
        return acc


    def detect_matches(self, accumulation: Dict[Device, int]):
        """ detect devices that are detected more often or equal to the threshold amount"""
        self.matches = [dev for dev, count in accumulation.items() if count >= self.threshold]

    def update_staying_time(self):
        for mac in self.matches:
            device = self.macs[mac]
            if mac not in self.staying_time.keys():
                self.staying_time[mac] = [device.get_rssi()]
            else:
                self.staying_time[mac].append(device.get_rssi())

    def update(self, scanned_devices):
        """update the list of devices. Will add devices to the current timestep and then increase the timestep by one"""
        self.devices[self.current_scan] = scanned_devices
        self.current_scan = (self.current_scan + 1) % self.scans
        for device in scanned_devices:
            self.macs[device.get_mac()] = device
        #self.print(self.devices)



    def filter_devices(self, devices: List[Device]) -> List[Device]:
        """ filter devices for given service_uuid"""
        return [dev for dev in devices if self.service_uuid in dev.get_service_uuids()]

    def process_scan(self, devices: List[Device]):
        """process a single 1s scan interval"""

        filtered = self.filter_devices(devices)

        self.update(filtered)
        acc = self.accumulate()

        self.print(acc)

        self.detect_matches(acc)

        self.print(self.matches)
        self.update_staying_time()

        self.print(self.staying_time)

        exited = [mac for mac in self.staying_time.keys() if mac not in self.matches]

        if len(exited) > 0:
            self.store_devices(exited)

    def __str__(self) -> str:
        return self.name

    def print(self, text: str):
        print(f"BleBeacon {self}: {text}")

    def prepare_for_storing_beacon(self, timestep, mac):
        """
        Beacon headers: (Time,Tag Name,Staying time, Average RSSI)
        """
        average_rssi = mean(self.staying_time[mac])
        time = len(self.staying_time[mac])

        # TODO get tagname from device
        tagname = ''

        return [timestep, tagname, time, average_rssi]

    def store_devices(self, macs):
        """store results into all given storage instances"""
        self.print("storing beacons")
        self.print(f"beacons to store: {len(self.matches)}")

        # format for storing:
        now = datetime.now()
        time = now.replace(second=(now.second // 10)*10)
        timestr = time.strftime("%H:%M:%S")

        data_rows = []

        for mac in macs:
            data_rows.append(self.prepare_for_storing_beacon(timestr, mac))
            del self.staying_time[mac]

        for storage in self.storages:
            for row in data_rows:
                self.print(f"saving row {row}")
                storage.save_beacon(row)

        