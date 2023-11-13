from typing import Dict, List, Union
from device import Device
from storage import Storage
from numpy import mean
from datetime import datetime

import logging

logger = logging.getLogger(f'blescan.Beacon')

class BleBeacon:
    """
    Class that analyses the beacons.

    The BleBeacon works by only storing informations about near bluetooth beacons with a specific uuid.
    In every 1s scan interval beacons are detected.
    For every completed round of scans, a threshold determines wether a beacon is considered close or not.
    For example we do 8 1s scans. If a beacon is detected more than 4 times, it is considered present in this area.
    """

    def __init__(self, beacon_id: str = '', scans: int = 8, threshold: int = 5, storage:Union[Storage, List[Storage]] = []):
        """
        Construct an instance of the Beacon Analysis.

        Keyword arguments:
        beacon_id -- the uuid to filter devices for. All devices with a different uuid in manufacturer_data will be ignored.

        scans -- the amount of scans to keep track of.

        threshold -- if a device is in more or equal scans detected, it is considered present. 

        storage -- storage -- a single or a list of storage instances to save the data to. 
                    Multiple storage instances could be used for saving to USB and to SDcard as backup.
                    This class uses the save_beacon function to save the data.
        """
        if type(storage) is not list: storage = [storage]
        self.scanned_devices = {}
        self.beacon_id = beacon_id
        self.threshold = threshold
        self.scans = scans
        self.devices = {_: [] for _ in range(scans)}
        self.staying_time = {}
        self.current_scan = 0
        self.matches = []
        self.storages = storage
        self.macs = {} 
        self.beacons = {}

    
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



    def filter_devices(self, devices: List[Device]) -> List[Device]:
        """ filter devices for the beacon id"""
        is_beacon = lambda dev: self.beacon_id == dev.get_beacon_uuid()
        beacons = [dev for dev in devices if is_beacon(dev)]
        return beacons

    def process_scan(self, devices: List[Device]):
        """process a single 1s scan interval"""

        filtered = self.filter_devices(devices)

        self.update(filtered)
        acc = self.accumulate()

        logger.debug(acc)

        self.detect_matches(acc)

        logger.debug(self.matches)
        self.update_staying_time()

        logger.debug(self.staying_time)

        exited = [mac for mac in self.staying_time.keys() if mac not in self.matches]

        if len(exited) > 0:
            self.store_devices(exited)

    def __str__(self) -> str:
        return self.name

    def store_devices(self, macs):
        """store results into all given storage instances"""
        logger.debug("storing beacon data")
        logger.info(f"beacons to store: {len(self.matches)}")

        # format for storing:
        now = datetime.now()
        time = now.replace(second=(now.second // 10)*10)
        timestr = time.strftime("%H:%M:%S")

        data_rows = []

        for storage in self.storages:

            for mac in macs:
                manufacturer_data = self.macs[mac].get_manufacturer_data()
                storage.save_from_beacon(timestr, self.staying_time[mac], manufacturer_data)
                del self.staying_time[mac]


        