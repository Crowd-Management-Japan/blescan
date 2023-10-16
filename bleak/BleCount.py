from typing import List
from device import Device
from datetime import datetime
from collections import namedtuple

class BleCount:
    """
    Class for analysing raw device data
    """

    def __init__(self, rssi_threshold: int = -100, name: str = ''):
        self.scanned_devices = {}
        self.name = name
        self.rssi_threshold = rssi_threshold
        self.delta = 10 #seconds
        self.last_update = datetime.now()
        

    def filter_devices(self, devices: List[Device]) -> List[Device]:
        return [dev for dev in devices if dev.get_rssi() > self.rssi_threshold]

    def process_scan(self, devices: List[Device]):

        # filter devices above treshold
        filtered = self.filter_devices(devices)

        # write to local memory
        for device in filtered:
            mac = device.get_mac()
            if mac not in self.scanned_devices.keys():
                self.scanned_devices[mac] = device
            else:
                old = self.scanned_devices[mac]
                if old.get_rssi() < device.get_rssi():
                    self.scanned_devices[mac] = device

        # check if storage should happen
        diff = datetime.now() - self.last_update
        if diff.total_seconds() > self.delta:
            self.store_devices()

    def __str__(self) -> str:
        return self.name

    def print(self, text: str):
        print(f"BleCount {self}: {text}")

    def store_devices(self):
        print(f"BleCount {self}: storing devices")
        print(f"BleCount {self}: devices found: {len(self.scanned_devices)}")
        self.scanned_devices.clear()
        self.last_update = datetime.now()