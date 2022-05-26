# This code is based on Adafruit's PyPortal User Interface code https://learn.adafruit.com/making-a-pyportal-user-interface-displayio/the-full-code
# SPDX-FileCopyrightText: 2020 Richard Albritton for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import sys
import board
import microcontroller
import displayio
import busio
from analogio import AnalogIn
import neopixel
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_button import Button
import adafruit_touchscreen
from adafruit_pyportal import PyPortal
import adafruit_lidarlite
import adafruit_ltr390
import adafruit_gps
import adafruit_ds3231
from TEA5767 import Radio

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
sys.path.append(cwd)

# ------------- Inputs and Outputs Setup ------------- #
i2c_bus = busio.I2C(board.SCL, board.SDA)
ltr = adafruit_ltr390.LTR390(i2c_bus, address=0x53)
gps = adafruit_gps.GPS_GtopI2C(i2c_bus, address=0x10)
rtc = adafruit_ds3231.DS3231(i2c_bus)
radio = Radio(i2c_bus, addr=0x60, freq=94.5, band="US", stereo=True, soft_mute=True, noise_cancel=True, high_cut=True)
radio.standby(True) # This turns off the radio to save power. You can turn the radio on with the ON button on View4

#RTC Clock
# Lookup table for names of days (nicer printing).
days = ("Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun")

if False:  # change to True if you want to set the time!
    # year, mon, date, hour, min, sec, wday, yday, isdst
    # t = time.struct_time((2022, 5, 22, 15, 47, 00, 6, -1, -1))
    # you must set year, mon, date, hour, min, sec and weekday
    rtc.datetime = t
    print()

#GPS 
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")# Turn on just minimum info (RMC only, location):
gps.send_command(b"PMTK220,20000") # Set update rate to once a second (1hz) which is what you typically want.
timestamp = time.monotonic() # Main loop runs forever printing data as it comes in

# Neopixels
pixel_pin = board.D3
num_pixels = 1
ORDER = neopixel.RGB

pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=1.0, auto_write=True, pixel_order=ORDER
)

# ---------- Sound Effects ------------- #
soundDemo = '/sounds/sound.wav'
soundBeep = '/sounds/beep.wav'
soundTab = '/sounds/tab.wav'

# ------------- Other Helper Functions------------- #
# Helper for cycling through a number set of 1 to x.
def numberUP(num, max_val):
    num += 1
    if num <= max_val:
        return num
    else:
        return 1

# ------------- Screen Setup ------------- #
pyportal = PyPortal()
display = board.DISPLAY
display.rotation = 0

# Backlight function: Value between 0 and 1 where 0 is OFF, 0.5 is 50% and 1 is 100% brightness.
def set_backlight(val):
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val
set_backlight(0.5)

# Touchscreen setup
# ------Rotate 0:
screen_width = 320
screen_height = 240
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(320, 240))


# ------------- Display Groups ------------- #
splash = displayio.Group()  # The Main Display Group
view1 = displayio.Group()  # Group for View 1 objects
view2 = displayio.Group()  # Group for View 2 objects
view3 = displayio.Group()  # Group for View 3 objects
view4 = displayio.Group()  # Group for View 4 objects

def hideLayer(hide_target):
    try:
        splash.remove(hide_target)
    except ValueError:
        pass

def showLayer(show_target):
    try:
        time.sleep(0.1)
        splash.append(show_target)
    except ValueError:
        pass

# ------------- Setup for Images ------------- #

# Display an image until the loop starts
pyportal.set_background('/images/loading.bmp')

bg_group = displayio.Group()
splash.append(bg_group)

icon_group = displayio.Group()
icon_group.x = 0
icon_group.y = 40
icon_group.scale = 1
view4.append(icon_group)

# This will handel switching Images and Icons
def set_image(group, filename):
    """Set the image file for a given goup for display.
    This is most useful for Icons or image slideshows.
        :param group: The chosen group
        :param filename: The filename of the chosen image
    """
    print("Set image to ", filename)
    if group:
        group.pop()

    if not filename:
        return  # we're done, no icon desired

    image_file = open(filename, "rb")
    image = displayio.OnDiskBitmap(image_file)
    try:
        image_sprite = displayio.TileGrid(image, pixel_shader=displayio.ColorConverter())
    except TypeError:
        image_sprite = displayio.TileGrid(image, pixel_shader=displayio.ColorConverter(),
                                          position=(0, 0))
    group.append(image_sprite)

set_image(bg_group, "/images/BGimage.bmp")

