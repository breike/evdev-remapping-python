#!/usr/bin/python3

# CC0, originally written by t184256.

# This is an example Python program for Linux that remaps a keyboard.
# The events (key presses releases and repeats), are captured with evdev,
# and then injected back with uinput.

# This approach should work in X, Wayland, anywhere!

# Also it is not limited to keyboards, may be adapted to any input devices.

# The program should be easily portable to other languages or extendable to
# run really any code in 'macros', e.g., fetching and typing current weather.

# The ones eager to do it in C can take a look at (overengineered) caps2esc:
# https://github.com/oblitum/caps2esc


# Import necessary libraries.
import argparse
import atexit
import datetime
# You need to install evdev with a package manager or pip3.
import evdev  # (sudo pip3 install evdev)
import tomllib

configs = {
    "current_number": 0,
    "list": []
}


def add_to_configs_list(path):
    configs["list"].append(path)


argument_parser = argparse.ArgumentParser(prog="kekmapper",
                                          description="Remapping on evdev")
argument_parser.add_argument("-c", type=add_to_configs_list)
argument_parser.parse_args()

with open(configs["list"][configs["current_number"]], "rb") as f:
    config = tomllib.load(f)


def send_layout_change_signal(signal):
    if wanted_keyboard == 'thinkpad':
        f = open("/sys/class/leds/tpacpi::thinklight/brightness", "w")
        if signal == "on":
            f.write("1")
        else:
            f.write("0")
        f.close()
    else:
        pass

def parse_config_maps(config):
    maps = {}

    for map in config['maps'].keys():
        for hotkey in map:
            


# The names can be found with evtest or in evdev docs.
# The keyboard name we will intercept the events for. Obtainable with evtest.

MATCH = config["device"]["wantedKeyboard"]
# Find all input devices.
devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
if config["device"]["wantedIdType"] == "name":
    # Limit the list to those containing MATCH and pick the first one.
    kbd = [d for d in devices if MATCH in d.name][0]
elif config["device"]["wantedIdType"] == "path":
    kbd = [d for d in devices if MATCH in d.path][0]
else:
    print("Unknown device ID type: ",
          config["device"]["wantedIdType"], "\n")
    exit(1)

atexit.register(kbd.ungrab)  # Don't forget to ungrab the keyboard on exit!
kbd.grab()  # Grab, i.e. prevent the keyboard from emitting original events.

flags = {
    "current_layout": "base_map",
    "current_level": 0,
    "prssd_ctl": False,
    "prssd_shift": False,
    "soloing_spc": False # A flag needed for CapsLock example later.
}

key_maps = parse_config_maps(config)

soloing_spc   = False  
pressed_ctrl  = False
pressed_shift = False
spc_layout    = False
meta_layout   = False

space_key_timestamp = datetime.datetime.now()  # timestamp for space hotkey for autodisabling space layout in some time
meta_key_timestamp  = datetime.datetime.now()  # timestamp for meta hotkey for autodisabling meta layout in some time

