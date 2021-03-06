__author__ = 'srkiyengar'

import sys
import time
import struct
from socket import *

## looking at the finger side, "thumb" up:
##
##       thumb == z
##
##
##   left   (spread)  right
##    x               y
##
##  smaller spread is "towards the thumb"

# reflex-ros-pkg-master/firmware/reflex-takktile/reflex.h
NUM_FINGERS = 3

# reflex-ros-pkg-master/firmware/reflex-takktile/enc.h
NUM_ENC = 3

# reflex-ros-pkg-master/firmware/reflex-takktile/tactile.h
SENSORS_PER_FINGER =  9
NUM_PALM_SENSORS =11
NUM_SENSORS = (NUM_FINGERS * SENSORS_PER_FINGER + NUM_PALM_SENSORS)
NUM_TACTILE_PORTS = 4
NUM_INTERNAL_I2C = 2
NUM_BRIDGED_I2C = 2

# reflex-ros-pkg-master/firmware/reflex-takktile/state.h
state_t_decl = [
    ("header", "B", 4),         # version==1, pad, pad, pad
    ("systime", "I", 1),        # microseconds since boot
    ("tactile_pressures", "H", NUM_SENSORS),
    ("tactile_temperatures", "H", NUM_SENSORS),
    ("encoders", "H", NUM_ENC),
    ("dynamixel_error_status", "B", 4),
    ("dynamixel_angles", "H", 4),
    ("dynamixel_speeds", "H", 4),
    ("dynamixel_loads", "H", 4),
    ("dynamixel_voltages", "B", 4),
    ("dynamixel_temperatures", "B", 4), # celsius
]

# trivial "struct" mapper
endian = "<"

class byte_fields(object):
    def __init__(self, decl):
        self._decl = decl
        #self._fmt = endian + "".join(["%s%s" % (count, stformat) for name, stformat, count in self._decl])
        self._fmt = endian + "".join(["{}{}".format(count,stformat) for name, stformat, count in self._decl])
    def parse(self, packet):
        values = list(struct.unpack(self._fmt, packet))
        for name, stformat, count in self._decl:
            if count == 1:
                setattr(self, name, values.pop(0))
            else:
                setattr(self, name, values[:count])
                values[:count] = []
        assert not values, values

state_t = byte_fields(state_t_decl)

def onepkt():
    rx = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
    rx.bind(("", 11333))
    rx.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, inet_pton(2, '224.0.0.124') + inet_aton("0.0.0.0"))
    pkt, addr = rx.recvfrom(8192)
    return pkt, addr

def hear():
    pkt, addr = onepkt()
    print "from:", addr
    # print len(pkt), repr(pkt)
    state_t.parse(pkt)
    state_t.systime /= 1.0e6
    for name, _, _ in state_t_decl:
        print "%s: %s" % (name, getattr(state_t, name))

# Sample output:
#
# from: ('10.99.99.99', 11333)
#   -- address built into the firmware
# header: [1, 0, 0, 0]
#   -- version 1, 3 padding bytes
# systime: 1206.098311
#   -- seconds since boot
# tactile_pressures: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255]
#   -- sensors not hooked up to demo unit
# tactile_temperatures: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#   -- sensors not hooked up to demo unit
# encoders: [0, 0, 0]
#   -- sensors not hooked up to demo unit
# dynamixel_error_status: [0, 0, 0, 0]
#   -- should stay zero but if not, you probably want to intervene
# dynamixel_angles: [13542, 15930, 15007, 13091]
#   -- *motor* angles, not finger angles
# dynamixel_speeds: [0, 0, 0, 0]
#   -- likewise
# dynamixel_loads: [40, 24, 40, 8]
#   -- units?
# dynamixel_voltages: [120, 123, 123, 121]
#   -- units?
# dynamixel_temperatures: [39, 39, 42, 40]
#   -- degrees celsius

DMXL_CM_VELOCITY = 1
DMXL_CM_POSITION = 2

def set_position(x,y,z,spread):
    tx = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
    dest = ("224.0.0.124", 11333)
    tmp_str = chr(1) + chr(DMXL_CM_POSITION)*4, dest

    tx.sendto(chr(1) + chr(DMXL_CM_POSITION)*4, dest)
    time.sleep(0.01)
    msg = struct.pack(">"+"BHHHH", 2, x,y,z,spread)
    print tx.sendto(msg, dest)

# 100 is about 1cm at the tips
def nudge():
    pkt, addr = onepkt()
    state_t.parse(pkt)
    left,right,thumb,spread = state_t.dynamixel_angles
    print "Moving From: ", left,right,thumb,spread
    # modify these to play around!
    left += -100
    right += -100
    thumb += -100
    spread += -100
    print "Moving to: ", left,right,thumb,spread
    set_position(left,right,thumb,spread)

def wiggle():
    pkt, addr = onepkt()
    state_t.parse(pkt)
    left,right,thumb,spread = state_t.dynamixel_angles
    print left,right,thumb,spread
    delta=250
    delta_t=0.25
    try:
        while True:
            time.sleep(delta_t)
            set_position(left+delta,right,thumb,spread)
            time.sleep(delta_t)
            set_position(left+delta,right+delta,thumb,spread)
            time.sleep(delta_t)
            set_position(left+delta,right+delta,thumb+3*delta,spread)
            time.sleep(delta_t)
            set_position(left,right+delta,thumb+delta,spread)
            time.sleep(delta_t)
            set_position(left,right,thumb+delta,spread)
            time.sleep(delta_t)
            set_position(left,right,thumb,spread)
    except KeyboardInterrupt:
        time.sleep(delta_t)
        set_position(left,right,thumb,spread)



if __name__ == "__main__":

    hear()
    time.sleep(1)
    nudge()
    time.sleep(1)
    hear()
    #if sys.argv[1] == "hear":
    #    hear()
    #elif sys.argv[1] == "nudge":
    #    nudge()
    #elif sys.argv[1] == "wiggle":
    #    wiggle()
    #else:
    #    sys.exit("hear, nudge, wiggle")