# ---------- Text Boxes ------------- #
# Set the font and preload letters
font = bitmap_font.load_font("/fonts/StarFleet-24.bdf")
font1 = bitmap_font.load_font("/fonts/Greek-Regular-19.bdf")
font2 = bitmap_font.load_font("/fonts/BebasNeue-Regular-25.bdf")
font3 = bitmap_font.load_font("/fonts/TrekClassic-25.bdf")
font4 = bitmap_font.load_font("/fonts/TrekClassic-31.bdf")
font.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()')

# Default Label styling:
TABS_X = 5
TABS_Y = 50

# Text Label Objects 
sensors_label1 = Label(font2, text="", color=0x03AD31)
sensors_label1.x = TABS_X+100
sensors_label1.y = TABS_Y
view1.append(sensors_label1)

sensor_data1 = Label(font2, text="", color=0x03AD31)
sensor_data1.x = TABS_X+15
sensor_data1.y = 70
view1.append(sensor_data1)

sensors_label2 = Label(font4, text="", color=0x03AD31)
sensors_label2.x = TABS_X+100
sensors_label2.y = TABS_Y
view2.append(sensors_label2)

sensor_data2 = Label(font4, text="", color=0x03AD31)
sensor_data2.x = TABS_X+15
sensor_data2.y = 70
view2.append(sensor_data2)

sensors_label = Label(font4, text="Data View", color=0x03AD31)
sensors_label.x = TABS_X+20
sensors_label.y = TABS_Y
view3.append(sensors_label)

sensor_data = Label(font4, text="Data View", color=0x03AD31)
sensor_data.x = TABS_X+15
sensor_data.y = 65
view3.append(sensor_data)

feed4_label = Label(font1, text="", color=0xFFFFFF)
feed4_label.x = TABS_X+30
feed4_label.y = TABS_Y
view4.append(feed4_label)

text_hight = Label(font, text="M", color=0x03AD31)

# return a reformatted string with word wrapping using PyPortal.wrap_nicely
def text_box(target, top, string, max_chars):
    text = pyportal.wrap_nicely(string, max_chars)
    new_text = ""
    test = ""
    for w in text:
        new_text += '\n'+w
        test += 'M\n'
    text_hight.text = test  # Odd things happen without this
    glyph_box = text_hight.bounding_box
    target.text = ""  # Odd things happen without this
    target.y = int(glyph_box[3]/2)+top
    target.text = new_text

# ---------- Display Buttons ------------- #
# Default button styling:
BUTTON_HEIGHT = 40
BUTTON_WIDTH = 50

# We want four buttons across the top of the screen
TAPS_HEIGHT = 40
TAPS_WIDTH = int(screen_width/4)
TAPS_Y = 0

# We want two big buttons at the bottom of the screen
BIG_BUTTON_HEIGHT = int(screen_height/3.2)
BIG_BUTTON_WIDTH = int(screen_width/2)
BIG_BUTTON_Y = int(screen_height-BIG_BUTTON_HEIGHT)

# This group will make it easy for us to read a button press later.
buttons = []

# Main User Interface Buttons
button_view1 = Button(x=0, y=0,
                      width=TAPS_WIDTH, height=TAPS_HEIGHT,
                      label="LOC", label_font=font4, label_color=0xff7e00,
                      fill_color=0x5c5b5c, outline_color=0x767676,
                      selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                      selected_label=0x525252)
pixels.fill((0, 255, 0))
buttons.append(button_view1)  # adding this button to the buttons group

button_view2 = Button(x=TAPS_WIDTH, y=0,
                      width=TAPS_WIDTH, height=TAPS_HEIGHT,
                      label="TARGET", label_font=font4, label_color=0xff7e00,
                      fill_color=0x5c5b5c, outline_color=0x767676,
                      selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                      selected_label=0x525252)
buttons.append(button_view2)  # adding this button to the buttons group

button_view3 = Button(x=TAPS_WIDTH*2, y=0,
                      width=TAPS_WIDTH, height=TAPS_HEIGHT,
                      label="λ", label_font=font4, label_color=0xff7e00,
                      fill_color=0x5c5b5c, outline_color=0x767676,
                      selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                      selected_label=0x525252)
buttons.append(button_view3)  # adding this button to the buttons group

button_view4 = Button(x=TAPS_WIDTH*3, y=0,
                      width=TAPS_WIDTH, height=TAPS_HEIGHT,
                      label="FM", label_font=font4, label_color=0xff7e00,
                      fill_color=0x5c5b5c, outline_color=0x767676,
                      selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                      selected_label=0x525252)
buttons.append(button_view4)  # adding this button to the buttons group

# Add all of the main buttons to the splash Group
for b in buttons:
    splash.append(b)

