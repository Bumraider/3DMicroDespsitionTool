# -*- coding: utf-8 -*-
"""
Created on Fri Apr 22 12:34:06 2022

@author: Admin
"""


# -------------------------------
# imports
# -------------------------------

# builtins
import os
import sys
import time
import traceback
from math import hypot
import pandas as pd
# must be installed using pip
# python3 -m pip install opencv-python
import numpy as np
import cv2
import tkinter as tk
# local clayton libs
import frame_capture
import frame_draw
import sched
# Importing required modules
import csv
from datetime import datetime
txtName = "Distances_temp"
# -------------------------------
# File data
# -------------------------------
start_timer = False
collectnow = False

xcords = []
ycords = []
# Read the csv file with first row skipped
# def find_cordsnow():
#     global x_cords,y_cords,array_size
#     df = pd.read_csv("Cords_temp.csv")
#     df.head()
#     array_size=len(df)
#     xcords=df["xcord"]
#     ycords=df["ycord"]

# find_cordsnow()
global x1c, y1c, x2c, y2c, xlen, ylen


def start():  # Stores Data Initial Columns
    # + time.strftime('-%H-%M-%S', time.localtime()) +
    with open(txtName + '.csv', 'w', newline='') as data:
        output = csv.writer(data)
        row = ['Time', 'X Length', 'Y Length', 'x1',
               'y1', 'x2', 'y2', 'xcord', 'ycord']
        output.writerow(row)


def collect(xlen, ylen, x1, y1, x2, y2, xcord, ycord):  # Stores Data File Name With User Input

    # + time.strftime('-%H-%M-%S', time.localtime())
    with open(txtName + '.csv', 'a', newline='') as data:

        ##### THIS IS MY ATTEMPT AT A 10 second loop #######
        # for everysecond in range(60):
        #   if everysecond % 10 is 0:
        output = csv.writer(data)

        rows = [time.strftime('%H:%M:%S', time.localtime(
        )), xlen, ylen, x1, y1, x2, y2, xcord[len(xcord)-1], ycord[len(ycord)-1]]
        # ,xcord[array_size],ycord[array_size]]
        # ,x1c,y1c,x2c,y2c
        print(rows)
        output.writerow(rows)
    # I Think this is where the code for the 10 second loop should go, For
    # some reason i cant get it to take data with respect to computer time.


# -------------------------------
# camera
# -------------------------------

# get camera id from argv[1]
# example "python3 camruler.py 2"
camera_id = 0
if len(sys.argv) > 1:
    camera_id = sys.argv[1]
    if camera_id.isdigit():
        camera_id = int(camera_id)

# camera thread setup
camera = frame_capture.Camera_Thread()
camera.camera_source = camera_id  # SET THE CORRECT CAMERA NUMBER
# camera.camera_width,camera.camera_height =  640, 480
# camera.camera_width,camera.camera_height = 1280, 720
# camera.camera_width,camera.camera_height = 1280,1024
# camera.camera_width,camera.camera_height = 1920,1080
camera.camera_frame_rate = 30
# camera.camera_fourcc = cv2.VideoWriter_fourcc(*"YUYV")
camera.camera_fourcc = cv2.VideoWriter_fourcc(*"MJPG")

# start camera thread
camera.start()

# initial camera values (shortcuts for below)
width = camera.camera_width
height = camera.camera_height
area = width*height
cx = int(width/2)
cy = int(height/2)
dm = hypot(cx, cy)  # max pixel distance
frate = camera.camera_frame_rate
print('CAMERA:', [camera.camera_source, width, height, area, frate])

# -------------------------------
# frame drawing/text module
# -------------------------------

draw = frame_draw.DRAW()
draw.width = width
draw.height = height

# -------------------------------
# conversion (pixels to measure)
# -------------------------------

# distance units designator
unit_suffix = 'um'

# calibrate every N pixels
pixel_base = 10
# maximum field of view from center to farthest edge
# should be measured in unit_suffix  in um
cal_range = 9500
# initial calibration values table {pixels:scale}
# this is based on the frame size and the cal_range
cal = dict([(x, cal_range/dm) for x in range(0, int(dm)+1, pixel_base)])

# calibration loop values
# inside of main loop below
cal_base = 1000
cal_last = None

# calibration update


