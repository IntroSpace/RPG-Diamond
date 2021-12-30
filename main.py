import os
import random
import sys

import pygame
import pygame_menu

pygame.init()
WIDTH, HEIGHT = 1920, 1080
surface = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
ACC = 0.4
FRIC = -0.10
COUNT = 0
vec = pygame.math.Vector2
FPS = 60
FPS_CLOCK = pygame.time.Clock()
WORLD_VEL = 5
MAX_WORLD_VEL = 5
pygame.display.set_caption("Game")
tile_size = HEIGHT // 20
game_font = pygame.font.Font(os.path.abspath('data/fonts/pixeloid_sans.ttf'), 35)
mana_font = pygame.font.Font(os.path.abspath('data/fonts/pixeloid_sans.ttf'), tile_size)
intro_count = None
s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
player_state = None
player_mana_state = None
NON_COMFORT_ZONE = -1, -1
max_values = [0, 0]
enemies_killed = 0
results = None
prev_level_num = None

heart_files = ['death', 'onelife', 'halflife', 'almosthalflife', 'fulllife']

pick_up = pygame.mixer.Sound('data/sounds/pick_up.wav')
pick_up.set_volume(0.22)
player_regeneration = pygame.mixer.Sound('data/sounds/player_regeneration.wav')
player_regeneration.set_volume(0.13)
bat_sound = pygame.mixer.Sound('data/sounds/bats.wav')
jump_sound = pygame.mixer.Sound('data/sounds/jump.wav')
jump_sound.set_volume(0.35)
knife_attack_sound = pygame.mixer.Sound('data/sounds/knife_attack.wav')
knife_attack_sound.set_volume(0.6)
teleport_sound = pygame.mixer.Sound('data/sounds/teleport.wav')
teleport_sound.set_volume(0.8)
# step_sound = pygame.mixer.Sound('data/sounds/footsteps.wav')
pygame.mixer.music.load('data/sounds/background_music.wav')
pygame.mixer.music.play(-1)

TEXT_COLOR = pygame.Color(115, 125, 125)
END_TEXT_COLOR = 245, 245, 245
TEXT_SHIFT = game_font.render(f'Your score: 0   ©', True, TEXT_COLOR).get_width() // 1.4 + 15
MANA_COLOR = pygame.Color(49, 105, 168)

enemies = list()

# группа всех спрайтов
all_sprites = pygame.sprite.Group()
# группа блоков
tiles_group = pygame.sprite.Group()
# группа всех спрайтов, кроме игрока
other_group = pygame.sprite.Group()
# группа врагов
enemy_group = pygame.sprite.Group()
# группа для монеток
coins_group = pygame.sprite.Group()
# группа магических снарядов
fireball_group = pygame.sprite.Group()
# группа для отображения сердечек и маны
design_group = pygame.sprite.Group()


# Анимации для бега вправо
def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


run_animation_RIGHT = [load_image("Player_Sprite_R.png"), load_image("Player_Sprite2_R.png"),
                       load_image("Player_Sprite3_R.png"), load_image("Player_Sprite4_R.png"),
                       load_image("Player_Sprite5_R.png"), load_image("Player_Sprite6_R.png")]

# Анимации для бега влево
run_animation_LEFT = [load_image("Player_Sprite_L.png"), load_image("Player_Sprite2_L.png"),
                      load_image("Player_Sprite3_L.png"), load_image("Player_Sprite4_L.png"),
                      load_image("Player_Sprite5_L.png"), load_image("Player_Sprite6_L.png")]

attack_animation_RIGHT = [load_image("Player_Sprite_R.png"), load_image("Player_Attack_R.png"),
                          load_image("Player_Attack2_R.png"), load_image("Player_Attack2_R.png"),
                          load_image("Player_Attack3_R.png"), load_image("Player_Attack3_R.png"),
                          load_image("Player_Attack4_R.png"), load_image("Player_Attack4_R.png"),
                          load_image("Player_Attack5_R.png"), load_image("Player_Attack5_R.png")]
attack_animation_LEFT = [load_image("Player_Sprite_L.png"), load_image("Player_Attack_L.png"),
                         load_image("Player_Attack2_L.png"), load_image("Player_Attack2_L.png"),
                         load_image("Player_Attack3_L.png"), load_image("Player_Attack3_L.png"),
                         load_image("Player_Attack4_L.png"), load_image("Player_Attack4_L.png"),
                         load_image("Player_Attack5_L.png"), load_image("Player_Attack5_L.png")]

