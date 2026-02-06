#########################################################################################
#
# Program  : ttv7_1_cpu1.py
# Version  : 7.0.0.1
# Target   : Robbie
#

# Author   : Pablo Cordoba
# Updated  : 5/02/2026 at 09:00 (Thursday)
# Function : Top level module which provides a command processor and motion controller
#            for either the flushing or lancing Mk.7.1 robot.
# Copyright: Tubetech Industrial Ltd. 2023.
#
#robbie External dependencies (Python files):
#            ttv7_mc5005.py
#            ttv7_logging.py
#            ttv7_motors.py
#            ttv7_threads.py
#            ttv7_robot.py
#
#########################################################################################

import os
import sys
import board
import socket
import serial
import logging
import threading
import multiprocessing
import ipaddress
import ttv7_robot
import ttv7_motors as m
import RPi.GPIO as GPIO
import adafruit_icm20x
import numpy as np
import math
from datetime import datetime
from time import sleep


def system_initialisation():
    global robbie

    
    # Set the vehicle driving light (4 x white LED strips) to ON.
    robbie.system_message = "SUPERVISORY LAMP TEST (WHITE)..."
    GPIO.output(DRIVING_LIGHTS, GPIO.HIGH)
    sleep(1)
    GPIO.output(DRIVING_LIGHTS, GPIO.LOW)
        
    
    # Initialise motors
    m.stop_robot()
    m.terminate_motors()
    sleep(1)
    m.initialise_motors()
    robbie.system_message = "Motors initialised successfully."
    sleep(1)

    # Level the robot
    set_robot_level()
    flash_lights()
    
    # Confirmed initialised, so update the model...
    robbie.current_state = 'INITIALISED'
    robbie.system_message = "Robot initialised."
    robbie.initialised = True
    sleep(1)



 
def run_control_program():
    global robbie, connected, s
    
    SERVER = '192.168.0.60'     # This is the server, CPU1 - this one!
    PORT = 22001
    ADDR = (SERVER, PORT)
    
    # Create socket for the Control Client, Pi4(2) client and Server to use...
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Using TCP.
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Manage any binding errors...
    try:
        s.bind(ADDR)
    except socket.error:
        robbie.system_message = "Socket bind failed."

    s.listen()
    
    # Enable all motors and set their initial operation mode (velocity not position).
    robbie.system_message = "Initialising the V7 Robot. All wheel levers will be set to their currently located positions."
    robbie.current_command = 'INITIALISING'
    
    
    robbie.system_message = "Awaiting connection request from TT robot controller..."
    
    
    while True:
        (conn, addr) = s.accept() # Blocking call; this loop runs for each new client connection.
        connected = True
        robbie.system_message = f"[NEW CONNECTION] {addr} connected. {threading.activeCount()-1}"
        print(robbie.system_message)
        
        print(conn,addr)
        
        # These IP addresses are hard coded - very fixed indeed as any deviation will render the robot useless.
        if '192.168.0.70' in str(conn):
            robbie.cpu2_connected = True
        if '192.168.0.80' in str(conn):
            robbie.ctrl_connected = True

            
        filtered_msg = ''    
        
        msg_route_thread = threading.Thread(target = route_messages, args=(conn, addr))
        msg_route_thread.start()
         
        
def route_messages(conn, addr):
    global robbie, connected
    # This method provides message routing depending upon the client who just connected (indicated in the message prefix e.g. 'ADMN').
    #e clients are: Control Client (CTRL)
    
    print("\n Route thread started \n")
    
    connected = True
    try:
        while connected:
            # Waiting for messages (this is a blocking call and other threads will be running.)
            raw_data = conn.recv(256) # custom command messages can be very long!
            data = raw_data.decode()
            raw_data = ""
            x = len(raw_data)
            #print(f"RAW_DATA_LENGTH: -------------------------------------> {x}")
            data = data.strip(' ,')
            
            msg_prefix = data[0:4]
            filtered_msg = data[5:]

            
            # Each of these procedure calls proceses one message. (None from CPU1 of course!)
            def controller():
                if msg_prefix == "CTRL":
                    robbie.ctrl_latest_message = f"{msg_prefix}~ {filtered_msg}"
                    process_ctrl_messages(conn, filtered_msg)
                    
            controller_route_thread = threading.Thread(target = controller)
            controller_route_thread.start()
#                 controller_route_thread.join()
                
            
            def admin():
                if msg_prefix == "ADMN":
                    robbie.admn_latest_message = f"{msg_prefix}~ {filtered_msg}"
                    process_admn_messages(filtered_msg)       
            
            admin_route_thread = threading.Thread(target = admin)
            admin_route_thread.start()
    #                 admin_route_thread.join()
                
    except socket.error as msg:
        print(msg)
        logging.exception("Control message command failed: ")
        
    except KeyboardInterrupt:
        connected = False
        robbie.system_message = 'Server program was terminated on the robot.'
        
    
    

def process_admn_messages(msg):
    global connected, robbie, abort, command_running, oscillate
    
    robbie.admn_latest_message = msg
    
    print(f"ADMN~ ---> {msg}")
    robbie.current_command = msg
    robbie.amdn_connected = True
    
    if 'STOP' in msg:
        robbie.current_command = 'STOPPED'
        abort = True
        command_running = False
        oscillate = False
        
        sleep(0.1)
        
        m.stop_robot()
        
        if robbie.head_initialised:
            m.stop_head()
    
    
    elif 'PAUSE' in msg:
        robbie.current_command = 'PAUSE'
        m.halt_motors()
        
        if robbie.head_initialised:
            m.halt_head_motors()
            
        robbie.paused = True
        
    elif 'RESUME' in msg:
        robbie.current_command = 'RESUME'
        m.unhalt_motors()
        
        if robbie.head_initialised:
            m.unhalt_head_motors()
            
        robbie.paused = False
        
    elif 'OSCILLATE' in msg:
        robbie.current_command = 'OSCILLATE'
        
        msg = msg.split("~")
        anglesmsg = msg[1].split(",")
        
        if msg[1] == "STOP":
            
            oscillate = False
            
        else:
            
            anglesmsg = msg[1].split(",")
            oscillate = True

            StartAngle = int(anglesmsg[0])
            FinishAngle = int(anglesmsg[1])

            oscillate_lance(StartAngle, FinishAngle)

    

