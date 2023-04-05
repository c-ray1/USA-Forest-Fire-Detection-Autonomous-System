#!/usr/bin/env python3
###############################################################################
# File: signal_handler.py
# Date: 03/14/2023
# Description: Signal handler object used to catch signal interrupts.
# Version: 1.0
# Version: 1.1 Rethrow the KeyboardInterrupt to termainte blocking system calls
###############################################################################
import signal
import time

class SignalHandler:
    KEEP_PROCESSING = True
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.KEEP_PROCESSING = False
        print("exit_gracefully")
        time.sleep(0.5)
        raise KeyboardInterrupt

