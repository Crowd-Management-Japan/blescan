import bleak
import asyncio


class Scanner:

    def __init__(self, duration=1):
        self.duration = duration
        self.scanner = bleak.BleakScanner()
        self.observer = []

    async def start(self):
        self.loop = True
        await self.scanLoop()
        

    async def stop(self):
        self.loop = False

    def subscribe(self, fun):
        self.observer.append(fun)


    async def scanLoop(self):
        print("Starting scanning process")
        while self.loop:
            devices = await self.scanner.discover(self.duration, return_adv=True)

            for ob in self.observer:
                ob(devices)       

        print("Stopping scanning process")     


