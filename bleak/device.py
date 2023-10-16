import bleak
from bleak.backends.device import BLEDevice


"""
Wrapper class for bleaks BLEDevice to make it easier to access the most common fields
"""
class Device:

    def __init__(self, bledevice: BLEDevice, ad_data):
        self.bledevice = bledevice
        self.ad_data = ad_data

    def get_mac(self):
        return self.bledevice.address
    
    def get_rssi(self):
        return self.ad_data.rssi

    def get_service_uuids(self):
        return self.ad_data.service_uuids

    def __str__(self):
        return f"Device:({self.bledevice}, {self.ad_data})"

    def __repr__(self):
        return self.__str__()


def transform_scan_results(scanned_devices):
    return [Device(d[0], d[1]) for d in scanned_devices.values()]
