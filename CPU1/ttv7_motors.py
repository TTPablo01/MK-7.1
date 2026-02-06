##############################################################################################
#
# Program  : ttv7_motors.py ("TT Robot V7.0 Motor object")
# Version  : 7.4.0.65
# Target   : Robbie
#

# Author   : Gary Bigden and Pablo Cordoba
# Updated  : 15/10/2024 at 09:00 (Tuesday)
# Function : Provides basic motion control for motors attached to levers and traction motors.
#            This module in intended For Mk6.5 and Mk7.0 robots.
#
# Copyright: Tubetech Industrial Ltd. 2023.
#
# Dependencies (Python files):
#            ttv7_mc5005.py
#
#
##############################################################################################

import ttv7_mc5005 as mc
from time import sleep

CURRENT_POSITION = 0x25    # Method No.37: Home motor at its current position...

Motor_1 =  mc.MotorController(b'\x01')
Motor_2 =  mc.MotorController(b'\x02')
Motor_3 =  mc.MotorController(b'\x03')
Motor_4 =  mc.MotorController(b'\x04')
Motor_5 =  mc.MotorController(b'\x05')
Motor_6 =  mc.MotorController(b'\x06')
Motor_7 =  mc.MotorController(b'\x07')
Motor_8 =  mc.MotorController(b'\x08')
Motor_9 =  mc.MotorController(b'\x09')
Motor_A =  mc.MotorController(b'\x0A')
Motor_B =  mc.MotorController(b'\x0B')
Motor_C =  mc.MotorController(b'\x0C')
Motor_D =  mc.MotorController(b'\x0D')
Motor_E =  mc.MotorController(b'\x0E')
Motor_F =  mc.MotorController(b'\x0F')