life_states = [[] for i in range(len(heart_files))]
for i, directory in enumerate(heart_files):
    final_dir = os.path.join('designs', directory)
    for file in os.listdir(os.path.join('data', final_dir)):
        life_states[i].append(pygame.transform.scale(load_image(os.path.join(final_dir, file)),
                                                     (0.11 * WIDTH, 0.11 / 4 * WIDTH)))


class World:
    def __init__(self, screen_size):
        self.dx = self.key_dx = 0
        self.dy = self.key_dy = 0
        width, height = screen_size
        self.borders_x = pygame.Rect(((width - height) // 2, 0, height, height))
        self.borders_y = pygame.Rect((0, tile_size * 5, width, tile_size * 11))

    def update(self, __player):
        player_rect = __player.rect
        if self.key_dx != 0:
            if __player.vel.x == __player.acc.x == 0:
                if (10 < __player.rect.x and self.key_dx < 0) \
                        or (__player.rect.x < WIDTH - (__player.rect.width + 10) and self.key_dx > 0):
                    self.dx = self.key_dx
                else:
                    self.dx = 0
                self.key_dx = 1e-10 if self.key_dx > 0 else -1e-10
            else:
                self.key_dx = 0
        else:
            if not self.borders_x.collidepoint(player_rect.topleft) \
                    and self.borders_x.x > player_rect.x:
                self.dx = min([self.borders_x.x - player_rect.x, MAX_WORLD_VEL])
            elif not self.borders_x.collidepoint(player_rect.topright) \
                    and self.borders_x.topright[0] < player_rect.topright[0]:
                self.dx = - min([player_rect.topright[0] - self.borders_x.topright[0], MAX_WORLD_VEL])
            else:
                self.dx = 0
        if not self.borders_y.collidepoint(player_rect.topleft) \
                and self.borders_y.y > player_rect.y:
            self.dy = min([self.borders_y.y - player_rect.y, MAX_WORLD_VEL])
        elif not self.borders_y.collidepoint(player_rect.bottomleft) \
                and self.borders_y.bottomleft[1] + tile_size // 2 < player_rect.bottomleft[1]:
            self.dy = - min([player_rect.bottomleft[1] - self.borders_y.bottomleft[1], MAX_WORLD_VEL])
        else:
            self.dy = 0


class Background(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.transform.scale(load_image('background.jpg'), (WIDTH, HEIGHT))
        self.bgY = 0
        self.bgX = 0
        self.rect = self.image.get_rect(topleft=(self.bgX, self.bgY))

    def render(self):
        surface.blit(self.image, (self.bgX, self.bgY))


class Ground(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(all_sprites)
        self.image = pygame.transform.scale(load_image("ground.png"), (1920, 300))
        self.rect = self.image.get_rect()
        self.rect.y = 780

    def render(self):
        surface.blit(self.image, (self.rect.x, self.rect.y))


class Tile(pygame.sprite.Sprite):
    def __init__(self, name, pos, *groups, flag=0):
        if flag == 1:
            super(Tile, self).__init__(all_sprites, tiles_group, other_group)
        else:
            super(Tile, self).__init__(all_sprites, tiles_group, *groups)
            self.image = pygame.transform.scale(load_image(name), (tile_size, tile_size))
            self.rect = self.image.get_rect(topleft=(pos[0] * tile_size, pos[1] * tile_size))


class Land(Tile):
    def __init__(self, pos, *groups):
        super(Land, self).__init__('land.png', pos, *groups)


class Stone1(Tile):
    def __init__(self, pos, *groups):
        super(Stone1, self).__init__('stone1.png', pos, *groups)


class Sand(Tile):
    def __init__(self, pos, *groups):
        super(Sand, self).__init__('sand.png', pos, *groups)


class Portal(Tile):
    def __init__(self, sheet: pygame.Surface, pos, size):
        super(Portal, self).__init__(0, 0, flag=1)
        x, y = pos
        self.row, self.col = size
        self.frames = []
        delta = int(tile_size * 0.65)
        self.rect = pygame.Rect(x * tile_size - delta * 2, y * tile_size - delta * 2, tile_size + delta * 2,
                                tile_size + delta * 2)
        self.mask = None
        self.cut_sheet(sheet)
        self.frame = None
        self.image = self.frames[self.col * 3 - 1]
        self.mask = pygame.mask.from_surface(self.image)
        self.counter = None

    def cut_sheet(self, sheet):
        size_sprite = sheet.get_width() // self.col, sheet.get_height() // self.row
        for j in range(self.row):
            for i in range(self.col):
                frame_location = (size_sprite[0] * i, size_sprite[1] * j)
                self.frames.append(pygame.transform.scale(sheet.subsurface(pygame.Rect(
                    frame_location, size_sprite)), self.rect.size))

    def open(self):
        self.frame = 1, 0
        self.image = self.frames[self.col]
        self.mask = pygame.mask.from_surface(self.image)

    def start_cycle(self):
        self.frame = 0, 0

    def close(self):
        if self.frame[0] != 2:
            self.frame = 2, 0
            self.counter = -7

    def update(self, *args, **kwargs) -> None:
        if not 0 < self.rect.centerx < WIDTH:
            return
        if self.frame is None and self.rect.width / 2 < self.rect.centerx < WIDTH - self.rect.width / 2:
            self.counter = -10
            self.open()
        elif self.frame:
            pass
        else:
            return
        row, col = self.frame
        self.counter += 1
        if self.counter == 7:
            col += 1
            self.counter = 0
        if col == self.col:
            if row == 1:
                self.start_cycle()
                row, col = self.frame
            elif row == 2:
                teleport_sound.play()
                outro_play()
        col = col % self.col
        self.frame = row, col
        self.image = self.frames[row * self.col + col]
        self.mask = pygame.mask.from_surface(self.image)


class Level:
    @staticmethod
    def new_level(data, replay=False):
        global max_values
        res_player = None
        main_portal = None
        for y, row in enumerate(data):
            for x, tile in enumerate(row):
                if tile == 'L':
                    Land((x, y), other_group)
                if tile == 'S':
                    Sand((x, y), other_group)
                if tile == 'R':
                    Stone1((x, y), other_group)
                if tile == 'P':
                    if player_state is None:
                        res_player = Player((x, y), 0 if player is None else player.score)
                    else:
                        res_player = Player((x, y), player_state)
                if tile == 'E':
                    main_portal = Portal(load_image('green_portal.png'), (x, y), (3, 8))
                if tile == 'C':
                    if not replay:
                        max_values[0] += 1
                    Coin((x, y))
                if tile == 'B':
                    if not replay:
                        max_values[1] += 1
                    enemies.append(Bat((x, y)))
                    bat_sound.stop()
                    bat_sound.play(-1)
        return res_player, main_portal


class Player(pygame.sprite.Sprite):
    def __init__(self, pos, score=0):
        super().__init__(all_sprites)
        self.image = load_image("Player_Sprite_R.png")
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.experience = 0
        # Атака
        self.attacking = False
        self.attack_frame = 0
        # Движение
        self.jumping = False
        self.running = False
        self.move_frame = 0
        # Позиция и направление
        self.vx = 0
        self.pos = vec((pos[0] * tile_size, pos[1] * tile_size))
        self.vel = vec(0, 0)
        self.acc = vec(0, 0)
        self.direction = "RIGHT"
        self.block_right = self.block_left = 0
        self.score = score
        self.heart = 4 if heart is None else heart.heart
        self.magic_cooldown = 1

    def move(self):
        sprite_list = pygame.sprite.spritecollide(self, other_group, False)
        self.block_right = self.block_left = 0
        if sprite_list:
            self.mask = pygame.mask.from_surface(self.image)
            for sprite in sprite_list:
                if isinstance(sprite, Portal):
                    if pygame.sprite.collide_mask(self, sprite):
                        sprite.close()
                    continue
                if isinstance(sprite, Coin):
                    continue
                if isinstance(sprite, Enemy):
                    if pygame.sprite.collide_mask(self, sprite):
                        self.enemy_collide(sprite)
                    continue
                rect = sprite.rect
                if not self.block_right and rect.collidepoint(self.rect.midright):
                    self.block_right = 1
                if not self.block_left and rect.collidepoint(self.rect.midleft):
                    self.block_left = 1
        self.acc = vec(0, 0.5)
        if abs(self.vel.x) > 0.5:
            self.running = True
        else:
            self.running = False
        if pygame.key.get_pressed()[pygame.K_LEFT]:
            self.acc.x = -ACC
        if pygame.key.get_pressed()[pygame.K_RIGHT]:
            self.acc.x = ACC
        if abs(self.vel.x) < 0.4:
            self.vel.x = 0
        self.acc.x += self.vel.x * FRIC
        self.vel += self.acc
        if self.block_left:
            if self.vel.x < 0 or (self.vel.x == 0 and self.acc.x < 0):
                self.acc.x = self.vel.x = 0
        if self.block_right:
            if self.vel.x > 0 or (self.vel.x == 0 and self.acc.x > 0):
                self.acc.x = self.vel.x = 0
        self.pos += self.vel + 0.5 * self.acc
        self.rect.midbottom = self.pos

    def world_shift(self, dx, dy):
        self.pos.x += dx
        self.pos.y += dy

    def update(self):
        if len(fireball_group.sprites()) == 0:
            self.magic_cooldown = 1
        if pygame.key.get_pressed()[pygame.K_SPACE]:
            self.jump()
        if pygame.key.get_pressed()[pygame.K_RETURN] and not self.attacking:
            self.attacking = True
            self.attack()
        if self.move_frame > 10:
            self.move_frame = 0
            return
        if not self.jumping and self.running:
            if self.vel.x > 0:
                self.image = run_animation_RIGHT[self.move_frame // 2]
                self.direction = "RIGHT"
            elif self.vel.x == 0:
                if self.direction == 'RIGHT':
                    self.image = run_animation_RIGHT[self.move_frame // 2]
                elif self.direction == 'LEFT':
                    self.image = run_animation_LEFT[self.move_frame // 2]
            else:
                self.image = run_animation_LEFT[self.move_frame // 2]
                self.direction = "LEFT"
            self.move_frame += 1
        if self.jumping:
            self.move_frame = 4 * 2
            if self.vel.x > 0:
                self.direction = 'RIGHT'
            if self.vel.x < 0:
                self.direction = 'LEFT'
        if abs(self.vel.x) < 1 and self.move_frame != 0:
            self.move_frame = 0
            if self.direction == "RIGHT":
                self.image = run_animation_RIGHT[self.move_frame // 2]
            elif self.direction == "LEFT":
                self.image = run_animation_LEFT[self.move_frame // 2]

    def attack(self):
        if self.attack_frame == 1:
            knife_attack_sound.play()
        if self.attack_frame > 9:
            self.attack_frame = -1
            if not pygame.key.get_pressed()[pygame.K_RETURN]:
                self.attacking = False
        if self.direction == "RIGHT":
            if self.attack_frame < 0:
                self.attack_frame = 0
            self.image = attack_animation_RIGHT[self.attack_frame]
        elif self.direction == "LEFT":
            self.correction()
            self.image = attack_animation_LEFT[self.attack_frame]
        self.attack_frame += 1

    def correction(self):
        if self.attack_frame == 1:
            self.pos.x -= 20
        if self.attack_frame == -1:
            self.attack_frame = 0
            self.pos.x += 20

    def jump(self):
        if not self.jumping:
            self.jumping = True
            self.vel.y = -12
            jump_sound.play()

    def gravity_check(self):
        if self.vel.y > 0:
            if pygame.sprite.spritecollide(player, other_group, False):
                self.mask = pygame.mask.from_surface(self.image)
                for sprite in pygame.sprite.spritecollide(player, other_group, False):
                    if isinstance(sprite, Portal):
                        if pygame.sprite.collide_mask(self, sprite):
                            sprite.close()
                        continue
                    if isinstance(sprite, Coin):
                        continue
                    if isinstance(sprite, Enemy):
                        if pygame.sprite.collide_mask(self, sprite):
                            self.enemy_collide(sprite)
                        continue
                    if sprite.rect.collidepoint(self.rect.bottomleft[0] + 5, self.rect.bottomleft[1]) \
                            or sprite.rect.collidepoint(self.rect.bottomright[0] - 5, self.rect.bottomright[1]):
                        self.pos.y = sprite.rect.top + 1
                        self.vel.y = 0
                        self.jumping = False
        elif self.vel.y < 0:
            if pygame.sprite.spritecollide(player, other_group, False):
                self.mask = pygame.mask.from_surface(self.image)
                for sprite in pygame.sprite.spritecollide(player, other_group, False):
                    if isinstance(sprite, Portal):
                        if pygame.sprite.collide_mask(self, sprite):
                            sprite.close()
                        continue
                    if isinstance(sprite, Coin):
                        continue
                    if isinstance(sprite, Enemy):
                        if pygame.sprite.collide_mask(self, sprite):
                            self.enemy_collide(sprite)
                        continue
                    if sprite.rect.collidepoint(self.rect.topleft[0] + 5, self.rect.topleft[1]) \
                            or sprite.rect.collidepoint(self.rect.topright[0] - 5, self.rect.topright[1]):
                        self.vel.y *= -1
                        self.acc.y *= -1
                        break

    def single_score(self, screen):
        text = game_font.render(f'Your score: {str(self.score).ljust(3, " ")}©', True, TEXT_COLOR)
        text_x = WIDTH - tile_size * 2 - TEXT_SHIFT
        text_y = tile_size
        screen.blit(text, (text_x, text_y))

    def add_score(self):
        self.score += 1
        pick_up.play()

    def enemy_collide(self, enemy):
        if enemy.is_killed():
            return
        if self.attacking:
            global enemies_killed
            enemies_killed += 1
            enemy.end()
        else:
            self.heart -= 1
            heart.heart -= 1
            if heart.heart >= 0:
                outro_play(replay=True)
            else:
                outro_play(end_of_game=True)

    def get_results(self):
        return self.score, enemies_killed


class Enemy(pygame.sprite.Sprite):
    def __init__(self, sheet: pygame.Surface, direction: int, velocity: int, x: int, y: int, columns: int, rows: int):
        super().__init__(all_sprites, other_group, enemy_group)
        self.frames = []
        self.direction = direction
        self.cut_sheet(sheet, columns, rows)
        self.columns = columns
        self.mana = 3
        self.frame = 0, 0
        self.image = self.frames[self.frame[0] * self.columns + self.frame[1]]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.velocity = vec(0, 0)
        self.position = vec(x, y)
        self.velocity.x = velocity
        self.count = 0
        self.delta_x = 0

    def cut_sheet(self, sheet, columns, rows):
        sprite_rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                  sheet.get_height() // rows)
        self.rect = pygame.Rect(0, 0, tile_size, tile_size)
        for j in range(rows):
            for i in range(columns):
                frame_location = (sprite_rect.w * i, sprite_rect.h * j)
                self.frames.append(pygame.transform.scale(sheet.subsurface(pygame.Rect(
                    frame_location, sprite_rect.size)), self.rect.size))

    def update(self, without_move=False):
        # Анимация врага
        if self.count == 5:
            self.count = 0
            if not without_move:
                self.move()
            self.frame = self.frame[0], self.frame[1] + 1
            self.image = self.frames[self.frame[0] * self.columns + self.frame[1]]
            if self.direction == -1:
                self.image = pygame.transform.flip(self.image, True, False)
        self.count += 1

    def move(self):
        if 2 * tile_size - (self.velocity.x - 1) // 2 <= abs(self.delta_x) \
                <= 2 * tile_size + (self.velocity.x - 1) // 2:
            self.direction = self.direction * -1
        # ИИ врага
        if self.direction == 1:
            self.position.x += self.velocity.x
            self.delta_x -= self.velocity.x
        if self.direction == -1:
            self.position.x -= self.velocity.x
            self.delta_x += self.velocity.x
        self.rect.topleft = self.position

    def world_shift(self, dx, dy):
        self.position += vec(dx, dy)


class Bat(Enemy):
    def __init__(self, pos, angry_vel=(2, 1)):
        super(Bat, self).__init__(load_image('bat_sprite.png'), 1, 5,
                                  pos[0] * tile_size, pos[1] * tile_size, 5, 3)
        self.angry_state = False
        self.angry_vel = vec(*angry_vel)
        self.start()

    def start(self):
        self.frame = 1, 0

    def end(self):
        if not self.is_killed():
            player.experience += 1
            mana.mana += self.mana
        self.frame = 2, 0
        if len(enemies) == 1:
            bat_sound.fadeout(1000)

    def is_killed(self):
        return self.frame[0] == 2

    def update(self):
        if self.frame[0] == 2:
            pass
        elif abs(self.rect.x - player.rect.x) <= NON_COMFORT_ZONE[0] \
                and abs(self.rect.y - player.rect.y) <= NON_COMFORT_ZONE[1]:
            if not self.angry_state:
                self.start_angry()
            else:
                self.angry()
        else:
            self.stop_angry()
        if self.frame[0] != 2:
            super(Bat, self).update(self.frame[0] == 0)
        else:
            if self.count == 10:
                self.frame = 2, self.frame[1] + 1
                self.image = self.frames[self.frame[0] * self.columns + self.frame[1]]
                if self.direction == -1:
                    self.image = pygame.transform.flip(self.image, True, False)
                self.count = 0
            self.count += 1
        if self.frame[1] == self.columns - 1:
            if self.frame[0] == 2:
                del enemies[enemies.index(self)]
                self.kill()
                return
            self.frame = self.frame[0], -1

    def start_angry(self):
        self.angry_state = True
        self.frame = 0, self.frame[1]

    def stop_angry(self):
        self.angry_state = False
        self.frame = 1, self.frame[1]

    def angry(self):
        if self.frame[0] == 2:
            return
        delta = (self.velocity.x - 1) // 2
        if self.rect.y - delta <= player.rect.y <= self.rect.y + delta:
            if player.attacking:
                self.position.y -= self.angry_vel.y
        elif self.rect.y < player.rect.y:
            if player.attacking:
                self.position.y -= self.angry_vel.y
            else:
                self.position.y += self.angry_vel.y
        else:
            if player.attacking:
                self.position.y += self.angry_vel.y
            else:
                self.position.y -= self.angry_vel.y
        self.rect.topleft = self.position
        if self.rect.x - delta <= player.rect.x <= self.rect.x + delta:
            if player.attacking:
                self.direction = 1
            else:
                return
        if self.rect.x < player.rect.x:
            if player.attacking:
                self.direction = -1
            else:
                self.direction = 1
        elif self.rect.x > player.rect.x:
            if player.attacking:
                self.direction = 1
            else:
                self.direction = -1
        # ИИ во время "злости"
        if self.direction == 1:
            self.position.x += self.angry_vel.x
        if self.direction == -1:
            self.position.x -= self.angry_vel.x
        self.rect.topleft = self.position


class Coin(pygame.sprite.Sprite):
    def __init__(self, pos, *other_groups):
        super(Coin, self).__init__(all_sprites, other_group, coins_group, *other_groups)
        self.frames = list()
        self.frame = 0
        self.count = 0
        self.rect = pygame.Rect((pos[0] * tile_size, pos[1] * tile_size, tile_size, tile_size))
        self.mask = None
        self.cut_sheet(load_image('coin_yellow.png'))
        self.image = self.frames[self.frame]
        self.mask = pygame.mask.from_surface(self.image)

    def cut_sheet(self, sheet):
        size_sprite = sheet.get_width() // 5, sheet.get_height()
        for i in range(5):
            frame_location = (size_sprite[0] * i, 0)
            self.frames.append(pygame.transform.scale(sheet.subsurface(pygame.Rect(
                frame_location, size_sprite)), self.rect.size))

    def update(self, *args, **kwargs):
        self.image = self.frames[self.frame]
        self.mask = pygame.mask.from_surface(self.image)
        if pygame.sprite.collide_mask(self, player):
            player.add_score()
            self.kill()
        if self.count == 7:
            self.frame = (self.frame + 1) % 5
            self.count = 0
        self.count += 1


class FireBall(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(all_sprites, fireball_group)
        self.direction = player.direction
        if self.direction == "RIGHT":
            self.image = load_image("fire_R.png")
        else:
            self.image = load_image("fire_L.png")
        self.rect = self.image.get_rect(center=player.pos)
        self.rect.x = player.pos.x
        self.rect.y = player.pos.y - 40

    def fire(self):
        player.magic_cooldown = 0
        # Запускается пока снаряд находится в рамках экрана
        if -10 < self.rect.x < WIDTH:
            if self.direction == "RIGHT":
                self.image = load_image("fire_R.png")
                surface.blit(self.image, self.rect)
            else:
                self.image = load_image("fire_L.png")
                surface.blit(self.image, self.rect)

            if self.direction == "RIGHT":
                self.rect.move_ip(12, 0)
            else:
                self.rect.move_ip(-12, 0)
        else:
            self.kill()
            player.attacking = False
            return
        if pygame.sprite.spritecollide(self, other_group, False):
            for sprite in pygame.sprite.spritecollide(self, other_group, False):
                if isinstance(sprite, Enemy):
                    sprite.end()
                if isinstance(sprite, Tile):
                    self.kill()


class Heart(pygame.sprite.Sprite):
    def __init__(self):
        super(Heart, self).__init__(all_sprites, design_group)
        self.image = life_states[-1][0]
        self.rect = self.image.get_rect(topleft=(tile_size, tile_size))
        self.heart = len(heart_files) - 1
        self.count = 0
        self.frame = -1

    def update(self):
        cur_frames = life_states[self.heart]
        self.frame = self.frame % len(cur_frames)
        if self.count == 12:
            self.frame = (self.frame + 1) % len(cur_frames)
            self.count = 0
        self.count += 1
        self.image = cur_frames[self.frame]


class Mana(pygame.sprite.Sprite):
    def __init__(self):
        super(Mana, self).__init__(all_sprites, design_group)
        text = mana_font.render(str(10), True, MANA_COLOR)
        self.image = pygame.transform.scale(load_image('designs/mana.png'),
                                            (0.027 * WIDTH, 0.027 * WIDTH))
        self.rect = self.image.get_rect(topleft=(tile_size + text.get_width(), tile_size * 2))
        self.mana = 6

    def show_score(self):
        text = mana_font.render(str(self.mana), True, MANA_COLOR)
        text_x = tile_size
        text_y = tile_size * 2
        text_w, text_h = text.get_width() * tile_size / text.get_height(), tile_size
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)), (text_x, text_y))


heart = None
mana = Mana()


def set_difficulty(value, difficulty):
    global NON_COMFORT_ZONE
    if difficulty == 0:
        NON_COMFORT_ZONE = -1, -1
    elif difficulty == 1:
        NON_COMFORT_ZONE = WIDTH * 0.3, HEIGHT * 0.5
    elif difficulty == 2:
        NON_COMFORT_ZONE = WIDTH * 0.5, HEIGHT * 0.6
    elif difficulty == 3:
        NON_COMFORT_ZONE = WIDTH * 0.75, HEIGHT * 0.8


def load_level_data(filename):
    global intro_count, prev_level_num
    replay = prev_level_num == level_num
    prev_level_num = level_num
    intro_count = 255
    with open(f'levels/{filename}.map', mode='r', encoding='utf8') as f:
        return Level.new_level(map(str.strip, f.readlines()), replay=replay)


def load_level_from_list(list_of_levels, num):
    return *load_level_data(list_of_levels[num]), num + 1


def intro_play():
    global intro_count, heart, player, player_mana_state
    if intro_count >= 255:
        player_mana_state = mana.mana
        if heart is None:
            heart = Heart()
    s.fill((10, 10, 10, intro_count))
    surface.blit(s, (0, 0))
    if intro_count == 225:
        player_regeneration.play()
    intro_count -= 2


def outro_play(replay=False, end_of_game=False):
    global player, portal, level_num, player_state, heart, mana, player_mana_state
    outro_count = 0
    while outro_count < 255:
        background.render()
        all_sprites.draw(surface)
        player.single_score(surface)
        design_group.draw(surface)
        mana.show_score()
        s.fill((10, 10, 10, outro_count))
        surface.blit(s, (0, 0))
        pygame.display.flip()
        outro_count += 2
    if replay:
        level_num -= 1
        mana.mana = player_mana_state
    for sprite in all_sprites.sprites():
        if isinstance(sprite, Heart) and sprite.heart >= 0:
            continue
        if isinstance(sprite, Mana):
            continue
        sprite.kill()
    enemies.clear()
    bat_sound.stop()
    if level_num < len(levels) and not end_of_game:
        if not replay:
            player_state = None
        player, portal, level_num = load_level_from_list(levels, level_num)
    else:
        save_results()
        player = None
    player_state = player.score


def save_results():
    global results
    results = player.get_results()


def end_the_game():
    pressed = False
    counter, direction = 255, -1
    while not pressed:
        surface.fill((45, 40, 40))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                return
        center_x = WIDTH // 2
        center_y = HEIGHT // 2
        text = mana_font.render(f'{max(heart.heart, 0)} of {len(life_states) - 1} lifes',
                                True, END_TEXT_COLOR)
        text_h = HEIGHT * 0.049
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, center_y - text_h * 3))

        text = mana_font.render(f'{results[0]} of {max_values[0]} coins', True, END_TEXT_COLOR)
        text_h = HEIGHT * 0.048
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, center_y - text_h * 2))

        text = mana_font.render(f'{results[1]} of {max_values[1]} enemies', True, END_TEXT_COLOR)
        text_h = HEIGHT * 0.046
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, center_y - text_h))
        text = mana_font.render(f'{level_num} of {len(levels)} levels', True, END_TEXT_COLOR)
        text_h = HEIGHT * 0.044
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, center_y))

        text = mana_font.render(f'Press any key to continue...',
                                True, pygame.Color(*END_TEXT_COLOR, counter))
        text_h = HEIGHT * 0.052
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, HEIGHT * 0.94 - text_h))

        counter += direction
        if counter in [0, 255]:
            direction *= -1
        pygame.display.flip()
        FPS_CLOCK.tick(FPS)


