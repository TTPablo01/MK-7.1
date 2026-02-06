import evdev
from time import sleep
import datetime as dt
import threading

controller = evdev.InputDevice('/dev/input/event7')

while True:
    
     if controller.read():
         print(controller.read_one())
         sleep(0.1)