def initialise_motors():
    # initialise the four traction motors (Mecanum wheeled)
    Motor_1.shutDown()
    Motor_1.switchOn()
    Motor_1.setHomingMode()   #\x06
    Motor_1.setHomingMethod(CURRENT_POSITION)
    Motor_1.enable()
    Motor_1.setSupplyVoltage(24)
    Motor_1.setGearRatio(1,1)
    Motor_1.startHoming()     #\x1f
    Motor_1.setVelocityMode()
    #sleep(0.1)
    Motor_2.shutDown()  #06
    Motor_2.switchOn()  #07
    Motor_2.setHomingMode()   #\x06
    Motor_2.setHomingMethod(CURRENT_POSITION)
    Motor_2.enable()    #0f
    Motor_2.setSupplyVoltage(24)
    Motor_2.setGearRatio(1,1)
    Motor_2.startHoming()     #\x1f
    Motor_2.setVelocityMode()
    #sleep(0.1)
    Motor_3.shutDown()
    Motor_3.switchOn()
    Motor_3.setHomingMode()   #\x06
    Motor_3.setHomingMethod(CURRENT_POSITION)
    Motor_3.enable()
    Motor_3.setSupplyVoltage(24)
    Motor_3.setGearRatio(1,1)
    Motor_3.startHoming()     #\x1f
    Motor_3.setVelocityMode()
    #sleep(0.1)
    Motor_4.shutDown()  #06
    Motor_4.switchOn()  #07
    Motor_4.setHomingMode()   #\x06
    Motor_4.setHomingMethod(CURRENT_POSITION)
    Motor_4.enable()    #0f
    Motor_4.setSupplyVoltage(24)
    Motor_4.setGearRatio(1,1)
    Motor_4.startHoming()     #\x1f
    Motor_4.setVelocityMode()
    #sleep(0.1)
  
    Motor_5.shutDown()        #\x06
    Motor_5.switchOn()        #\x07
    Motor_5.setHomingMode()   #\x06
    Motor_5.setHomingMethod(CURRENT_POSITION)
    Motor_5.enable()          #\x0f
    Motor_5.setSupplyVoltage(24)
    Motor_5.setGearRatio(1,1)
    Motor_5.startHoming()     #\x1f
    Motor_5.setPositionMode() #\x01
    #sleep(0.1)
    Motor_6.shutDown()        #\x06
    Motor_6.switchOn()        #\x07
    Motor_6.setHomingMode()   #\x06
    Motor_6.setHomingMethod(CURRENT_POSITION)
    Motor_6.enable()          #\x0f
    Motor_6.setSupplyVoltage(24)
    Motor_6.setGearRatio(1,1)
    Motor_6.startHoming()     #\x1f
    Motor_6.setPositionMode() #\x01
    #sleep(0.1)
    Motor_7.shutDown()        #\x06
    Motor_7.switchOn()        #\x07
    Motor_7.setHomingMode()   #\x06
    Motor_7.setHomingMethod(CURRENT_POSITION)
    Motor_7.enable()
    Motor_7.setSupplyVoltage(24)#\x0f
    Motor_7.setGearRatio(1,1)
    Motor_7.startHoming()     #\x1f
    Motor_7.setPositionMode() #\x01
    #sleep(0.1)
    Motor_8.shutDown()        #\x06
    Motor_8.switchOn()        #\x07
    Motor_8.setHomingMode()   #\x06
    Motor_8.setHomingMethod(CURRENT_POSITION)
    Motor_8.enable()          #\x0f
    Motor_8.setSupplyVoltage(24)
    Motor_8.setGearRatio(1,1)
    Motor_8.startHoming()     #\x1f
    Motor_8.setPositionMode() #\x01
    #sleep(0.1)
    Motor_9.shutDown()        #\x06
    Motor_9.switchOn()        #\x07
    Motor_9.setHomingMode()   #\x06
    Motor_9.setHomingMethod(CURRENT_POSITION)
    Motor_9.enable()          #\x0f
    Motor_9.setSupplyVoltage(24)
    Motor_9.setGearRatio(1,1)
    Motor_9.startHoming()     #\x1f
    Motor_9.setPositionMode() #\x01
    #sleep(0.1)
    Motor_A.shutDown()        #\x06
    Motor_A.switchOn()        #\x07
    Motor_A.setHomingMode()   #\x06
    Motor_A.setHomingMethod(CURRENT_POSITION)
    Motor_A.enable()          #\x0f
    Motor_A.setSupplyVoltage(24)
    Motor_A.setGearRatio(1,1)
    Motor_A.startHoming()     #\x1f
    Motor_A.setPositionMode() #\x01
    #sleep(0.1)
    Motor_B.shutDown()        #\x06
    Motor_B.switchOn()        #\x07
    Motor_B.setHomingMode()   #\x06
    Motor_B.setHomingMethod(CURRENT_POSITION)
    Motor_B.enable()          #\x0f
    Motor_B.setSupplyVoltage(24)
    Motor_B.setGearRatio(1,1)
    Motor_B.startHoming()     #\x1f
    Motor_B.setPositionMode() #\x01
    #sleep(0.1)
    Motor_C.shutDown()        #\x06
    Motor_C.switchOn()        #\x07
    Motor_C.setHomingMode()   #\x06
    Motor_C.setHomingMethod(CURRENT_POSITION)
    Motor_C.enable()          #\x0f
    Motor_C.setSupplyVoltage(24)
    Motor_C.setGearRatio(1,1)
    Motor_C.startHoming()     #\x1f
    Motor_C.setPositionMode() #\x01
    #sleep(0.1)
    
