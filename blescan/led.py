from time import sleep
from enum import IntEnum
from typing import Dict
import logging
import multiprocessing as mp
import threading

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

def LED_SLEEP(led: LED):
    pass

def LED_BOTH_SLEEP(green: LED, red: LED):
    pass

def LED_HEARTBEAT(led: LED):
    led.on()
    sleep(.1)
    led.off()
    sleep(.1)
    led.on()
    sleep(.1)
    led.off()
    sleep(.7)

def LED_TRIPLE(led: LED):
    led.on()
    sleep(.1)
    led.off()
    sleep(.1)
    led.on()
    sleep(.1)
    led.off()
    sleep(.1)
    led.on()
    sleep(.1)
    led.off()
    sleep(.6)



def _LED_BLINKING(time: float):
    def fun(led):
        led.on()
        sleep(time)
        led.off()
        sleep(time)
    return fun
    
LED_FAST = _LED_BLINKING(.25)
LED_SLOW = _LED_BLINKING(.75)

class LEDState(IntEnum):
    SETUP = 0

    INTERNET_STACKING = 10
    NO_INTERNET_CONNECTION = 11

    XBEE_STACKING = 30
    XBEE_SETUP = 31
    XBEE_CRASH = 32
    NO_XBEE_CONNECTION = 33

def get_green_function(state: Dict[LEDState, bool]) -> lambda led: None:
    if state.get(LEDState.INTERNET_STACKING, False):
        return LED_FAST
    if state.get(LEDState.NO_INTERNET_CONNECTION, False):
        return LED_SLOW

    return LED_HEARTBEAT

def get_red_function(state: Dict[LEDState, bool]) -> lambda led: None:

    if state.get(LEDState.XBEE_SETUP, False):
        return LED_HEARTBEAT
    if state.get(LEDState.XBEE_CRASH, False):
        return LED_TRIPLE

    if state.get(LEDState.XBEE_STACKING, False):
        return LED_FAST
    if state.get(LEDState.NO_XBEE_CONNECTION, False):
        return LED_SLOW
    


    return LED_SLEEP

def get_combined_function(state):
    if state[LEDState.SETUP]:
        return LED_SETUP
    return None

class LEDCommunicator:
    """
    This Class functions as a communicator towards the outside world. 
    It starts a daemon thread that uses both LEDs on the raspberry to send information
    """

    def __init__(self):
        self.running = False
        self.code = LED_SETUP
        self._states = mp.Manager().dict()
        self._states.update({
            value: False for value in LEDState
        })
        self._states[LEDState.SETUP] = True
        self._state_changed = True
        self.setup()

        self.green_function = LED_SLEEP
        self.red_function = LED_SLEEP



    def setup(self):
        self.green = LED('led0')
        self.red = LED('led1')


    def _blocking_single(self, led, blink_function):
        while self.running:
            blink_function(led)
            sleep(0.5)

    def _start_thread(self):
        threading.Thread(target=lambda: self._blocking_single(self.green, lambda l: self.green_function(l)), daemon=True).start()
        threading.Thread(target=lambda: self._blocking_single(self.red, lambda l: self.red_function(l)), daemon=True).start()

        both_function = None

        while self.running:
            if self._state_changed:
                both_function = get_combined_function(self._states)
                if both_function is not None:
                    self.green_function = LED_SLEEP
                    self.red_function = LED_SLEEP
                else:
                    self.green_function = get_green_function(self._states)
                    self.red_function = get_red_function(self._states)

            if both_function is not None:
                both_function(self.green, self.red)
            sleep(.25)


    def start(self):
        logger.info("--- starting LED thread ---")
        if self.running:
            logger.error("LED thread already started")
            return
        
        self.running = True

        self.thread = mp.Process(target=self._start_thread, daemon=True)
        self.thread.start()

    def enable_state(self, state):
        self.set_state(state, True)

    def disable_state(self, state):
        self.set_state(state, False)

    def set_state(self, state, value):
        if self._states.get(state, False) == value:
            self._states[state] = value
            return
        
        logger.debug(f"changing led state {state} to {value}")
        
        self._states[state] = value
        self._state_changed = True

    def stop(self):
        logger.info("--- shutting down LED thread ---")
        if self.running == False:
            return
        self.running = False
        self.thread.join()