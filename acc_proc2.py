# usage: python data_fuser.py [mac1] [mac2] ... [mac(n)]
from __future__ import print_function
from ctypes import c_void_p, cast, POINTER
from mbientlab.metawear import MetaWear, libmetawear, parse_value, cbindings,LedPattern, Const, byref,LedPreset,LedColor
from mbientlab.warble import BleScanner
from time import sleep, time
from datetime import datetime
from threading import Event
#from sys import argv
import sys 
import csv
import configparser
import os
import platform
import six

from colorama import Fore, Back, Style

states = []
CC_main = None
CC_sec = None


def print_red(string):
   print(Fore.RED + string)

def print_yellow(string):
   print(Fore.YELLOW + string)   
   
def print_green(string):
   print(Fore.GREEN + string)


def print_logo():
    print_green('')
    print(r"  ____ _ _        ____                 _          _    ___ ")
    print(r" / ___| (_)_ __  / ___|___   __ _  ___| |__      / \  |_ _|")
    print(r"| |   | | | '_ \| |   / _ \ / _` |/ __| '_ \    / _ \  | | ")
    print(r"| |___| | | |_) | |__| (_) | (_| | (__| | | |  / ___ \ | | ")
    print(r" \____|_|_| .__/ \____\___/ \__,_|\___|_| |_| /_/   \_\___|")
    print(r"          |_|                                              ")
    print("ver 1.0")

   

class State:
    # init
    def __init__(self, device):
        self.device = device
        self.callback = cbindings.FnVoid_VoidP_DataP(self.data_handler)
        self.processor = None
        # Create or open the file in append mode
        self.file_name = 'clipcoach_' + datetime.now().strftime("%Y%m%d_%H%M%S") + '_' + self.device.address.replace(':','') +'.csv'
        with open(self.file_name, mode='w', newline='') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(['Timestamp', 'Address', 'ACC_X', 'ACC_Y', 'ACC_Z', 'GYRO_X', 'GYRO_Y', 'GYRO_Z'])

    # download data callback fxn
    def data_handler(self, ctx, data):
        values = parse_value(data, n_elem = 2)
        timestamp = time()
        if self.device.address == CC_main:
         device_type = 'main'
        else:
         device_type = 'sec'
        
        with open(self.file_name, mode='a', newline='') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow([timestamp, device_type, values[0].x, values[0].y, values[0].z, values[1].x, values[1].y, values[1].z])
         
        
    # setup
    def setup(self):
        # ble settings
        libmetawear.mbl_mw_settings_set_connection_parameters(self.device.board, 7.5, 7.5, 0, 6000)
        sleep(1.5)
        # events
        e = Event()
        # processor callback fxn
        def processor_created(context, pointer):
            self.processor = pointer
            e.set()
        # processor fxn ptr
        fn_wrapper = cbindings.FnVoid_VoidP_VoidP(processor_created)
        # get acc signal
        acc = libmetawear.mbl_mw_acc_get_acceleration_data_signal(self.device.board)
        # get gyro signal - MMRl, MMR, MMc ONLY
        gyro = libmetawear.mbl_mw_gyro_bmi160_get_rotation_data_signal(self.device.board)
        
        
        # create signals variable
        signals = (c_void_p * 1)()
        signals[0] = gyro
        # create acc + gyro signal fuser
        libmetawear.mbl_mw_dataprocessor_fuser_create(acc, signals, 1, None, fn_wrapper)
        # wait for fuser to be created
        e.wait()
        # subscribe to the fused signal
        libmetawear.mbl_mw_datasignal_subscribe(self.processor, None, self.callback)
    # start
    def start(self):
        # start gyro sampling - MMRL, MMC, MMR only
        libmetawear.mbl_mw_gyro_bmi160_enable_rotation_sampling(self.device.board)
        
        # start acc sampling
        libmetawear.mbl_mw_acc_enable_acceleration_sampling(self.device.board)
        # start gyro - MMRL, MMC, MMR only
        libmetawear.mbl_mw_gyro_bmi160_start(self.device.board)
        
        
        # start acc
        libmetawear.mbl_mw_acc_start(self.device.board)

