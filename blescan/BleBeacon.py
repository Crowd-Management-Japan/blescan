from typing import Dict, List, Union
from device import Device
from storage import Storage
from datetime import datetime, timedelta
import config

import logging

logger = logging.getLogger(f'blescan.Beacon')

class BleBeacon:
    """
    Class that analyses the beacons.

    The BleBeacon works by only storing informations about near bluetooth beacons with a specific uuid.
    In every (1s) scan interval beacons are detected.
    For every completed round of scans, a threshold determines whether a beacon is considered close or not.
    For example we do 8 (1s) scans. If a beacon is detected more than 4 times, it is considered present in this area.
    """

    stop_call = False

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
        self.rssi_list = {}
        self.detected_time = {}
        self.current_scan = 0
        self.matches = []
        self.storages = storage
        self.macs = {} 
        self.beacons = {}
        self.last_scan_save = datetime.min

    
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

    def update_time_rssi(self):
        for mac in self.matches:
            device = self.macs[mac]
            if mac not in self.rssi_list.keys():
                self.detected_time[mac] = datetime.now()
                self.rssi_list[mac] = [device.get_rssi()]
            else:
                self.rssi_list[mac].append(device.get_rssi())

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
        """process a single scan interval"""

        filtered = self.filter_devices(devices)

        if self.check_shutdown(filtered):
            self.stop_call = True

        self.update(filtered)
        acc = self.accumulate()

        self.detect_matches(acc)
        self.update_time_rssi()

        exited = [mac for mac in self.rssi_list.keys() if mac not in self.matches]

        if len(exited) > 0:
            self.store_devices(exited)

        if datetime.now() - self.last_scan_save >= timedelta(seconds=1):
            self.store_scan(filtered)

    def __str__(self) -> str:
        return self.name

    def check_shutdown(self, devices: List[Device]) -> bool:
        if config.Config.Beacon.shutdown_id == None or (not config.Config.Beacon.shutdown_on_scan):
            return False
        
        mm_string = lambda dev: f"{dev.get_major()}{dev.get_minor()}"

        mm_strings = [mm_string(dev) for dev in devices]

        return config.Config.Beacon.shutdown_id in mm_strings
    
    def store_scan(self, beacons):

        id = config.Config.serial_number

        self.last_scan_save = datetime.now().replace(microsecond=0)
        logger.debug(f"exact beacon save: {self.last_scan_save}")
        timestr = datetime.now().strftime("%H:%M:%S")

        for storage in self.storages:
            try:
                storage.save_beacon_scan(id, timestr, beacons)
            except PermissionError as e:
                logger.debug(f"No writing permission for {storage}")
            except Exception as e:
                logger.debug(f"Unkwnow writing error: {e}")

    def store_devices(self, macs):
        """store results into all given storage instances"""
        logger.debug("storing beacon data")
        logger.info(f"beacons to store: {len(self.matches)}")

        # format for storing:
        time = datetime.now()
        timestr = time.strftime("%H:%M:%S")

        id = config.Config.serial_number

        for mac in macs:
            for storage in self.storages:
                try:
                    staying_time = round((datetime.now() - self.detected_time[mac]).total_seconds())
                    manufacturer_data = self.macs[mac].get_manufacturer_data()
                    storage.save_beacon_stay(id, timestr, staying_time, self.rssi_list[mac], manufacturer_data)
                except PermissionError as e:
                    logger.debug(f"No writing permission for {storage}")
                except Exception as e:
                    logger.debug(f"Unkwnow writing error: {e}")
            del self.rssi_list[mac]
            del self.detected_time[mac]


        