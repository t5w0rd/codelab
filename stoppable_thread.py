from threading import Thread, Event


class StoppableThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._stop_event = Event()
        self._stop_event.set()

    def start(self):
        self._stop_event.clear()
        Thread.start(self)

    def stop(self):
        self._stop_event.set()

    @property
    def running(self):
        return not self._stop_event.is_set()

    def run(self):
        self.nop_loop()

    def nop_loop(self):
        while not self._stop_event.wait(timeout=3600):
            pass
