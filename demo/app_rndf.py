# usage: python data_fuser.py [mac1] [mac2] ... [mac(n)]
from __future__ import print_function
from ctypes import c_void_p, cast, POINTER
from mbientlab.metawear import MetaWear, libmetawear, parse_value, cbindings,LedPattern, Const, byref,LedPreset,LedColor
from mbientlab.warble import BleScanner
from time import sleep, time
from datetime import datetime
from threading import Event
from sklearn.preprocessing import StandardScaler,RobustScaler
#from sys import argv
import sys 
import csv
import configparser
import os
import platform
import six
import keyboard
import joblib
import pandas as pd
import numpy as np
import threading
from playsound import playsound
import winsound


from alive_progress import alive_bar

from colorama import Fore, Back, Style

states = []
CC_main = None
CC_sec = None
pre_winner = -1
win_count = 0

threshold = 0.9
window_size = 35
step_size = 5
#ai_model = 'model/clipcoach_first.joblib'
#ai_model = 'model/clipcoach_1DConv_35_5.joblib'
#ai_model = 'model/clipcoach_LSTM_35_5.joblib'
ai_model = 'model/clipcoach_RNDF_35_5.joblib'



buffer = []  # Egy ideiglenes puffer az ablak méretének feltöltésére
result_df = pd.DataFrame() 
cols = ['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z']
status =('Sitting','StandingUP', 'Standing', 'SittingDown')
prev_status = 0


def print_red(string):
   print(Fore.RED + string)

def print_yellow(string):
   print(Fore.YELLOW + string)   
   
def print_green(string):
   print(Fore.GREEN + string)

def print_white(string):
   print(Fore.WHITE + string)

def print_logo():
    print_white('')
    print(r"  ____ _ _        ____                 _          _    ___ ")
    print(r" / ___| (_)_ __  / ___|___   __ _  ___| |__      / \  |_ _|")
    print(r"| |   | | | '_ \| |   / _ \ / _` |/ __| '_ \    / _ \  | | ")
    print(r"| |___| | | |_) | |__| (_) | (_| | (__| | | |  / ___ \ | | ")
    print(r" \____|_|_| .__/ \____\___/ \__,_|\___|_| |_| /_/   \_\___|")
    print(r"          |_|                                              ")
    print("ver 1.0")

def play_audio(audio_mp3):
 playsound(audio_mp3)

def sound(p):
    global prev_status
    #print(f'Prediction: {p}')
    if prev_status != p:
        if p == 2:
         print('StandUP')
         #winsound.Beep(1000, 500)
         thread = threading.Thread(target=play_audio(r'dog.mp3'))
         thread.start()
         #playsound.playsound(r'dog.mp3')
        if p == 0:
         print('SitDOWN')
         #winsound.Beep(1000, 500)
         thread = threading.Thread(target=play_audio(r'cat.wav'))
         thread.start()
         #playsound.playsound(r'cat.wav')
        prev_status = p

def init_streaming_data():
    # Üres DataFrame az ablakok tárolására
    global columns
    columns = [cols for i in range(window_size)]
    
    global result_df
    result_df = pd.DataFrame(columns=columns) 

def check_movement(df_in):

    
    acc_columns = ['acc_x', 'acc_y', 'acc_z']
    gyro_columns = ['gyro_x', 'gyro_y', 'gyro_z']
    cols = ['acc_x', 'acc_y', 'acc_z','gyro_x', 'gyro_y', 'gyro_z']
    #print(df_in[:10])
    
    
    df = pd.DataFrame(df_in,columns = cols) 
    
    #print(df.head())
    scaler = StandardScaler()
    #scaler = RobustScaler()
    #df[:, acc_columns_indices] = scaler.fit_transform(df[:, acc_columns_indices])
    #df.loc[:, acc_columns] = scaler.fit_transform(df.loc[:, acc_columns])
    df[acc_columns] = scaler.fit_transform(df[acc_columns])

    gyro_scaler = StandardScaler()
    #gyro_scaler = RobustScaler()
    #df[:, gyro_columns_indices] = scaler.fit_transform(df[:, gyro_columns_indices])
    #df.loc[:,gyro_columns] = gyro_scaler.fit_transform(df.loc[:,gyro_columns])
    df[gyro_columns] = gyro_scaler.fit_transform(df[gyro_columns])


    
    data_to_scale = df[acc_columns + gyro_columns]

    scaled_data = scaler.fit_transform(data_to_scale)
    
    scaled_data = np.expand_dims(np.array(scaled_data), axis=0)
    
    #RNDF
    scaled_data = scaled_data.reshape(1, -1)
    #df_test = pd.DataFrame(scaled_data, columns=(acc_columns + gyro_columns))
    global pre_winner
    global win_count
    prediction = model.predict(scaled_data) #.argmax(axis=1)
    if 1==1: #prediction.max() > threshold:
        winner = model.predict(scaled_data) #.argmax(axis=1)
        print(f'{winner}')
        #print(Fore.YELLOW + f'{status(winner)}({prediction.max()})' + Style.RESET_ALL )
        #+ f'{status[prediction]}({prediction.max()})' + Style.RESET_ALL)
        
        
        if pre_winner != winner:
            #if winner ==0:
            # print(Fore.YELLOW +f'{prediction[:,0]}'+ Style.RESET_ALL + Fore.GREEN + f',{prediction[:,1]},{prediction[:,2]}')
            #else:
            #  if winner ==1:
            #     print(Fore.GREEN +f'{prediction[:,0]}'+ Fore.YELLOW + f',{prediction[:,1]}' + Fore.GREEN + f',{prediction[:,2]}')
            #  else:
            #    if winner == 2:
            #

            pre_winner = winner        
        #print(f'{prediction[:,0]},{prediction[:,1]},{prediction[:,2]}')
        #pred = prediction.argmax(axis=1)
        

        
        if winner != 1:
           #win_count+=1
           #if win_count>1:
            #print(f'{prediction[:,0]},{prediction[:,1]},{prediction[:,2]}')
            sound(winner)
            win_count = 0
    
   

