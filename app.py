#!/usr/bin/env python

import sys, os
import inspect
import gi
import ctypes
import threading
import pigpio

gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GObject, Gtk, Gdk, GstVideo

gdkdll = ctypes.CDLL ("libgdk-3-0.dll")

ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]  

PAN = 18
TILT = 17
RPI_IP = "192.168.1.60"

pi = pigpio.pi(RPI_IP, 8900)

def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t


class Holo_Drone_Main:
    def __init__(self, debug):

        print("Player Started")

        gst_pipe = "udpsrc multicast-group=224.1.1.1 auto-multicast=true port=9000 ! application/x-rtp,encoding-name=H264,payload=96 ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"

        # Set up the gstreamer pipeline
        if (debug):
            self.player = Gst.parse_launch ("videotestsrc ! autovideosink")
            print("demo")
        else:
            self.player = Gst.parse_launch (gst_pipe)
        bus = self.player.get_bus()

        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.window = window
        window.set_title("Raspberry Pi HMD")
        window.set_default_size(1920, 1080)
        screen = window.get_screen()
        window.fullscreen()
        window.connect("destroy", Gtk.main_quit, "WM destroy")

        whbox = Gtk.HBox()
        window.add(whbox)
        bus.window = Gtk.DrawingArea()
        whbox.pack_start(bus.window, True, True, 0)

        window.realize()
        window.show_all()


        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)

        bus.hnd = gdkdll.gdk_win32_window_get_handle(ctypes.pythonapi.PyCapsule_GetPointer(bus.window.get_property("window").__gpointer__, None))

        self.player.set_state(Gst.State.PLAYING)
        set_interval(self.getPos, 0.1)

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
            self.button.set_label("Start")
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.player.set_state(Gst.State.NULL)
            self.button.set_label("Start")

    def on_sync_message(self, bus, message):
        struct = message.get_structure()
        if not struct:
            return
        message_name = struct.get_name()
        # Printer(self.left_window.get_property('window'))

        if message_name == "prepare-window-handle":

            #get the gdk window and the corresponding c gpointer
            drawingareawnd = bus.window.get_property("window")
            drawingareawnd.ensure_native()
        #    self.left_window.realize()
         
            #make sure to call ensure_native before e.g. on realize
            if not drawingareawnd.has_native():
                print("Your window is gonna freeze as soon as you move or resize it...")
            #get the win32 handle

            # Assign the viewport
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", False)
            imagesink.set_window_handle(bus.hnd)

    def getPos(self):
        (x,y) = self.window.get_pointer()
        x = self.setBetween(x,0,1920)
        y = self.setBetween(y,0,1080)

        x = 1500*(1920-x)/1920+1000
        y = 1500*y/1080+1000
        pi.set_servo_pulsewidth(PAN, x)
        pi.set_servo_pulsewidth(TILT, y)

        print("x: "+str(x) +" y: "+str(y))

    def setBetween(self, n, b, t):
        if (n<b):
            return b
        if (n>t):
            return t
        return n

def main():
    debug = True & False
    Gst.init(None)
    Holo_Drone_Main(debug)
    GObject.threads_init()
    Gtk.main()

if __name__ == "__main__":
    main()


# raspivid -t 0 -w 1920 -h 1080 -fps 30 -b 4000000 -o - | gst-launch-1.0 -v fdsrc ! h264parse config-interval=1 ! rtph264pay ! udpsink host=192.168.1.120 port=9000