def cal_update(x, y, unit_distance):

    # basics
    pixel_distance = hypot(x, y)
    try:

        scale = abs(unit_distance/pixel_distance)
    except:
        pass
    target = baseround(abs(pixel_distance), pixel_base)

    # low-high values in distance
    low = target*scale - (cal_base/2)
    high = target*scale + (cal_base/2)

    # get low start point in pixels
    start = target
    if unit_distance <= cal_base:
        start = 0
    else:
        while start*scale > low:
            start -= pixel_base

    # get high stop point in pixels
    stop = target
    if unit_distance >= baseround(cal_range, pixel_base):
        high = max(cal.keys())
    else:
        while stop*scale < high:
            stop += pixel_base

    # set scale
    for x in range(start, stop+1, pixel_base):
        cal[x] = scale
        print(f'CAL: {x} {scale}')


# read local calibration data
calfile = 'camruler_cal.csv'
if os.path.isfile(calfile):
    with open(calfile) as f:
        for line in f:
            line = line.strip()
            if line and line[0] in ('d',):
                axis, pixels, scale = [_.strip() for _ in line.split(',', 2)]
                if axis == 'd':
                    # print(f'LOAD: {pixels} {scale}')
                    cal[int(pixels)] = float(scale)

# convert pixels to units


def conv(x, y):

    d = distance(0, 0, x, y)

    scale = cal[baseround(d, pixel_base)]

    return x*scale, y*scale

# round to a given base


def baseround(x, base=1):
    return int(base * round(float(x)/base))

# distance formula 2D


def distance(x1, y1, x2, y2):
    return hypot(x1-x2, y1-y2)

# -------------------------------
# define frames
# -------------------------------


# define display frame
framename = "uRuler"
cv2.namedWindow(framename, flags=cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)

# -------------------------------
# key events
# -------------------------------

key_last = 0
key_flags = {'config': False,  # c key
             'auto': False,   # a key
             'home': False,  # h key
             'thresh': False,  # t key
             'percent': False,  # p key
             'norms': False,  # n key
             'rotate': False,  # r key
             'lock': False,   #

             }


def key_flags_clear():

    global key_flags

    for key in list(key_flags.keys()):
        if key not in ('rotate',):
            key_flags[key] = False


def key_event(key):

    global key_last
    global key_flags
    global mouse_mark
    global cal_last
    global print_once

    # config mode
    if key == 99:
        if key_flags['config']:
            key_flags['config'] = False
        else:
            key_flags_clear()
            key_flags['config'] = True
            cal_last, mouse_mark = 0, None

    # normilization mode
    elif key == 110:
        if key_flags['norms']:
            key_flags['norms'] = False
        else:
            key_flags['thresh'] = False
            key_flags['percent'] = False
            key_flags['lock'] = False
            key_flags['norms'] = True
            mouse_mark = None

    # rotate
    elif key == 114:
        if key_flags['rotate']:
            key_flags['rotate'] = False
        else:
            key_flags['rotate'] = True

    # auto mode
    elif key == 97:
        if key_flags['auto']:
            key_flags['auto'] = False
        else:
            key_flags_clear()
            key_flags['auto'] = True
            mouse_mark = None
    # home mode
    elif key == 104:
        if key_flags['home']:
            key_flags['home'] = False
        else:
            key_flags_clear()
            key_flags['home'] = True
            mouse_mark = None

    # auto percent
    elif key == 112 and key_flags['auto']:
        key_flags['percent'] = not key_flags['percent']
        key_flags['thresh'] = False
        key_flags['lock'] = False

    # auto threshold
    elif key == 116 and key_flags['auto']:
        key_flags['thresh'] = not key_flags['thresh']
        key_flags['percent'] = False
        key_flags['lock'] = False

    # log
    print('key:', [key, chr(key)])
    key_last = key

# -------------------------------
# mouse events
# -------------------------------


# mouse events
mouse_raw = (0, 0)  # pixels from top left
mouse_now = (0, 0)  # pixels from center
mouse_mark = None  # last click (from center)

# auto measure mouse events
auto_percent = 0.2
auto_threshold = 127
auto_blur = 5

# normalization mouse events
norm_alpha = 0
norm_beta = 255

# mouse callback