def process_ctrl_messages(conn, msg):
    global connected, robbie,  abort, command_running, StartPosition, FinishPosition
    
    abort = False
    
    robbie.ctrl_latest_message = msg
    
    print(f"CTRL~ ---> {msg}")
    
    robbie.current_command = msg
    robbie.ctrl_connected = True
    
    # A 'normal' command not prefixed with 'CC', so process the message received as a single control command...
    if not (msg[0]=='C' and msg[1]=='C'):
        
        if 'L-TOGGLE' in msg:
            robbie.current_command = 'TOGGLE_LIGHTS'
            if GPIO.input(DRIVING_LIGHTS) == 0:
                GPIO.output(DRIVING_LIGHTS, GPIO.HIGH)
                robbie.driving_lights = ON
            elif GPIO.input(DRIVING_LIGHTS) == 1:
                GPIO.output(DRIVING_LIGHTS, GPIO.LOW)
                robbie.driving_lights = OFF
        
        elif not command_running:
            
            if 'FASTER' in msg:
                robbie.current_command = 'FASTER'
                faster_responses = {"FORWARD", "REVERSE", "LEFT", "RIGHT", "FASTER", "SLOWER", "NO-COMMAND"}
                if msg in faster_responses:
                    if robbie.speed < 4000:
                        robbie.speed += 500
                        #m.stop_robot()
                        print("Speeding up to {sp}".format(sp=robbie.speed))
                        if robbie.current_command == 'FORWARD':
                            m.forward(robbie.speed)
                        elif robbie.current_command == 'REVERSE':
                            m.reverse(robbie.speed)
                        elif robbie.current_command == 'LEFT':
                            m.left(robbie.speed)
                        elif robbie.current_command == 'RIGHT':
                            m.right(robbie.speed)
                    reply = 'ACK~SPEED:' + str(robbie.speed)
                    conn.send(reply.encode())  # Send this value back to the controller so it can display the speed in cm/s.
            
            elif 'SLOWER' in msg:
                robbie.current_command = 'SLOWER'
                slower_responses = {"FORWARD", "REVERSE", "LEFT", "RIGHT", "FASTER", "SLOWER", "NO-COMMAND"}
                if msg in slower_responses:
                    if robbie.speed > 500:
                        robbie.speed -= 500
                        #m.stop_robot()
                        print("Slowing down to {sp}".format(sp=robbie.speed))
                        if robbie.current_command == 'FORWARD':
                            m.forward(robbie.speed)
                        elif robbie.current_command == 'REVERSE':
                            m.reverse(robbie.speed)
                        elif robbie.current_command == 'LEFT':
                            m.left(robbie.speed)
                        elif robbie.current_command == 'RIGHT':
                            m.right(robbie.speed)
                    reply = 'ACK~SPEED:' + str(robbie.speed)
                    conn.send(reply.encode())  # Send this value back to the controller so it can display the speed in cm/s.
            
            

            elif 'IMU' in msg:
                
                robbie.current_command = 'IMU'
                reply = (str(robbie.roll) + ',' + str(robbie.pitch) + ',' + str(robbie.yaw))
                conn.send(reply.encode())
                print(reply)

                
            elif 'LEFT' in msg:
                
                robbie.current_command = 'LEFT'
                m.left(robbie.speed)
            
            elif 'L-CLIMB' in msg:
                global TubeSize

                robbie.current_command = 'LEFT_CLIMB'

                msg = msg.split(",")
                TubeSize = msg[1]

                left_climb(TubeSize)
            
            elif 'RIGHT' in msg:
                
                robbie.current_command = 'RIGHT'
                m.right(robbie.speed)
            
            elif 'R-CLIMB' in msg:
 

                robbie.current_command = 'RIGHT_CLIMB'

                msg = msg.split(",")
                TubeSize = msg[1]

                right_climb(TubeSize)
                
            
            elif 'REVERSE' in msg:
                
                robbie.current_command = 'REVERSE'
                m.reverse(robbie.speed)
            
            elif 'RVRS-BC' in msg:
                
                robbie.current_command = 'RVRS-BC'
                reverse_baffle_climb()
            
            elif 'FORWARD' in msg:
                
                robbie.current_command = 'FORWARD'
                m.forward(robbie.speed)
            elif 'FRWD-BC' in msg:
                
                robbie.current_command = 'FRWD-BC'
                forward_baffle_climb()
      
            elif 'RSIDE-UP' in msg:
                
                robbie.current_command = 'RIGHT_AXLES_UP'
                ru_conditions = [(robbie.lever_09["CURRENT_AXLE_LIFT"] + robbie.cc_step_size) <= robbie.lever_09["MAX_AXLE_LIFT"],
                                 (robbie.lever_0A["CURRENT_AXLE_LIFT"] + robbie.cc_step_size) <= robbie.lever_0A["MAX_AXLE_LIFT"],
                                 (robbie.lever_0B["CURRENT_AXLE_LIFT"] + robbie.cc_step_size) <= robbie.lever_0B["MAX_AXLE_LIFT"],
                                 (robbie.lever_0C["CURRENT_AXLE_LIFT"] + robbie.cc_step_size) <= robbie.lever_0C["MAX_AXLE_LIFT"]]
                if all(ru_conditions):
                    m.axles_raise_right_side(robbie.cc_step_size)
                    robbie.lever_09["CURRENT_AXLE_LIFT"] += robbie.cc_step_size
                    robbie.lever_0A["CURRENT_AXLE_LIFT"] += robbie.cc_step_size
                    robbie.lever_0B["CURRENT_AXLE_LIFT"] += robbie.cc_step_size
                    robbie.lever_0C["CURRENT_AXLE_LIFT"] += robbie.cc_step_size
                    
            elif 'LSIDE-DN' in msg:
                
                robbie.current_command = 'LEFT_AXLES_DOWN'
                ld_conditions = [(robbie.lever_05["CURRENT_AXLE_LIFT"] - robbie.cc_step_size) >= 0,
                                 (robbie.lever_06["CURRENT_AXLE_LIFT"] - robbie.cc_step_size) >= 0,
                                 (robbie.lever_07["CURRENT_AXLE_LIFT"] - robbie.cc_step_size) >= 0,
                                 (robbie.lever_08["CURRENT_AXLE_LIFT"] - robbie.cc_step_size) >= 0]
                if all(ld_conditions):
                    m.axles_lower_left_side(robbie.cc_step_size)
                    robbie.lever_05["CURRENT_AXLE_LIFT"] -= robbie.cc_step_size
                    robbie.lever_06["CURRENT_AXLE_LIFT"] -= robbie.cc_step_size
                    robbie.lever_07["CURRENT_AXLE_LIFT"] -= robbie.cc_step_size
                    robbie.lever_08["CURRENT_AXLE_LIFT"] -= robbie.cc_step_size           
                    
            elif 'RSIDE-DN' in msg:
                
                robbie.current_command = 'RIGHT_AXLES_DOWN'               
                rd_conditions = [(robbie.lever_09["CURRENT_AXLE_LIFT"] - robbie.cc_step_size) >= 0,
                                 (robbie.lever_0A["CURRENT_AXLE_LIFT"] - robbie.cc_step_size) >= 0,
                                 (robbie.lever_0B["CURRENT_AXLE_LIFT"] - robbie.cc_step_size) >= 0,
                                 (robbie.lever_0C["CURRENT_AXLE_LIFT"] - robbie.cc_step_size) >= 0]
                if all(rd_conditions):
                    m.axles_lower_right_side(robbie.cc_step_size)
                    robbie.lever_09["CURRENT_AXLE_LIFT"] -= robbie.cc_step_size
                    robbie.lever_0A["CURRENT_AXLE_LIFT"] -= robbie.cc_step_size
                    robbie.lever_0B["CURRENT_AXLE_LIFT"] -= robbie.cc_step_size
                    robbie.lever_0C["CURRENT_AXLE_LIFT"] -= robbie.cc_step_size
                    
            elif 'LSIDE-UP' in msg:
                
                robbie.current_command = 'LEFT_AXLES_UP'
                lu_conditions = [(robbie.lever_05["CURRENT_AXLE_LIFT"] + robbie.cc_step_size) <= robbie.lever_05["MAX_AXLE_LIFT"],
                                 (robbie.lever_06["CURRENT_AXLE_LIFT"] + robbie.cc_step_size) <= robbie.lever_06["MAX_AXLE_LIFT"],
                                 (robbie.lever_07["CURRENT_AXLE_LIFT"] + robbie.cc_step_size) <= robbie.lever_07["MAX_AXLE_LIFT"],
                                 (robbie.lever_08["CURRENT_AXLE_LIFT"] + robbie.cc_step_size) <= robbie.lever_08["MAX_AXLE_LIFT"]]
                if all(lu_conditions):
                    m.axles_raise_left_side(robbie.cc_step_size)
                    robbie.lever_05["CURRENT_AXLE_LIFT"] += robbie.cc_step_size
                    robbie.lever_06["CURRENT_AXLE_LIFT"] += robbie.cc_step_size
                    robbie.lever_07["CURRENT_AXLE_LIFT"] += robbie.cc_step_size
                    robbie.lever_08["CURRENT_AXLE_LIFT"] += robbie.cc_step_size
                
            elif 'TILTR' in msg:
                robbie.current_command = 'TILT RIGHT'
                tilt_right()
            
            elif 'TILTL' in msg:
                robbie.current_command = 'TILT LEFT'
                tilt_left()
                
            elif 'SAVEMOTORPOS' in msg:
                robbie.current_command = 'SAVE MOTOR POSITION'
                reply = str(m.Motor_1.getPosition())
                conn.send(reply.encode())
                print(reply)

    
            # Manual head control
            
            
            elif 'SLIDEANGLE' in msg:
                msg = msg.split(",")
                Angle = msg[1]

                slide_out_distance(Angle)
            
            elif 'SLIDEL' in msg:
                m.slide_motor_left()
            
            elif 'SLIDER' in msg:
                m.slide_motor_right()

            elif 'ROLLANGLE' in msg:
                msg = msg.split(",")
                Angle = msg[1]

                roll_to_angle(Angle)
            
            elif 'ROLLCLOCK' in msg:
                m.roll_motor_clockwise()
            
            elif 'ROLLANTICLOCK' in msg:
                m.roll_motor_anticlockwise()

            elif 'PITCHANGLE' in msg:
                msg = msg.split(",")
                Angle = msg[1]

                pitch_to_angle(Angle)
                
            elif 'PITCHUP' in msg:
                m.pitch_motor_up()
            
            elif 'PITCHDOWN' in msg:
                m.pitch_motor_down()
            
            elif 'HEAD_INIT' in msg:
                m.terminate_head_motors()
                m.initialise_head_motors()
                robbie.system_message = "Head motors initialised successfully."
                flash_lights()
                
                robbie.head_initialised = True
            
            elif 'HOME_HEAD' in msg:
                home_head_motors()
                
            elif 'MANUAL_HOME' in msg:
                manual_home_head_motors()
                
            elif 'SLIDE_HOME' in msg:
                slide_home()
            
            elif 'ROLL_HOME' in msg:
                roll_home()
            
            elif 'PITCH_HOME' in msg:
                pitch_home()
                
            elif 'LANCE_ANGLE_A' in msg:
                msg = msg.split(",")

                SlideDistance = int(msg[1])
                RollAngle = int(msg[2])

                Angle_A(SlideDistance, RollAngle)
            
            elif 'LANCE_ANGLE_B' in msg:
                msg = msg.split(",")

                SlideDistance = int(msg[1])
                RollAngle = int(msg[2])

                Angle_B(SlideDistance, RollAngle)
                
            elif 'HEAD_SENSORS' in msg:
                 
                robbie.current_command = 'HEAD SENSORS READING'
                reply = (str(robbie.slide_motor_homed) + ',' + str(robbie.roll_motor_homed) + ',' + str(robbie.pitch_motor_homed))
                conn.send(reply.encode())
                print(reply)
                
                
                
                
            # Automatic mode command
            
            elif 'AS' in msg:
                
                split_msg = msg.split("~")
                print(split_msg)
                
                
                if split_msg[1]=='F':
                    speed = "FAST"
                    
                
                elif split_msg[1]=='M':
                    speed = "MEDIUM"
                
                    
                elif split_msg[1]=='S':
                    speed = "SLOW"
                    
                    
                
                if split_msg[2] == 'L':
                       
                    direction = "LEFT"
                       
                elif split_msg[2] == 'R':
                    
                    direction = "RIGHT"
                        
                
                if ',' in split_msg[3]:
                    
                    length_split = split_msg[3].split(',')
                    
                    StartPosition = int(length_split[0])
                    FinishPosition = int(length_split[1])
                    
                    length = -1
                
                else:
                    
                    length = int(split_msg[3])
                    
                piperuns = int(split_msg[4])

                pipesize = split_msg[5]
                
                runsPerPipe = split_msg[6]
                    
                automatic_run(speed,direction,length,piperuns,pipesize,runsPerPipe)
                
            # Levers commands
                
            elif 'RAISE1' in msg:
                axle_1_manual_raising()
                    
            elif 'LOWER1' in msg:
                axle_1_manual_lowering()
                
            elif 'RAISE2' in msg:
                axle_2_manual_raising()
                    
            elif 'LOWER2' in msg:
                axle_2_manual_lowering()
                    
            elif 'RAISE3' in msg:
                axle_3_manual_raising()
                    
            elif 'LOWER3' in msg:
                axle_3_manual_lowering()
                
            elif 'RAISE4' in msg:
                axle_4_manual_raising()
                    
            elif 'LOWER4' in msg:
                axle_4_manual_lowering()
                
            elif 'LEVEL' in msg:
                set_robot_level()
                flash_lights()
                            
            elif 'FULL_INIT' in msg: #CHANGED FROM INIT AS PREVIOUSLY USED IN 'HEAD_INIT'
                # The delay of 8 seconds here gives the user time to reposition the robot or reset its wheels orthogonal to the pipes in the pipe wells.
                print("Re-initialising the V7 Robot. Set all wheel levers to their zeroed positions!")
                robbie.current_command = 'RE-INITIALISING'
                m.stop_robot()
                m.terminate_motors()
                sleep(5)
                m.initialise_motors()
                reset_levers_model_values()
                flash_lights()
                
            elif 'MOTORS_STATUS' in msg:
                
                robbie.current_command = 'MOTORS STATUS'
                m.get_all_motors_status()
                reply = str(m.get_all_motors_status())
                conn.send(reply.encode())
                print(reply)
        
                
            elif 'EXIT' in msg: # Client wants to exit the connection, but which client?
                connected = False
                robbie.current_command = 'EXIT'
                robbie.ctrl_connected = False
                #reply = 'ACK: ' + msg
                #conn.send(reply.encode())
                print("The Operator has terminated the robot control program.")
                m.stop_robot()
                m.terminate_motors()
                conn.close()
                #sys.exit()
            
            else:
                # An unknown command is received.
                print(f'[UNKNOWN COMMAND] {msg} >>>')
                logging.warning('[UNKNOWN COMMAND] %s >>>', msg)
                
            # Set the last_command value to the one just processed...
            robbie.last_command = robbie.current_command
            
    
 
