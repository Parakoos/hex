import time
import neopixel # type: ignore
import keypad
from adafruit_led_animation.animation.pulse import Pulse # type: ignore
from adafruit_led_animation.animation.rainbowcomet import RainbowComet # type: ignore
from adafruit_led_animation.helper import PixelSubset # type: ignore
from hex_settings import TRANSITION_SECONDS, TRANSITION_EASING, BRIGHTNESS_BRIGHT, BRIGHTNESS_DIM, PIXELS_PIN, SEAT_CONFIG, BUTTON_SWITCH_VALUE_WHEN_PRESSED, LONG_PRESS_THRESHOLD_MS, SHORT_PRESS_THRESHOLD_MS, RAINBOW_PIXELS_LENGTH, RAINBOW_SPEED, TIME_REMINDER_BLINK_DURATION_EASING, TIME_REMINDER_EVERY_X_SECONDS, TIME_REMINDER_BLINK_DURATION_SECONDS
import adafruit_fancyled.adafruit_fancyled as fancy # type: ignore
import supervisor
import random

# Game State
FANCY_BLACK = fancy.CRGB(0, 0, 0)
GAME_STATE_NOT_STARTED = 0
GAME_STATE_STARTED = 1
game_state = GAME_STATE_NOT_STARTED
active_player = None
turn_start_ts = None

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
		self.passed = False
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
		self.pixel_subset = PixelSubset(pixels, self.start_pixel, self.end_pixel + 1)
		self.selected_animation = Pulse(self.pixel_subset, speed=0.01, color=self.color.pack(), period=3)

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
				self.pixel_subset.fill((0, 0, 0))
		else:
			now = time.monotonic()
			elapsed_time = min(TRANSITION_SECONDS, (now - self.fade_ts))
			if elapsed_time == TRANSITION_SECONDS:
				if active_player == self.index or turn_start_ts == None:
					# Do not blink the active player
					self.pixel_subset.fill(self.fade_end_color.pack())
				else:
					# Check if we need to blink
					time_into_turn = now - turn_start_ts
					reminder_number, seconds_into_reminder = divmod(time_into_turn, TIME_REMINDER_EVERY_X_SECONDS)
					blink_number, seconds_into_blink = divmod(seconds_into_reminder, TIME_REMINDER_BLINK_DURATION_SECONDS)
					if reminder_number > 0 and blink_number < reminder_number:
						blink_progress = TIME_REMINDER_BLINK_DURATION_EASING(seconds_into_blink)
						color = fancy.mix(self.fade_end_color, FANCY_BLACK, blink_progress)
						self.pixel_subset.fill(color.pack())
					else:
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

# Starts the game, among other things, figuring out what seats around the table are taken.
def start_game():
	global pressed_keys, game_state
	pressed_keys = dict()
	keys.reset()
	start_player_turn(determine_taken_seats())
	print(f"First player is {active_player}")
	game_state = GAME_STATE_STARTED

# Does the initial determination of taken seats
def determine_taken_seats():
	global game_state
	game_state = GAME_STATE_NOT_STARTED
	for seat in seats:
		seat.reset()
	rainbow = RainbowComet(pixels, RAINBOW_SPEED, tail_length=RAINBOW_PIXELS_LENGTH, ring=True)
	keys.reset()
	pressed_keys_set = set()
	selected_seats = set()
	# First, wait for all pressed keys to be released. Important as reset is a long
	# press, so that key will be depressed initially.
	print(f"Release all keys!")
	while True:
		rainbow.animate()
		event = keys.events.get()
		if not event:
			if len(pressed_keys_set) == 0:
				break
		elif event.pressed:
			pressed_keys_set.add(event.key_number)
		else:
			pressed_keys_set.remove(event.key_number)

	print(f"Keys released")
	while True:
		while True:
			event = keys.events.get()
			if not event:
				break
			elif event.pressed:
				print(f"Key {event.key_number} is pressed")
				pressed_keys_set.add(event.key_number)
				if len(selected_seats) == 0:
					pixels.fill((0, 0, 0))
					pixels.show()
				selected_seats.add(event.key_number)
				seats[event.key_number].make_selected()
			else:
				print(f"Key {event.key_number} was released")
				pressed_keys_set.remove(event.key_number)
		if len(pressed_keys_set) == 0 and len(selected_seats) == 0:
			rainbow.animate()
		elif len(pressed_keys_set) == 0:
			return random.choice(list(selected_seats))
		else:
			for seat in seats:
				seat.animate()

