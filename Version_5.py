# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 18:46:27 2022

@author: Rahill
"""

# import tkinter
try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    import Tkinter as tk
    from Tkinter import filedialog
import numpy as np
# must be installed using pip
# python3 -m pip install opencv-python
import csv
import time
# local clayton libs
# import frame_capture
# import frame_draw
from PIL import Image, ImageTk

import pandas as pd
import serial as sr
# operations handling and reporting
import sys
import warnings
import subprocess
from tkinter import ttk


from matplotlib.figure import Figure

import re
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)


# use to load images and search serial ports

import serial.tools.list_ports

from itertools import count, cycle


from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
# MAY NEED TO INSTALL
txtName = "Cords_temp"
######Preparing variables######
# When these are edited by param window, the prog will edit these values

global xcord, ycord
global serial_ink_stat, serial_kin_stat, emerg_stop

save_stat = False
emerg_stop = False
g_code_x_val = 0
g_code_y_val = 0
g_code_z_val = 0
g_code_feed_val = 0
xcord = 0
ycord = 0
t_um = 2000
syr_id_mm = 4.7


def start():  # Stores Data Initial Columns
    with open(txtName + '.csv', 'w') as data:  # + time.strftime('-%H-%M-%S', time.localtime()) +
        output = csv.writer(data)
        row = ['time', 'xcord', 'ycord']
        output.writerow(row)


start()

# this will scan all ports avalible and find the arduino automatically
serial_ink_stat = False
serial_kin_stat = False
global port_kin_found, port_ink_found
port_kin_found = ""
port_ink_found = ""
ports = serial.tools.list_ports.comports()
# PIDLIST=[]
# try:
for port, desc, hwid in sorted(ports):

    a_string = hwid
    print(port)
    print(desc)
    print(hwid)

    # PIDLIST.append(re.search('VID:', hwid).group(1))

    match_kin = ["PID=1A86:7523"]

    if any(x in a_string for x in match_kin):
        port_kin_found = port
        print(port_kin_found)
        print("kin port found and matched")

    print("{}: {} [{}]".format(port, desc, hwid))
#     pass
#     # with open('Distances_temp.csv', newline='') as f:
#     #     reader = csv.reader(f)
#     #     data = list(reader)

#     # for i in len(data):

#     #     print(data[i])

#     # # print(data)

# except:
#     pass


arduino_ports = [
    p.device
    for p in serial.tools.list_ports.comports()
    if '' in p.description  # may need tweaking to match new arduinos names here
]
if not arduino_ports:
    global no_ports
    # raise IOError("No Arduino found")
    print("No COM Modules Found!!")

    no_ports = True

else:
    no_ports = False
if len(arduino_ports) > 1:
    warnings.warn('Multiple COMS found - using the first')


class ImageLabel(tk.Label):
    """
    A Label that displays images, and plays them if they are gifs
    :im: A PIL Image instance or a string filename
    """

    def load(self, im):
        if isinstance(im, str):
            im = Image.open(im)
        frames = []

        try:
            for i in count(1):
                frames.append(ImageTk.PhotoImage(im.copy()))
                im.seek(i)
        except EOFError:
            pass
        self.frames = cycle(frames)

        try:
            self.delay = im.info['duration']
        except:
            self.delay = 100

        if len(frames) == 1:
            self.config(image=next(self.frames))
        else:
            self.next_frame()

    def unload(self):
        self.config(image=None)
        self.frames = None

    def next_frame(self):
        if self.frames:
            self.config(image=next(self.frames))
            self.after(self.delay, self.next_frame)


class SplashScreen(tk.Frame):
    def __init__(self, master=None, width=0.4, height=0.3, useFactor=True):
        tk.Frame.__init__(self, master)
        # root.wm_attributes('-transparentcolor','#add123')

        # self.config(bg="#add123")
        self.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
        lbl = ImageLabel(root)
        logo_img = Image.open("imgs/inesc_logo.png")
        logo_img = logo_img.resize((166, 98))
        logo_lod = ImageTk.PhotoImage(logo_img)
        try:

            lbl.load('splash.gif')
        # Add widget with the splash screen image on it.
        # self.img = ImageTk.PhotoImage(file='splash.gif')
        # btn = tk.Label(self, image=self.img)
            Lablel_logo = tk.Label(image=logo_lod)
            Lablel_logo.image = logo_lod
            Lablel_logo.pack(expand=tk.YES, ipadx=10, ipady=10)
            lbl.pack(expand=tk.YES, ipadx=10, ipady=10)

        except:
            print("Splash Couldn't Load :(")
            pass
        load_text = tk.Label(self, text="Loading...\n Please wait....",
                             cursor="hand2", foreground="Black", font=('Aerial 48'))
        load_text.pack(expand=tk.YES, ipadx=10, ipady=10)
        # get screen width and height
        ws = self.master.winfo_screenwidth()
        hs = self.master.winfo_screenheight()
        w = (useFactor and ws * width) or width
        h = (useFactor and ws * height) or height

        # calculate position x, y
        x = (ws / 2) - (w / 1.8)
        y = (hs / 2) - (h / 1.4)
        self.master.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.master.overrideredirect(True)

        self.lift()

        def closesp():
            root.withdraw()
        root.after(4000, closesp)


class App:
    global pos_dring_cap_x, pos_dring_cap_y, next_pos_y, next_pos_x, current_pos_x, current_pos_y, update_x, update_y, step_size, current_pos_z, next_pos_z
    next_pos_y = 0
    current_pos_y = 0
    next_pos_x = 0
    current_pos_x = 0
    next_pos_z = 0
    current_pos_z = 0
    step_size = 0.05

    pos_dring_cap_x = 80
    pos_dring_cap_y = 120

    def __init__(self, window, window_title):
        # video_source=1):
        global console_win
        self.window = window

        # GUI WINODW!

        # self.window.attributes("-fullscreen", True)  # substitute `Tk` for whatever your `Tk()` object is called

        self.window.configure(background='White')
        self.window.title(' μ-Structure3D: GUI @INESC MN')
        self.window.iconbitmap("imgs/logo.ico")

        # Turn off the window shadow
        xrat = 4
        yrat = 12
        # self.window.geometry("1750x900")
        #self.window.eval('tk::PlaceWindow . center')
        w = self.window.winfo_reqwidth()
        h = self.window.winfo_reqheight()
        ws = self.window.winfo_screenwidth()
        hs = self.window.winfo_screenheight()

        x = (ws/xrat) - (w/xrat)
        y = (hs/yrat) - (h/yrat)
        # this part allows you to only change the location
        self.window.geometry('910x700+%d+%d' % (x, y))

        self.window.resizable(False, False)
        self.window.bind('<Escape>', self.close)

        def disable_event():
            pass
        # Disable the Close Window Control Icon
        self.window.protocol("WM_DELETE_WINDOW", disable_event)

        # Add image file
        try:
            global bg_img
            bg_img = ImageTk.PhotoImage(Image.open("imgs/bg.png"))

            jog = Image.open("imgs/topview.PNG")
            jog = jog.resize((553, 383))
            jog_lod = ImageTk.PhotoImage(jog)

            fnt = Image.open("imgs/frontview.PNG")
            fnt = fnt.resize((382, 645))
            fnt_lod = ImageTk.PhotoImage(fnt)

            logo_img = Image.open("imgs/inesc_logo.png")
            logo_img = logo_img.resize((83, 49))
            logo_lod = ImageTk.PhotoImage(logo_img)

            # Load images for buttons:

            ##import images

            sml_width = 40
            sml_height = 40

            med_width = 60
            med_height = 60

            r_1 = Image.open("imgs/right-1.png")
            r_1 = r_1.resize((sml_width, sml_height))
            r_1_lod = ImageTk.PhotoImage(r_1)

            r_2 = Image.open("imgs/right-2.png")
            r_2 = r_2.resize((sml_width, sml_height))
            r_2_lod = ImageTk.PhotoImage(r_2)

            l_1 = Image.open("imgs/left-1.png")
            l_1 = l_1.resize((sml_width, sml_height))
            l_1_lod = ImageTk.PhotoImage(l_1)

            l_2 = Image.open("imgs/left-2.png")
            l_2 = l_2.resize((sml_width, sml_height))
            l_2_lod = ImageTk.PhotoImage(l_2)

            dwn_1 = Image.open("imgs/down-1.png")
            dwn_1 = dwn_1.resize((sml_width, sml_height))
            dwn_1_lod = ImageTk.PhotoImage(dwn_1)

            dwn_2 = Image.open("imgs/down-2.png")
            dwn_2 = dwn_2.resize((sml_width, sml_height))
            dwn_2_lod = ImageTk.PhotoImage(dwn_2)

            up_1 = Image.open("imgs/up-1.png")
            up_1 = up_1.resize((sml_width, sml_height))
            up_1_lod = ImageTk.PhotoImage(up_1)

            up_2 = Image.open("imgs/up-2.png")
            up_2 = up_2.resize((sml_width, sml_height))
            up_2_lod = ImageTk.PhotoImage(up_2)

            quit_img_path = Image.open("imgs/quit.png")
            quit_img_path = quit_img_path.resize((60, 60))
            quit_img = ImageTk.PhotoImage(quit_img_path)

            serial_kin_img_path = Image.open("imgs/serial_robot.png")
            serial_kin_img_path = serial_kin_img_path.resize(
                (sml_width, sml_height))
            serial_kin_img = ImageTk.PhotoImage(serial_kin_img_path)

            homex_img_path = Image.open("imgs/home_x.png")
            homex_img_path = homex_img_path.resize((sml_width, sml_height))
            homex_img_lod = ImageTk.PhotoImage(homex_img_path)

            homey_img_path = Image.open("imgs/home_y.png")
            homey_img_path = homey_img_path.resize((sml_width, sml_height))
            homey_img_lod = ImageTk.PhotoImage(homey_img_path)

            homez_img_path = Image.open("imgs/home_z.png")
            homez_img_path = homez_img_path.resize((sml_width, sml_height))
            homez_img_lod = ImageTk.PhotoImage(homez_img_path)

            home_img_path = Image.open("imgs/home.png")
            home_img_path = home_img_path.resize((sml_width, sml_height))
            home_img_lod = ImageTk.PhotoImage(home_img_path)

            send_g_path = Image.open("imgs/send_g.png")
            send_g_path = send_g_path.resize((med_width, med_height))
            send_g_lod = ImageTk.PhotoImage(send_g_path)

            cam_img_path = Image.open("imgs/camrul.png")
            cam_img_path = cam_img_path.resize((med_width, med_height))
            cam_img_lod = ImageTk.PhotoImage(cam_img_path)

            auto_img_path = Image.open("imgs/automode.png")
            auto_img_path = auto_img_path.resize((med_width, med_height))
            auto_img_lod = ImageTk.PhotoImage(auto_img_path)

            send_img = Image.open("imgs/send.png")
            send_img = send_img.resize((30, 30))
            send_img_lod = ImageTk.PhotoImage(send_img)

            posinow_img = Image.open("imgs/posinow.png")
            posinow_img = posinow_img.resize((sml_width, sml_height))
            posinow_img_lod = ImageTk.PhotoImage(posinow_img)

        except:
            pass

        self.backdrop = tk.Canvas(self.window, width=1750, height=900)
        self.backdrop.place(x=0, y=0)
        self.backdrop.create_image(0, 0, anchor=tk.NW, image=bg_img)
        # self.backdrop.create_image(980,15,anchor=tk.NW ,image= btn_back_lod)
        # self.backdrop.create_image(50,140,anchor=tk.NW ,image= main_btn_back_lod)
        self.backdrop.create_rectangle(20, 30, 485, 370, fill="grey65")
        self.backdrop.create_rectangle(485, 30, 700, 370, fill="grey70")
        self.backdrop.create_rectangle(700, 30, 900, 370, fill="grey60")

        def delete_entry(event):
            event.widget.delete(0, "end")

        self.syr_id_var = tk.StringVar()
        self.t_thick_var = tk.IntVar()

        def updateval(*args):
            global t_um, syr_id_mm
            t_um = int(self.t_thick.get())
            syr_id_mm = self.syr_id.get()
            pass
        # try:
        # For t thicnkess rate only

        self.t_thick = tk.Entry(self.window, font=40)
        t_thick_val = (self.window.register(self.validate),
                       '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.t_thick = tk.Entry(self.window, width=6, textvariable=self.t_thick_var, font=(
            'Georgia 16'), validate='key', validatecommand=t_thick_val)
        self.t_thick.insert(tk.END, t_um)
        self.t_thick.place(x=300, y=285)
        self.t_thick_var.trace("w", updateval)

        # For t thicness rate only

        self.syr_id = tk.Entry(self.window, font=40)
        syr_id_val = (self.window.register(self.validate),
                      '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.syr_id = tk.Entry(self.window, width=6, textvariable=self.syr_id_var, font=(
            'Georgia 16'), validate='key', validatecommand=syr_id_val)
        self.syr_id.insert(tk.END, syr_id_mm)
        self.syr_id.place(x=300, y=315)
        self.syr_id_var.trace("w", updateval)
        # except:
        #     pass

        self.g_x_lbl = self.backdrop.create_text(
            160, 290, text="Wafer Thickness:", fill="black", font=('Helvetica 12 bold'), anchor=tk.NW)
        self.g_x_lbl = self.backdrop.create_text(
            200, 320, text="Syringe ID:", fill="black", font=('Helvetica 12 bold'), anchor=tk.NW)

        self.g_x_lbl = self.backdrop.create_text(
            400, 290, text="(um)", fill="black", font=('Helvetica 12 bold'), anchor=tk.NW)
        self.g_x_lbl = self.backdrop.create_text(
            400, 320, text="(mm)", fill="black", font=('Helvetica 12 bold'), anchor=tk.NW)

        self.can_jog = tk.Canvas(
            self.window, bg='white', width=850, height=310)
        self.can_jog.place(x=25, y=380)

        # For Feed rate only
        self.g_feed = tk.Entry(self.window, font=40)
        g_feed_val = (self.window.register(self.validate),
                      '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.g_feed = tk.Entry(self.window, width=6, font=(
            'Georgia 16'), validate='key', validatecommand=g_feed_val)
        self.g_feed.insert(tk.END, "")

        # For movement /move+extru

        self.g_code_x = tk.Entry(self.window, font=40)
        g_code_x_val = (self.window.register(self.validate),
                        '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.g_code_x = tk.Entry(self.window, width=6, font=(
            'Georgia 16'), validate='key', validatecommand=g_code_x_val)
        self.g_code_x.insert(tk.END, "")

        self.g_code_y = tk.Entry(self.window, font=40)
        g_code_y_val = (self.window.register(self.validate),
                        '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.g_code_y = tk.Entry(self.window, width=6, font=(
            'Georgia 16'), validate='key', validatecommand=g_code_y_val)
        self.g_code_y.insert(tk.END, "")

        self.g_code_z = tk.Entry(self.window, font=40)
        g_code_z_val = (self.window.register(self.validate),
                        '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.g_code_z = tk.Entry(self.window, width=6, font=(
            'Georgia 16'), validate='key', validatecommand=g_code_z_val)
        self.g_code_z.insert(tk.END, "")

        # extension of syringe (extruder mm)
        self.ext_pos = tk.Entry(self.window, font=40)
        ext_pos_val = (self.window.register(self.validate),
                       '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.ext_pos = tk.Entry(self.window, width=6, font=(
            'Georgia 16'), validate='key', validatecommand=ext_pos_val)
        self.ext_pos.insert(tk.END, "")

        # Flow of syringe (extruder mm)
        self.flow_per = tk.Entry(self.window, font=40)
        flow_per_val = (self.window.register(self.validate),
                        '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.flow_per = tk.Entry(self.window, width=6, font=(
            'Georgia 16'), validate='key', validatecommand=flow_per_val)
        self.flow_per.insert(tk.END, "")

        def g_selector(choice):
            global g_choice, g_code_x, g_code_y, g_feed

            choice = self.g_var.get()
            g_choice = str(choice)

            if choice == "Move Only":

                self.g_code_x.place(x=entry_pos_x, y=150+y_padding*0)

                self.g_code_y.place(x=entry_pos_x, y=150+y_padding*1)

                self.g_code_z.place(x=entry_pos_x, y=150+y_padding*2)

                self.g_feed.place_forget()

                self.ext_pos.place_forget()
                self.flow_per.place_forget()

            elif choice == "Move & Extrude":

                self.g_code_x.place(x=entry_pos_x, y=150+y_padding*0)

                self.g_code_y.place(x=entry_pos_x, y=150+y_padding*1)

                self.g_code_z.place(x=entry_pos_x, y=150+y_padding*2)
                self.g_feed.place(x=entry_pos_x, y=150+y_padding*3)

                self.ext_pos.place(x=entry_pos_x, y=150+y_padding*4)

                self.flow_per.place_forget()

            elif choice == "Travel Feedrate":
                self.g_code_x.place_forget()

                self.g_code_y.place_forget()

                self.g_code_z.place_forget()
                self.ext_pos.place_forget()

                self.flow_per.place_forget()

                self.g_feed.place(x=entry_pos_x, y=150+y_padding*3)

            elif choice == "Flow %":
                self.g_code_x.place_forget()

                self.g_code_y.place_forget()

                self.g_code_z.place_forget()
                self.ext_pos.place_forget()

                self.g_feed.place_forget()
                self.flow_per.place(x=entry_pos_x, y=150+y_padding*5)

            print(g_choice)

            self.window.update()

  ####################G code selector // dropdown to select commands types#####################
        entry_pos_x = 610
        y_padding = 32
        input_x_pos = 540

        g_list = ["Move Only", "Move & Extrude", "Travel Feedrate", "Flow %"]
        self.g_var = tk.StringVar(self.window)
        self.g_var.set("Select a command ")  # default value
        g_drop = tk.OptionMenu(self.window, self.g_var,
                               *g_list, command=g_selector)
        g_drop.config(width=25)
        g_drop.place(x=input_x_pos-40, y=y_padding+60)

        self.bnt_send_gvals = tk.Button(window, command=lambda e="send_g_values": self.serial_start_kin(
            e), image=send_img_lod, width=40, height=185)
        self.bnt_send_gvals.place(x=input_x_pos-50, y=150)

        self.g_x_lbl = self.backdrop.create_text(
            input_x_pos, 60+y_padding*0, text="Select Command:", fill="black", font=('Helvetica 12 bold'), anchor=tk.NW)
        self.g_x_lbl = self.backdrop.create_text(
            input_x_pos, 150+y_padding*0, text="X", fill="black", font=('Helvetica 16 bold'), anchor=tk.NW)
        self.g_x_lbl = self.backdrop.create_text(
            input_x_pos, 150+y_padding*1, text="Y", fill="black", font=('Helvetica 16 bold'), anchor=tk.NW)
        self.g_x_lbl = self.backdrop.create_text(
            input_x_pos, 150+y_padding*2, text="Z", fill="black", font=('Helvetica 16 bold'), anchor=tk.NW)
        self.g_x_lbl = self.backdrop.create_text(
            input_x_pos, 150+y_padding*3, text="Feed", fill="black", font=('Helvetica 12 bold'), anchor=tk.NW)
        self.g_x_lbl = self.backdrop.create_text(
            input_x_pos, 150+y_padding*4, text="Ext", fill="black", font=('Helvetica 12 bold'), anchor=tk.NW)
        self.g_x_lbl = self.backdrop.create_text(
            input_x_pos, 150+y_padding*5, text="Flow %", fill="black", font=('Helvetica 12 bold'), anchor=tk.NW)

        self.window.update()

        self.backdrop.create_text(250, 6, text="3D-μ-deposition Computer Vision Interface ",
                                  fill="black", font=('Helvetica 18 bold'), anchor=tk.NW)

        def slider_changed(event, sliders):
            global step_size
            if sliders == "step":
                if slider_ex.get() == 1:
                    step_size = 0.1
                elif slider_ex.get() == 2:
                    step_size = 1
                elif slider_ex.get() == 3:
                    step_size = 10
                print(step_size)
                print(slider_ex.get())

            # elif sliders== "acce":
            #     print(slider_ac.get())
            # elif sliders== "feed":
            #     print(slider_feed.get())

        self.can_jog.create_image(0, 0, anchor=tk.NW, image=jog_lod)
        self.can_jog.create_image(560, -150, anchor=tk.NW, image=fnt_lod)

        self.can_jog.create_image(450, 250, anchor=tk.NW, image=logo_lod)

        self.can_jog.create_text(600, 250, text=" by Rahill Ismael\n INESCMN 2022",
                                 fill="white", font=('Helvetica 13 bold'), anchor=tk.NW)

        global slider_ex
        current_value_step = tk.DoubleVar()
        slider_ex = tk.Scale(self.window, from_=1, to=3, length=300, tickinterval=1, orient='vertical',
                             variable=current_value_step, command=lambda b="", e="step": slider_changed(b, e))
        slider_ex.place(x=50, y=380)

        self.backdrop.create_text(40, 330, text="Select Step Size \n - 0.1mm/1mm/10mm/",
                                  fill="black", font=('Helvetica 12 bold'), anchor=tk.NW)

        self.can_jog.create_text(70, 20, text="0.1mm", fill="white", font=(
            'Helvetica 12 bold'), anchor=tk.NW)
        self.can_jog.create_text(70, 150, text="1mm", fill="white", font=(
            'Helvetica 12 bold'), anchor=tk.NW)
        self.can_jog.create_text(70, 250, text="10mm", fill="white", font=(
            'Helvetica 12 bold'), anchor=tk.NW)

        self.vid = None
        self.window.update()
# VARIABLES

        # Buttons user for
        main_btn_padding = 50
        y_pos_srlbtn = 400
        x_pos_srlbtn = 725
        self.backdrop.create_text(750, 40, text="Force Quit", fill="red", font=(
            'Helvetica 14 bold'), anchor=tk.NW)

        self.btn_quit = tk.Label(window, text="Quit", cursor="hand2",
                                 foreground="green", font=('Aerial 18'), image=quit_img)
        self.btn_quit.place(x=750, y=60)
        self.btn_quit.bind("<Button-1>", lambda e="esc": self.close(e))

        panel_start_button_x = 725
        panel_start_button_y = 270

        self.backdrop.create_text(x_pos_srlbtn, panel_start_button_y-140,
                                  text="Port Found:", fill="white", font=('Helvetica 14 bold'), anchor=tk.NW)

        self.backdrop.create_text(x_pos_srlbtn-20, panel_start_button_y-80,
                                  text="Machine IO", fill="white", font=('Helvetica 14 bold'), anchor=tk.NW)

        self.backdrop.create_text(x_pos_srlbtn+50, panel_start_button_y-30,
                                  text="Connect", fill="white", font=('Helvetica 12 '), anchor=tk.NW)

        self.backdrop.create_text(x_pos_srlbtn+50, panel_start_button_y+10,
                                  text="Home All", fill="white", font=('Helvetica 12 '), anchor=tk.NW)

        self.backdrop.create_text(x_pos_srlbtn+50, panel_start_button_y+50,
                                  text="Get Position", fill="white", font=('Helvetica 12 '), anchor=tk.NW)

        # Button that lets connection via serial 3d platform
        self.btn_serial_start = tk.Button(
            window, command=lambda e="connect": self.serial_start_kin(e), image=serial_kin_img)
        self.btn_serial_start.place(
            x=panel_start_button_x, y=panel_start_button_y-50)
        self.window.update()

        # Button that lets connection via serial 3d platform
        # self.bnt_send_gvals= tk.Label(window, text= "Send Values", cursor= "hand2", foreground= "green", font= ('Aerial 18'),image = send_img_lod)
        # self.bnt_send_gvals.place(x=panel_start_button_x,y=panel_start_button_y)
        # self.bnt_send_gvals.bind("<Button-1>", lambda e="send_g_values": self.serial_start_kin(e))

        self.btn_home = tk.Button(
            window, command=lambda e="home": self.serial_start_kin(e), image=home_img_lod)
        self.btn_home.place(x=panel_start_button_x, y=panel_start_button_y)
        self.window.update()

        # # Button that lets connection via serial 3d platform
        # self.btn_home= tk.Label(window, text= "home", cursor= "hand2", foreground= "green", font= ('Aerial 18'),image = home_img_lod)
        # self.btn_home.place(x=panel_start_button_x,y=panel_start_button_y+80)
        # self.btn_home.bind("<Button-1>", lambda e="home": self.serial_start_kin(e))

        # Button that lets connection via serial 3d platform
        self.position_3d = tk.Button(
            window, command=lambda e="get_pos_now": self.serial_start_kin(e), image=posinow_img_lod)
        self.position_3d.place(x=panel_start_button_x,
                               y=panel_start_button_y+50)
        self.window.update()

        # self.position_3d= tk.Label(window, text= "Get Position Now", cursor= "hand2", foreground= "green", font= ('Aerial 18'),image = posinow_img_lod)
        # self.position_3d.place(x=panel_start_button_x,y=panel_start_button_y+160)
        # self.position_3d.bind("<Button-1>", lambda e="get_pos_now": self.serial_start_kin(e))

        perp_pos_x = 70
        perp_pos_y = 105
        perp_btn_x = 50
        perp_btn_y = 195

        self.backdrop.create_text(perp_pos_x-main_btn_padding, perp_pos_y*1.65,
                                  text="SetupG-Code:", fill="black", font=('Helvetica  12 bold'), anchor=tk.NW)

        self.backdrop.create_text(perp_pos_x+main_btn_padding*1.5, perp_pos_y*1.65,
                                  text="Measure+Align :", fill="black", font=('Helvetica  12 bold'), anchor=tk.NW)
        self.backdrop.create_text(perp_pos_x+main_btn_padding*4.5, perp_pos_y*1.65,
                                  text="Automode:", fill="black", font=('Helvetica  12 bold'), anchor=tk.NW)

        self.btn_startgcode = tk.Button(
            window, command=self.start_gcode, image=send_g_lod)
        self.btn_startgcode.place(x=perp_btn_x, y=perp_btn_y)
        self.window.update()

        self.camrul_btn = tk.Button(
            window, command=self.camrul_f, image=cam_img_lod)
        self.camrul_btn.place(x=perp_btn_x+main_btn_padding*2.5, y=perp_btn_y)
        self.window.update()

        self.auto_mode_btn = tk.Button(
            window, command=self.auto_mode, image=auto_img_lod)
        self.auto_mode_btn.place(x=perp_btn_x+main_btn_padding*5, y=perp_btn_y)
        self.window.update()

        global portselec

        portselec = tk.StringVar(self.window)

        # def display_selected(choice_kin):

        #     choice_of_port=  portselec.get()
        #     print(choice_of_port)

        if no_ports == False:

            try:
                portselec.set(port_kin_found)
                portselec = tk.OptionMenu(
                    self.window, portselec, *arduino_ports)
                # ,command=display_selected)
                portselec.place(x=x_pos_srlbtn, y=155)
            except:

                portselec.set("Not found")
                print("No additional  port found")
        else:
            portselec.set("Port Not Found")
            portselec = tk.OptionMenu(window, portselec, "No Ports")
            portselec.place(x=x_pos_srlbtn, y=155)

        self.window.update()

        # Creating the movement buttons
        center_jog_y = 530
        center_jog_x = 270
        jog_padding = 50
        self.moveup1 = tk.Label(image=up_1_lod)
        self.moveup1_btn = tk.Button(
            self.window, command=lambda e="up1": self.movebuttons(e), image=up_1_lod)
        self.moveup1_btn.place(x=center_jog_x, y=center_jog_y-jog_padding)

        self.window.update()

        self.moveup2 = tk.Label(self.window, image=up_2_lod)
        self.moveup2_btn = tk.Button(
            self.window, command=lambda e="up2": self.movebuttons(e), image=up_2_lod)
        self.moveup2_btn.place(x=center_jog_x, y=center_jog_y-jog_padding*2)
        self.window.update()

        self.movedwn1 = tk.Label(window, image=dwn_1_lod)
        self.movedwn1_btn = tk.Button(
            self.window, command=lambda e="dwn1": self.movebuttons(e), image=dwn_1_lod)
        self.movedwn1_btn.place(x=center_jog_x, y=center_jog_y+jog_padding)
        self.window.update()

        self.movedwn2 = tk.Label(window, image=dwn_2_lod)
        self.movedwn2_btn = tk.Button(
            self.window, command=lambda e="dwn2": self.movebuttons(e), image=dwn_2_lod)
        self.movedwn2_btn.place(x=center_jog_x, y=center_jog_y+jog_padding*2)
        self.window.update()

        self.right_1 = tk.Label(window, image=r_1_lod)
        self.right_1_btn = tk.Button(
            self.window, command=lambda e="right1": self.movebuttons(e), image=r_1_lod)
        self.right_1_btn.place(x=center_jog_x+jog_padding, y=center_jog_y)
        self.window.update()

        self.right_2 = tk.Label(window, image=r_2_lod)
        self.right_2_btn = tk.Button(
            self.window, command=lambda e="right2": self.movebuttons(e), image=r_2_lod)
        self.right_2_btn.place(x=center_jog_x+jog_padding*2, y=center_jog_y)
        self.window.update()

        self.left_1 = tk.Label(window, image=l_1_lod)
        self.left_1_btn = tk.Button(
            self.window, command=lambda e="left1": self.movebuttons(e), image=l_1_lod)
        self.left_1_btn.place(x=center_jog_x-jog_padding, y=center_jog_y)
        self.window.update()

        self.left_2 = tk.Label(window, image=l_2_lod)
        self.left_2_btn = tk.Button(
            self.window, command=lambda e="left2": self.movebuttons(e), image=l_2_lod)
        self.left_2_btn.place(x=center_jog_x-jog_padding*2, y=center_jog_y)
        self.window.update()

        self.z_up = tk.Label(window, image=up_1_lod)
        self.z_up_btn = tk.Button(
            self.window, command=lambda e="zup": self.movebuttons(e), image=up_1_lod)
        self.z_up_btn.place(x=center_jog_x+jog_padding*8, y=center_jog_y)
        self.window.update()

        self.z_dwn = tk.Label(window, image=dwn_1_lod)
        self.z_dwn_btn = tk.Button(
            self.window, command=lambda e="zdwn": self.movebuttons(e), image=dwn_1_lod)
        self.z_dwn_btn.place(x=center_jog_x+jog_padding *
                             8, y=center_jog_y+jog_padding)
        self.window.update()

        # Button that lets connection via serial 3d platform
        self.btn_homex = tk.Button(
            window, command=lambda e="homex": self.serial_start_kin(e), image=homex_img_lod)
        self.btn_homex.place(x=center_jog_x+jog_padding*3, y=center_jog_y)
        self.window.update()

        # Button that lets connection via serial 3d platform
        self.btn_homey = tk.Button(
            window, command=lambda e="homey": self.serial_start_kin(e), image=homey_img_lod)
        self.btn_homey.place(x=center_jog_x, y=center_jog_y-jog_padding*3)
        self.window.update()

        # Button that lets connection via serial 3d platform
        self.btn_homez = tk.Button(
            window, command=lambda e="homez": self.serial_start_kin(e), image=homez_img_lod)
        self.btn_homez.place(x=center_jog_x+jog_padding*7,
                             y=center_jog_y+(jog_padding/2))
        self.window.update()

        self.window.update()

     # After it is called once, the update method will be automatically called every delay milliseconds
        self.delay = 3000
        self.endprog = False
        self.update()

        console_win = tk.Listbox(self.window, height=7, width=50)
        console_win.place(x=35, y=45)
        # will use the default font
        bolded = tk.font.Font(weight='bold', size=10)
        console_win.config(font=bolded)

        console_win.insert(0, "Laucnhed! Connect to get started ")
        console_win.insert(0, "Check flowchart for user operation")
        console_win.insert(0, "Loading....")

        self.window.mainloop()

    def update_x_or_y(self, X_or_Y, next_pos):
        global next_pos_y, next_pos_x, current_pos_x, current_pos_y, update_x, update_y, step_size, current_pos_z, next_pos_z
        if X_or_Y == "X":
            if next_pos <= 0:
                current_pos_x = 0
            else:
                current_pos_x = next_pos

            print(current_pos_x)

        if X_or_Y == "Y":

            if next_pos <= 0:
                current_pos_y = 0
            else:
                current_pos_y = next_pos

            print(current_pos_y)

        if X_or_Y == "Z":
            if next_pos <= 0:
                current_pos_z = 0
            else:
                current_pos_z = next_pos

            print(current_pos_z)

    def close(self, key):
        global baudrate, s_kin, s_ink

        try:
            if s_kin.isOpen() == True:
                s_kin.close()
                print("Serial Kin Closed")
            else:
                print("wasnt open")

        except:
            print("Quit but 3d serial was not disconnected successfully :(")
        self.window.destroy()
        root.destroy()
        # self.window.quit()
        # sys.exit(0)

    def validate(self, action, index, value_if_allowed,
                 prior_value, text, validation_type, trigger_type, widget_name):
        global g_code_x_val, g_code_y_val, g_code_z_val, g_code_feed_val, ext_pos_val, flow_per_val, t_um, syr_id_mm
        if value_if_allowed:
            try:
                print(widget_name)

                float(value_if_allowed)
                if widget_name == ".!toplevel.!entry2":
                    print(self.t_thick.get())
                    t_um = int(self.t_thick.get())

                if widget_name == ".!toplevel.!entry4":
                    print(self.syr_id.get())
                    syr_id_mm = self.syr_id.get()

                if widget_name == ".!toplevel.!entry6":
                    print(self.g_feed.get())
                    g_code_feed_val = self.g_feed.get()
                if widget_name == ".!toplevel.!entry8":

                    g_code_x_val = self.g_code_x.get()
                    print(self.g_code_x.get())
                if widget_name == ".!toplevel.!entry10":
                    print(self.g_code_y.get())
                    g_code_y_val = self.g_code_y.get()
                if widget_name == ".!toplevel.!entry12":
                    print(self.g_code_z.get())
                    g_code_z_val = self.g_code_z.get()

                if widget_name == ".!toplevel.!entry14":
                    print(self.ext_pos.get())
                    ext_pos_val = self.g_feed.get()

                if widget_name == ".!toplevel.!entry16":
                    print(self.flow_per.get())
                    flow_per_val = self.g_feed.get()

                return True
            except ValueError:
                return False
        else:
            return False

    def serial_start_kin(self, command):
        # baudrate
        global baudrate_kin, serial_ink_stat, cond, s_kin, arduino_ports, read_pos
        baudrate_kin = 115200
        # try open serial for the 3d printer platofrm

        # s_kin=sr.Serial(arduino_ports[0],baudrate_kin,parity=sr.PARITY_ODD,stopbits=sr.STOPBITS_ONE,bytesize=sr.EIGHTBITS,timeout=0);
        def command_kin(s_kin, command):

            global current_pos_x, current_pos_y, current_pos_z, xcord, ycord

            print(command)

            s_kin.write(str.encode(command+"\r\n"))
            # time.sleep(1)

            while True:
                if command == "M114":
                    line = s_kin.readline()
                    line_decoded = line.decode()
                    try:
                        found_x = re.search('X:(.+?)Y:', line_decoded).group(1)
                        found_y = re.search('Y:(.+?)Z:', line_decoded).group(1)
                        found_z = re.search('Z:(.+?)E:', line_decoded).group(1)

                        current_pos_x = found_x
                        current_pos_y = found_y
                        current_pos_z = found_z
                        xcord = found_x
                        ycord = found_y
                        print(found_x)
                        print(found_y)
                        print(found_z)
                        self.position_3d.config(activebackground="green")

                    except AttributeError:
                        # AAA, ZZZ not found in the original string
                        found_x = '?'  # apply your error handling
                        found_y = '?'
                        found_z = '?'
                else:
                    line = s_kin.readline()

                print(line)

                if line == b'ok\n':
                    break
        if no_ports == False:

            # try:
            def connect_check_message():
                global s_kin, g_code_x_val, g_code_y_val, g_code_feed_val, g_code_z_val, serial_kin_stat, command
                s_kin = sr.Serial(port_kin_found, 115200)

                if s_kin.isOpen() == True:

                    while True:
                        line = s_kin.readline()
                        print(line)
                        if line == b'start\n':
                            command = ""
                            serial_kin_stat = True
                            self.btn_serial_start.configure(bg="Green")

                            command_kin(s_kin, "M114")
                            break

                        # if line == b'echo:Hardcoded Default Settings Loaded\n':

                # else:
                #     print("The serial port didnt open... trying again....")
                #     self.btn_serial_start.configure(bg="Red")
                #     sr.Serial(port_kin_found,baudrate).close()

                #     self.btn_serial_start.configure(bg="Orange")
                #     connect_check_message()

            if command == "connect":

                connect_check_message()

            if serial_kin_stat == True:

                if command == "home":
                    command_kin(s_kin, "G28")

                    command_kin(s_kin, "M114")
                elif command == "homex":
                    command_kin(s_kin, "G28 X")
                elif command == "homey":
                    command_kin(s_kin, "G28 Y")
                elif command == "homez":
                    command_kin(s_kin, "G28 Z")
                elif command == "refresh_srl":
                    pass
                elif command == "get_pos_now":
                    command_kin(s_kin, "M114")
                elif command == "send_g_values":

                    x_ax = g_code_x_val
                    y_ax = g_code_y_val
                    z_ax = g_code_z_val
                    f_rate = g_code_feed_val
                    ext = ext_pos_val
                    flowr = flow_per_val

                    if g_choice == "Move Only":

                        message = "G0 X{} Y{} Z{}".format(x_ax, y_ax, z_ax)
                        command_kin(s_kin, message)

                    elif g_choice == "Move & Extrude":

                        message = "G0 F{} X{} Y{} Z{} E{}".format(
                            f_rate, x_ax, y_ax, z_ax, ext)
                        command_kin(s_kin, message)

                    elif g_choice == "Travel Feedrate":

                        message = "G0 F{}".format(f_rate)
                        print(message)
                        command_kin(s_kin, message)
                    elif g_choice == "Flow %":

                        message = "M221 S{}".format(flowr)
                        print(message)
                        command_kin(s_kin, message)
                else:
                    print(command)

                    if command != "connect":

                        command_kin(s_kin, command)
            else:
                print("serial3d not connected")

            # ##catch serial error and try to close the open port
            # except serial.SerialException:
            #     for i in arduino_ports:
            #         sr.Serial(arduino_ports[i],baudrate).close()
            #         print ("Port was already open but now is closed")
            #         s_kin=sr.Serial(arduino_ports[i],baudrate)
            #         print ("Port is open again!")

    def movebuttons(self, movement_key):
        global next_pos_y, next_pos_x, current_pos_x, current_pos_y, update_x, update_y, step_size, current_pos_z
        if movement_key == "up1":

            next_pos_y = round(float(current_pos_y)+step_size, 2)

            self.update_x_or_y("Y", next_pos_y)

            EX = lambda e="G1 Y"+str(next_pos_y) + \
                "\r\n": self.serial_start_kin(e)
            EX()

        elif movement_key == "up2":

            next_pos_y = round(float(current_pos_y)+step_size*5, 2)

            self.update_x_or_y("Y", next_pos_y)

            EX = lambda e="G1 Y"+str(next_pos_y) + \
                "\r\n": self.serial_start_kin(e)
            EX()
        elif movement_key == "dwn1":
            next_pos_y = round(float(current_pos_y)-step_size, 2)

            self.update_x_or_y("Y", next_pos_y)
            EX = lambda e="G1 Y"+str(next_pos_y) + \
                "\r\n": self.serial_start_kin(e)
            EX()

        elif movement_key == "dwn2":
            next_pos_y = round(float(current_pos_y)-step_size*5, 2)

            self.update_x_or_y("Y", next_pos_y)
            EX = lambda e="G1 Y"+str(next_pos_y) + \
                "\r\n": self.serial_start_kin(e)
            EX()
        elif movement_key == "right1":
            next_pos_x = round(float(current_pos_x)+step_size, 2)

            self.update_x_or_y("X", next_pos_x)
            EX = lambda e="G1 X"+str(next_pos_x) + \
                "\r\n": self.serial_start_kin(e)
            EX()

        elif movement_key == "right2":
            next_pos_x = round(float(current_pos_x)+step_size*5, 2)
            self.update_x_or_y("X", next_pos_x)
            EX = lambda e="G1 X"+str(next_pos_x) + \
                "\r\n": self.serial_start_kin(e)
            EX()

        elif movement_key == "left1":
            next_pos_x = round(float(current_pos_x)-step_size, 2)
            self.update_x_or_y("X", next_pos_x)
            EX = lambda e="G1 X"+str(next_pos_x) + \
                "\r\n": self.serial_start_kin(e)

            EX()
        elif movement_key == "left2":

            next_pos_x = round(float(current_pos_x)-step_size*5, 2)
            self.update_x_or_y("X", next_pos_x)
            EX = lambda e="G1 X"+str(next_pos_x) + \
                "\r\n": self.serial_start_kin(e)
            EX()

        elif movement_key == "zup":

            next_pos_z = round(float(current_pos_z)-step_size)
            self.update_x_or_y("Z", next_pos_z)
            EX = lambda e="G1 Z"+str(next_pos_z) + \
                "\r\n": self.serial_start_kin(e)
            EX()

        elif movement_key == "zdwn":

            next_pos_z = round(float(current_pos_z)+step_size)
            self.update_x_or_y("Z", next_pos_z)

            EX = lambda e="G1 Z"+str(next_pos_z) + \
                "\r\n": self.serial_start_kin(e)
            EX()

    # fucntion tied to try serial to open port at baude with normal parity and stop bit

    def restart(self):

        self.window.destroy()
        App(tk.Toplevel(), "μ-structure 3D Control Panel")

    def start_gcode(self):
        global g_port, emerg_stop
        global g_port, filename, newPath
        filename = ""
        newPath = ""
        g_port = ""
        self.gc_win = tk.Toplevel(self.window)
        self.gc_win.title("GCode Import")
        self.gc_win.configure(background='grey90')
        self.gc_win.geometry("700x700")

        g_code_bg = tk.Canvas(self.gc_win, width=700, height=700)
        g_code_bg.place(x=0, y=0)

        g_code_bg.create_image(0, 0, anchor=tk.NW, image=bg_img)
        g_code_bg.create_rectangle(5, 5, 695, 100, fill='grey81')
        g_code_bg.create_rectangle(250, 105, 695, 600, fill='grey81')

        g_code_bg.create_text(40, 40, text="GCODE Importer", fill='black', font=(
            'Helvetica 16 bold'), anchor=tk.NW)
        g_code_bg.create_text(50, 65, text="Select Gcode File To Send", fill='black', font=(
            'Helvetica 12 bold'), anchor=tk.NW)

        Lb1 = tk.Listbox(self.gc_win, height=10, width=60)
        Lb1.insert(tk.END, "Starting.......")
        if serial_kin_stat == True:
            Lb1.insert(tk.END, "Serial is connected !")
        else:
            Lb1.insert(tk.END, "Nothing is connected")

        Lb1.place(x=5, y=490)

        def browsefunc():
            global filename, newPath
            filename = filedialog.askopenfilename(filetypes=(
                ("G-Code File", "*.gcode"), ("All files", "*.*")))
            # ent1.insert(tk.END, filename) # add this
            file_ent.delete(0, tk.END)
            file_ent.insert(tk.END, filename)
            newPath = filename.replace('\\', '/')

            g_code_v = subprocess.Popen(
                [sys.executable, './altviewer.py test.gcode'])
            print(newPath)
        self.gc_but = tk.Button(
            self.gc_win, text="Select Path:", command=browsefunc)
        self.gc_but.place(x=60, y=175)

        g_code_bg.create_text(40, 100, text="Select Path:",
                              fill='black', font=('Helvetica 16 '), anchor=tk.NW)
        file_ent = tk.Entry(self.gc_win, font=40, width=50)
        file_ent.place(x=5, y=665)
        file_ent.config(state='readonly')

        def _create_circle(self, x, y, r, **kwargs):
            return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
        tk.Canvas.create_circle = _create_circle
        g_code_bg.create_circle(
            125, 335, 70, fill="white", outline="red", width=6)
        port_but_stop = tk.Button(
            self.gc_win, text="Emergency Stop!!", command=emerg_stop != emerg_stop)
        port_but_stop.place(x=75, y=325)

        def send_g_code(g_port, newPath):
            # try:
            # execfile('gcodesender.py')
            # subprocess.call(['C:/Users/Admin/anaconda3/python.exe','C:/Users/Admin/Desktop/Printer/gcodesender.py','-p', 'COM3', '-f', 'C:/Users/Admin/Desktop/CFFFP_side_syringle.gcode'],shell=True)
            print(newPath)
            # print("Gcode_launched")
            try:
                sr.Serial(arduino_ports[0], baudrate).close()
                sr.Serial(arduino_ports[1], baudrate).close()
                print("ports closed")
            except:
                print("couldnt disconnect the serial")

            def removeComment(string):
                if (string.find(';') == -1):
                    return string
                else:
                    return string[:string.index(';')]

            # Open serial port
            #s = serial.Serial('/dev/ttyACM0',115200)
            # try:

            s_sender = sr.Serial(port_kin_found, 115200)

            print('Opening Serial Port')
            # except:
            print("couldnt open the serial")

            # Open g-code file
            #f = open('/media/UNTITLED/shoulder.g','r');
            f = open(newPath, 'r')
            print('Opening gcode file')

            # Wake up
            # Hit enter a few times to wake the Printrbot
            s_sender.write(str.encode("\r\n\r\n"))
            time.sleep(2)   # Wait for Printrbot to initialize
            s_sender.flushInput()  # Flush startup text in serial input
            print('Sending gcode')
            z = 0
            # Stream g-code
            for line in f:

                l = removeComment(line)
                l = l.strip()  # Strip all EOL characters for streaming
                if (l.isspace() == False and len(l) > 0):
                    print('Sending: ' + l)
                    Lb1.insert(z, l)
                    s_sender.write(str.encode(l + '\r\n'))  # Send g-code block
            while True:
                line = s_sender.readline()
                print(line.decode())

                if line == b'ok\n':
                    break
            grbl_out = s_sender.readline()  # Wait for response with carriage return
            grbl_decodestr = grbl_out.strip()
            print(grbl_decodestr)

            # Wait here until printing is finished to close serial port and file.
            input("  Press <Enter> to exit.")

            # Close file and serial port
            f.close()
            s_sender.close()
            # except:
            # print("unable to launch g-code")

    def auto_mode(self):
        autowin = tk.Toplevel(self.window)
        autowin.title("Automode")
        autowin.configure(background='white')

        def closeauto():
            autowin.destroy()

        autowin.bind('<Escape>', lambda e="": closeauto())
        # autowin.geometry("700x700")

        # Turn off the window shadow
        xrat = 4
        yrat = 10
        # self.window.geometry("1750x900")
        #self.window.eval('tk::PlaceWindow . center')
        w = autowin.winfo_reqwidth()
        h = autowin.winfo_reqheight()
        ws = autowin.winfo_screenwidth()
        hs = autowin.winfo_screenheight()

        x = (ws/xrat) - (w/xrat)
        y = (hs/yrat) - (h/yrat)
        # this part allows you to only change the location
        autowin.geometry('800x700+%d+%d' % (x, y))

        autowin.resizable(False, False)

        automode_bg = tk.Canvas(autowin, width=800, height=700)
        automode_bg.place(x=0, y=0)

        automode_bg.create_image(0, 0, anchor=tk.NW, image=bg_img)
        automode_bg.create_rectangle(5, 0, 500, 100, fill='white')

        automode_bg.create_text(45, 30, text="Autonomous Mode", fill='black', font=(
            'Helvetica 14 bold'), anchor=tk.NW)

        automode_bg.create_text(25, 70, text="Please choose area", fill='black', font=(
            'Helvetica 12 bold'), anchor=tk.NW)

        bed_sele = tk.Canvas(autowin, width=640, height=480)

        bed_sele.create_oval(-5, -5, 5, 5, fill="red")
        bed_sele.configure(scrollregion=(-320, -240, 320, 240))
        bed_sele.xview_moveto(.5)
        bed_sele.yview_moveto(.5)
        bed_sele.place(x=50, y=120)
        # bed_sele.create_rectangle(0,0,250,250,fill='silver')
        bed_sele.create_line(-320, 0, 320, 0, fill="green", width=1)  # x axis
        bed_sele.create_line(0, -240, 0, 240, fill="green", width=1)  # y axis
        cor_list = np.array([""])

        try:
           # Read the csv file with first row skipped
            df = pd.read_csv("Distances_temp.csv")

            df.head()
            array_size = len(df)
            console_win.insert(0, "Number of points {}".format(array_size))
            print(array_size)
            time_cv = df["Time"]
            console_win.insert(
                0, "First capture taken at {}".format(time_cv[0]))

            Xlen_cv = df["X Length"]

            Ylen_cv = df["Y Length"]

            x1_cv = df["x1"]

            x2_cv = df["x2"]

            y1_cv = df["y1"]

            y2_cv = df["y2"]

            x_cords = df["xcord"]
            y_cords = df["ycord"]
            # print (Xlen_cv)
            # print (Ylen_cv)

            console_win.insert(0, "Captured at X {} and  Y{}".format(
                x_cords[len(x_cords)-1], y_cords[len(y_cords)-1]))

            # net_store_cv_x.append(net_x)
            # net_y=abs(y2_cv[i]-y1_cv[i])

            # print(net_y[i])
            # x_pixlen=(Xlen_cv[i]/net_x[i])
            # y_pixlen=(Ylen_cv[i]/net_y[i])

            # console_win.insert(0, y_pixlen[1])
            # print(net_store_cv_x)

            # print(Ypairs)
        except:
            pass

        def abs_cal(v1, v2):
            return (abs(v2-v1))
        global Xpairs, Ypairs, x_len_per_pix, y_len_per_pix
        Xpairs = []
        Ypairs = []
        x_len_per_pix = []
        y_len_per_pix = []
        x_dir = []
        y_dir = []
        x_cv_diff = []
        y_cv_diff = []
        x_2dir = []

        y_2dir = []
        x_2dir = []
        x2_cv_diff = []
        y2_cv_diff = []

        y_mid_diff = []
        x_mid_diff = []
        cor_list = []

        travel_x = []
        travel_y = []
        area_xy = []
        vol_um = []
        vol_uL = []
        fig = Figure()

        # canvas = FigureCanvasTkAgg(fig, master =autowin)
        # # placing the canvas on the Tkinter window
        # canvas.get_tk_widget().place(x=650,y=300)

        def make_cals():

            if array_size > 0:

                for i in range(0, array_size, 1):

                    Xpairs.append(
                        [float(Xlen_cv[i]), float(abs_cal(x1_cv[i], x2_cv[i]))])

                    Ypairs.append(
                        [float(Ylen_cv[i]), float(abs_cal(y1_cv[i], y2_cv[i]))])

                    cor_list.append([round(x1_cv[i]), round(
                        y1_cv[i]), round(x2_cv[i]), round(y2_cv[i])])
                    x_len_per_pix.append(
                        float(Xpairs[i][0])/float(Xpairs[i][1]))
                    y_len_per_pix.append(
                        float(Ypairs[i][0])/float(Ypairs[i][1]))
                    # print(
                    area_xy.append(float(Xpairs[i][1])*float(Xpairs[i][0]))
                    vol_um.append(float((area_xy[i])*int(t_um)))
                    vol_uL.append(float(vol_um[i]/1000000000))

                    if (int(x1_cv[i])) < 0:
                        x_dir.append("left")
                        x_cv_diff.append((abs(x1_cv[i])*x_len_per_pix[i])/1000)

                        # total_travel_x.append(x_cv_diff[i]-x_mid_diff[i])

                    if(int(x1_cv[i])) > 0:
                        x_dir.append("right")
                        x_cv_diff.append((abs(x1_cv[i])*x_len_per_pix[i])/1000)
                        # total_travel_x.append(x_cv_diff[i]+x_mid_diff[i])

                    if (int(y1_cv[i])) < 0:
                        y_dir.append("down")
                        y_cv_diff.append((abs(y1_cv[i])*y_len_per_pix[i])/1000)

                    if int(y1_cv[i]) > 0:
                        y_dir.append("up")
                        y_cv_diff.append((abs(y1_cv[i])*y_len_per_pix[i])/1000)

                    if (int(x2_cv[i])) < 0:
                        x_2dir.append("left")
                        x2_cv_diff.append(
                            (abs(x2_cv[i])*x_len_per_pix[i])/1000)

                    if(int(x2_cv[i])) > 0:
                        x_2dir.append("right")
                        x2_cv_diff.append(
                            (abs(x2_cv[i])*x_len_per_pix[i])/1000)

                    if (int(y2_cv[i])) < 0:
                        y_2dir.append("down")
                        y2_cv_diff.append(
                            (abs(y2_cv[i])*y_len_per_pix[i])/1000)

                    if int(y2_cv[i]) > 0:
                        y_2dir.append("up")
                        y2_cv_diff.append(
                            (abs(y2_cv[i])*y_len_per_pix[i])/1000)

                    # x_mid_diff.append((x2_cv_diff[i]-x_cv_diff[i])/2)
                    # y_mid_diff.append((y2_cv_diff[i]-y_cv_diff[i])/2)

                    if x_dir[i] == "left":

                        travel_x.append((x_len_per_pix[i]*abs(x1_cv[i]))/1000)

                        # actual_x=travel_x[i]+x_mid_diff[i]
                        print(travel_x[i])

                    else:
                        travel_x.append((x_len_per_pix[i]*-abs(x1_cv[i]))/1000)
                        # actual_x=travel_x[i]+x_mid_diff[i]
                        print(travel_x[i])

                    if y_dir[i] == "up":
                        travel_y.append((x_len_per_pix[i]*-abs(y1_cv[i]))/1000)
                        # actual_y=travel_y[i]+y_mid_diff[i]
                        print(travel_y[i])
                    else:
                        travel_y.append((y_len_per_pix[i]*abs(y1_cv[i]))/1000)
                        # actual_y=travel_y[i]+y_mid_diff[i]
                        print(travel_y[i])

                    bed_sele.create_rectangle(
                        x1_cv[i], -y1_cv[i], x2_cv[i], -y2_cv[i], fill="grey70")

                # print(x_len_per_pix)
                # print(y_len_per_pix)

                # # cor_list=np.concatenate(cor_list)
                # # print(x_dir)
                # print(x_cv_diff)
                # # print(y_dir)
                # print(y_cv_diff)
                # # print(x_2dir)
                # print(x2_cv_diff)
                # # print(y_2dir)
                # print(y2_cv_diff)
                # # print(y_mid_diff)
                # # print(x_mid_diff)

                # print(Xlen_cv)
                print(travel_x)

                print(travel_y)
                print("volumes uL:")
                print(vol_uL)

                # X = np.linspace(-Xlen_cv[i]/2,Xlen_cv[i]/2,50)

                # Y = np.linspace(-Ylen_cv[i]/2,Ylen_cv[i]/2,50)

                # X, Y = np.meshgrid(X,Y)

                # X_mean = 0; Y_mean = 0

                # X_var = 5; Y_var = 8

                # pos = np.empty(X.shape+(2,))

                # pos[:,:,0]=X

                # pos[:,:,1]=Y

                # rv = multivariate_normal([X_mean, Y_mean],[[X_var, 0], [0, Y_var]])

                # ax = fig.add_subplot(211, projection='3d')

                # ax[i].plot_surface(X, Y, rv.pdf(pos), cmap="plasma")

                # # creating the Tkinter canvas
                # # containing the Matplotlib figure

                # canvas.draw()

            else:
                console_win.insert(0, "No co-ordinates!")

        def OptionCallBack(*args):
            global slected, selected_cor_index
            print(self.cor_var.get())
            selected_cor_index = so.current()
            # try:
            #     bed_sele.delete(slected)
            # except:
            try:
                if slected == None:
                    slected = bed_sele.create_rectangle(x1_cv[so.current(
                    )], -y1_cv[so.current()], x2_cv[so.current()], -y2_cv[so.current()], fill="green")
                else:
                    bed_sele.delete(slected)
                    slected = bed_sele.create_rectangle(x1_cv[so.current(
                    )], -y1_cv[so.current()], x2_cv[so.current()], -y2_cv[so.current()], fill="green")

            except:

                slected = bed_sele.create_rectangle(x1_cv[so.current(
                )], -y1_cv[so.current()], x2_cv[so.current()], -y2_cv[so.current()], fill="green")

                pass

        make_cals()
        self.cor_var = tk.StringVar(autowin)
        self.cor_var.set("Select a command ")  # default value
        self.cor_var.trace('w', OptionCallBack)
        # def cor_current_unti(cor):

        #     next_pos_x=current_pos_x+x_mid_diff[cor]+x_cv_diff[i]

        #     # next_pos_x=round(float(current_pos_x)-step_size*5,2)
        #     self.update_x_or_y("X",next_pos_x)
        #     EX=lambda e="G1 X"+str(next_pos_x)+"\r\n":self.serial_start_kin(e)
        #     EX()
        so = ttk.Combobox(autowin, textvariable=self.cor_var)
        so.config(values=('Tracing Upstream', 'Tracing Downstream', 'Find Path'))
        so.place(x=250, y=40)
        so['values'] = (cor_list)
        # def cor_selector(selected_cor):

        x_shift = 100
        y_shift = 101302

        def updateval(*args):
            global x_shift, y_shift
            x_shift = int(self.x_camera_shift.get())
            y_shift = int(self.y_camera_shift.get())
            pass
        self.x_shift_var = tk.StringVar()
        self.y_shift_var = tk.StringVar()
        self.x_camera_shift = tk.Entry(autowin, font=40, width=40)
        x_camera_shift_val = (self.window.register(self.validate),
                              '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.x_camera_shift = tk.Entry(autowin, width=8, textvariable=self.x_shift_var, font=(
            'Georgia 20'), validate='key', validatecommand=x_camera_shift_val)
        self.x_camera_shift.insert(tk.END, x_shift)
        self.x_camera_shift_lbl = automode_bg.create_text(
            50, 620, text="X camera um:", fill="black", font=('Helvetica 22 bold'), anchor=tk.NW)
        self.x_camera_shift.place(x=100, y=660)
        self.x_shift_var.trace("w", updateval)

        self.y_camera_shift = tk.Entry(autowin, font=40, width=40)
        y_camera_shift_val = (self.window.register(self.validate),
                              '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.y_camera_shift = tk.Entry(autowin, width=8, textvariable=self.y_shift_var, font=(
            'Georgia 20'), validate='key', validatecommand=y_camera_shift_val)
        self.y_camera_shift.insert(tk.END, y_shift)

        self.y_camera_shift_lbl = automode_bg.create_text(
            350, 620, text="Y camera um:", fill="black", font=('Helvetica 22 bold'), anchor=tk.NW)
        self.y_camera_shift.place(x=400, y=660)
        self.y_shift_var.trace("w", updateval)

        #     # Function to print the index of selected option in Combobox

        #     selected_cor = self.cor_var.get()
        #     print(selected_cor[0])

        #     index=int(np.argwhere(cor_list==selected_cor))
        #     print(index)
        # c_drop = tk.OptionMenu(autowin, self.cor_var, *cor_list,command=cor_selector)
        # c_drop.config(width=30)
        # c_drop.place(x=250,y=40)

        def auto_calc(cordinate):
            global selected_cor_index, pos_dring_cap_x, pos_dring_cap_y
            # for ar in range(0,array_size,1) :

            #     next_pos_x=round(float(current_pos_x)+x_shift+travel_x[ar],2)
            #     next_pos_y=round(float(current_pos_x)+y_shift+travel_y[ar],2)

            #     self.update_x_or_y("X",next_pos_x)
            #     self.update_x_or_y("Y",next_pos_y)
            #     print("G1 X"+str(next_pos_x)+" Y"+str(next_pos_y)+"\r\n")
            #     # EX=lambda e="G1 X"+str(next_pos_x)+" Y"+str(next_pos_y)+"\r\n":self.serial_start_kin(e)
            #     # EX()

            auto_pos_x = round(float(
                x_cords[selected_cor_index])+(x_shift/1000)-travel_x[selected_cor_index], 2)
            auto_pos_y = round(float(
                y_cords[selected_cor_index])+(y_shift/1000)+travel_y[selected_cor_index], 2)

            # self.update_x_or_y("X",next_pos_x)
            # self.update_x_or_y("Y",next_pos_y)
            print("G1 X"+str(auto_pos_x)+" Y"+str(auto_pos_y)+"\r\n")
            EX=lambda e="G1 X"+str(next_pos_x)+" Y"+str(next_pos_y)+"\r\n":self.serial_start_kin(e)
            EX()

        exe_but = tk.Button(autowin, text="Execute",
                            command=lambda e="": auto_calc(e))
        exe_but.place(x=300, y=80)
        autowin.update()

    def camrul_f(self):
        # sp = subprocess.Popen(['python', '-c', 'camrul_old.py'], stdout=subprocess.PIPE)
        # return sp.stdout.readlines()
        global consol_cam, process_cam, poll

    # def camrul_f(self):

    #     # somescript_arg1="send"
    #     # # url = 'http://www.whatever.com'
    #     # # cmd = 'ffplay -vn -nodisp -bufsize 4096 '.split()
    #     # # subprocess.call(cmd + [str(url)], shell=False)
    #     # # subprocess.call(['python', 'camrul.py'],shell=True)
        process_cam = subprocess.Popen([sys.executable, 'camrul_launcher.py'])

        # process_cam = subprocess.Popen([sys.executable, 'camrul_old.py'], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)

    #      # execfile('camrul_old.py')
    #     print("launching")

  # pass

    def update(self):

        global srl_com_kin_lbl, srl_com_ink_lbl, console_win

        def collect():  # Stores Data File Name With User Input
            global xcord, ycord
            # + time.strftime('-%H-%M-%S', time.localtime())
            with open(txtName + '.csv', 'a') as data:

                ##### THIS IS MY ATTEMPT AT A 10 second loop #######
                # for everysecond in range(60):
                #   if everysecond % 10 is 0:
                output = csv.writer(data)
                rows = [time.strftime(
                    '%H:%M:%S', time.localtime()), xcord, ycord]
                # ,x1c,y1c,x2c,y2c
                output.writerow(rows)
            # I Think this is where the code for the 10 second loop should go, For
            # some reason i cant get it to take data with respect to computer time.

        collect()
        try:

            poll = process_cam.poll()
            if poll is None:
                # p.subprocess is alive
                cam_started = True
            else:
                pass
            if cam_started == True and poll != None:
                self.auto_mode()
            for line in process_cam.stdout:
                print(line)  # , end='') # process line here

                console_win.insert(0, line)

        #    # Read the csv file with first row skipped
        #     df = pd.read_csv("Distances_temp.csv")

        #     df.head()
        #     array_size=len(df)
        #     print(array_size)
        #     time_cv=df["Time"]

        #     Xlen_cv=df["X Length"]

        #     Ylen_cv=df["Y Length"]

        #     x1_cv=df["x1"]

        #     x2_cv=df["x2"]

        #     y1_cv=df["y1"]

        #     y2_cv=df["y2"]
        #     for i in range(0,array_size,1):

        #         print("Y2:"+str(y2_cv[i]))

            # consol_cam=process_cam.stdout.readlines()
            # print(consol_cam)

        except:
            pass
        serial_txt_x = 620
        serial_txt_y = 670
        srl_com_kin_lbl1 = tk.Label(
            self.window, text="Serial Communication 3D Not Connected!", font=('calbiri', 10))
        srl_com_kin_lbl = tk.Label(
            self.window, text="Serial Communication  3D Connected!", font=('calbiri', 10))

        if serial_kin_stat == True:
            try:
                srl_com_kin_lbl1.place_forget()
                self.window.update()
            except:
                pass
            srl_com_kin_lbl.place(x=serial_txt_x, y=serial_txt_y)
            srl_com_kin_lbl.configure(background='green')

            x_pos_lbl = tk.Label(self.window, text="X:{}..Y:{}..Z:{}..".format(
                current_pos_x, current_pos_y, current_pos_z), font=('calbiri', 10))
            x_pos_lbl.configure(background='orange')
            x_pos_lbl.place(x=serial_txt_x, y=serial_txt_y-200)

            self.window.update()
        else:
            try:
                srl_com_kin_lbl.place_forget()
                self.window.update()
            except:
                pass
            srl_com_kin_lbl1.place(x=serial_txt_x, y=serial_txt_y)
            srl_com_kin_lbl1.configure(background='orange')
            self.window.update()

        self.window.after(self.delay, self.update)
        pass

        #print("unable to get feed")


root = tk.Tk()
sp = SplashScreen(root)


# Create a window and pass it to the Application object
App(tk.Toplevel(), "μ-structure 3D Control Panel")
App(tk.Toplevel(), "μ-structure 3D Control Panel")