class State:
    # init
    def __init__(self, device):
        self.device = device
        self.callback = cbindings.FnVoid_VoidP_DataP(self.data_handler)
        self.processor = None
        # Create or open the file in append mode
        #self.file_name = 'clipcoach_' + datetime.now().strftime("%Y%m%d_%H%M%S") + '_' + self.device.address.replace(':','') +'.csv'
        #with open(self.file_name, mode='w', newline='') as file:
        #    writer = csv.writer(file, delimiter=',')
        #    if self.device.address == CC_main: 
        #     writer.writerow(['timestamp','acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z'])
        #    else:
        #     writer.writerow(['timestamp','acc_x','acc_y', 'acc_z'])

    # download data callback fxn
    def data_handler(self, ctx, data):
        values = parse_value(data, n_elem = 2)
        timestamp = time()
        
        #####################################################
        global buffer
        global result_df
        global cols
        global step_size
        global window_size
        #global windowed_data
        windowed_data = np.empty(( window_size, 6))
        
        buffer.append([values[0].x, values[0].y, values[0].z, values[1].x, values[1].y, values[1].z])
        if len(buffer) == window_size:
            #lehet kiértékelni
            buffer_array = np.array(buffer).reshape(window_size, 6)  
            #windowed_data = np.concatenate([windowed_data, buffer_array], axis=0)
            windowed_data = buffer_array
            buffer = buffer[step_size:]
            #print(windowed_data.shape)
            check_movement(windowed_data)
        
        
        #predictions = model.predict(your_input_data)
        
        #with open(self.file_name, mode='a', newline='') as file:
        #        writer = csv.writer(file, delimiter=',')
        #        if device_type =='main':
        #         writer.writerow([timestamp, values[0].x, values[0].y, values[0].z, values[1].x, values[1].y, values[1].z])
        #        else: 
        #         writer.writerow([timestamp, values[0].x, values[0].y, values[0].z])
        # 
        
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
        
        ## params    
        libmetawear.mbl_mw_acc_set_odr(self.device.board, 25.0)  # Frequency in Hz
        # Set the accelerometer range, for example, ±4g
        libmetawear.mbl_mw_acc_set_range(self.device.board, 2.0)  # Range in g
        # Write the settings to the sensor
        libmetawear.mbl_mw_acc_write_acceleration_config(self.device.board)
        
        
        #window_size = 5  # Number of samples to average over
        #processor = libmetawear.mbl_mw_dataprocessor_average_create(acc_signal, window_size, None, lambda context, signal: print("Rolling average processor created"))

        
        
        acc = libmetawear.mbl_mw_acc_get_acceleration_data_signal(self.device.board)
        gyro = libmetawear.mbl_mw_gyro_bmi160_get_rotation_data_signal(self.device.board)
        
        if self.device.address == CC_main:
         device_type = 'main'
        else:
         device_type = 'sec'
        
        if device_type == 'main':
            libmetawear.mbl_mw_dataprocessor_highpass_create(acc, 8, None, fn_wrapper)
            e.wait()
            hp_acc = self.processor
            e.clear()
            
            
            libmetawear.mbl_mw_dataprocessor_average_create(hp_acc, 8, None, fn_wrapper)
            e.wait()
            avg_hp_acc = self.processor
            e.clear()
            
            
            libmetawear.mbl_mw_dataprocessor_highpass_create(gyro, 8, None, fn_wrapper)
            e.wait()
            hp_gyro = self.processor
            e.clear()
            
            
            libmetawear.mbl_mw_dataprocessor_average_create(hp_gyro, 8, None, fn_wrapper)
            e.wait()
            avg_hp_gyro = self.processor
            e.clear()
            
            # create signals variable
            signals = (c_void_p * 1)()
            signals[0] = avg_hp_gyro
            # create acc + gyro signal fuser
            libmetawear.mbl_mw_dataprocessor_fuser_create(avg_hp_acc, signals, 1, None, fn_wrapper)
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
    print_green('Loading AI model...')
    global model
    model = joblib.load(ai_model) 
    init_streaming_data()
    
    global cat
    #cat = AudioSegment.from_file('c:/Users/Gerie/MeatWear/ClipCoach/cat.mp3')
    
    global dog
    #dog = AudioSegment.from_file('c:/Users/Gerie/MeatWear/ClipCoach/dog.mp3')
    
    CC_main, CC_sec = load_ini()    
    
    if CC_main is not None and CC_sec is not None:
        print_red(f"ClipCoach: {CC_main}")
        #print_green(f"Sec ClipCoach: {CC_sec}")
        if not ask_yes_no("Do you want to continue?"):
            CC_main = None
            CC_sec = None
        else:
           d = MetaWear(CC_main)
           d.connect()
           states.append(State(d))
           #d = MetaWear(CC_sec)
           #d.connect()
           #states.append(State(d))
           
    if CC_main is None or CC_sec is None:
        CC_main = scan_connect('main')
       # CC_sec = scan_connect('sec')
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
    print_green("Press ESC to stop streaming!")
    
    with alive_bar(title='Streaming...',monitor =False ,spinner='classic',theme='smooth',elapsed=True, stats=False, bar=None,spinner_length=2) as bar:
      while True:
            sleep(0.1)  # Simulate work being done
            bar()
            if keyboard.is_pressed('esc'):
                print_white("End streaming...")
                break  # Exit the loop when 'Esc' is pressed    
        

    # reset
    print("Reseting devices")
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