def initialise_head_motors():
    """ Pitch, roll and slide motors setup """
    # SLIDE: 0x0D, RED
    # Need to know how we home this motor at robot initialisation.
    Motor_D.shutDown()        #\x06
    Motor_D.switchOn()        #\x07
    Motor_D.setHomingMode()   #\x06
    Motor_D.setHomingMethod(CURRENT_POSITION)
    Motor_D.enable()          #\x0f
    Motor_D.setSupplyVoltage(24)
    Motor_D.startHoming()    #\x1f # ???         #\x0f
    Motor_D.setGearRatio(16,1)
    Motor_D.setLeadscrewControl(1.5)
    Motor_D.setPositionMode() #\x01
    #sleep(0.1)
    # ROLL: 0x0E, BLUE
    # Need to know how we home this motor at robot initialisation.
    Motor_E.shutDown()        #\x06
    Motor_E.setHomingMode()   #\x06
    Motor_E.setHomingMethod(CURRENT_POSITION)
    Motor_E.enable()          #\x0f
    Motor_E.setSupplyVoltage(24)
    Motor_E.startHoming()          #\x0f
    Motor_E.setGearRatio(196,1)
    Motor_E.setRotaryControl()
    Motor_E.setPositionMode() #\x01
    #sleep(0.1)
    # PITCH: 0x0F, YELLOW
    # Need to know how we home this motor at robot initialisation.
    Motor_F.shutDown()        #\x06
    Motor_F.switchOn()        #\x07
    Motor_F.setHomingMode()   #\x06
    Motor_F.setHomingMethod(CURRENT_POSITION)
    Motor_F.enable()          #\x0f
    Motor_F.setSupplyVoltage(24)
    Motor_F.startHoming()           #\x0f
    Motor_F.setGearRatio(196,1)
    Motor_F.setRotaryControl()
    Motor_F.setProfileVelocity(5)
    Motor_F.setPositionMode() #\x01
    #sleep(0.1)
 
def stop_robot():
    Motor_1.setTargetVelocity(0)
    Motor_2.setTargetVelocity(0)
    Motor_3.setTargetVelocity(0)
    Motor_4.setTargetVelocity(0)
 
 
def stop_head():
    Motor_D.setVelocityMode()
    Motor_E.setVelocityMode()
    Motor_F.setVelocityMode()
    Motor_D.setTargetVelocity(0)
    Motor_E.setTargetVelocity(0)
    Motor_F.setTargetVelocity(0)
    Motor_D.setPositionMode()
    Motor_E.setPositionMode()
    Motor_F.setPositionMode()

def halt_motors():

    Motor_1.halt()
    Motor_2.halt()
    Motor_3.halt()
    Motor_4.halt()
    Motor_5.halt()
    Motor_6.halt()
    Motor_7.halt()
    Motor_8.halt()
    Motor_9.halt()
    Motor_A.halt()
    Motor_B.halt()
    Motor_C.halt()
    
def halt_head_motors():    
    
    Motor_D.halt()
    Motor_E.halt()
    Motor_F.halt()

def unhalt_motors():

    Motor_1.unhalt()
    Motor_2.unhalt()
    Motor_3.unhalt()
    Motor_4.unhalt()
    Motor_5.unhalt()
    Motor_6.unhalt()
    Motor_7.unhalt()
    Motor_8.unhalt()
    Motor_9.unhalt()
    Motor_A.unhalt()
    Motor_B.unhalt()
    Motor_C.unhalt()
    
def unhalt_head_motors():    
    
    Motor_D.unhalt()
    Motor_E.unhalt()
    Motor_F.unhalt()
    
    
def left(rate):
    Motor_1.setTargetVelocity(-rate)
    Motor_2.setTargetVelocity(rate)
    Motor_3.setTargetVelocity(rate)
    Motor_4.setTargetVelocity(-rate)   
    
def left_1_2(rate):
    Motor_1.setTargetVelocity(-rate)
    Motor_2.setTargetVelocity(rate)
    
def left_3_4(rate):
    Motor_3.setTargetVelocity(rate)
    Motor_4.setTargetVelocity(-rate) 
    
def right(rate):
    Motor_1.setTargetVelocity(rate)
    Motor_2.setTargetVelocity(-rate)
    Motor_3.setTargetVelocity(-rate)
    Motor_4.setTargetVelocity(rate)
    
def right_1_2(rate):
    Motor_1.setTargetVelocity(rate)
    Motor_2.setTargetVelocity(-rate)
    
def right_3_4(rate):
    Motor_3.setTargetVelocity(-rate)
    Motor_4.setTargetVelocity(rate)


def forward(rate):
    Motor_1.setTargetVelocity(-rate)
    Motor_2.setTargetVelocity(-rate)
    Motor_3.setTargetVelocity(rate)
    Motor_4.setTargetVelocity(rate)
    
