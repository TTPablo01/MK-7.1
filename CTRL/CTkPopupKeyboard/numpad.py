'''
On-screen Popup Numpad for customtkinter
Author: Akash Bora
'''

from tkinter import *
from customtkinter import *
import sys

class PopupNumpad(CTkToplevel):
    
    def __init__(self, attach=None, x=None, y=None, keycolor=None,
                 fg_color=None, keyheight: int = 100, keywidth: int = 100,
                 alpha: float = 0.85, corner=20, point=True, **kwargs):
        
        super().__init__(takefocus=1)
        self.lift()
        self.attributes("-topmost", True)
        self.corner = corner
        self.disable = True
        
        
        self.attach = attach
        
        if self.attach is not None:
            self.attach.bind('<Key>', lambda e: self.withdraw() if not self.disable else None, add="+")
            self.attach.bind('<Button-1>', lambda e: self._iconify(), add="+")

    
        
        if sys.platform.startswith("win"):
            self.overrideredirect(True)
            self.transparent_color = self._apply_appearance_mode(self._fg_color)
            self.attributes("-transparentcolor", self.transparent_color)
        elif sys.platform.startswith("darwin"):
            self.overrideredirect(True)
            self.bind('<Configure>', lambda e: self.withdraw() if not self.disable else None, add="+")
            self.transparent_color = 'systemTransparent'
            self.attributes("-transparent", True)
        else:
            self.attributes("-type", "splash")
            self.transparent_color = 'white'
            self.corner = 0
            self.withdraw()
            
        
        self.disable = False  
        self.fg_color = ThemeManager.theme["CTkFrame"]["fg_color"] if fg_color is None else fg_color
        self.frame = CTkFrame(self, fg_color=self.fg_color, corner_radius=self.corner, border_width=2)
        self.frame.pack(expand=True, fill="both")
        self.withdraw()
        self.attach = attach
        self.keycolor = ThemeManager.theme["CTkFrame"]["fg_color"] if keycolor is None else keycolor
        self.keywidth = keywidth
        self.keyheight = keyheight
        self.point = point
        
        self.resizable(width=False, height=False)
        self.transient(self.master)

        self.frame_color = ThemeManager.theme["CTkFrame"]["fg_color"]
        self.row1 = CTkFrame(self.frame, fg_color=self.frame_color)
        self.row2 = CTkFrame(self.frame, fg_color=self.frame_color)
        self.row3 = CTkFrame(self.frame, fg_color=self.frame_color)
        self.row4 = CTkFrame(self.frame, fg_color=self.frame_color)
        
        self.row1.grid(row=1, column=0, pady=(10,0))
        self.row2.grid(row=2, column=0, padx=10)
        self.row3.grid(row=3, column=0, padx=10)
        self.row4.grid(row=4, column=0, pady=(0,10))
    
        self._init_keys(**kwargs)
        

        
        self.update_idletasks()
        self.x = x
        self.y = y
#         self._iconify()
        self.attributes('-alpha', alpha)
        
    def _init_keys(self, **kwargs):
        self.keys = {
            'row1' : ['7','8','9'],
            'row2' : ['4','5','6'],
            'row3' : ['1','2','3'],
            'row4' : ['-','0','◀']
            }
        
        for row in self.keys.keys(): 
            if row == 'row1':            
                i = 1                     
                for k in self.keys[row]:
                    CTkButton(self.row1,
                              text=k,
                              width=self.keywidth,
                              height=self.keyheight,
                              border_width = 3,
                              font = ("Bahnschrift", 26),
                              fg_color=self.keycolor,
                              text_color="black",
                              command=lambda k=k: self._attach_key_press(k), **kwargs).grid(row=0,column=i)
                    i += 1
            elif row == 'row2':
                i = 2
                for k in self.keys[row]:
                    CTkButton(self.row2,
                              text=k,
                              width=self.keywidth,
                              height=self.keyheight,
                              border_width = 3,
                              font = ("Bahnschrift", 26),
                              fg_color=self.keycolor,
                              text_color="black",
                              command=lambda k=k: self._attach_key_press(k), **kwargs).grid(row=0,column=i)
                    i += 1
                i = 2
            elif row == 'row3':
                i = 2
                for k in self.keys[row]:
                    CTkButton(self.row3,
                              text=k,
                              width=self.keywidth,
                              height=self.keyheight,
                              border_width = 3,
                              font = ("Bahnschrift", 26),
                              fg_color=self.keycolor,
                              text_color="black",
                              command=lambda k=k: self._attach_key_press(k), **kwargs).grid(row=0,column=i)
                    i += 1

            elif row == 'row4':
                i = 2
                for k in self.keys[row]:
                    CTkButton(self.row4,
                              text=k,
                              width=self.keywidth,
                              height=self.keyheight,
                              border_width = 3,
                              font = ("Bahnschrift", 26),
                              fg_color=self.keycolor,
                              text_color="black",
                              command=lambda k=k: self._attach_key_press(k), **kwargs).grid(row=0,column=i)
                    i += 1
            
            self.up = False
            self.hide = False
            
    def destroy_popup(self):
        self.destroy()
        self.disable = True
        
        
    def _iconify(self, widget=None):
        if self.disable:
            return
        
        if self.hide:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.focus_force()
            self.hide = False
            
            if self.attach:

                screen_w = self.winfo_screenwidth()
                screen_h = self.winfo_screenheight()
                
                w = 320
                h = 420
                
                x = int((screen_w / 2) - (w/2))
                y = int((screen_h / 2) - (h/2)) + 40

                
                self.geometry(f"{w}x{h}+{x}+{y}")
                
                if self.master:
                    try:
                        self.master.attributes("-fullscreen", True)
                    except Exception as e:
                        print("Error restoring fullscreen")
        else:
            self.withdraw()
            self.hide = True
            self.attach = None
        
        
    def attach_to(self, textbox):
        self.attach = textbox
        self._iconify()
        
        
    def _attach_key_press(self, k):
        
        widget = self.attach
        
        if not widget:
            return
        
        
        if k == '◀':
            try:
                if isinstance(widget, Text) or isinstance(widget, CTkTextbox):
                    text = widget.get("1.0", END)
                    widget.delete("1.0", END)
                    widget.insert("1.0", text[:-2])
                    
                else:
                    text = widget.get()
                    widget.delete(0, END)
                    widget.insert(0, text[:-1])
            
            except Exception as e:
                print("Delete error: ", e)
            return
        
        if k == "." and self.point:
            widget.insert(INSERT, k)
            
        else:
            widget.insert(INSERT, k)