#### LIGHTS FUNCTION ####
                                       
            
def flash_lights():
    
    if GPIO.input(DRIVING_LIGHTS) == 0:

        GPIO.output(DRIVING_LIGHTS, GPIO.HIGH)
        sleep(0.2)
        GPIO.output(DRIVING_LIGHTS, GPIO.LOW)
        sleep(0.1)
        GPIO.output(DRIVING_LIGHTS, GPIO.HIGH)
        sleep(0.2)
        GPIO.output(DRIVING_LIGHTS, GPIO.LOW)
        


    elif GPIO.input(DRIVING_LIGHTS) == 1:
        
        GPIO.output(DRIVING_LIGHTS, GPIO.LOW)
        sleep(0.1)
        GPIO.output(DRIVING_LIGHTS, GPIO.HIGH)
        sleep(0.2)
        GPIO.output(DRIVING_LIGHTS, GPIO.LOW)
        sleep(0.1)
        GPIO.output(DRIVING_LIGHTS, GPIO.HIGH)
        
    
    
    
#### IMU FUNCTION ####
    


def get_roll_pitch_yaw_data():
    global robbie, i2c, icm
    
    """ Thread procedure that collects the Roll, pitch and Yaw data from the IMU chip on the sensors interface board """
    # Only interested in Roll at present and only 60 roll lookup values in list at prresent - this is the most roll the robot can tolerate!
    icm_roll_value = 0
    icm_pitch_value = 0
    icm_yaw_value = 0
    
    while True:
        
        N = 100
        icm_roll = np.zeros((N,),dtype=float)
     
        for i in range(N):
        
            icm_roll[i] = icm.acceleration[0]
    
    
        icm_roll_avg = np.mean(icm_roll)
        
        icm_roll_value = icm_roll_avg * 100
        icm_pitch_value = icm.acceleration[1] * 100
        icm_yaw_value = icm.acceleration[2] * 100
        
        # Roll is used by the LEFT/RIGHT climbing algorithm to determine how the 'turn' left or right is progressing.
        
        # Store the latest value of roll in Robbie's object model.
        robbie.roll = int(icm_roll_value)
        robbie.pitch = int(icm_pitch_value)
        robbie.yaw = int(icm_yaw_value)
        
        
        

#### LANCE SENSORS FUNCTION ####

def read_head_sensors():
    global robbie
    
    while True:

        if GPIO.input(SLIDE_SENSOR):
                    robbie.slide_motor_homed = False
        else:
            robbie.slide_motor_homed = True

        
        if GPIO.input(ROLL_SENSOR):
            robbie.roll_motor_homed = True
        else:
            robbie.roll_motor_homed = False

            
        if GPIO.input(PITCH_SENSOR):
            robbie.pitch_motor_homed = True
        else:
            robbie.pitch_motor_homed = False
            
#         print(robbie.slide_motor_homed, robbie.roll_motor_homed, robbie.pitch_motor_homed)

        sleep(0.1)


#### ROBOT LEVELLING ####
    
def tilt_right():
    
    if robbie.tilt_steps["CURRENT_TILT"] < robbie.tilt_steps["MAX_RIGHT_TILT"]:
        m.axles_lower_right_side(150)
        m.axles_raise_left_side(150)
        
        robbie.tilt_steps["CURRENT_TILT"] += 1
    
def tilt_left():
    
    if robbie.tilt_steps["CURRENT_TILT"] > robbie.tilt_steps["MAX_LEFT_TILT"]:
        m.axles_lower_left_side(150)
        m.axles_raise_right_side(150)
        
        robbie.tilt_steps["CURRENT_TILT"] -= 1

def set_robot_level() -> bool:
    """ Sets the robot to as close to horizontal as it can get whenever this function is called. """
    # Uses the real IMU values (which are probably degrees), not the quantised values! 
    horizontal = False
    # IMU value is 0 => level, do nothing.

    while not horizontal:
               
        # IMU roll negative => raise the left side
        while robbie.roll > -10:
            
            m.axles_lower_right_side(robbie.mm_step_size)
            m.axles_raise_left_side(robbie.mm_step_size)
            sleep(0.2)
            
        horizontal = True

        # IMU roll positive => raise the right side.
        while robbie.roll < -15:                                                                                                                                                                                                                           
           
            m.axles_lower_left_side(robbie.mm_step_size)
            m.axles_raise_right_side(robbie.mm_step_size)
            sleep(0.2)
            
        horizontal = True

    return(horizontal)





