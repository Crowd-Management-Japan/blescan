import asyncio
from config import Config

from typing import Dict, List, Union, Any, Set
from queue import Queue
from threading import Thread

from storage import prepare_row_data_summary
import util
from datetime import datetime
import time
import logging
import traceback

import serial.tools.list_ports

from led import LEDState


from digi.xbee.devices import XBeeDevice
from digi.xbee.models.address import XBee16BitAddress
from digi.xbee.models.message import XBeeMessage
from digi.xbee.exception import TransmitException,XBeeException,TimeoutException

logger = logging.getLogger('blescan.XBee')

XBEE_STACKING_THRESHOLD = 3
XBEE_QUEUE_SIZE = 1000

class XBee:

    def __init__(self, port):
        self.device = XBeeDevice(port, Config.Zigbee.baud_rate)
        self.device.open()
        self.device.add_data_received_callback(self._message_received)
        self.callbacks = []
        self.targets = []
        self.remotes = {}

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
    
    def set_target_nodes(self, targets: Union[str, List[str]]) -> None:
        """
        Specify a list of target devices by their NI
        """
        if type(targets) is not list: targets = [targets]
        self.targets = targets

    
    def discover_targets(self) -> None:
        """
        Discover nodes in this networks and save them for connecting later
        """

        logger.debug("discovering remotes...")

        xnet = self.device.get_network()

        xnet.start_discovery_process()
        while xnet.is_discovery_running():
            time.sleep(0.5)

        logger.debug(f"discovered remotes: [{','.join(map(str, discovered))}]")

        pass
    
    def send_to_device(self, node_identifier: str, data: str) -> bool:

        if node_identifier not in self.targets:
            self.set_target_nodes(self.targets.append(node_identifier))
            self.discover_targets()

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
        
    def close(self):
        self.device.close()


def get_configuration(pan_id=1, is_coordinator=False, label=' ') -> Dict:
    params = {'ID': pan_id.to_bytes(8, 'little'), 'CE': (1 if is_coordinator else 0).to_bytes(1, 'little'), 'NI': bytearray(label, "utf8")}

    return params
    
def encode_data(data: Dict) -> str:
    """encode a dict for sending data to the homepage.
    "DeviceID,Date,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI"
    ignore keys, to reduce bytes that need to be transferred
    """
    return ",".join([str(v) for v in data.values()])

def decode_data(data: str) -> Dict[str, Any]:
    """decode data that was encoded with the function above
    """

    s = data.split(",")

    return {"id": int(s[0]), "timestamp": s[1],"date": s[2], "time": s[3], "close": int(s[4]), "count": int(s[5]), 
            'rssi_avg':float(s[6]),'rssi_std':float(s[7]),'rssi_min':int(s[8]),'rssi_max':int(s[9]), 
            'latitude': util.float_or_else(s[10], None), 
            'longitude': util.float_or_else(s[11], None)}



class XBeeCommunication:

    def __init__(self, sender: XBee=None, led_communicator = None):
        self.sender = sender
        self.queue = Queue()
        self.running = False
        self.targets = Queue()
        self._max_size = XBEE_QUEUE_SIZE
        self.led_communicator = led_communicator

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

    def start_in_thread(self):
        if self.running:
            raise RuntimeError("Sending thread already started")
        if self.targets.qsize == 0:
            raise ValueError("No targets specified")
        if self.sender is None:
            raise ValueError("No sender device specified")

        logger.info("--- starting Xbee thread ---")
        
        self.running = True
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()

    def _send_data(self, data: str) -> bool:
        target = self.targets.queue[0]
        first = target

        success = False

        while self.running:
            logger.debug(f"unfinished zigbee tasks: {self.queue.unfinished_tasks}")
            self.set_led_state(LEDState.ZIGBEE_STACKING, self.queue.unfinished_tasks > XBEE_STACKING_THRESHOLD)
            success = self.sender.send_to_device(target, data)
            if success:
                self.set_led_state(LEDState.NO_ZIGBEE_CONNECTION, False)
                return success
            logger.debug(f"cannot reach target {target}")
            self.set_led_state(LEDState.NO_ZIGBEE_CONNECTION, True)
            target = self.targets.get()
            self.targets.put(target)
            target = self.targets.queue[0]

            if target == first:
                logger.warn(f"no target nodes reachable. Try again in 2s")
                time.sleep(2)
            else:
                time.sleep(0.5)
        return False

    def _blocking_sending_loop(self):
        while self.running:
            try: 
                if self.queue.unfinished_tasks > 0:
                    data = self.queue.get()

                    self._send_data(data)

                    logger.debug(f"Data sent to node {self.targets.queue[0]}")
                    self.queue.task_done()

                time.sleep(1)

                if self.queue.unfinished_tasks >= 10:
                    logger.warn(f"zigbee queue is not getting done. Size: {self.queue.unfinished_tasks}")
            except Exception as e:
                logger.error(f"uncaught exception")
                logger.error(traceback.format_exc(e))
                time.sleep(5)
        logger.info("zigbee thread finished")

    def stop(self):
        logger.info("--- Shutting down Zigbee thread ---")
        if self.running == False:
            return

        self.running = False
        logger.debug("queue joined")
        self.thread.join()
        logger.debug("thread joined")
        self.sender.device.close()
        logger.info("--- Zigbee thread shut down ---")

    def set_led_state(self, state: LEDState, value: bool):
        if not self.led_communicator:
            return
        
        logger.debug("setting zigbee comm value")

        if value:
            self.led_communicator.enable_state(state)
        else:
            self.led_communicator.disable_state(state)
    

