import time

class Recieve_wdt():
    def __init__(self, wdt_interval_second):
        self.first_recieve_flg = False
        self.recieve_time = None
        self.interval_second = wdt_interval_second

    def tap(self):
        if not self.first_recieve_flg:
            self.first_recieve_flg = True
        
        self.recieve_time = time.time()


    def check(self):
        if not self.first_recieve_flg: return

        diff = time.time() - self.recieve_time
        if diff > self.interval_second:
            message = "recieve-wdt error. The specified time has passed. (wdt interval conf:%d second)" % self.interval_second
            raise Exception(message)

if __name__ == "__main__":
    print("--recieve wdt unit test--")
    import threading
    rwdt = Recieve_wdt(60)
    def run():
        count = 0
        while True:
            time.sleep(5)
            print("tap")
            rwdt.tap()
            count += 5
            if count >= 20:
                break

    thd = threading.Thread(target=run, daemon=True)
    thd.start()
    while True:
        rwdt.check()
