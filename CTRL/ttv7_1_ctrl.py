#!/usr/bin/python

################################################################################################################
#
# Program  : ttv7_1_ctrl.py
# Version  : 7.0.0.1
#
# Aauthor  : Pablo Cordoba 
# Updated  : 05/02/2026 at 09:00 (Thursday)
# Function : Connects to the Robot's server application to allow full control for R&D test purposes.
#
# Copyright: Tubetech Industrial 2025.
#
 ################################################################################################################


from tkinter import *
from tkinter.ttk import Progressbar
from tkinter.ttk import Combobox
from tkinter.ttk import Notebook
from tkinter.ttk import Treeview
from tkinter.filedialog import askopenfilename
from PIL import Image, ImageTk
import tkinter.font
import tkinter.messagebox
import customtkinter
from CTkPopupKeyboard import PopupNumpad
from distutils.cmd import Command
import socket
from time import sleep,time
import subprocess
import evdev
import datetime as dt
import threading
import read_excel_data as excel
import openpyxl
import io
import struct
import cv2
import numpy as np
import queue
import ast


# ------------------ Communications setup -------------------------------------------------------------------------------------
HOST = '192.168.0.60'
PORT = 22001


customtkinter.set_appearance_mode("Light")
  
last_unit = 'Metric'
controller_active = "on"

climb_button_state = 0
tubes_across = 0
furnace_length = 0
lance_length = 100
start_position = 0
finish_position = 0

manual_parameters_saved = False
head_initialised = False
head_homed = False
file_loaded = False
controller = False
connected = False

# Number of cameras connected
NUM_CAMS = 2

# Port numbers for each camera
PORTS = [22002, 22003]

# empty image to set at start and when client disconnets
empty_image = Image.open("/home/pi/Desktop/ROBOT_7/icons/no_camera.png")
images = [empty_image.copy() for _ in range(NUM_CAMS)]
photos = [None] * NUM_CAMS  # Store Tkinter-compatible images

# Queue to store frames for each camera
frame_queues = [queue.Queue(maxsize=1) for _ in range(NUM_CAMS)]


