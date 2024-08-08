
class Device():
    """
    Wrapper for bluepy library
    """
    def __init__(self, bluepy_device):
        self.bluepy_device = bluepy_device
        self.scan_data = bluepy_device.getScanData()

        self.uuid = ""
        self.raw_manufacturer = ""
        self.major = ""
        self.minor = ""
        self.tx = ""
        self.rssi = None

        for (adTypeCode, description, valueText) in self.scan_data:
            if description == "Manufacturer":
                self.raw_manufacturer = valueText
                self.uuid = valueText[-42:-10] # target_id
                self.major = valueText[-10:-6]
                self.minor = valueText[-6:-2]


    def get_mac(self):
        return self.bluepy_device.addr

    def get_rssi(self):
        return self.bluepy_device.rssi

    def get_service_uuids(self):
        return ""

    def get_major(self):
        return self.major

    def get_minor(self):
        return self.minor


    def get_tx_power(self):
        return self.tx

    def get_manufacturer_data(self):
        return {'major': self.get_major(), 'minor': self.get_minor(), 'tx': self.get_tx_power()}

    def get_beacon_uuid(self):
        return self.uuid


def transform_bluepy_results(bluepy_devices):
    return [Device(d) for d in bluepy_devices]