# Create a new keyboard mimicking the original one.
with evdev.UInput.from_device(kbd, name='kbdremap') as ui:
    remapped_code = False
    for ev in kbd.read_loop():  # Read events from original keyboard.
        if ev.type == evdev.ecodes.EV_KEY:  # Process key events.
            # If we just pressed (or held) CapsLock, remember it.
            # Other keys will reset this flag.
            # Also, remap a 'solo CapsLock' into an Escape as promised.
            soloing_spc = (ev.code == evdev.ecodes.KEY_SPACE and ev.value)

            # opening Ctrl+Key hotkey for chord
            if (pressed_ctrl and ev.value == 1 and ev.code != evdev.ecodes.KEY_LEFTMETA):
                ui.write(evdev.ecodes.EV_KEY, evdev.ecodes.KEY_LEFTCTRL, 1)

            if ev.code == evdev.ecodes.KEY_PAUSE and ev.value == 1:
                # Exit on pressing PAUSE.
                # Useful if that is your only keyboard. =)
                # Also if you bind that script to PAUSE, it'll be a toggle.
                break
            elif (ev.code == evdev.ecodes.KEY_TAB) and (spc_layout or meta_layout):
                spc_layout = False
                meta_layout = False
                send_layout_change_signal("off")
            elif ev.code in REMAP_TABLE:
                # Lookup the key we want to press/release instead...
                remapped_code = REMAP_TABLE[ev.code]
                # And do it.
                ui.write(evdev.ecodes.EV_KEY, remapped_code, ev.value)
            # if shift was pressed in previous time
            #elif (pressed_shift and ev.code in SHIFT_KEYS):
            #    # make shift hotkey
            #    ui.write(evdev.ecodes.EV_KEY, SHIFT_KEYS[ev.code], ev.value)
            #    # always send it because key can stuck if shift key released first
            #    ui.write(evdev.ecodes.EV_KEY, SHIFT_KEYS[ev.code], 0)
            # if space was pressed in previous time
            elif (spc_layout and ev.code in SPACE_KEYS):
                time_difference = datetime.datetime.now() - space_key_timestamp
                # if time difference between now and entering space layout is less needed timeout
                if (time_difference.total_seconds() < space_key_timeout):
                    # make space hotkey
                    ui.write(evdev.ecodes.EV_KEY, SPACE_KEYS[ev.code], ev.value)
                    # update timer
                    space_key_timestamp = datetime.datetime.now()
                    send_layout_change_signal("on")
                else:
                    # else disable space layout and send default key
                    ui.write(ev.type, ev.code, ev.value)
                    spc_layout = False
                    send_layout_change_signal("off")
            elif (meta_layout and ev.code in META_KEYS):
                time_difference = datetime.datetime.now() - meta_key_timestamp
                # if time difference between now and entering meta layout is less needed timeout
                if (time_difference.total_seconds() < meta_key_timeout):
                    # make meta hotkey
                    ui.write(evdev.ecodes.EV_KEY, META_KEYS[ev.code], ev.value)
                    # update timer
                    meta_key_timestamp = datetime.datetime.now()
                else:
                    # else disable meta layout and send default key
                    ui.write(ev.type, ev.code, ev.value)
                    meta_layout = False
                    send_layout_change_signal("off")
            # space layout works like a chord: if space key pressed and released,
            # layout activates, if pressed again, deactivates
            elif ev.code == evdev.ecodes.KEY_SPACE and pressed_shift:
                if (ev.value > 0):
                    if spc_layout == True:
                        spc_layout = False
                        send_layout_change_signal("off")
                    else:
                        spc_layout = True
                        space_key_timestamp = datetime.datetime.now()
                        send_layout_change_signal("on")

                        pressed_shift = False
                        meta_layout   = False
            elif (key_layout == 'colemak-wide-angle' and  ev.code in COLEMAK_TABLE):
                # Lookup the key we want to press/release instead...
                remapped_code = COLEMAK_TABLE[ev.code]
                # And do it.
                ui.write(evdev.ecodes.EV_KEY, remapped_code, ev.value)
            else:
                # Passthrough other events unmodified (e.g. SYNs).
                ui.write(ev.type, ev.code, ev.value)

            if ev.code == evdev.ecodes.KEY_LEFTSHIFT:
                if (ev.value > 0):
                    pressed_shift = True
                else:
                    pressed_shift = False

            # closing Ctrl+Key hotkey for chord
            if (pressed_ctrl and ev.value == 0 and ev.code != evdev.ecodes.KEY_LEFTMETA):
                ui.write(evdev.ecodes.EV_KEY, evdev.ecodes.KEY_LEFTCTRL, 0)
                pressed_ctrl = False

            if ev.code == evdev.ecodes.KEY_LEFTMETA and ev.value == 1:
                if pressed_ctrl == False:
                    pressed_ctrl = True
                else:
                    pressed_ctrl = False
        else:
            # Passthrough other events unmodified (e.g. SYNs).
            ui.write(ev.type, ev.code, ev.value)



        # meta layout works like a chord: if meta key pressed and released,
        # layout activates, if pressed again or pressed escape, deactivates
        if ev.code == evdev.ecodes.KEY_LEFTCTRL:
            if (ev.value > 0):
                if meta_layout == True:
                    meta_layout = False
                    print("meta_layout is disabled")
                    send_layout_change_signal("off")
                else:
                    meta_layout = True
                    print("meta_layout is enabled")
                    send_layout_change_signal("on")
                    meta_key_timestamp = datetime.datetime.now()

                    pressed_shift = False
                    spc_layout    = False
