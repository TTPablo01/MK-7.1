#########################################################################################
#
# Program  : tubetech_mc5005.py
# Version  : 0.0.0.5
#
# Author   : Gary Bigden / Robert Evans
# Updated  : 09/01/2024 at 16:00
# Function : Module containing the Motor Controller class template to interface with a
#            Faulhaber MC5005 motion control board.
#            
# Copyright: IGS / Tubetech Industrial Ltd. 2023.
#
# External dependencies (Python files):
#
#
#########################################################################################

import serial
import struct
import time
import math

S32 = 2147483648

OPERATION_MODE = 0x6060           # operation mode
OPERATION_MODE_DISP = 0x6061      # operation mode display

DEBUG = False

# All motors use the network attached to the first serial port - do not use the mini port for this!
ser = serial.Serial("/dev/ttyS0", baudrate=115200, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE, timeout=2, parity=serial.PARITY_NONE)

class MotorController():
    S = b'\x53'
    E = b'\x45'
    GET = b'\x01'
    SET = b'\x02'

    def __init__(self, nodeId):
        self.node = nodeId
    
    #---------------------------------------------------------------------------------
    # Core functions. These allow you to write and read from the motor control card.
    #---------------------------------------------------------------------------------
    
    def close(self):
        ser.close()

    def CRC(self, msg):
        poly = 0xd5
        crc = 0xff

        for byte in msg:
            crc = crc ^ byte
            for _ in range(8):
                if crc & 0x01:
                    crc = ((crc >> 1) ^ poly) 
                else:
                    crc >>= 1

        return struct.pack("B", crc)

    def write(self, command):
        """Write command. The length of the command is 
        length of the argument  + 1 for the length byte + 1 for the CRC byte"""

        command = struct.pack("B", len(command) + 2) + command
        command = self.S + command + self.CRC(command) + self.E

        # time.sleep(0.2)
        ser.flushOutput()
        ser.flushInput()
        time.sleep(0.)
        ser.write(command)
        time.sleep(0.)

        #print("write :: " + dump(command))
        return self.read()

    def read(self):
        """First read the start bit and the length,
        then read the rest of the transmission."""

        ans = ser.read(2)        
        try:
            length = ans[1]
            
        except IndexError as e:
            print(f"Error in xyframe_mc5005.py/read():  Motor ID: {self.node} is not currently available on the motor control network.")
            return

        ansAll = ans + ser.read(length)
        #print("read :: " + dump(ansAll))

        #check CRC is correct
        #print(self.CRC(ansAll[1:-2]))
        #print(struct.pack("B", ansAll[-2]))
        if (self.CRC(ansAll[1:-2]) != struct.pack("B", ansAll[-2])):
            print(self.CRC(ansAll[1:-2]))
            print(struct.pack("B", ansAll[-2]))
        assert self.CRC(ansAll[1:-2]) == struct.pack("B", ansAll[-2])

        # ansAll includes self.S, so data starts at position 7
        return ansAll[7:-2]


    def readRegister(self, address, nodeID, subindex = 0):
        """Read Register 
        address: address of register to be read
        node = b'\x01' optional node
        sudindex = 0 optional subindex
        """    
        command = nodeID + self.GET + int.to_bytes(address, 2, 'little') + int.to_bytes(subindex, 1, 'little')
        if DEBUG: 
            print(dump(command))
        return self.write(command)

    def setRegister(self, address, value, length, node, subindex = 0):
        """set register address: two byte address of the register, i.e. 0x6040
        value: value of the register length: length of the register, in bytes"""

        command = ( node + self.SET
                    + int.to_bytes(address, 2, 'little')
                    + int.to_bytes(subindex, 1, 'little')
                    + int.to_bytes(value, length, 'little',signed=True))
        #print(dump(command))
        #####print(command)
        
        self.write(command)

    def getCastedRegister(self, address, subindex = 0):
        return hex(int.from_bytes(self.readRegister(address, self.node, subindex = subindex), byteorder='little'))

    def printStatus(self):
        print("Status: ", self.getCastedRegister(0x6041))
        return(self.getCastedRegister(0x6041))
    
    def setControlWord(self, word):
        self.setRegister(0x6040, word, 2, node = self.node)
    

    #--------------------------------------------
    # State machine commands.
    #--------------------------------------------  
    
    def shutDown(self):
        #Register(0x6040)
        self.setControlWord(0x06)

    def switchOn(self):
        #Register(0x6040)
        self.setControlWord(0x07)

    def enable(self):
        #Register(0x6040)
        self.setControlWord(0x0f)

    def disable(self):
        #Register(0x6040)
        self.setControlWord(0x07)
        
    def quickStop(self):
        #Register(0x6040)
        self.setControlWord(0x02)
    
    def halt(self):
        """
        Pauses current movement without deleting movement command from memory. 
        When unhalted motor will resume the set movement.
        """
        #Register(0x6040)
        self.setControlWord(0x10f)
    
    def unhalt(self):
        #Register(0x6040)
        self.setControlWord(0x0f)
        
    
    def setSupplyVoltage(self, voltage: int):
        voltage_upper_limit = 100*math.ceil(voltage*1.15)
        self.setRegister(0x2325, voltage_upper_limit, 2, node = self.node, subindex=4)


    #--------------------------------------------
    # Motor setup commands.
    #--------------------------------------------  

    def setGearRatio(self, motor_revolutions: int, drive_revolutions: int):
        """
        Lets the motor card know which gear ratio is being used by the attached motor.

        Example:

        You have a motor with gear ratio 196:1. You set this up in the card by calling setGearRatio(196,1)
        """
        self.setRegister(0x6091, motor_revolutions, 4, node = self.node, subindex=1) 
        self.setRegister(0x6091, drive_revolutions, 4, node = self.node, subindex=2)
 
    
    def setRotaryControl(self):
        """Sets the motor so that Position mode moves it in 0.1 degree steps, and velocity mode moves it in RPM. """
        self.setRegister(0x6092, 3600, 4, node=self.node, subindex=1) #breaks up 1 drive revolution into 3600 steps (360 degrees in 0.1 degree steps)
        self.setRegister(0x6096, 3600, 4, node=self.node, subindex=2) #sets the velocity factor to 3600 steps per minute (1RPM)
        
    def setLeadscrewControl(self, leadscrew_pitch: float):
        """
        Sets the motor so that Position mode moves it in micrometers, and velocity mode moves it in mm/s.
        
        leadscrew_pitch = pitch of the leadscrew given in mm.    
        """
        feed_in_micrometers = int(leadscrew_pitch*1000) #converts the pitch from mm to micrometers.

        self.setRegister(0x6092, feed_in_micrometers, 4, node=self.node, subindex=1) #breaks 1 drive revolution into steps equal to pitch length
        self.setRegister(0x6096, 60000, 4, node=self.node, subindex=2) #sets the velocity factor to mm/s

    def setMaxSpeed(self, value=6000): #WIP
        # Seem to have set a top speed of 6000(?)
        self.setRegister(0x6080, value, 2, node = self.node)
    
    def setProfileVelocity(self, value: int):
        """
        Sets the profile velocity. In position mode this sets the speed that the motor will move between positions, in velocity mode it acts like a top speed.   
        """
        self.setRegister(0x6081, value, 4, node = self.node)
        
    def disableVoltage(self):
        self.setControlWord(0x00)

    def setHomingMethod(self, value):
        self.setRegister(0x6098, value, 2, node = self.node)


    #--------------------------------------------
    # Homing operation mode controls.
    #--------------------------------------------  

    def setHomingMode(self):
        #self.setRegister(0x6060, 1, 6)
        command = self.node + b'\x02' + b'\x60\x60\x00' + b'\x06'
        self.write(command)


    def setHomingSpeed(self, switch_seek_speed: int, zero_seek_speed: int):
        self.setRegister(0x6099, switch_seek_speed, 4, node = self.node, subindex=1)
        self.setRegister(0x6099, zero_seek_speed, 4, node = self.node, subindex=2)


    def startHoming(self):
        # setRegister(0x6040)
        self.setControlWord(0x1f)


    #------------------------------------------------
    # Profile Position (PP) operation mode controls.
    #------------------------------------------------

    def setPositionMode(self):
        #self.setRegister(0x6060, 1, 1)
        command = self.node + b'\x02' + b'\x60\x60\x00' + b'\x01'
        self.write(command)
    
    def setPositionModeWindow(self, window: int):
        """
        Sets a window of accepted deviation around a target position. 
        The motor will signal "Target Reached" when its current position falls within the window.
        
        Default = 1 
        """

        self.setRegister(0x6067, window, 4, node = self.node)
    
    def setPositionModeWindowTime(self, minimum_time: int):
        """
        Sets the minimum time in ms that the motor has to stay in a target position before
        the motor card sends the signal "Target Reached".
        """

        self.setRegister(0x6068, minimum_time, 4, node = self.node)

    
    def setTargetPosition(self, value):
        """
        Tells the motor controller what the target position is. 
        
        Must be used in conjunction with extra setControlWord() commands 
        to tell the motor how you would like to reach that position. 
        """
        
        self.setRegister(0x607a, value, 4, node = self.node)
        
    def setPositionAbsolute(self, value):
        """
        Sets target position relative to the set 0 position. 

        By default this command will be interrupted by any new position command set.
        If you would like to set multiple positions, use setPositionAbsoluteQueue
        
        Make sure the device is in position mode prior to using 
        this function.
        """

        self.setTargetPosition(value)
        self.setControlWord(0x0f)
        self.setControlWord(0x3f)
    
    def setPositionAbsolute_Queue(self, values: list):
        """
        Sets a queue of target positions relative to the motor's home point. 
        It will not move to the next position until it has reached the current position in the queue.  
        """
        self.setTargetPosition(values[0])
        self.setControlWord(0x0f)
        self.setControlWord(0x1f)
        for value in values[1:]:
            self.setControlWord(0x0f)
            self.setTargetPosition(value)
            self.setControlWord(0x1f)

    def setPositionRelative(self, value):
        """
        Sets target position relative to the motor's current position. 
        Make sure the device is in position mode prior to using this function.
        """
        self.setTargetPosition(value)
        self.setControlWord(0x0f)
        self.setControlWord(0x7f)

    def setPositionRelative_Queue(self, values: list):
        """
        Sets a queue of target positions relative to the motor's current position. 
        It will not move to the next position until it has reached the current position in the queue.  
        """
        self.setTargetPosition(values[0])
        self.setControlWord(0x0f)
        self.setControlWord(0x5f)
        for value in values[1:]:
            self.setControlWord(0x0f)
            self.setTargetPosition(value)
            self.setControlWord(0x5f)


    #------------------------------------------------
    # Profile Velocity (PV) operation mode controls.
    #------------------------------------------------

    def setVelocityMode(self):
        #self.setRegister(0x6060, 1, 3)
        command = self.node + b'\x02' + b'\x60\x60\x00' + b'\x03'
        self.write(command)
    
    def setTargetVelocity(self, value):
        self.setRegister(0x60ff, value, 4, node = self.node)


    #--------------------------------------------
    # Reading motor status.
    #-------------------------------------------- 

    def readCurrent(self): #NEEDS TESTING 
        continuous_current = self.readRegister(0x2329, self.node, subindex=2)
        actual_current = self.readRegister(0x6074, self.node)

        continuous_current_int = int.from_bytes(continuous_current, byteorder='little', signed = True) #value given in mA
        actual_current_int = int.from_bytes(actual_current, byteorder='little', signed = True) #value is how many 1000ths of the current limit you are currently at.

        converted_reading = (continuous_current_int/1000) * (actual_current_int/1000) #converts to A 
        
        return converted_reading

    def getPosition(self):
        """Reads the current position of the motor."""
        
        answer = self.readRegister(0x6064, self.node) 
        position = int.from_bytes(answer, byteorder='little', signed = True)
        return position
    
    def readProfileVelocity(self): #NEEDS TESTING
        answer = self.readRegister(0x6081, self.node) 
        position = int.from_bytes(answer, byteorder='little', signed = True)

        return position
    

    #--------------------------------------------
    # Software Limits
    #--------------------------------------------
    def setMotorDefaultLimits(self, motor_revolutions, drive_revolutions): #WIP
        """
        Will incorporate into setGearRatio when setPositionRangeLimit and setSoftwarePositionLimit are tested.
        These will set the limits so that the internal position value never reaches over the maximum possible internal position the given gear ratio.

        Example:

        A motor with gear ratio 588:1 is set up on the motor card. 
        It recieves a command to move it to position S32 (the max possible internal position of the motor).

        The command position would be multiplied by the gear ratio to find the required internal position. This would lead the motor to try and 
        drive to position 58*S32, which is not possible. The movement would start but not complete, which could damage the motor.
        """
        
        ratio = motor_revolutions/drive_revolutions

        motor_nom_maximum = math.floor(S32/ratio)

        self.setPositionRangeLimit(minimum=-motor_nom_maximum, maximum=motor_nom_maximum)

        self.setSoftwarePositionLimit(minimum=-motor_nom_maximum, maximum = motor_nom_maximum)


    def setPositionRangeLimit(self, minimum: int, maximum: int): #NEEDS TESTING
        """
        Allows you to set a position range limit. 
        If a movement takes you past the max, your actual position value loops to the minimum.

        This is mainly for rotary drives, if so it should sit inside your software limit range.

        If your motor is driving a linear system please ensure that your range limit is larger than the software position limit.
        """
        self.setRegister(0x607B, minimum, 4, node=self.node, subindex=1)
        self.setRegister(0x607B, maximum, 4, node=self.node, subindex=2)


    def setSoftwarePositionLimit(self, min: int, maximum: int): #NEEDS TESTING
        """
        Allows you to set a position limit. Any movement command that would put your actual position outside of this range will not be executed.

        This is mainly for linear drives.
        """
        self.setRegister(0x607D, min, 4, node=self.node, subindex=1)
        self.setRegister(0x607D, maximum, 4, node=self.node, subindex=2)

    #--------------------------------------------
    # Digital Inputs
    #--------------------------------------------

    def set_input_bitmask(self, digital_inputs: list): #NEEDS TESTING
        """
        Takes a list of digital inputs that you would like to change settings for and returns the appropriate
        binary number to be sent to the register to change them.

        If you pass [0] as the input it will set all switches to 0 (reset to default).
        
        Pin 32 - DigIn 1 
        Pin 33 - DigIn 2 
        Pin 34 - DigIn 3 
        Pin 35 - DigIn 4 
        Pin 36 - DigIn 5 
        Pin 37 - DigIn 6 
        Pin 38 - DigIn 7 
        Pin 39 - DigIn 8
        """

        if digital_inputs==[0]:
            return int('0',2)
        bitmask = [0]*8
        for num in digital_inputs:
            bitmask[8-num] = 1
        bitmask = ''.join(map(str, bitmask))
     
        return int(bitmask, 2)


    def setLowerLimitSwitches(self, input_pins: list): #NEEDS TESTING
        """
        Configure digital input pins for a lower limit switch (limit for when motion is moving in the negative direction).

        """
        setting = self.set_input_bitmask(input_pins) #NEEDS TESTING

        self.setRegister(0x2310, setting, 4, node=self.node, subindex=1)


    def setUpperLimitSwitches(self, input_pins: list):
        """
        Configure digital input pins for an upper limit switch.

        """

        setting = self.set_input_bitmask(input_pins)

        self.setRegister(0x2310, setting, 4, node=self.node, subindex=2)


    def setReferenceSwitch(self, input_pin: int): #NEEDS TESTING
        """
        Configure a digital input to be a reference limit switch.

        Reference switches are used during homing to set the 0 position for the motor. 

        A digital input can be used as both a limit and reference switch.

        """ 
        self.setRegister(0x2310, input_pin, 4, node=self.node, subindex=4)


    def setSwitchBehaviour(self, stop_type: str):  #NEEDS TESTING
        
        """
        Choose how you want the motor to stop upon hitting a limit switch.
        """

        if stop_type.upper() =="BRAKE":
            self.setRegister(0x2310, 1, 4, node=self.node, subindex=3)

        elif stop_type.upper() == "QUICK":
            self.setRegister(0x2310, 2, 4, node=self.node, subindex=3)

        else: 
            print("Please choose from either BRAKE or QUICK stop options.")

    def setActiveLevelLow(self, inputs: list): #NEEDS TESTING
        
        """
        Use this to set selected digital pins to be active at a low level of current.

        Default is all digital inputs are set to read high as active. 

        To reset to default enter [0] into this function.    
        """

        setting = self.set_input_bitmask(inputs)

        self.setRegister(0x2310, setting, 4, node=self.node, subindex=10)


    def setTriggerThreshold(self, inputs: list): #NEEDS TESTING
        
        """
        Use this to set selected digital pins to trigger at a high level of current (24V).

        Default is all digital inputs are set with a trigger threshold of 5V. 

        To reset to default enter [0] into this function.
        """

        setting = self.set_input_bitmask(inputs)

        self.setRegister(0x2310, setting, 4, node=self.node, subindex=11)
    
    #--------------------------------------------
    # Digital Outputs
    #--------------------------------------------
    
    def SetDigOut(self, PinNr):
        # SetDigOut(PinNr)
        # Will set the digital output 1 or 2 to high. Shutdown hall sensors
        if PinNr==1:
            self.setRegister(0x2311, 0xfd, 2, node = b'\x01',subindex=4)

        if PinNr==2:
            self.setRegister(0x2311, 0xf7, 2, node = b'\x01',subindex=4)
      
    def ClearDigOut(self, PinNr):
        # ClearDigOut(PinNr)
        # Will clear the digital output 1 or 2 to low. Switch on hall sensors.
        if PinNr==1:
            self.setRegister(0x2311, 0xfc, 2, node = b'\x01',subindex=4)

        if PinNr==2:
            self.setRegister(0x2311, 0xf3, 2, node = b'\x01',subindex=4)

    #-----------------------------------------------------------------------------------------------
    # Other controls. This section is for controls written by Gary that I have not yet figured out.
    #-------------------------------------------- --------------------------------------------------
    
    def getTargetPositionSource(self):
       return self.readRegister(0x2331, subindex = 4, nodeID = self.node)

    
    def enable2(self):
        """
        Enable()
        will start the CiA 402 state machine or re-enable the control. Returns only after the OperationEnabled
        state is reached. Adapted from FA.
        """
        EnState = 0  #reset the local step counter
        CiAStatusword = int(self.getCastedRegister(0x6041), base=16) #initial check of the status word
        CiAStatusMask = 0x6f
        CiAStatus = CiAStatusword & CiAStatusMask
        CiAStatus_OperationEnabled = 0x27
        CiAStatus_SwitchOnDisabled = 0x40
        CiAStatus_QuickStop = 0x07
        #check for being in stopped mode
        if CiAStatus == CiAStatus_QuickStop:
            self.setControlWord(0x0f)   #Enable Operation
            EnState = 1
        elif CiAStatus == CiAStatus_OperationEnabled:   #drive is already enabled               
            EnState = 2
        elif CiAStatus != CiAStatus_SwitchOnDisabled: # otherwise it's safe to disable first
            # we need to send a shutdown first
            self.setControlWord(0x00)   #Controlword = CiACmdDisableVoltage

        while EnState != 2:
            CiAStatusword = int(self.getCastedRegister(0x6041),base=16)
            CiAStatusMask = 0x6f
            CiAStatus = (CiAStatusword & CiAStatusMask) #cyclically check the status word
            if EnState == 0:
                if CiAStatus == 0x40:
                #send the enable signature
                    self.setControlWord(0x06) #CiACmdShutdown
                    self.setControlWord(0x0f) #CiACmdEnableOperation
                    #now wait for being enabled
                    EnState = 1

            elif EnState == 1:
                #wait for enabled
                if CiAStatus == CiAStatus_OperationEnabled:
                    EnState = 2
    """
     Disable()
     Will stop the drive and shut the CiA 402 state machine down TO the initial state
     returns only after the initial state (Switch On Disabled) is reached. Adapted from FA.
    """
    def disable2(self):
        DiState = 0 #reset the local step counter
        CiAStatusword = int(self.getCastedRegister(0x6041), base=16) #initial check of the status word
        CiAStatusMask = 0x6f
        CiAStatus = CiAStatusword & CiAStatusMask
        CiAStatus_OperationEnabled = 0x27
        if CiAStatus == CiAStatus_OperationEnabled:
            #send a shutdown command first to stop the motor
            self.setControlWord(0x07) #CiACmdDisable
            DiState = 1
        else:
            #otherwise the disable voltage is the next command
            #out of quick-stop or switched on.
            DiState = 2

        while DiState != 4:
            CiAStatusword = int(self.getCastedRegister(0x6041),base=16)
            CiAStatusMask = 0x6f
            CiAStatus = (CiAStatusword & CiAStatusMask) #cyclically check the status
            if DiState == 1:
                if CiAStatus == 0x23:
                    #only now it's safe to send the disable voltage command
                    DiState = 2

            elif DiState == 2:
                #wait for enabled
                self.setControlWord(0x00) #CiACmdDisableVoltage
                DiState = 3

            elif DiState == 3:
                #wait for final state
                if CiAStatus == 0x40:
                    DiState = 4


def enable_1(NodeNr):   #simple enable of axis
    NodeNr.shutDown()
    NodeNr.switchOn()
    NodeNr.enable()
    print ('Enable motor ' + str(NodeNr) + ' successful')
    
def dump(x):
    return ''.join([type(x).__name__, "('", *['\\x'+'{:02x}'.format(i) for i in x], "')"])