def fw_1(rate):
    Motor_1.setTargetVelocity(-rate)
    
def fw_2(rate):
    Motor_2.setTargetVelocity(-rate)

def fw_3(rate):
    Motor_3.setTargetVelocity(rate)

def fw_4(rate):
    Motor_4.setTargetVelocity(rate)
    
def forward_axle_1(rate):
    Motor_2.setTargetVelocity(rate)
    Motor_3.setTargetVelocity(-rate)
    
def forward_axle_4(rate):
    Motor_1.setTargetVelocity(-rate)
    Motor_4.setTargetVelocity(rate)    
    
def reverse(rate):
    Motor_1.setTargetVelocity(rate)
    Motor_2.setTargetVelocity(rate)
    Motor_3.setTargetVelocity(-rate)
    Motor_4.setTargetVelocity(-rate)
    
def rv_1(rate):
    Motor_1.setTargetVelocity(rate)

def rv_2(rate):
    Motor_2.setTargetVelocity(rate)

def rv_3(rate):
    Motor_3.setTargetVelocity(-rate)

def rv_4(rate):
    Motor_4.setTargetVelocity(-rate)
        
    
def reverse_axle_1(rate):
    Motor_2.setTargetVelocity(-rate)
    Motor_3.setTargetVelocity(rate)
    
def reverse_axle_4(rate):
    Motor_1.setTargetVelocity(rate)
    Motor_4.setTargetVelocity(-rate)    
    
def axle_1_raise(height):
    Motor_8.setPositionRelative(-height)
    Motor_9.setPositionRelative(height)

def axle_2_raise(height):
    Motor_7.setPositionRelative(-height)
    Motor_A.setPositionRelative(height)
    
def axle_3_raise(height):
    Motor_6.setPositionRelative(height)
    Motor_B.setPositionRelative(-height)
    
def axle_4_raise(height):
    Motor_5.setPositionRelative(height)
    Motor_C.setPositionRelative(-height)
    
def axle_1_lower(height):
    Motor_8.setPositionRelative(height)
    Motor_9.setPositionRelative(-height)
    
def axle_2_lower(height):
    Motor_7.setPositionRelative(height)
    Motor_A.setPositionRelative(-height)
        
def axle_3_lower(height):
    Motor_6.setPositionRelative(-height)
    Motor_B.setPositionRelative(height)
    
def axle_4_lower(height):
    Motor_5.setPositionRelative(-height)
    Motor_C.setPositionRelative(height)
    
# Specific motor (motor ID used as index) commands for raise and lower.

# Raises the lever on motor 5 while turning the wheel on motor 1.
def U5(height, rate):
    Motor_1.setTargetVelocity(-rate)
    #sleep(1)
    Motor_5.setPositionRelative(height)
    sleep(1.5)
    Motor_1.setTargetVelocity(0)
    sleep(0.5)    
# The no wheel spin version of U5.
def V5(height):
    Motor_5.setPositionRelative(height)
    
    
def U6(height):
    Motor_6.setPositionRelative(height)
    
def U7(height):
    Motor_7.setPositionRelative(-height)
    
# Raises the lever on motor 8 while turning the wheel on motor 2.
def U8(height, rate):
    Motor_2.setTargetVelocity(rate)
    #sleep(1)
    Motor_8.setPositionRelative(-height)
    sleep(1.5)
    Motor_2.setTargetVelocity(0)
    sleep(0.5)    
# The no wheel spin version of U8.
def V8(height):
    Motor_8.setPositionRelative(-height)
    
# Raises the lever on motor 9 while turning the wheel on motor 3.
def U9(height, rate):
    Motor_3.setTargetVelocity(-rate)
    #sleep(1)
    Motor_9.setPositionRelative(height)
    sleep(1.5)
    Motor_3.setTargetVelocity(0)
    sleep(0.5)  
# The no wheel spin version of U9.
def V9(height):
    Motor_9.setPositionRelative(height)
    
    
def UA(height):
    Motor_A.setPositionRelative(height)
    
