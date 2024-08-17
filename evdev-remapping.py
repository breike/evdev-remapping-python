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
    evdev.ecodes.KEY_CAPSLOCK: evdev.ecodes.KEY_SCREENLOCK,
    evdev.ecodes.KEY_TAB: evdev.ecodes.KEY_ESC,
    evdev.ecodes.KEY_ESC: evdev.ecodes.KEY_GRAVE,
    evdev.ecodes.KEY_GRAVE: evdev.ecodes.KEY_TAB,
    evdev.ecodes.KEY_SPACE: evdev.ecodes.KEY_EJECTCD,
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

# Create a new keyboard mimicking the original one.
with evdev.UInput.from_device(kbd, name='kbdremap') as ui:
    for ev in kbd.read_loop():  # Read events from original keyboard.
        if ev.type == evdev.ecodes.EV_KEY:  # Process key events.
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
                # Also, remap a 'solo CapsLock' into an Escape as promised.
                if ev.code == evdev.ecodes.KEY_CAPSLOCK and ev.value == 0:
                    if soloing_spc:
                        # Single-press Space.
                        ui.write(evdev.ecodes.EV_KEY, evdev.ecodes.KEY_SPACE, 1)
                        ui.write(evdev.ecodes.EV_KEY, evdev.ecodes.KEY_SPACE, 0)
            else:
                # Passthrough other key events unmodified.
                ui.write(evdev.ecodes.EV_KEY, ev.code, ev.value)
            # If we just pressed (or held) CapsLock, remember it.
            # Other keys will reset this flag.
            soloing_spc = (ev.code == evdev.ecodes.KEY_SPACE and ev.value)
        else:
            # Passthrough other events unmodified (e.g. SYNs).
            ui.write(ev.type, ev.code, ev.value)