def mouse_event(event, x, y, flags, parameters):

    # print(event,x,y,flags,parameters)

    # event =  0 = current location
    # event =  1 = left   down click
    # event =  2 = right  down click
    # event =  3 = middle down
    # event =  4 = left   up   click
    # event =  5 = right  up   click
    # event =  6 = middle up
    # event = 10 = middle scroll, flag negative|positive value = down|up

    # globals
    global x1c, y1c, x2c, y2c, xlen, ylen
    global mouse_raw
    global mouse_now
    global mouse_mark
    global key_last
    global auto_percent
    global auto_threshold
    global auto_blur
    global norm_alpha
    global norm_beta

    # update percent
    if key_flags['percent']:
        auto_percent = 5*(x/width)*(y/height)

    # update threshold
    elif key_flags['thresh']:
        auto_threshold = int(255*x/width)
        auto_blur = int(20*y/height) | 1  # insure it is odd and at least 1

    # update normalization
    elif key_flags['norms']:
        norm_alpha = int(64*x/width)
        norm_beta = min(255, int(128+(128*y/height)))

    # update mouse location
    mouse_raw = (x, y)

    # offset from center
    # invert y to standard quadrants
    ox = x - cx
    oy = (y-cy)*-1

    # update mouse location
    mouse_raw = (x, y)
    if not key_flags['lock']:
        mouse_now = (ox, oy)

    # left click event
    if event == 1:

        if key_flags['config']:
            key_flags['lock'] = False
            mouse_mark = (ox, oy)

        elif key_flags['auto']:
            key_flags['lock'] = False
            mouse_mark = (ox, oy)

        if key_flags['percent']:
            key_flags['percent'] = False
            mouse_mark = (ox, oy)

        elif key_flags['thresh']:
            key_flags['thresh'] = False
            mouse_mark = (ox, oy)

        elif key_flags['norms']:
            key_flags['norms'] = False
            mouse_mark = (ox, oy)

        elif not key_flags['lock']:
            if mouse_mark:
                key_flags['lock'] = True
                global print_once
                print_once = True
            else:
                mouse_mark = (ox, oy)
        else:
            key_flags['lock'] = False
            mouse_now = (ox, oy)
            mouse_mark = (ox, oy)

        key_last = 0

    # right click event
    elif event == 2:
        key_flags_clear()
        mouse_mark = None
        key_last = 0


# register mouse callback
cv2.setMouseCallback(framename, mouse_event)

