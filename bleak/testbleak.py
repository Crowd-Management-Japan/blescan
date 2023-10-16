import bleak
import asyncio
import time
from time import sleep
from scanner import Scanner

class LED:

    def __init__(self):
        self.trigger = "/sys/class/leds/led0/trigger"
        self.brightness = "/sys/class/leds/led0/brightness"
        with open(self.trigger, 'w') as file:
            file.write("none")

    def on(self):
        with open(self.brightness, 'w') as file:
            file.write("1")
    
    def off(self):
        with open(self.brightness, 'w') as file:
            file.write("0")

async def blink(led):
    while True:
        led.on()
        await asyncio.sleep(.5)
        led.off()
        await asyncio.sleep(.5)

async def scan(scanner):
    await scanner.start()


def countDevices(devices):
    print(f"count: {len(devices)}")

async def terminate(time, scanner):
    await asyncio.sleep(time)
    #await scanner.stop()


async def main():
    print("Hello World")


    led = LED()

    scanner = Scanner()
    scanner.subscribe(countDevices)

    asyncio.gather(scan(scanner), terminate(10, scanner))
    #await scan(scanner)



    #task = asyncio.create_task(scan())
    #await asyncio.create_task(blink(led))

    #await task
    #await asyncio.gather(scan(), blink(led))



if __name__ == "__main__":
    asyncio.run(main())