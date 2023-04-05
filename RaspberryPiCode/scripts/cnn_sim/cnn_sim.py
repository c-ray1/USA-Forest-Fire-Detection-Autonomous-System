#!/usr/bin/env python3
###############################################################################
# File: cnn_sim.py
# Date: 03/14/2023
# Description: CNN simulator used to simulate the triggering of fire detection.
# Version: 1.0
###############################################################################
import os
import sys
import getopt
import random
import base64
import json
import time
import zmq
from threading import Thread
from signal_handler import SignalHandler
from watcher import Watcher
from watchdog.events import FileSystemEventHandler
from queue import Queue
from queue import Empty

# Global variable for monitoring Ctrl+C
signal_handler = SignalHandler()

class Alert:
    def __init__(self, filename, accuracy):
        self._filename = filename
        self._accuracy = accuracy

    def get_msg(self):
        return { "filename": self._filename,
                 "accuracy": self._accuracy }

#class Detection:
#    def __init__(self, time, lat, lon, alt, yaw, pitch, roll, speed):
#        self._time=time
#        self._lat = lat
#        self._lon = lon
#        self._alt = alt
#        self._yaw = yaw
#        self._pitch = pitch
#        self._roll = roll
#        self._speed = speed
#        self._blob = None
#        self._accuracy = 0.0

#    def load_img_file(self, img_file):
##
#        with open(img_file, 'rb') as fp:
#            img_data = fp.read()
#
#        self.blob = base64.b64encode(img_data)
#
#    def set_accuracy(self, accuracy):
#        self._accuracy = accuracy
#
#    def get_msg(self):
#        return {
#                "time" : self._time,
#                "lat" : self._lat,
#                "lon" : self._lon,
#                "alt" : self._alt,
#                "yaw" : self._yaw,
#                "pitch" : self._pitch,
#                "roll" : self._roll,
#                "speed" : self._speed,
#                "blob" : self._blob,
#                "accuracy" : self._accuracy
#                }

class FileHandler(FileSystemEventHandler):
    def __init__(self, queue, prob_rate=50.0):
        self._queue = queue
        self._prob_rate=prob_rate

    def on_any_event(self, event):
        if event.event_type == "created":
            path = event.src_path
            if path.lower().endswith(('.jpg','.jpeg')):
                if os.path.getsize(path) != 0:
                    probability = random.uniform(0, 100)

                    if probability > self._prob_rate:
                        self._queue.put(Alert(path, random.uniform(50,100)))

def publish_alert(queue, url="tcp://127.0.0.1:5556"):

    context  = zmq.Context()
    pub_sock = context.socket(zmq.PUB)
    pub_sock.bind(url)
    
    while signal_handler.KEEP_PROCESSING:
        try:
            alert = queue.get(block=True, timeout=1)
            if alert is not None:
                pub_sock.send_string('Alert',flags=zmq.SNDMORE)
                pub_sock.send_json(json.dumps(alert.get_msg()))
                print(f'{json.dumps(alert.get_msg())}')
        except Empty:
            time.sleep(0.5)


def usage():
    print('Usage: cnn_sim [<option>...]\n')
    print('\t-w <directory>\tDirectory to watch for geotagged JPEG files [--watch]')
    print('\t-u <URL>\tZeroMQ URL for posting detections [--url] (default: tcp://localhost:5555)')
    print('\t-p <probability>\tProbability limit for detections [--prob] (default: 50)')
    print('\t-h\t\tPrint the help menu')


def get_params():
    """Param function for detecting geotagged files. """
    watch_dir = "."
    url_addr = "tcp://127.0.0.1:5556"
    prob = 50

    try:
        opts, args = getopt.getopt(
                            sys.argv[1:],
                            "w:h:u:p:",
                            ["watch", "help", "url", "prob"])

    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-w", "--watch"):
            watch_dir = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-u", "--url"):
            url_addr = o
        elif o in ("-p", "--prob"):
            prob = float(a)
        else:
            usage()
            assert False, "unhandled option"

    return {"watch" : watch_dir, "url" : url_addr, "prob": prob}


if __name__=="__main__":
    try:
        config = get_params()
        pub_q = Queue()
        
        watch_dir = config["watch"]
        url       = config["url"]
        prob_rate = config["prob"]

        if not os.path.exists(watch_dir):
            print(f'Warning: {watch_dir} does not exit!')
            sys.exit(1)


        w = Watcher(watch_dir, FileHandler(pub_q, prob_rate), signal_handler)
        watcher_thread = Thread(target=w.run)
        watcher_thread.start()

        pub_thread = Thread(target=publish_alert, args=(pub_q, url, ))
        pub_thread.start()

        watcher_thread.join()
        pub_thread.join()


    except KeyboardInterrupt:
        print(f'Shutting Down!')

