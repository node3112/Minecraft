from pyglet.gl import *
from pyglet.window import key
import math
import random
import time
import argparse
import os
import cPickle as pickle
from blocks import *
from items import *
from inventory import *
from entity import *

SECTOR_SIZE = 16
DRAW_DISTANCE = 60.0
FOV = 65.0 #TODO add menu option to change FOV
NEAR_CLIP_DISTANCE = 0.1 #TODO make min and max clip distance dynamic
FAR_CLIP_DISTANCE = 200.0 # Maximum render distance, ignoring effects of sector_size and fog
WORLDTYPE = 0 #1=grass,2=dirt,3=sand,4=islands
HILLHEIGHT = 6  #height of the hills, increase for mountains :D
FLATWORLD=0  # dont make mountains,  make a flat world
SAVE_FILENAME = 'save.dat'
DISABLE_SAVE = True

def cube_vertices(x, y, z, n):
    return [
        x-n,y+n,z-n, x-n,y+n,z+n, x+n,y+n,z+n, x+n,y+n,z-n, # top
        x-n,y-n,z-n, x+n,y-n,z-n, x+n,y-n,z+n, x-n,y-n,z+n, # bottom
        x-n,y-n,z-n, x-n,y-n,z+n, x-n,y+n,z+n, x-n,y+n,z-n, # left
        x+n,y-n,z+n, x+n,y-n,z-n, x+n,y+n,z-n, x+n,y+n,z+n, # right
        x-n,y-n,z+n, x+n,y-n,z+n, x+n,y+n,z+n, x-n,y+n,z+n, # front
        x+n,y-n,z-n, x-n,y-n,z-n, x-n,y+n,z-n, x+n,y+n,z-n, # back
    ]

FACES = [
    ( 0, 1, 0),
    ( 0,-1, 0),
    (-1, 0, 0),
    ( 1, 0, 0),
    ( 0, 0, 1),
    ( 0, 0,-1),
]

class TextureGroup(pyglet.graphics.Group):
    def __init__(self, path):
        super(TextureGroup, self).__init__()
        self.texture = pyglet.image.load(path).get_texture()
    def set_state(self):
        glEnable(self.texture.target)
        glBindTexture(self.texture.target, self.texture.id)
    def unset_state(self):
        glDisable(self.texture.target)

def normalize(position):
    x, y, z = position
    x, y, z = (int(round(x)), int(round(y)), int(round(z)))
    return (x, y, z)

def sectorize(position):
    x, y, z = normalize(position)
    x, y, z = x / SECTOR_SIZE, y / SECTOR_SIZE, z / SECTOR_SIZE
    return (x, 0, z)

class Player(Entity):
    def __init__(self, position, rotation, flying = False):
        super(Player, self).__init__(position, rotation, health = 20)
        self.inventory = Inventory(27)
        self.quick_slots = Inventory(9)
        self.flying = flying
        initial_items = [dirt_block, sand_block, brick_block, stone_block, glass_block, water_block, chest_block, sandstone_block, marble_block]
        
        for item in initial_items:
            quantity = random.randint(1, 10)
            if FLATWORLD == 1:
                self.quick_slots.add_item(item.id(), 99)
            if FLATWORLD == 0:
                self.quick_slots.add_item(item.id(), quantity)

    def add_item(self, item_id):
        if self.quick_slots.add_item(item_id):
            return True
        elif self.inventory.add_item(item_id):
            return True
        return False