class MainFrame(customtkinter.CTk):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
        self.title("Mark 7 GUI")
        self.geometry('3000x1500')
            
        self.GUI_Tabs = customtkinter.CTkTabview(self, width = 1275, height = 800, fg_color = "white", segmented_button_selected_color = "orange", segmented_button_selected_hover_color = "grey", anchor = 's')
        self.GUI_Tabs.pack()

        self.FlushingTab = self.GUI_Tabs.add("  Flushing  ")
        self.LancingTab = self.GUI_Tabs.add("  Lancing  ")
        self.ManualDriveTab = self.GUI_Tabs.add("  Manual Drive  ")
        self.CamerasTab = self.GUI_Tabs.add("  Cameras  ")
        self.SettingsAndParametersTab = self.GUI_Tabs.add("  Settings  ")

        custom_font = ("Bahnschrift", 30, 'bold')
        self.GUI_Tabs._segmented_button.configure(font=custom_font)
        
        self.numpad = PopupNumpad()
        self.numpad.bind("<FocusOut>", lambda e: self.numpad._iconify())
        
        
        
        

        ### FLUSHING TAB WIDGETS ###
        
        
        
        self.ControllerVar = customtkinter.StringVar(value = "on")
        
        self.ControllerIcon = customtkinter.CTkCanvas(self.FlushingTab, bg = 'white', width = 110, height = 80, highlightthickness = 0)
        self.ControllerIcon.place(x = 25, y = 5)
        
        self.ControllerIconi = Image.open("/home/pi/Desktop/ROBOT_7/icons/controller_icon.png")
        self.ControllerIconimg = ImageTk.PhotoImage(self.ControllerIconi.resize((90, 80)))
        self.ControllerIcon.create_image(0, 0, image = self.ControllerIconimg, anchor=NW)
        
        self.ControllerSwitch = customtkinter.CTkSwitch(self.FlushingTab, text = "", variable = self.ControllerVar, onvalue = "on", offvalue = "off", switch_width = 75, switch_height = 40, progress_color = "orange")
        self.ControllerSwitch.place(x = 125, y = 25)
        
        
        self.LightsButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/lights_icon.png"), size=(90,90))
        self.LightsButton = customtkinter.CTkButton(self.FlushingTab, text = "", fg_color = "transparent", hover_color = "orange", cursor = "arrow", state = "normal", image = self.LightsButtonimg, anchor = "center" , width = 120, height = 120, border_width=3, corner_radius=8, command = self.LightsToggle)
        self.LightsButton.place(x = 25, y = 125)
        self.LightsLabel = customtkinter.CTkLabel(self.FlushingTab, text = "Lights", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31)
        self.LightsLabel.place(x = 25, y = 90)

        self.SpeedLabel = customtkinter.CTkLabel(self.FlushingTab, text = "Speed", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31)
        self.SpeedLabel.place(x = 25, y = 300)
        
        self.SpeedVarLabel = customtkinter.CTkLabel(self.FlushingTab, text = "20%", text_color = "white", fg_color = "orange", font = ("Bahnschrift", 28), cursor = "arrow", state = "normal", width = 120, height = 50, corner_radius=8 )
        self.SpeedVarLabel.place(x = 25, y = 340)
        
        self.FasterButton = customtkinter.CTkButton(self.FlushingTab, text = "+", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 32), text_color = "black", cursor = "arrow", state = "normal", width = 60, height = 60, border_width=3, corner_radius=8, command = Faster)
        self.FasterButton.place(x = 25, y = 410)
        
        self.SlowerButton = customtkinter.CTkButton(self.FlushingTab, text = "-", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 45), text_color = "black", cursor = "arrow", state = "normal", width = 60, height = 60, border_width=3, corner_radius=8, command = Slower)
        self.SlowerButton.place(x = 95, y = 410)
        
        self.LoadFileLabel = customtkinter.CTkLabel(self.FlushingTab, text = "Load File ", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 32,)
        self.LoadFileLabel.place(x = 25, y = 550)
        self.LoadFileButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/USB-Logo.png"), size=(60,60))
        self.LoadFileButton = customtkinter.CTkButton(self.FlushingTab, text = "", fg_color = "transparent", hover_color = "orange", cursor = "arrow", state = "normal", image = self.LoadFileButtonimg, compound = "top", width = 120, height = 120, border_width=3, corner_radius=8, command = self.LoadFile)
        self.LoadFileButton.place(x = 25, y = 585)
        
        
        
        self.ClimbDirectionLabel = customtkinter.CTkLabel(self.FlushingTab, text = "Climb Direction:  ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.ClimbDirectionLabel.place(x = 220, y = 130)
        self.ClimbDirectionComboBoxVar = customtkinter.StringVar(value="Left")
        self.ClimbDirectionComboBox = customtkinter.CTkComboBox(self.FlushingTab, height = 50, width = 175, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["Left", "Right"], variable = self.ClimbDirectionComboBoxVar)
        self.ClimbDirectionComboBox.place(x = 445, y = 125)
        
        
        self.RunsPerTubeLabel = customtkinter.CTkLabel(self.FlushingTab, text = "Runs per tube:  ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.RunsPerTubeLabel.place(x = 750, y = 130)
        self.RunsPerTubeComboBoxVar = customtkinter.StringVar(value="1")
        self.RunsPerTubeComboBox = customtkinter.CTkComboBox(self.FlushingTab, height = 50, width = 175, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["1", "2", "3","4"], variable = self.RunsPerTubeComboBoxVar)
        self.RunsPerTubeComboBox.place(x = 970, y = 125)
        
        
        self.SetStartPositionLabel = customtkinter.CTkLabel(self.FlushingTab, text = "Set Start Position:  ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.SetStartPositionLabel.place(x = 220, y = 230)
        self.SetStartPositionComboBoxVar = customtkinter.StringVar(value="Set Start & Finish")
        self.SetStartPositionComboBox = customtkinter.CTkComboBox(self.FlushingTab, height = 50, width = 275, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["Set Start & Finish", "Manual Distance"], variable = self.SetStartPositionComboBoxVar)
        self.SetStartPositionComboBox.place(x = 470, y = 222)
        self.SetStartPositionComboBoxVar.trace_add('write', self.SetStartPositionOptions)
        
        
        self.AutomaticRunSpeedLabel = customtkinter.CTkLabel(self.FlushingTab, text = "Speed:  ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.AutomaticRunSpeedLabel.place(x = 850, y = 230)
        self.AutomaticRunSpeedComboBoxVar = customtkinter.StringVar(value="Medium")
        self.AutomaticRunSpeedComboBox = customtkinter.CTkComboBox(self.FlushingTab, height = 50, width = 175, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["Slow", "Medium", "Fast"], variable = self.AutomaticRunSpeedComboBoxVar)
        self.AutomaticRunSpeedComboBox.place(x = 970, y = 222)
        
        

        self.BanksFrame = customtkinter.CTkFrame(self.FlushingTab, width=350, height=200, border_width = 3)
        self.BanksFrame.place(x = 220, y = 325)

        self.BanksLabel = customtkinter.CTkLabel(self.BanksFrame, text = "Bank:", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.BanksLabel.place(x = 50, y = 20)
        self.BanksComboBoxVar = customtkinter.StringVar(value="0")
        self.BanksComboBox = customtkinter.CTkComboBox(self.BanksFrame, height = 50, width = 100, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["0"], variable = self.BanksComboBoxVar)
        self.BanksComboBox.place(x = 150, y = 15)
        self.BanksComboBoxVar.trace_add('write', self.BanksOptions)

        self.TubesAcrossLabel = customtkinter.CTkLabel(self.BanksFrame, text = "Tubes across:", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 22), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.TubesAcrossLabel.place(x = 50, y = 90)
        self.TubesAcrossVarLabel = customtkinter.CTkLabel(self.BanksFrame, text = "N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 22), cursor = "arrow", state = "normal", width = 50, height = 31 )
        self.TubesAcrossVarLabel.place(x = 205, y = 90)

        self.TubesDownLabel = customtkinter.CTkLabel(self.BanksFrame, text = "Tubes down:", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 22), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.TubesDownLabel.place(x = 50, y = 150)
        self.TubesDownVarLabel = customtkinter.CTkLabel(self.BanksFrame, text = "N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 22), cursor = "arrow", state = "normal", width = 50, height = 31 )
        self.TubesDownVarLabel.place(x = 205, y = 150)
        

        self.StartPositionFrame = customtkinter.CTkFrame(self.FlushingTab, width=550, height=200, border_width = 3)
        self.StartPositionFrame.place(x = 650, y = 325)

        self.StartPositionLabel = customtkinter.CTkLabel(self.StartPositionFrame, text = "Start\nPosition", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.StartPositionLabel.place(x = 50, y = 25)
        
        self.SaveStartPositionButton = customtkinter.CTkButton(self.StartPositionFrame, text = "Save", fg_color = "orange", hover_color = "white", font = ("Bahnschrift", 26), text_color = "black", cursor = "arrow", state = "normal", width = 100, height = 55, border_width=3, corner_radius=8, command = SaveStartPosition)
        self.SaveStartPositionButton.place(x = 50, y = 100)
        
        self.FinishPositionLabel = customtkinter.CTkLabel(self.StartPositionFrame, text = "Finish\nPosition", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.FinishPositionLabel.place(x = 250, y = 25)
        
        self.SaveFinishPositionButton = customtkinter.CTkButton(self.StartPositionFrame, text = "Save", fg_color = "orange", hover_color = "white", font = ("Bahnschrift", 26), text_color = "black", cursor = "arrow", state = "normal", width = 100, height = 55, border_width=3, corner_radius=8, command = SaveFinishPosition)
        self.SaveFinishPositionButton.place(x = 250, y = 100)
        
        self.DriveForwardButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/up_arrow.png"), size=(40,40))
        self.DriveForwardButton3 = customtkinter.CTkButton(self.StartPositionFrame, text = "Forward", fg_color = "white", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.DriveForwardButtonimg, compound = "top", width = 130, height = 60, border_width=3, corner_radius=8, command = Forward)
        self.DriveForwardButton3.place(x = 400, y =  15)
        
        self.DriveBackwardsButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/down_arrow.png"), size=(40,40))
        self.DriveBackwardsButton3 = customtkinter.CTkButton(self.StartPositionFrame, text = "Backward", fg_color = "white", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.DriveBackwardsButtonimg, compound = "top", width = 130, height = 60, border_width=3, corner_radius=8, command = Reverse)
        self.DriveBackwardsButton3.place(x = 400, y = 105)

        
        
        
        
        self.FurnaceLengthLabel2 = customtkinter.CTkLabel(self.StartPositionFrame, text = "Furnace Length:  ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.FurnaceLengthVarLabel = customtkinter.CTkLabel(self.StartPositionFrame, text = "N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
    
    


        self.StopButton1 = customtkinter.CTkButton(self.FlushingTab, text = "STOP", fg_color = "red", hover_color = "red", font = ("Bahnschrift", 34), text_color = "yellow", cursor = "arrow", state = "normal", width = 160, height = 140, border_width=3, corner_radius=8, command = Stop)
        self.StopButton1.place(x = 530, y = 565)
        
        self.PauseButton = customtkinter.CTkButton(self.FlushingTab, text = "PAUSE", fg_color = "blue", hover_color = "blue", font = ("Bahnschrift", 34), text_color = "yellow", cursor = "arrow", state = "normal", width = 160, height = 140, border_width=3, corner_radius=8, command = self.PauseToggle)
        self.PauseButton.place(x = 730, y = 565)


        self.StartAutomaticRunButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/1933666-200.png"), size=(80,80))
        self.StartAutomaticRunButton = customtkinter.CTkButton(self.FlushingTab, text = "Start Run", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 24), text_color = "black", cursor = "arrow", state = "normal", image = self.StartAutomaticRunButtonimg, compound = "top", width = 200, height = 140, border_width=3, corner_radius=8, command = Automatic)
        self.StartAutomaticRunButton.place(x = 930, y = 565)
        
        
        self.TTLogo = customtkinter.CTkCanvas(self.FlushingTab, bg = 'white', width = 300, height = 80, highlightthickness = 0)
        self.TTLogo.place(x = 960, y = 5)
        
        self.TTLogoi = Image.open("/home/pi/Desktop/ROBOT_7/icons/logo.png")
        self.TTLogoimg = ImageTk.PhotoImage(self.TTLogoi.resize((275, 70)))
        self.TTLogo.create_image(10, 10, image = self.TTLogoimg, anchor=NW)



        ### LANCING TAB WIDGETS ###

       
       
        self.LineButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "black", hover_color = "black", cursor = "arrow", state = "disabled",  width = 2, height = 650, border_width=3, corner_radius=8)
        self.LineButton.place(x = 450, y = 75)

        self.LineButton2 = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "black", hover_color = "black", cursor = "arrow", state = "disabled",  width = 760, height = 2, border_width=3, corner_radius=8)
        self.LineButton2.place(x = 500, y = 250)

        self.LineButton3 = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "black", hover_color = "black", cursor = "arrow", state = "disabled",  width = 760, height = 2, border_width=3, corner_radius=8)
        self.LineButton3.place(x = 500, y = 550)
       
        self.ManualHeadControlLabel = customtkinter.CTkLabel(self.LancingTab, text = "Head Controls", text_color = "white", fg_color = "orange", anchor='w', font = ("Bahnschrift", 28), cursor = "arrow", state = "normal", width = 140, height = 31, corner_radius=8 )
        self.ManualHeadControlLabel.place(x = 500, y = 15)
        
        
        
        self.InitHeadButton = customtkinter.CTkButton(self.LancingTab, text = "Initialise\n Head", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 24), text_color = "black", cursor = "arrow", state = "normal", compound = "top", width = 160, height = 120, border_width=3, corner_radius=8, command = InitHeadMotors )
        self.InitHeadButton.place(x = 50, y = 25)
        
        self.HomeButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/home.png"), size=(60,60))
        self.HomeButton = customtkinter.CTkButton(self.LancingTab, text = "Home Head", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 24), text_color = "black", cursor = "arrow", state = "normal", image = self.HomeButtonimg, compound = "top", width = 160, height = 120, border_width=3, corner_radius=8, command = ManualHomeHead )
        self.HomeButton.place(x = 230, y = 25)
        
        
        self.AngleAButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/down_left_arrow.png"), size=(80,80))
        self.AngleAButton2 = customtkinter.CTkButton(self.LancingTab, text = "Angle A", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 24), text_color = "black", cursor = "arrow", state = "normal", image = self.AngleAButtonimg, compound = "top", width = 160, height = 120, border_width=3, corner_radius=8, command = LanceAngleA)
        self.AngleAButton2.place(x = 50, y = 180)

        self.AngleBButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/down_right_arrow.png"), size=(80,80))
        self.AngleBButton2 = customtkinter.CTkButton(self.LancingTab, text = "Angle B", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 24), text_color = "black", cursor = "arrow", state = "normal", image = self.AngleBButtonimg, compound = "top", width = 160, height = 120, border_width=3, corner_radius=8, command = LanceAngleB)
        self.AngleBButton2.place(x = 230, y = 180)
        
        self.AnglesValuesLabel = customtkinter.CTkLabel(self.LancingTab, text = "Slide: N/A \n Roll: N/A ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 20), cursor = "arrow", state = "normal", width = 60, height = 31, corner_radius=8 )
        self.AnglesValuesLabel.place(x = 100, y = 330)
        
        self.UpdateAnglesButton = customtkinter.CTkButton(self.LancingTab, text = "Update", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 20), text_color = "black", cursor = "arrow", state = "normal", compound = "top", width = 70, height = 50, border_width=3, corner_radius=8 )
        self.UpdateAnglesButton.place(x = 240, y = 330)
        
        
        self.OscillationFrame = customtkinter.CTkFrame(self.LancingTab, width=380, height=175, border_width = 3)
        self.OscillationFrame.place(x = 30, y = 420)
        
        self.OscillationLabel = customtkinter.CTkLabel(self.OscillationFrame, text = "Oscillation", fg_color = "#013E50", text_color = "white", anchor='w', font = ("Bahnschrift", 24), cursor = "arrow", state = "normal", width = 70, height = 31, corner_radius=8 )
        self.OscillationLabel.place(x = 120, y = 10)
        
        self.StartOscillationLabel = customtkinter.CTkLabel(self.OscillationFrame, text = "Start:", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 22), cursor = "arrow", state = "normal", width = 80, height = 31 )
        self.StartOscillationLabel.place(x = 25, y = 57)
        self.StartOscillationComboBoxVar = customtkinter.StringVar(value="30")
        self.StartOscillationComboBox = customtkinter.CTkComboBox(self.OscillationFrame, height = 50, width = 130, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["30", "40", "50", "60"], variable = self.StartOscillationComboBoxVar)
        self.StartOscillationComboBox.place(x = 100, y = 50)
        
        self.FinishOscillationLabel = customtkinter.CTkLabel(self.OscillationFrame, text = "Finish:", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 22), cursor = "arrow", state = "normal", width = 80, height = 31 )
        self.FinishOscillationLabel.place(x = 20, y = 117)
        self.FinishOscillationComboBoxVar = customtkinter.StringVar(value="60")
        self.FinishOscillationComboBox = customtkinter.CTkComboBox(self.OscillationFrame, height = 50, width = 130, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["60", "70", "80", "90"], variable = self.FinishOscillationComboBoxVar)
        self.FinishOscillationComboBox.place(x = 100, y = 110)
        
        self.OscillationVar = customtkinter.BooleanVar(value = False)
        
        self.OscillationSwitch = customtkinter.CTkSwitch(self.OscillationFrame, text = "", variable = self.OscillationVar, switch_width = 75, switch_height = 40, progress_color = "orange", command = OscillateLance)
        self.OscillationSwitch.place(x = 270, y = 80)
        
        
    
        self.StopButton3 = customtkinter.CTkButton(self.LancingTab, text = "STOP", fg_color = "red", hover_color = "red", font = ("Bahnschrift", 34), text_color = "yellow", cursor = "arrow", state = "normal", width = 250, height = 100, border_width=3, corner_radius=8, command = Stop)
        self.StopButton3.place(x = 80, y = 625)



        self.SlideControlLabel = customtkinter.CTkLabel(self.LancingTab, text = "Slide", fg_color = "#013E50", text_color = "white", anchor='w', font = ("Bahnschrift", 24), cursor = "arrow", state = "normal", width = 70, height = 31, corner_radius=8 )
        self.SlideControlLabel.place(x = 500, y = 75)
        
        self.SlideValueLabel = customtkinter.CTkLabel(self.LancingTab, text = "Current Distance: N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 22), cursor = "arrow", state = "normal", width = 140, height = 31, corner_radius=8 )
        self.SlideValueLabel.place(x = 500, y = 120)

        self.SlideTextBox = customtkinter.CTkTextbox(self.LancingTab, font = ("Bahnschrift", 22), width = 100, height = 53, border_width=3, corner_radius=8)
        self.SlideTextBox.place(x = 500, y = 166)
        self.SlideTextBox.bind("<Button-1>", lambda e: self.ShowNumpad(self.SlideTextBox))
        self.SlideDistanceSendButton = customtkinter.CTkButton(self.LancingTab, text = "Send", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 100, height = 55, border_width=3, corner_radius=8, command = SlideToAngle)
        self.SlideDistanceSendButton.place(x = 620, y = 165)

        self.SlideLeftButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/left_arrow.png"), size=(80,80))
        self.SlideLeftButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.SlideLeftButtonimg, compound = "top", width = 100, height = 80, border_width=3, corner_radius=8, command = SlideLeft)
        self.SlideLeftButton.place(x = 875, y = 125)

        self.SlideRightButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/right_arrow.png"), size=(80,80))
        self.SlideRightButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.SlideRightButtonimg, compound = "top", width = 100, height = 80, border_width=3, corner_radius=8, command = SlideRight)
        self.SlideRightButton.place(x = 1000, y = 125)
        
        self.HomeButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/home.png"), size=(60,60))
        self.SlideHomeButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 24), text_color = "black", cursor = "arrow", state = "normal", image = self.HomeButtonimg, compound = "top", width = 80, height = 80, border_width=3, corner_radius=8, command = SlideHome )
        self.SlideHomeButton.place(x = 1175, y = 130)


        self.RollControlLabel = customtkinter.CTkLabel(self.LancingTab, text = "Roll", fg_color = "#013E50", text_color = "white", anchor='w', font = ("Bahnschrift", 24), cursor = "arrow", state = "normal", width = 60, height = 31, corner_radius=8 )
        self.RollControlLabel.place(x = 500, y = 270)

        self.RollAngles = customtkinter.CTkCanvas(self.LancingTab, bg = 'white', width = 260, height = 210, highlightthickness = 0)
        self.RollAngles.place(x = 500, y = 305)
        
        self.RollAnglesi = Image.open("/home/pi/Desktop/ROBOT_7/icons/roll_angles_circle.png")
        self.RollAnglesimg = ImageTk.PhotoImage(self.RollAnglesi.resize((250, 175)))
        self.RollAngles.create_image(10, 30, image = self.RollAnglesimg, anchor=NW)
        
        self.RollValueLabel = customtkinter.CTkLabel(self.LancingTab, text = "Current Angle: N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 22), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.RollValueLabel.place(x = 880, y = 280)

        self.RollTextBox = customtkinter.CTkTextbox(self.LancingTab, font = ("Bahnschrift", 22), width = 100, height = 53, border_width=3, corner_radius=8)
        self.RollTextBox.place(x = 880, y = 326)
        self.RollTextBox.bind("<Button-1>", lambda e: self.ShowNumpad(self.RollTextBox))
        self.RollAngleSendButton = customtkinter.CTkButton(self.LancingTab, text = "Send", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 100, height = 55, border_width=3, corner_radius=8, command = RollToAngle)
        self.RollAngleSendButton.place(x = 1000, y = 323)


        self.RotateLeftButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/rotate_left_arrow.png"), size=(80,80))
        self.RotateLeftButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.RotateLeftButtonimg, compound = "top", width = 100, height = 80, border_width=3, corner_radius=8, command = RollAnticlock)
        self.RotateLeftButton.place(x = 875, y = 430)

        self.RotateRightButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/rotate_right_arrow.png"), size=(80,80))
        self.RotateRightButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.RotateRightButtonimg, compound = "top", width = 100, height = 80, border_width=3, corner_radius=8, command = RollClock)
        self.RotateRightButton.place(x = 1000, y = 430)
        
        self.HomeButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/home.png"), size=(60,60))
        self.RollHomeButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 24), text_color = "black", cursor = "arrow", state = "normal", image = self.HomeButtonimg, compound = "top", width = 80, height = 80, border_width=3, corner_radius=8, command = RollHome )
        self.RollHomeButton.place(x = 1175, y = 360)



        self.PitchControlLabel = customtkinter.CTkLabel(self.LancingTab, text = "Pitch", fg_color = "#013E50", text_color = "white", anchor='w', font = ("Bahnschrift", 24), cursor = "arrow", state = "normal", width = 60, height = 31, corner_radius=8 )
        self.PitchControlLabel.place(x = 500, y = 570)

        self.PitchAngles = customtkinter.CTkCanvas(self.LancingTab, bg = 'white', width = 130, height = 130, highlightthickness = 0)
        self.PitchAngles.place(x = 500, y = 600)

        self.PitchAnglesi = Image.open("/home/pi/Desktop/ROBOT_7/icons/pitch_degrees_icon.jpg")
        self.PitchAnglesimg = ImageTk.PhotoImage(self.PitchAnglesi.resize((125, 125)))
        self.PitchAngles.create_image(10, 10, image = self.PitchAnglesimg, anchor=NW)

        self.PitchValueLabel = customtkinter.CTkLabel(self.LancingTab, text = "Current Angle: N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 22), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.PitchValueLabel.place(x = 700, y = 600)

        self.PitchTextBox = customtkinter.CTkTextbox(self.LancingTab, width = 100, height = 53, font = ("Bahnschrift", 22), border_width=3, corner_radius=8)
        self.PitchTextBox.place(x = 700, y = 652)
        self.PitchTextBox.bind("<Button-1>", lambda e: self.ShowNumpad(self.PitchTextBox))
        self.PitchAngleSendButton = customtkinter.CTkButton(self.LancingTab, text = "Send", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 100, height = 55, border_width=3, corner_radius=8, command = PitchToAngle)
        self.PitchAngleSendButton.place(x = 820, y = 652)

        self.PitchUpButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/left_up_arrow.png"), size=(70,70))
        self.PitchUpButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.PitchUpButtonimg, compound = "top", width = 95, height = 70, border_width=3, corner_radius=8, command = PitchUp)
        self.PitchUpButton.place(x = 1000, y = 560)

        self.PitchDownButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/left_down_arrow.png"), size=(70,70))
        self.PitchDownButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.PitchDownButtonimg, compound = "top", width = 95, height = 70, border_width=3, corner_radius=8, command = PitchDown)
        self.PitchDownButton.place(x = 1000, y = 650)
        
        self.HomeButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/home.png"), size=(60,60))
        self.PitchHomeButton = customtkinter.CTkButton(self.LancingTab, text = "", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 24), text_color = "black", cursor = "arrow", state = "normal", image = self.HomeButtonimg, compound = "top", width = 80, height = 80, border_width=3, corner_radius=8, command = PitchHome )
        self.PitchHomeButton.place(x = 1175, y = 610)
        
        

        ### MANUAL DRIVE TAB WIDGETS ###


        
        self.ControllerIcon2 = customtkinter.CTkCanvas(self.ManualDriveTab, bg = 'white', width = 110, height = 80, highlightthickness = 0)
        self.ControllerIcon2.place(x = 25, y = 5)
        
        self.ControllerIconi2 = Image.open("/home/pi/Desktop/ROBOT_7/icons/controller_icon.png")
        self.ControllerIconimg2= ImageTk.PhotoImage(self.ControllerIconi.resize((90, 80)))
        self.ControllerIcon2 .create_image(0, 0, image = self.ControllerIconimg, anchor=NW)
        
        self.ControllerSwitch2 = customtkinter.CTkSwitch(self.ManualDriveTab, text = "", variable = self.ControllerVar, onvalue = "on", offvalue = "off", switch_width = 75, switch_height = 40, progress_color = "orange")
        self.ControllerSwitch2.place(x = 125, y = 25)
        
        
        self.LightsButtonimg2 = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/lights_icon.png"), size=(90,90))
        self.LightsButton2 = customtkinter.CTkButton(self.ManualDriveTab, text = "", fg_color = "transparent", hover_color = "orange", cursor = "arrow", state = "normal", image = self.LightsButtonimg2, anchor = "center" , width = 120, height = 120, border_width=3, corner_radius=8, command = self.LightsToggle)
        self.LightsButton2.place(x = 25, y = 125)
        self.LightsLabel2 = customtkinter.CTkLabel(self.ManualDriveTab, text = "Lights", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31)
        self.LightsLabel2.place(x = 25, y = 90)

        
        self.SpeedLabel2 = customtkinter.CTkLabel(self.ManualDriveTab, text = "Speed", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31)
        self.SpeedLabel2.place(x = 25, y = 300)
        
        self.SpeedVarLabel2 = customtkinter.CTkLabel(self.ManualDriveTab, text = "20%", text_color = "white", fg_color = "orange", font = ("Bahnschrift", 28), cursor = "arrow", state = "normal", width = 120, height = 50, corner_radius=8 )
        self.SpeedVarLabel2.place(x = 25, y = 340)
        
        self.FasterButton2 = customtkinter.CTkButton(self.ManualDriveTab, text = "+", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 32), text_color = "black", cursor = "arrow", state = "normal", width = 60, height = 60, border_width=3, corner_radius=8, command = Faster)
        self.FasterButton2.place(x = 25, y = 410)
        
        self.SlowerButton2 = customtkinter.CTkButton(self.ManualDriveTab, text = "-", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 45), text_color = "black", cursor = "arrow", state = "normal", width = 60, height = 60, border_width=3, corner_radius=8, command = Slower)
        self.SlowerButton2.place(x = 95, y = 410)

        
        self.DriveForwardButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/up_arrow.png"), size=(90,90))
        self.DriveForwardButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Forward", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", image = self.DriveForwardButtonimg, compound = "top", width = 180, height = 160, border_width=3, corner_radius=8, command = Forward)
        self.DriveForwardButton.place(x = 550, y =  50)

        self.DriveBackwardsButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/down_arrow.png"), size=(90,90))
        self.DriveBackwardsButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Backward", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", image = self.DriveBackwardsButtonimg, compound = "top", width = 180, height = 160, border_width=3, corner_radius=8, command = Reverse)
        self.DriveBackwardsButton.place(x = 550, y = 450)

        self.ClimbLeftButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/left_arrow_curved.png"), size=(100,100))
        self.ClimbLeftButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Climb left", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", image = self.ClimbLeftButtonimg, compound = "top", width = 180, height = 160, border_width=3, corner_radius=8, command = LeftClimb)
        self.ClimbLeftButton.place(x = 300, y = 250)

        self.ClimbRightButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/right_arrow_curved.png"), size=(100,100))
        self.ClimbRightButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Climb right", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", image = self.ClimbRightButtonimg, compound = "top", width = 180, height = 160, border_width=3, corner_radius=8, command = RightClimb)
        self.ClimbRightButton.place(x = 800, y = 250)

        self.StopButton2 = customtkinter.CTkButton(self.ManualDriveTab, text = "STOP", fg_color = "red", hover_color = "red", font = ("Bahnschrift", 34), text_color = "yellow", cursor = "arrow", state = "normal", width = 180, height = 160, border_width=3, corner_radius=8, command = Stop)
        self.StopButton2.place(x = 550, y = 250)
        
        self.LevelButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Level Robot", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = Level)
        self.LevelButton.place(x = 25, y = 530)
        
        self.TiltRightButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Tilt Right", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = TiltRight)
        self.TiltRightButton.place(x = 900, y = 560)
        
        self.TiltLeftButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Tilt Left", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = TiltLeft)
        self.TiltLeftButton.place(x = 900, y = 630)
        
        self.Axle1UpButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Axle 1 Up", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = Axle1Up)
        self.Axle1UpButton.place(x = 1100, y = 50)
        
        self.Axle1DownButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Axle 1 Down", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = Axle1Down)
        self.Axle1DownButton.place(x = 1100, y = 120)
        
        self.Axle2UpButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Axle 2 Up", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = Axle2Up)
        self.Axle2UpButton.place(x = 1100, y = 220)
        
        self.Axle2DownButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Axle 2 Down", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = Axle2Down)
        self.Axle2DownButton.place(x = 1100, y = 290)
        
        self.Axle3UpButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Axle 3 Up", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = Axle3Up)
        self.Axle3UpButton.place(x = 1100, y = 390)
        
        self.Axle3DownButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Axle 3 Down", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = Axle3Down)
        self.Axle3DownButton.place(x = 1100, y = 460)
        
        self.Axle4UpButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Axle 4 Up", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = Axle4Up)
        self.Axle4UpButton.place(x = 1100, y = 560)
        
        self.Axle4DownButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Axle 4 Down", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 62, border_width=3, corner_radius=8, command = Axle4Down)
        self.Axle4DownButton.place(x = 1100, y = 630)
        
        self.ReInitialiseButton = customtkinter.CTkButton(self.ManualDriveTab, text = "Re-initialise\nMotors", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", width = 160, height = 80, border_width=3, corner_radius=8, command = Initialise)
        self.ReInitialiseButton.place(x = 25, y = 610)
        
        
        
        


        
        ### CAMERAS WIDGETS ###
        
        self.BackCameraLabel = customtkinter.CTkLabel(self.CamerasTab, text = "Back Camera", text_color = "white", fg_color = "orange", anchor='w', font = ("Bahnschrift", 28), cursor = "arrow", state = "normal", width = 90, height = 31, corner_radius=8 )
        self.BackCameraLabel.place(x = 220, y = 25)
        
        self.Camera1Frame = customtkinter.CTkFrame(self.CamerasTab, width=540, height=480, border_width = 3)
        self.Camera1Frame.place(x = 50, y = 75)
        
        self.FrontCameraLabel = customtkinter.CTkLabel(self.CamerasTab, text = "Front Camera", text_color = "white", fg_color = "orange", anchor='w', font = ("Bahnschrift", 28), cursor = "arrow", state = "normal", width = 90, height = 31, corner_radius=8 )
        self.FrontCameraLabel.place(x = 850, y = 25)
        
        self.Camera2Frame = customtkinter.CTkFrame(self.CamerasTab, width=540, height=480, border_width = 3)
        self.Camera2Frame.place(x = 670, y = 75)
        
        
        self.DriveForwardButton2 = customtkinter.CTkButton(self.CamerasTab, text = "Forward", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", image = self.DriveForwardButtonimg, compound = "top", width = 160, height = 145, border_width=3, corner_radius=8, command = Forward)
        self.DriveForwardButton2.place(x = 860, y =  575)

        self.DriveBackwardsButton2 = customtkinter.CTkButton(self.CamerasTab, text = "Backward", fg_color = "transparent", hover_color = "orange", font = ("Bahnschrift", 22), text_color = "black", cursor = "arrow", state = "normal", image = self.DriveBackwardsButtonimg, compound = "top", width = 160, height = 145, border_width=3, corner_radius=8, command = Reverse)
        self.DriveBackwardsButton2.place(x = 240, y = 575)
        
        self.StopButton4 = customtkinter.CTkButton(self.CamerasTab, text = "STOP", fg_color = "red", hover_color = "red", font = ("Bahnschrift", 34), text_color = "yellow", cursor = "arrow", state = "normal", width = 160, height = 145, border_width=3, corner_radius=8, command = Stop)
        self.StopButton4.place(x = 550, y = 575)
        
        
        

        ### SETTINGS AND PARAMETERS TAB WIDGETS ###


       
        self.LineButton4 = customtkinter.CTkButton(self.SettingsAndParametersTab, text = "", fg_color = "black", hover_color = "black", cursor = "arrow", state = "disabled",  width = 2, height = 675, border_width=3, corner_radius=8)
        self.LineButton4.place(x = 625, y = 50)

        self.LineButton5 = customtkinter.CTkButton(self.SettingsAndParametersTab, text = "", fg_color = "black", hover_color = "black", cursor = "arrow", state = "disabled",  width = 520, height = 2, border_width=3, corner_radius=8)
        self.LineButton5.place(x = 50, y = 320)
       
        
        self.RobotParametersLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Robot", text_color = "white", fg_color = "orange", anchor='w', font = ("Bahnschrift", 28), cursor = "arrow", state = "normal", width = 90, height = 31, corner_radius=8 )
        self.RobotParametersLabel.place(x = 260, y = 15)

        self.FurnaceParametersLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Furnace", text_color = "white", fg_color = "orange", anchor='w', font = ("Bahnschrift", 28), cursor = "arrow", state = "normal", width = 120, height = 31, corner_radius=8 )
        self.FurnaceParametersLabel.place(x = 250, y = 340)


        self.wheel_sizeLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Wheels Size: ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.wheel_sizeLabel.place(x = 50, y = 75)
        

        self.wheel_sizeComboBoxVar = customtkinter.StringVar(value="Small")
        self.wheel_sizeComboBox = customtkinter.CTkComboBox(self.SettingsAndParametersTab, height = 50, width = 175, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["Small", "Big"], variable = self.wheel_sizeComboBoxVar)
        self.wheel_sizeComboBox.place(x = 240, y = 70)


        self.LanceLengthLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Lance Length: ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.LanceLengthLabel.place(x = 50, y = 165)
        self.LanceLengthUnitLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "(Centimeters)", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 24), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.LanceLengthUnitLabel.place(x = 447, y = 165)

        self.LanceLengthComboBoxVar = customtkinter.StringVar(value=lance_length)
        self.LanceLengthComboBox = customtkinter.CTkComboBox(self.SettingsAndParametersTab, height = 50, width = 175, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["60", "80", "100", "120"], variable = self.LanceLengthComboBoxVar)
        self.LanceLengthComboBox.place(x = 245, y = 160)


        self.SaveParametersButton = customtkinter.CTkButton(self.SettingsAndParametersTab, text = "Save", fg_color = "orange", hover_color = "white", font = ("Bahnschrift", 26), text_color = "black", cursor = "arrow", state = "normal", width = 100, height = 55, border_width=3, corner_radius=8, command = self.SaveRobotParameters)
        self.SaveParametersButton.place(x = 260, y = 240)

    
        self.FurnaceLengthLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Furnace Length:  ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.FurnaceLengthLabel.place(x = 50, y = 405)
        self.FurnaceLengthTextBox = customtkinter.CTkTextbox(self.SettingsAndParametersTab, width = 130, height = 51, font = ("Bahnschrift", 20), border_width=3, corner_radius=8)
        self.FurnaceLengthTextBox.place(x = 270, y = 400)
        self.FurnaceLengthTextBox.bind("<Button-1>", lambda e: self.ShowNumpad(self.FurnaceLengthTextBox))
        self.FurnaceLengthUnitLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "(Centimetres)", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 24), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.FurnaceLengthUnitLabel.place(x = 418, y = 405)
        


        self.TubeSizeLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Tube Size:  ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.TubeSizeLabel.place(x = 50, y = 495)
        self.TubeSizeComboBoxVar = customtkinter.StringVar(value="Small")
        self.TubeSizeComboBox = customtkinter.CTkComboBox(self.SettingsAndParametersTab, height = 50, width = 175, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["Small", "Medium", "Big"], variable = self.TubeSizeComboBoxVar)
        self.TubeSizeComboBox.place(x = 220, y = 490)

        self.TubesAcrossLabel2 = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Tubes Across:  ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.TubesAcrossLabel2.place(x = 50, y = 585)
        self.TubesAcrossTextBox = customtkinter.CTkTextbox(self.SettingsAndParametersTab, width = 130, height = 51, font = ("Bahnschrift", 20), border_width=3, corner_radius=8)
        self.TubesAcrossTextBox.place(x = 290, y = 580)
        self.TubesAcrossTextBox.bind("<Button-1>", lambda e: self.ShowNumpad(self.TubesAcrossTextBox))
        
        

        self.SaveParametersButton2 = customtkinter.CTkButton(self.SettingsAndParametersTab, text = "Save", fg_color = "orange", hover_color = "white", font = ("Bahnschrift", 26), text_color = "black", cursor = "arrow", state = "normal", width = 100, height = 55, border_width=3, corner_radius=8, command = self.SaveManualParameters)
        self.SaveParametersButton2.place(x = 260, y = 670)

        
        self.DiagnosticsPanelLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Diagnostics Panel", text_color = "white", fg_color = "orange", anchor='w', font = ("Bahnschrift", 28), cursor = "arrow", state = "normal", width = 90, height = 31, corner_radius=8 )
        self.DiagnosticsPanelLabel.place(x = 810, y = 15)

        self.MotorsStatusLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Motors Status: ", fg_color = "#013E50", text_color = "white", anchor='w', font = ("Bahnschrift", 24), cursor = "arrow", state = "normal", width = 140, height = 31, corner_radius=8 )
        self.MotorsStatusLabel.place(x = 675, y = 100)
        
        self.MotorsStatusValuesLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.MotorsStatusValuesLabel.place(x = 685, y = 200)

        self.HeadSensorsLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Head Sensor Homed: ", fg_color = "#013E50", text_color = "white", anchor='w', font = ("Bahnschrift", 24), cursor = "arrow", state = "normal", width = 140, height = 31, corner_radius=8 )
        self.HeadSensorsLabel.place(x = 675, y = 300)

        self.SlideSensorLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Slide: N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.SlideSensorLabel.place(x = 685, y = 350)
           
        self.RollSensorLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Roll: N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.RollSensorLabel.place(x = 850, y = 350)

        self.PitchSensorLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Pitch: N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.PitchSensorLabel.place(x = 1030, y = 350)

        self.IMUStatusLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "IMU Status: ", fg_color = "#013E50", text_color = "white", anchor='w', font = ("Bahnschrift", 24), cursor = "arrow", state = "normal", width = 140, height = 31, corner_radius=8 )
        self.IMUStatusLabel.place(x = 675, y = 400)

        self.IMURollStatusLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Roll: N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.IMURollStatusLabel.place(x = 685, y = 450)

        self.IMUPitchStatusLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Pitch: N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.IMUPitchStatusLabel.place(x = 850, y = 450)

        self.IMUYawStatusLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Yaw: N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.IMUYawStatusLabel.place(x = 1030, y = 450)

        self.GetStatusButton = customtkinter.CTkButton(self.SettingsAndParametersTab, text = "Get Status", fg_color = "orange", hover_color = "white", font = ("Bahnschrift", 26), text_color = "black", cursor = "arrow", state = "normal", width = 150, height = 55, border_width=3, corner_radius=8, command = GetSensorStatus)
        self.GetStatusButton.place(x = 865, y = 525)

        self.UnitsLabel = customtkinter.CTkLabel(self.SettingsAndParametersTab, text = "Units:", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
        self.UnitsLabel.place(x = 1000, y = 650)
        self.UnitsComboBoxVar = customtkinter.StringVar(value="Metric")
        self.UnitsComboBox = customtkinter.CTkComboBox(self.SettingsAndParametersTab, height = 50, width = 175, font = ("Bahnschrift", 24), dropdown_font = ("Bahnschrift", 24), values = ["Metric", "Imperial"], variable = self.UnitsComboBoxVar)
        self.UnitsComboBox.place(x = 1085, y = 642)
        self.UnitsComboBoxVar.trace_add('write', self.UnitsOptions)
        
        self.ReconnectToRobotButton = customtkinter.CTkButton(self.SettingsAndParametersTab, text = "Reconnect to Robot", fg_color = "orange", hover_color = "white", font = ("Bahnschrift", 26), text_color = "black", cursor = "arrow", state = "normal", width = 300, height = 75, border_width=3, corner_radius=8, command = AttemptConnection)
        self.ReconnectToRobotButton.place(x = 650, y = 625)
        
        


    def BanksOptions(self, *args):
        global BanksComboBoxVar, CurrentBank, furnace_length, tubes_across

        CurrentBank = self.BanksComboBox.get()
        current_unit = self.UnitsComboBox.get()

        if CurrentBank != '' and CurrentBank != '0':
        
            CurrentBank = int(CurrentBank) - 1

            tubes_across = int(banks[CurrentBank]["tube_across"])
            TubesDown = int(banks[CurrentBank]["tube_down"])
            furnace_length = int(banks[CurrentBank]["effective_length"]/10)

            self.TubesAcrossTextBox.delete("1.0", 'end-1c')
            self.FurnaceLengthTextBox.delete("1.0", 'end-1c')
    
            self.TubesAcrossVarLabel.configure(text = tubes_across)
            self.TubesDownVarLabel.configure(text = TubesDown)
            self.TubesAcrossTextBox.insert( "1.0", tubes_across)

            if current_unit == 'Metric':

                self.FurnaceLengthTextBox.delete("1.0", 'end-1c')
                self.FurnaceLengthTextBox.insert( "1.0", furnace_length)
                self.FurnaceLengthVarLabel.configure(text = str(furnace_length) + ' cm')

                

            elif current_unit == 'Imperial':

                self.FurnaceLengthTextBox.delete("1.0", 'end-1c')
                self.FurnaceLengthTextBox.insert( "1.0", round(furnace_length*0.0328084,1))
                self.FurnaceLengthVarLabel.configure(text = str(round(furnace_length*0.0328084,1)) + ' ft')

            

    def UnitsOptions(self, *args):
        global UnitsComboBoxVar, current_unit, last_unit

        current_unit = self.UnitsComboBox.get()


        if current_unit == 'Metric'and last_unit != 'Metric':

            lance_length = int(float(self.LanceLengthComboBox.get()))

            self.LanceLengthComboBoxVar = customtkinter.StringVar(value=str(int(lance_length*2.54)))
            self.LanceLengthComboBox.configure(variable = self.LanceLengthComboBoxVar)
            self.FurnaceLengthUnitLabel.configure(text = "(Centimeters)")
            self.LanceLengthUnitLabel.configure(text = "(Centimeters)")
            self.LanceLengthComboBox.configure(values = ["60", "80", "100", "120"])

            if file_loaded or manual_parameters_saved:
                
                self.FurnaceLengthTextBox.delete("1.0", 'end-1c')
                self.FurnaceLengthTextBox.insert( "1.0", furnace_length)
                self.FurnaceLengthVarLabel.configure(text = str(furnace_length) + ' cm')



            last_unit = 'Metric'
             
                    

        elif current_unit == 'Imperial' and last_unit != 'Imperial':

            lance_length = int(float(self.LanceLengthComboBox.get()))
            
            self.LanceLengthComboBoxVar = customtkinter.StringVar(value=str(round(lance_length*0.393701,1)))
            self.LanceLengthComboBox.configure(variable = self.LanceLengthComboBoxVar)
            self.FurnaceLengthUnitLabel.configure(text = "(Feet)")
            self.LanceLengthUnitLabel.configure(text = "(Inches)")
            self.LanceLengthComboBox.configure(values = ["23.6", "31.5", "39.4", "47.2"])
            

            if file_loaded or manual_parameters_saved:

                self.FurnaceLengthTextBox.delete("1.0", 'end-1c')
                self.FurnaceLengthTextBox.insert( "1.0", round(float(furnace_length)*0.0328084,1))
                self.FurnaceLengthVarLabel.configure(text = str(round(float(furnace_length)*0.0328084,1)) + ' in')

            
            last_unit = 'Imperial'





    def SetStartPositionOptions(self, *args):
        global SetStartPositionComboBoxVar, furnace_length
        
        start_position_mode = self.SetStartPositionComboBox.get()
        current_unit = self.UnitsComboBox.get()

        self.StartPositionFrame.place_forget()
        self.FinishPositionLabel.place_forget()
        self.SaveStartPositionButton.place_forget()
        self.SaveFinishPositionButton.place_forget()
        self.DriveForwardButton3.place_forget()
        self.DriveBackwardsButton3.place_forget()
        
        
        self.FurnaceLengthLabel2.place_forget()
        self.FurnaceLengthVarLabel.place_forget()
        
        if start_position_mode == "Set Start & Finish":
            
            
            self.StartPositionFrame = customtkinter.CTkFrame(self.FlushingTab, width=550, height=200, border_width = 3)
            self.StartPositionFrame.place(x = 650, y = 325)
            
            self.StartPositionLabel = customtkinter.CTkLabel(self.StartPositionFrame, text = "Start\nPosition", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
            self.StartPositionLabel.place(x = 50, y = 25)
            
            self.SaveStartPositionButton = customtkinter.CTkButton(self.StartPositionFrame, text = "Save", fg_color = "orange", hover_color = "white", font = ("Bahnschrift", 26), text_color = "black", cursor = "arrow", state = "normal", width = 100, height = 55, border_width=3, corner_radius=8, command = SaveStartPosition)
            self.SaveStartPositionButton.place(x = 50, y = 100)
            
            self.FinishPositionLabel = customtkinter.CTkLabel(self.StartPositionFrame, text = "Finish\nPosition", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
            self.FinishPositionLabel.place(x = 250, y = 25)
            
            self.SaveFinishPositionButton = customtkinter.CTkButton(self.StartPositionFrame, text = "Save", fg_color = "orange", hover_color = "white", font = ("Bahnschrift", 26), text_color = "black", cursor = "arrow", state = "normal", width = 100, height = 55, border_width=3, corner_radius=8, command = SaveFinishPosition)
            self.SaveFinishPositionButton.place(x = 250, y = 100)
            
            self.DriveForwardButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/up_arrow.png"), size=(40,40))
            self.DriveForwardButton3 = customtkinter.CTkButton(self.StartPositionFrame, text = "Forward", fg_color = "white", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.DriveForwardButtonimg, compound = "top", width = 130, height = 60, border_width=3, corner_radius=8, command = Forward)
            self.DriveForwardButton3.place(x = 400, y =  15)
            
            self.DriveBackwardsButtonimg = customtkinter.CTkImage(Image.open("/home/pi/Desktop/ROBOT_7/icons/down_arrow.png"), size=(40,40))
            self.DriveBackwardsButton3 = customtkinter.CTkButton(self.StartPositionFrame, text = "Backward", fg_color = "white", hover_color = "orange", font = ("Bahnschrift", 18), text_color = "black", cursor = "arrow", state = "normal", image = self.DriveBackwardsButtonimg, compound = "top", width = 130, height = 60, border_width=3, corner_radius=8, command = Reverse)
            self.DriveBackwardsButton3.place(x = 400, y = 105)
        

        
        elif start_position_mode == "Manual Distance":
            
        
            self.StartPositionFrame = customtkinter.CTkFrame(self.FlushingTab, width=550, height=200, border_width = 3)
            self.StartPositionFrame.place(x = 650, y = 325)
            
            self.FurnaceLengthLabel2 = customtkinter.CTkLabel(self.StartPositionFrame, text = "Furnace Length:  ", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
            self.FurnaceLengthLabel2.place(x = 50, y = 75)
            
            if manual_parameters_saved == True or file_loaded == True:
                
                if current_unit == 'Metric':
                    self.FurnaceLengthVarLabel.configure(text = str(furnace_length) + ' cm')
                elif current_unit == 'Imperial':
                    self.FurnaceLengthVarLabel.configure(text = str(round(float(furnace_length)*0.0328084,1))+ ' ft')
                
            else:
                
                self.FurnaceLengthVarLabel = customtkinter.CTkLabel(self.StartPositionFrame, text = "N/A", fg_color = "transparent", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", width = 140, height = 31 )
            
            self.FurnaceLengthVarLabel.place(x = 275, y = 75)
            


    def SaveManualParameters(self):
        global tubes_across, furnace_length, manual_parameters_saved
        
        manual_parameters_saved = True
        current_unit = self.UnitsComboBox.get()

        tubes_across = self.TubesAcrossTextBox.get("1.0", 'end-1c')
        
        
        if current_unit == 'Metric':
            furnace_length = self.FurnaceLengthTextBox.get("1.0", 'end-1c')
            self.FurnaceLengthVarLabel.configure(text = str(furnace_length) + ' cm')
            
        elif current_unit == 'Imperial':
            furnace_length = float(self.FurnaceLengthTextBox.get("1.0", 'end-1c'))*2.54
            self.FurnaceLengthVarLabel.configure(text = str(round(float(furnace_length)*0.0328084,1))+ ' ft')

        print(tubes_across)
        print(furnace_length)


    def SaveRobotParameters(self):
        global wheel_size, lance_length 

        wheel_size = self.wheel_sizeComboBox.get()
        lance_length = self.LanceLengthComboBox.get()
        
        
        print(wheel_size)
        print(lance_length)
        
    
    def LoadFile(self):
        global banks, number_of_banks, file_loaded

        tkinter.Tk().withdraw()

        FileName = askopenfilename(initialdir="/media/pi/", filetypes=[("Excel files", "*.xlsx")])

        if not FileName:
            return

        if FileName.endswith('.xlsx'):
            # Show the loading frame
            self.LoadingFrame = customtkinter.CTkFrame(self.FlushingTab, width=500, height=300)
            self.LoadingFrame.place(relx=0.5, rely=0.5, anchor="center")

            self.LoadingLabel = customtkinter.CTkLabel(self.LoadingFrame, text="Loading file...", font=("Bahnschrift", 36))
            self.LoadingLabel.pack(padx =100, pady=80)

            self.update_idletasks()  # Force GUI update

            # Delay the file loading to allow the frame to appear
            self.after(100, lambda: self.ProccessFile(FileName))  # Call helper after 100ms

        else:
            tkinter.messagebox.showwarning('Error', 'Select a valid .xlsx file')


    def ProccessFile(self, FileName):
        global banks, number_of_banks, file_loaded

        try:
            banks = excel.read_excel_sheet(FileName)
            number_of_banks = len(banks)
            banks_list = [str(i+1) for i in range(number_of_banks)]

            
            self.BanksComboBox.configure(values=banks_list)
            self.BanksComboBox.set("1")

            print("User chose:", FileName)
            file_loaded = True

        except Exception as e:
            tkinter.messagebox.showerror("Error", f"Failed to load file:\n{e}")
        finally:
            self.LoadingFrame.destroy()
    

    
    def PauseToggle(self):
        # Pause and resume robot while on automatic mode
        if  self.PauseButton.cget("fg_color") == "blue":
            self.PauseButton.configure(fg_color = "green", text_color = "yellow", hover_color = "green", text = "RESUME")
            Pause()
        
        elif self.PauseButton.cget("fg_color") == "green":
            self.PauseButton.configure(fg_color = "blue", text_color = "yellow", hover_color = "blue", text = "PAUSE")
            Resume()
            
    
    def LightsToggle(self):
        # Request the rover to toggle the lights
        if  self.LightsButton.cget("fg_color") == "transparent":
            self.LightsButton.configure(fg_color = "orange")
            command = 'CTRL~L-TOGGLE'
            s.send(command.encode())
            print(command)
            
        
        else:
            self.LightsButton.configure(fg_color = "transparent")
            command = 'CTRL~L-TOGGLE'
            s.send(command.encode())
            print(command)
            
            
    def ShowNumpad(self, textbox):
        self.numpad.attach_to(textbox)
    
    
    def CheckNumpadFocus(self, event):
        widget = event.widget
        if isinstance(widget, customtkinter.CTkTextbox):
            return  # Let the textbox open the numpad
        if self.numpad and not str(widget).startswith(str(self.numpad)):
            self.numpad._iconify()  # Hide the numpad


            
        







# ------------------ Event functions ------------------------------------------------------------------------------------------

def ControllerSelection():
    
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    controller_connected = False
    
    for device in devices:
        if "Logitech" in device.name:
            controller = evdev.InputDevice(device.path)
            controller_connected = True
            
            
    if controller_connected:
        print("XBOX CONTROLLER CONNECTED\n")
        sleep(1)
            
    else:
        print("XBOX CONTROLLER NOT DETECTED\n")
        sleep(1)
        
        
def ControllerButtonRead():
    
    global climb_button_state, controller_active
    
    
    last_event = 0
    
    if controller:
        while True:
        
            for event in controller.read_loop():
                
                
                
                if event.type == evdev.ecodes.EV_KEY:
                    event_msg = str(event).split(",")
                    
                elif event.type == evdev.ecodes.EV_ABS:
                    event_msg = str(event).split(",")
                        
    #                 print(event_msg[1][6:9],event_msg[3][5:12])

                controller_active = app.ControllerVar.get()

                if controller_active == "on" and last_event != event_msg[0]:
                    
                    if int(event_msg[1][6:9]) == 16:
                        
                        climb_button_state = int(event_msg[3][5:9])
                        
                        Climbcontroller_thread = threading.Thread(target = ControllerClimbControl)
                        Climbcontroller_thread.start()
                        
                            
                    if int(event_msg[1][6:9]) == 308:
                        
                        if int(event_msg[3][5:12]) == 1:
                            print("Lights")
                            app.LightsToggle()
                        
                                
                    elif int(event_msg[1][6:9]) == 1:
                        if int(event_msg[3][5:12]) >= 32700:
                            # Request the rover to move backwards at the speed currently set.
    #                         print("Reverse")
                            Reverse()
                            sleep(0.5)
                            
                        elif int(event_msg[3][5:12]) < -32700:
                            # Request the rover to move forwards at the speed currently set.
    #                         print("Forward")
                            Forward()
                            sleep(0.5)
                            
                        
                        elif int(event_msg[3][5:12]) == -129:
                            # Stop the rover immediately
    #                         print("Stop")
                            Stop()
                            sleep(0.5)

                            
                    elif int(event_msg[1][6:9]) == 305:
                        if int(event_msg[3][5:12]) == 1:
                            stop_button_state = int(event_msg[3][5:12])
    #                         print("Stop")
                            Stop()
                            
                last_event = event_msg[0]
        
            
                    
        
def ControllerClimbControl():
    

    if climb_button_state == 1:
            
        start_time = dt.datetime.utcnow()
        current_time = dt.datetime.utcnow()
        
        
        while (current_time - start_time).total_seconds() < 2:
            
            if climb_button_state != 1:
                
                break
            
            else:
                
                current_time = dt.datetime.utcnow()
                
                
        if climb_button_state == 1:
#             print("Climb right")
            RightClimb()
            
    if climb_button_state == -1:

        start_time = dt.datetime.utcnow()
        current_time = dt.datetime.utcnow()
        
        while (current_time - start_time).total_seconds() < 2:
            
            if climb_button_state != -1:
                
                break
            
            else:
                
                current_time = dt.datetime.utcnow()
                
                
        if climb_button_state == -1:
#             print("Climb left")
            LeftClimb()



def CameraServer(port, client_id):
    global images
    global frame_queues
    
    while True:
        try:
            
            # Start a socket listening for connections on 0.0.0.0:8000 (0.0.0.0 means
            # all interfaces)
            camera_server_socket = socket.socket()
            camera_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # solution for '[Error 89] Address already in use'. Use before bind()
            camera_server_socket.bind(('0.0.0.0', port))
            camera_server_socket.listen(NUM_CAMS)
            
            # Wait max 5 seconds for a client to connect
            camera_server_socket.settimeout(5) 
            
            try:
                conn, addr = camera_server_socket.accept()
                
            
            except socket.timeout:
#                 print(f"Camera {client_id} not found, retrying...")
                camera_server_socket.close()
                continue
            
            print(f"Connection from: {addr} on port: {port}")
            
            # Make a file-like object out of the connection
            connection = conn.makefile('rb')

            try:
                while True:
                    # Read the length of the incoming image
                    image_len_data = connection.read(struct.calcsize('<L'))
                    if not image_len_data:
                        break  # No data, exit loop

                    image_len = struct.unpack('<L', image_len_data)[0]
                    if image_len == 0:
                        break  # Stop if sender signals the end
                    
                    # Construct a stream to hold the image data and read the image
                    # data from the connection
                    image_stream = io.BytesIO()
                    image_stream.write(connection.read(image_len))
                    image_stream.seek(0)
                    
                    # Convert to PIL image
                    img = Image.open(image_stream).copy()
                    
                    # Put the frame in the queue (overwrite old frames if full)
                    if not frame_queues[client_id].full():
                        frame_queues[client_id].put(img)
                        
            except Exception as e:
                print(f"Camera {client_id} error {e}")


            finally:
                print(f"Camera {client_id} disconnected")
                
                frame_queues[client_id].put(empty_image.copy())  # Show black image when disconnected
                connection.close()
                camera_server_socket.close()
                
        except Exception as e:
            print(f"Error in Camera {client_id}")
            
        sleep(3)
    
    
        
# Updates the Tkinter UI with new frames from each camera.
def UpdateFrames():
    global photos
    
    for i in range(NUM_CAMS):
        if not frame_queues[i].empty():
            img = frame_queues[i].get()
            new_photo = ImageTk.PhotoImage(img)
            canvases[i].itemconfig(photo_ids[i], image=new_photo)
            canvases[i].image = new_photo  # Store a reference to prevent garbage collection
            photos[i] = new_photo
            
        else:
            img = empty_image
    
    app.after(5, UpdateFrames)  # Repeat after 10ms



def Screenshot():
    filename = datetime.datetime.now().strftime('%Y.%m.%d-%H.%M.%S.jpg')
    image.save(filename)
    print('Saved:', filename)



def Automatic():
    global AutomaticRunSpeed, ClimbDirection
    
    start_position_mode = app.SetStartPositionComboBox.get()
    CLimbDirection = app.ClimbDirectionComboBox.get()
    AutomaticRunSpeed = app.AutomaticRunSpeedComboBox.get()
    TubeSize = app.TubeSizeComboBox.get()
    RunsPerTube = app.RunsPerTubeComboBox.get()
    
    
    
    if start_position_mode == "Set Start & Finish":
        
        if int(tubes_across) < 3 or tubes_across == None:
            
            tkinter.messagebox.showwarning('Error', 'Furnace has to be at least 3 tubes across')
            
        else:
            
            invalid = False

            
            base_command =  'CTRL~AS~'
            
            
            if AutomaticRunSpeed == 'Fast':
            
                speed_command = 'F'
            
            elif AutomaticRunSpeed == 'Medium':
                
                speed_command = 'M'
                    
            elif AutomaticRunSpeed == 'Slow':
                
                speed_command = 'S'
                
                    
            if CLimbDirection == 'Left':

                direction_command = 'L'
                
            elif CLimbDirection == 'Right':

                direction_command = 'R'
                
            if start_position != 0 and finish_position != 0:
                
                length_command = str(start_position) + ',' + str(finish_position)
                
            else:
                
                tkinter.messagebox.showwarning('Error', 'Please save a Start and Finish Position')

            
            if TubeSize == 'Small':

                tubesize_command = 'S'

            elif TubeSize == 'Medium':

                tubesize_command = 'M'

            elif TubeSize == 'Big':

                tubesize_command = 'B'
                
                
            runs_per_tube_command = RunsPerTube
            
            command = base_command + speed_command + '~' + direction_command + '~' + length_command + '~' + str(tubes_across) + '~' + tubesize_command + '~' + str(runs_per_tube_command)
            print(command)
            s.send(command.encode())
                
    
    elif start_position_mode == "Manual Distance":
        
        
        if furnace_length == 0 or int(tubes_across) < 3:
            
            tkinter.messagebox.showwarning('Error', 'Load a file or enter valid parameters manually')
            
        else:
        
            
            invalid = False

            
            base_command =  'CTRL~AS~'
            
            
            if AutomaticRunSpeed == 'Fast':
            
                speed_command = 'F'
            
            elif AutomaticRunSpeed == 'Medium':
                
                speed_command = 'M'
                    
            elif AutomaticRunSpeed == 'Slow':
                
                speed_command = 'S'
                
                    
            if CLimbDirection == 'Left':

                direction_command = 'L'
                
            elif CLimbDirection == 'Right':

                direction_command = 'R'

            
            if TubeSize == 'Small':

                tubesize_command = 'S'

            elif TubeSize == 'Medium':

                tubesize_command = 'M'

            elif TubeSize == 'Big':

                tubesize_command = 'B'
            
            
            command = base_command + speed_command + '~' + direction_command + '~' + str(furnace_length) + '~' + str(tubes_across) + '~' + tubesize_command + '~' + str(runs_per_tube_command)
            print(command)
            s.send(command.encode())
                
        
        

def SaveStartPosition():
    global start_position
    
    # Save start position for automatic run.
    command = 'CTRL~SAVEMOTORPOS'
    s.send(command.encode())
    Robot_reply = s.recv(32)
    Robot_msg = Robot_reply.decode('ascii')
    
    app.SaveStartPositionButton.place_forget()
    
    app.StartPositionSavedLabel = customtkinter.CTkLabel(app.StartPositionFrame, text = "Saved", fg_color = "orange", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", corner_radius=8, width = 90, height = 31 )
    app.StartPositionSavedLabel.place(x = 55, y = 105)
    
    print(Robot_msg)
    
    start_position = int(Robot_msg)
    
    print(command)
    
def SaveFinishPosition():
    global finish_position
    
    # Save start position for automatic run.
    command = 'CTRL~SAVEMOTORPOS'
    s.send(command.encode())
    Robot_reply = s.recv(32)
    Robot_msg = Robot_reply.decode('ascii')
    
    app.SaveFinishPositionButton.place_forget()
    
    app.FinishPositionSavedLabel = customtkinter.CTkLabel(app.StartPositionFrame, text = "Saved", fg_color = "orange", anchor='w', font = ("Bahnschrift", 26), cursor = "arrow", state = "normal", corner_radius=8, width = 90, height = 31 )
    app.FinishPositionSavedLabel.place(x = 255, y = 105)
    
    
    print(Robot_msg)
    
    finish_position = int(Robot_msg)
    
    print(command)

def Forward():
    # Request the rover to move forwards at the speed currently set.
    command = 'CTRL~FORWARD'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)

def Reverse():
    # Request the rover to move backwards at the speed currently set.
    command = 'CTRL~REVERSE'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)

def Faster():
    # Increment the speed parameter.
    command = 'CTRL~FASTER'
    s.send(command.encode())
    motor_speed_set = s.recv(32)
    CalculateVehicleSpeed(motor_speed_set)
    print(command)
    
def Slower():
    # Decrement the speed parameter.
    command = 'CTRL~SLOWER'
    s.send(command.encode())
    motor_speed_set = s.recv(32)
    CalculateVehicleSpeed(motor_speed_set)
    print(command)
    
def CalculateVehicleSpeed(ack_motor_speed_reply):
    # Obtain robot speed.
    motor_units = ack_motor_speed_reply[10:]
    pctg_speed = int(motor_units) / 50
    app.SpeedVarLabel.configure(text = str(int(pctg_speed)) + ' %')
    app.SpeedVarLabel2.configure(text = str(int(pctg_speed)) + ' %')
    
def OscillateLance():
    
   
    if app.OscillationVar.get():
        
        if head_initialised and head_homed:
            
            StartOscillationAngle = app.StartOscillationComboBox.get()
            FinishOscillationAngle = app.FinishOscillationComboBox.get()
            
            command = 'ADMN~OSCILLATE' + '~' + str(																																																																																																																																																								StartOscillationAngle) + ',' + str(FinishOscillationAngle)
            s.send(command.encode())
            print(command)
            
            
                
        else:
        
            app.OscillationVar.set(False)
            tkinter.messagebox.showwarning('Error', 'Please initialise and home the head first.')
            print(app.OscillationVar.get())
        
    else:
        
        command = 'ADMN~OSCILLATE' + '~' + 'STOP'
        s.send(command.encode()) 
        print(command)
         
                

def GetSensorStatus():
    # Return Head, Motors and IMU values.
    GetHeadSensorValues()
    GetIMUValues()
    GetMotorsStatus()
    
    
def GetMotorsStatus():
    
    # Get status from all Motors.
    command = 'CTRL~MOTORS_STATUS'
    s.send(command.encode())
    s.settimeout(5)
    Robot_reply = s.recv(64)
    Robot_msg = Robot_reply.decode('ascii')
    
    print(Robot_reply)
    
    faulty_motors = Robot_msg
    faulty_motors_list = ast.literal_eval(faulty_motors)
                         
    if not faulty_motors_list:
        app.MotorsStatusValuesLabel.configure(text = 'All motors are enabled and working')
        
    else:
        app.MotorsStatusValuesLabel.configure(text = 'Faulty motors: \n' + str(faulty_motors_list))
    
    
    
    print(command)
    
    
    
    
    
def GetHeadSensorValues():


    # Get distance from robot head sensors.
    command = 'CTRL~HEAD_SENSORS'
    s.send(command.encode())
    Robot_reply = s.recv(32)
    Robot_msg = Robot_reply.decode('ascii')
    
    print(Robot_reply)
    
    Robot_msg = Robot_msg.split(",")
    

    slide_sensor_homed = Robot_msg[0]
    roll_sensor_homed = Robot_msg[1]
    pitch_sensor_homed = Robot_msg[2]
    
    if slide_sensor_homed == False:
        app.SlideSensorLabel.configure(text = 'Slide: ' + 'Yes')
        
    else:
        app.SlideSensorLabel.configure(text = 'Slide: ' + 'No')
        
    
    if roll_sensor_homed == True:
        app.RollSensorLabel.configure(text = 'Roll: ' + 'Yes')
        
    else:
        app. RollSensorLabel.configure(text = 'Roll: ' + 'No')
        
        
    if pitch_sensor_homed == True:
        app.PitchSensorLabel.configure(text = 'Pitch: ' + 'Yes')
        
    else:
        app.PitchSensorLabel.configure(text = 'Pitch: ' + 'No')
        
    
    
    
   
    print(command)



def GetIMUValues():
    global RobotRoll, RobotPitch, RobotYaw

    # Get values from robot IMU.
    command = 'CTRL~IMU'
    s.send(command.encode())
    Robot_reply = s.recv(32)
    Robot_msg = Robot_reply.decode('ascii')
    
    print(Robot_reply)
    
    Robot_msg = Robot_msg.split(",")

    RobotRoll = int(Robot_msg[0])
    RobotPitch = int(Robot_msg[1])
    RobotYaw = int(Robot_msg[2])
    
    app.IMURollStatusLabel.configure(text = 'Roll: ' + str(int(RobotRoll)))
    app.IMUPitchStatusLabel.configure(text = 'Pitch: ' + str(int(RobotPitch)))
    app.IMUYawStatusLabel.configure(text = 'Yaw: ' + str(int(RobotYaw)))
    

    print(command)
    

def LeftClimb():
    # Request the rover to move left (viewed from the rear) by invoking its pipe climbing function.
    TubeSize = app.TubeSizeComboBox.get()

    if TubeSize == "Small":
        command = 'CTRL~L-CLIMB,S'
    elif TubeSize == "Medium":
        command = 'CTRL~L-CLIMB,M'
    elif TubeSize == "Big":
        command = 'CTRL~L-CLIMB,B'

    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    
def RightClimb():
    # Request the rover to move right (viewed from the rear) by invoking its pipe climbing function.
    TubeSize = app.TubeSizeComboBox.get()

    if TubeSize == "Small":
        command = 'CTRL~R-CLIMB,S'
    elif TubeSize == "Medium":
        command = 'CTRL~R-CLIMB,M'
    elif TubeSize == "Big":
        command = 'CTRL~R-CLIMB,B'

    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    
def Axle1Up():
    # Raise the front set of wheels to clear a baffle plate.
    command = 'CTRL~RAISE1'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    sleep(1)
    
def Axle1Down():
    # Lower the front set of wheels to clear a baffle plate.
    command = 'CTRL~LOWER1'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    sleep(1)
    
def Axle2Up():
    # Raise the 2nd set of wheels to clear a baffle plate.
    command = 'CTRL~RAISE2'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    sleep(1)
    
def Axle2Down():
    # Lower the 2nd set of wheels to clear a baffle plate.
    command = 'CTRL~LOWER2'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    sleep(1)
    
def Axle3Up():
    # Raise the 3rd set of wheels to clear a baffle plate.
    command = 'CTRL~RAISE3'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    sleep(1)
    
def Axle3Down():
    # Lower the 3rd set of wheels to clear a baffle plate.
    command = 'CTRL~LOWER3'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    sleep(1)
    
def Axle4Up():
    # Raise the back set of wheels to clear a baffle plate.
    command = 'CTRL~RAISE4'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    sleep(1)
    
def Axle4Down():
    # Lower the back set of wheels to clear a baffle plate.
    command = 'CTRL~LOWER4'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    sleep(1)
    
def TiltRight():
    # Show stream of what front camera can see.
    command = 'CTRL~TILTR'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    
def TiltLeft():
    # Show stream of what front camera can see.
    command = 'CTRL~TILTL'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    
def Level():
    # Show stream of what front camera can see.
    command = 'CTRL~LEVEL'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)

def HomeHead():
    global head_homed
    
    if head_initialised:
        # Home the head motors
        command = 'CTRL~HOME_HEAD'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
        
        head_homed = True
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    

def ManualHomeHead():
    global head_homed
    
    if head_initialised:
        # Home the head motors
        command = 'CTRL~MANUAL_HOME'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
        
        head_homed = True
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
        
def SlideHome():
    global head_homed
    
    if head_initialised:
        # Home the head motors
        command = 'CTRL~SLIDE_HOME'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
        
        head_homed = True
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
        
        
def RollHome():
    global head_homed
    
    if head_initialised:
        # Home the head motors
        command = 'CTRL~ROLL_HOME'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
        
        head_homed = True
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
        
        
def PitchHome():
    global head_homed
    
    if head_initialised:
        # Home the head motors
        command = 'CTRL~PITCH_HOME'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
        
        head_homed = True
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    

def InitHeadMotors():
    global head_initialised
    
    # Home the head motors
    command = 'CTRL~HEAD_INIT'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    
    head_initialised = True
    
def LanceAngleA():
    # Home the head motors

    if file_loaded == True:
        
        if app.wheel_sizeComboBoxVar.get() == 'Small':
            wheel_diameter = 101.6
        elif app.wheel_sizeComboBoxVar.get() == 'Big':
            wheel_diameter = 152.4
            
        excel.save_wheel_diameter(wheel_diameter)
        
        LancingPositions = excel.get_head_positions(banks[CurrentBank])
        print(LancingPositions[0])
        
        if head_initialised and head_homed:
            
            app.AnglesValuesLabel = customtkinter.CTkLabel(app.LancingTab, text = "Slide: " + str(LancingPositions[0][0]) + "\n Roll: " + str(LancingPositions[0][1]/10), fg_color = "transparent", anchor='w', font = ("Bahnschrift", 20), cursor = "arrow", state = "normal", width = 60, height = 31, corner_radius=8 )
            app.AnglesValuesLabel.place(x = 100, y = 330)
            
            command = 'CTRL~LANCE_ANGLE_A,' + str(LancingPositions[0][0]) + ',' + str(LancingPositions[0][1])
            s.send(command.encode())
            #reply = s.recv(32)
            print(command)
        
        else:

            tkinter.messagebox.showwarning('Error', 'Initialise head and home it before moving to a Lance Angle')

    else:

        tkinter.messagebox.showwarning('Error', 'Load a file first.')
    
def LanceAngleB():
    # Home the head motors
    if file_loaded == True:
        
        if app.wheel_sizeComboBoxVar.get() == 'Small':
            wheel_diameter = 101.6
        elif app.wheel_sizeComboBoxVar.get() == 'Big':
            wheel_diameter = 152.4
            
        excel.save_wheel_diameter(wheel_diameter)
        
        LancingPositions = excel.get_head_positions(banks[CurrentBank])
        print(LancingPositions[1])
        
        if head_initialised and head_homed:

            app.AnglesValuesLabel = customtkinter.CTkLabel(app.LancingTab, text = "Slide: " + str(LancingPositions[0][0]) + "\n Roll: " + str(LancingPositions[0][1]/10), fg_color = "transparent", anchor='w', font = ("Bahnschrift", 20), cursor = "arrow", state = "normal", width = 60, height = 31, corner_radius=8 )
            app.AnglesValuesLabel.place(x = 100, y = 330)
            
            command = 'CTRL~LANCE_ANGLE_B,' + str(LancingPositions[1][0]) + ',' + str(LancingPositions[1][1])
            s.send(command.encode())
            #reply = s.recv(32)
            print(command)
        
        else:

            tkinter.messagebox.showwarning('Error', 'Initialise head and home it before moving to a Lance Angle')


    else:

        tkinter.messagebox.showwarning('Error', 'Load a file first.')

def SlideToAngle():
    
    if head_initialised:
        # Move Slide to specific position.
        Angle = app.SlideTextBox.get("1.0", 'end-1c')
        if int(Angle) <= 94:
            command = 'CTRL~SLIDEANGLE,' + str(Angle)
            s.send(command.encode())
            #reply = s.recv(32)
            print(command)
            
        else:
    
            tkinter.messagebox.showwarning('Error', 'Enter valid distance (0-94mm).')
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    
        
    

def SlideLeft():
    
    if head_initialised:
        
        # Move Slide to the left.
        command = 'CTRL~SLIDEL'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    
    
def SlideRight():
    
    if head_initialised:
        
        # Move Slide to the right.
        command = 'CTRL~SLIDER'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
        
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    
    
def RollToAngle():
     
    if head_initialised:
        # Show stream of what front camera can see.
        Angle = app.RollTextBox.get("1.0", 'end-1c')
        Angle = int(Angle)
        
        if Angle < 180 or Angle > -180:
            command = 'CTRL~ROLLANGLE,' + str(Angle)
            s.send(command.encode())
            #reply = s.recv(32)
            print(command)
            
        else:

            tkinter.messagebox.showwarning('Error', 'Enter an angle between 180 and -180 degrees.')
   
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    
    
def RollClock():
    
    if head_initialised:
        
        # Show stream of what front camera can see.
        command = 'CTRL~ROLLCLOCK'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
        
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    
    
def RollAnticlock():
    
    if head_initialised:
        
        # Show stream of what front camera can see.
        command = 'CTRL~ROLLANTICLOCK'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    

def PitchToAngle():
    
    if head_initialised:
        
        # Show stream of what front camera can see.
        Angle = app.PitchTextBox.get("1.0", 'end-1c')
        command = 'CTRL~PITCHANGLE,' + str(Angle)
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    

def PitchUp():
    
    if head_initialised:
    
        # Show stream of what front camera can see.
        command = 'CTRL~PITCHUP'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
    
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    
    
def PitchDown():
    
    if head_initialised:
        
        # Show stream of what front camera can see.
        command = 'CTRL~PITCHDOWN'
        s.send(command.encode())
        #reply = s.recv(32)
        print(command)
        
    else:

        tkinter.messagebox.showwarning('Error', 'Initialise head first.')
    

def Stop():
    # Stop the rover immediately
    command = 'ADMN~STOP'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)

def Pause():
    # Stop the rover immediately
    command = 'ADMN~PAUSE'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)

def Resume():
    # Stop the rover immediately
    command = 'ADMN~RESUME'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)


