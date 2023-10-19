import bleak
from bleak.backends.device import BLEDevice



# key of the manufacturer data for the beacon
MANUFACTURER_ID = 76



class Device:
    """
    Wrapper class for bleaks BLEDevice to make it easier to access the most common fields.
    It is used for both normal and the special beacon devices

    The Beacons used (BlueBeacon Tag) are produced by apple and use the manufacturer code 76 (the one of apple).
    The data is encoded like: 
    Fixed data: 2 bytes
    UUID: 16bytes
    MAJOR: 2 bytes
    MINOR: 2 bytes
    TX_POWER: 1byte (signed)
        
    """
    def __init__(self, bledevice: BLEDevice, ad_data):
        self.bledevice = bledevice
        self.ad_data = ad_data

    def get_mac(self):
        return self.bledevice.address
    
    def get_rssi(self):
        return self.ad_data.rssi

    def get_service_uuids(self):
        return self.ad_data.service_uuids

    def get_major(self):
        if MANUFACTURER_ID not in self.ad_data.manufacturer_data.keys():
            return ''
        
        data = self.ad_data.manufacturer_data[MANUFACTURER_ID]
        return ''.join(format(x, "02x") for x in data[18:20])

    def get_minor(self):
        if MANUFACTURER_ID not in self.ad_data.manufacturer_data.keys():
            return ''
        
        data = self.ad_data.manufacturer_data[MANUFACTURER_ID]
        return ''.join(format(x, "02x") for x in data[20:22])

    def get_tx_power(self):
        if MANUFACTURER_ID not in self.ad_data.manufacturer_data.keys():
            return ''
        
        data = self.ad_data.manufacturer_data[MANUFACTURER_ID]

        return int.from_bytes(data[-1:], signed=True, byteorder='big')

    def get_manufacturer_data(self):
        return {'major': self.get_major(), 'minor': self.get_minor(), 'tx': self.get_tx_power()}

    def get_beacon_uuid(self):
        if 76 in self.ad_data.manufacturer_data.keys():
            data = self.ad_data.manufacturer_data[76]
            return ''.join(format(x, "02x") for x in data[2:18])
        return ''


    def __str__(self):
        return f"Device:({self.bledevice}, {self.ad_data})"

    def __repr__(self):
        return self.__str__()


def transform_scan_results(scanned_devices):
    return [Device(d[0], d[1]) for d in scanned_devices.values()]
