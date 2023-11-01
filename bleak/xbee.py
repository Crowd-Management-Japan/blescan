
from config import Config

from typing import Dict

from digi.xbee.devices import XBeeDevice,RemoteXBeeDevice
from digi.xbee.models.address import XBee16BitAddress
from digi.xbee.models.message import XBeeMessage
from digi.xbee.exception import TransmitException,XBeeException,TimeoutException

BAUD_RATE = 9600


class XBee:

    def __init__(self, port):
        self.device = XBeeDevice(port, BAUD_RATE)
        self.device.open()
        self.device.add_data_received_callback(self._message_received)
        self.callbacks = []

    def __del__(self):
        self.device.close()

    def _message_received(self, xbee_message: XBeeMessage):
        for callback in self.callbacks:
            callback(xbee_message.remote_device, xbee_message.data.decode())

    def configure(self, params:Dict[str,bytearray]):
        for k,v in params.items():
            self.device.set_parameter(k, v)

        self.device.write_changes()

        # re-open to see changes
        self.device.close()
        self.device.open()

    def add_receive_callback(self, callback: lambda device, text: None):
        self.callbacks += callback

    def get_param(self, name: str) -> bytearray:
        return self.device.get_parameter(name)
    
    def get_pan_id(self) -> int:
        pan = self.get_param("ID")
        return int.from_bytes(pan)
    
    def is_coordinator(self) -> bool:
        con = self.get_param("CE")
        return con == b'\x01'

    def get_label(self) -> str:
        return self.get_param("NI").decode()



def get_configuration(pan_id=1, is_coordinator=False, label=' '):
    params = {'ID': pan_id.to_bytes(8), 'CE': (1 if is_coordinator else 0).to_bytes(1), 'NI': bytearray(label, "utf8")}

    return params
    
def encode_data(data: Dict) -> str:
    """encode a dict for sending data to the homepage.
    "DeviceID,Date,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI"
    ignore keys, to reduce bytes that need to be transferred
    """
    return ",".join([str(v) for v in data.values()])

def decode_data(data: str) -> Dict:
    """decode data that was encoded with the function above
    """

    s = data.split(",")

    return {"device_id": int(s[0]), "date": s[1], "time": s[2], "count": int(s[3]), "total": int(s[4]), 
            'rssi_avg':int(s[5]),'rssi_std':int(s[6]),'rssi_min':int(s[7]),'rssi_max':int(s[8])}



class XBeeCommunication:

    def __init__(self, sender: XBee):
        self.sender = sender

    