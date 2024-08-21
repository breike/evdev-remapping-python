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
import atexit
# You need to install evdev with a package manager or pip3.
import evdev  # (sudo pip3 install evdev)


# Define an example dictionary describing the remaps.
REMAP_TABLE = {
    # Let's swap A and B...
    evdev.ecodes.KEY_CAPSLOCK: evdev.ecodes.KEY_WWW,
    evdev.ecodes.KEY_TAB: evdev.ecodes.KEY_ESC,
    evdev.ecodes.KEY_ESC: evdev.ecodes.KEY_GRAVE,
    evdev.ecodes.KEY_GRAVE: evdev.ecodes.KEY_TAB,
    #evdev.ecodes.KEY_SPACE: evdev.ecodes.KEY_MAIL,
    evdev.ecodes.KEY_LEFTMETA: evdev.ecodes.KEY_LEFTCTRL,
    evdev.ecodes.KEY_LEFTCTRL: evdev.ecodes.KEY_LEFTMETA,
    evdev.ecodes.KEY_1: evdev.ecodes.KEY_STOP,
    evdev.ecodes.KEY_2: evdev.ecodes.KEY_STOP,
    evdev.ecodes.KEY_3: evdev.ecodes.KEY_STOP,
    evdev.ecodes.KEY_4: evdev.ecodes.KEY_SPACE,
    evdev.ecodes.KEY_5: evdev.ecodes.KEY_STOP,
    evdev.ecodes.KEY_6: evdev.ecodes.KEY_BACKSPACE,
    evdev.ecodes.KEY_7: evdev.ecodes.KEY_STOP,
    evdev.ecodes.KEY_8: evdev.ecodes.KEY_STOP,
    evdev.ecodes.KEY_9: evdev.ecodes.KEY_STOP,
    evdev.ecodes.KEY_0: evdev.ecodes.KEY_STOP,
    evdev.ecodes.KEY_MINUS: evdev.ecodes.KEY_SPACE,
    evdev.ecodes.KEY_EQUAL: evdev.ecodes.KEY_SPACE,
}

# mapping for space hotkeys (Space+Key, etc...)
SPACE_KEYS = {
    # Space+Q to 1
    evdev.ecodes.KEY_Q: evdev.ecodes.KEY_1,
    # Space+W to 2
    evdev.ecodes.KEY_W: evdev.ecodes.KEY_2,
    # Space+E to 3
    evdev.ecodes.KEY_E: evdev.ecodes.KEY_3,
    # Space+R to 4
    evdev.ecodes.KEY_R: evdev.ecodes.KEY_4,
    # Space+A to 5
    evdev.ecodes.KEY_A: evdev.ecodes.KEY_5,
    # Space+S to 6
    evdev.ecodes.KEY_S: evdev.ecodes.KEY_6,
    # Space+D to 7
    evdev.ecodes.KEY_D: evdev.ecodes.KEY_7,
    # Space+F to 8
    evdev.ecodes.KEY_F: evdev.ecodes.KEY_8,
    # Space+Z to 9
    evdev.ecodes.KEY_Z: evdev.ecodes.KEY_9,
    # Space+X to 0
    evdev.ecodes.KEY_X: evdev.ecodes.KEY_0,
    # Space+C to minus
    evdev.ecodes.KEY_C: evdev.ecodes.KEY_MINUS,
    # Space+V to equal
    evdev.ecodes.KEY_V: evdev.ecodes.KEY_EQUAL,
    # Space+Caps Lock to mail key
    evdev.ecodes.KEY_CAPSLOCK: evdev.ecodes.KEY_EJECTCD,
}

# mapping for shift hotkeys (Shift+Key, etc...)
SHIFT_KEYS = {
    # force space key for shift hotkey (Shift+Space)
    evdev.ecodes.KEY_SPACE: evdev.ecodes.KEY_SPACE,
}

# The names can be found with evtest or in evdev docs.


# The keyboard name we will intercept the events for. Obtainable with evtest.
MATCH = 'Akko 2.4G Wireless Keyboard'
# Find all input devices.
devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
# Limit the list to those containing MATCH and pick the first one.
kbd = [d for d in devices if MATCH in d.name][0]
atexit.register(kbd.ungrab)  # Don't forget to ungrab the keyboard on exit!
kbd.grab()  # Grab, i.e. prevent the keyboard from emitting original events.


soloing_spc = False  # A flag needed for CapsLock example later.
pressed_spc = False
pressed_shift = False

# Create a new keyboard mimicking the original one.
with evdev.UInput.from_device(kbd, name='kbdremap') as ui:
    for ev in kbd.read_loop():  # Read events from original keyboard.
        if ev.type == evdev.ecodes.EV_KEY:  # Process key events.
            # If we just pressed (or held) CapsLock, remember it.
            # Other keys will reset this flag.
            # Also, remap a 'solo CapsLock' into an Escape as promised.
            soloing_spc = (ev.code == evdev.ecodes.KEY_SPACE and ev.value)

            if ev.code == evdev.ecodes.KEY_PAUSE and ev.value == 1:
                # Exit on pressing PAUSE.
                # Useful if that is your only keyboard. =)
                # Also if you bind that script to PAUSE, it'll be a toggle.
                break
            elif ev.code in REMAP_TABLE:
                # Lookup the key we want to press/release instead...
                remapped_code = REMAP_TABLE[ev.code]
                # And do it.
                ui.write(evdev.ecodes.EV_KEY, remapped_code, ev.value)
            # if shift was pressed in previous time
            elif (pressed_shift and ev.code in SHIFT_KEYS):
                # make shift hotkey
                ui.write(evdev.ecodes.EV_KEY, SHIFT_KEYS[ev.code], ev.value)
                # always send it because key can stuck if shift key released first
                ui.write(evdev.ecodes.EV_KEY, SHIFT_KEYS[ev.code], 0)
            # if space was pressed in previous time
            elif (pressed_spc and ev.code in SPACE_KEYS):
                # make space hotkey
                ui.write(evdev.ecodes.EV_KEY, SPACE_KEYS[ev.code], ev.value)
                # always send it because key can stuck if space key released first
                ui.write(evdev.ecodes.EV_KEY, SPACE_KEYS[ev.code], 0)
            elif ev.code == evdev.ecodes.KEY_SPACE:
                if (ev.value > 0):
                    pressed_spc = True
                else:
                    pressed_spc = False
            else:
                # Passthrough other events unmodified (e.g. SYNs).
                ui.write(ev.type, ev.code, ev.value)

            if ev.code == evdev.ecodes.KEY_LEFTSHIFT:
                if (ev.value > 0):
                    pressed_shift = True
                else:
                    pressed_shift = False
        else:
            # Passthrough other events unmodified (e.g. SYNs).
            ui.write(ev.type, ev.code, ev.value)