import time
import neopixel
import keypad
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.helper import PixelSubset
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.color import calculate_intensity
from hex_settings import TRANSITION_SECONDS, TRANSITION_EASING, BRIGHTNESS_BRIGHT, BRIGHTNESS_DIM, PIXELS_PIN, SEAT_CONFIG, BUTTON_SWITCH_VALUE_WHEN_PRESSED
import adafruit_fancyled.adafruit_fancyled as fancy
import supervisor

# Game State
GAME_STATE_NOT_STARTED = 0
GAME_STATE_STARTED = 1
game_state = GAME_STATE_NOT_STARTED

# Setup NeoPixel Strip
pixels_length = sum([seat['pixel_length'] for seat in SEAT_CONFIG])
pixels = neopixel.NeoPixel(PIXELS_PIN, pixels_length, brightness=1, auto_write=False)

# Setup Button Switches
keys = keypad.Keys(tuple((seat['switch_pin']) for seat in SEAT_CONFIG), value_when_pressed=BUTTON_SWITCH_VALUE_WHEN_PRESSED, pull=True)

# Setup Seats
class Seat:
	def __init__(self, index):
		self.is_in_game = False
		self.is_active = False
		self.index = index
		self.start_pixel = 0
		self.color = SEAT_CONFIG[index]['color']
		self.fade_start_color = None
		self.fade_end_color = None
		self.fade_ts = None
		self.pixel_length = SEAT_CONFIG[index]['pixel_length']
		self.led_pin = SEAT_CONFIG[index]['led_pin']
		for n in range(index):
			self.start_pixel += SEAT_CONFIG[n]['pixel_length']
		self.end_pixel = self.start_pixel + self.pixel_length - 1
		self.pixel_subset = PixelSubset(pixels, self.start_pixel, self.end_pixel+1)
		self.selected_animation = Comet(self.pixel_subset, 0.1, self.color.pack(), tail_length=self.pixel_length, bounce=True, reverse=True)

	def reset(self):
		self.is_active = False
		self.is_in_game = False
		self.led_pin.value = False

	def make_selected(self):
		self.is_in_game = True

	def make_inactive(self):
		self.is_active = False
		self.led_pin.value = False

	def make_active(self):
		self.is_active = True
		self.led_pin.value = True
	
	def set_color(self, color):
		brightness = BRIGHTNESS_BRIGHT if self.is_active else BRIGHTNESS_DIM
		self.fade_end_color = fancy.gamma_adjust(color, brightness=brightness)
		self.fade_start_color = fancy.CRGB(*self.pixel_subset[0])
		self.fade_ts = time.monotonic()

	def animate(self):
		if game_state == GAME_STATE_NOT_STARTED:
			if self.is_in_game:
				self.selected_animation.animate()
			else:
				self.pixel_subset.fill((0,0,0))
		else:
			elapsed_time = min(TRANSITION_SECONDS, (time.monotonic() - self.fade_ts))
			if elapsed_time == TRANSITION_SECONDS:
				self.pixel_subset.fill(self.fade_end_color.pack())
			else:
				fade_progress = TRANSITION_EASING.ease(elapsed_time)
				color = fancy.mix(self.fade_start_color, self.fade_end_color, fade_progress)
				self.pixel_subset.fill(color.pack())
		self.pixel_subset.show()

	def __str__(self):
		return f"Seat {self.index} (color={self.color}, px={self.start_pixel}-{self.end_pixel})"
	def __repr__(self):
		return self.__str__()
	
seats = [Seat(n) for n in range(len(SEAT_CONFIG))]

# Does the inital 
def determine_taken_seats():
	global game_state
	game_state = GAME_STATE_NOT_STARTED
	for seat in seats:
		seat.reset()
	rainbow = RainbowComet(pixels, 0.1, tail_length=5, ring=True)
	keys.reset()
	pressed_keys = set()
	selected_seats = set()
	while True:
		while True:
			event = keys.events.get()
			if not event:
				break
			elif event.pressed:
				print(f"Key {event.key_number} is pressed")
				pressed_keys.add(event.key_number)
				if len(selected_seats) == 0:
					pixels.fill((0,0,0))
					pixels.show()
				selected_seats.add(event.key_number)
				seats[event.key_number].make_selected()
			else: 
				print(f"Key {event.key_number} was released")
				pressed_keys.remove(event.key_number)
		if len(pressed_keys) == 0 and len(selected_seats) == 0:
			rainbow.animate()
		elif len(pressed_keys) == 0:
			return selected_seats.pop()
		else:
			for seat in seats:
				seat.animate()

# The Eternal Loop
while True:
	active_player = determine_taken_seats()
	print(f"First player is {active_player}")
	game_state = GAME_STATE_STARTED
	for seat in seats:
		if seat.index == active_player:
			seat.make_active()
		else:
			seat.make_inactive()
		seat.set_color(seats[active_player].color)

	pressed_keys = dict()
	keys.reset()
	while True:		
		# Detect any button presses
		while True:
			event = keys.events.get()
			if not event:
				break
			elif event.released:
				del pressed_keys[event.key_number]
			elif event.pressed:
				pressed_keys[event.key_number] = event.timestamp
				if event.key_number == active_player:
					seats[active_player].make_inactive()
					while True:
						active_player += 1
						active_player = active_player % len(seats)
						if seats[active_player].is_in_game:
							seats[active_player].make_active()
							for seat in seats:
								seat.set_color(seats[active_player].color)
							break
					break
				
		for seat in seats:
			seat.animate()

		cutoff = supervisor.ticks_ms() - 3 * 1000
		long_press_detected = False
		for ts in pressed_keys.values():
			if ts < cutoff:
				long_press_detected = True
				break
		
		if long_press_detected:
			print("RESET!")
			pixels.fill((0,0,0))
			pixels.show()
			while True:
				event = keys.events.get()
				if not event:
					if len(pressed_keys) == 0:
						break
				elif event.released:
					del pressed_keys[event.key_number]
				elif event.pressed:
					pressed_keys[event.key_number] = event.timestamp
			break