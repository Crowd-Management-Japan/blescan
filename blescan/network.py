
from storage import prepare_row_data_summary
from datetime import datetime
from typing import List, Dict, Union
import requests
from time import sleep
import logging
import util
from config import Config
from led import LEDState, LEDCommunicator
import multiprocessing as mp

import json

logger = logging.getLogger('blescan.Network')

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

INTERNET_STACKING_THRESHOLD = 3
INTERNET_QUEUE_SIZE = 1000

class InternetController:
    """
    The internet controller manages the internet connection.
    It can be started in a separated process by calling the `start()`-method.
    After doing this, messages can be enqueue by calling `enqueue_message(message)`.
    These messages will get sent to the specified `url` endpoint.
    When also given a LEDCommunicator, this instance will give information about its current state.

    Stop the process by calling `stop()`. This will terminate the loop safely, with trying to send all
    enqueued messages before exiting.
    """

    def __init__(self, url='', led_communicator:LEDCommunicator=None):
        self.url:str = url
        self.led_communicator: LEDCommunicator = led_communicator
        self.message_queue = mp.Queue()
        self.process: mp.Process
        self.ready: bool = False
        self.running: bool = False

    def set_url(self, url:str):
        self.url = url

    def set_led_communicator(self, communicator: LEDCommunicator):
        self.led_communicator = communicator

    def start(self):
        """
        Start a process as a daemon. Only has effect, if the instance is not running yet.
        """
        if self.running:
            logger.error("Internet process already running")
        self.running = True
        logger.info("--- starting Internet process ---")

        self.process = mp.Process(target=self._run, daemon=True)
        self.process.start()
        logger.debug("internet process started")

    def stop(self):
        """
        Stop the process and terminate safely. Try to send remaining messages before exiting
        """
        if not self.running:
            return
        logger.debug("internet process stop call")
        self.running = False
        self.process.join()
        logger.info("--- Internet process shut down ---")

    def enqueue_message(self, message: str):
        """
        Enqueue a message to be sent.
        If the Queue is already full, older data will be dropped to add this message
        """
        if self.message_queue.qsize() >= INTERNET_QUEUE_SIZE:
            logger.warn("internet queue full. Dropping old data")
            self.message_queue.get()
            self.message_queue.task_done()
        self.message_queue.put(message)
        
        logger.debug(f"adding message to internet queue. size: {self.message_queue.qsize()}")

    def _run(self):
        """
        Private method that is actually executed as a process.
        """
        message = None
        while self.running:

            if Config.led:
                self._set_state(LEDState.INTERNET_STACKING, self.message_queue.qsize() > INTERNET_STACKING_THRESHOLD)

            if message is not None:
                success = self._send_message(message)
                logger.debug(f"internet sending success: {success} ")
                if success:
                    if Config.led:
                        self._set_state(LEDState.NO_INTERNET_CONNECTION, False)
                    message = None
                else:
                    if Config.led:
                        self._set_state(LEDState.NO_INTERNET_CONNECTION, True)
                    sleep(2)

            elif self.message_queue.qsize() > 0:
                logger.debug(f"retrieving next internet message")
                message = self.message_queue.get()
        # end while


        logger.debug("internet process stopping safely. Send remaining messages")            
        # first still selected message. Otherwhise the task is never marked done and the process stucks
        if message:
            self._send_message(message, timeout=0.5)

        while self.message_queue.qsize() > 0:
            logger.debug(f"internet remaining: {self.message_queue.qsize()}")
            message = self.message_queue.get()
            self._send_message(message, timeout=0.5)

        logger.debug("internet process finished")
            

    def _send_message(self, message: Dict, timeout=5) -> bool:
        """
        Try to send a single message to the upstream.
        Return true if sending process was successfull.
        """
        logger.debug("sending internet message...")
        success = False
        try:
            response = requests.post(self.url, json=message, timeout=timeout)
            code = response.status_code
            success = (code == 200)
        except Exception as e:
            logger.error("Error while sending message to internet")
            logger.error(e)
            return False
        return success

    def _set_state(self, state: LEDState, value: bool):
        if self.led_communicator is None:
            return
        
        self.led_communicator.set_state(state, value)



class InternetStorage:
    """
    Storage adapter for internet connection.

    Implements the method `save_from_count` to be seen as storage from the count functionality.

    It brings the data in the right format and prepares it to send
    """

    def __init__(self, controller: InternetController):
        self.com = controller

    def save_count(self, id: int, timestamp: datetime, scans: int, scantime: float, rssi_list: List, instantaneous_counts: List, static_list: List):


        time_format = util.format_datetime_network(timestamp)
        old_format = util.format_datetime_old(timestamp)

        # return value is "ID,Time,Scans,Scantime,Tot.all,Tot.close,Inst.all,Inst.close,Stat.all,Stat.close,Avg RSSI,Std RSSI,Min RSSI,Max RSSI,Stat.ratio,Lat,Lon"
        summary = prepare_row_data_summary(id, time_format, scans, scantime, rssi_list, instantaneous_counts, static_list)
        # {'id': '45', 'date': '20231020', 'time': '104000', 'scans': 8, 'scantime': '9.126',
        #  'tot_all': '26', 'tot_close': '26', 'inst_all': '26', 'inst_close': '26', 'stat_all': '26', 'stat_close': '26',
        #  'rssi_avg': '-93.615', 'rssi_std': '3.329', 'rssi_min': '-99', 'rssi_max': '-85', 
        #  'rssi_thresh': -70, 'stat_ratio': '0.7', 'lat': '-3.52842', 'lon': '-15.52842'}
        
        # %Y%m%d,%H%M%S
        date = datetime.now().strftime("%Y%m%d")

        params = {'id':id,
                  'timestamp':time_format,
                  'date':date,
                  'time':old_format.replace(':', ''),
                  'scans': scans,
                  'scantime':scantime,
                  'tot_all':summary[4],
                  'tot_close':summary[5],
                  'inst_all':summary[6],
                  'inst_close':summary[7],
                  'stat_all':summary[8],
                  'stat_close':summary[9],
                  'rssi_avg':summary[10],
                  'rssi_std':summary[11],
                  'rssi_min':summary[12],
                  'rssi_max':summary[13],
                  'rssi_thresh':Config.Counting.rssi_close_threshold,
                  'static_ratio':Config.Counting.static_ratio,
                  'latitude':Config.latitude, 
                  'longitude':Config.longitude  
                  }

        self.com.enqueue_message(params)