def Initialise():
    # Re-Initialise the robot (after crossing tubes)
    command = 'CTRL~FULL_INIT'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)

def LevelRobot():
    # Level the robot 
    command = 'CTRL~Level'
    s.send(command.encode())
    #reply = s.recv(32)
    print(command)
    
                
                
                
def AttemptConnection():
    global s, connected
    
    start_time = time()
    print("ATTEMPTING CONNECTION WITH ROVER...\n")
    
    sleep(1)
    
    while True:
        try:
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((HOST, PORT))
            
            connected = True
            print("\nSUCCESSFUL CONNECTION WITH THE ROBOT\n")
            
            MonitorConnection()
            
            break # Exit the loop if connection succceds
            
        except socket.error as msg:
            
            elapsed_time = time() - start_time
            print(".", end= ' ')
            sleep(1)
            
            if elapsed_time >= 20:
                
                connected = False
                print("\n\nFAILED TO CONNECT WITH THE ROBOT AFTER 20s.")
                print("CHECK THAT THE ROBOT IS POWERED,AND HAS FLASHED ITS LIGHTS")
                exit()



def MonitorConnection():

    def check():
        global connected
        
        while connected:
            try:
                
                s.settimeout(2)
                s.sendall(b'ping')
                
            except:
                connected = False
                tkinter.messagebox.showwarning("Disconnected", "Lost connection to the robot.")
                break
            sleep(5)

    threading.Thread(target=check, daemon=True).start()