class ItemSelector(object):
    def __init__(self, width, height, player, model):
        self.batch = pyglet.graphics.Batch()
        self.group = pyglet.graphics.OrderedGroup(1)
        self.amount_labels_group = pyglet.graphics.OrderedGroup(2)
        self.amount_labels = []
        self.model = model
        self.player = player
        self.max_items = 9
        self.current_index = 1
        self.icon_size = self.model.group.texture.width / 8 #4

        image = pyglet.image.load('slots.png')
        frame_size = image.height / 2
        self.frame = pyglet.sprite.Sprite(image.get_region(0, frame_size, image.width, frame_size), batch=self.batch, group=pyglet.graphics.OrderedGroup(0))
        self.active = pyglet.sprite.Sprite(image.get_region(0, 0, frame_size, frame_size), batch=self.batch, group=pyglet.graphics.OrderedGroup(2))
        self.set_position(width, height)
        
    def change_index(self, change):
        self.set_index(self.current_index + change)
            
    def set_index(self, index):
        index = int(index)
        if self.current_index == index:
            return
        self.current_index = index
        if self.current_index >= self.max_items:
            self.current_index = 0
        elif self.current_index < 0:
            self.current_index = self.max_items - 1;
        self.update_current()
            
    def update_items(self):
        self.icons = []
        for amount_label in self.amount_labels:
            amount_label.delete()
        self.amount_labels = []
        x = self.frame.x + 3
        items = self.player.quick_slots.get_items()
        items = items[:self.max_items]
        for item in items:
            if not item:
                x += (self.icon_size * 0.5) + 3
                continue
            block = BLOCKS_DIR[item.type]
            #block_icon = self.model.group.texture.get_region(int(block.side[0] * 4) * self.icon_size, int(block.side[1] * 4) * self.icon_size, self.icon_size, self.icon_size)
            block_icon = self.model.group.texture.get_region(int(block.side[0] * 8) * self.icon_size, int(block.side[1] * 8) * self.icon_size, self.icon_size, self.icon_size)
            icon = pyglet.sprite.Sprite(block_icon, batch=self.batch, group=self.group)
            icon.scale = 0.5
            icon.x = x
            icon.y = self.frame.y + 3
            x += (self.icon_size * 0.5) + 3
            amount_label = pyglet.text.Label(str(item.amount), font_name='Arial', font_size=9, 
                x=icon.x + 3, y=icon.y, anchor_x='left', anchor_y='bottom', 
                color=(block.amount_label_color), batch=self.batch, group=self.amount_labels_group)
            self.amount_labels.append(amount_label)
            self.icons.append(icon)
        
    def update_current(self):
        self.active.x = self.frame.x + (self.current_index * 35);
        
    def set_position(self, width, height):
        self.frame.x = (width - self.frame.width) / 2
        self.frame.y = self.icon_size * 0.5
        self.active.y = self.frame.y            
        self.update_current()
        self.update_items()

    def get_current_block(self):
        item = self.player.quick_slots.at(self.current_index)
        if item:
            item_id = item.type
            self.player.quick_slots.remove_item(item_id)
            self.update_items()
            if item_id >= ITEM_ID_MIN:
                return ITEMS_DIR[item_id]
            else:
                return BLOCKS_DIR[item_id]
        return False

