
from storage import prepare_row_data_summary
from datetime import datetime
from queue import Queue
from typing import List, Dict, Union
import requests
from threading import Thread
from time import sleep
import logging
import datetime
import util
import config
from led import LEDState, LEDCommunicator

import json

logger = logging.getLogger('blescan.Network')

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

INTERNET_STACKING_THRESHOLD = 3
INTERNET_QUEUE_SIZE = 1000

class InternetController:
    """
    The internet controller manages the internet connection.
    It can be started in a separated thread by calling the `start()`-method.
    After doing this, messages can be enqueue by calling `enqueue_message(message)`.
    These messages will get sent to the specified `url` endpoint.
    When also given a LEDCommunicator, this instance will give information about its current state.

    Stop the thread by calling `stop()`. This will terminate the loop safely, with trying to send all
    enqueued messages before exiting.
    """

    def __init__(self, url='', led_communicator:LEDCommunicator=None):
        self.url:str = url
        self.led_communicator: LEDCommunicator = led_communicator
        self.message_queue = Queue()
        self.thread: Thread
        self.ready: bool = False
        self.running: bool = False

    def set_url(self, url:str):
        self.url = url

    def set_led_communicator(self, communicator: LEDCommunicator):
        self.led_communicator = communicator

    def start(self):
        """
        Start a thread as a daemon. Only has effect, if the instance is not running yet.
        """
        if self.running:
            logger.error("Internet thread already running")
        self.running = True
        logger.info("--- starting Internet thread ---")

        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """
        Stop the thread and terminate safely. Try to send remaining messages before exiting
        """
        if not self.running:
            return
        logger.debug("internet thread stop call")
        self.running = False
        self.thread.join()
        logger.info("--- Internet thread shut down ---")

    def enqueue_message(self, message: str):
        """
        Enqueue a message to be sent.
        If the Queue is already full, older data will be dropped to add this message
        """
        if self.message_queue.unfinished_tasks >= INTERNET_QUEUE_SIZE:
            logger.warn("internet queue full. Dropping old data")
            self.message_queue.get()
            self.message_queue.task_done()
        self.message_queue.put(message)
        
        logger.debug(f"adding message to internet queue. size: {self.message_queue.unfinished_tasks}")

    def _run(self):
        """
        Private method that is actually executed as a thread.
        """
        message = None
        while self.running:

            self._set_state(LEDState.INTERNET_STACKING, self.message_queue.unfinished_tasks > INTERNET_STACKING_THRESHOLD)

            if message is not None:
                success = self._send_message(message)
                logger.debug(f"internet sending success: {success} ")
                if success:
                    self._set_state(LEDState.NO_INTERNET_CONNECTION, False)
                    self.message_queue.task_done()
                    message = None
                else:
                    self._set_state(LEDState.NO_INTERNET_CONNECTION, True)
                    sleep(2)

            elif self.message_queue.unfinished_tasks > 0:
                logger.debug(f"retrieving next internet message")
                message = self.message_queue.get()
        # end while
            

        logger.debug("internet thread stopping safely. Send remaining messages")
        while self.message_queue.unfinished_tasks > 0:
            logger.debug(f"internet remaining: {self.message_queue.unfinished_tasks}")
            message = self.message_queue.get()
            self._send_message(message, timeout=0.5)
            self.message_queue.task_done()

        logger.debug("internet thread finished")
            

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

    async def save_count(self, id: int, timestamp: datetime.datetime, rssi_list: List, close_threshold: int):


        time_format = util.format_datetime_network(timestamp)
        old_format = util.format_datetime_old(timestamp)

        # return value is "DeviceID,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI"
        summary = prepare_row_data_summary(id, time_format, rssi_list, close_threshold)

        # {'device_id': '45', 'date': '20231020', 'time': '104000', 'count': '26', 'total': '26', 'rssi_avg': '-93.615', 'rssi_std': '3.329', 'rssi_min': '-99', 'rssi_max': '-85'}
        
        # %Y%m%d,%H%M%S
        date = datetime.datetime.now().strftime("%Y%m%d")

        

        params = {'id':id,'timestamp': time_format,'date':date,'time':old_format.replace(':', ''),'close':summary[2],'count':summary[3],
                                    'rssi_avg':summary[4],'rssi_std':summary[5],'rssi_min':summary[6],'rssi_max':summary[7],
                                    'latitude': config.Config.latitude, 'longitude': config.Config.longitude}

        self.com.enqueue_message(params)
