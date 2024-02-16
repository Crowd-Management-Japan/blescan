import asyncio
from config import Config

from typing import Dict, List, Union, Any, Set
import multiprocessing as mp

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
        logger.warn(f"xbee port is ambigeous. [{','.join(possibles)}]")
    return possibles[0]




class XBeeController:

    def __init__(self, port='auto', led_communicator=None):
        self.port: str = port
        self.device: XBeeDevice = None
        self.target_ids: List[str] = []
        self.targets: Dict = {}
        self.message_received_callback = lambda s, t: logger.debug(f"message from {t}: {s}")
        self.running: bool = False
        self.message_queue = mp.Queue()
        self.thread = None
        self.is_sender: bool = None
        self.led_communicator = led_communicator

    def __del__(self):
        if self.device is not None and self.device.is_open():
            self.device.close()

    def _setup(self):
        self._set_state(LEDState.XBEE_SETUP, True)
        port = self.port
        logger.debug(f"port: {port}")
        if port == 'auto': port = auto_find_port()
        self.target_ids = Config.XBee.internet_ids

        logger.debug(f"setting up xbee device on port {port}")
        self.device = XBeeDevice(port, Config.XBee.baud_rate)
        self.device.open()

        self.device.set_pan_id(Config.XBee.pan.to_bytes(8, 'little'))
        self.device.set_node_id(Config.XBee.my_label)
        self.device.set_parameter('CE', (1 if Config.XBee.is_coordinator else 0).to_bytes(1, 'little'))

        self.device.apply_changes()
        self.device.write_changes()

        self.device.add_data_received_callback(lambda m: self.message_received_callback(m.remote_device, m.data.decode()))

        logger.debug(f"xbee settings: [ \n\
                     PAN: {util.byte_to_hex(self.device.get_pan_id())}, \n\
                     CE: {util.byte_to_hex(self.device.get_parameter('CE'))},\n\
                     NI: {self.device.get_node_id()}]")


        logger.debug(f"device using protocol {self.device.get_protocol()}")
        logger.debug(f"device setup completed")
        self._set_state(LEDState.XBEE_SETUP, False)

    def _teardown(self):
        if self.device is not None and self.device.is_open():
            self.device.close()

    def start(self):
        if self.running:
            logger.error("Already running a XBee instance")
            return
        self.running = True
        logger.info("--- starting XBee thread ---")

        # determine role
        self.is_sender = Config.XBee.my_label not in self.target_ids

        self.thread = mp.Process(target=self._run, daemon=True)
        self.thread.start()

        # wait a second for the thread to start
        time.sleep(1)

    def stop(self):
        if not self.running:
            return
        logger.debug("xbee stop call")
        self.running = False
        self.thread.join()

    def _run(self):
        while self.running:
            try:
                self._setup()
                
                if self.is_sender:
                    logger.info("Running XBee as Sender")
                    self._run_sender()
                else:
                    logger.info("Running XBee as Receiver")
                    self._run_receiver()

                logger.debug("tearing down xbee")
            except Exception as e:
                self._set_state(LEDState.XBEE_CRASH, True)
                logger.error("XBee thread crashed with exception - trying to restart in 5s")
                
                logger.error(e)
                logger.debug("end of error message")
                time.sleep(10)
                logger.debug("restarting xbee thread")
                self._set_state(LEDState.XBEE_CRASH, False)
            finally:
                self._teardown()
        logger.info("--- xbee thread finished ---")

    def _run_receiver(self):
        while self.running:
            # if there are some issues with xbee, the discovery will throw an exception which causes the thread to restart
            logger.debug("xbee receive checkup")
            self._discover_network(5)
            logger.debug(f"devices discovered: [{','.join(id for id in self.targets.keys())}]")
            time.sleep(10)


    def _run_sender(self):
        available_targets = []

        message = None

        while self.running:
            if len(available_targets) == 0:
                self._set_state(LEDState.NO_XBEE_CONNECTION, True)
                logger.debug("No reachable targets. Rescanning")
                available_targets = self._discover_network()
                logger.debug(f"available internet nodes: {available_targets}")
                continue
            else:
                self._set_state(LEDState.NO_XBEE_CONNECTION, False)

            self._set_state(LEDState.XBEE_STACKING, self.message_queue.qsize() > XBEE_STACKING_THRESHOLD)

            # if there is a message, send it to an available target.
            # if the target happens to not be available (_send_message return false),
            # remove this target from the available list
            if message is not None:

                target = available_targets[0]
                success = self._send_message(target, message)

                if success:
                    message = None
                else:
                    available_targets.remove(target)

            elif self.message_queue.qsize() > 0:
                message = self.message_queue.get()

        # end while
        
        logger.debug("stopping xbee. Clearing queue")
        if len(available_targets) > 0:
            # first still selected message. Otherwhise the task is never marked done and the thread stucks
            if message:
                self._send_message(message, timeout=0.5)

            while self.message_queue.qsize() > 0:
                target = available_targets[0]
                message = self.message_queue.get()
                self._send_message(target, message)

        logger.debug("xbee thread finished")



    def set_message_received_callback(self, callback: lambda sender, text: None):
        self.message_received_callback = callback
        
    def enqueue_message(self, message: str):
        if self.message_queue.qsize() >= XBEE_QUEUE_SIZE:
            logger.warn("xbee queue full. Dropping old data")
            self.message_queue.get()
        self.message_queue.put(message)
        
        logger.debug(f"adding message to xbee queue. size: {self.message_queue.qsize()}")

    def _discover_network(self, timeout=10) -> List[str]:
        """
        Make a discovery in the xbee network with the given timeout.
        Every discovered node is written to the self.targets dict.

        @return a list of the intersection between all discovered devices and set targets.
            This directly displays a list of available targets found.
        """
        logger.debug("starting xbee network discovery")
        xnet = self.device.get_network()

        xnet.set_discovery_timeout(timeout)
        xnet.start_discovery_process(True, 1)

        while xnet.is_discovery_running():
            if not self.running:
                xnet.stop_discovery_process()
            time.sleep(.5)

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
    
    def _set_state(self, state: LEDState, value: bool):
        if self.led_communicator is None:
            return
        
        self.led_communicator.set_state(state, value)
    

class XBeeStorage:

    def __init__(self, com):
        self.com = com

    
    async def save_count(self, id: int, timestamp: datetime, rssi_list: List, close_threshold: int):

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
