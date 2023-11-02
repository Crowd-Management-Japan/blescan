
from config import Config

from typing import Dict, List, Union
from queue import Queue
from threading import Thread

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
    
    def send_to_device(self, node_identifier: str, data: str) -> bool:
        net = self.device.get_network()
        remote = net.discover_device(node_identifier)
        if remote is None:
            return False
        try:
            self.device.send_data(remote, data)
            return True
        except TransmitException:
            print(f"Error sending to node {node_identifier}")
            return False
        



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
        self.queue = Queue()
        self.running = False
        self.targets = Queue()

    def __del__(self):
        self.stop()

    def add_targets(self, targets: Union[str,List[str]]):
        """Add a set of nodes (by their node identifier (xbee NI value)) that are connected to the internet and can thus be used for internet communication.
        Data will be sent to one of these.
        """
        if type(targets) is not list: targets = [targets]
        for target in targets:
            self.targets.put(target)

    def encode_and_send(self, data: Dict):
        self.send_data(encode_data(data))

    def send_data(self, data: str):
        self.queue.put(data)

    def start_sending_thread(self):
        if self.running:
            raise RuntimeError("Sending thread already started")
        if self.targets.qsize == 0:
            raise ValueError("No targets specified")
        
        self.running = True
        self.thread = Thread(target=self._blocking_sending_loop)
        self.thread.daemon = True
        self.thread.start()

    def _send_data(self, data: str):
        target = self.targets.queue[0]
        first = target

        while not self.sender.send_to_device(target, data):
            target = self.targets.get()
            self.targets.put(target)
            target = self.targets.queue[0]

            if target == first:
                print(f"no target nodes reachable")

        

    def _blocking_sending_loop(self):
        while self.running:
            if self.queue.unfinished_tasks > 0:
                data = self.queue.get()

                self._send_data(data)

                self.queue.task_done()

    def stop(self):
        self.running = False
        self.thread.join()
        del self.sender()
    