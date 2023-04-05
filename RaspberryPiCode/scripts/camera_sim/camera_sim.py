#!/usr/bin/env python3
###############################################################################
# File: camera_sim.py
# Date: 03/16/2023
# Description: Script used to generate JPEG files for testing.
# Version: 1.0
###############################################################################

import os
import sys
import getopt
import time
import shutil


def usage():
    print('Usage: camera_sim.py [<option>...]\n')
    print('\t-i <directory>\tDirectory look for JPEG files [--input]')
    print('\t-o <directory>\tDirectory where the files will be placed [--output]')
    print('\t-r <rate>\tSet the timeout between copies in seconds [--rate]')
    print('\t-h\t\tPrint the help menu')


def get_params():
    """Param function for capturing the camera sim generated files."""
    img_dir ='./images'
    output_dir = '/tmp/out/input'
    rate = 1.0

    try:
        opts, args = getopt.getopt(
                            sys.argv[1:],
                            "i:h:o:r:",
                            ["input", "help", "output", "rate"])

    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-i", "--input"):
            img_dir = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-o", "--output"):
            output_dir = a
        elif o in ("-r", "--rate"):
            rate = float(a)
        else:
            usage()
            assert False, "unhandled option"

    return {"input": img_dir,
            "output": output_dir,
            "rate" : rate}


if __name__=='__main__':
    config = get_params()
    img_dir = config['input']
    output_dir = config['output']
    rate = config["rate"]

    try:
        if not os.path.exists(img_dir) or os.listdir(img_dir) == []:
            print(f'Warning: Image directory does not exist!')
            print(f'Please restart with the correct path.')
            sys.exit(1)

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

        os.makedirs(output_dir)

        i = 1
        print('Starting the camera sim:......')
        print(f'Copying from {img_dir} to {output_dir}')

        while True:
            for s in os.listdir(img_dir):
                src = img_dir + f'/{s}' 
                dst = output_dir + f'/img_{i:0>3d}.jpg'
                shutil.copy2(src,dst)
                print(f'Created file: {dst}',end='\r')
                i += 1

                time.sleep(rate)
    except KeyboardInterrupt:
        print('\nShutting down!')

