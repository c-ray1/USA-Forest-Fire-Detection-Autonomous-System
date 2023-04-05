#!/usr/bin/env python3
import _thread
import socket
import sys
import json
import time
import os
import getopt
import base64
import logging
import logging.handlers

LOG_FILENAME = '/opt/firedrone/logs/mission_srv.log'

#Set up a specific logger with a desired output level
mission_logger = logging.getLogger('mission_srv')
mission_logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes = 200000, backupCount = 5)

mission_logger.addHandler(handler)

formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

RCVBUF = 1024 

def usage():
    print('Usage: mission_srv [<source:port>...]\n')
    print('default source <0.0.0.0:16551>')


def process_msg(path:str='/opt/firedrone/data', msg:dict=None):
    
    tel_path = f'{path}/telemetry'
    img_path = f'{path}/imagery'

    if not os.path.exists(tel_path):
       # print(f'Warning: Path {path} does not exit')
        mission_logger.info(f'Warning: Path {path} does not exist')
       # print('Attempting to create!')
        mission_logger.info('Attempting to create!')
        os.makedirs(tel_path, exist_ok=True)

    if msg is not None:
        tel_file = msg["uuid"]

        tel_keys = ['time','lat','lon','alt','yaw','pitch','roll','speed']

        tel_dict = {key:value for key, value in msg.items() if key in tel_keys}
        tel_path = f'{tel_path}/{tel_file}'

        with open(tel_path, 'w') as tp:
            tp.write(json.dumps(tel_dict))


        img_dict = msg['image']
        img_data = base64.b64decode(img_dict['b64'].encode('utf'))

        if not os.path.exists(img_path):
            #print(f'Warning: Path {path} does not exit')
            mission_logger.info(f'Warning: Path {path} does not exist')
            #print('Attempting to create!')
            mission_logger.info('Attempting to create!')
            os.makedirs(img_path, exist_ok=True)
        img_path = f'{img_path}/{msg["uuid"]}.{img_dict["ext"]}'

        with open(img_path, 'wb') as ip:
            ip.write(img_data)




def recv_func(conn, out_dir):

    i = 0

    while True:
        i += 1
        # Buffer for message string
        det_msg = b'' 
        
        # Protocol to receive the detection id and detection size
        det_info = conn.recv(RCVBUF).decode('utf-8')
        det = det_info.split(',')

        # Verify that the received string contains the two items
        if len(det) < 2:
            #print('Error: Invalid buffer.')
            mission_logger.debug('Error: Invalid buffer.')
            break;

        det_id = det[0]
        det_size = int(det[1])

       # print(f'Count: {i}\tReceived: {det_id}\t{det_size} bytes')
        mission_logger.info(f'Count: {i}\tReceived: {det_id}\t{det_size} bytes')
        conn.send(b'NAME_SIZE')

        bytes_recvd = 0

        # Loop until all the detection bytes have been received
        while bytes_recvd < det_size:
            data = conn.recv(RCVBUF)
            bytes_recvd += len(data)
            # Accumlate all the bytes
            det_msg += data

        conn.send(det_id.encode('utf-8'))

        msg = json.loads(det_msg.decode('utf-8'))

        process_msg(out_dir,msg)


    conn.close()

def get_params():
    dst_url = "0.0.0.0:16551"
    dst     = "0.0.0.0"
    port    = 16551
    output_dir = "/opt/firedrone/data"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "o:h:", ["output", "help"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-o", "--output"):
             output_dir = a
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
            "output" : output_dir}


def main():
    """Default values for the duration and sample count."""
    config = get_params()
    dst = config["dst"]
    port = config["port"]
    output_dir = config["output"]

    # check if output path exists. if not attempt to create it.
    if not os.path.exists(output_dir):
        #print(f'Warning: Directory [{output_dir}] does not exist')
        mission_logger.info(f'Warning: Directory [{output_dir}] does not exist')
        os.makedirs(output_dir, exist_ok=True)

    #if len(sys.argv) > 1:
    #    url = sys.argv[1].split(':')
    #    dst = url[0]
    #    port = int(url[1])
    #    print(f'url = {dst}:{port}')

    gcs_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    gcs_sock.bind((dst, port))
    gcs_sock.listen(5)


    #print(f'Waiting for network packets on {dst}:{port}')
    mission_logger.info(f'Waiting for network packets on {dst}:{port}')

    while True:
        conn, addr = gcs_sock.accept()

        #print(f'Connected to {addr[0]}:{addr[1]}')
        mission_logger.info(f'Connected to {addr[0]}:{addr[1]}')
        _thread.start_new_thread(recv_func, (conn,output_dir))

    gcs_sock.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        #print('Exiting program!')
        mission_logger.info('Exiting program!')