def save_ini():
     config = configparser.ConfigParser()
     global CC_main
     config['main'] = {
          'MAC' : str(CC_main)
        }
     global CC_sec
     config['sec'] = {
          'MAC' : str(CC_sec)
        }
     with open('device_config.ini', 'w') as configfile:
         config.write(configfile)
      


def load_ini():
    if os.path.exists('device_config.ini'):
     mac=[]
     print('read from ini...')
     config = configparser.ConfigParser()
     
     # Read from the .ini file
     config.read('device_config.ini')
     
     mac.append(config['main']['mac'])
     mac.append(config['sec']['mac'])
     return mac
    
    

def scan_connect(CCType):
  selection = -1
  devices = None
  
  while selection == -1:
        print(f"Scanning for ClipCoach ({CCType}) device...")
        devices = {}
        def handler(result):
            devices[result.mac] = result.name
        
        BleScanner.set_handler(handler)
        BleScanner.start()
        sleep(5.0)
        BleScanner.stop()
       
        i = 0
        for address, name in six.iteritems(devices):
            print("[%d] %s (%s)" % (i, address, name))
            i+= 1

        msg = "Select your device (-1 to rescan): "
        selection = int(raw_input(msg) if platform.python_version_tuple()[0] == '2'
        else input(msg))

  address = list(devices)[selection] 
  print("Connecting to %s..." % (address))
  device = MetaWear(address)
  device.connect()
  libmetawear.mbl_mw_haptic_start_buzzer(device.board, 500)
  sleep(0.8)
  libmetawear.mbl_mw_haptic_start_buzzer(device.board, 500)
  print("Connected to " + device.address)
  states.append(State(device))
  pattern= LedPattern(repeat_count= Const.LED_REPEAT_INDEFINITELY)
  libmetawear.mbl_mw_led_load_preset_pattern(byref(pattern), LedPreset.SOLID)
  if CCType=="main":
   libmetawear.mbl_mw_led_write_pattern(device.board, byref(pattern), LedColor.GREEN)
  else:
   libmetawear.mbl_mw_led_write_pattern(device.board, byref(pattern), LedColor.RED)
  libmetawear.mbl_mw_led_play(device.board)
  sleep(5.0)
  libmetawear.mbl_mw_led_stop_and_clear(device.board)
  #device.disconnect()
  sleep(1)
  return device.address

def ask_yes_no(prompt):
    while True:
        print_yellow('')
        response = input(prompt).lower()  # Convert to lowercase for easier comparison
        if response in ['yes', 'y','']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'.")  # If input is invalid, prompt again

    
def main():
    os.system('cls')
    print_logo()
    global CC_main
    global CC_sec
    CC_main = None
    CC_sec = None
    CC_main, CC_sec = load_ini()    
    
    if CC_main is not None and CC_sec is not None:
        print_red(f"Main ClipCoach: {CC_main}")
        print_green(f"Sec ClipCoach: {CC_sec}")
        if not ask_yes_no("Do you want to continue?"):
            CC_main = None
            CC_sec = None
        else:
           d = MetaWear(CC_main)
           d.connect()
           states.append(State(d))
           d = MetaWear(CC_sec)
           d.connect()
           states.append(State(d))
           
    if CC_main is None or CC_sec is None:
        CC_main = scan_connect('main')
        CC_sec = scan_connect('sec')
    save_ini()
    #'D3:2D:3E:01:8E:AF'
    #d = MetaWear(CC_main)
    #d.connect()
    #print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))
    #states.append(State(d))
    #
    #d = MetaWear('D3:2D:3E:01:8E:AF')
    #d.connect()
    #print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))
    #states.append(State(d))

    # configure
    for s in states:
        print("Configuring %s" % (s.device.address))
        s.setup()
    print_green('START!')
    # start
    for s in states:
        s.start()

    # wait 10 s
    #sleep(10.0)
    if ask_yes_no("Press ENTER to end streaming!"):
        None

    # reset
    print("Resetting devices")
    events = []
    for s in states:
        e = Event()
        events.append(e)

        s.device.on_disconnect = lambda s: e.set()
        libmetawear.mbl_mw_debug_reset(s.device.board)

    for e in events:
        e.wait()
    
if __name__ == "__main__":
    main()