class Model(object):
    def __init__(self, initialize=True):
        self.batch = pyglet.graphics.Batch()
        self.group = TextureGroup('texture.png')
        self.world = {}
        self.shown = {}
        self._shown = {}
        self.sectors = {}
        self.queue = []
        if initialize:
            self.initialize()
    def initialize(self):
        n = 80
        s = 1
        y = 0
        for x in xrange(-n, n + 1, s):
            for z in xrange(-n, n + 1, s):
                if WORLDTYPE == 0:
                    self.init_block((x, y - 2, z), grass_block)
                if WORLDTYPE == 1:
                    self.init_block((x, y - 2, z), dirt_block)
                if WORLDTYPE == 2:
                    self.init_block((x, y - 2, z), sand_block)
                if WORLDTYPE == 3:
                    self.init_block((x, y - 2, z), water_block)
                if WORLDTYPE == 4:
                    self.init_block((x, y - 2, z), grass_block)
                #self.init_block((x, y - 2, z), water_block)
                self.init_block((x, y - 3, z), dirt_block)
                self.init_block((x, y - 4, z), bed_block) # was stone_block
                if x in (-n, n) or z in (-n, n):
                    for dy in xrange(-3, 10): #was -2 ,6
                        self.init_block((x, y + dy, z), stone_block)
        o = n - 10
        if HILLHEIGHT > 6:
            o = n - 10 + HILLHEIGHT / 2
        if FLATWORLD == 1:
            return
        for _ in xrange(120):
            a = random.randint(-o, o)
            b = random.randint(-o, o)
            c = -1
            h = random.randint(1, HILLHEIGHT)
            s = random.randint(4, HILLHEIGHT + 2)
            d = 1
            if WORLDTYPE == 0:
                t = random.choice([grass_block]) # removed brick_block
            if WORLDTYPE == 1:
                t = random.choice([dirt_block]) # removed brick_block
            if WORLDTYPE == 2:
                t = random.choice([sand_block]) # removed brick_block
            if WORLDTYPE == 3:
                t = random.choice([grass_block, sand_block]) # removed brick_block
            if WORLDTYPE == 4:
                t = random.choice([grass_block, sand_block, dirt_block]) # removed brick_block
            for y in xrange(c, c + h):
                for x in xrange(a - s, a + s + 1):
                    for z in xrange(b - s, b + s + 1):
                        if (x - a) ** 2 + (z - b) ** 2 > (s + 1) ** 2:
                            continue
                        if (x - 0) ** 2 + (z - 0) ** 2 < 5 ** 2:
                            continue
                        self.init_block((x, y, z), t)
                s -= d

    def hit_test(self, position, vector, max_distance=8):
        m = 8
        x, y, z = position
        dx, dy, dz = vector
        previous = None
        for _ in xrange(max_distance * m):
            key = normalize((x, y, z))
            if key != previous and key in self.world:
                return key, previous
            previous = key
            x, y, z = x + dx / m, y + dy / m, z + dz / m
        return None, None
    def exposed(self, position):
        x, y, z = position
        for dx, dy, dz in FACES:
            if (x + dx, y + dy, z + dz) not in self.world:
                return True
        return False
    def init_block(self, position, block):
        self.add_block(position, block, False)
    def add_block(self, position, block, sync=True):
        if position in self.world:
            self.remove_block(position, sync)
        self.world[position] = block
        self.sectors.setdefault(sectorize(position), []).append(position)
        if sync:
            if self.exposed(position):
                self.show_block(position)
            self.check_neighbors(position)
    def remove_block(self, position, sync=True):
        del self.world[position]
        self.sectors[sectorize(position)].remove(position)
        if sync:
            if position in self.shown:
                self.hide_block(position)
            self.check_neighbors(position)
    def check_neighbors(self, position):
        x, y, z = position
        for dx, dy, dz in FACES:
            key = (x + dx, y + dy, z + dz)
            if key not in self.world:
                continue
            if self.exposed(key):
                if key not in self.shown:
                    self.show_block(key)
            else:
                if key in self.shown:
                    self.hide_block(key)
    def show_blocks(self):
        for position in self.world:
            if position not in self.shown and self.exposed(position):
                self.show_block(position)
    def show_block(self, position, immediate=True):
        block = self.world[position]
        self.shown[position] = block
        if immediate:
            self._show_block(position, block)
        else:
            self.enqueue(self._show_block, position, block)
    def _show_block(self, position, block):
        x, y, z = position
        # only show exposed faces
        index = 0
        count = 24
        vertex_data = cube_vertices(x, y, z, 0.5)
        texture_data = block_texture(block)
        for dx, dy, dz in []:#FACES:
            if (x + dx, y + dy, z + dz) in self.world:
                count -= 8 #4
                i = index * 12
                j = index * 8
                del vertex_data[i:i + 12]
                del texture_data[j:j + 8]
            else:
                index += 1
        # create vertex list
        self._shown[position] = self.batch.add(count, GL_QUADS, self.group,
            ('v3f/static', vertex_data),
            ('t2f/static', texture_data))
    def hide_block(self, position, immediate=True):
        self.shown.pop(position)
        if immediate:
            self._hide_block(position)
        else:
            self.enqueue(self._hide_block, position)
    def _hide_block(self, position):
        self._shown.pop(position).delete()
    def show_sector(self, sector):
        for position in self.sectors.get(sector, []):
            if position not in self.shown and self.exposed(position):
                self.show_block(position, False)
    def hide_sector(self, sector):
        for position in self.sectors.get(sector, []):
            if position in self.shown:
                self.hide_block(position, False)
    def change_sectors(self, before, after):
        before_set = set()
        after_set = set()
        pad = 4
        for dx in xrange(-pad, pad + 1):
            for dy in [0]: # xrange(-pad, pad + 1):
                for dz in xrange(-pad, pad + 1):
                    if dx ** 2 + dy ** 2 + dz ** 2 > (pad + 1) ** 2:
                        continue
                    if before:
                        x, y, z = before
                        before_set.add((x + dx, y + dy, z + dz))
                    if after:
                        x, y, z = after
                        after_set.add((x + dx, y + dy, z + dz))
        show = after_set - before_set
        hide = before_set - after_set
        for sector in show:
            self.show_sector(sector)
        for sector in hide:
            self.hide_sector(sector)
    def enqueue(self, func, *args):
        self.queue.append((func, args))
    def dequeue(self):
        func, args = self.queue.pop(0)
        func(*args)
    def process_queue(self):
        start = time.clock()
        while self.queue and time.clock() - start < 1 / 60.0:
            self.dequeue()
    def process_entire_queue(self):
        while self.queue:
            self.dequeue()

