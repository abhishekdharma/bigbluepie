#!/usr/bin/env python

"""Copyright (c) 2015, Douglas Otwell

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Dependencies:
# sudo apt-get install -y python-gobject
# sudo apt-get install -y python-smbus
from gi.repository import GLib

import time
import dbus
import dbus.service
import dbus.mainloop.glib
import gobject
import logging
import traceback
import Tkinter as tk
import ttk

SERVICE_NAME = "org.bluez"
AGENT_IFACE = SERVICE_NAME + '.Agent1'
ADAPTER_IFACE = SERVICE_NAME + ".Adapter1"
DEVICE_IFACE = SERVICE_NAME + ".Device1"
PLAYER_IFACE = SERVICE_NAME + '.MediaPlayer1'
TRANSPORT_IFACE = SERVICE_NAME + '.MediaTransport1'
PHONEBOOK_ACCESS_INTERFACE = SERVICE_NAME + 'obex.PhonebookAccess1'

#LOG_LEVEL = logging.INFO
LOG_LEVEL = logging.DEBUG
LOG_FILE = "/dev/stdout"
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

"""Utility functions from bluezutils.py"""
def getManagedObjects():
    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
    return manager.GetManagedObjects()

def findAdapter():
    objects = getManagedObjects();
    bus = dbus.SystemBus()
    for path, ifaces in objects.iteritems():
        adapter = ifaces.get(ADAPTER_IFACE)
        if adapter is None:
            continue
        obj = bus.get_object(SERVICE_NAME, path)
        return dbus.Interface(obj, ADAPTER_IFACE)
    raise Exception("Bluetooth adapter not found")

class BluePlayer(dbus.service.Object):
    AGENT_PATH = "/blueplayer/agent"
#    CAPABILITY = "DisplayOnly"
    CAPABILITY = "NoInputNoOutput"

#    lcd = None
    bus = None
    adapter = None
    device = None
    deviceAlias = None
    player = None
    transport = None
    connected = None
    state = None
    status = None
    discoverable = None
    track = None
    mainloop = None
#   tkTop = None 
    lines = []
    notebook = None
    modem = None
    modem_path = None
    def __init__(self):
	print("Init")

    def start(self):
        from gui import gui_init
        from gui import refreshApp
        """Initialize gobject, start the LCD, and find any current media players"""
        gobject.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self.bus = dbus.SystemBus()
        dbus.service.Object.__init__(self, dbus.SystemBus(), BluePlayer.AGENT_PATH)

        self.bus.add_signal_receiver(self.playerHandler,
                bus_name="org.bluez",
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged",
                path_keyword="path")

        self.registerAgent()

        adapter_path = findAdapter().object_path
        self.bus.add_signal_receiver(self.adapterHandler,
                bus_name = "org.bluez",
                path = adapter_path,
                dbus_interface = "org.freedesktop.DBus.Properties",
                signal_name = "PropertiesChanged",
                path_keyword = "path")
 
	self.bus.add_signal_receiver(self.call_added,
				bus_name="org.ofono",
				signal_name = "CallAdded",
				member_keyword="member",
				path_keyword="path",
				interface_keyword="interface")

	self.bus.add_signal_receiver(self.call_removed,
				bus_name="org.ofono",
				signal_name = "CallRemoved",
				member_keyword="member",
				path_keyword="path",
				interface_keyword="interface")

        self.findPlayer()
        gui_init(self)
        self.updateDisplay()
	self.enableModem()

        """Start the BluePlayer by running the gobject mainloop()"""
	gobject.idle_add(refreshApp)	
        self.mainloop = gobject.MainLoop()
        self.mainloop.run()
#	tk.mainloop()

    def call_added(self, name, value, member, path, interface):
        from gui import update_phone_display
        iface = interface[interface.rfind(".") + 1:]
        print("{%s} [%s] %s %s" % (iface, member, name, value['LineIdentification']))
	update_phone_display("Incoming: ", value['LineIdentification'])
		 
    def call_removed(self, name, member, path, interface):
        from gui import update_phone_display
	iface = interface[interface.rfind(".") + 1:]
	print("{%s} [%s] %s" % (iface, name, member))
	update_phone_display("", "") 

    def enableModem(self):
	"""Enable modem"""
	manager = dbus.Interface(self.bus.get_object('org.ofono', '/'),
			'org.ofono.Manager')
	modems = manager.GetModems()
	self.modem_path = modems[0][0]
	print("Connecting modem %s..." % self.modem_path)
	self.modem = dbus.Interface(self.bus.get_object('org.ofono', self.modem_path), 'org.ofono.Modem')

    def findPlayer(self):
        """Find any current media players and associated device"""
        manager = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()

        player_path = None
        transport_path = None
        print (objects.iteritems())
        for path, interfaces in objects.iteritems():
            print(interfaces)
            if PLAYER_IFACE in interfaces:
                player_path = path
            if TRANSPORT_IFACE in interfaces:
                transport_path = path

        if player_path:
            logging.debug("Found player on path [{}]".format(player_path))
            self.connected = True
            self.getPlayer(player_path)
            player_properties = self.player.GetAll(PLAYER_IFACE, dbus_interface="org.freedesktop.DBus.Properties")
            if "Status" in player_properties:
                self.status = player_properties["Status"]
            if "Track" in player_properties:
                self.track = player_properties["Track"]
        else:
            logging.debug("Could not find player")

        if transport_path:
            logging.debug("Found transport on path [{}]".format(player_path))
            self.transport = self.bus.get_object("org.bluez", transport_path)
            logging.debug("Transport [{}] has been set".format(transport_path))
            transport_properties = self.transport.GetAll(TRANSPORT_IFACE, dbus_interface="org.freedesktop.DBus.Properties")
            if "State" in transport_properties:
                self.state = transport_properties["State"]

    def getPlayer(self, path):
        """Get a media player from a dbus path, and the associated device"""
        self.player = self.bus.get_object("org.bluez", path)
        logging.debug("Player [{}] has been set".format(path))
        device_path = self.player.Get("org.bluez.MediaPlayer1", "Device", dbus_interface="org.freedesktop.DBus.Properties")
        self.getDevice(device_path)

    def getDevice(self, path):
        """Get a device from a dbus path"""
        self.device = self.bus.get_object("org.bluez", path)
        self.deviceAlias = self.device.Get(DEVICE_IFACE, "Alias", dbus_interface="org.freedesktop.DBus.Properties")

    def playerHandler(self, interface, changed, invalidated, path):
        """Handle relevant property change signals"""
        logging.debug("Interface [{}] changed [{}] on path [{}]".format(interface, changed, path))
        iface = interface[interface.rfind(".") + 1:]

        if iface == "Device1":
            if "Connected" in changed:
                self.connected = changed["Connected"]
        if iface == "MediaControl1":
            if "Connected" in changed:
                self.connected = changed["Connected"]
                if changed["Connected"]:
                    logging.debug("MediaControl is connected [{}] and interface [{}]".format(path, iface))
                    self.findPlayer()
        elif iface == "MediaTransport1":
            if "State" in changed:
                logging.debug("State has changed to [{}]".format(changed["State"]))
                self.state = (changed["State"])
            if "Connected" in changed:
                self.connected = changed["Connected"]
        elif iface == "MediaPlayer1":
            if "Track" in changed:
                logging.debug("Track has changed to [{}]".format(changed["Track"]))
                self.track = changed["Track"]
            if "Status" in changed:
                logging.debug("Status has changed to [{}]".format(changed["Status"]))
                self.status = (changed["Status"])
    
        self.updateDisplay()

    def adapterHandler(self, interface, changed, invalidated, path):
        """Handle relevant property change signals"""
        if "Discoverable" in changed:
                logging.debug("Adapter dicoverable is [{}]".format(self.discoverable))
                self.discoverable = changed["Discoverable"]
                self.updateDisplay()

    def updateDisplay(self):
        """Display the current status of the device on the LCD"""
        logging.debug("Updating display for connected: [{}]; state: [{}]; status: [{}]; discoverable [{}]".format(self.connected, self.state, self.status, self.discoverable))
        if self.discoverable:
            self.wake()
            self.showDiscoverable()
        else:
            if self.connected:
                self.showPaused()
                self.showTrack()


    def showTrack(self):
        """Display track info on the screen"""
        from gui import update_music_display
        if "Artist" in self.track:
            self.lines.append(self.track["Artist"])
            print("Artist (%s)" % (self.track["Artist"]))
            if self.track["Title"]:
                print("Title (%s)" % (self.track["Title"]))
                self.lines.append(self.track["Title"])
        if "Title" in self.track:
            print("Title (%s)" % (self.track["Title"]))
            self.lines.append(self.track["Title"])
	update_music_display(self.lines)

    def showPaused(self):
        print("Device is paused")

    def showDiscoverable(self):
        print("Waiting to pair")
        print("with device")


    def next(self):
        self.player.Next(dbus_interface=PLAYER_IFACE)

    def previous(self):
        self.player.Previous(dbus_interface=PLAYER_IFACE)

    def play(self):
        print("play issued")
        self.player.Play(dbus_interface=PLAYER_IFACE)

    def pause(self):
        self.player.Pause(dbus_interface=PLAYER_IFACE)

    def answer(self):
        print("answer issued")
        properties = self.modem.GetProperties()
#       for properties, value in self.modem.GetProperties().items():

        print(properties["Interfaces"]);
        if "org.ofono.VoiceCallManager" not in properties["Interfaces"]:
             return

        mgr = dbus.Interface(self.bus.get_object('org.ofono', self.modem_path), 'org.ofono.VoiceCallManager')

        calls = mgr.GetCalls()

        for path, properties in calls:
            state = properties["State"]
            print("[ %s ] %s" % (path, state))

            if state != "incoming":
                continue

            call = dbus.Interface(self.bus.get_object('org.ofono', path), 'org.ofono.VoiceCall')
            call.Answer()

    def end_call(self):
        print ("end issued");
        manager = dbus.Interface(self.bus.get_object('org.ofono', self.modem_path),
                                                'org.ofono.VoiceCallManager')
        manager.HangupAll()
	

    def volumeUp(self):
        self.control.VolumeUp(dbus_interface=CONTROL_IFACE)
        self.transport.VolumeUp(dbus_interface=TRANSPORT_IFACE)

    def shutdown(self):
        logging.debug("Shutting down BluePlayer")
        if self.mainloop:
            self.mainloop.quit()

    def getStatus(self):
        return self.status

    """Pairing agent methods"""
    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print("RequestPinCode (%s)" % (device))
        self.trustDevice(device)
        return "0000"

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        """Always confirm"""
        logging.debug("RequestConfirmation returns")
        self.trustDevice(device)
        return

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        """Always authorize"""
        logging.debug("Authorize service returns")
        return

    def trustDevice(self, path):
        """Set the device to trusted"""
        device_properties = dbus.Interface(self.bus.get_object(SERVICE_NAME, path), "org.freedesktop.DBus.Properties")
        device_properties.Set(DEVICE_IFACE, "Trusted", True)

    def registerAgent(self):
        """Register BluePlayer as the default agent"""
        manager = dbus.Interface(self.bus.get_object(SERVICE_NAME, "/org/bluez"), "org.bluez.AgentManager1")
        manager.RegisterAgent(BluePlayer.AGENT_PATH, BluePlayer.CAPABILITY)
        manager.RequestDefaultAgent(BluePlayer.AGENT_PATH)
        logging.debug("Blueplayer is registered as a default agent")

    def startPairing(self):
        logging.debug("Starting to pair")
        """Make the adpater discoverable"""
        adapter_path = findAdapter().object_path
        adapter = dbus.Interface(self.bus.get_object(SERVICE_NAME, adapter_path), "org.freedesktop.DBus.Properties")
        adapter.Set(ADAPTER_IFACE, "Discoverable", True)


logging.basicConfig(filename=LOG_FILE, format=LOG_FORMAT, level=LOG_LEVEL)
logging.info("Starting BluePlayer")

#gobject.threads_init()
#dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

print("Starting")
print("BluePlayer")
time.sleep(2)

player = None
try:
    player = BluePlayer()
    player.start()
except KeyboardInterrupt as ex:
    logging.info("BluePlayer cancelled by user")
except Exception as ex:
    logging.error("How embarrassing. The following error occurred {}".format(ex))
    traceback.print_exc()
finally:
    player.shutdown()

