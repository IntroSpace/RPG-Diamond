import os
import sys

import pygame
import pygame_menu

pygame.init()
WIDTH, HEIGHT = 1920, 1080
surface = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.key.set_repeat(1, 20)
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
intro_count = None
s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

TEXT_COLOR = pygame.Color(115, 125, 125)
TEXT_SHIFT = game_font.render(f'Your score: 0   ©', True, TEXT_COLOR).get_width() // 1.4 + 15

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
                          load_image("Player_Attack5_R.png"), load_image("Player_Attack5_R.png"),
                          load_image("Player_Sprite_R.png")]
attack_animation_LEFT = [load_image("Player_Sprite_L.png"), load_image("Player_Attack_L.png"),
                         load_image("Player_Attack2_L.png"), load_image("Player_Attack2_L.png"),
                         load_image("Player_Attack3_L.png"), load_image("Player_Attack3_L.png"),
                         load_image("Player_Attack4_L.png"), load_image("Player_Attack4_L.png"),
                         load_image("Player_Attack5_L.png"), load_image("Player_Attack5_L.png"),
                         load_image("Player_Sprite_L.png")]


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
                outro_play()
        col = col % self.col
        self.frame = row, col
        self.image = self.frames[row * self.col + col]
        self.mask = pygame.mask.from_surface(self.image)


class Level:
    @staticmethod
    def new_level(data):
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
                    res_player = Player((x, y), 0 if player is None else player.score)
                if tile == 'E':
                    main_portal = Portal(load_image('green_portal.png'), (x, y), (3, 8))
                if tile == 'C':
                    Coin((x, y))
                if tile == 'B':
                    enemies.append(Bat((x, y)))
        return res_player, main_portal


class Player(pygame.sprite.Sprite):
    def __init__(self, pos, score=0):
        super().__init__(all_sprites)
        self.image = load_image("Player_Sprite_R.png")
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
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

    def move(self):
        sprite_list = pygame.sprite.spritecollide(self, other_group, False)
        self.block_right = self.block_left = 0
        if sprite_list:
            for sprite in sprite_list:
                if isinstance(sprite, Portal):
                    if pygame.sprite.collide_mask(self, sprite):
                        sprite.close()
                    continue
                if isinstance(sprite, Coin):
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
        if pygame.key.get_pressed()[pygame.K_SPACE]:
            self.jump()
        if pygame.key.get_pressed()[pygame.K_RETURN] and not self.attacking:
            self.attack()
            self.attacking = True
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
        if self.attack_frame > 10:
            self.attack_frame = 0
            self.attacking = False
        if self.direction == "RIGHT":
            self.image = attack_animation_RIGHT[self.attack_frame]
        elif self.direction == "LEFT":
            self.correction()
            self.image = attack_animation_LEFT[self.attack_frame]
        self.attack_frame += 1

    def correction(self):
        ...
        # if self.attack_frame == 1:
        #     self.pos.x -= 20
        # if self.attack_frame == 10:
        #     self.pos.x += 20

    def jump(self):
        if not self.jumping:
            self.jumping = True
            self.vel.y = -12

    def gravity_check(self):
        if self.vel.y > 0:
            if pygame.sprite.spritecollide(player, other_group, False):
                sprites = pygame.sprite.spritecollide(player, other_group, False)
                for sprite in sprites:
                    if isinstance(sprite, Portal):
                        if pygame.sprite.collide_mask(self, sprite):
                            sprite.close()
                        continue
                    if isinstance(sprite, Coin):
                        continue
                    if sprite.rect.collidepoint(self.rect.bottomleft[0] + 5, self.rect.bottomleft[1]) \
                            or sprite.rect.collidepoint(self.rect.bottomright[0] - 5, self.rect.bottomright[1]):
                        self.pos.y = sprite.rect.top + 1
                        self.vel.y = 0
                        self.jumping = False
        elif self.vel.y < 0:
            if pygame.sprite.spritecollide(player, other_group, False):
                for sprite in pygame.sprite.spritecollide(player, other_group, False):
                    if isinstance(sprite, Portal):
                        if pygame.sprite.collide_mask(self, sprite):
                            sprite.close()
                        continue
                    if isinstance(sprite, Coin):
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