if __name__ == '__main__':
    
    Connection_thread = threading.Thread(target = AttemptConnection)
    Connection_thread.start()
    
    
    app = MainFrame() # Define GUI object
    app.attributes("-fullscreen", True) # Set full-screen mode	
    
    ControllerSelection() # Find if controller is connected to the GUI Pi
    
    controller_thread = threading.Thread(target = ControllerButtonRead)
    controller_thread.start()
    
    
    canvases = []
    photo_ids = []
    
    for i in range(NUM_CAMS):
        
        photo =  ImageTk.PhotoImage(empty_image)
        
        # Get the correct frame name dynamically
        frame_name = f"app.Camera{i+1}Frame"
        
        try:
            frame = eval(frame_name) # Ensure frame exists
            
        except NamError:
            print("Frame not found")
            continue
       
        canvas = customtkinter.CTkCanvas(frame, width=photo.width(), height=photo.height())
        canvas.pack()

        # set object and get ID to update it later
        photo_id = canvas.create_image((0,0),image=photo, anchor='nw')
        
        canvases.append(canvas)
        photo_ids.append(photo_id)
        
    
    
    camera1thread = threading.Thread(target=CameraServer, args=(22003, 1), daemon=True)
    camera2thread = threading.Thread(target=CameraServer, args=(22004, 0), daemon=True)
    
    camera1thread.start()
    camera2thread.start()
        
    # Start updating the Tkinter GUI    
    UpdateFrames()
    
    #Run Tkinter main loop
    app.mainloop()
    
    

    print('Stop GUI')


    print('Stop Server')
    camera1_server_socket.close()

        