#### AUTOMATIC RUN FUNCTIONS ####
    
def reposition_robot_to_start_position():
    
    CurrentMotorPos = m.Motor_1.getPosition()
    
    sleep(1)
        
    if CurrentMotorPos < StartPosition:
        
        m.reverse(robbie.flush_speed)
        
        while m.Motor_1.getPosition() < StartPosition:
            if abort == True: # Check to see if someone wants the robot stopped by putting their hand in front (<10cm) of the rear LIDAR unit.
                m.stop_robot()
                robbie.system_message = "Aborting Automatic Sequence command"
                break
            
            sleep(0.1)
            
        m.stop_robot()
    
    elif CurrentMotorPos > StartPosition:
        
        m.forward(robbie.flush_speed)
        
        while m.Motor_1.getPosition() > StartPosition:
            if abort == True: # Check to see if someone wants the robot stopped by putting their hand in front (<10cm) of the rear LIDAR unit.
                m.stop_robot()
                robbie.system_message = "Aborting Automatic Sequence command"
                break
            
            sleep(0.1)
            
        m.stop_robot()

    sleep(3)
        
    
def automatic_run(speed, direction, length, piperuns, pipesize, runsPerPipe):
    global abort, command_running
    abort = False
    command_running = True
    
    
    piperuns = piperuns - 2
    
    runsPerPipe = int(runsPerPipe)

# Select speed of the automatic run   
    if speed == "FAST":
        robbie.flush_speed = 3000
        odometry_steps = 10.35
    
    elif speed == "MEDIUM":
        robbie.flush_speed = 2000
        odometry_steps = 6.9

    elif speed == "SLOW":
        robbie.flush_speed = 1000
        odometry_steps = 3.45


# Select length of the automatic run
        
    overall_run_length = length
    print(f"Chamber is {overall_run_length}cm long")
        
        
    if length == -1:
        
        PosDifference = StartPosition - FinishPosition
        
        reposition_robot_to_start_position()
        
        if not abort:
            for n in range(0, piperuns):
                for i in range(0, runsPerPipe):
                    
                    ### FOWRWARD ###
                    
                    CurrentPosition = m.Motor_1.getPosition()
              
                    m.forward(robbie.flush_speed)
                    robbie.system_message = 'FORWARD'
                    
                    
                    while(m.Motor_1.getPosition() > (CurrentPosition - PosDifference)):
                        if abort == True: # Check to see if someone wants the robot stopped by pressing the STOP button.
                            
                            m.stop_robot()
                                
                            robbie.system_message = "Aborting Automatic Sequence command"
                            break

                        sleep(0.5)
                        print(m.Motor_1.getPosition(),(CurrentPosition + PosDifference))
                     
                    robbie.system_message = 'STOPPED'
                    m.stop_robot()
                    
                        
                    set_robot_level()
                    sleep(0.5)
                    
                    
                    if not abort:
                     
                        ### REVERSE IN THE CURRENT TUBE ###
                        m.reverse(robbie.flush_speed)
                        robbie.system_message = 'REVERSE'
                        odom_position = 0
                        

                        while (m.Motor_1.getPosition() < (CurrentPosition) - 300):
                            if abort == True: # Check to see if someone wants the robot stopped by pressing the STOP button.
                                
                                m.stop_robot()
                                    
                                robbie.system_message = "Aborting Automatic Sequence command"
                                break
                            
                            
                            sleep(0.5)
                        
                        robbie.sytem_message = 'STOPPED'
                        m.stop_robot()


                if not abort:
                
                    if(n < (piperuns - 1)):
    
                        if (direction == 'RIGHT' and not abort):
                            right_climb(pipesize)
                            command_running = True
                            print("AS-RIGHT_CLIMB")
                        elif (direction == 'LEFT' and not abort):
                            left_climb(pipesize)
                            command_running = True
                            print("AS-LEFT_CLIMB")
                            
                        robbie.system_message = 'STOPPED'
                        sleep(0.5)
                            
                
        if not abort:    
            for n in range(0, (piperuns - 1)):  # This moves the robot to the start position once all the pipes have been cleaned.
                if direction == 'RIGHT':
                    left_climb(pipesize)
                    command_running = True
                    print("AS-LEFT_CLIMB")
                    
                elif direction == 'LEFT':
                    right_climb(pipesize)
                    command_running = True
                    print("AS-RIGHT_CLIMB")
                    
                sleep(1) 
        
            
        
    else:

        
        if not abort:
            for n in range(0, piperuns):
                for i in range(0, runsPerPipe):
              
                    m.forward(robbie.flush_speed)
                    robbie.system_message = 'FORWARD'
                    
                    
                    odom_position = 0
                    
                    while((overall_run_length - odom_position) > 60):
                        if abort == True: # Check to see if someone wants the robot stopped by pressing the STOP button.
                            
                            m.stop_robot()
                                
                            robbie.system_message = "Aborting Automatic Sequence command"
                            break
                        
     
                        if not robbie.paused:
                            odom_position += odometry_steps

                        sleep(0.5)
                     
                    robbie.system_message = 'STOPPED'
                    m.stop_robot()
                    
                    set_robot_level()
                    sleep(0.5)
                    
                    
                    if not abort:
                     
                        # Reverse, and back down the current tube...
                        m.reverse(robbie.flush_speed)
                        robbie.system_message = 'REVERSE'
                        odom_position = 0
                        sleep(1)


                        while((overall_run_length - odom_position) > 60):
                            if abort == True: # Check to see if someone wants the robot stopped by pressing the STOP button.
                                
                                m.stop_robot()
                                    
                                robbie.system_message = "Aborting Automatic Sequence command"
                                break
                            
                            if not robbie.paused:
                                odom_position += odometry_steps
                            
                            sleep(0.5)
                        
                        robbie.sytem_message = 'STOPPED'
                        m.stop_robot()


                if not abort:
                
                    if(n < (piperuns - 1)):
    
                        if (direction == 'RIGHT' and not abort):
                            right_climb(pipesize)
                            command_running = True
                            print("AS-RIGHT_CLIMB")
                        elif (direction == 'LEFT' and not abort):
                            left_climb(pipesize)
                            command_running = True
                            print("AS-LEFT_CLIMB")
                            
                        robbie.system_message = 'STOPPED'
                        sleep(0.5)
                        
                
        if not abort:    
            for n in range(0, (piperuns - 1)):  # This moves the robot to the start position once all the pipes have been cleaned.
                if direction == 'RIGHT':
                    left_climb(pipesize)
                    command_running = True
                    print("AS-LEFT_CLIMB")
                    
                elif direction == 'LEFT':
                    right_climb(pipesize)
                    command_running = True
                    print("AS-RIGHT_CLIMB")
                    
                sleep(1)           
    
            
    flash_lights()
    
    command_running = False




#### PIPE CLIMBING FUNCTIONS ####

  

  
def left_climb(TubeSize):
    global abort, command_running
    abort = False
    command_running = True

    if TubeSize == "S":
        ClimbTimeLimit = 5
        RollThreshold = -150

    elif TubeSize == "M":
        ClimbTimeLimit = 15
        RollThreshold = -200

    elif TubeSize == "B":
        ClimbTimeLimit = 25
        RollThreshold = -300
    
    # Set the speed to move the robot rightwards as though on flat ground.
    m.stop_robot()
    sleep(0.25)
    RePosition_cmd()
    sleep(0.25)
    
    n = 0
    
    while not abort and n < 1:
        
        # Only allow this left turn if robbie is close to level...
        if (abs(robbie.roll) <= 100):
            m.left_1_2(robbie.CLIMB_SPEED)                          # TL
            sleep(0.25)                                            #
            m.axles_raise_left_side_climb(robbie.cc_step_size * 2)    # LU, LU
            sleep(0.5)
            m.axles_raise_right_side_climb(robbie.cc_step_size * 2)   # RU, RU
            m.axles_raise_left_side_climb(robbie.cc_step_size)        # LU
            m.left_3_4(robbie.CLIMB_SPEED)
            
            ClimbCount = 0
            while(robbie.roll > RollThreshold and ClimbCount < ClimbTimeLimit):
                sleep(0.1)
                ClimbCount += 1
            sleep(1)
            
            m.stop_robot()
            m.left_3_4(robbie.CLIMB_SPEED)
            m.right_1_2(robbie.CLIMB_SPEED)
            m.axles_lower_left_side_climb(robbie.cc_step_size * 3)    # LD, LD
            m.axles_lower_right_side_climb(robbie.cc_step_size * 2)   # RD, RD
            sleep(1)
         
            n += 1
    
    m.stop_robot()                                          # All wheels stopped.    
    sleep(0.25)
    RePosition_cmd()
    sleep(0.25)
    set_robot_level()
    flash_lights()
    
    command_running = False
    

