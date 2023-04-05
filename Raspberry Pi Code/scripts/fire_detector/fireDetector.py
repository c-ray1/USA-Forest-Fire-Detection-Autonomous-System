#!/usr/bin/env python3
###############################################################################
# File: fireDetector.py
# Date: 03/18/2023
# Description: Script used to detect fire alert messages and output to GCS.
# Version: 1.0
###############################################################################

import getopt
import json
import random
import sys
import os
import base64
import time
import uuid
import socket
import zmq
import logging
import logging.handlers
from signal_handler import SignalHandler
from threading import Thread
from queue import Queue
from queue import Empty
from zmq import ContextTerminated
from json.decoder import JSONDecodeError

signal_handler = SignalHandler()

LOG_FILENAME = '/opt/firedrone/logs/fire_detector.log'

#Set up a specific logger with a desired output level

fireDetector_logger = logging.getLogger('fire_detector')
fireDetector_logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes = 200000, backupCount = 5)

fireDetector_logger.addHandler(handler)

formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

class Detection:
    def __init__(self, uuid, time, lat, lon, alt, yaw, pitch, roll, speed):
        self._uuid = str(uuid)
        self._time=time
        self._lat = lat
        self._lon = lon
        self._alt = alt
        self._yaw = yaw
        self._pitch = pitch
        self._roll = roll
        self._speed = speed
        self._image = {}
        self._accuracy = 0.0

    def load_img_file(self, img_file):

        with open(img_file, 'rb') as fp:
            img_bytes = fp.read()

        base64_encoded_data = base64.b64encode(img_bytes)

        self._image = {'b64': f'{base64_encoded_data.decode("utf-8")}',
                'ext': 'jpg'}
       

    def set_accuracy(self, accuracy):
        self._accuracy = accuracy

    def get_msg(self):
        return {"uuid" : self._uuid,
                "time" : self._time,
                "lat" : self._lat,
                "lon" : self._lon,
                "alt" : self._alt,
                "yaw" : self._yaw,
                "pitch" : self._pitch,
                "roll" : self._roll,
                "speed" : self._speed,
                "accuracy" : self._accuracy,
                "image" : self._image
                }
def create_detection(filename, accuracy):
    path, img_file = os.path.split(filename)
    tel_file = os.path.splitext(img_file)[0]
    tel_path = path.rsplit('/', 1)[0]+f'/telemetry/{tel_file}'

    while not os.path.exists(tel_path) and signal_handler.KEEP_PROCESSING:
        #print(f'Warning: {tel_path} does not exist')
        time.sleep(0.5)

    data : dict = None
    try:
        with open(tel_path) as js:
            data = json.load(js)
    except JSONDecodeError:
        #print(f'Warning: JSON Error - failed to parse {tel_file}')  
        fireDetector_logger.info(f'Warning: JSON Error - failed to parse {tel_file}')  
    except FileNotFoundError:
        #print(f'Warning: FileNotFound Error - failed to parse {tel_file}')  
        fireDetector_logger.info(f'Warning: FileNotFound Error - failed to parse {tel_file}')  


    detection = None

    if data is not None:
        detection = Detection(tel_file, data['time'], data['lat'],
                data['lon'], data['alt'], data['yaw'], data['pitch'],
                data['roll'], data['speed'])

        detection.load_img_file(filename)
        detection.set_accuracy(accuracy)

    return detection

def process_queue(context, url="tcp://127.0.0.1:5556", queue=None):
    socket = context.socket(zmq.SUB)
    socket.connect(url)
    socket.subscribe('Alert')
    try:
        while signal_handler.KEEP_PROCESSING:
            topic, msg = socket.recv_multipart()
            data = {}
            if queue is not None:
                data = json.loads(json.loads(msg.decode('utf-8')))
                det = create_detection(data["filename"],data["accuracy"])
                #queue.put(create_detection(data["filename"],data["accuracy"]))
                if det is not None:
                    queue.put(det)

    except ContextTerminated as e:
        #print(f'Shutting down socket queue!')
        fireDetector_logger.info(f'Shutting down socket queue!')


def usage():
    print('Usage: fireDetector [<option>...] [<destination:port>...]\n')
    print('-z <zmq_url>\tZeroMQ URL (default: tcp://127.0.0.1:5556)')
    print('default destination <127.0.0.1:16551>')


def get_params():
    """Default values for the duration and sample count."""
    dst_url = "127.0.0.1:16551"
    dst     = "127.0.0.1"
    port    = 16551
    zmq_url = "tcp://127.0.0.1:5556"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:h:z:", ["dst", "help", "zmq"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-o", "--zmq"):
            zmq_url = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"
    # ...
    if len(args) > 0:
        dst_url = args[0].split(':')
        dst     = dst_url[0]
        port    = int(dst_url[1])

    return { "dst": dst,
            "port" : port,
            "zmq" : zmq_url}


if __name__ == '__main__':
    try:
        config  = get_params()
        dst     = config["dst"]
        port    = config["port"]
        zmq_url = config["zmq"]

        drone_sock = socket.socket(family=socket.AF_INET, 
                type=socket.SOCK_STREAM)
        done = False
        queue= Queue()

        context = zmq.Context()
        alert_thread = Thread(target=process_queue, args=(context,zmq_url,queue,))
        alert_thread.start()

        cnt = 0
            
        while not done:
            try:
                #print("Attempting to connect!")
                fireDetector_logger.info("Attempting to connect!")
                drone_sock.connect((dst, port))

                while signal_handler.KEEP_PROCESSING:
                    try:
                        # Queue updated with new detection
                        detection = queue.get(block=True, timeout=1)
                        if detection is not None:
                            cnt += 1
                            det_data = detection.get_msg() 

                            # Detection id extracted
                            detection_id    = det_data['uuid']

                            # Detection size sent 
                            det_json = json.dumps(det_data)
                            det_size = len(det_json)
                            det_info = f'{detection_id},{det_size}'
                            
                            drone_sock.send(det_info.encode('utf-8'))
                            ack = drone_sock.recv(1024)

                            drone_sock.sendall(det_json.encode('utf-8'))

                            ack = drone_sock.recv(1024)
                            #print(f'Count: {cnt}\t ACK: {ack}')
                            fireDetector_logger.info(f'Count: {cnt}\t ACK: {ack}')

                        else:
                            #print('Queue is empty.')
                            fireDetector_logger.info('Queue is empty.')
                            time.sleep(1)


                    except Empty:
                        time.sleep(0.5)
            except ConnectionRefusedError:
                time.sleep(1)
                if not signal_handler.KEEP_PROCESSING:
                    done = True
                
            #except ConnectionResetError:
               # drone_sock.close()
               #drone_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

               # time.sleep(1)
               #if not signal_handler.KEEP_PROCESSING:
               #done = True
            except FileNotFoundError:
                done = True
            except OSError:
                #print('Error: Exiting program.')
                fireDetector_logger.info('Error: Exiting program.')
                done = True

        #print("Socket loop closed")
        fireDetector_logger.info("Socket loop closed")
        context.destroy()
        alert_thread.join()
        drone_sock.close()


    except KeyboardInterrupt:
        #print('Exiting program!')
        fireDetector_logger.info('Exiting program!')
        sys.exit(1)