class Window(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        self.show_gui = kwargs.pop('show_gui', True)
        if 'save' in kwargs and kwargs['save'] != None:
            self.save = kwargs['save']
        else:
            self.save = None
        del kwargs['save']
        super(Window, self).__init__(*args, **kwargs)
        self.exclusive = False
        self.strafe = [0, 0]
        self.sector = None
        self.reticle = None
        self.dy = 0
        save_len = -1 if self.save == None else len(self.save)
        if self.save == None or save_len < 2: # Model.world and model.sectors
            self.model = Model()
            self.player = Player((0, 0, 0), (-20, 0))
        else:
            self.model = Model(initialize=False)
            self.model.world = self.save[0]
            self.model.sectors = self.save[1]
            if save_len > 2 and isinstance(self.save[2], list) and len(self.save[2]) == 2: self.strafe = self.save[2]
            if save_len > 3 and isinstance(self.save[3], Player): self.player = self.save[3]
        self.item_list = ItemSelector(self.width, self.height, self.player, self.model)
        self.num_keys = [
            key._1, key._2, key._3, key._4, key._5,
            key._6, key._7, key._8, key._9, key._0]
        if self.show_gui:
            self.label = pyglet.text.Label('', font_name='Arial', font_size=8,
                x=10, y=self.height - 10, anchor_x='left', anchor_y='top',
                color=(0, 0, 0, 255))
        pyglet.clock.schedule_interval(self.update, 1.0 / 60)
    def set_exclusive_mouse(self, exclusive):
        super(Window, self).set_exclusive_mouse(exclusive)
        self.exclusive = exclusive
    def get_sight_vector(self):
        x, y = self.player.rotation
        m = math.cos(math.radians(y))
        dy = math.sin(math.radians(y))
        dx = math.cos(math.radians(x - 90)) * m
        dz = math.sin(math.radians(x - 90)) * m
        return (dx, dy, dz)
    def get_motion_vector(self):
        if any(self.strafe):
            x, y = self.player.rotation
            strafe = math.degrees(math.atan2(*self.strafe))
            if self.player.flying:
                m = math.cos(math.radians(y))
                dy = math.sin(math.radians(y))
                if self.strafe[1]:
                    dy = 0.0
                    m = 1
                if self.strafe[0] > 0:
                    dy *= -1
                dx = math.cos(math.radians(x + strafe)) * m
                dz = math.sin(math.radians(x + strafe)) * m
            else:
                dy = 0.0
                dx = math.cos(math.radians(x + strafe))
                dz = math.sin(math.radians(x + strafe))
        else:
            dy = 0.0
            dx = 0.0
            dz = 0.0
        return (dx, dy, dz)

    def update(self, dt):
        self.model.process_queue()
        sector = sectorize(self.player.position)
        if sector != self.sector:
            self.model.change_sectors(self.sector, sector)
            if self.sector is None:
                self.model.process_entire_queue()
            self.sector = sector
        m = 8
        dt = min(dt, 0.2)
        for _ in xrange(m):
            self._update(dt / m)
    def _update(self, dt):
        # walking
        speed = 15 if self.player.flying else 5
        d = dt * speed
        dx, dy, dz = self.get_motion_vector()
        dx, dy, dz = dx * d, dy * d, dz * d
        # gravity
        if not self.player.flying:
            self.dy -= dt * 0.022 # g force, should be = jump_speed * 0.5 / max_jump_height
            self.dy = max(self.dy, -0.5) # terminal velocity
            dy += self.dy
        else:
            self.dy = max(self.dy, -0.5) # terminal velocity
            dy += self.dy
        # collisions
        x, y, z = self.player.position
        x, y, z = self.collide((x + dx, y + dy, z + dz), 2)
        self.player.position = (x, y, z)

    def save_to_file(self):
        if DISABLE_SAVE:
            pickle.dump((self.model.world, self.model.sectors, self.strafe, self.player), open(SAVE_FILENAME, "wb"))

    def collide(self, position, height):
        pad = 0.25
        p = list(position)
        np = normalize(position)
        for face in FACES: # check all surrounding blocks
            for i in xrange(3): # check each dimension independently
                if not face[i]:
                    continue
                d = (p[i] - np[i]) * face[i]
                if d < pad:
                    continue
                for dy in xrange(height): # check each height
                    op = list(np)
                    op[1] -= dy
                    op[i] += face[i]
                    op = tuple(op)
                    if op not in self.model.world:
                        continue
                    p[i] -= (d - pad) * face[i]
                    if face == (0, -1, 0) or face == (0, 1, 0):
                        self.dy = 0
                    break
        return tuple(p)
        
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.exclusive and scroll_y != 0:
            self.item_list.change_index(scroll_y*-1)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.exclusive:
            vector = self.get_sight_vector()
            block, previous = self.model.hit_test(self.player.position, vector)
            if button == pyglet.window.mouse.LEFT:
                if block:
                    hit_block = self.model.world[block]
                    if hit_block != bed_block:
                        self.model.remove_block(block)
                        if self.player.add_item(hit_block.drop()):
                            self.item_list.update_items()
            else:
                if previous:
                    current_block = self.item_list.get_current_block()
                    if current_block:
                        # if current block is an item, call its on_right_click() method to handle this event
                        if current_block.id() >= ITEM_ID_MIN:
                            current_block.on_right_click()
                        else:
                            self.model.add_block(previous, current_block)
        else:
            self.set_exclusive_mouse(True)
            
    def on_mouse_motion(self, x, y, dx, dy):
        if self.exclusive:
            m = 0.15
            x, y = self.player.rotation
            x, y = x + dx * m, y + dy * m
            y = max(-90, min(90, y))
            self.player.rotation = (x, y)
    def on_key_press(self, symbol, modifiers):
        if symbol == key.W:
            self.strafe[0] -= 1
        elif symbol == key.S:
            self.strafe[0] += 1
        elif symbol == key.A:
            self.strafe[1] -= 1
        elif symbol == key.D:
            self.strafe[1] += 1
        elif symbol == key.SPACE:
            if self.player.flying:
                self.dy = 0.045 # jump speed
            elif self.dy == 0:
                self.dy = 0.015 # jump speed
        elif symbol == key.LSHIFT or symbol == key.RSHIFT:
            if self.player.flying:
                self.dy = -0.045 # inversed jump speed
        elif symbol == key.ESCAPE:
            self.set_exclusive_mouse(False)
        elif symbol == key.TAB:
            self.player.flying = not self.player.flying
        elif symbol == key.B or symbol == key.F3:
            self.show_gui = not self.show_gui
        elif symbol in self.num_keys:
            index = (symbol - self.num_keys[0])
            self.item_list.set_index(index)
        elif symbol == key.V:
            self.save_to_file()
        elif symbol == key.M:
            self.player.quick_slots.change_sort_mode()
            self.item_list.update_items()

    def on_key_release(self, symbol, modifiers):
        if symbol == key.W:
            self.strafe[0] += 1
        elif symbol == key.S:
            self.strafe[0] -= 1
        elif symbol == key.A:
            self.strafe[1] += 1
        elif symbol == key.D:
            self.strafe[1] -= 1
        elif (symbol == key.SPACE or symbol == key.LSHIFT or symbol == key.RSHIFT) and self.player.flying:
            self.dy = 0
        elif symbol == key.M:
            self.player.quick_slots.change_sort_mode()
            self.item_list.update_items()
    def on_resize(self, width, height):
        # label
        # reticle
        if self.reticle:
            self.reticle.delete()
        x, y = self.width / 2, self.height / 2
        n = 10
        self.reticle = pyglet.graphics.vertex_list(4,
            ('v2i', (x - n, y, x + n, y, x, y - n, x, y + n))
        )
        if self.show_gui:
            self.label.y = height - 10
            self.item_list.set_position(width, height)

    def set_2d(self):
        width, height = self.get_size()
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if width != 0:
            glOrtho(0, width, 0, height, -1, 1)
        else:
            glOrtho(0, 1, 0, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
    def set_3d(self):
        width, height = self.get_size()
        glEnable(GL_DEPTH_TEST)
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if width != float(height):
            gluPerspective(FOV, width / float(height), NEAR_CLIP_DISTANCE, FAR_CLIP_DISTANCE)
        else:
            gluPerspective(FOV, 1, NEAR_CLIP_DISTANCE, FAR_CLIP_DISTANCE)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        x, y = self.player.rotation
        glRotatef(x, 0, 1, 0)
        glRotatef(-y, math.cos(math.radians(x)), 0, math.sin(math.radians(x)))
        x, y, z = self.player.position
        glTranslatef(-x, -y, -z)
    def on_draw(self):
        self.clear()
        self.set_3d()
        glColor3d(1, 1, 1)
        self.model.batch.draw()
        self.draw_focused_block()
        self.set_2d()
        if self.show_gui:
            self.draw_label()
            self.item_list.batch.draw()
        self.draw_reticle()
    def draw_focused_block(self):
        vector = self.get_sight_vector()
        block = self.model.hit_test(self.player.position, vector)[0]
        if block:
            x, y, z = block
            vertex_data = cube_vertices(x, y, z, 0.51)
            glColor3d(0, 0, 0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            pyglet.graphics.draw(24, GL_QUADS, ('v3f/static', vertex_data))
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    def draw_label(self):
        x, y, z = self.player.position
        self.label.text = '%02d (%.2f, %.2f, %.2f) %d / %d' % (
            pyglet.clock.get_fps(), x, y, z,
            len(self.model._shown), len(self.model.world))
        self.label.draw()
    def draw_reticle(self):
        glColor3d(0, 0, 0)
        self.reticle.draw(GL_LINES)

def setup_fog():
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.5, 0.69, 1.0, 1))
    glHint(GL_FOG_HINT, GL_DONT_CARE)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_DENSITY, 0.35)
    glFogf(GL_FOG_START, 20.0)
    glFogf(GL_FOG_END, 80)