def right_climb(TubeSize):
    global abort, command_running 
    abort = False
    command_running = True 
    
    if TubeSize == "S":
        ClimbTimeLimit = 5
        RollThreshold = 150

    elif TubeSize == "M":
        ClimbTimeLimit = 15
        RollThreshold = 200

    elif TubeSize == "B":
        ClimbTimeLimit = 25
        RollThreshold = 300
   
    # Instrumented version of right_climb(TubeSize) intended to prove that the IMU is working OK and is actually useful!
    # Set the speed to move the robot rightwards as though on flat ground.
    m.stop_robot()
    sleep(0.25)
    RePosition_cmd()
    sleep(0.25)
   
    n = 0

    while not abort and n < 1:
       
        if (abs(robbie.roll) <= 100):
            m.right_3_4(robbie.CLIMB_SPEED)                         # TR - wheels turning right now...
            sleep(0.25)
            m.axles_raise_right_side_climb(robbie.cc_step_size * 2)   # RU, RU
            sleep(0.5)
            m.axles_raise_left_side_climb(robbie.cc_step_size * 2)    # LU, LU
            m.axles_raise_right_side_climb(robbie.cc_step_size)       # RU
            m.right_1_2(robbie.CLIMB_SPEED)
            
            ClimbCount = 0
            while(robbie.roll < RollThreshold and ClimbCount < ClimbTimeLimit):
                sleep(0.1)
                ClimbCount += 1
            sleep(1)
            
            n += 1
        
            m.stop_robot()
            m.left_3_4(robbie.CLIMB_SPEED)
            m.right_1_2(robbie.CLIMB_SPEED)
            m.axles_lower_right_side_climb(robbie.cc_step_size * 3)   # RD, RD
            m.axles_lower_left_side_climb(robbie.cc_step_size * 2)    # LD, LD 
            sleep(1)

    m.stop_robot()                                          # All wheels stopped.
    sleep(0.25)
    RePosition_cmd()
    sleep(0.25)
    set_robot_level()
    flash_lights()
    
    command_running = False
      
                                        # All wheels stopped.

def RePosition_cmd():
    """ This command should end with a call to set_robot_level() because although the wheels are now set into the tubes
        after the reposition action the robot is not necessarily level.  Correct when set_robot_level() is tested.
    """
    
    global abort
    
    n=0
    print("RP COMMAND CALLED.")
    
    while n < 3 and abort == False:
            m.forward(robbie.CLIMB_SPEED)
            sleep(0.75)
            m.stop_robot()
            m.reverse(robbie.CLIMB_SPEED)
            sleep(0.75)
            m.stop_robot()
            n += 1
            
            

#### LEVERS MOVEMENT FUNCTIONS ####



def axle_1_raising():
    robbie.current_command = 'AXLE_1_RAISING'
    raise1_conditions = [(robbie.lever_08["CURRENT_AXLE_LIFT"] + robbie.hl_step_size) <= robbie.lever_08["MAX_AXLE_LIFT"],
                         (robbie.lever_09["CURRENT_AXLE_LIFT"] + robbie.hl_step_size) <= robbie.lever_09["MAX_AXLE_LIFT"]]
    if all(raise1_conditions):
        m.Motor_2.setTargetVelocity(3500)
        m.Motor_3.setTargetVelocity(-3500)
        m.axle_1_raise(robbie.hl_step_size)
        robbie.lever_08["CURRENT_AXLE_LIFT"] += robbie.hl_step_size
        robbie.lever_09["CURRENT_AXLE_LIFT"] += robbie.hl_step_size
        sleep(1)
        m.Motor_2.setTargetVelocity(0)
        m.Motor_3.setTargetVelocity(-0)
        
def axle_1_manual_raising():
    robbie.current_command = 'AXLE_1_RAISING'
    raise1_conditions = [(robbie.lever_08["CURRENT_AXLE_LIFT"] + robbie.sl_step_size) <= robbie.lever_08["MAX_AXLE_LIFT"],
                         (robbie.lever_09["CURRENT_AXLE_LIFT"] + robbie.sl_step_size) <= robbie.lever_09["MAX_AXLE_LIFT"]]
    if all(raise1_conditions):
        m.Motor_2.setTargetVelocity(3500)
        m.Motor_3.setTargetVelocity(-3500)
        m.axle_1_raise(robbie.sl_step_size)
        robbie.lever_08["CURRENT_AXLE_LIFT"] += robbie.sl_step_size
        robbie.lever_09["CURRENT_AXLE_LIFT"] += robbie.sl_step_size
        sleep(0.5)
        m.Motor_2.setTargetVelocity(0)
        m.Motor_3.setTargetVelocity(-0)
        
        
def axle_1_lowering():
    robbie.current_command = 'AXLE_1_LOWERING'
    lower1_conditions = [(robbie.lever_08["CURRENT_AXLE_LIFT"] - robbie.hl_step_size) >= -1000,
                         (robbie.lever_09["CURRENT_AXLE_LIFT"] - robbie.hl_step_size) >= 1000]
    if all(lower1_conditions): 
        m.Motor_2.setTargetVelocity(-3500)
        m.Motor_3.setTargetVelocity(3500)
        m.axle_1_lower(robbie.hl_step_size)
        robbie.lever_08["CURRENT_AXLE_LIFT"] -= robbie.hl_step_size
        robbie.lever_09["CURRENT_AXLE_LIFT"] -= robbie.hl_step_size
        sleep(1)
        m.Motor_2.setTargetVelocity(0)
        m.Motor_3.setTargetVelocity(-0)
        