# Looks at the keys array to see which further presses and releases has occured, and
# records them for later review.
def detect_button_presses():
	while True:
		event = keys.events.get()
		if not event:
			break

		if event.key_number not in pressed_keys:
			pressed_keys[event.key_number] = {
				"player_number": event.key_number,
				"presses": 0,
				"pressed_ts": None,
				"released_ts": None,
			}

		if event.released and pressed_keys[event.key_number]["pressed_ts"] != None:
			pressed_keys[event.key_number]["released_ts"] = event.timestamp
			print(f"Key released by player {pressed_keys[event.key_number]["player_number"]}, Presses: {pressed_keys[event.key_number]["presses"]}, TS: {pressed_keys[event.key_number]["released_ts"]}")
		elif event.pressed:
			pressed_keys[event.key_number]["presses"] += 1
			pressed_keys[event.key_number]["pressed_ts"] = event.timestamp
			pressed_keys[event.key_number]["released_ts"] = None
			print(f"Key pressed by player {pressed_keys[event.key_number]["player_number"]}, Presses: {pressed_keys[event.key_number]["presses"]}, TS: {pressed_keys[event.key_number]["pressed_ts"]}")

# Looks at the current list of recorded key presses, and see if enough time has passed
# since the last press or release to determine that a series of short presses has concluded,
# optionally ending with a long press.
def handle_button_presses():
	for btn in pressed_keys.values():
		if btn["pressed_ts"] != None and btn["released_ts"] == None:
			# The button is currently being depressed. Is it a long press?
			if supervisor.ticks_ms() - btn["pressed_ts"] > LONG_PRESS_THRESHOLD_MS:
				# Long press detected!
				del pressed_keys[btn["player_number"]]
				execute_button_press(btn["player_number"], btn["presses"], True)
				# Only execute one action per loop to allow for resets to take effect
				return

		elif btn["pressed_ts"] != None and btn["released_ts"] != None:
			# We have a press and release. Has enough time passed to act on it?
			if supervisor.ticks_ms() - btn["released_ts"] > SHORT_PRESS_THRESHOLD_MS:
				# Short press detected!
				del pressed_keys[btn["player_number"]]
				execute_button_press(btn["player_number"], btn["presses"], False)
				# Only execute one action per loop to allow for resets to take effect
				return

# Determines which action to do considering that a certain player has done a series of short and long presses.
def execute_button_press(player_number, press_count, final_long_press):
	global game_state

	if player_number != active_player:
		print(f"Press detected for inactive player ${player_number}. Press Count: ${press_count}, Long Press: ${final_long_press}")

	elif press_count == 1 and not final_long_press:
		# Single press confirmed
		print(f"Single press detected for active player {active_player}")
		go_to_next_player()

	elif press_count == 2 and not final_long_press:
		# Double press detected
		print(f"Double press detected for active player {active_player}")
		seats[active_player].passed = True
		go_to_next_player()

	elif final_long_press:
		print("RESET!")
		pixels.fill((0, 0, 0))
		pixels.show()
		game_state = GAME_STATE_NOT_STARTED

	else:
		print(f"Unmapped press detected for active player ${player_number}. Press Count: ${press_count}, Long Press: ${final_long_press}")

# Move the active player to the next player in turn order.
def go_to_next_player():
	previously_active_player = active_player
	pid = active_player
	while True:
		pid -= 1
		pid = pid % len(seats)
		if pid == previously_active_player and seats[pid].passed:
			# We have run out of players! Everyone must have passed. Reset players.
			end_round()
			return
		elif seats[pid].is_in_game and not seats[pid].passed:
			start_player_turn(pid)
			return

def start_player_turn(player_number):
	global active_player, turn_start_ts
	turn_start_ts = time.monotonic()
	active_player = player_number
	print(f"Player {active_player} started their turn.")
	for seat in seats:
		if seat.index == active_player:
			seat.make_active()
		else:
			seat.make_inactive()
		seat.set_color(seats[active_player].color)


# Makes all taken seats 'un-passed' and sets the new active player to the first
# player to press their button.
def end_round():
	global pressed_keys, turn_start_ts
	turn_start_ts = None
	keys.reset()
	for seat in seats:
		if seat.is_in_game:
			seat.is_active = False
			seat.set_color(seats[seat.index].color)
			seat.led_pin.value = True
		else:
			seat.set_color(FANCY_BLACK)
	while True:
		for seat in seats:
			seat.animate()
		event = keys.events.get()
		if event and event.released and seats[event.key_number].is_in_game:
			print(f"First player is {event.key_number}")
			start_player_turn(event.key_number)
			for seat in seats:
				seat.passed = False
			pressed_keys = dict()
			keys.reset()
			return

# The Eternal Loop
while True:
	if game_state != GAME_STATE_STARTED:
		start_game()

	# Detect any button presses, but don't handle them.
	detect_button_presses()

	# Check if any of the button presses should be acted on, or trimmed away.
	handle_button_presses()

	for seat in seats:
		seat.animate()
