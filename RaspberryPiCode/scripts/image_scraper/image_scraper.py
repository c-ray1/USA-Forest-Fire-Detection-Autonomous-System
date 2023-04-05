#!/usr/bin/env python3
############################################################################ File: image_scraper.py
# Date: 03/13/2023
# Description: Main script used to monitor a directory for JPEG files, 
#              subscribe to zeromq "GeoTags" Topic,  and use this info
#              to geo-tag the JPEG files.
# Version: 1.0 - Baseline
# Version: 1.1 - Removed boolean parameter from set_gps_loc (03/18/2023)
###########################################################################
import time
import sys
import signal
import os
import getopt
import json
import uuid
import shutil
import time
import logging
import logging.handlers
from watchdog.events import FileSystemEventHandler
from threading import Thread
from datetime import datetime
from watcher import Watcher
from geo_utils import *
from geo_tag_sub import GeoTagSub

LOG_FILENAME = '/opt/firedrone/logs/image_scraper.log'

#Set up a specific logger with a desired output level
img_logger = logging.getLogger('image_scraper')
img_logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes = 200000, backupCount = 5)
img_logger.addHandler(handler)

formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

class SignalHandler:
    KEEP_PROCESSING = True
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.KEEP_PROCESSING = False

# Global variable for monitoring Ctrl+C
signal_handler = SignalHandler()

class GeoTagFileHandler(FileSystemEventHandler):
    def __init__(self, path='/tmp', zq_url="tcp://localhost:5555"):
        self._output_dir = path
        self._geo_tag_sub = GeoTagSub(url=zq_url)
        self._geo_tag_sub.create_thread()
        
        super().__init__()

    def on_any_event(self, event):
        print(f'Event = {event.event_type}')
        if event.event_type == "moved":
            if event.dest_path.lower().endswith(('.jpg','.jpeg')):
                if os.path.getsize(event.dest_path) != 0:
                    unique_name = uuid.uuid4().hex
                    dst_img = unique_name + ".jpg"
                    img_path = self._output_dir  + "/inprocessing/" + \
                                dst_img
                   # print(f'Generating image file: {img_path}')
                    img_logger.info(f'Generating image file: {img_path}')
                    shutil.copy2(event.dest_path,img_path)
                    geo_data = self._geo_tag_sub.get_data()

                    set_gps_loc(img_path,
                            geo_data['lat'],
                            geo_data['lon'],
                            geo_data['alt'],
                            geo_data['time'])

                    tel_path = self._output_dir + "/telemetry/" + \
                                unique_name
                    #print(f'Generating telemetry file {tel_path}')
                    img_logger.info(f'Generating telemetry file: {tel_path}')
                    with open(tel_path, 'w') as fp:
                        fp.write(json.dumps(geo_data))
    def close(self):
        self._geo_tag_sub.close()


def usage():
    print('Usage: image_scraper [<option>...]\n')
    print('\t-w <directory>\tDirectory to watch for JPEG files [--watch]')
    print('\t-o <directory>\tDirectory to write geotagged files [--output]')
    print('\t-h\t\tPrint the help menu')

def create_output_dirs(path: str) -> str:
    if not os.path.exists(path):
       # print(f'Warning: Path {path} does not exist')
       img_logger.info(f'Warning: Path {path} does not exist')
       # print('Attempting to create!')
       img_logger.info('Attemping to create!')

    os.makedirs(path +'/inprocessing', exist_ok=True)
    os.makedirs(path +'/telemetry', exist_ok=True)

    return path

def get_params():
    """Param function for geo-tagging newly detected files."""
    watch_dir = "."
    output_dir= "/tmp/"
    msq_url = "tcp://localhost:5555"

    try:
        opts, args = getopt.getopt(
                            sys.argv[1:], 
                            "w:h:o:q:", 
                            ["watch", "help", "output", "queue"])

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
        elif o in ("-o", "--output"):
            output_dir = a
        elif o in ("-q","--queue"):
            msq_url = a
        else:
            usage()
            assert False, "unhandled option"

    return {"watch": watch_dir,
            "output": output_dir,
            "zmq" : msq_url}


if __name__=="__main__":
    try:
        config = get_params()

        geo_tag_handler = GeoTagFileHandler(
                            create_output_dirs(
                                config["output"]),
                            config["zmq"])

        w = Watcher(config["watch"], geo_tag_handler, signal_handler)
        watcher_thread = Thread(target=w.run)
        watcher_thread.start()

        watcher_thread.join()
        geo_tag_handler.close()
        
    except Exception as  e:
       # print(e)
       img_logger.debug(e)
       # print(f'Shutting Down!')
       img_logger.info(f'Shutting Down!')

