import threading
from time import sleep
from enum import IntEnum
import logging

logger = logging.getLogger('blescan.LED')

class LED:
    """
    Setting up the LED. 
    @param led_code refers to the path specified in the raspberry where the trigger and brightness file can be found. e.g. 'led0' for the green led.
    """
    def __init__(self, led_code):
        self.trigger = f"/sys/class/leds/{led_code}/trigger"
        self.brightness = f"/sys/class/leds/{led_code}/brightness"
        try:
            with open(self.trigger, 'w') as file:
                file.write("none")
        except FileNotFoundError:
            logger.error("Cannot find LEDs. Disabling LED functionality")
            self.on = lambda: None
            self.off = lambda: None
        except PermissionError:
            logger.error("Missing permission for controlling LEDs. Disabling LED functionality")
            self.on = lambda: None
            self.off = lambda: None
            

    def on(self):
        with open(self.brightness, 'w') as file:
            file.write("1")
    
    def off(self):
        with open(self.brightness, 'w') as file:
            file.write("0")

def LED_ERROR(green: LED, red: LED):
    green.off()
    red.on()

def LED_SETUP(green: LED, red: LED):
    green.off()
    red.on()
    sleep(.25)
    green.on()
    red.off()
    sleep(.25)

def LED_RUNNING(green: LED, red: LED):
    red.off()
    green.on()
    sleep(.25)
    green.off()
    sleep(.25)
    green.on()
    sleep(.25)
    green.off()
    sleep(1)

def LED_GREEN_FAST(green: LED, red: LED):
    green.on()
    sleep(.25)
    green.off()
    sleep(.25)

def LED_GREEN_SLOW(green: LED, red: LED):
    green.on()
    sleep(.75)
    green.off()
    sleep(.75)


class LEDState(IntEnum):
    INTERNET_STACKING = 1
    ZIGBEE_STACKING = 2
    SETUP = 4


def get_led_function(state) -> lambda g,r:None :

    enabled = [s for s,v in state.items() if v]
    sum = 0
    for state in enabled:
        sum += state

    logger.debug(f"choosing led function for value {sum}")

    if sum == 0:
        return LED_RUNNING
    if sum == 1:
        return LED_GREEN_FAST
    if sum == 2:
        return LED_GREEN_SLOW
    if sum == 3: 
        return LED_ERROR
    if sum == 4: 
        return LED_SETUP
    
    return LED_ERROR

class LEDCommunicator:
    """
    This Class functions as a communicator towards the outside world. 
    It starts a daemon thread that uses both LEDs on the raspberry to send information
    """

    def __init__(self):
        self.running = False
        self.code = LED_SETUP
        self._states = {
            value: False for value in LEDState
        }
        self._states[LEDState.SETUP] = True
        self._state_changed = True
        self.setup()

    def setup(self):
        self.green = LED('led0')
        self.red = LED('led1')


    def blink_blocking(self):
        function = self.code
        while self.running:
            if self._state_changed:
                function = get_led_function(self._states)
                self._state_changed = False

            function(self.green, self.red)
        logger.info("thread finishing")

    def start_in_thread(self):
        logger.info("--- starting LED thread ---")
        if self.running:
            logger.error("blinking thread already started")
            return
        
        self.running = True

        self.thread = threading.Thread(target=self.blink_blocking, daemon=True)
        self.thread.start()
        logger.info("done")

    def enable_state(self, state):
        if self._states.get(state, False):
            return
        self._states[state] = True
        self._state_changed = True

    def disable_state(self, state):
        if not self._states.get(state, False):
            return
        self._states[state] = False
        self._state_changed = True

    def stop(self):
        logger.info("--- shutting down LED thread ---")
        if self.running == False:
            return
        self.running = False
        self.thread.join()
        logger.info("done")