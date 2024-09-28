from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *

from time import sleep, time
from threading import Event
from mbientlab.warble import * 
import sys



import platform
import six



states = []
CC_main_address = None
CC_sec_address = None

def print_logo():
    print(r"  ____ _ _        ____                 _          _    ___ ")
    print(r" / ___| (_)_ __  / ___|___   __ _  ___| |__      / \  |_ _|")
    print(r"| |   | | | '_ \| |   / _ \ / _` |/ __| '_ \    / _ \  | | ")
    print(r"| |___| | | |_) | |__| (_) | (_| | (__| | | |  / ___ \ | | ")
    print(r" \____|_|_| .__/ \____\___/ \__,_|\___|_| |_| /_/   \_\___|")
    print(r"          |_|                                              ")
    print("ver 1.0")
    
class State:
    def __init__(self, device):
        self.device = device
        self.samples = 0
        self.accCallback = FnVoid_VoidP_DataP(self.acc_data_handler)
        self.gyroCallback = FnVoid_VoidP_DataP(self.gyro_data_handler)

    # acc callback function
    def acc_data_handler(self, ctx, data):
        self.acc_values = parse_value(data)
        self.log_data()
        #print(f"{self.device.address};ACC;{timestamp};{values})")
        #self.samples+= 1
                        
    # gyro callback function
    def gyro_data_handler(self, ctx, data):
       
       self.gyro_values = parse_value(data)
       self.log_data()
       #print(f"{self.device.address};GYRO;{timestamp};{values})")
       #print("GYRO: %s -> %s" % (self.device.address, parse_value(data)))
       #self.samples+= 1
        
    def log_data(self):
      if self.gyro_values is not None and self.acc_values is not None:
        timestamp = time()
        log_entry = f"{self.device.address};{timestamp};{self.samples};ACC:{self.acc_values};GYRO:{self.gyro_values}"
        print(log_entry)  # Print or store the log entry
        self.samples += 1

   


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
        sleep(10.0)
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
  device.disconnect()
  sleep(1)
  return device.address

def add_states(address):
  device = MetaWear(address)
  states.append(State(device))
   
   
def start_streaming():
  for s in states:
    if s.device.address == CC_main_address:
        print("Configuring main ClipCoach...")
    else:
        print("Configuring sec ClipCoach...")
        
    #libmetawear.mbl_mw_settings_set_connection_parameters(s.device.board, 7.5, 7.5, 0, 6000)
    #sleep(1.5)
    print(f' ClipoCoach: {s.device.address}');
    s.device.connect()
    # config acc
    libmetawear.mbl_mw_acc_set_odr(s.device.board, 50.0)  # Set sampling rate to 50 Hz
    libmetawear.mbl_mw_acc_set_range(s.device.board, 4.0)  # Set range ±4g
    libmetawear.mbl_mw_acc_write_acceleration_config(s.device.board)

    acc = libmetawear.mbl_mw_acc_get_acceleration_data_signal(s.device.board)
    libmetawear.mbl_mw_datasignal_subscribe(acc, None, s.accCallback)
    
    libmetawear.mbl_mw_acc_enable_acceleration_sampling(s.device.board)
    libmetawear.mbl_mw_acc_start(s.device.board)

    # Configure Gyroscope
    libmetawear.mbl_mw_gyro_bmi160_set_odr(s.device.board, GyroBoschOdr._50Hz)
    libmetawear.mbl_mw_gyro_bmi160_set_range(s.device.board, GyroBoschRange._500dps)
    libmetawear.mbl_mw_gyro_bmi160_write_config(s.device.board)
    
    gyro = libmetawear.mbl_mw_gyro_bmi160_get_rotation_data_signal(s.device.board)
    libmetawear.mbl_mw_datasignal_subscribe(gyro, None, s.gyroCallback)
    
    libmetawear.mbl_mw_gyro_bmi160_enable_rotation_sampling(s.device.board)
    libmetawear.mbl_mw_gyro_bmi160_start(s.device.board)
    
    print("Streaming started...") 
   
def stop_streaming():
    for s in states:
        libmetawear.mbl_mw_acc_stop(s.device.board)
        libmetawear.mbl_mw_acc_disable_acceleration_sampling(s.device.board)
        
        libmetawear.mbl_mw_gyro_bmi160_stop(s.device.board)
        libmetawear.mbl_mw_gyro_bmi160_disable_rotation_sampling(s.device.board)

    # unsubscribe gyro
        gyro = libmetawear.mbl_mw_gyro_bmi160_get_rotation_data_signal(s.device.board)
        libmetawear.mbl_mw_datasignal_unsubscribe(gyro)
        
        acc = libmetawear.mbl_mw_acc_get_acceleration_data_signal(s.device.board)        
        libmetawear.mbl_mw_datasignal_unsubscribe(acc)
        # disconnect
        libmetawear.mbl_mw_debug_disconnect(s.device.board)

        #signal = libmetawear.mbl_mw_acc_get_acceleration_data_signal(s.device.board)
        #libmetawear.mbl_mw_datasignal_unsubscribe(signal)
        #libmetawear.mbl_mw_debug_disconnect(s.device.board)
        s.device.disconnect()


def main():
    os.system('cls')
    print_logo()
    #CC_main_address = scan_connect("main")
    #CC_sec_address = scan_connect("sec")
    CC_main_address ='D3:2D:3E:01:8E:AF'
    CC_sec_address = 'D4:A6:10:C2:43:C7'
    print("Main device:" + CC_main_address)
    add_states(CC_main_address) # todo ini-be a mac-ekkel
    print("Sec device:" + CC_sec_address)
    add_states(CC_sec_address) # todo ini-be a mac-ekkel
    start_streaming()    
    sleep(5)
    stop_streaming()
    
#TODO  - Nem sikerül az object létrehozás "'write without resp async'"
#      - Ha jön adat, akkor sensor fusion, illetve egyéb beállítás vizsgálata, zajszűrés stb.
#      - A két eszköz egymáshoz szinkronizálása, timestamp? Egy adatsor kellene.

if __name__ == "__main__":
    main()
    