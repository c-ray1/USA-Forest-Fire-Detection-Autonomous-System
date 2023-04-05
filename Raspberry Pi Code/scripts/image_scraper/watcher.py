############################################################################ File: watcher.py
# Date: 03/13/2023
# Description: watchdog monitor used to trigger observations.
# Version: 1.0
###########################################################################
import signal
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Watcher:

    def __init__(self, directory=".", 
            handler=FileSystemEventHandler(), 
            signal_handler=None):
        self.observer   = Observer()
        self.handler    = handler
        self.directory  = directory
        self.signal     = signal_handler

    def run(self):
        self.observer.schedule(
            self.handler, self.directory, recursive=True)
        self.observer.start()
        print(f'\nwatchdog monitoring: {self.directory}\n')

        if self.signal is not None:
            while self.signal.KEEP_PROCESSING:
                    time.sleep(1)
        else:
            while True:
                time.sleep(1)

        self.observer.stop()
        self.observer.join()

        print("\nWatcher Terminated\n")



