#!/usr/bin/env python3
###############################################################################
# Description: Simulator for publishing fire detecitons using Zero MQ
# Date: 02/19/2023
# Version: 1.0
# Packages: 
# 1) apt install libexiv2-dev libboost-python-dev libexiv2python python3-py3exiv2
# 2) pip3 install pyzmq
###############################################################################
import zmq

class Director:
    _builder = None

    def set_builder(self, builder):
        self._builder = builder
    def getDetection():


class Builder:
    def get_gps_position(self): pass
    def get_image_file(self): pass

class DetectionBuilder:
    def __init__(self):


def main() -> None:
    pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program exiting...")
