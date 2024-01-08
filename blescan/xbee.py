import asyncio
from config import Config

from typing import Dict, List, Union
from queue import Queue
from threading import Thread

from storage import prepare_row_data_summary
import util
from datetime import datetime
import time
import logging
import traceback

import serial.tools.list_ports


from digi.xbee.devices import XBeeDevice
from digi.xbee.models.address import XBee16BitAddress
from digi.xbee.models.message import XBeeMessage
from digi.xbee.exception import TransmitException,XBeeException,TimeoutException

logger = logging.getLogger('blescan.XBee')


class XBee:

    def __init__(self, port):
        self.device = XBeeDevice(port, Config.Zigbee.baud_rate)
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
        self.callbacks.append(callback)

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
            logger.error(f"Error sending to node {node_identifier}")
            return False
        except TimeoutException:
            logger.error(f"Timeout during connection. Try again in 5s")
            time.sleep(5)
            return False
        



def get_configuration(pan_id=1, is_coordinator=False, label=' '):
    params = {'ID': pan_id.to_bytes(8, 'little'), 'CE': (1 if is_coordinator else 0).to_bytes(1, 'little'), 'NI': bytearray(label, "utf8")}

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

    return {"id": int(s[0]), "timestamp": s[1],"date": s[2], "time": s[3], "close": int(s[4]), "count": int(s[5]), 
            'rssi_avg':float(s[6]),'rssi_std':float(s[7]),'rssi_min':int(s[8]),'rssi_max':int(s[9]), 'latitude': util.float_or_None(s[10]), 'longitude': util.float_or_None(s[11])}



class XBeeCommunication:

    def __init__(self, sender: XBee=None):
        self.sender = sender
        self.queue = Queue()
        self.running = False
        self.targets = Queue()
        self._max_size = 100

    def __del__(self):
        self.stop()

    def set_sender(self, sender: XBee):
        self.sender = sender

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
        if self.queue.unfinished_tasks >= self._max_size:
            self.queue.get()
            self.queue.task_done()
        self.queue.put(data)

    def start_sending_thread(self):
        if self.running:
            raise RuntimeError("Sending thread already started")
        if self.targets.qsize == 0:
            raise ValueError("No targets specified")
        if self.sender is None:
            raise ValueError("No sender device specified")
        
        self.running = True
        self.thread = Thread(target=self._blocking_sending_loop)
        self.thread.daemon = True
        self.thread.start()

    def _send_data(self, data: str):
        target = self.targets.queue[0]
        first = target

        while not self.sender.send_to_device(target, data):
            logger.debug(f"cannot reach target {target}")
            target = self.targets.get()
            self.targets.put(target)
            target = self.targets.queue[0]

            if target == first:
                logger.warn(f"no target nodes reachable. Try again in 2s")
                time.sleep(2)

        

    def _blocking_sending_loop(self):
        while self.running:
            try: 
                if self.queue.unfinished_tasks > 0:
                    data = self.queue.get()

                    self._send_data(data)

                    logger.debug(f"Data sent to node {self.targets.queue[0]}")
                    self.queue.task_done()
                else:
                    time.sleep(2)

                if self.queue.unfinished_tasks >= 10:
                    logger.warn(f"zigbee queue is not getting done. Size: {self.queue.unfinished_tasks}")
            except Exception as e:
                logger.error(f"uncaught exception")
                logger.error(traceback.format_exc())
                time.sleep(5)
        logger.info("zigbee thread finished")

    def stop(self):
        if self.running == False:
            return

        logger.info("--- Shutting down Zigbee thread ---")
        self.queue.join()
        self.running = False
        self.thread.join()
        self.sender.device.close()
        logger.info("done")
    

class ZigbeeStorage:

    def __init__(self, com):
        self.com = com

    
    async def save_from_count(self, id: int, timestamp: datetime, rssi_list: List, close_threshold: int):

        summary = prepare_row_data_summary(id, timestamp, rssi_list, close_threshold)
        # %Y%m%d,%H%M%S
        date = datetime.now().strftime("%Y%m%d")

        time_format = util.format_datetime_network(timestamp)
        old_format = util.format_datetime_old(timestamp)

        params = {'id':id, 'timestamp': time_format, 'date':date,'time':old_format, 'close':summary[2],'count':summary[3],
                                    'rssi_avg':summary[4],'rssi_std':summary[5],'rssi_min':summary[6],'rssi_max':summary[7], 
                                    'latitude': Config.latitude, 'longitude': Config.longitude}

        self.com.encode_and_send(params)


def auto_find_port():
    ports = serial.tools.list_ports.comports()

    possibles = []

    for port in ports:
        if port.manufacturer == "FTDI" and port.product == "FT231X USB UART":
            possibles.append(port.device)

    if len(possibles) == 0:
        logger.warn("No port automatically detected. Return default /dev/ttyUSB0")
        return "/dev/ttyUSB0"
    if len(possibles) > 1:
        logger.warn(f"zigbee port is ambigeous. [{','.join(possibles)}]")
    return possibles[0]