def UB(height):
    Motor_B.setPositionRelative(-height)

# Raises the lever on motor C while turning the wheel on motor 4.
def UC(height, rate):
    Motor_4.setTargetVelocity(rate)
    #sleep(1)
    Motor_C.setPositionRelative(-height)
    sleep(1.5)
    Motor_4.setTargetVelocity(0)
    sleep(0.5) 
# The no wheel spin version of UC.
def VC(height):
    Motor_C.setPositionRelative(-height)


# Lowers the lever on motor 5 while turning the wheel on motor 1.
def D5(height, rate):
    Motor_1.setTargetVelocity(rate)
    #sleep(1)
    Motor_5.setPositionRelative(-height)
    sleep(1.5)
    Motor_1.setTargetVelocity(0)
    sleep(0.5)
# The no wheel spin version of D5.
def E5(height):
    Motor_5.setPositionRelative(-height)
    

def D6(height):
    Motor_6.setPositionRelative(-height)
    
def D7(height):
    Motor_7.setPositionRelative(height)

# Raises the lever on motor 8 while turning the wheel on motor 2.
def D8(height, rate):
    Motor_2.setTargetVelocity(-rate)
    #sleep(1)
    Motor_8.setPositionRelative(height)
    sleep(1.5)
    Motor_2.setTargetVelocity(0)
    sleep(0.5)
# The no wheel spin version of D8.
def E8(height):
    Motor_8.setPositionRelative(height)
    

# Raises the lever on motor 9 while turning the wheel on motor 3.
def D9(height, rate):
    Motor_3.setTargetVelocity(rate)
    #sleep(1)
    Motor_9.setPositionRelative(-height)
    sleep(1.5)
    Motor_3.setTargetVelocity(0)
    sleep(0.5)
# The no wheel spin version of D9.
def E9(height):
    Motor_9.setPositionRelative(-height)
    
    
def DA(height):
    Motor_A.setPositionRelative(-height)
    
def DB(height):
    Motor_B.setPositionRelative(height)
    
# Raises the lever on motor C while turning the wheel on motor 4.
def DC(height, rate):
    Motor_4.setTargetVelocity(-rate)
    #sleep(1)
    Motor_C.setPositionRelative(height)
    sleep(1.5)
    Motor_4.setTargetVelocity(0)
    sleep(0.5)
# The no wheel spin version of DC.
def EC(height):
    Motor_C.setPositionRelative(height)


# control all frour axles but on one side only.  
def axles_raise_left_side(height):
    Motor_6.setPositionRelative(height) 
    Motor_7.setPositionRelative(-height)
    Motor_5.setPositionRelative(height)
    Motor_8.setPositionRelative(-height)

def axles_lower_left_side(height):
    Motor_6.setPositionRelative(-height) 
    Motor_7.setPositionRelative(height)
    Motor_5.setPositionRelative(-height)
    Motor_8.setPositionRelative(height)
    
def axles_raise_right_side(height):
    Motor_A.setPositionRelative(height)
    Motor_B.setPositionRelative(-height)
    Motor_9.setPositionRelative(height)
    Motor_C.setPositionRelative(-height)
    
def axles_lower_right_side(height):
    Motor_A.setPositionRelative(-height)
    Motor_B.setPositionRelative(height)
    Motor_9.setPositionRelative(-height)
    Motor_C.setPositionRelative(height)
    
    
    
    
def axles_raise_left_side_climb(height):
    Motor_6.setPositionRelative(height) 
    Motor_7.setPositionRelative(-height)
    sleep(0.5)
    Motor_5.setPositionRelative(height)
    Motor_8.setPositionRelative(-height)

def axles_lower_left_side_climb(height):
    Motor_5.setPositionRelative(-height)
    Motor_8.setPositionRelative(height)
    sleep(0.5)
    Motor_6.setPositionRelative(-height) 
    Motor_7.setPositionRelative(height)
    
    
    
def axles_raise_right_side_climb(height):
    Motor_A.setPositionRelative(height)
    Motor_B.setPositionRelative(-height)
    sleep(0.5)
    Motor_9.setPositionRelative(height)
    Motor_C.setPositionRelative(-height)
    
