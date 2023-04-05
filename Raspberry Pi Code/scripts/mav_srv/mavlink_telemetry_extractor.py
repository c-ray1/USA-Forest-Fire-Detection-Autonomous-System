#!/usr/bin/env python3

import asyncio
import math
import sys
import zmq
import json
import logging
from mavsdk import System
import logging.handlers


LOG_FILENAME = '/opt/firedrone/logs/mav_src.log'

#Set up a specific logger with a desired output level
mav_logger = logging.getLogger('mav_srv')
mav_logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes = 200000, backupCount = 5)

mav_logger.addHandler(handler)

formatter = logging.Formatter('%(asctime)s -[%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

class GeoTag:
    def __init__(self):
        self._lat_deg = 0.0
        self._lon_deg = 0.0
        self._alt_m = 0.0
        self._yaw = 0.0
        self._roll = 0.0
        self._pitch = 0.0
        self._speed = 0.0
        self._time_utc = 0
    def get_msg(self):
        return {
                "time" : self._time_utc,
                "lat" : self._lat_deg,
                "lon" : self._lon_deg,
                "alt" : self._alt_m,
                "yaw" : self._yaw,
                "pitch" : self._pitch,
                "roll" : self._roll,
                "speed" : self._speed
                }

async def run(url="serial:///dev/ttyS0:921600"):
    drone = System()
    await drone.connect(url)
    #print("Waiting for drone...")
    mav_logger.info("Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
           # print("Drone discovered")
           mav_logger.info("Drone discovered")
           break
    context = zmq.Context()
    pub_sock= context.socket(zmq.PUB)
    pub_sock.bind("tcp://127.0.0.1:5555")

    obj = GeoTag()
    asyncio.ensure_future(print_position(drone, obj))
    asyncio.ensure_future(print_eangle(drone, obj))
    asyncio.ensure_future(print_rawgps(drone, obj))
    asyncio.ensure_future(print_velocity(drone, obj))
    
    while True:
       # print("-------GeoTag-----------")
       mav_logger.info("-------GeoTag------------")
       #print(obj.get_msg())
       mav_logger.info(obj.get_msg())
       pub_sock.send_string('GeoTag', flags=zmq.SNDMORE)
       pub_sock.send_json(obj.get_msg())
       await asyncio.sleep(1)

async def print_position(drone, obj: GeoTag):
   async for position in drone.telemetry.position():
        obj._lat_deg = position.latitude_deg
        obj._lon_deg = position.longitude_deg
        obj._alt_m = position.absolute_altitude_m
    
async def print_eangle(drone, obj: GeoTag):
    async for eulerangle in drone.telemetry.attitude_euler():
        obj._yaw = eulerangle.yaw_deg
        obj._roll = eulerangle.roll_deg
        obj._pitch= eulerangle.pitch_deg
        
async def print_rawgps(drone, obj: GeoTag):
    async for rawgps in drone.telemetry.raw_gps():
        obj._time_utc = rawgps.timestamp_us
        
async def print_velocity(drone, obj: GeoTag):
    async for velocity in drone.telemetry.velocity_ned():
        a = velocity.north_m_s * velocity.north_m_s
        b = velocity.east_m_s * velocity.east_m_s
        c = velocity.down_m_s * velocity.down_m_s
        
        speed = math.sqrt(a + b + c) * 2.237
        obj._speed = speed
        
if __name__ == "__main__":
    try:
        # Default connection URL
        url = "serial:///dev/ttyS0:921600"
        if(len(sys.argv) > 1):
            url = sys.argv[1]
          # print(f'Attempting to connect to drone: {url}')
            mav_logger.info(f'Attemping to connect to drone:{url}')
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run(url))
    except KeyboardInterrupt:
        print("\nShutting Down!")


