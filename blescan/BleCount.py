from typing import List, Any, Union
from device import Device
from datetime import datetime, timedelta
from collections import namedtuple, Counter
from storage import Storage
from network import InternetStorage
import math
from config import Config
import logging
import requests
import json

logger = logging.getLogger('blescan.Counting')

class BleCount:
    """
    Class for analysing raw device data.
    Accumulates all devices from each scan until it is called to write the data. Then the list gets cleared.

    This is done, because in the original program, the scan duration was 8s, but this whole program lives with a 1s interval.
    Therefore we need to accumulate devices over several 1s scans, to somehow mimic a longer scan.
    When saving, this accumulation is cleared to mimic the next longer scan.
    """

    def __init__(self, rssi_threshold: int = -100, rssi_close_threshold = -75, static_ratio: float = 0.7, storage: Union[Storage,List[Storage]] = []):
        """
        Create an instance to keep track of the total amount of devices.

        Keyword arguments:
        rssi_threshold -- completely ignores devices below this threshold

        rssi_close_threshold -- devices with a greater rssi_value are considered close.
                    Used for the summary statistic

        storage -- a single or a list of storage instances to save the data to.
                    Multiple storage instances could be used for saving to USB and to SDcard as backup.
                    This class uses the save_rssi and save_summary functions to save data.
        """
        if type(storage) is not list: storage = [storage]
        self.storages = storage
        self.prev_remainder = {
            "count": 0,
            "transit": 0
        }
        self.last_update = datetime.now()
        self.scanned_devices = {}
        self.rssi_threshold = rssi_threshold
        self.rssi_close_threshold = rssi_close_threshold
        self.static_ratio = static_ratio
        self.scan_info = {
            "scans": 0,
            "total_time": 0
        }
        self.static_list = []
        self.transit_list = []
        self.instantaneous_counts = {
            "all": [],
            "close": []
        }

    # filter devices that are below the mininium RSSI defined for detection threshold
    def filter_devices(self, devices: List[Device]) -> List[Device]:
        """filter out devices below the minimum rssi threshold"""
        return [dev for dev in devices if dev.get_rssi() > self.rssi_threshold]

    # filter devices above the specified RSSI threshold for "close"
    def filter_close(self, devices: List[Device]) -> List[Device]:
        """filter out devices below the close rssi threshold"""
        return [dev for dev in devices if dev.get_rssi() > self.rssi_close_threshold]

    def process_scan(self, devices: List[Device], scantime: float):
        """process one scan interval: accumulates devices."""
        self.scan_info["scans"] += 1
        self.scan_info["total_time"] += scantime

        filtered = self.filter_devices(devices)
        close = self.filter_close(filtered)
        self.instantaneous_counts["all"].append(len(filtered))
        self.instantaneous_counts["close"].append(len(close))

        # assumes multiple detections in a single scan
        for device in filtered:
            mac = device.get_mac()
            self.static_list.append(mac)

            if mac not in self.scanned_devices.keys():
                self.scanned_devices[mac] = device
            else:
                old = self.scanned_devices[mac]
                if old.get_rssi() < device.get_rssi():
                    self.scanned_devices[mac] = device

        # check if storage or should happen
        now = datetime.now()
        midnight = datetime.combine(now.date(), datetime.min.time())
        seconds = (now - midnight).seconds

        if seconds % Config.Counting.delta < self.prev_remainder['count']:
            reference_time = midnight + timedelta(seconds=(seconds // Config.Counting.delta) * Config.Counting.delta)
            self.store_devices(reference_time)
        self.prev_remainder['count'] = seconds % Config.Counting.delta

        # prepare list for transit time detection
        if Config.Transit.enabled:
            for device in close:
                code = self.encript_mac_to_code(device.get_mac())
                self.transit_list.append(code)

            if seconds % Config.Transit.delta < self.prev_remainder['transit']:
                reference_time = midnight + timedelta(seconds=(seconds // Config.Transit.delta) * Config.Transit.delta)
                self.transit_list = list(set(self.transit_list))
                logger.debug(f"transit data for {reference_time} ready to be sent to the backend")
                ##ESPARK: include here the function sending the data for the transit time to the backend
                #         information to be sent are: device id (Config.serial_number), time (reference_time), and id list (self.transit_list)
                self.store_transit(reference_time)
        self.prev_remainder['transit'] = seconds % Config.Transit.delta

    def __str__(self) -> str:
        return self.name

    def encript_mac_to_code(self, mac_address: str) -> int:
        string, mac_address = '', mac_address.replace(":", "")
        for i in range(len(mac_address)):
            num = ord(mac_address[i])
            code = num
            if 48 <= num <= 57:
                code = num - 48
            elif 97 <= num <= 109:
                code = num - 87
            string = string + str(code)
        return int(string)

    def get_rssi_list(self) -> List[int]:
        return [dev.get_rssi() for dev in self.scanned_devices.values()]

    def store_devices(self, time: datetime):
        """
        Call all registered storage instances to save RSSI and summary statistics.
        """
        logger.debug("storing devices")
        logger.info(f"devices found: {len(self.scanned_devices)}")
        logger.debug(f"exact saving time: {datetime.now()}, exact delta: {datetime.now() - self.last_update}")

        id = Config.serial_number

        # Count the number of occurrences of MAC addresses
        mac_counter = Counter(self.static_list)

        # Filtering only MAC addresses whose number of occurrences exceeds a threshold
        static_thresh = self.scan_info["scans"] * self.static_ratio
        filtered_macs = [mac for mac, count in mac_counter.items() if count >= static_thresh]

        # Get a list of devices based on filtered MAC addresses
        static_list = [dev for dev in self.scanned_devices.values() if dev.get_mac() in filtered_macs]

        for storage in self.storages:
            try:
                total_scans = self.scan_info["scans"]
                scantime = round(self.scan_info["total_time"],3)
                storage.save_count(id, time, total_scans, scantime, self.get_rssi_list(), self.instantaneous_counts, static_list)
            except PermissionError as e:
                logger.error(f"No writing permission for {storage}")
            except Exception as e:
                logger.error(f"Unkwnow writing error: {e}")

        self.scanned_devices.clear()
        self.static_list.clear()
        self.instantaneous_counts["all"].clear()
        self.instantaneous_counts["close"].clear()
        self.scan_info["scans"] = 0
        self.scan_info["total_time"] = 0

        self.last_update = time

    def store_transit(self, time: datetime):
        logger.debug("storing data for transit")

        id = Config.serial_number
        timestamp = time.isoformat()
        mac_list = self.transit_list

        for storage in self.storages:
            if isinstance(storage, InternetStorage):
                storage.save_transit(id, timestamp, mac_list)

        self.transit_list.clear()