def axles_lower_right_side_climb(height):
    Motor_9.setPositionRelative(-height)
    Motor_C.setPositionRelative(height)
    sleep(0.5)
    Motor_A.setPositionRelative(-height)
    Motor_B.setPositionRelative(height)
    

    

    
    
def mid_axles_right_up(height):
    Motor_A.setPositionRelative(height)
    Motor_B.setPositionRelative(-height)
    
def mid_axles_right_down(height):
    Motor_A.setPositionRelative(-height)
    Motor_B.setPositionRelative(height)
    
def mid_axles_left_up(height):
    Motor_6.setPositionRelative(height) 
    Motor_7.setPositionRelative(-height)
    
def mid_axles_left_down(height):
    Motor_6.setPositionRelative(-height)
    Motor_7.setPositionRelative(height)
    
    
def home_slide_motor():
    Motor_D.setVelocityMode()
    Motor_D.setTargetVelocity(7)
    
    
def slide_motor_left():
    Motor_D.setPositionMode()
    Motor_D.setPositionRelative(2500)
    sleep(5)
    

def slide_motor_right():
    Motor_D.setPositionMode()
    Motor_D.setPositionRelative(-2500)
    sleep(5)

    
def stop_slide_motor():
    Motor_D.setVelocityMode()
    Motor_D.setTargetVelocity(0)
    Motor_D.setPositionMode()

    
def home_roll_motor():
    Motor_E.setVelocityMode()
    Motor_E.setTargetVelocity(-3)
    

    
def roll_motor_clockwise():
    Motor_E.setPositionMode()
    Motor_E.setPositionRelative(-20)
    

def roll_motor_anticlockwise():
    Motor_E.setPositionMode()
    Motor_E.setPositionRelative(20)
    
def stop_roll_motor():
    Motor_F.setVelocityMode()
    Motor_E.setTargetVelocity(0)
    Motor_E.setPositionMode()
    
    
    
def home_pitch_motor():
    Motor_F.setVelocityMode()
    Motor_F.setTargetVelocity(2)
    
    
def pitch_motor_up():
    Motor_F.setPositionMode()
    Motor_F.setPositionRelative(50)

def pitch_motor_down():
    Motor_F.setPositionMode()
    Motor_F.setPositionRelative(-50)
    
    
def stop_pitch_motor():
    Motor_F.setVelocityMode()
    Motor_F.setTargetVelocity(0)
    Motor_F.setPositionMode()
    
def terminate_motors():
    Motor_1.shutDown()
    Motor_2.shutDown()
    Motor_3.shutDown()
    Motor_4.shutDown()
    Motor_5.shutDown()
    Motor_6.shutDown()
    Motor_7.shutDown()
    Motor_8.shutDown()
    Motor_9.shutDown()
    Motor_A.shutDown()
    Motor_B.shutDown()
    Motor_C.shutDown()
    sleep(0.3)
    
    
def terminate_head_motors():
    Motor_D.shutDown()
    Motor_E.shutDown()
    Motor_F.shutDown()
    sleep(0.3)
    
def get_all_motors_status():
    
    MotorsList = [Motor_1, Motor_2, Motor_3, Motor_4, Motor_5, Motor_6, Motor_7, Motor_8, Motor_9, Motor_A, Motor_B, Motor_C]
    FaultyMotorsList = []
    
    for index, motor in enumerate(MotorsList):
        try:
            motorStatus = motor.printStatus()
        except Exception as e:
            FaultyMotorsList.append(index+1)
            continue
            
            
        if (motorStatus != '0x1427') and (motorStatus != '0x427') and (motorStatus != '0x27'):
            
            FaultyMotorsList.append(index+1)
            
            
#     MotorStatusList.append(Motor_D.printStatus())
#     MotorStatusList.append(Motor_E.printStatus())
#     MotorStatusList.append(Motor_F.printStatus())
    
    return(FaultyMotorsList)
    
    
    

""" There is only one motor; all serially connected motor instances are closed by this. """