class Enemy(pygame.sprite.Sprite):
    def __init__(self, sheet: pygame.Surface, direction: int, velocity: int, x: int, y: int, columns: int, rows: int):
        super().__init__(all_sprites, other_group, enemy_group)
        self.frames = []
        self.direction = direction
        self.cut_sheet(sheet, columns, rows)
        self.columns = columns
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.velocity = vec(0, 0)
        self.position = vec(x, y)
        self.velocity.x = velocity
        self.count = 0

    def cut_sheet(self, sheet, columns, rows):
        sprite_rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                  sheet.get_height() // rows)
        self.rect = pygame.Rect(0, 0, tile_size, tile_size)
        for j in range(rows):
            for i in range(columns):
                frame_location = (sprite_rect.w * i, sprite_rect.h * j)
                self.frames.append(pygame.transform.scale(sheet.subsurface(pygame.Rect(
                    frame_location, sprite_rect.size)), self.rect.size))

    def update(self):
        self.move()
        # Анимация врага
        if self.count % 5 == 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.image = self.frames[self.cur_frame]
        self.count += 1

    def move(self):
        # ИИ врага
        if self.count % 5 == 0:
            if self.direction == 0:
                self.position.x += self.velocity.x
            if self.direction == 1:
                self.position.x -= self.velocity.x
        self.rect.center = self.position

    def world_shift(self, dx, dy):
        self.position += vec(dx, dy)


class Bat(Enemy):
    def __init__(self, pos):
        super(Bat, self).__init__(load_image('bat_sprite.png'), 0, 5,
                                  pos[0] * tile_size, pos[1] * tile_size, 5, 3)


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


def set_difficulty(value, difficulty):
    pass


def load_level_data(filename):
    global intro_count
    intro_count = 255
    with open(f'levels/{filename}.map', mode='r', encoding='utf8') as f:
        return Level.new_level(map(str.strip, f.readlines()))


def load_level_from_list(list_of_levels, num):
    return *load_level_data(list_of_levels[num]), num + 1


def intro_play():
    global intro_count
    s.fill((10, 10, 10, intro_count))
    surface.blit(s, (0, 0))
    intro_count -= 2


def outro_play():
    outro_count = 0
    while outro_count < 255:
        background.render()
        all_sprites.draw(surface)
        s.fill((10, 10, 10, outro_count))
        surface.blit(s, (0, 0))
        pygame.display.flip()
        outro_count += 2
    global player, portal, level_num
    for sprite in all_sprites.sprites():
        sprite.kill()
    enemies.clear()
    if level_num < len(levels):
        player, portal, level_num = load_level_from_list(levels, level_num)
    else:
        player = None


world = level_num = player = portal = None
background = Background()
levels = ['level1', 'level2', 'level3']

# skeleton = Enemy(load_image("SkeletonEnemyMove.png"), 0, 3, 100, 100, 12, 1)


def start_the_game():
    global world, level_num, player, portal
    world = World((WIDTH, HEIGHT - 100))
    level_num = 0
    player, portal, level_num = load_level_from_list(levels, level_num)
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
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_DELETE:
                        world.key_dx = WORLD_VEL
                    if event.key == pygame.K_PAGEDOWN:
                        world.key_dx = - WORLD_VEL
            surface.fill((0, 0, 0))
            player.update()
            if player.attacking:
                player.attack()
            player.move()
            background.render()
            enemy_group.update()
            world.update(player)
            if world.dx != 0 or world.dy != 0:
                player.world_shift(world.dx, world.dy)
                for enemy in enemies:
                    enemy.world_shift(world.dx, world.dy)
                for sprite in all_sprites.sprites():
                    sprite.rect = sprite.rect.move(world.dx, world.dy)
            other_group.draw(surface)
            enemy_group.draw(surface)
            portal.update()
            player.single_score(surface)
            surface.blit(player.image, player.rect)
            if intro_count > 0:
                intro_play()
            pygame.display.flip()
            FPS_CLOCK.tick(FPS)
    except AttributeError:
        FPS_CLOCK.tick(0.5)


menu = pygame_menu.Menu('Welcome', WIDTH, HEIGHT,
                        theme=pygame_menu.themes.THEME_DARK)

menu.add.text_input('Name: ', default='John Doe')
menu.add.selector('Difficulty: ', [('Hard', 3), ('Medium', 2), ('Easy', 1)], onchange=set_difficulty)
menu.add.button('Play', start_the_game)
menu.add.button('Quit', pygame_menu.events.EXIT)
menu.mainloop(surface)