def setup():
    glClearColor(0.5, 0.69, 1.0, 1)
    glEnable(GL_CULL_FACE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

def main(options):
    save_object = None
    global SAVE_FILENAME
    global DISABLE_SAVE    
    SAVE_FILENAME = options.save
    DISABLE_SAVE = options.disable_save
    if os.path.exists(SAVE_FILENAME) and options.disable_save:
        save_object = pickle.load(open(SAVE_FILENAME, "rb"))
    if options.draw_distance == 'medium':
        DRAW_DISTANCE = 60.0 * 1.5
    elif options.draw_distance == 'long':
        DRAW_DISTANCE = 60.0 * 2.0
    global WORLDTYPE
    WORLDTYPE = options.terrain
    global HILLHEIGHT
    HILLHEIGHT = options.hillheight
    global FLATWORLD
    FLATWORLD = options.flat

    #try:
        #config = Config(sample_buffers=1, samples=4) #, depth_size=8)  #, double_buffer=True) #TODO Break anti-aliasing/multisampling into an explicit menu option
        #window = Window(show_gui=options.show_gui, width=options.width, height=options.height, caption='pyCraftr', resizable=True, config=config, save=save_object)
    #except pyglet.window.NoSuchConfigException:
    window = Window( width=options.width, height=options.height, caption='pyCraftr_No-Conf', resizable=True, save=save_object)
    
    window.set_exclusive_mouse(True)
    setup()
    if not options.hide_fog:
        setup_fog()
    pyglet.app.run()
    if options.disable_auto_save and options.disable_save:
        window.save_to_file()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-width", type=int, default=850)
    parser.add_argument("-height", type=int, default=480)
    parser.add_argument("-terrain", type=int, default=0)
    parser.add_argument("-hillheight", type=int, default=6)
    parser.add_argument("-flat", type=int, default=0)
    parser.add_argument("--hide-fog", action="store_true", default=False)
    parser.add_argument("--show-gui", action="store_true", default=True)
    parser.add_argument("--disable-auto-save", action="store_false", default=True)
    parser.add_argument("-draw-distance", choices=['short', 'medium', 'long'], default='short')
    parser.add_argument("-save", type=unicode, default=SAVE_FILENAME)
    parser.add_argument("--disable-save", action="store_false", default=True)
    options = parser.parse_args()
    main(options)
