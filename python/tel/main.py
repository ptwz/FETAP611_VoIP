import time
import phone
import signal

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-u", "--user",
    help="SIP user name",
    action="store",
    default=None,
    type=str)
parser.add_argument("-p", "--password",
    help="SIP password",
    action="store",
    default=None,
    type=str)
parser.add_argument("host",
    help="SIP host",
    action="store",
    type=str)

args = parser.parse_args()

p = phone.Phone( user=args.user, host=args.host,  passwd=args.password )

signal.signal(signal.SIGINT, signal.default_int_handler)

try:
    while True:
        #time.sleep(.005)
        time.sleep(.5)
        p.run()
except KeyboardInterrupt:
    p.shutdown()

