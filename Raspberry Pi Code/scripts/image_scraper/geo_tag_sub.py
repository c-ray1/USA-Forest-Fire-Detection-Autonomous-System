#!/usr/bin/env python3
############################################################################ File: geo_tag_sub.py
# Date: 03/13/2023
# Description: Object used to subscribe to the GeoTag zeromq message bus.
# Version: 1.0
###########################################################################
import zmq
import json
from zmq import ContextTerminated
from threading import Thread 

class GeoTagSub():
    def __init__(self,topic="GeoTag", url="tcp://localhost:5555"):
        self._subscribe = topic
        self._url = url
        self._context = zmq.Context()
        self._shutdown = False
        self._data = {
                "time": 0,
                "lat" : 0.0,
                "lon" : 0.0,
                "alt" : 0.0,
                "yaw" : 0.0,
                "pitch": 0.0,
                "roll" : 0.0,
                "speed" : 0.0 }

    def create_thread(self):
        successful = False
        sub_thread = Thread(target=self.run)
        sub_thread.start()

        return successful

    def run(self):
        socket  = self._context.socket(zmq.SUB)
        socket.connect(self._url)
        socket.subscribe(self._subscribe)
        try:
            while not self._shutdown:
                topic, msg = socket.recv_multipart()
                self._data = json.loads(msg.decode("utf-8"))

        except ContextTerminated as e:
            print(f'Shutting down socket queue')

    def get_time_utc(self):
        return self._data["time"]

    def get_lat_deg(self):
        return self._data["lat"]

    def get_lon_deg(self):
        return self._data["lon"]

    def get_alt_deg(self):
        return self._data["alt"]

    def get_yaw_deg(self):
        return self._data["yaw"]

    def get_pitch_deg(self):
        return self._data["pitch"]

    def get_roll_deg(self):
        return self._data["roll"]

    def get_speed_mph(self):
        return self._data["speed"]

    def get_data(self):
        return self._data

    def close(self):
        self._shutdown = True
        self._context.destroy(linger=0)



