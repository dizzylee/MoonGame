import libtcodpy as libtcod
import textwrap

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
MAP_WIDTH = 80
MAP_HEIGHT = 43
LIMIT_FPS = 20

BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

INVENTORY_WIDTH = 50

OXYGEN_AMOUNT = 20

FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 20

PLAYER_SPEED = 1
DEFAULT_SPEED = 8

#Colors
WHITE = (255, 255, 255)
color_dark_wall = libtcod.Color(80, 80, 90)
color_light_wall = libtcod.Color(110, 110, 120)
color_dark_metal1 = libtcod.Color(10, 10, 10)
color_light_metal1 = libtcod.Color(20, 20, 20)
color_dark_metal2 = libtcod.Color(30, 30, 30)
color_light_metal2 = libtcod.Color(50, 50, 50)
color_dark_ground = libtcod.Color(95, 95, 105)
color_light_ground = libtcod.Color(140, 140, 150)

libtcod.console_set_custom_font('fonts/arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'MoonGame', False)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

libtcod.sys_set_fps(LIMIT_FPS)

class Object:
	#This is a generic object: the player, an npc, an item...
	#It's always represented by a character on screen
	def __init__(self, x, y, char, color, name, blocks = False, spaceman = None, item = None, speed = DEFAULT_SPEED):
		self.x = x
		self.y = y
		self.char = char
		self.color = color
		self.name = name
		self.blocks = blocks
		self.speed = speed
		self.wait = 0

		self.spaceman = spaceman
		if self.spaceman:
			self.spaceman.owner = self
	
		self.item = item
		if self.item:
			self.item.owner = self
		

	def move(self, dx, dy):
		if(self.x + dx >= 0 and self.x + dx < MAP_WIDTH):
			if(self.y + dy >= 0 and self.y + dy < MAP_HEIGHT):
				if not is_blocked(self.x + dx, self.y + dy):
					self.x += dx
					self.y += dy
	
					self.wait = self.speed

	def draw(self):
		if libtcod.map_is_in_fov(fov_map, self.x, self.y):
			libtcod.console_set_foreground_color(con, self.color)
			libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

	def clear(self):
		libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

class Spaceman:
	def __init__(self, oxygen):
		self.max_oxygen = oxygen
		self.oxygen = oxygen

	def replenish(self, amount):
		self.oxygen += amount
		if self.oxygen > self.max_oxygen:
			self.oxygen = self.max_oxygen

class Item:
	def __init__(self, use_function = None):
		self.use_function = use_function

	def pick_up(self):
		if len(inventory) == 26:
			message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
		else:
			inventory.append(self.owner)
			objects.remove(self.owner)
			message('You picked up a ' + self.owner.name + '!', libtcod.green)

	def use(self):
		if self.use_function is None:
			message('The ' + self.owner.name + ' cannot be used.')
		else:
			if self.use_function() != 'cancelled':
				inventory.remove(self.owner)

	def drop(self):
		objects.append(self.owner)
		inventory.remove(self.owner)
		self.owner.x = player.x
		self.owner.y = player.y
		message('You dropped a ' + self.owner.name + '.', libtcod.yellow)

class Tile:
	def __init__(self, blocked, sort, block_sight = None, explored = False):
		self.blocked = blocked
		self.explored = explored
		self.sort = sort

		if block_sight is None: block_sight = blocked
		self.block_sight = block_sight

def handle_keys():
	global fov_recompute

	key = libtcod.console_check_for_keypress()
	if key.vk == libtcod.KEY_ENTER and key.lalt:
		#Alt+Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	elif key.vk == libtcod.KEY_ESCAPE:
		return 'exit' #exit game

	if game_state == 'playing':
		#if player.wait > 0:
			#player.wait -= 1
		#else:
			#Movement keys
		if libtcod.console_is_key_pressed(libtcod.KEY_UP):
			player.move(0, -1)
			fov_recompute = True
		elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
			player.move(0, 1)
			fov_recompute = True
		elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
			player.move(-1, 0)
			fov_recompute = True
		elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
			player.move(1, 0)
			fov_recompute = True
		else:
			key_char = chr(key.c)

			if key_char == 'g':
				for object in objects:
					if object.x == player.x and object.y == player.y and object.item:
						object.item.pick_up()
						break
			elif key_char == 'i':
				chosen_item = inventory_menu('Press the key next to an item to use it, or any other key to cancel\n')
				if chosen_item is not None:
					chosen_item.use()
			elif key_char == 'd':
				chosen_item = inventory_menu('Press the key next to an item to drop it, or any other key to cancel\n')
				if chosen_item is not None:
					chosen_item.drop()

def make_map():
	global map

	map = [[ Tile(False, 'floor')
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]

	map[30][22].blocked = True
	map[30][22].block_sight = True
	map[30][22].sort = 'wall'
	map[50][22].blocked = True
	map[50][22].block_sight = True
	map[50][22].sort = 'wall'

	#Lander
	for i in range(11, 20):
		map[45][i].sort = 'metal2'
	for i in range(44, 47):
		map[i][13].sort = 'metal2'
		map[i][17].sort = 'metal2'
	for i in range(43, 48):
		map[i][14].sort = 'metal2'
		map[i][16].sort = 'metal2'
	for i in range(41, 50):
		map[i][15].sort = 'metal2'

	map[45][10].sort = 'metal1'
	map[44][11].sort = 'metal1'
	map[46][11].sort = 'metal1'
	map[41][14].sort = 'metal1'
	map[49][14].sort = 'metal1'
	map[40][15].sort = 'metal1'
	map[50][15].sort = 'metal1'
	map[41][16].sort = 'metal1'
	map[49][16].sort = 'metal1'
	map[44][19].sort = 'metal1'
	map[46][19].sort = 'metal1'
	map[45][20].sort = 'metal1'

	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			map[x][y].explored = False
			if map[x][y].sort != 'floor':
				map[x][y].blocked = True
				map[x][y].block_sight = True

def render_all():
	global fov_map, color_dark_wall, color_light_wall
	global color_dark_ground, color_light_ground
	global fov_recompute

	if fov_recompute:
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			visible = libtcod.map_is_in_fov(fov_map, x, y)
			tile = map[x][y].sort
			if not visible:
				if map[x][y].explored:
					if tile == 'wall':
						libtcod.console_set_back(con, x, y, color_dark_wall, libtcod.BKGND_SET)
					elif tile == 'metal1':
						libtcod.console_set_back(con, x, y, color_dark_metal1, libtcod.BKGND_SET)
					elif tile == 'metal2':
						libtcod.console_set_back(con, x, y, color_dark_metal2, libtcod.BKGND_SET)
					else:
						libtcod.console_set_back(con, x, y, color_dark_ground, libtcod.BKGND_SET)
			else:
				if tile == 'wall':
					libtcod.console_set_back(con, x, y, color_light_wall, libtcod.BKGND_SET)
				elif tile == 'metal1':
					libtcod.console_set_back(con, x, y, color_light_metal1, libtcod.BKGND_SET)
				elif tile == 'metal2':
					libtcod.console_set_back(con, x, y, color_light_metal2, libtcod.BKGND_SET)
				else:
					libtcod.console_set_back(con, x, y, color_light_ground, libtcod.BKGND_SET)
				map[x][y].explored = True

	for object in objects:
		if object != player:
			object.draw()
	player.draw()

	libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)

	libtcod.console_set_background_color(panel, libtcod.black)
	libtcod.console_clear(panel)
	
	y = 1
	for (line, color) in game_msgs:
		libtcod.console_set_foreground_color(panel, color)
		libtcod.console_print_left(panel, MSG_X, y, libtcod.BKGND_NONE, line)
		y += 1

	render_bar(1, 1, BAR_WIDTH, 'John\'s Oxygen', player.spaceman.oxygen, player.spaceman.max_oxygen, libtcod.light_red, libtcod.darker_red)
	render_bar(1, 3, BAR_WIDTH, 'Adam\'s Oxygen', npc.spaceman.oxygen, npc.spaceman.max_oxygen, libtcod.light_magenta, libtcod.darker_magenta)

	libtcod.console_set_foreground_color(panel, libtcod.light_gray)
	libtcod.console_print_left(panel, 1, 0, libtcod.BKGND_NONE, get_names_under_mouse())

	libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

	for object in objects:
		object.clear()

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
	float_value = float(value)
	float_max = float(maximum)
	bar_width = int((float_value/float_max)*total_width)

	#bar_width = int((float(value)/maximum) * total_width)

	libtcod.console_set_background_color(panel, back_color)
	libtcod.console_rect(panel, x, y, total_width, 1, False)

	libtcod.console_set_background_color(panel, bar_color)
	if bar_width > 0:
		libtcod.console_rect(panel, x, y, bar_width, 1, False)

	libtcod.console_set_foreground_color(panel, libtcod.white)
	libtcod.console_print_center(panel, x + total_width/2, y, libtcod.BKGND_NONE, name + ': ' + str(value) + '/' + str(maximum))

def is_blocked(x, y):
	if map[x][y].blocked:
		return True

	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True

	return False

def message(new_msg, color = libtcod.white):
	global game_msgs

	new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

	for line in new_msg_lines:
		if len(game_msgs) == MSG_HEIGHT:
			del game_msgs[0]

		game_msgs.append( (line, color) )

def get_names_under_mouse():
	mouse = libtcod.mouse_get_status()
	(x, y) = (mouse.cx, mouse.cy)

	names = [obj.name for obj in objects
		if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]

	names = ', '.join(names)
	return names.capitalize()

def pop_up(text):
	width = INVENTORY_WIDTH

	header_height = libtcod.console_height_left_rect(con, 0, 0, width, SCREEN_HEIGHT, text)

	height = header_height

	window = libtcod.console_new(width, height)

	libtcod.console_set_foreground_color(window, libtcod.white)
	libtcod.console_print_left_rect(window, 0, 0, width, height, libtcod.BKGND_NONE, text)

	x = SCREEN_WIDTH/2 - width/2
	y = SCREEN_HEIGHT/2 - height/2

	libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

	libtcod.console_flush()
	key = libtcod.console_wait_for_keypress(True)

def menu(header, options, width):
	if len(options) > 16: raise ValueError('Cannot have a menu with more than 26 options.')

	header_height = libtcod.console_height_left_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
	height = len(options) + header_height

	window = libtcod.console_new(width, height)

	libtcod.console_set_foreground_color(window, libtcod.white)
	libtcod.console_print_left_rect(window, 0, 0, width, height, libtcod.BKGND_NONE, header)

	y = header_height
	letter_index = ord('a')
	for option_text in options:
		text = '(' + chr(letter_index) + ') ' + option_text
		libtcod.console_print_left(window, 0, y, libtcod.BKGND_NONE, text)
		y += 1
		letter_index += 1

	x = SCREEN_WIDTH/2 - width/2
	y = SCREEN_HEIGHT/2 - height/2

	libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

	libtcod.console_flush()
	key = libtcod.console_wait_for_keypress(True)

	index = key.c - ord('a')
	if index >= 0 and index < len(options): return index
	return None

def inventory_menu(header):
	if len(inventory) == 0:
		options = ['Inventory is empty']
	else:
		options = [item.name for item in inventory]

	index = menu(header, options, INVENTORY_WIDTH)
	if index is None or len(inventory) == 0: return None
	return inventory[index].item

def use_oxygen():
	if player.spaceman.oxygen == player.spaceman.max_oxygen:
		message('You are already at full oxygen capacity', libtcod.red)
		return 'cancelled'

	message('You replenish your oxygen tanks!', libtcod.light_violet)
	player.spaceman.replenish(OXYGEN_AMOUNT)

def main_menu():
	img = libtcod.image_load('moon.png')

	while not libtcod.console_is_window_closed():
		libtcod.image_blit_2x(img, 0, 0, 0)

		choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)

		if choice == 0:
			new_game()
			play_game()
		elif choice == 2:
			break

