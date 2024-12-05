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
import pprint
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
    f = open("/sys/class/leds/tpacpi::thinklight/brightness", "w")
    if signal == "on":
        f.write("1")
    else:
        f.write("0")
    f.close()

def parse_config_maps(config):
    maps = {}

    for map in config['maps'].keys():
        # map structure:
        # {map: level: previous_level_key: old_key: new_key}
        maps.update({map: {0: {}}})

        layer_lvl = 0

        for hotkey in config['maps'][map]:
            # if first element of hotkey is list
            if isinstance(hotkey[0], list):
                prev_lvl_key = ""

                for index, key in enumerate(hotkey[0]):
                    if index == 0:
                        prev_lvl_key = key
                    else:
                        prev_lvl_key = prev_lvl_key + ", " + key

                    if not layer_lvl in maps[map]:
                        maps[map].update({layer_lvl: {}})

                    maps[map][layer_lvl].update({prev_lvl_key: hotkey[1]})

                    layer_lvl += 1

                layer_lvl = 0

                maps[map][layer_lvl].update({hotkey[0][0]: 0})
                if not (layer_lvl + 1) in maps[map]:
                    maps[map].update({layer_lvl + 1: {}})
            else:
                maps[map][0].update({hotkey[0]: hotkey[1]})

        layer_lvl += 1

#        while True:
#            have_keys_on_layer = False
#
#            if not layer_lvl in maps[map]:
#                maps[map].update({layer_lvl: {}})
#
#            for key in maps[map].keys():

    return maps

#pp = pprint.PrettyPrinter(width=41, compact=True)
#pp.pprint(parse_config_maps(config))
#exit(0)

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
    "soloing_spc": False, # A flag needed for CapsLock example later.
    "prev_lvl_keys": []
}

key_maps = parse_config_maps(config)

# timestamp for space hotkey for autodisabling space layout in some time
space_key_timestamp = datetime.datetime.now()
# timestamp for meta hotkey for autodisabling meta layout in some time
meta_key_timestamp = datetime.datetime.now()

# Create a new keyboard mimicking the original one.
with evdev.UInput.from_device(kbd, name='kbdremap2') as ui:
    remapped_code = False
    for ev in kbd.read_loop():  # Read events from original keyboard.
        if ev.type == evdev.ecodes.EV_KEY:  # Process key events.
            pressed_key = ""
            # If we just pressed (or held) CapsLock, remember it.
            # Other keys will reset this flag.
            # Also, remap a 'solo CapsLock' into an Escape as promised.
            if len(flags["prev_lvl_keys"]) > 0:
                for key in flags["prev_lvl_keys"]:
                    if key == flags["prev_lvl_keys"][0]:
                        pressed_key = key
                    elif (len(flags["prev_lvl_keys"]) == 1):
                        pressed_key = key
                    else:
                        pressed_key = pressed_key + ", " + key

                pressed_key = pressed_key + ", " + evdev.ecodes.KEY[ev.code]
            else:
                pressed_key = evdev.ecodes.KEY[ev.code]

            if pressed_key in key_maps[flags["current_layout"]][flags["current_level"]]:
                print("Key in config\n")
                if key_maps[flags["current_layout"]][flags["current_level"]][pressed_key] == 0 and ev.value == 1:
                    flags["current_level"] += 1
                    flags["prev_lvl_keys"].append(evdev.ecodes.KEY[ev.code])
                    print("Move to next level\n")
                elif "map:" == key_maps[flags["current_layout"]][flags["current_level"]][pressed_key][0:4] and ev.value == 1:
                    flags["current_layout"] = key_maps[flags["current_layout"]][flags["current_level"]][pressed_key][4:]
                    flags["current_level"] = 0
                    print("Move to another layout\n")
                else:
                    ui.write(ev.type, evdev.ecodes.ecodes[key_maps[flags["current_layout"]][flags["current_level"]][pressed_key]], ev.value)
                    print("Sended key\n")
            else:
                flags["current_level"] = 0
                flags["prev_lvl_keys"] = []
                flags["current_layout"] = "base_map"
                ui.write(ev.type, ev.code, ev.value)

                print("Pressed key: " + pressed_key + "\n")
                if pressed_key in key_maps[flags["current_layout"]][flags["current_level"]]:
                    print("Final key: " + str(key_maps[flags["current_layout"]][flags["current_level"]][pressed_key]) + "\n")
                print("current_layout: " + str(flags["current_layout"]) + "\n")
                print("current_level: " + str(flags["current_level"]) + "\n")
                print("prssd_ctl: " + str(flags["prssd_ctl"]) + "\n")
                print("prssd_shift: " + str(flags["prssd_shift"]) + "\n")
                print("soloing_spc: " + str(flags["soloing_spc"]) + "\n")
                print("prev_lvl_keys: " + str(flags["prev_lvl_keys"]) + "\n")

        else:
            # Passthrough other events unmodified (e.g. SYNs).
            ui.write(ev.type, ev.code, ev.value)