def axle_1_manual_lowering():
    robbie.current_command = 'AXLE_1_LOWERING'
    lower1_conditions = [(robbie.lever_08["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000,
                         (robbie.lever_09["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000]
    print(robbie.lever_08["CURRENT_AXLE_LIFT"])
    if all(lower1_conditions): 
        m.Motor_2.setTargetVelocity(-3500)
        m.Motor_3.setTargetVelocity(3500)
        m.axle_1_lower(robbie.sl_step_size)
        robbie.lever_08["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size
        robbie.lever_09["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size
        sleep(0.5)
        m.Motor_2.setTargetVelocity(0)
        m.Motor_3.setTargetVelocity(-0)
        
        print("hello")
      
      
def axle_2_raising():    
    robbie.current_command = 'AXLE_2_RAISING'
    raise2_conditions = [(robbie.lever_07["CURRENT_AXLE_LIFT"] + robbie.hl_step_size) <= robbie.lever_07["MAX_AXLE_LIFT"],
                         (robbie.lever_0A["CURRENT_AXLE_LIFT"] + robbie.hl_step_size) <= robbie.lever_0A["MAX_AXLE_LIFT"]]
    if all(raise2_conditions):
        m.axle_2_raise(robbie.hl_step_size)
        robbie.lever_07["CURRENT_AXLE_LIFT"] += robbie.hl_step_size
        robbie.lever_0A["CURRENT_AXLE_LIFT"] += robbie.hl_step_size
        
def axle_2_manual_raising():    
    robbie.current_command = 'AXLE_2_RAISING'
    raise2_conditions = [(robbie.lever_07["CURRENT_AXLE_LIFT"] + robbie.sl_step_size) <= robbie.lever_07["MAX_AXLE_LIFT"],
                         (robbie.lever_0A["CURRENT_AXLE_LIFT"] + robbie.sl_step_size) <= robbie.lever_0A["MAX_AXLE_LIFT"]]
    if all(raise2_conditions):
        m.axle_2_raise(robbie.sl_step_size)
        robbie.lever_07["CURRENT_AXLE_LIFT"] += robbie.sl_step_size
        robbie.lever_0A["CURRENT_AXLE_LIFT"] += robbie.sl_step_size


def axle_2_lowering():
    robbie.current_command = 'AXLE_2_LOWERING'
    lower2_conditions = [(robbie.lever_07["CURRENT_AXLE_LIFT"] - robbie.hl_step_size) >= -1000,
                         (robbie.lever_0A["CURRENT_AXLE_LIFT"] - robbie.hl_step_size) >= -1000]
    if all(lower2_conditions):
        m.axle_2_lower(robbie.hl_step_size)
        robbie.lever_07["CURRENT_AXLE_LIFT"] -= robbie.hl_step_size
        robbie.lever_0A["CURRENT_AXLE_LIFT"] -= robbie.hl_step_size

def axle_2_manual_lowering():
    robbie.current_command = 'AXLE_2_LOWERING'
    lower2_conditions = [(robbie.lever_07["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000,
                         (robbie.lever_0A["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000]
    if all(lower2_conditions):
        m.axle_2_lower(robbie.sl_step_size)
        robbie.lever_07["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size
        robbie.lever_0A["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size


def axle_3_raising():
    robbie.current_command = 'AXLE_3_RAISING'
    raise3_conditions = [(robbie.lever_06["CURRENT_AXLE_LIFT"] + robbie.hl_step_size) <= robbie.lever_06["MAX_AXLE_LIFT"],
                         (robbie.lever_0B["CURRENT_AXLE_LIFT"] + robbie.hl_step_size) <= robbie.lever_0B["MAX_AXLE_LIFT"]]
    if all(raise3_conditions):
        m.axle_3_raise(robbie.hl_step_size)
        robbie.lever_06["CURRENT_AXLE_LIFT"] += robbie.hl_step_size
        robbie.lever_0B["CURRENT_AXLE_LIFT"] += robbie.hl_step_size
        
def axle_3_manual_raising():
    robbie.current_command = 'AXLE_3_RAISING'
    raise3_conditions = [(robbie.lever_06["CURRENT_AXLE_LIFT"] + robbie.sl_step_size) <= robbie.lever_06["MAX_AXLE_LIFT"],
                         (robbie.lever_0B["CURRENT_AXLE_LIFT"] + robbie.sl_step_size) <= robbie.lever_0B["MAX_AXLE_LIFT"]]
    if all(raise3_conditions):
        m.axle_3_raise(robbie.sl_step_size)
        robbie.lever_06["CURRENT_AXLE_LIFT"] += robbie.sl_step_size
        robbie.lever_0B["CURRENT_AXLE_LIFT"] += robbie.sl_step_size


def axle_3_lowering():
    robbie.current_command = 'AXLE_3_LOWERING'
    lower3_conditions = [(robbie.lever_06["CURRENT_AXLE_LIFT"] - robbie.hl_step_size) >= -1000,
                         (robbie.lever_0B["CURRENT_AXLE_LIFT"] - robbie.hl_step_size) >= -1000]
    if all(lower3_conditions):
        m.axle_3_lower(robbie.hl_step_size)
        robbie.lever_06["CURRENT_AXLE_LIFT"] -= robbie.hl_step_size
        robbie.lever_0B["CURRENT_AXLE_LIFT"] -= robbie.hl_step_size
        
def axle_3_manual_lowering():
    robbie.current_command = 'AXLE_3_LOWERING'
    lower3_conditions = [(robbie.lever_06["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000,
                         (robbie.lever_0B["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000]
    if all(lower3_conditions):
        m.axle_3_lower(robbie.sl_step_size)
        robbie.lever_06["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size
        robbie.lever_0B["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size

        
        
def axle_4_raising():
    robbie.current_command = 'AXLE_4_RAISING'
    raise4_conditions = [(robbie.lever_05["CURRENT_AXLE_LIFT"] + robbie.hl_step_size) <= robbie.lever_05["MAX_AXLE_LIFT"],
                         (robbie.lever_0C["CURRENT_AXLE_LIFT"] + robbie.hl_step_size) <= robbie.lever_0C["MAX_AXLE_LIFT"]]
    if all(raise4_conditions):
        m.Motor_1.setTargetVelocity(-3500)
        m.Motor_4.setTargetVelocity(3500)
        m.axle_4_raise(robbie.hl_step_size)
        robbie.lever_05["CURRENT_AXLE_LIFT"] += robbie.hl_step_size
        robbie.lever_0C["CURRENT_AXLE_LIFT"] += robbie.hl_step_size
        sleep(1)
        m.Motor_1.setTargetVelocity(0)
        m.Motor_4.setTargetVelocity(0)
        
def axle_4_manual_raising():
    robbie.current_command = 'AXLE_4_RAISING'
    raise4_conditions = [(robbie.lever_05["CURRENT_AXLE_LIFT"] + robbie.sl_step_size) <= robbie.lever_05["MAX_AXLE_LIFT"],
                         (robbie.lever_0C["CURRENT_AXLE_LIFT"] + robbie.sl_step_size) <= robbie.lever_0C["MAX_AXLE_LIFT"]]
    if all(raise4_conditions):
        m.Motor_1.setTargetVelocity(-3500)
        m.Motor_4.setTargetVelocity(3500)
        m.axle_4_raise(robbie.sl_step_size)
        robbie.lever_05["CURRENT_AXLE_LIFT"] += robbie.sl_step_size
        robbie.lever_0C["CURRENT_AXLE_LIFT"] += robbie.sl_step_size
        sleep(0.5)
        m.Motor_1.setTargetVelocity(0)
        m.Motor_4.setTargetVelocity(0)
    
    
def axle_4_lowering():
    robbie.current_command = 'AXLE_4_LOWERING'
    lower4_conditions = [(robbie.lever_05["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000,
                         (robbie.lever_0C["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000]
    if all(lower4_conditions):
        m.Motor_1.setTargetVelocity(3500)
        m.Motor_4.setTargetVelocity(-3500)
        m.axle_4_lower(robbie.hl_step_size)
        robbie.lever_05["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size
        robbie.lever_0C["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size
        sleep(1)
        m.Motor_1.setTargetVelocity(0)
        m.Motor_4.setTargetVelocity(0)
        
def axle_4_manual_lowering():
    robbie.current_command = 'AXLE_4_LOWERING'
    lower4_conditions = [(robbie.lever_05["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000,
                         (robbie.lever_0C["CURRENT_AXLE_LIFT"] - robbie.sl_step_size) >= -1000]
    if all(lower4_conditions):
        m.Motor_1.setTargetVelocity(3500)
        m.Motor_4.setTargetVelocity(-3500)
        m.axle_4_lower(robbie.sl_step_size)
        robbie.lever_05["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size
        robbie.lever_0C["CURRENT_AXLE_LIFT"] -= robbie.sl_step_size
        sleep(0.5)
        m.Motor_1.setTargetVelocity(0)
        m.Motor_4.setTargetVelocity(0)
        
        
def raise_left_corner_levers():
    lift = robbie.lever_05["MAX_AXLE_LIFT"] - robbie.lever_05["CURRENT_AXLE_LIFT"]
    m.V5(lift)
    robbie.lever_05["CURRENT_AXLE_LIFT"] += lift
    lift = robbie.lever_08["MAX_AXLE_LIFT"] - robbie.lever_08["CURRENT_AXLE_LIFT"]
    m.V8(lift)
    robbie.lever_08["CURRENT_AXLE_LIFT"] += lift


def raise_right_corner_levers():
    lift = robbie.lever_09["MAX_AXLE_LIFT"] - robbie.lever_09["CURRENT_AXLE_LIFT"]
    m.V9(lift)
    robbie.lever_09["CURRENT_AXLE_LIFT"] += lift
    lift = robbie.lever_0C["MAX_AXLE_LIFT"] - robbie.lever_0C["CURRENT_AXLE_LIFT"]
    m.VC(lift)
    robbie.lever_0C["CURRENT_AXLE_LIFT"] += lift
                
                
def reset_levers_to_zero():
    m.E5(robbie.lever_05["CURRENT_AXLE_LIFT"])
    m.D6(robbie.lever_06["CURRENT_AXLE_LIFT"])
    m.D7(robbie.lever_07["CURRENT_AXLE_LIFT"])
    m.E8(robbie.lever_08["CURRENT_AXLE_LIFT"])
    m.E9(robbie.lever_09["CURRENT_AXLE_LIFT"])
    m.DA(robbie.lever_0A["CURRENT_AXLE_LIFT"])
    m.DB(robbie.lever_0B["CURRENT_AXLE_LIFT"])
    m.EC(robbie.lever_0C["CURRENT_AXLE_LIFT"])
    reset_levers_model_values()
    
    
def reset_levers_model_values():
    robbie.lever_05["CURRENT_AXLE_LIFT"] = 0
    robbie.lever_06["CURRENT_AXLE_LIFT"] = 0
    robbie.lever_07["CURRENT_AXLE_LIFT"] = 0
    robbie.lever_08["CURRENT_AXLE_LIFT"] = 0
    robbie.lever_09["CURRENT_AXLE_LIFT"] = 0
    robbie.lever_0A["CURRENT_AXLE_LIFT"] = 0
    robbie.lever_0B["CURRENT_AXLE_LIFT"] = 0
    robbie.lever_0C["CURRENT_AXLE_LIFT"] = 0
                
                
def middle_axles_left_up():
    
    robbie.current_command = 'MID_LEFT_AXLES_UP'
    mlu_conditions = [(robbie.lever_06["CURRENT_AXLE_LIFT"] + robbie.mm_step_size) <= robbie.lever_06["MAX_AXLE_LIFT"],
                      (robbie.lever_07["CURRENT_AXLE_LIFT"] + robbie.mm_step_size) <= robbie.lever_07["MAX_AXLE_LIFT"]]
    if all(mlu_conditions):
        m.mid_axles_left_up(robbie.mm_step_size)
        robbie.lever_06["CURRENT_AXLE_LIFT"] += robbie.mm_step_size
        robbie.lever_07["CURRENT_AXLE_LIFT"] += robbie.mm_step_size                
        print(f'Mid left axles (2 and 3) raised by {robbie.mm_step_size}.')
        
        
def middle_axles_left_down():
    
    robbie.current_command = 'MID_LEFT_AXLES_DOWN'
    mld_conditions = [(robbie.lever_06["CURRENT_AXLE_LIFT"] - robbie.mm_step_size) >= 0,
                      (robbie.lever_07["CURRENT_AXLE_LIFT"] - robbie.mm_step_size) >= 0]
    if all(mld_conditions):
        m.mid_axles_left_down(robbie.mm_step_size)
        robbie.lever_06["CURRENT_AXLE_LIFT"] -= robbie.mm_step_size
        robbie.lever_07["CURRENT_AXLE_LIFT"] -= robbie.mm_step_size 
        print(f'Mid left axles (2 and 3) lowered by {robbie.mm_step_size}.')


def middle_axles_right_up():   
    
    robbie.current_command = 'MID_RIGHT_AXLES_UP'
    mru_conditions = [(robbie.lever_0A["CURRENT_AXLE_LIFT"] + robbie.mm_step_size) <= robbie.lever_0A["MAX_AXLE_LIFT"],
                      (robbie.lever_0B["CURRENT_AXLE_LIFT"] + robbie.mm_step_size) <= robbie.lever_0B["MAX_AXLE_LIFT"]]
    if all(mru_conditions):
        m.mid_axles_right_up(robbie.mm_step_size)
        robbie.lever_0A["CURRENT_AXLE_LIFT"] += robbie.mm_step_size
        robbie.lever_0B["CURRENT_AXLE_LIFT"] += robbie.mm_step_size
        print(f'Mid right axles (2 and 3) raised by {robbie.mm_step_size}.')
        
        
def middle_axles_right_down():
    
    robbie.current_command = 'MID_RIGHT_AXLES_DOWN'
    mrd_conditions = [(robbie.lever_0A["CURRENT_AXLE_LIFT"] - robbie.mm_step_size) >= 0,
                      (robbie.lever_0B["CURRENT_AXLE_LIFT"] - robbie.mm_step_size) >= 0]
    if all(mrd_conditions):            
        m.mid_axles_right_down(robbie.mm_step_size)
        robbie.lever_0A["CURRENT_AXLE_LIFT"] -= robbie.mm_step_size
        robbie.lever_0B["CURRENT_AXLE_LIFT"] -= robbie.mm_step_size
        print(f'Mid right axles (2 and 3) lowered by {robbie.mm_step_size}.')
        
        
        
#### BAFFLE CLIMB FUNCTIONS ####
        
        
    
def forward_baffle_climb():
    global abort, command_running
    abort = False
    command_running = True
    
    n = 0
    
    while not abort or n < 1:
        axle_1_raising()
        axle_3_raising()    
        m.axle_4_lower(400)   
       
        sleep(2)
        start_distance = robbie.rear_lidar_value
        m.forward(robbie.BAFFLE_CLIMB_SPEED)
#         while robbie.rear_lidar_value < start_distance + 18:
#             sleep(0.1)
        sleep(6)
        m.stop_robot()
        sleep(2)
        
        
        axle_1_lowering()
        m.axle_4_raise(400) 
        axle_2_raising()
        
        
        sleep(2)
        start_distance = robbie.rear_lidar_value
        m.forward(robbie.BAFFLE_CLIMB_SPEED)
#         while robbie.rear_lidar_value < start_distance + 24:
#             sleep(0.1)
        sleep(8)
        m.stop_robot()
        sleep(2)
          
          
        axle_3_lowering()
        sleep(1)
        axle_4_raising()
        m.axle_1_raise(400)
        sleep(2)
        
        start_distance = robbie.rear_lidar_value
        m.forward(robbie.BAFFLE_CLIMB_SPEED)
#         while robbie.rear_lidar_value < start_distance + 22:
#             sleep(0.1)
        sleep(6)
        m.stop_robot()
        sleep(2)
        
        
        axle_4_lowering()
        axle_2_lowering()
        m.axle_1_lower(400)
        
        n += 1
        
    command_running = False

def reverse_baffle_climb():
    global abort, command_running
    abort = False
    command_running = True
    
    n = 0
    
    while not abort or n < 1:
        
        axle_4_raising()
        axle_2_raising()    
        m.axle_1_lower(400)   
       
        sleep(2)
        start_distance = robbie.rear_lidar_value
        m.reverse(robbie.BAFFLE_CLIMB_SPEED)
        while robbie.rear_lidar_value > start_distance - 17:
            sleep(0.1)
        m.stop_robot()
        sleep(2)
        
        
        axle_4_lowering()
        m.axle_1_raise(400) 
        axle_3_raising()
        
        
        sleep(2)
        start_distance = robbie.rear_lidar_value
        m.reverse(robbie.BAFFLE_CLIMB_SPEED)
        while robbie.rear_lidar_value > start_distance - 23:
            sleep(0.1)
        m.stop_robot()
        sleep(2)
          
          
        axle_2_lowering()
        sleep(1)
        axle_1_raising()
        m.axle_4_raise(400)

        
        sleep(2)
        start_distance = robbie.rear_lidar_value
        m.reverse(robbie.BAFFLE_CLIMB_SPEED)
        while robbie.rear_lidar_value > start_distance - 22:
            sleep(0.1)
        m.stop_robot()
        sleep(2)
        
        axle_1_lowering()
        axle_3_lowering()
        m.axle_4_lower(400)
         
        n += 1

    command_running = False
    
    
    
#### LANCE HEAD FUNCTIONS ####    



def slide_out_distance(length):
    length = int(length)
    if robbie.head_homed:
        m.Motor_D.setPositionAbsolute(-length*1000 + robbie.slide_home_position)
    else:
        m.Motor_D.setPositionAbsolute(-length*1000)
    

def slide_home():
    global abort, command_running
    command_running = True
    
    """ The slide could be anywhere so try to wind it in unless already homed. """
    if not robbie.slide_motor_homed or abort:
        # Always negative (anticlockwise) to home...
        m.home_slide_motor()
        while True:
            if robbie.slide_motor_homed or abort:
                m.stop_slide_motor()
                robbie.slide_home_position = m.Motor_D.getPosition()
                sleep(0.5)
                break
 
            sleep(0.1)
            
        m.stop_slide_motor()
        
        if not abort:
            
            m.Motor_D.setPositionMode()
            m.Motor_D.setPositionRelative(-3000)
            sleep(3)
            
    command_running = False

def roll_to_angle(angle):
    angle = int(float(angle))
    m.Motor_E.setPositionMode()
    if robbie.head_homed:
        m.Motor_E.setPositionAbsolute(angle*10 + robbie.roll_home_position)
    else:
        m.Motor_E.setPositionAbsolute(angle*10)
   
   


def roll_home():
    global abort
    
    """ The lance head could be rotated to any angle so crank it in to the home position unless it is already there. """
    if not robbie.roll_motor_homed or abort:
        m.home_roll_motor()
        while True:
            if robbie.roll_motor_homed or abort:
                sleep(0.1)
                break
            
            sleep(0.1)
            
        sleep(0.15)    
        m.stop_roll_motor()
        
       
        if not abort:
        
            sleep(1)
            m.Motor_E.setPositionMode()
            m.Motor_E.setPositionRelative(1800)
            sleep(3)
            robbie.roll_home_position = m.Motor_E.getPosition()
            



def pitch_to_angle(angle):
    angle = int(angle)
    m.Motor_F.setPositionMode()
    if robbie.head_homed:
        m.Motor_F.setPositionAbsolute(-angle*10 + robbie.pitch_home_position)
    else:
        m.Motor_F.setPositionAbsolute(-angle*10)
    

def pitch_home():
    global abort
    
    """ The lance could be pointing (pitch) at any angle, so crank it in to 0 degrees (i.e. horizontal) unless it is already there. """
    m.Motor_F.setPositionRelative(-200)
    sleep(1)
        
    if not robbie.pitch_motor_homed or abort:
        m.home_pitch_motor()

        while True:
            if robbie.pitch_motor_homed or abort:
                m.stop_pitch_motor()
                robbie.pitch_home_position = m.Motor_F.getPosition()
                sleep(0.5)
                break
            
            sleep(0.1)
        
        m.stop_pitch_motor()



def oscillate_lance(StartOscillationAngle, FinishOscillationAngle):
    global oscillate
    
    
    while oscillate:
        
        print(StartOscillationAngle, FinishOscillationAngle)
        m.Motor_F.setPositionMode()
        m.Motor_F.setPositionAbsolute(robbie.pitch_home_position - StartOscillationAngle*10)
        sleep(3)
        m.Motor_F.setPositionAbsolute(robbie.pitch_home_position - FinishOscillationAngle*10)
        sleep(3)
    

def home_head_motors():
    global abort
    abort = False
    
    if robbie.head_initialised and robbie.head_homed == False:
        if not abort:

            pitch_home()
            roll_home()
            slide_home()
            
            robbie.head_homed = True
            
    elif robbie.head_initialised and robbie.head_homed:
    
        m.Motor_F.setPositionAbsolute(robbie.pitch_home_position)
        sleep(5)
        m.Motor_E.setPositionAbsolute(robbie.roll_home_position)
        sleep(5)
        m.Motor_D.setPositionAbsolute(robbie.slide_home_position)
        
    else:
        print("Initialise head before homing")
    
    abort = False
    
    flash_lights()


def manual_home_head_motors():
    
    if robbie.head_initialised:
        
        robbie.slide_home_position = m.Motor_D.getPosition()
        robbie.roll_home_position = m.Motor_E.getPosition()
        robbie.pitch_home_position = m.Motor_F.getPosition()
        
        sleep(1)
        
        flash_lights()
        
        robbie.head_homed = True

    
def move_lance_to_position(SlideDistance, RollAngle):
    """Takes a list generated by 'get_head_positions' and moves the slide and roll motors to the required position"""
    m.Motor_D.setPositionMode()
    m.Motor_E.setPositionMode()
    
    SlideDistance = -SlideDistance*1000
    
    m.Motor_F.setPositionAbsolute(robbie.pitch_home_position)
    sleep(5)
    m.Motor_D.setPositionAbsolute(robbie.slide_home_position + SlideDistance)
    sleep(10)
    m.Motor_E.setPositionAbsolute(robbie.roll_home_position + RollAngle)
    sleep(3)
    
def Angle_A(SlideDistance,RollAngle):
    global command_running
    command_running = True
    
    if robbie.head_initialised and robbie.head_homed:
    
        move_lance_to_position(SlideDistance, RollAngle)
        print('Head moved to Position A.')
        
    else:
        print("Initialise head and home it before moving to a Lance Angle")
    
    command_running = False
    
def Angle_B(SlideDistance,RollAngle):
    global command_running
    command_running = True
    
    if robbie.head_initialised and robbie.head_homed:
    
        move_lance_to_position(SlideDistance, RollAngle)
        print('Head moved to Position B.')

    else:
        print("Initialise head and home it before moving to a Lance Angle")
        
    command_running = False


    
    
    
#### REPORT ROBOT INFORMATION FUNCTION ####
    
    

# def report_robot_model():
#     global robbie
#     
#     """ Thread procedure which reports the entire robot instance data for diagnostics purposes """
#     display_counter = 0
#     while True:
#         print(f"Mk.{robbie.robot_version} Robot control program for the connected {robbie.robot_type} robot model.")
#         now = datetime.now()
#         date_time = now.strftime("[%d-%m-%Y %H:%m:%s]")
#         print(f"Date/time: {date_time}")
#         print(a.BLD_GR + f"{robbie.system_message}" + a.RES)
#         print(f"Connections: CPU2: " + a.BLU + f"{robbie.cpu2_connected}")
#         print(f"CURRENT_COMND: {robbie.current_command}")
#         print(f"CURRENT_STATE: {robbie.current_state}")
#         print(a.YEL + "LEVERS:")
#         print('           {:<6}'.format('M09'), '{:<6}'.format('M0A'), '{:<6}'.format('M0B'), '{:<6}'.format('M0C'))
#         
#         print(f"FRONT <-- {robbie.lever_09['CURRENT_AXLE_LIFT']:04} : {robbie.lever_0A['CURRENT_AXLE_LIFT']:04} : {robbie.lever_0B['CURRENT_AXLE_LIFT']:04} : "
#               f"{robbie.lever_0C['CURRENT_AXLE_LIFT']:04} ---> REAR")
#         print(f"FRONT <-- {robbie.lever_08['CURRENT_AXLE_LIFT']:04} : {robbie.lever_07['CURRENT_AXLE_LIFT']:04} : {robbie.lever_06['CURRENT_AXLE_LIFT']:04} : "
#               f"{robbie.lever_05['CURRENT_AXLE_LIFT']:04} ---> REAR")
#         print('           {:<6}'.format('M08'), '{:<6}'.format('M07'), '{:<6}'.format('M06'), '{:<6}'.format('M05') + a.RES)
#         print("Roll = %f , Pitch = %f , Yaw = %f" %(robbie.roll,icm.acceleration[0],icm.acceleration[2]))
#         print(" ")
#         print(" ")
# 
#         print(f"-------------------------------------------------------------------------------------------")
#         print(f"LANCE CONTROL")
#         print(f"Roll motor homed? : {robbie.roll_motor_homed}    Pitch motor homed? : {robbie.pitch_motor_homed}    Slide motor homed? : {robbie.slide_motor_homed}")
#         print(f"Report page: {display_counter}   Tone: {robbie.rl_lidar_value * 5}")
#         print(f"CTRL Last message: {robbie.ctrl_latest_message}")
#         print(f"ADMN Last message: {robbie.admn_latest_message}")
#         
#         print(" ")
#         display_counter += 1
#         sleep(0.8)
#         os.system('clear')
    
    
if __name__ == "__main__":
    
    # Logging configuration...
#     logging.basicConfig(filename='/home/pi/Desktop/ttv7_cpu1.log', level=logging.DEBUG, format='[%(asctime)s], %(levelname)s, %(message)s', filemode = 'a')
    
    # Constants
    ON = True
    OFF = False
    
    global abort, command_running, oscillate
    abort = False
    command_running = False
    oscillate = False

    DRIVING_LIGHTS = 26         # GPIO26, pin 37

    SLIDE_SENSOR = 13
    ROLL_SENSOR = 6
    PITCH_SENSOR = 5
    
    TubeSize = 'S'
    
      # Features of the cleaning environment
      
    PIPES_START_POSITION = 55
    FLUSH_SPEED = 1000
    LANCE_SPEED = 1000
    
    StartPosition = 0
    FinishPosition = 0
   
    # Create an instance of the Robot!
    robbie = ttv7_robot.robot('FLUSHING', 6.5)  # To be read from the configuration spreadsheet.

    # RPi board configuration and setup/initialise GPIO lines (See other project files as they may use GPIO lines not documented here!)----------
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    GPIO.setup(DRIVING_LIGHTS, GPIO.OUT)
    GPIO.output(DRIVING_LIGHTS, GPIO.LOW)

    GPIO.setup(SLIDE_SENSOR, GPIO.IN)
    GPIO.setup(ROLL_SENSOR, GPIO.IN)
    GPIO.setup(PITCH_SENSOR, GPIO.IN)

    # Initialise variables --------------------------------------------------------------------------------
    sesison_id = "XYZ123"
    connected = False
    #rear_camera = PiCamera()
    i2c = board.I2C()
    icm = adafruit_icm20x.ICM20948(i2c)
    
    robbie.system_message = "Tubetech Robot V7 Started. Session ID: {sesison_id}"
    
    # Start critical threads...
    
    IMU_thread = threading.Thread(target=get_roll_pitch_yaw_data)
    IMU_thread.start()

    Head_Sensors_thread = threading.Thread(target=read_head_sensors)
    Head_Sensors_thread.start()
   
 
    
    # Monitor all parameters of interest; a static display of all values updating each second in a terminal window (assuming not headless)
#     reporting_thread = threading.Thread(target=report_robot_model)
#     reporting_thread.start()


    
    try:
        
        system_initialisation_thread = threading.Thread(target = system_initialisation)
        system_initialisation_thread.start()
        
        sleep(10)
        
        run_control_program()
        
       
    finally:
        print('[FINALLY] Robot control program was terminated by the control console operator.')
        logging.info('[FINALLY] Tubetech Robot V7 control program terminated by the operator.')
        m.stop_robot()
        
            
        GPIO.cleanup()
        m.terminate_motors()
        m.terminate_head_motors()
        print('ROBOT SESSION TERMINATED.')

 
 