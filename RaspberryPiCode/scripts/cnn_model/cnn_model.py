#!/usr/bin/env python3
###############################################################################
# File: cnn_model.py
# Date: 03/25/2023
# Description: CNN model used to detect fires and to trigger fire detection.
# Version: 1.0
###############################################################################
import numpy as np
import cv2
import os
import sys
import getopt
import random
import base64
import json
import time
import zmq
import logging
import logging.handlers
from threading import Thread
from signal_handler import SignalHandler
from watcher import Watcher
from watchdog.events import FileSystemEventHandler
from queue import Queue
from queue import Empty
from tflite_runtime.interpreter import Interpreter

LOG_FILENAME = '/opt/firedrone/logs/cnn_model.log'

#Set up a specific logger with a desired output level
cnn_logger = logging.getLogger('cnn_model')
cnn_logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes = 200000, backupCount = 5)

cnn_logger.addHandler(handler)

formatter = logging.Formatter('%asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Global variable for monitoring Ctrl+C
signal_handler = SignalHandler()

class Alert:
    def __init__(self, filename, accuracy):
        self._filename = filename
        self._accuracy = accuracy

    def get_msg(self):
        return { "filename": self._filename,
                 "accuracy": self._accuracy }
                 
class FileHandler(FileSystemEventHandler):
    def __init__(self, queue, prob_rate=50.0, model_path=".", label_path="."):
        self._queue = queue
        self._prob_rate=prob_rate
        self._label_path=label_path
        self._model_path=model_path

    def on_any_event(self, event):
        if event.event_type == "created":
            path = event.src_path
            if path.lower().endswith(('.jpg','.jpeg')):
                if os.path.getsize(path) != 0:
                    #probability = random.uniform(0, 100)
                    input_shape = (256, 256, 3)
                    threshold = 0.8
                    labels = load_labels(self._label_path)
                    interpreter = load_interpreter(self._model_path)
                    image = preprocess_image(path, input_shape)
                    label, probability = classify_image(interpreter, image, labels, threshold)
                    probability = probability * 100
                    #print(f'Fire Detection Probability: {probability}%')
                    cnn_logger.info(f'Fire Detection Probability: {probability}%')
                    if probability > self._prob_rate:
                        self._queue.put(Alert(path, probability))              
                        
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
                #print(f'{json.dumps(alert.get_msg())}')
                cnn_logger.debug(f'{json.dumps(alert.get_msg())}')
        except Empty:
            time.sleep(0.5)
def usage():
    print('Usage: cnn_sim [<option>...]\n')
    print('\t-w <directory>\tDirectory to watch for geotagged JPEG files [--watch]')
    print('\t-u <URL>\tZeroMQ URL for posting detections [--url] (default: tcp://localhost:5555)')
    print('\t-p <probability>\tProbability limit for detections [--prob] (default: 50)')
    print('\t-m <model_path>\tPath to model file [--model]')
    print('\t-l <label_path>\tPath to label file [--label}')
    print('\t-h\t\tPrint the help menu')


def get_params():
    """Param function for detecting geotagged files. """
    watch_dir = "."
    url_addr = "tcp://127.0.0.1:5556"
    model_path = "/opt/firedrone/data/classify.tflite"
    label_path = "/opt/firedrone/data/labels.txt"
    
    prob = 50

    try:
        opts, args = getopt.getopt(
                            sys.argv[1:],
                            "w:h:u:p:m:l:",
                            ["watch", "help", "url", "prob", "model","label"])

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
        elif o in ("-m", "--model"):
            model_path = a
        elif o in ("-l", "--label"):
            label_path = a
        else:
            usage()
            assert False, "unhandled option"

    return {"watch" : watch_dir, "url" : url_addr, "prob": prob, "model" : model_path, "label" : label_path}

             
def load_labels(path):
    with open(path, 'r') as f:
        return [line.strip() for line in f.readlines()]

def load_interpreter(path):
    with open(path, 'rb') as f:
        interpreter = Interpreter(model_content=f.read())
    interpreter.allocate_tensors()
    return interpreter

def preprocess_image(image_path, input_shape):
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, input_shape[:-1])
    image = (image.astype(np.float32) / 127.5) - 1.0
    image = np.expand_dims(image, 0)
    return image

def classify_image(interpreter, image, labels, threshold):
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    interpreter.set_tensor(input_details[0]['index'], image)
    interpreter.invoke()
    scores = interpreter.get_tensor(output_details[0]['index'])[0]
    index = np.argmax(scores)
    probability = 1 - scores[index]
    label = labels[index]
    return label, probability

def main():
    config = get_params()
    pub_q = Queue()
    
    watch_dir = config["watch"]
    url       = config["url"]
    prob_rate = config["prob"]
    model_path = config["model"]
    label_path = config["label"]
    
    if not os.path.exists(watch_dir):
            #print(f'Warning: {watch_dir} does not exit!')
            cnn_logger.info(f'Warning: {watch_dir} does not exit!')
            sys.exit(1)
    
    w = Watcher(watch_dir, FileHandler(pub_q, prob_rate, model_path, label_path), signal_handler)
    watcher_thread = Thread(target=w.run)
    watcher_thread.start()
    
    pub_thread = Thread(target=publish_alert, args=(pub_q, url, ))
    pub_thread.start()
    
    watcher_thread.join()
    pub_thread.join()
    
    #model_path = 'classify.tflite'
    #label_path = 'labels.txt'
    #image_path = 'JPGs'
    #input_shape = (256, 256, 3)
    #threshold = 0.8

    #for filename in os.listdir(image_path):
        #f = os.path.join(image_path, filename)
        # checking if it is a file
        #if os.path.isfile(f):
            #image = f
            #print(image)
        #labels = load_labels(label_path)
        #interpreter = load_interpreter(model_path)
        #image = preprocess_image(image, input_shape)
        #label, probability = classify_image(interpreter, image, labels, threshold)
        #print(f'The model classified the image as {label} with a probability of {probability:.2f}.')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        #print(f'Shutting Down')
        cnn_logger.info(f'Shutting Down')
