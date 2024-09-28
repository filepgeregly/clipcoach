# usage: python data_fuser.py [mac1] [mac2] ... [mac(n)]
from __future__ import print_function
from ctypes import c_void_p, cast, POINTER
from mbientlab.metawear import MetaWear, libmetawear, parse_value, cbindings
from time import sleep, time
from datetime import datetime
from threading import Event
from sys import argv
import csv

states = []

class State:
    # init
    def __init__(self, device):
        self.device = device
        self.callback = cbindings.FnVoid_VoidP_DataP(self.data_handler)
        self.processor = None
        # Create or open the file in append mode
        print('START')
        self.file_name = 'sensordata_' + datetime.now().strftime("%Y%m%d_%H%M%S") + '_' + self.device.address.replace(':','') +'.csv'
        with open(self.file_name, mode='w', newline='') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(['Timestamp', 'Address', 'ACC_X', 'ACC_Y', 'ACC_Z', 'GYRO_X', 'GYRO_Y', 'GYRO_Z'])

    # download data callback fxn
    def data_handler(self, ctx, data):
        values = parse_value(data, n_elem = 2)
        timestamp = time()
        
        with open(self.file_name, mode='a', newline='') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow([timestamp, self.device.address, values[0].x, values[0].y, values[0].z, values[1].x, values[1].y, values[1].z])
         
        
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
        
    
def main():
  
    d = MetaWear('D3:2D:3E:01:8E:AF')
    d.connect()
    print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))
    states.append(State(d))
    
    d = MetaWear('D3:2D:3E:01:8E:AF')
    d.connect()
    print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))
    states.append(State(d))

    # configure
    for s in states:
        print("Configuring %s" % (s.device.address))
        s.setup()

    # start
    for s in states:
        s.start()

    # wait 10 s
    sleep(10.0)

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