class XBeeController:

    def __init__(self, port='auto'):
        if port == 'auto': port = auto_find_port()
        self.port: str = port
        self.device: XBeeDevice
        self.target_ids: List[str] = []
        self.targets: Dict = {}
        self.message_received_callback = lambda s, t: logger.debug(f"message from {t}: {s}")
        self.running: bool = False
        self.message_queue = Queue()
        self.thread = None
        self.ready = False
        self.is_sender: bool = None

    def __del__(self):
        if self.device is not None and self.device.is_open():
            self.device.close()

    def _setup(self):

        self.target_ids = Config.Zigbee.internet_ids

        logger.debug(f"setting up xbee device on port {self.port}")
        self.device = XBeeDevice(self.port, Config.Zigbee.baud_rate)
        self.device.open()

        self.device.set_pan_id(Config.Zigbee.pan.to_bytes(8, 'little'))
        self.device.set_node_id(Config.Zigbee.my_label)
        self.device.set_parameter('CE', (1 if Config.Zigbee.is_coordinator else 0).to_bytes(1, 'little'))

        self.device.apply_changes()
        self.device.write_changes()

        self.device.add_data_received_callback(lambda m: self.message_received_callback(m.remote_device, m.data.decode()))

        logger.debug(f"xbee settings: [ \n\
                     PAN: {util.byte_to_hex(self.device.get_pan_id())}, \n\
                     CE: {util.byte_to_hex(self.device.get_parameter('CE'))},\n\
                     NI: {self.device.get_node_id()}]")
        logger.debug(f"device using protocol {self.device.get_protocol()}")
        logger.debug(f"device setup completed")

    def _teardown(self):
        if self.device is not None and self.device.is_open():
            self.device.close()

    def start(self):
        if self.running:
            logger.error("Already running a XBee instance")
            return
        self.running = True
        logger.info("--- starting XBee thread ---")

        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

        while self.is_sender is None:
            pass
        time.sleep(1)

    def stop(self):
        self.running = False
        self.thread.join()

    def _run(self):
        self._setup()
        
        if Config.Zigbee.my_label in self.target_ids:
            logger.info("Running XBee as Receiver")
            self._run_receiver()
        else:
            logger.info("Running XBee as Sender")
            self._run_sender()

        logger.debug("tearing down xbee")
        self._teardown()
        logger.info("--- xbee thread finished ---")

    def _run_receiver(self):
        self.is_sender = False
        self.ready = True
        # receiver does nothing, because receiving messages in mananged by the callback
        while self.running:
            time.sleep(5)


    def _run_sender(self):
        self.is_sender = True
        self.ready = True
        available_targets = []

        message = None

        while self.running:
            if len(available_targets) == 0:
                logger.debug("No reachable targets. Rescanning")
                available_targets = self._discover_network()
                logger.debug(f"available internet nodes: {available_targets}")
                continue

            # if there is a message, send it to an available target.
            # if the target happens to not be available (_send_message return false),
            # remove this target from the available list
            if message is not None:

                target = available_targets[0]
                success = self._send_message(target, message)

                if success:
                    self.message_queue.task_done
                    message = None
                else:
                    available_targets.remove(target)

            elif self.message_queue.unfinished_tasks > 0:
                message = self.message_queue.get()
        
        # end while




    def set_message_received_callback(self, callback: lambda sender, text: None):
        self.message_received_callback = callback
        
    def enqueue_message(self, message: str):
        logger.debug("adding message to queue")
        if self.message_queue.unfinished_tasks >= XBEE_QUEUE_SIZE:
            logger.warn("xbee queue full. Dropping old data")
            self.message_queue.get()
            self.message_queue.task_done
        self.message_queue.put(message)

    def _discover_network(self) -> List[str]:
        logger.debug("starting xbee network discovery")
        xnet = self.device.get_network()

        xnet.set_discovery_timeout(20)
        xnet.start_discovery_process(True, 1)

        while xnet.is_discovery_running():
            logger.debug("discovery running")
            time.sleep(1)

        nodes = xnet.get_devices()
        logger.debug(f"found nodes: [{','.join(map(str, nodes))}]")

        discovered_ids = [node.get_node_id() for node in nodes]
        
        self.targets.clear()
        self.targets.update({node.get_node_id(): node for node in nodes })

        return [id for id in self.target_ids if id in discovered_ids]


    def _send_message(self, target: str, message: str) -> bool:
        remote = self.targets.get(target, None)

        if remote is None:
            logger.debug("target not in list of discovered nodes")
            return False

        try:
            self.device.send_data(remote, message)
        except TransmitException:
            logger.error(f"Transmit exception when sending to {target}")
            return False
        except TimeoutException:
            logger.error(f"TimeoutException sending to {target}")
            return False

        logger.debug(f"Message sent to {target}")
        return True
    

class ZigbeeStorage:

    def __init__(self, com):
        self.com = com

    
    async def save_from_count(self, id: int, timestamp: datetime, rssi_list: List, close_threshold: int):

        summary = prepare_row_data_summary(id, timestamp, rssi_list, close_threshold)
        # %Y%m%d,%H%M%S
        date = datetime.now().strftime("%Y%m%d")

        time_format = util.format_datetime_network(timestamp)
        old_format = util.format_datetime_old(timestamp)

        params = {'id':id, 'timestamp': time_format, 'date':date,'time':old_format.replace(':', ''), 'close':summary[2],'count':summary[3],
                                    'rssi_avg':summary[4],'rssi_std':summary[5],'rssi_min':summary[6],'rssi_max':summary[7], 
                                    'latitude': Config.latitude, 'longitude': Config.longitude}

        #self.com.encode_and_send(params)
        message = encode_data(params)
        self.com.enqueue_message(message)


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