def new_game():
	global player, npc, inventory, game_msgs, game_state, objects

	#create object representing the player and the npc
	spaceman_component = Spaceman(80)
	player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.white, 'John', blocks=True, spaceman=spaceman_component)
	spaceman_component = Spaceman(30)
	npc = Object(SCREEN_WIDTH/2 - 5, SCREEN_HEIGHT/2, '@', libtcod.yellow, 'Adam', blocks=True, spaceman=spaceman_component)

	#create the initial objects
	item_component = Item(use_function=use_oxygen)
	item1 = Object(12, 13, '!', libtcod.violet, 'oxygen pack', item = item_component)
	item2 = Object(56, 37, '$', libtcod.orange, 'wrench', item = Item())
	item3 = Object(39, 39, '#', libtcod.blue, 'metal panel', item = Item())

	objects = [npc, player, item1, item2, item3]
	inventory = []

	game_msgs = []

	make_map()

	initialize_fov()

def initialize_fov():
	global fov_recompute, fov_map
	fov_recompute = True

	fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

def play_game():
	global game_state, adam_state
	
	game_state = 'start'
	player_action = None
	adam_state = 'alive'

	frame_counter = 0

	while not libtcod.console_is_window_closed():
		render_all()
		libtcod.console_flush()

		if game_state == 'start':
			pop_up(	'Welcome to the game.\n\n' +
					'Pressing the arrow keys will allow you to move around.' +
					'\n\nLook out for oxygen packs: \'!\'\n\n' + 
					'To pick up an oxygen pack press \'g\' while standing over it.\n\n' + 
					'To use an oxygen pack open up your inventory by pressing \'i\' ' + 
					'and then pressing the corresponding letter.\n\n' +
					'Your oxygen is already running out.\n\n' +
					'Press any key to continue\n\n' +
					'Oh, and try not to die.')
			game_state = 'playing'

		#handle keys and exit game if needed
		player_action = handle_keys()
		if player_action == 'exit':
			break

		frame_counter += 1

		if not(frame_counter%LIMIT_FPS) and game_state == 'playing':
			player.spaceman.oxygen -= 1

		if not(frame_counter%LIMIT_FPS) and adam_state == 'alive':
			npc.spaceman.oxygen -= 1

		if player.spaceman.oxygen <= 0 and game_state == 'playing':
			message('You are dead!', libtcod.red)
			game_state = 'dead'

		if npc.spaceman.oxygen <= 0 and adam_state == 'alive':
			message(npc.name + ' is dead!', libtcod.dark_magenta)
			adam_state = 'dead'

main_menu()
