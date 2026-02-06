############################################################################################
#
# Program  : ttv7_robot.py
# Version  : 7.4.0.61
#
# Author   : Gary Bigden
# Updated  : 29/01/2024 at 15:00 (Monday)
# Function : This is the central robot class which holds the machine state. The constructor
#            takes a type parameter indicating either a flushing robot (FLUSH) or a cleaning
#            robot (LANCE)
#            
# Copyright: Tubetech Industrial Ltd. 2023.
#
# External dependencies (Python files):
#
#
############################################################################################

class robot:
    # Constants.
    ON = True
    OFF = False
    
    # Robot types
    FLUSHING = 0x01    # 12 motors (0x01-0x0C)
    LANCING = 0x02     # 15 motors (0x01-0x0F)
    BODY_LENGTH = 120  # cm.
    
    # Robot speed parameters
    MAX_F_R_SPEED = 4000
    MIN_F_R_SPEED = 300
    START_SPEED = 1000
    CLIMB_SPEED = 2000
    BAFFLE_CLIMB_SPEED = 2500
    flush_speed = 2000
    REPOSITION_SPEED = 1500
    DRIVE_WHEEL_RESEAT_SPEED = 3000
    
    # Lancing robot extents...
    PITCH_MOTOR_MAX_STEPS_FROM_HOME = 10_000  # The limit (maximum extent) of pitch travel from the horizontal - correct value yet to be found.
    ROLL_MOTOR_MAX_STEPS_FROM_HOME  = 10_000  # The limit of roll from the homed position - correct value yet to be found.
    SLIDE_MOTOR_MAX_STEPS_FROM_HOME = 200_000  # The limit of slide from the homed position (fully left viewed from the rear) - correct value yet to be found.
    
    # Robot limb height limits
    HIGH_LIFT = 1750
    SMALL_LIFT = 300
    CCMD_STEP_SIZE = 400
    MAN_MIN_STEP_SIZE = 3
    
    # Directions
    FORWARD = 0x10
    REVERSE = 0x20
    LEFT = 0x30
    RIGHT = 0x40
    
    # Variables...
    # Commands.
    system_message = ''
    cpu2_latest_message = ''
    ctrl_latest_message = ''
    admn_latest_message = ''
    last_command = 'NO-COMMAND'
    current_command = 'NO-COMMAND'
    current_state = 'UNDEFINED'
    cpu2_connected = False             # CPU2 connection state with CPU1 (master)
    ctrl_connected = False             # CTRL is the robot controller head mounted on the pole.
    
    # Housekeeping
    initialised = None                 # Robot initialisation successful flag - it's game up if this does not get set to TRUE   
    tcp_connection = None              # Robot communications running flag - it's game up if this does not get set to TRUE
    head_initialised = False
    head_homed = False
    
    # Basic movement...
    speed = START_SPEED                # Always very slow to start.
    direction = None                   # Useful...
    moving = False                     # Robot will never be moving before initialisation
    
    cc_step_size = CCMD_STEP_SIZE      # The step size used with Custom Commands.
    mm_step_size = MAN_MIN_STEP_SIZE   # The step size used with manual commands which gives finer control
    hl_step_size = HIGH_LIFT           # A large step size used to get a lever to 
    sl_step_size = SMALL_LIFT          # A small step size used to get a lever to 
    
    # Lights.
    driving_lights = None
    
    paused = False
    
    # Inertial Measurement Unit values (IMU). Only interested in roll for left/right climbing.
    # Pitch will be useful if the robot is nose diving off the tubes.
    pitch = 0       # Robot body pitch, not lance pitch.
    roll = 0        # Robot body roll.
    yaw = 0         # Robot body yaw, not used at all.
    quant_roll = 0  # Quantised roll value
    
    # IMU diagnostics...
    pitch_sensor_working = None
    roll_sensor_level = None
    yaw_sensor_working = None
    
    # Proximity sensors for slide, pitch and roll head assembly (in the case of a lancing robot)
    pitch_motor_homed = 0
    roll_motor_homed = 0
    slide_motor_homed = 0
    
    pitch_home_position = 0
    roll_home_position = 0
    slide_home_position = 0
    
    faulty_motors_list = []
    
    # Axle lift position (absolute) data to prevent robot overreach and self harm. All axles independently preset.
    lever_05 = {"MAX_AXLE_LIFT" : 3000, "CURRENT_AXLE_LIFT" : 0}
    lever_06 = {"MAX_AXLE_LIFT" : 3000, "CURRENT_AXLE_LIFT" : 0}
    lever_07 = {"MAX_AXLE_LIFT" : 3000, "CURRENT_AXLE_LIFT" : 0}
    lever_08 = {"MAX_AXLE_LIFT" : 3000, "CURRENT_AXLE_LIFT" : 0}
    lever_09 = {"MAX_AXLE_LIFT" : 3000, "CURRENT_AXLE_LIFT" : 0}
    lever_0A = {"MAX_AXLE_LIFT" : 3000, "CURRENT_AXLE_LIFT" : 0}
    lever_0B = {"MAX_AXLE_LIFT" : 3000, "CURRENT_AXLE_LIFT" : 0}
    lever_0C = {"MAX_AXLE_LIFT" : 3000, "CURRENT_AXLE_LIFT" : 0}
    
    tilt_steps = {"MAX_LEFT_TILT" : -4, "MAX_RIGHT_TILT" : 4, "CURRENT_TILT" : 0}
    
    
    def __init__(self, robot_type, robot_version):
        self.robot_type = robot_type
        self.robot_version = robot_version
        
    def invoke_self_test(self):
        # Operator will place the robot on the test stand for this full routine of the system.
        pass
        
    def print_robot_object():
        print("Boo!")
        
    