world = level_num = player = portal = None
background = Background()
levels = ['level1', 'level2', 'level3']


# skeleton = Enemy(load_image("SkeletonEnemyMove.png"), 0, 3, 100, 100, 12, 1)


def start_the_game():
    global world, level_num, player, portal, player_state, mana,\
        heart, player_mana_state, max_values, enemies_killed, prev_level_num
    world = World((WIDTH, HEIGHT - 100))
    prev_level_num = -1
    level_num = 0
    heart = Heart()
    mana = Mana()
    player_mana_state = mana.mana
    max_values = [0, 0]
    enemies_killed = 0
    player, portal, level_num = load_level_from_list(levels, level_num)
    player_state = player.score
    running = True
    try:
        while running:
            coins_group.update()
            player.gravity_check()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if not player.attacking:
                            player.attack()
                            player.attacking = True
                    if event.button == 3:
                        if mana.mana >= 6 and player.magic_cooldown:
                            mana.mana -= 6
                            player.attacking = True
                            FireBall()
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                running = False
                break
            if keys[pygame.K_DELETE]:
                world.key_dx = WORLD_VEL
            if keys[pygame.K_PAGEDOWN]:
                world.key_dx = - WORLD_VEL
            surface.fill((0, 0, 0))
            player.update()
            if player.attacking:
                player.attack()
            player.move()
            background.render()
            for ball in fireball_group:
                ball.fire()
            enemy_group.update()
            world.update(player)
            if world.dx != 0 or world.dy != 0:
                player.world_shift(world.dx, world.dy)
                for enemy in enemies:
                    enemy.world_shift(world.dx, world.dy)
                for sprite in all_sprites.sprites():
                    if design_group.has(sprite):
                        continue
                    sprite.rect = sprite.rect.move(world.dx, world.dy)
            other_group.draw(surface)
            enemy_group.draw(surface)
            portal.update()
            player.single_score(surface)
            design_group.update()
            design_group.draw(surface)
            mana.show_score()
            surface.blit(player.image, player.rect)
            if intro_count > 0:
                intro_play()
            pygame.display.flip()
            FPS_CLOCK.tick(FPS)
    except AttributeError:
        FPS_CLOCK.tick(0.5)
        end_the_game()


menu = pygame_menu.Menu('Welcome', WIDTH, HEIGHT,
                        theme=pygame_menu.themes.THEME_DARK)

menu.add.text_input('Name: ', default='Player')
menu.add.selector('Difficulty: ', [('Very Easy', 0), ('Easy', 1), ('Medium', 2), ('Hard', 3)],
                  onchange=set_difficulty)
menu.add.button('Play', start_the_game)
menu.add.button('Quit', pygame_menu.events.EXIT)
menu.mainloop(surface)
