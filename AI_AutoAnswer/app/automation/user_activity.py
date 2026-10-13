import threading


class MouseActivityGuard:
    def __init__(self, get_position, interval: float = 0.025):
        self.get_position = get_position
        self.interval = interval
        self.moved = False
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        initial = self.get_position()

        def observe():
            while not self._stop.wait(self.interval):
                if self.get_position() != initial:
                    self.moved = True
                    return

        self._thread = threading.Thread(target=observe, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join(timeout=1)