# -------------------------------
# main loop
# -------------------------------
start()
# loop
while True:

    # get frame
    frame0 = camera.next(wait=1)
    if frame0 is None:
        time.sleep(0.1)
        continue

    # normalize
    cv2.normalize(frame0, frame0, norm_alpha, norm_beta, cv2.NORM_MINMAX)

    # rotate 180
    if key_flags['rotate']:
        frame0 = cv2.rotate(frame0, cv2.ROTATE_180)

    # start top-left text block
    text = []

    # camera text
    fps = camera.current_frame_rate
    text.append(f'CAMERA ID:{camera_id} WxH:{width}x{height} FPS:{fps}')

    # mouse text
    text.append('')
    if not mouse_mark:
        text.append(f'LAST CLICK: NONE')
    else:
        text.append(f'LAST CLICK: {mouse_mark} PIXELS')
    text.append(f'CURRENT XY: {mouse_now} PIXELS')

    # -------------------------------
    # normalize mode
    # -------------------------------
    if key_flags['norms']:

        # print
        text.append('')
        text.append(f'NORMILIZE')
        text.append(f'ALPHA (min): {norm_alpha}')
        text.append(f'BETA (max): {norm_beta}')

    # -------------------------------
    # config mode
    # -------------------------------
    if key_flags['config']:

        # quadrant crosshairs
        draw.crosshairs(frame0, 5, weight=2, color='red', invert=True)

        # crosshairs aligned (rotated) to maximum distance
        draw.line(frame0, cx, cy, cx+cx, cy+cy, weight=1, color='red')
        draw.line(frame0, cx, cy, cx+cy, cy-cx, weight=1, color='red')
        draw.line(frame0, cx, cy, -cx+cx, -cy+cy, weight=1, color='red')
        draw.line(frame0, cx, cy, cx-cy, cy+cx, weight=1, color='red')

        # mouse cursor lines (parallel to aligned crosshairs)
        mx, my = mouse_raw
        draw.line(frame0, mx, my, mx+dm, my +
                  (dm*(cy/cx)), weight=1, color='green')
        draw.line(frame0, mx, my, mx-dm, my -
                  (dm*(cy/cx)), weight=1, color='green')
        draw.line(frame0, mx, my, mx+dm, my +
                  (dm*(-cx/cy)), weight=1, color='green')
        draw.line(frame0, mx, my, mx-dm, my -
                  (dm*(-cx/cy)), weight=1, color='green')

        # config text data
        text.append('')
        text.append(f'CALIBRATE')

        # start cal
        if not cal_last:
            cal_last = cal_base
            caltext = f'CAL: Click on D = {cal_last}'

        # continue cal
        elif cal_last <= cal_range:
            if mouse_mark:
                cal_update(*mouse_mark, cal_last)
                cal_last += cal_base
            caltext = f'CAL: Click on D = {cal_last}'

        # done
        else:
            key_flags_clear()
            cal_last == None
            with open(calfile, 'w') as f:
                data = list(cal.items())
                data.sort()
                for key, value in data:
                    f.write(f'd,{key},{value}\n')
                f.close()
            caltext = f'CAL: Complete.'

        # add caltext
        draw.add_text(frame0, caltext, (cx)-20, (cy)+30, color='red')

        # clear mouse
        mouse_mark = None

    # -------------------------------
    # auto mode
    # -------------------------------
    elif key_flags['auto']:

        mouse_mark = None

        # auto text data
        text.append('')
        text.append(f'AUTO MODE')
        text.append(f'UNITS: {unit_suffix}')
        text.append(f'MIN: {auto_percent:.2f}')
        text.append(f'GAIN: {auto_threshold}')
        text.append(f'BLUR: {auto_blur}')

        # gray frame
        frame1 = cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY)

        # blur frame
        frame1 = cv2.GaussianBlur(frame1, (auto_blur, auto_blur), 0)

        # threshold frame n out of 255 (85 = 33%)
        frame1 = cv2.threshold(frame1, auto_threshold,
                               255, cv2.THRESH_BINARY)[1]

        # invert
        frame1 = ~frame1

        # find contours on thresholded image
        contours, nada = cv2.findContours(
            frame1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # small crosshairs (after getting frame1)
        draw.crosshairs(frame0, 5, weight=2, color='green')

        # loop over the contours
        for c in contours:

            # contour data (from top left)
            x1, y1, w, h = cv2.boundingRect(c)
            x2, y2 = x1+w, y1+h
            x3, y3 = x1+(w/2), y1+(h/2)

            # percent area
            percent = 100*w*h/area

            # if the contour is too small, ignore it
            if percent < auto_percent:
                continue

            # if the contour is too large, ignore it
            elif percent > 2:
                continue

            # convert to center, then distance
            x1c, y1c = conv(x1-(cx), y1-(cy))
            x2c, y2c = conv(x2-(cx), y2-(cy))
            xlen = abs(x1c-x2c)
            ylen = abs(y1c-y2c)
            alen = 0
            current_con = c
            if max(xlen, ylen) > 0 and min(xlen, ylen)/max(xlen, ylen) >= 0.95:
                alen = (xlen+ylen)/2
            carea = xlen*ylen

            # plot
            draw.rect(frame0, x1, y1, x2, y2, weight=1, color='yellow')

            # add dimensions
            draw.add_text(frame0, f'{xlen:.2f}', x1-((x1-x2)/2),
                          min(y1, y2)-8, center=True, color='red')
            draw.add_text(
                frame0, f'Area:{carea:.2f}', x3, y2+8, center=True, top=True, color='red')
            if alen:
                draw.add_text(
                    frame0, f'Avg: {alen:.2f}', x3, y2+34, center=True, top=True, color='green')
            if x1 < width-x2:
                draw.add_text(frame0, f'{ylen:.2f}', x2+4,
                              (y1+y2)/2, middle=True, color='red')
            else:
                draw.add_text(
                    frame0, f'{ylen:.2f}', x1-4, (y1+y2)/2, middle=True, right=True, color='red')

    # -------------------------------
    # home mode
    # -------------------------------
    elif key_flags['home']:

        # auto text data
        text.append('')
        text.append(f'HOME MODE')
        text.append(f'UNITS: {unit_suffix}')

    # -------------------------------
    # dimension mode
    # -------------------------------
    else:

        # small crosshairs
        draw.crosshairs(frame0, 5, weight=2, color='green')

        # mouse cursor lines
        draw.vline(frame0, mouse_raw[0], weight=1, color='green')
        draw.hline(frame0, mouse_raw[1], weight=1, color='green')

        # draw
        if mouse_mark:

            # locations
            x1, y1 = mouse_mark
            x2, y2 = mouse_now

            # convert to distance
            x1c, y1c = conv(x1, y1)
            x2c, y2c = conv(x2, y2)
            xlen = abs(x1c-x2c)
            ylen = abs(y1c-y2c)
            llen = hypot(xlen, ylen)
            alen = 0
            if max(xlen, ylen) > 0 and min(xlen, ylen)/max(xlen, ylen) >= 0.95:
                alen = ((xlen+ylen)/2)
            carea = xlen*ylen

            # print distances
            microxlen = xlen
            microylen = ylen
            microhypotlen = llen

            text.append('')
            text.append(f'X LEN: {microxlen:.2f}{unit_suffix}')
            text.append(f'Y LEN: {microylen:.2f}{unit_suffix}')
            text.append(f'L LEN: {microhypotlen:.2f}{unit_suffix}')

            # convert to plot locations
            x1 += cx
            x2 += cx
            y1 *= -1
            y2 *= -1
            y1 += cy
            y2 += cy
            x3 = x1+((x2-x1)/2)
            y3 = max(y1, y2)

            # line weight
            weight = 1
            if key_flags['lock']:
                global print_once
                weight = 2
                if print_once == True:
                    global x_cords, y_cords, array_size
                    df = pd.read_csv("Cords_temp.csv")
                    df.head()
                    array_size = len(df)
                    time_stamp = df["time"]
                    xcord = df["xcord"]
                    ycord = df["ycord"]

                    collect(
                        xlen, ylen, mouse_mark[0], mouse_mark[1], mouse_now[0], mouse_now[1], xcord, ycord)
                    print("TopLeft: (X:%s,Y:%s)" %
                          (mouse_mark[0], mouse_mark[1]))
                    print("Topright: (X:%s,Y:%s)" %
                          (mouse_now[0], mouse_now[1]))
                    print_once = False

                    # txt_3 = "Xlen:{xlen} co-ordinates!"
                    # print(txt_3.format(xlen))
                    # txt_4 = "Ylen:{ylen} co-ordinates!"
                    # print(txt_4.format(ylen))

            # plot
            microarea = carea
            draw.rect(frame0, x1, y1, x2, y2, weight=weight, color='red')
            draw.line(frame0, x1, y1, x2, y2, weight=weight, color='green')

            # add dimensions
            draw.add_text(frame0, f'{xlen:.2f}', x1-((x1-x2)/2),
                          min(y1, y2)-8, center=True, color='red')
            draw.add_text(
                frame0, f'Area: {microarea:.2f}', x3, y3+8, center=True, top=True, color='red')
            if alen:
                draw.add_text(
                    frame0, f'Avg: {alen:.2f}', x3, y3+34, center=True, top=True, color='green')
            if x2 <= x1:
                draw.add_text(frame0, f'{ylen:.2f}', x1+4,
                              (y1+y2)/2, middle=True, color='red')
                draw.add_text(frame0, f'{llen:.2f}',
                              x2-4, y2-4, right=True, color='green')
            else:
                draw.add_text(
                    frame0, f'{ylen:.2f}', x1-4, (y1+y2)/2, middle=True, right=True, color='red')
                draw.add_text(frame0, f'{llen:.2f}', x2+8, y2-4, color='green')

    # add usage key
    text.append('')
    text.append(f'Q = END VISION')
    text.append(f'R = ROTATE CAMERA')
    text.append(f'N = NORMALIZE')
    text.append(f'A = FEATURE DETECT')
    if key_flags['auto']:
        text.append(f'P = MIN')
        text.append(f'T = GAIN')
        text.append(f'T = BLUR')
    text.append(f'C = CALIBRATE')

    # draw top-left text block
    draw.add_text_top_left(frame0, text)

    # display
    cv2.imshow(framename, frame0)

    isWritten = cv2.imwrite("Result/Image.png", frame0)
    if isWritten:
        print('Image is successfully saved as file.')
    # key delay and action
    key = cv2.waitKey(1) & 0xFF

    # esc ==  27 == quit
    # q   == 113 == quit
    if key in (27, 113):
        break

    # key data
    # elif key != 255:
    elif key not in (-1, 255):
        key_event(key)

# -------------------------------
# kill sequence
# -------------------------------
cam_stat = False
# close camera thread
camera.stop()
cv2.destroyWindow(framename)
# close all windows
cv2.destroyAllWindows()

# done
# exit()

# -------------------------------
# end
# -------------------------------


class MyVideoCapture:
    def __init__(self, video_source=0):
        # Open the video source
        self.vid = cv2.VideoCapture(video_source)

        width = 640
        height = 480
        self.vid.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.vid.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", video_source)

        # Get video source width and height
        self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

    def get_frame(self):
        global cam_stat
        if cam_stat == False:
            if self.vid.isOpened():
                ret, frame = self.vid.read()
                if ret:
                    # Return a boolean success flag and the current frame converted to BGR
                    return (ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                else:
                    return (ret, None)
            else:

                return (ret, None)
          #  else:
        # if self.vid.isOpened():
            #    self.vid.release()

    # Release the video source when the object is destroyed

    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()