# Make a button to turn on radio in view4
button_play = Button(x=25, y=60,
                     width=BUTTON_WIDTH, height=BUTTON_HEIGHT -10,
                     label="ON", label_font=font, label_color=0xffffff,
                     fill_color=0x0A9800, outline_color=0xbc55fd,
                     selected_fill=0x11FF00, selected_outline=0xff6600,
                     selected_label=0x525252, style=Button.ROUNDRECT)
buttons.append(button_play)  # adding this button to the buttons group
view4.append(button_play)

# Make a button to turn off radio in view4
button_pause = Button(x=120, y=60,
                      width=BUTTON_WIDTH, height=BUTTON_HEIGHT-10,
                      label="OFF", label_font=font, label_color=0xffffff,
                      fill_color=0xFF0000, outline_color=0xbc55fd,
                      selected_fill=0x5a5a5a, selected_outline=0xff6600,
                      selected_label=0x525252, style=Button.ROUNDRECT)
buttons.append(button_pause)  # adding this button to the buttons group
view4.append(button_pause)

# Make a button to increase 1mHz view4
button_increase_big = Button(x=25, y=110,
                      width=BUTTON_WIDTH+30, height=BUTTON_HEIGHT-10,
                      label="UP 1", label_font=font, label_color=0xffffff,
                      fill_color=0x8900ff, outline_color=0xbc55fd,
                      selected_fill=0x5a5a5a, selected_outline=0xff6600,
                      selected_label=0x525252, style=Button.ROUNDRECT)
buttons.append(button_increase_big)  # adding this button to the buttons group
view4.append(button_increase_big)

# Make a button to decrease 1mHz view4
button_decrease_big = Button(x=25, y=160,
                      width=BUTTON_WIDTH+30, height=BUTTON_HEIGHT-10,
                      label="DOWN 1", label_font=font, label_color=0xffffff,
                      fill_color=0xB000FF, outline_color=0xbc55fd,
                      selected_fill=0x5a5a5a, selected_outline=0xff6600,
                      selected_label=0x525252, style=Button.ROUNDRECT)
buttons.append(button_decrease_big)  # adding this button to the buttons group
view4.append(button_decrease_big)

# Make a button to increase 0.1mHz in view4
button_increase_small = Button(x=130, y=110,
                      width=BUTTON_WIDTH+40, height=BUTTON_HEIGHT-10,
                      label="UP 0.1", label_font=font, label_color=0xffffff,
                      fill_color=0x8900ff, outline_color=0xbc55fd,
                      selected_fill=0x5a5a5a, selected_outline=0xff6600,
                      selected_label=0x525252, style=Button.ROUNDRECT)
buttons.append(button_increase_small)  # adding this button to the buttons group
view4.append(button_increase_small)

# Make a button to decrease 0.1mHz in view4
button_decrease_small = Button(x=130, y=160,
                      width=BUTTON_WIDTH+40, height=BUTTON_HEIGHT-10,
                      label="DOWN 0.1", label_font=font, label_color=0xffffff,
                      fill_color=0xB000FF, outline_color=0xbc55fd,
                      selected_fill=0x5a5a5a, selected_outline=0xff6600,
                      selected_label=0x525252, style=Button.ROUNDRECT)
buttons.append(button_decrease_small)  # adding this button to the buttons group
view4.append(button_decrease_small)

#pylint: disable=global-statement - this is how screens are hidden and shown in each screen.
def switch_view(what_view):
    global view_live
    if what_view == 1:
        hideLayer(view2)
        hideLayer(view3)
        hideLayer(view4)
        button_view1.selected = False
        button_view2.selected = True
        button_view3.selected = True
        button_view4.selected = True
        showLayer(view1)
        view_live = 1
        print("View1 On")
    elif what_view == 2:
        # global icon
        hideLayer(view1)
        hideLayer(view3)
        hideLayer(view4)
        button_view1.selected = True
        button_view2.selected = False
        button_view3.selected = True
        button_view4.selected = True
        showLayer(view2)
        view_live = 2
        print("View2 On")
    else:
        hideLayer(view1)
        hideLayer(view2)
        hideLayer(view4)
        button_view1.selected = True
        button_view2.selected = True
        button_view3.selected = False
        button_view4.selected = True
        showLayer(view3)
        view_live = 3
        print("View3 On")
    if what_view == 4:
        hideLayer(view1)
        hideLayer(view2)
        hideLayer(view3)
        button_view1.selected = True
        button_view2.selected = True
        button_view3.selected = True
        button_view4.selected = False
        showLayer(view4)
        view_live = 4
        print("View4 On")
#pylint: enable=global-statement

# Set veriables and startup states
button_view1.selected = False
button_view2.selected = True
button_view3.selected = True
button_view4.selected = True
showLayer(view1)
hideLayer(view2)
hideLayer(view3)
hideLayer(view4)

