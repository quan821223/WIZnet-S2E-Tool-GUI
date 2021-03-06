# -*- coding: utf-8 -*-

## Make Serial command

import socket
import time
import struct
import binascii
import sys
import getopt
import logging
import re
import os
from WIZ750CMDSET import WIZ750CMDSET
from WIZ752CMDSET import WIZ752CMDSET
from WIZUDPSock import WIZUDPSock
from WIZMSGHandler import WIZMSGHandler
from WIZArgParser import WIZArgParser
from FWUploadThread import FWUploadThread
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

OP_SEARCHALL = 1
OP_GETCOMMAND = 2
OP_SETCOMMAND = 3
OP_SETFILE = 4
OP_GETFILE = 5
OP_FWUP = 6

# Supported devices
ONE_PORT_DEV = [
    "WIZ750SR",
    "WIZ750SR-100",
    "WIZ750SR-105",
    "WIZ750SR-110",
    "WIZ107SR",
    "WIZ108SR",
]
TWO_PORT_DEV = ["WIZ752SR-12x", "WIZ752SR-120", "WIZ752SR-125"]
# DEVICE_SERVER = []

# BAUDRATES = [300, 600, 1200, 1800, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400, 460800]
# not use 'UI' and 'EI' on Configuration tool (UART interface(Code))

# for pre-search
cmd_presearch = ["MC", "VR", "MN", "ST", "IM", "OP", "LI", "SM", "GW"]

# Command for each device
cmd_ch1 = ['MC','VR','MN','UN','ST','IM','OP','DD','CP','PO','DG','KA','KI','KE','RI','LI','SM','GW','DS','PI','PP','DX','DP','DI','DW','DH','LP','RP','RH','BR','DB','PR','SB','FL','IT','PT','PS','PD','TE','SS','NP','SP']
cmd_added = ['SC', 'TR']  # for WIZ750SR F/W version 1.2.0 or later
cmd_ch2 = ['QS','QO','QH','QP','QL','RV','RA','RE','RR','EN','RS','EB','ED','EP','ES','EF','E0','E1','NT','NS','ND']

cmd_gpio = ["CA", "CB", "CC", "CD", "GA", "GB", "GC", "GD"] # for expansion GPIO

# command for WIZ2000
cmd_wiz2000 = ['MB', 'SE', 'CE', 'N0', 'N1', 'N2', 'LF', 'AE', 'AP', 'CT', 'AL', 'GR', 'AM', 'CM', 'C0', 'C1', 'C2', 'C3', 'UP']
# cmd_wiz2000 = ['MB', 'MM', 'SE', 'CE', 'N0', 'N1', 'N2', 'LF', 'QF', 'AE', 'AP', 'CT', 'AL', 'GR', 'AM'] # include channel 2 command

### CMD list
cmd_1p_default = cmd_ch1
cmd_1p_advanced = cmd_ch1 + cmd_added
cmd_2p_default = cmd_ch1 + cmd_ch2

def version_compare(version1, version2):
    def normalize(v):
        # return [x for x in re.sub(r'(\.0+)*$','',v).split('.')]
        return [x for x in re.sub(r"(\.0+\.[dev])*$", "", v).split(".")]

    obj1 = normalize(version1)
    obj2 = normalize(version2)
    return (obj1 > obj2) - (obj1 < obj2)
    # if return value < 0: version2 upper than version1


class WIZMakeCMD:
    def __init__(self):
        pass

    def make_header(self, mac_addr, idcode, devname='', set_pw=''):
        cmd_header = []
        cmd_header.append(["MA", mac_addr])
        cmd_header.append(["PW", idcode])
        # print('reset', mac_addr, idcode, set_pw, devname)
        if devname:
            if "WIZ2000" in devname:
                cmd_header.append(["AP", set_pw.decode()])

        return cmd_header

    def presearch(self, mac_addr, idcode):
        cmd_list = self.make_header(mac_addr, idcode)
        # Search All Devices on the network
        # 장치 검색 시 필요 정보 Get
        for cmd in cmd_presearch:
            cmd_list.append([cmd, ""])
        return cmd_list

    def search(self, mac_addr, idcode, devname, version):
        cmd_list = []
        # Search All Devices on the network
        cmd_list.append(["MA", mac_addr])
        cmd_list.append(["PW", idcode])

        if devname in ONE_PORT_DEV or "750" in devname:
            if "750" in devname and version_compare("1.2.0", version) <= 0:
                for cmd in cmd_1p_advanced:
                    cmd_list.append([cmd, ""])
            else:
                for cmd in cmd_1p_default:
                    cmd_list.append([cmd, ""])
        elif devname in TWO_PORT_DEV or "752" in devname:
            for cmd in cmd_2p_default:
                cmd_list.append([cmd, ""])
        elif "WIZ2000" in devname:
            cmds = cmd_1p_advanced + cmd_wiz2000
            for cmd in cmds:
                cmd_list.append([cmd, ""])
        else:
            pass

        return cmd_list

    def get_gpiovalue(self, mac_addr, idcode):
        cmd_list = self.make_header(mac_addr, idcode)
        
        for cmd in cmd_gpio:
            cmd_list.append([cmd, ""])
        return cmd_list

    # Set device
    # TODO: device profile 적용
    def setcommand(self, mac_addr, idcode, set_pw, command_list, param_list, devname, version):
        cmd_list = self.make_header(mac_addr, idcode, devname=devname, set_pw=set_pw)
        try:
            # print('Macaddr: %s' % mac_addr)

            for i in range(len(command_list)):
                cmd_list.append([command_list[i], param_list[i]])

            if devname in ONE_PORT_DEV or "750" in devname:
                if "750" in devname and version_compare("1.2.0", version) <= 0:
                    for cmd in cmd_1p_advanced:
                        cmd_list.append([cmd, ""])
                else:
                    for cmd in cmd_1p_default:
                        cmd_list.append([cmd, ""])
            elif devname in TWO_PORT_DEV or "752" in devname:
                # for cmd in cmd_2p_default:
                #     cmd_list.append([cmd, ""])
                # for WIZ752SR-12x
                for cmd in cmd_ch2:
                    cmd_list.append([cmd, ""])
            elif "WIZ2000" in devname:
                cmds = cmd_1p_advanced + cmd_wiz2000
                for cmd in cmds:
                    cmd_list.append([cmd, ""])
            cmd_list.append(["SV", ""])  # save device setting
            cmd_list.append(["RT", ""])  # Device reboot
            # print("setcommand()", cmd_list)
            return cmd_list
        except Exception as e:
            sys.stdout.write("[ERROR] setcommand(): %r\r\n" % e)

    def reset(self, mac_addr, idcode, set_pw, devname):
        print('reset', mac_addr, idcode, set_pw, devname)
        cmd_list = self.make_header(mac_addr, idcode, devname=devname, set_pw=set_pw)
        cmd_list.append(["RT", ""])
        return cmd_list

    def factory_reset(self, mac_addr, idcode, set_pw, devname, param):
        cmd_list = self.make_header(mac_addr, idcode, devname=devname, set_pw=set_pw)
        cmd_list.append(["FR", param])
        return cmd_list

