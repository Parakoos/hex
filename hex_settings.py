import board
import adafruit_fancyled.adafruit_fancyled as fancy
import digitalio
import busio
import adafruit_74hc595
from easing import CubicEaseOut

P1_COLOR = fancy.CRGB(255, 0, 0)
P2_COLOR = fancy.CRGB(0, 0, 255)
P3_COLOR = fancy.CRGB(0, 255, 0)
P4_COLOR = fancy.CRGB(255, 255, 0)
P5_COLOR = fancy.CRGB(0, 255, 255)
P6_COLOR = fancy.CRGB(255, 0, 255)

#############################################
############ For the Hex Table ##############
#############################################

# Setup Button LEDs Shift Register
latch_pin = digitalio.DigitalInOut(board.IO44)
spi = busio.SPI(board.IO7, MOSI=board.IO9)
sr = adafruit_74hc595.ShiftRegister74HC595(spi, latch_pin)

# Brightness Settings
BRIGHTNESS_BRIGHT = 0.8
BRIGHTNESS_DIM = 0.1

# Fade Transition
TRANSITION_SECONDS = 3
TRANSITION_EASING = CubicEaseOut(0, 1, TRANSITION_SECONDS)

# Different board have different values for when a button is pressed
BUTTON_SWITCH_VALUE_WHEN_PRESSED = False

# NeoPixel Strip
PIXELS_PIN = board.IO43

# Button LED pins
SEAT_CONFIG = [
	{ 'pixel_length': 41, 'switch_pin': board.IO1, 'led_pin': sr.get_pin(1), 'color': P1_COLOR },
    { 'pixel_length': 41, 'switch_pin': board.IO2, 'led_pin': sr.get_pin(2), 'color': P2_COLOR },
    { 'pixel_length': 41, 'switch_pin': board.IO3, 'led_pin': sr.get_pin(3), 'color': P3_COLOR },
    { 'pixel_length': 41, 'switch_pin': board.IO4, 'led_pin': sr.get_pin(4), 'color': P4_COLOR },
    { 'pixel_length': 41, 'switch_pin': board.IO5, 'led_pin': sr.get_pin(5), 'color': P5_COLOR },
    { 'pixel_length': 41, 'switch_pin': board.IO6, 'led_pin': sr.get_pin(6), 'color': P6_COLOR },
]

######################################################
############ For the Circuit Playground ##############
######################################################

# # Brightness Settings
# BRIGHTNESS_BRIGHT = 0.8
# BRIGHTNESS_DIM = 0.1

# # Fade Transition
# TRANSITION_SECONDS = 3
# TRANSITION_EASING = CubicEaseOut(0, 1, TRANSITION_SECONDS)

# # Different board have different values for when a button is pressed
# BUTTON_SWITCH_VALUE_WHEN_PRESSED = True

# # NeoPixel Strip
# PIXELS_PIN = board.NEOPIXEL		# .IO43

# # Button LED pins
# _seat_1_led = digitalio.DigitalInOut(board.D13)
# _seat_1_led.switch_to_output()
# _seat_2_led = digitalio.DigitalInOut(board.A2)
# _seat_2_led.switch_to_output()
# _seat_3_led = digitalio.DigitalInOut(board.A3)
# _seat_3_led.switch_to_output()

# SEAT_CONFIG = [
# 	{ 'pixel_length': 4, 'switch_pin': board.BUTTON_A, 'led_pin': _seat_1_led, 'color': P1_COLOR   },
# 	{ 'pixel_length': 4, 'switch_pin': board.BUTTON_B, 'led_pin': _seat_2_led, 'color': P2_COLOR	},
#     { 'pixel_length': 2, 'switch_pin': board.D6, 'led_pin': _seat_3_led, 'color': P3_COLOR	},
# ]