view_live = 1
icon = 1
icon_name = "Ruby"
button_mode = 1
switch_state = 0


#text_box(feed2_label, TABS_Y, '', 18)

text_box(sensors_label, TABS_Y-20,
         "", 28)

board.DISPLAY.show(splash)

# ------------- Code Loop ------------- #
while True:
    touch = ts.touch_point
    data = gps.read(32)
    t = rtc.datetime
    sensor = adafruit_lidarlite.LIDARLite(i2c_bus)

    if data is not None:
        # convert bytearray to string
        data_string = "".join([chr(b) for b in data])
        print(data_string, end="")
# '\n' is your Y axis (Enter button) and the spaces are used for the X axis.
    sensor_data.text = 'UV INDEX\n{}\n                   UV LUX\n                   {}'.format(ltr.uvi, ltr.lux)
    sensor_data1.text = '{} {}/{}/{}  {}:{:02}:{:02}\nGlobal Position\n{}'.format(days[int(t.tm_wday)], t.tm_mon, t.tm_mday, t.tm_year,t.tm_hour, t.tm_min, t.tm_sec,("\n".join(pyportal.wrap_nicely(str(data, "utf8"), 20))))
    sensor_data2.text = 'OBJ DISTANCE\n\n                   {}m'.format(sensor.distance/100)


    # ------------- Handle Button Press Detection  ------------- #
    if touch:  # Only do this if the screen is touched
        # loop with buttons using enumerate() to number each button group as i
        for i, b in enumerate(buttons):
            if b.contains(touch):  # Test each button to see if it was pressed
                print('button%d pressed' % i)
                if i == 0 and view_live != 1:  # only if view1 is visable
                    pyportal.play_file(soundTab)
                    switch_view(1)
                    pixels.fill((0, 255, 0))
                    while ts.touch_point:
                        pass
                if i == 1 and view_live != 2:  # only if view2 is visable
                    pyportal.play_file(soundTab)
                    switch_view(2)
                    pixels.fill((255, 0, 0))
                    while ts.touch_point:
                        pass
                if i == 2 and view_live != 3:  # only if view3 is visable
                    pyportal.play_file(soundTab)
                    switch_view(3)
                    pixels.fill((0, 0, 255))
                    while ts.touch_point:
                        pass
                if i == 3 and view_live != 4:  # only if view4 is visable
                    pyportal.play_file(soundTab)
                    switch_view(4)
                    pixels.fill((0, 255, 255))
                    while ts.touch_point:
                        pass
                if i == 4:  # only if view4 is visable
                    pyportal.play_file(soundBeep)
                    radio.standby(False) # turns ON the radio
                    b.selected = True
                    while ts.touch_point:
                        pass
                    print("Icon Button Pressed")
                    b.selected = False
                    text_box(feed4_label, TABS_Y,
                             "".format(button_play), 18)
                if i == 5:  # only if view4 is visable
                    pyportal.play_file(soundBeep)
                    radio.standby(True) # turns OFF the radio
                    b.selected = True
                    while ts.touch_point:
                        pass
                    print("Icon Button Pressed")
                    b.selected = False
                    text_box(feed4_label, TABS_Y,
                             "".format(button_pause), 18)
                if i == 6:  # only if view4 is visable
                    pyportal.play_file(soundBeep)
                    radio.change_freqency(1.0)  # increase 1.0 MHz
                    b.selected = True
                    while ts.touch_point:
                        pass
                    print("Icon Button Pressed")
                    b.selected = False
                    text_box(feed4_label, TABS_Y,
                             "".format(button_increase_big), 18)
                if i == 7:  # only if view4 is visable
                    pyportal.play_file(soundBeep)
                    radio.change_freqency(-1.0)  # decrease 1.0 MHz
                    b.selected = True
                    while ts.touch_point:
                        pass
                    print("Icon Button Pressed")
                    b.selected = False
                    text_box(feed4_label, TABS_Y,
                             "".format(button_decrease_big), 18)
                if i == 8:  # only if view4 is visable
                    pyportal.play_file(soundBeep)
                    radio.change_freqency(0.1)  # increase 0.1 MHz
                    b.selected = True
                    while ts.touch_point:
                        pass
                    print("Icon Button Pressed")
                    b.selected = False
                    text_box(feed4_label, TABS_Y,
                             "".format(button_increase_big), 18)
                if i == 9:  # only if view4 is visable
                    pyportal.play_file(soundBeep)
                    radio.change_freqency(-0.1)  # decrease 0.1 MHz
                    b.selected = True
                    while ts.touch_point:
                        pass
                    print("Icon Button Pressed")
                    b.selected = False
                    text_box(feed4_label, TABS_Y,
                             "".format(button_decrease_big), 18)