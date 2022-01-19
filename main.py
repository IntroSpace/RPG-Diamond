import os
import random
import socket
import sys
import shutil
import threading
from errno import EADDRINUSE
from math import ceil
from time import sleep

import pygame
import pygame_menu
from languages.languages import lang
import sqlite3

# открываем соединение с sql базой
con = sqlite3.connect("game.sql")


def load_lang() -> str:
    """
    Возвращает текущий установленный язык.

    :return: Язык интерфейса
    :rtype: str
    """
    cur = con.cursor()
    return cur.execute("""SELECT value FROM settings WHERE name = 'lang'""").fetchone()[0]


def load_settings() -> list:
    """
    Возвращает никнейм игрока и все настройки игры.

    :return: Настройки игры
    :rtype: list
    """
    cur = con.cursor()
    return [i[0] for i in cur.execute("""SELECT value FROM settings ORDER BY id""").fetchall()]


# загружаем настройки с базы данных
username, cur_lang, vol_music, vol_sound = load_settings()
# получаем список фраз на текущем языке
word = lang.get(cur_lang, dict())
# выставляем значения звуков и музыки
vol_music, vol_sound = int(vol_music), int(vol_sound)
new_music = vol_music
new_sound = vol_sound

pygame.init()
# получаем размеры экрана для кроссплатформенности
WIDTH, HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
# вычисляем размер одного блока
tile_size = HEIGHT // 20
# создаём игровое окно
surface = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF, 16)
surface.set_alpha(None)
# игровые константы
ACC = 0.4 * tile_size / 54
FRIC = - (0.09 + 0.01 * tile_size / 54)
COUNT = 0
vec = pygame.math.Vector2
FPS = 60
FPS_CLOCK = pygame.time.Clock()
WORLD_VEL = 5
MAX_WORLD_VEL = 5
# установка названия игры
pygame.display.set_caption("RPG Diamond")
# инициализация необходимых шрифтов
game_font = pygame.font.Font(os.path.abspath('data/fonts/pixeloid_sans.ttf'), 33)
special_font = pygame.font.Font(os.path.abspath('data/fonts/pixeloid_bold.ttf'), 23)
mana_font = pygame.font.Font(os.path.abspath('data/fonts/pixeloid_sans.ttf'), tile_size)
big_font = pygame.font.Font(os.path.abspath('data/fonts/pixeloid_sans.ttf'), tile_size * 5)
# переменные для запуска уровней
intro_count = None
s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
player_state = None
player_mana_state = None
# зона активации врагов
# меняется в зависимости от сложности
NON_COMFORT_ZONE = -1, -1
# для подсчёта результатов
max_values = [0, 0]
enemies_killed = 0
cur_enemies_killed = 0
results = None
# переменные для перезапуска уровней
prev_level_num = None
completed_levels = 0
# задний фон игры
background = None
DEFAULT_BG = 'lands.png'
# переменная для хранения класса анимации
tutor_animation = None
# значения для сложностей
DIFFICULTIES_NAME = [word.get("very easy"), word.get("easy"), word.get("med"), word.get("hard")]
DIFFICULTIES_COLOR = [(150, 150, 248), (102, 102, 255), (220, 87, 87), (187, 52, 52)]
PARTICLES_BY_DIFFICULTY = [2, 3, 6, 9]
PARTS_COUNT = 2
# дефолт уровни
GAME_LEVELS = ['level1', 'level2', 'level3']

# файлы для показателя жизней и для обучения
heart_files = ['death', 'onelife', 'halflife', 'almosthalflife', 'fulllife']
stage_files = ['keyboard/arrows', 'keyboard/space', 'keyboard/enter',
               'mouse/left', 'mouse/right', 'keyboard/fireball_attack', 'keyboard/esc']

# список звуков для установки громкости
all_sounds = list()


class CustomSound:
    def __init__(self, filename: str, volume: int = 1) -> None:
        """
        Класс для звуков для более удобной настройки громкости

        :param filename: Путь к файлу
        :type filename: str
        :param volume: Стандартная громкость звука
        :type volume: int
        """
        all_sounds.append(self)
        self.sound = pygame.mixer.Sound(filename)
        self.volume = volume
        # выставляем громкости
        self.sound.set_volume(volume)
        self.set_default_volume(vol_sound)

    def set_volume(self, volume: int) -> None:
        """
        Установка громкости

        :param volume: Громкость
        :type volume: int
        """
        self.volume = volume
        self.sound.set_volume(volume)

    def set_default_volume(self, new_volume: int) -> None:
        """
        Поставить громкость, выбранную пользователем

        :param new_volume: Громкость из настроек
        :type new_volume: int
        """
        self.sound.set_volume(self.volume * new_volume)

    def play(self, *args, **kwargs) -> None:
        """
        Проигрывание звука
        """
        self.sound.play(*args, **kwargs)

    def stop(self) -> None:
        """
        Остановить проигрывание звука
        """
        self.sound.stop()

    def fadeout(self, *args, **kwargs) -> None:
        """
        Плавная остановка проигрывания звука
        """
        self.sound.fadeout(*args, **kwargs)


# инициализация всех звуков
pick_up = CustomSound('data/sounds/pick_up.wav', 0.22)
player_regeneration = CustomSound('data/sounds/player_regeneration.wav', 0.08)
bat_sound = CustomSound('data/sounds/bats.wav', 0.9)
jump_sound = CustomSound('data/sounds/jump.wav', 0.27)
knife_attack_sound = CustomSound('data/sounds/knife_attack.wav', 0.45)
teleport_sound = CustomSound('data/sounds/teleport.wav', 0.75)
rev_count_sound = CustomSound('data/sounds/reverse_counter_bits.wav', 0.83)
count_end_sound = CustomSound('data/sounds/reverse_counter_end.wav', 0.75)
# установка музыки
pygame.mixer.music.load('data/sounds/background_music.wav')
pygame.mixer.music.set_volume(vol_music)
pygame.mixer.music.play(-1)

# значения для редактора уровней
CELL_COLOR = pygame.Color(245, 245, 245)
CELL_CHOSEN_COLOR = pygame.Color(140, 185, 205)
CELL_WIDTH = 1
ITEM_CHOSEN_COLOR = pygame.Color(230, 235, 235)

# значения для передачи по локальной сети
ACCEPTED_PORTS = range(10000, 11000)

# настраивание игровых переменных
BG_COLOR = 45, 40, 40
TEXT_COLOR = pygame.Color(115, 125, 125)
STAGES_COLOR = pygame.Color(190, 195, 175)
END_TEXT_COLOR = 245, 245, 245
TEXT_SHIFT = game_font.render(f'{word.get("your score")}: 0   ©',
                              True, TEXT_COLOR).get_width() // 1.4 + 15
MANA_COLOR = pygame.Color(49, 105, 168)
# расположения собственных уровней
CUSTOM_LEVELS_DIRECTORY = os.path.join('levels/custom')
CUSTOM_LEVELS_DIR_WITHOUT_LVL = os.path.join('custom')

# список всех врагов для контроля ими
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
# группа для обучения
tutorial_group = pygame.sprite.Group()
# группа для осколков (атака SpikeBall)
particles_group = pygame.sprite.Group()


def load_image(image_name: str, colorkey: int = None, size: int = None) -> pygame.Surface:
    """
    Загружает спрайт

    :param image_name: Путь к изображению
    :type image_name: str
    :param colorkey: Альфа переменная
    :type colorkey: int
    :param size: Размер спрайта
    :type size: int
    :return: Спрайт
    :rtype: pygame.Surface
    """
    fullname = os.path.join('data', image_name)
    if not os.path.isfile(fullname):
        print(f'{word.get("img file")} \'{fullname}\' {word.get("not found")}')
        con.close()
        sys.exit()
    image = pygame.image.load(fullname)
    if size is not None:
        size -= 1
        delta = size / 54
        image = pygame.transform.scale(image, (int(image.get_width() * delta),
                                               int(image.get_height() * delta)))
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


def cut_sheet(filename: str, columns: int, size: int = tile_size) -> list:
    """
    Нарезает однострочные спрайтщиты

    :param filename: Путь к спрайтщиту
    :type filename: str
    :param columns: Количество столбцов спрайтов
    :type columns: int
    :param size: Размер спрайта
    :type size: int
    :return: Список спрайтов
    :rtype: list
    """
    sheet = load_image(filename)
    sprite_rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                              sheet.get_height())
    frames = []
    delta = size / sprite_rect.h
    rect = pygame.Rect(0, 0, int(sprite_rect.w * delta), size)
    for i in range(columns):
        frame_location = (sprite_rect.w * i, 0)
        frames.append(pygame.transform.scale(sheet.subsurface(pygame.Rect(
            frame_location, sprite_rect.size)), rect.size))
    return frames


def sprites_by_directory(filename: str, count: int) -> list:
    """
    Объединяет спрайты из одной директории

    :param filename: Путь к директории со спрайтами
    :type filename: str
    :param count: Количество спрайтов
    :type count: int
    :return: Список спрайтов
    :rtype: list
    """
    direct = os.path.join('bomb', filename)
    frames = []
    for i in range(count):
        sprite = load_image(os.path.join(direct, f'{i}.png'))
        frames.append(pygame.transform.scale(sprite, (tile_size, tile_size)))
    return frames


# анимации игрока
run_animation_RIGHT = [load_image("Player_Sprite_R.png", size=tile_size),
                       load_image("Player_Sprite2_R.png", size=tile_size),
                       load_image("Player_Sprite3_R.png", size=tile_size),
                       load_image("Player_Sprite4_R.png", size=tile_size),
                       load_image("Player_Sprite5_R.png", size=tile_size),
                       load_image("Player_Sprite6_R.png", size=tile_size)]

run_animation_LEFT = [load_image("Player_Sprite_L.png", size=tile_size),
                      load_image("Player_Sprite2_L.png", size=tile_size),
                      load_image("Player_Sprite3_L.png", size=tile_size),
                      load_image("Player_Sprite4_L.png", size=tile_size),
                      load_image("Player_Sprite5_L.png", size=tile_size),
                      load_image("Player_Sprite6_L.png", size=tile_size)]

attack_animation_RIGHT = [load_image("Player_Sprite_R.png", size=tile_size),
                          load_image("Player_Attack_R.png", size=tile_size),
                          load_image("Player_Attack2_R.png", size=tile_size),
                          load_image("Player_Attack2_R.png", size=tile_size),
                          load_image("Player_Attack3_R.png", size=tile_size),
                          load_image("Player_Attack3_R.png", size=tile_size),
                          load_image("Player_Attack4_R.png", size=tile_size),
                          load_image("Player_Attack4_R.png", size=tile_size),
                          load_image("Player_Attack5_R.png", size=tile_size),
                          load_image("Player_Attack5_R.png", size=tile_size)]
attack_animation_LEFT = [load_image("Player_Sprite_L.png", size=tile_size),
                         load_image("Player_Attack_L.png", size=tile_size),
                         load_image("Player_Attack2_L.png", size=tile_size),
                         load_image("Player_Attack2_L.png", size=tile_size),
                         load_image("Player_Attack3_L.png", size=tile_size),
                         load_image("Player_Attack3_L.png", size=tile_size),
                         load_image("Player_Attack4_L.png", size=tile_size),
                         load_image("Player_Attack4_L.png", size=tile_size),
                         load_image("Player_Attack5_L.png", size=tile_size),
                         load_image("Player_Attack5_L.png", size=tile_size)]

# анимации персонажа Bomby
bomb_idle = cut_sheet('bomb/bomb_idle.png', 2)
bomb_walk = cut_sheet('bomb/bomb_walk.png', 6)
bomb_fall_down = cut_sheet('bomb/bomb_fall_down.png', 1)
bomb_jump_up = cut_sheet('bomb/bomb_jump_up.png', 1)
bomb_explode = sprites_by_directory('bomb_explode', 4)


def get_first_frame(sheet: pygame.Surface, col: int, row: int, pos: tuple = (0, 0)) -> pygame.Surface:
    """
    Забрать один спрайт из спрайтщита

    :param sheet: Спрайтщит
    :type sheet: pygame.Surface
    :param col: Количество столбцов
    :type col: int
    :param row: Количество строчек
    :type row: int
    :param pos: Позиция необходимого спрайта
    :type pos: tuple
    :return: Необходимый спрайт
    :rtype: pygame.Surface
    """
    sprite_rect = pygame.Rect(0, 0, sheet.get_width() // col,
                              sheet.get_height() // row)
    rect = pygame.Rect(0, 0, tile_size, tile_size)
    frame_location = (sprite_rect.w * pos[0], sprite_rect.h * pos[1])
    return pygame.transform.scale(sheet.subsurface(
        pygame.Rect(frame_location, sprite_rect.size)), rect.size)


# берём спрайты для редактора уровней
teleport_sprite = get_first_frame(load_image('green_portal.png'), 8, 3)
spike_ball_sprite = get_first_frame(load_image('spike_ball.png'), 6, 1, pos=(2, 0))
bat_sprite = get_first_frame(load_image('bat_sprite.png'), 5, 3, pos=(0, 1))
coin_sprite = get_first_frame(load_image('coin_yellow.png'), 5, 1)

# готовим анимации жизней
life_states = [[] for i in range(len(heart_files))]
for i, directory in enumerate(heart_files):
    final_dir = os.path.join('designs', directory)
    for file in os.listdir(os.path.join('data', final_dir)):
        life_states[i].append(pygame.transform.scale(load_image(os.path.join(final_dir, file)),
                                                     (0.11 * WIDTH, 0.11 / 4 * WIDTH)))

# готовим этапы обучения
stages = [[pygame.Surface((0, 0))]]
for name in stage_files:
    stages.append(cut_sheet(f'tutorial/{name}.png', 2, size=tile_size * 2))


def server_send_file(warning: pygame_menu.widgets.Label, level_name: str) -> None:
    """
    Запуск сервера для отправки уровня

    :param warning: Label для вывода ошибок на экран
    :type warning: pygame_menu.widgets.Label
    :param level_name: Название уровня
    :type level_name: str
    """
    filename = 'levels/custom/' + level_name
    if not os.path.isfile(f'{filename}.map'):
        warning.show()
        return
    with open(f'{filename}.map', 'r') as f:
        background_name = f.readline().replace('\n', '')
    # пробегаемся по портам, пока не найдем свободный
    for port in ACCEPTED_PORTS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host = socket.gethostbyname(socket.gethostname())
            sock.bind((host, port))
            break
        except socket.error as e:
            if e.errno == EADDRINUSE:
                continue
            else:
                print(e)

    def disable() -> None:
        """
        Остановка сервера
        """
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        except Exception:
            pass
        sock.close()
        try:
            threads = threading.enumerate()
            need_thread = threads[list(map(lambda i: i.getName(), threads)).index('serv_acc')]
            need_thread.running = False
        except ValueError:
            pass
        submenu.disable()

    submenu = pygame_menu.Menu(word.get("get level"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)
    label = submenu.add.label('', font_color=pygame.Color('#6666ff'))
    submenu.add.label(f'{word.get("tell friend")}')
    submenu.add.label(f'{word.get("show ip")}{host}')
    submenu.add.label(f'{word.get("show port")}{port}')
    submenu.add.button(word.get('back'), disable)
    # запускаем сервер в отдельном потоке
    serv_acc = threading.Thread(name='serv_acc', target=server_accepting_client,
                                args=(label, sock, filename, background_name))
    serv_acc.start()
    submenu.mainloop(surface)


def server_accepting_client(label: pygame_menu.widgets.Label, sock: socket.socket,
                            filename: str, background_name: str) -> None:
    """
    Ожидание клиента и передача ему уровня с задним фоном

    :param label: Label для вывода информации в процессе
    :type label: pygame_menu.widgets.Label
    :param sock: Сокет для отправки файлов
    :type sock: socket.socket
    :param filename: Название файла уровня
    :type filename: str
    :param background_name: Название заднего фона
    :type background_name: str
    """
    sock.listen(5)
    c, addr = sock.accept()
    try:
        c.send(bytes(f'{username}.{filename}'.encode()))
        sleep(1)
        with open(f'{filename}.map', 'rb') as f:
            c.sendfile(f)
        sleep(1)
        c.send('<eof>'.encode())
        while not (name_of_friend := c.recv(1024).decode()):
            pass
        label.set_title(f'{word.get("friend got lvl")}"{name_of_friend}"')
        sleep(1)
        c.send(bytes(background_name.encode()))
        sleep(2)
        with open(f'data/backgrounds/{background_name}', mode='rb') as f:
            c.sendfile(f)
        c.close()
    except BrokenPipeError:
        pass


def client_get_file(warning: pygame_menu.widgets.Label, host: str, port: int) -> None:
    """
    Запуск клиента для получения уровня

    :param warning: Label для показа ошибок
    :type warning: pygame_menu.widgets.Label
    :param host: Хост сервера
    :type host: str
    :param port: Порт сервера
    :type port: int
    """
    if port.isnumeric():
        port = int(port)
    else:
        warning.set_title(word.get('warning port not int'))
        warning.show()
        return
    s_get = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s_get.connect((host, port))
    except ConnectionRefusedError:
        warning.set_title(word.get('warning conn'))
        warning.show()
        return
    except OverflowError:
        warning.set_title(word.get('warning port value'))
        warning.show()
        return
    except Exception:
        warning.set_title(word.get('some error'))
        warning.show()
        return

    # запуск клиента в отдельном потоке
    client_main = threading.Thread(name='client_main', target=client_main_work, args=(s_get,))
    client_main.start()


def client_main_work(s_get: socket.socket) -> None:
    """
    Запуск клиента

    :param s_get: Сокет дял получения уровня с задним фоном
    :type s_get: socket.socket
    """
    intro_info = s_get.recv(1024).decode()
    *server_player_name, filename = intro_info.split('.levels/custom/')
    server_player_name = ''.join(server_player_name)
    filename = 'levels/custom/' + filename
    with open(f'{filename}-{server_player_name}.map', 'wb') as f:
        data = s_get.recv(1024)
        while data.decode() != '<eof>':
            f.write(data)
            data = s_get.recv(1024)
    sleep(1)
    s_get.send(bytes(username.encode()))
    while not (background_name := s_get.recv(1024).decode()):
        pass
    filename = 'data/backgrounds/' + background_name
    data_to_write = bytes()
    data = s_get.recv(1024)
    while data:
        data_to_write = data_to_write + data
        data = s_get.recv(1024)
    with open(filename, 'wb') as f:
        f.write(data_to_write)


class World:
    def __init__(self, screen_size: tuple) -> None:
        """
        КЛасс для смещения камеры

        :param screen_size: Размеры окна
        :type screen_size: tuple
        """
        self.dx = self.key_dx = 0
        self.dy = self.key_dy = 0
        width, height = screen_size
        self.borders_x = pygame.Rect(((width - height) // 2, 0, height, height))
        self.borders_y = pygame.Rect((0, tile_size * 5, width, int(tile_size * 11.1)))

    def update(self, __player) -> None:
        """
        Смещает камеру, если это необходимо

        :param __player: Класс игрока
        :type __player: Player
        """
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
    def __init__(self, filename: str = DEFAULT_BG) -> None:
        """
        Создание заднего фона

        :param filename: Название изображения заднего фона
        :type filename: str
        """
        super().__init__()
        self.name = filename
        filename = os.path.join('backgrounds', filename)
        if not os.path.isfile(os.path.join('data', filename)):
            raise FileNotFoundError
        self.image = pygame.transform.scale(load_image(filename), (WIDTH, HEIGHT)).convert()
        self.rect = self.image.get_rect(topleft=(0, 0))

    def render(self) -> None:
        """
        Отрисовка заднего фона
        """
        surface.blit(self.image, self.rect.topleft)


class Tile(pygame.sprite.Sprite):
    def __init__(self, filename: str, pos: tuple, *groups, flag: int = 0) -> None:
        """
        Класс одного блока

        :param filename: Название файла блока
        :type filename: str
        :param pos: Позиция блока в уровне
        :type pos: tuple
        :param groups: Группы спрайтов
        :type groups: pygame.sprite.Group
        :param flag: Флажок для некоторых наследственных классов
        :type flag: int
        """
        if flag == 1:
            super(Tile, self).__init__(all_sprites, tiles_group, other_group)
        else:
            super(Tile, self).__init__(all_sprites, tiles_group, *groups)
            self.image = pygame.transform.scale(load_image(filename), (tile_size, tile_size)).convert()
            self.rect = self.image.get_rect(topleft=(pos[0] * tile_size, pos[1] * tile_size))
            self.mask = pygame.mask.from_surface(self.image)


# блок земли
class Land(Tile):
    def __init__(self, pos, *groups):
        super(Land, self).__init__('land.png', pos, *groups)


# блок камня
class Stone1(Tile):
    def __init__(self, pos, *groups):
        super(Stone1, self).__init__('stone1.png', pos, *groups)


# блок песка
class Sand(Tile):
    def __init__(self, pos, *groups):
        super(Sand, self).__init__('sand.png', pos, *groups)


# конец уровня - портал
class Portal(Tile):
    def __init__(self, sheet: pygame.Surface, pos, size):
        super(Portal, self).__init__(0, 0, flag=1)
        x, y = pos
        self.row, self.col = size
        self.frames = []
        delta = int(tile_size * 0.05)
        self.rect = pygame.Rect(x * tile_size - delta, y * tile_size - delta * 2, tile_size + delta,
                                tile_size + delta)
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
                    frame_location, size_sprite)), self.rect.size).convert_alpha())

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
        if self.frame is None \
                and self.rect.width / 2 < self.rect.centerx < WIDTH - self.rect.width / 2:
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
                global completed_levels
                completed_levels += 1
                teleport_sound.play()
                outro_play()
        col = col % self.col
        self.frame = row, col
        self.image = self.frames[row * self.col + col]
        self.mask = pygame.mask.from_surface(self.image)


# класс для обработки уровней
class Level:
    @staticmethod
    def new_level(data, replay=False):
        global max_values, background, cur_enemies_killed
        cur_enemies_killed = 0
        data = list(data)
        index = 1
        try:
            background = Background(data[0])
        except FileNotFoundError:
            background = Background()
            index = 0
        res_player = None
        main_portal = None
        for y, row in enumerate(data[index:]):
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
                    Enemy.bats += 1
                    bat_sound.stop()
                    bat_sound.play(-1)
                if tile == 'Y':
                    if not replay:
                        max_values[1] += 1
                    enemies.append(Bomby((x, y)))
                if tile == 'A':
                    enemies.append(SpikeBall((x, y)))
        return res_player, main_portal

    @staticmethod
    def save_level(filename, data, background_name):
        filename = os.path.join(CUSTOM_LEVELS_DIRECTORY, f'{filename}.map')
        with open(filename, mode='w', encoding='utf8') as f:
            f.writelines([background_name + '\n', *data])


# класс главного героя
class Player(pygame.sprite.Sprite):
    def __init__(self, pos, score=0):
        super().__init__(all_sprites)
        self.image = run_animation_RIGHT[0]
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
        self.rect = self.image.get_rect(topleft=self.pos)
        self.vel = vec(0, 0)
        self.acc = vec(0, 0)
        self.direction = "RIGHT"
        self.block_right = self.block_left = 0
        self.score = score
        self.heart = 4 if heart is None else heart.heart
        self.magic_cooldown = 1
        self.killed_by_particles = False

    def move(self):
        sprite_list = pygame.sprite.spritecollide(self, other_group, False)
        self.block_right = self.block_left = 0
        if sprite_list:
            self.mask = pygame.mask.from_surface(self.image)
            for sprite in sprite_list:
                if isinstance(sprite, Particle):
                    if not self.killed_by_particles:
                        self.killed_by_particles = True
                        self.heart -= 1
                        heart.heart -= 1
                        if heart.heart >= 0:
                            outro_play(replay=True)
                        else:
                            outro_play(end_of_game=True)
                    continue
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
        self.acc = vec(0, 0.5 * tile_size / 54)
        if abs(self.vel.x) > 0.5 * tile_size / 54:
            self.running = True
        else:
            self.running = False
        if pygame.key.get_pressed()[pygame.K_LEFT]:
            self.acc.x = -ACC
        if pygame.key.get_pressed()[pygame.K_RIGHT]:
            self.acc.x = ACC
        if abs(self.vel.x) < 0.4 * tile_size / 54:
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
        self.rect.bottomleft = self.pos

    def world_shift(self, dx, dy):
        self.pos.x += dx
        self.pos.y += dy
        self.rect.bottomleft = self.pos

    def update(self):
        if len(fireball_group.sprites()) == 0:
            self.magic_cooldown = 1
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            self.jump()
        if (keys[pygame.K_RETURN] or keys[pygame.K_z]) and not self.attacking:
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
        if abs(self.vel.x) < tile_size / 54 and self.move_frame != 0:
            self.move_frame = 0
            if self.direction == "RIGHT":
                self.image = run_animation_RIGHT[self.move_frame // 2]
            elif self.direction == "LEFT":
                self.image = run_animation_LEFT[self.move_frame // 2]

    def attack(self):
        reserve_rect = self.rect
        rx, ry, rw, rh = *self.rect.topleft, *self.rect.size
        delta = 35 * tile_size / 54
        self.rect = pygame.Rect(rx - int(delta), ry, rw + int(2 * delta), rh)
        sprite_list = pygame.sprite.spritecollide(self, tiles_group, False)
        if sprite_list:
            self.mask = pygame.mask.from_surface(self.image)
            for sprite in sprite_list:
                if isinstance(sprite, Portal):
                    continue
                if isinstance(sprite, Coin):
                    continue
                rect = sprite.rect
                if rect.collidepoint(self.rect.midleft):
                    if self.direction == 'LEFT' and self.attack_frame not in [0, 1]:
                        reserve_rect.x += 20
                        self.pos.x += 20
                    self.attack_frame = 0
                    self.attacking = False
                    self.rect = reserve_rect
                    return
                if rect.collidepoint(self.rect.midright):
                    if self.direction == 'LEFT' and self.attack_frame not in [0, 1]:
                        self.pos.x += 20
                    self.attacking = False
                    self.attack_frame = 0
                    self.rect = reserve_rect
                    return
        self.rect = reserve_rect
        if self.attack_frame == 1:
            knife_attack_sound.play()
        if self.attack_frame > 9:
            self.attack_frame = -1
            if not pygame.key.get_pressed()[pygame.K_RETURN] \
                    and not pygame.key.get_pressed()[pygame.K_z]:
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
            self.vel.y = -12 * tile_size / 54
            jump_sound.play()

    def gravity_check(self):
        rect = self.rect
        if self.attacking:
            self.rect = self.image.get_rect(bottomleft=rect.bottomleft)
        if self.vel.y > 0:
            if pygame.sprite.spritecollide(player, other_group, False):
                self.mask = pygame.mask.from_surface(self.image)
                for sprite in pygame.sprite.spritecollide(player, other_group, False):
                    if isinstance(sprite, Particle):
                        if not self.killed_by_particles:
                            self.killed_by_particles = True
                            self.heart -= 1
                            heart.heart -= 1
                            if heart.heart >= 0:
                                outro_play(replay=True)
                            else:
                                outro_play(end_of_game=True)
                        continue
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
                    if sprite.rect.collidepoint(rect.bottomleft[0] + 5, rect.bottomleft[1]) \
                            or sprite.rect.collidepoint(rect.bottomright[0] - 5, rect.bottomright[1]):
                        self.pos.y = sprite.rect.top + 1
                        self.vel.y = 0
                        self.jumping = False
        elif self.vel.y < 0:
            if pygame.sprite.spritecollide(player, other_group, False):
                self.mask = pygame.mask.from_surface(self.image)
                for sprite in pygame.sprite.spritecollide(player, other_group, False):
                    if isinstance(sprite, Particle):
                        if not self.killed_by_particles:
                            self.killed_by_particles = True
                            self.heart -= 1
                            heart.heart -= 1
                            if heart.heart >= 0:
                                outro_play(replay=True)
                            else:
                                outro_play(end_of_game=True)
                        continue
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
                    if sprite.rect.collidepoint(rect.topleft[0] + 5, rect.topleft[1]) \
                            or sprite.rect.collidepoint(rect.topright[0] - 5, rect.topright[1]):
                        self.vel.y *= -1
                        self.acc.y *= -1
                        break
        self.rect = rect

    def single_score(self, screen):
        text = game_font.render(f'{word.get("your score")}: {str(self.score).ljust(3, " ")}©',
                                True, TEXT_COLOR)
        text_x = WIDTH - tile_size * 2 - TEXT_SHIFT
        text_y = tile_size
        screen.blit(text, (text_x, text_y))

    def add_score(self):
        self.score += 1
        pick_up.play()

    def enemy_collide(self, enemy):
        global enemies_killed, cur_enemies_killed
        if isinstance(enemy, Bomby):
            if enemy.is_killed() and enemy.frame[1] > 1:
                self.heart -= 1
                heart.heart -= 1
                if heart.heart >= 0:
                    outro_play(replay=True)
                else:
                    outro_play(end_of_game=True)
                return
            if self.attacking:
                if not enemy.is_killed():
                    enemies_killed += 1
                    cur_enemies_killed += 1
                    enemy.end()
                return
        elif enemy.is_killed():
            return
        if self.attacking and not isinstance(enemy, SpikeBall):
            enemies_killed += 1
            cur_enemies_killed += 1
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


# родительский класс врагов
class Enemy(pygame.sprite.Sprite):
    # количество летучих мышей в уровне
    bats = 0

    def __init__(self, sheet: pygame.Surface, direction: int,
                 velocity: int, x: int, y: int, columns: int, rows: int, skip=False):
        super().__init__(all_sprites, other_group, enemy_group)
        if skip:
            return
        self.frames = []
        self.direction = direction
        self.cut_sheet(sheet, columns, rows)
        self.columns = columns
        self.mana = 3
        self.frame = 0, 0
        self.image = self.frames[self.frame[0] * self.columns + self.frame[1]]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel = vec(0, 0)
        self.position = vec(x, y)
        self.vel.x = velocity
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
        if 2 * tile_size - self.vel.x <= abs(self.delta_x) \
                <= 2 * tile_size + self.vel.x:
            self.direction = self.direction * -1
        # ИИ врага
        if self.direction == 1:
            self.position += self.vel
            self.delta_x -= self.vel.x
        if self.direction == -1:
            self.position -= self.vel
            self.delta_x += self.vel.x
        self.rect.topleft = self.position

    def world_shift(self, dx, dy):
        self.position += vec(dx, dy)
        self.rect.topleft = self.position

    def end(self):
        pass

    def is_killed(self):
        pass


class Bat(Enemy):
    def __init__(self, pos, angry_vel=(2 * tile_size / 54, 1 * tile_size / 54)):
        super(Bat, self).__init__(load_image('bat_sprite.png'), 1, 5 * tile_size / 54,
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
        if Enemy.bats == 1:
            bat_sound.fadeout(1300)

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
                Enemy.bats -= 1
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
        delta = (self.vel.x - 1) // 2
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


class Bomby(Enemy):
    def __init__(self, pos):
        super(Bomby, self).__init__(0, 0, 0, 0, 0, 0, 0, skip=True)
        self.direction = 1
        self.frames = [bomb_idle, bomb_walk, bomb_fall_down, bomb_jump_up, bomb_explode]
        self.columns = 2
        self.mana = 3
        self.start()
        self.image = self.frames[self.frame[0]][self.frame[1]]
        self.rect = self.image.get_rect(topleft=(pos[0] * tile_size, pos[1] * tile_size))
        self.vel = vec(0, 0)
        self.jumping = False
        self.position = vec(pos[0] * tile_size, pos[1] * tile_size)
        self.vel.x = tile_size / 54
        self.count = 0
        self.delta_x = 0
        self.angry_state = False
        self.acc = vec(0, 0)

    def start(self):
        self.frame = 1, 0

    def end(self):
        if not self.is_killed():
            player.experience += 1
            mana.mana += self.mana
            self.count = 0
            self.frame = 4, 0

    def is_killed(self):
        return self.frame[0] == 4

    def update(self):
        if not self.is_killed():
            self.move()
        self.move_y()
        if int(self.vel.y) > 1 and not self.is_killed():
            self.frame = 2, 0
            self.image = self.frames[2][0]
            if self.direction == -1:
                self.image = pygame.transform.flip(self.image, True, False)
        elif self.vel.y < -1 and not self.is_killed():
            self.frame = 3, 0
            self.image = self.frames[3][0]
            if self.direction == -1:
                self.image = pygame.transform.flip(self.image, True, False)
        else:
            if (not self.is_killed() and self.count == 6) \
                    or (self.frame[1] <= 1 and self.count == 14) \
                    or (self.frame[1] > 1 and self.count == 9):
                self.count = 0
                self.frame = self.frame[0], self.frame[1] + 1
            if self.is_killed() and self.frame[1] == len(self.frames[self.frame[0]]):
                del enemies[enemies.index(self)]
                self.kill()
                return
            self.frame = self.frame[0], self.frame[1] % len(self.frames[self.frame[0]])
            self.image = self.frames[self.frame[0]][self.frame[1]]
            if self.direction == -1:
                self.image = pygame.transform.flip(self.image, True, False)
            self.count += 1
            if self.frame[1] == len(self.frames[self.frame[0]]) - 1 and not self.is_killed():
                self.frame = self.frame[0], -1

    def move(self):
        self.frame = 1, self.frame[1]
        if 2 * tile_size - self.vel.x <= abs(self.delta_x) \
                <= 2 * tile_size + self.vel.x:
            self.direction = self.direction * -1
        block_left, block_right = 0, 0
        if self.direction != -1:
            self.rect.right += 1
            for sprite in pygame.sprite.spritecollide(self, tiles_group, False):
                if isinstance(sprite, Portal):
                    continue
                rect = sprite.rect
                m_x, m_y = self.rect.midright
                if rect.collidepoint((m_x, m_y)) \
                        and not rect.collidepoint((m_x - 2, m_y)):
                    block_right = 1
                    self.direction = -1
                    break
            self.rect.right -= 1
        if self.direction != 1:
            self.rect.left -= 1
            for sprite in pygame.sprite.spritecollide(self, tiles_group, False):
                if isinstance(sprite, Portal):
                    continue
                rect = sprite.rect
                m_x, m_y = self.rect.midleft
                if rect.collidepoint((m_x, m_y)) \
                        and not rect.collidepoint((m_x + 2, m_y)):
                    block_left = 1
                    self.direction = 1
                    break
            self.rect.left += 1
        if block_left == block_right == 1:
            self.frame = 0, self.frame[1] % len(self.frames[0])
            self.direction = 0
        # ИИ врага
        if self.direction == 1:
            self.position.x += self.vel.x
            self.delta_x -= self.vel.x
        if self.direction == -1:
            self.position.x -= self.vel.x
            self.delta_x += self.vel.x
        self.rect.topleft = self.position

    def move_y(self):
        self.acc = vec(0, 0.5)
        self.vel += self.acc
        self.gravity_check()
        self.position.y += int(self.vel.y)
        self.position.y += int(0.5 * self.acc.y)
        self.rect.topleft = self.position

    def gravity_check(self):
        if self.vel.y > 0:
            if pygame.sprite.spritecollide(self, tiles_group, False):
                for sprite in pygame.sprite.spritecollide(self, tiles_group, False):
                    if isinstance(sprite, Portal):
                        continue
                    if -5 - self.vel.y < sprite.rect.top - self.rect.bottom:
                        self.jumping = False
                        self.vel.y = self.acc.y = 0
                        self.rect.bottom = sprite.rect.top
                        self.position.y = self.rect.top
        elif self.vel.y < 0:
            sprite = pygame.sprite.spritecollide(self, tiles_group, False)
            if sprite:
                if isinstance(sprite[0], Portal):
                    return
                self.vel.y *= -1
                self.acc.y *= -1


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
            self.image = load_image("fire_R.png", size=tile_size - 10)
        else:
            self.image = load_image("fire_L.png", size=tile_size - 10)
        self.rect = self.image.get_rect(center=player.rect.center)

    def fire(self):
        player.magic_cooldown = 0
        # Запускается пока снаряд находится в рамках экрана
        if -10 < self.rect.x < WIDTH:
            if self.direction == "RIGHT":
                self.image = load_image("fire_R.png", size=tile_size - 10)
                surface.blit(self.image, self.rect)
            else:
                self.image = load_image("fire_L.png", size=tile_size - 10)
                surface.blit(self.image, self.rect)

            if self.direction == "RIGHT":
                self.rect.move_ip(12 * tile_size / 54, 0)
            else:
                self.rect.move_ip(-12 * tile_size / 54, 0)
        else:
            self.kill()
            player.attacking = False
            return
        if pygame.sprite.spritecollide(self, other_group, False):
            for sprite in pygame.sprite.spritecollide(self, other_group, False):
                if isinstance(sprite, Enemy):
                    if not sprite.is_killed() and not isinstance(sprite, SpikeBall):
                        global enemies_killed, cur_enemies_killed
                        enemies_killed += 1
                        cur_enemies_killed += 1
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


class TutorialAnimation(pygame.sprite.Sprite):
    def __init__(self):
        super(TutorialAnimation, self).__init__(all_sprites, tutorial_group)
        self.image = stages[0][0]
        self.rect = self.image.get_rect(midtop=(WIDTH // 2, int(HEIGHT - tile_size * 3.5)))
        self.count = 0
        self.frame = -1

    def update(self, stage=0):
        cur_frames = stages[stage]
        if self.count == 12:
            self.frame += 1
            self.count = 0
        self.count += 1
        self.frame = self.frame % len(cur_frames)
        self.image = cur_frames[self.frame]
        self.rect = self.image.get_rect(midtop=(WIDTH // 2, int(HEIGHT - tile_size * 3.5)))


class Particle(pygame.sprite.Sprite):
    # сгенерируем частицы разного размера
    fire = [load_image("test_sprite.png", size=tile_size // 1.05)]

    def __init__(self, pos, dx, dy):
        super().__init__(all_sprites, other_group, particles_group)
        self.image = random.choice(self.fire)
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.from_surface(self.image)
        self.count = 300

        # у каждой частицы своя скорость — это вектор
        self.velocity = vec(dx, dy)

        # гравитация будет одинаковой
        self.gravity = 0.5

    def update(self):
        # движение с ускорением под действием гравитации
        self.velocity.y += self.gravity
        # перемещаем частицу
        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y
        self.image.set_alpha(min([255, self.count]))
        if self.count <= 10:
            self.kill()
        self.count -= 4


class SpikeBall(Enemy):
    def __init__(self, pos: tuple):
        super().__init__(0, 0, 0, 0, 0, 0, 0, skip=True)
        self.position = vec(pos[0] * tile_size, pos[1] * tile_size)
        self.frame = 0
        self.frames = []
        self.cut_sheet(load_image('spike_ball.png'), 6, 1)
        self.image = self.frames[self.frame]
        self.mask = pygame.mask.from_surface(self.image)
        self.count = 0
        self.fire_count = 0

    def cut_sheet(self, sheet, columns, rows):
        sprite_rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                  sheet.get_height() // rows)
        self.rect = pygame.Rect(*self.position, tile_size, tile_size)
        for j in range(rows):
            for i in range(columns):
                frame_location = (sprite_rect.w * i, sprite_rect.h * j)
                self.frames.append(pygame.transform.scale(sheet.subsurface(pygame.Rect(
                    frame_location, sprite_rect.size)), self.rect.size))

    def is_killed(self):
        return False

    def update(self):
        if self.fire_count >= 5 and self.frame == 2:
            self.create_particles()
            self.fire_count = 0
        if self.count == 10:
            self.count = 0
            self.frame = (self.frame + 1) % len(self.frames)
            if self.frame == 2:
                self.fire_count += 1
            self.image = self.frames[self.frame]
            self.mask = pygame.mask.from_surface(self.image)
        self.count += 1

    def create_particles(self):
        # количество создаваемых частиц
        particle_count = PARTS_COUNT
        # возможные скорости
        nums_x = range(-4, 5)
        nums_y = range(-7, -2)
        for _ in range(particle_count):
            Particle(self.rect.center,
                     random.choice(nums_x) * tile_size / 54,
                     random.choice(nums_y) * tile_size / 54)


heart = None
mana = Mana()


def set_difficulty(value, difficulty):
    global NON_COMFORT_ZONE, PARTS_COUNT
    PARTS_COUNT = PARTICLES_BY_DIFFICULTY[difficulty]
    if difficulty == 0:
        NON_COMFORT_ZONE = -1, -1
    elif difficulty == 1:
        NON_COMFORT_ZONE = WIDTH * 0.3, HEIGHT * 0.5
    elif difficulty == 2:
        NON_COMFORT_ZONE = WIDTH * 0.5, HEIGHT * 0.6
    elif difficulty == 3:
        NON_COMFORT_ZONE = WIDTH * 0.75, HEIGHT * 0.8


def load_level_data(filename, customs=False):
    global intro_count, prev_level_num
    replay = prev_level_num == level_num
    prev_level_num = level_num
    intro_count = 255
    if customs:
        full_filename = os.path.join(CUSTOM_LEVELS_DIRECTORY, f'{filename}.map')
    else:
        full_filename = os.path.join('levels', f'{filename}.map')
    with open(full_filename, mode='r', encoding='utf8') as f:
        return Level.new_level(map(lambda i: i.replace('\n', ''), f.readlines()), replay=replay)


def load_level_from_list(list_of_levels, num):
    return *load_level_data(list_of_levels[num]), num + 1


def intro_play():
    global intro_count, heart, player_mana_state
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
    global player, portal, level_num, player_state, heart, \
        mana, player_mana_state, enemies_killed, cur_enemies_killed
    outro_count = 0
    while outro_count < 255:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                con.close()
                sys.exit()
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
        enemies_killed -= cur_enemies_killed
        cur_enemies_killed = 0
        level_num -= 1
        mana.mana = player_mana_state
    for sprite in all_sprites.sprites():
        if isinstance(sprite, Heart) and sprite.heart >= 0:
            continue
        if isinstance(sprite, Mana):
            continue
        sprite.kill()
    enemies.clear()
    Enemy.bats = 0
    bat_sound.stop()
    if not end_of_game and level_num < len(levels):
        if not replay:
            player_state = None
        player, portal, level_num = load_level_from_list(levels, level_num)
    else:
        save_results()
        player = None
    player_state = 0
    player_state = player.score


def save_results():
    global results
    results = player.get_results()


def end_the_game():
    pressed = False
    counter, direction = 255, -3
    while not pressed:
        surface.fill(BG_COLOR)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                con.close()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                return
        center_x = WIDTH // 2
        center_y = HEIGHT // 2 + HEIGHT * 0.007

        difficulty = PARTICLES_BY_DIFFICULTY.index(PARTS_COUNT)
        name_of_difficulty = DIFFICULTIES_NAME[difficulty]
        color_of_difficulty = DIFFICULTIES_COLOR[difficulty]
        text = mana_font.render(f'{word.get("cur diffic")}: {name_of_difficulty}',
                                True, color_of_difficulty)
        text_h = HEIGHT * 0.058
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, HEIGHT * 0.08))

        text = mana_font.render(f'{max(heart.heart, 0)} {word.get("of")} '
                                f'{len(life_states) - 1} {word.get("lives")}',
                                True, END_TEXT_COLOR)
        text_h = HEIGHT * 0.049
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, center_y - text_h * 3))

        text = mana_font.render(f'{results[0]} {word.get("of")} '
                                f'{max_values[0]} {word.get("coins")}',
                                True, END_TEXT_COLOR)
        text_h = HEIGHT * 0.048
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, center_y - text_h * 2))

        text = mana_font.render(f'{results[1]} {word.get("of")} '
                                f'{max_values[1]} {word.get("enemies")}',
                                True, END_TEXT_COLOR)
        text_h = HEIGHT * 0.046
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, center_y - text_h))
        text = mana_font.render(f'{completed_levels} {word.get("of")} '
                                f'{len(levels)} {word.get("levels")}',
                                True, END_TEXT_COLOR)
        text_h = HEIGHT * 0.044
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, center_y))

        text = mana_font.render(f'{word.get("press key")}...',
                                True, END_TEXT_COLOR)
        text.set_alpha(counter)
        text_h = HEIGHT * 0.052
        text_w = text.get_width() * text_h / text.get_height()
        surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                     (center_x - text_w // 2, HEIGHT * 0.92 - text_h))

        counter += direction
        if counter in [0, 255]:
            direction *= -1
        pygame.display.flip()
        FPS_CLOCK.tick(FPS)


world = level_num = player = portal = None
levels = GAME_LEVELS


def choose_custom_level():
    custom_levels = list()
    for filename in os.listdir(CUSTOM_LEVELS_DIRECTORY):
        if filename.endswith(".map"):
            custom_levels.append((filename[:-4], len(custom_levels)))
    submenu = pygame_menu.Menu(word.get("custom levels"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)
    warning = submenu.add.label(word.get("warning custom lvl"), font_color=pygame.Color('#B33A3A'))
    warning.hide()
    lvl_select = submenu.add.dropselect(
        title=word.get("select level"),
        items=custom_levels,
        default=0,
        onchange=lambda *_: warning.hide(),
        placeholder_add_to_selection_box=False
    )
    submenu.select_widget(submenu.add.button(word.get("play"),
                                             lambda: start_the_game((warning,
                                                                     lvl_select.get_value()[0][0]))))
    submenu.add.button(word.get("back"), submenu.disable)
    submenu.mainloop(surface)


def send_level_menu():
    custom_levels = list()
    for filename in os.listdir(CUSTOM_LEVELS_DIRECTORY):
        if filename.endswith(".map"):
            custom_levels.append((filename[:-4], len(custom_levels)))

    submenu = pygame_menu.Menu(word.get("send level"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)
    warning = submenu.add.label(word.get("warning custom lvl"), font_color=pygame.Color('#B33A3A'))
    warning.hide()
    lvl_select = submenu.add.dropselect(
        title=word.get("select level"),
        items=custom_levels,
        default=0,
        onchange=lambda *_: warning.hide(),
        placeholder_add_to_selection_box=False
    )
    submenu.select_widget(submenu.add.button(word.get("send level"),
                                             lambda: server_send_file(warning,
                                                                      lvl_select.get_value()[0][0])))
    submenu.add.button(word.get("back"), submenu.disable)
    submenu.mainloop(surface)


def get_level_menu():
    submenu = pygame_menu.Menu(word.get("get level"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)
    warning = submenu.add.label(word.get("warning port conn"), font_color=pygame.Color('#B33A3A'))
    warning.hide()
    default_ip = socket.gethostbyname(socket.gethostname())
    ip_input = submenu.add.text_input(f'{word.get("input ip")}: ',
                                      default=default_ip, onchange=lambda *_: warning.hide())
    port_input = submenu.add.text_input(f'{word.get("input port")}: ',
                                        default='10000', onchange=lambda *_: warning.hide())
    submenu.select_widget(submenu.add.button(word.get("get level"),
                                             lambda: client_get_file(warning,
                                                                     ip_input.get_value(),
                                                                     port_input.get_value())))
    submenu.add.button(word.get("back"), submenu.disable)
    submenu.mainloop(surface)


def share_level_menu():
    submenu = pygame_menu.Menu(word.get("share level"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)

    submenu.select_widget(submenu.add.button(word.get("send level"), send_level_menu))
    submenu.add.button(word.get("get level"), get_level_menu)
    submenu.add.button(word.get("back"), submenu.disable)
    submenu.mainloop(surface)


def play_menu():
    submenu = pygame_menu.Menu(word.get("play"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)

    submenu.add.selector(f'{word.get("diffic")}: ',
                         [(word.get("very easy"), 0), (word.get("easy"), 1),
                          (word.get("med"), 2), (word.get("hard"), 3)],
                         onchange=set_difficulty)
    submenu.select_widget(submenu.add.button(word.get("play"), start_the_game))
    submenu.add.button(word.get("play customs"), choose_custom_level)
    submenu.add.button(word.get("back"), submenu.disable)
    submenu.mainloop(surface)


def pause_game():
    pause_counter = -1
    pause_direction = 2
    pause_black_screen = pygame.Surface((WIDTH, HEIGHT))
    center_x = WIDTH // 2
    center_y = HEIGHT // 2
    counter, direction = 0, 3
    bat_sound.fadeout(1300)
    rev_count_num = 0
    rev_counter = 0
    while True:
        pause_black_screen.fill((10, 10, 10))
        surface.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                con.close()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z and pause_counter >= 150:
                    set_music_volume([[0, (vol_music + 1) % 2]])
                    save_settings()
                elif event.key == pygame.K_x and pause_counter >= 150:
                    set_sound_volume([[0, (vol_sound + 1) % 2]])
                    save_settings()
                elif pause_direction > 0 and pause_counter >= 245:
                    rev_count_num = 3
                    pause_direction = -1
                    pause_counter = 245
                    if Enemy.bats > 0:
                        bat_sound.play(fade_ms=900)
        background.render()
        other_group.draw(surface)
        particles_group.draw(surface)
        enemy_group.draw(surface)
        player.single_score(surface)
        design_group.draw(surface)
        mana.show_score()
        surface.blit(player.image, player.rect)
        if (pause_direction > 0 and pause_counter < 245) \
                or (pause_direction < 0 and pause_counter > 0):
            if pause_counter <= 70 and pause_direction > 0:
                pause_counter += pause_direction // 2
            pause_counter += pause_direction
            pause_black_screen.set_alpha(pause_counter)

        text = mana_font.render(f'{word.get(f"press z music {vol_music}")}...',
                                True, END_TEXT_COLOR)
        text.set_alpha(min([170, counter]))
        text_h = HEIGHT * 0.03
        text_w = text.get_width() * text_h / text.get_height()
        pause_black_screen.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                                (center_x - text_w // 2,
                                 HEIGHT * 0.92 - text_h * 2 - HEIGHT * 0.056))

        text = mana_font.render(f'{word.get(f"press x sound {vol_sound}")}...',
                                True, END_TEXT_COLOR)
        text.set_alpha(min([205, counter]))
        text_h = HEIGHT * 0.03
        text_w = text.get_width() * text_h / text.get_height()
        pause_black_screen.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                                (center_x - text_w // 2,
                                 HEIGHT * 0.92 - text_h - HEIGHT * 0.055))

        text = mana_font.render(f'{word.get("press other key")}...',
                                True, END_TEXT_COLOR)
        text.set_alpha(counter)
        text_h = HEIGHT * 0.053
        text_w = text.get_width() * text_h / text.get_height()
        pause_black_screen.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                                (center_x - text_w // 2, HEIGHT * 0.92 - text_h))

        if rev_count_num > 0 and pause_counter < 235:
            if 0 < pause_counter:
                rev_counter = 85 - (pause_counter + 20) % 85
            else:
                rev_counter += 1
            if rev_counter == 84:
                if rev_count_num == 1:
                    count_end_sound.play()
                    return
                rev_count_num -= 1
            if rev_counter <= 15:
                if rev_counter == 15:
                    rev_count_sound.play()
                text = mana_font.render(str(rev_count_num), True, END_TEXT_COLOR)
                text_h = tile_size * 8 // (16 - rev_counter)
                text_w = text.get_width() * text_h / text.get_height()
                surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                             (center_x - text_w // 2, center_y - text_h // 2))
            else:
                text = mana_font.render(str(rev_count_num), True, END_TEXT_COLOR)
                text.set_alpha((86 - rev_counter + 8) * 3)
                text_h = tile_size * 8
                text_w = text.get_width() * text_h / text.get_height()
                surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                             (center_x - text_w // 2, center_y - text_h // 2))

        if rev_count_num > 0:
            counter -= min([counter, 5])
        elif pause_counter >= 60:
            counter += direction
            if counter in [0, 255]:
                direction *= -1
        else:
            counter = 0

        surface.blit(pause_black_screen, (0, 0))
        pygame.display.flip()
        FPS_CLOCK.tick(FPS)


def start_the_game(other_info=None):
    global world, level_num, player, portal, player_state, mana, completed_levels, background, \
        heart, player_mana_state, max_values, enemies_killed, cur_enemies_killed, prev_level_num, \
        levels
    world = World((WIDTH, HEIGHT - 100))
    prev_level_num = -1
    level_num = completed_levels = 0
    heart = Heart()
    mana = Mana()
    player_mana_state = mana.mana
    max_values = [0, 0]
    enemies_killed = cur_enemies_killed = 0
    if other_info is None:
        levels = GAME_LEVELS
        player, portal, level_num = load_level_from_list(levels, level_num)
    else:
        warning_label, other_level = other_info
        if not os.path.isfile(os.path.join(CUSTOM_LEVELS_DIRECTORY, f'{other_level}.map')):
            warning_label.show()
            return
        levels = [os.path.join(CUSTOM_LEVELS_DIR_WITHOUT_LVL, other_level)]
        try:
            player, portal, level_num = load_level_from_list(levels, level_num)
            if portal is None or player is None:
                raise AttributeError
        except AttributeError:
            warning_label.show()
            return
    player_state = player.score
    running = True
    try:
        while running:
            coins_group.update()
            player.gravity_check()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    con.close()
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
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and intro_count <= 0:
                        player.heart -= 1
                        heart.heart -= 1
                        if heart.heart >= 0:
                            outro_play(replay=True)
                        else:
                            outro_play(end_of_game=True)
                    elif event.key == pygame.K_p and intro_count <= 0:
                        pause_game()
                    if event.key == pygame.K_x:
                        if mana.mana >= 6 and player.magic_cooldown:
                            mana.mana -= 6
                            player.attacking = True
                            FireBall()
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DELETE]:
                world.key_dx = WORLD_VEL
            if keys[pygame.K_PAGEDOWN]:
                world.key_dx = - WORLD_VEL
            surface.fill((0, 0, 0))
            player.move()
            player.update()
            if player.attacking:
                player.attack()
            background.render()
            for ball in fireball_group:
                ball.fire()
            particles_group.update()
            enemy_group.update()
            world.update(player)
            if world.dx != 0 or world.dy != 0:
                player.world_shift(world.dx, world.dy)
                for enemy in enemies:
                    enemy.world_shift(world.dx, world.dy)
                for sprite in all_sprites.sprites():
                    if isinstance(sprite, Player) or isinstance(sprite, Enemy):
                        continue
                    if design_group.has(sprite):
                        continue
                    sprite.rect = sprite.rect.move(world.dx, world.dy)
            other_group.draw(surface)
            particles_group.draw(surface)
            enemy_group.draw(surface)
            portal.update()
            player.single_score(surface)
            design_group.update()
            design_group.draw(surface)
            mana.show_score()
            surface.blit(player.image, player.rect)
            if keys[pygame.K_ESCAPE]:
                outro_play(end_of_game=True)
            if intro_count > 0:
                intro_play()
            pygame.display.flip()
            FPS_CLOCK.tick(FPS)
    except AttributeError:
        FPS_CLOCK.tick(0.5)
        end_the_game()


def start_tutorial():
    global world, player, portal, tutor_animation
    world = World((WIDTH, HEIGHT - 100))
    player, _ = load_level_data('tutorial')
    running = True
    counter = 400
    stage = 0
    text = None
    tutor_animation = TutorialAnimation()
    try:
        while running:
            player.gravity_check()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    con.close()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if not player.attacking:
                            player.attack()
                            player.attacking = True
                    if event.button == 3:
                        if mana.mana >= 6 and player.magic_cooldown:
                            mana.mana = 6
                            player.attacking = True
                            FireBall()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_x:
                        if mana.mana >= 6 and player.magic_cooldown:
                            mana.mana = 6
                            player.attacking = True
                            FireBall()
            keys = pygame.key.get_pressed()
            surface.fill((0, 0, 0))
            player.update()
            tutor_animation.update(stage)
            if player.attacking:
                player.attack()
            player.move()
            background.render()
            for ball in fireball_group:
                ball.fire()
            world.update(player)
            if world.dx != 0 or world.dy != 0:
                player.world_shift(world.dx, world.dy)
                for sprite in all_sprites.sprites():
                    if tutorial_group.has(sprite):
                        continue
                    sprite.rect = sprite.rect.move(world.dx, world.dy)
            other_group.draw(surface)
            surface.blit(player.image, player.rect)
            if stage == 7 and counter > 500:
                counter = 500
            elif counter == 850:
                if stage != 7:
                    stage += 1
                counter = 0
            counter += 1
            if stage == 0 and counter >= 450:
                text = special_font.render(word.get('stage0'),
                                           True, STAGES_COLOR)
            elif stage < 1:
                pass
            elif stage == 1:
                text = special_font.render(word.get('stage1'),
                                           True, STAGES_COLOR)
            elif stage == 2 and counter >= 500:
                text = special_font.render(word.get('stage2.1'),
                                           True, STAGES_COLOR)
            elif stage == 2:
                text = special_font.render(word.get('stage2'),
                                           True, STAGES_COLOR)
            elif stage == 3:
                text = special_font.render(word.get('stage3'),
                                           True, STAGES_COLOR)
            elif stage == 4:
                text = special_font.render(word.get('stage4'),
                                           True, STAGES_COLOR)
            elif stage == 5 and counter >= 500:
                text = special_font.render(word.get('stage5.1'),
                                           True, STAGES_COLOR)
            elif stage == 5:
                text = special_font.render(word.get('stage5'),
                                           True, STAGES_COLOR)
            elif stage == 6:
                text = special_font.render(word.get('stage6'),
                                           True, STAGES_COLOR)
            elif stage == 7 and counter > 450:
                text = special_font.render(word.get('stage7.1'),
                                           True, STAGES_COLOR)
            else:
                text = special_font.render(word.get('stage7'),
                                           True, STAGES_COLOR)
            if text:
                text_x = tile_size * 2
                text_y = int(tile_size * 1.5)
                surface.blit(text, (text_x, text_y))
            tutorial_group.draw(surface)
            if keys[pygame.K_ESCAPE]:
                player = None
            if intro_count > 0:
                intro_play()
            pygame.display.flip()
            FPS_CLOCK.tick(FPS)
    except AttributeError:
        player = None
        world = None
        for sprite in all_sprites.sprites():
            sprite.kill()
        FPS_CLOCK.tick(1)
    except IndexError:
        player = None
        world = None
        for sprite in all_sprites.sprites():
            sprite.kill()
        FPS_CLOCK.tick(1)


class CellBoard:
    land = pygame.transform.scale(load_image('land.png'), (tile_size, tile_size))
    stone1 = pygame.transform.scale(load_image('stone1.png'), (tile_size, tile_size))
    sand = pygame.transform.scale(load_image('sand.png'), (tile_size, tile_size))
    player_sprite = run_animation_RIGHT[0]
    bomb_sprite = bomb_idle[0]
    teleport = teleport_sprite
    bat_sprite = bat_sprite
    spike_sprite = spike_ball_sprite
    coin_sprite = coin_sprite

    objects = [(pygame.transform.scale(load_image('land.png'), (tile_size, tile_size)), 'L'),
               (pygame.transform.scale(load_image('stone1.png'), (tile_size, tile_size)), 'R'),
               (pygame.transform.scale(load_image('sand.png'), (tile_size, tile_size)), 'S'),
               (run_animation_RIGHT[0], 'P'),
               (bomb_idle[0], 'Y'),
               (bat_sprite, 'B'),
               (spike_ball_sprite, 'A'),
               (teleport_sprite, 'E'),
               (coin_sprite, 'C')]

    def __init__(self, level_name, l_width, l_height, borders=0, gr_info=(0, 0)):
        global background
        self.player_pos = -1, -1
        self.tile_on_player = ' '
        self.teleport_pos = -1, -1
        self.tile_on_teleport = ' '
        filename = os.path.join(CUSTOM_LEVELS_DIRECTORY, f'{level_name}.map')
        if l_width == l_height == -1:
            with open(filename, mode='r', encoding='utf8') as f:
                data = list()
                for y, line in enumerate(f.readlines()):
                    line = line.replace('\n', '')
                    if 'P' in line:
                        self.player_pos = line.index('P'), y
                    if 'E' in line:
                        self.teleport_pos = line.index('E'), y
                    data.append(line)
            index = 1
            try:
                background = Background(data[0])
                if self.player_pos[1] != -1:
                    self.player_pos = self.player_pos[0], self.player_pos[1] - 1
                if self.teleport_pos[1] != -1:
                    self.teleport_pos = self.teleport_pos[0], self.teleport_pos[1] - 1
            except FileNotFoundError:
                background = Background()
                index = 0
            self.board = [list(str(row).ljust(len(max(data[index:], key=len)), ' '))
                          for row in data[index:]]
        else:
            if borders != 0:
                border_block = self.objects[borders - 1][1]
                self.board = [[border_block for _ in range(l_width)]]
                self.board.extend([[border_block, *[' ' for _ in range(l_width - 2)], border_block]
                                   for _ in range(l_height - 2)])
                if gr_info[0] > 0:
                    ground_block = self.objects[gr_info[0] - 1][1]
                    for i in range(l_height - gr_info[1], l_height - 1):
                        self.board[i] = [border_block, *[ground_block for _ in range(l_width - 2)],
                                         border_block]
                self.board.append([border_block for _ in range(l_width)])
            else:
                height = gr_info[1] if gr_info[0] > 0 else 0
                self.board = [[' ' for _ in range(l_width)] for _ in range(l_height - height)]
                if gr_info[0] > 0:
                    ground_block = self.objects[gr_info[0] - 1][1]
                    for i in range(l_height - height, l_height):
                        self.board.append([ground_block for _ in range(l_width)])
            background = Background()
        self.width, self.height = len(self.board[0]), len(self.board)
        self.cur_tile = 'L'
        self.spare_tile = ' '
        self.dx = self.dy = 0
        self.s_dx = self.s_dy = 0
        self.prev_x, self.prev_y = -1, -1
        self.size = tile_size
        self.inventory_surf = pygame.Surface((tile_size * 9, tile_size * 6))
        self.counter = 140
        self.inventory_surf.set_alpha(self.counter)
        self.indent_x = (self.inventory_surf.get_width() - tile_size * 4) // 5
        y_count = ceil((len(self.objects) - 1) / 4 + 0.01)
        self.indent_y = (self.inventory_surf.get_height() - tile_size * y_count) // (y_count + 1)
        self.mouse_downed = False
        self.rect_draw = -1, -1
        self.rect_action = -1
        self.warning_text = None
        self.warn_counter = [-1, 0]

    def set_size(self, new_size):
        x, y = pygame.mouse.get_pos()
        x -= self.dx
        y -= self.dy
        new_y = int(y / self.size * new_size)
        new_x = int(x / self.size * new_size)
        self.dx = self.s_dx + (x - new_x)
        self.dy = self.s_dy + (y - new_y)
        self.s_dx = self.dx
        self.s_dy = self.dy
        self.size = new_size
        self.land = pygame.transform.scale(load_image('land.png'), (self.size, self.size))
        self.stone1 = pygame.transform.scale(load_image('stone1.png'), (self.size, self.size))
        self.sand = pygame.transform.scale(load_image('sand.png'), (self.size, self.size))
        self.bomb_sprite = pygame.transform.scale(bomb_idle[0], (self.size, self.size))
        self.teleport = pygame.transform.scale(teleport_sprite, (self.size, self.size))
        self.bat_sprite = pygame.transform.scale(bat_sprite, (self.size, self.size))
        self.spike_sprite = pygame.transform.scale(spike_ball_sprite, (self.size, self.size))
        self.spike_sprite = pygame.transform.scale(spike_ball_sprite, (self.size, self.size))
        self.coin_sprite = pygame.transform.scale(coin_sprite, (self.size, self.size))
        spr = run_animation_RIGHT[0]
        self.player_sprite = pygame.transform.scale(spr, (spr.get_width() * self.size // tile_size,
                                                          spr.get_height() * self.size // tile_size))

    def draw_item(self, x, y, value):
        if value == 'L':
            surface.blit(self.land, (x * self.size + self.dx, y * self.size + self.dy))
        elif value == 'R':
            surface.blit(self.stone1, (x * self.size + self.dx, y * self.size + self.dy))
        elif value == 'S':
            surface.blit(self.sand, (x * self.size + self.dx, y * self.size + self.dy))
        elif value == 'P':
            surface.blit(self.player_sprite, (x * self.size + self.dx, y * self.size + self.dy))
        elif value == 'Y':
            surface.blit(self.bomb_sprite, (x * self.size + self.dx, y * self.size + self.dy))
        elif value == 'E':
            surface.blit(self.teleport, (x * self.size + self.dx, y * self.size + self.dy))
        elif value == 'B':
            surface.blit(self.bat_sprite, (x * self.size + self.dx, y * self.size + self.dy))
        elif value == 'A':
            surface.blit(self.spike_sprite, (x * self.size + self.dx, y * self.size + self.dy))
        elif value == 'C':
            surface.blit(self.coin_sprite, (x * self.size + self.dx, y * self.size + self.dy))

    def render(self, screen):
        keys = pygame.key.get_pressed()
        mods = pygame.key.get_mods()
        y_start = 0
        for y, row in enumerate(self.board):
            for x, cell in enumerate(row):
                if (x_start := x * self.size + self.dx) + self.size < 0 \
                        or (y_start := y * self.size + self.dy) + self.size < 0 \
                        or x_start > WIDTH or y_start > HEIGHT:
                    continue
                self.draw_item(x, y, cell)
                if not (mods & pygame.KMOD_CTRL and keys[pygame.K_h]):
                    pygame.draw.rect(screen, CELL_COLOR,
                                     (x_start, y_start, self.size, self.size), width=CELL_WIDTH)
        if not (mods & pygame.KMOD_CTRL and keys[pygame.K_h]):
            x, y = pygame.mouse.get_pos()
            x -= self.dx
            y -= self.dy
            x, y = x // self.size, y // self.size
            if self.rect_draw != (-1, -1):
                draw_x, draw_y = self.rect_draw
                f_x, f_y = draw_x, draw_y
                w, h = x - draw_x + 1, y - draw_y + 1
                if draw_x > x:
                    f_x, w = x, draw_x - x + 1
                if draw_y > y:
                    f_y, h = y, draw_y - y + 1
                if f_x + w > self.width:
                    w = self.width - f_x
                if f_y + h > self.height:
                    h = self.height - f_y
                if f_x < 0:
                    w += f_x
                    f_x = 0
                if f_y < 0:
                    h += f_y
                    f_y = 0
                pygame.draw.rect(screen, CELL_CHOSEN_COLOR,
                                 (f_x * self.size + self.dx, f_y * self.size + self.dy,
                                  w * self.size, h * self.size))
            elif not self.inventory_surf.get_rect().collidepoint(x, y):
                if 0 <= y < len(self.board) and 0 <= x < len(self.board[0]):
                    pygame.draw.rect(screen, CELL_CHOSEN_COLOR,
                                     (x * self.size + self.dx, y * self.size + self.dy,
                                      self.size, self.size), width=CELL_WIDTH * 3)
            self.inventory_render()
        self.mouse_downed = False
        if self.warning_text is not None:
            center_x = WIDTH // 2
            text = mana_font.render(self.warning_text, True, pygame.Color('#B63C3C'))
            text.set_alpha(int(self.warn_counter[0]))
            text_h = HEIGHT * 0.055
            text_w = text.get_width() * text_h / text.get_height()
            surface.blit(pygame.transform.smoothscale(text, (text_w, text_h)),
                         (center_x - text_w // 2, HEIGHT * 0.1))
            self.warn_counter[0] += self.warn_counter[1]
            if self.warn_counter[0] >= 251 and self.warn_counter[1] > 0:
                self.warn_counter = [255, -0.8]
            elif self.warn_counter[0] <= 3 and self.warn_counter[1] < 0:
                self.clear_warning()

    def inventory_render(self):
        self.inventory_surf.fill((35, 35, 35))
        pos = pygame.mouse.get_pos()
        if self.inventory_surf.get_rect().collidepoint(pos) and self.prev_x == self.prev_y == -1 \
                and self.rect_draw == (-1, -1):
            if self.counter < 236:
                self.counter += 4
                self.inventory_surf.set_alpha(self.counter)
        else:
            if self.counter > 140:
                self.counter -= 6
                self.inventory_surf.set_alpha(self.counter)
        if not self.mouse_downed or not self.prev_x == self.prev_y == -1:
            pos = (-1, -1)
        for i, (obj, char) in enumerate(self.objects):
            x, y = i % 4, i // 4
            rect = obj.get_rect(topleft=(x * tile_size + (x + 1) * self.indent_x,
                                         y * tile_size + (y + 1) * self.indent_y))
            if rect.collidepoint(pos):
                self.cur_tile = char
            self.inventory_surf.blit(obj, rect.topleft)
            if char == self.cur_tile:
                pygame.draw.rect(self.inventory_surf, ITEM_CHOSEN_COLOR,
                                 (x * tile_size + (x + 1) * self.indent_x,
                                  y * tile_size + (y + 1) * self.indent_y,
                                  tile_size, tile_size), width=CELL_WIDTH * 3)
        surface.blit(self.inventory_surf, (0, 0))

    def mouse_down(self, button):
        self.mouse_downed = (button == 1)
        if self.inventory_surf.get_rect().collidepoint(pygame.mouse.get_pos()):
            return
        if pygame.key.get_mods() & pygame.KMOD_SHIFT \
                and (button == 1 and self.cur_tile not in 'PE' or button == 3):
            x, y = pygame.mouse.get_pos()
            x -= self.dx
            y -= self.dy
            ind_y = y // self.size
            ind_x = x // self.size
            if 0 <= ind_y < len(self.board) and 0 <= ind_x < len(self.board[0]):
                self.rect_draw = ind_x, ind_y
                self.rect_action = button
        if button == 2:
            self.prev_x, self.prev_y = pygame.mouse.get_pos()
        if button == 5 and self.size > tile_size // 5:
            self.set_size(self.size - 3)
        if button == 4 and self.size < tile_size * 7:
            self.set_size(self.size + 3)

    def mouse_up(self, button):
        if self.rect_draw != (-1, -1) and button == self.rect_action:
            x, y = pygame.mouse.get_pos()
            x -= self.dx
            y -= self.dy
            x, y = x // self.size, y // self.size
            draw_x, draw_y = self.rect_draw
            f_x, f_y = draw_x, draw_y
            w, h = x - draw_x + 1, y - draw_y + 1
            if draw_x > x:
                f_x, w = x, draw_x - x + 1
            if draw_y > y:
                f_y, h = y, draw_y - y + 1
            if f_x + w > self.width:
                w = self.width - f_x
            if f_y + h > self.height:
                h = self.height - f_y
            if f_x < 0:
                w += f_x
                f_x = 0
            if f_y < 0:
                h += f_y
                f_y = 0
            cur_tile = self.spare_tile if self.rect_action == 3 else self.cur_tile
            for y in range(f_y, f_y + h):
                for x in range(f_x, f_x + w):
                    self.board[y][x] = cur_tile
            self.rect_draw = -1, -1
        if button == 2:
            self.prev_x, self.prev_y = -1, -1
            self.s_dx = self.dx
            self.s_dy = self.dy

    def mouse_pressed(self):
        x, y = pygame.mouse.get_pos()
        if not self.prev_x == self.prev_y == -1:
            self.dx = self.s_dx + x - self.prev_x
            self.dy = self.s_dy + y - self.prev_y
        if self.inventory_surf.get_rect().collidepoint(x, y):
            return
        if self.rect_draw != (-1, -1):
            return
        x -= self.dx
        y -= self.dy
        ind_y = y // self.size
        ind_x = x // self.size
        if 0 <= ind_y < len(self.board) and 0 <= ind_x < len(self.board[0]):
            if pygame.mouse.get_pressed()[0]:
                if self.cur_tile == 'P' and self.board[ind_y][ind_x] != 'P':
                    player_x, player_y = self.player_pos
                    if self.board[player_y][player_x] == 'P':
                        if self.tile_on_player == 'E' and self.player_pos != self.teleport_pos:
                            self.board[player_y][player_x] = self.tile_on_player = ' '
                        else:
                            self.board[player_y][player_x] = self.tile_on_player
                    if self.tile_on_teleport == 'P':
                        self.tile_on_teleport = ' '
                    self.tile_on_player = self.board[ind_y][ind_x]
                    self.player_pos = ind_x, ind_y
                elif self.cur_tile == 'E' and self.board[ind_y][ind_x] != 'E':
                    tel_x, tel_y = self.teleport_pos
                    if self.board[tel_y][tel_x] == 'E':
                        if self.tile_on_teleport == 'P' and self.player_pos != self.teleport_pos:
                            self.board[tel_y][tel_x] = self.tile_on_teleport = ' '
                        else:
                            self.board[tel_y][tel_x] = self.tile_on_teleport
                    if self.tile_on_player == 'E':
                        self.tile_on_player = ' '
                    self.tile_on_teleport = self.board[ind_y][ind_x]
                    self.teleport_pos = ind_x, ind_y
                if self.player_pos == (ind_x, ind_y) and self.cur_tile != 'P':
                    self.player_pos = -1, -1
                    self.tile_on_player = ' '
                if self.teleport_pos == (ind_x, ind_y) and self.cur_tile != 'E':
                    self.teleport_pos = -1, -1
                    self.tile_on_teleport = ' '
                self.board[ind_y][ind_x] = self.cur_tile
            elif pygame.mouse.get_pressed()[2]:
                if self.player_pos == (ind_x, ind_y):
                    self.player_pos = -1, -1
                    self.tile_on_player = ' '
                if self.teleport_pos == (ind_x, ind_y):
                    self.teleport_pos = -1, -1
                    self.tile_on_teleport = ' '
                self.board[ind_y][ind_x] = self.spare_tile

    def key_pressed(self):
        keys = pygame.key.get_pressed()
        mods = pygame.key.get_mods()
        if keys[pygame.K_p] and mods & pygame.KMOD_CTRL:
            x, y = pygame.mouse.get_pos()
            if self.inventory_surf.get_rect().collidepoint(x, y):
                return
            x -= self.dx
            y -= self.dy
            ind_y = y // self.size
            ind_x = x // self.size
            if 0 <= ind_y < len(self.board) and 0 <= ind_x < len(self.board[0]):
                if self.player_pos != (ind_x, ind_y):
                    player_x, player_y = self.player_pos
                    if self.board[player_y][player_x] == 'P':
                        if self.tile_on_player == 'E' and self.player_pos != self.teleport_pos:
                            self.board[player_y][player_x] = self.tile_on_player = ' '
                        else:
                            self.board[player_y][player_x] = self.tile_on_player
                    self.tile_on_player = self.board[ind_y][ind_x]
                    self.player_pos = ind_x, ind_y
                    self.board[ind_y][ind_x] = 'P'

    def get_level_map(self):
        res_board = [''.join(row) + '\n' for row in self.board]
        return res_board

    def warning(self, warn_text):
        self.warning_text = warn_text
        self.warn_counter = [0, 5]

    def clear_warning(self):
        self.warn_counter = [-1, 0]
        self.warning_text = None


def restart_with_language(lang_menu, new_lang):
    new_lang = new_lang[0][1]
    if new_lang != cur_lang:
        cur = con.cursor()
        cur.execute('UPDATE settings SET value=? WHERE name="lang"', (new_lang,))
        con.commit()
        pygame.quit()
        con.close()
        sys.exit()
    else:
        lang_menu.disable()


def save_settings():
    global vol_music, vol_sound
    if new_music != vol_music:
        vol_music = new_music
        cur = con.cursor()
        cur.execute('UPDATE settings SET value=? WHERE name="music"', (new_music,))
        con.commit()
    if new_sound != vol_sound:
        vol_sound = new_sound
        cur = con.cursor()
        cur.execute('UPDATE settings SET value=? WHERE name="sound"', (new_sound,))
        con.commit()


def close_settings(setting_menu, update=1):
    global new_music, new_sound
    if update == 1:
        save_settings()
    else:
        set_music_volume([[0, vol_music]])
        set_sound_volume([[0, vol_sound]])
    setting_menu.disable()


def set_music_volume(value, *args):
    global new_music
    new_music = value[0][1]
    pygame.mixer.music.set_volume(new_music)


def set_sound_volume(value, *args):
    global new_sound
    new_sound = value[0][1]
    for sound in all_sounds:
        sound.set_default_volume(new_sound)


def choose_language():
    lang_menu = pygame_menu.Menu(word.get("choose lang"), WIDTH, HEIGHT,
                                 theme=pygame_menu.themes.THEME_DARK)
    lang_menu.add.label(word.get("warning lang"), font_color=pygame.Color('#B33A3A'))
    new_lang = lang_menu.add.selector(word.get("lang"), word.get("lang list"))
    lang_menu.select_widget(
        lang_menu.add.button(word.get("apply"),
                             lambda: restart_with_language(lang_menu, new_lang.get_value()))
    )
    lang_menu.add.button(word.get("back"), lang_menu.disable)
    lang_menu.mainloop(surface)


def settings_menu():
    submenu = pygame_menu.Menu(word.get("settings"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)
    submenu.add.selector(f'{word.get("music")}: ',
                         word.get(f"en/dis list {vol_music}"), onchange=set_music_volume)
    submenu.add.selector(f'{word.get("sound")}: ',
                         word.get(f"en/dis list {vol_sound}"), onchange=set_sound_volume)
    submenu.add.button(word.get("choose lang"), lambda: (save_settings(), choose_language()))
    submenu.add.button(word.get("apply"), lambda: close_settings(submenu))
    submenu.mainloop(surface)


def save_username(new_username):
    global username
    username = new_username
    cur = con.cursor()
    cur.execute('UPDATE settings SET value=? WHERE name="username"', (username,))
    con.commit()


def start_level_editor(level_name, l_width, l_height, borders=0, gr_info=(0, 0)):
    global background
    board = CellBoard(level_name, l_width, l_height, borders, gr_info)
    while True:
        background.render()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                con.close()
                sys.exit()
            if event.type == pygame.DROPFILE:
                try:
                    start_file = os.path.basename(event.file)
                    filename, file_extension = os.path.splitext(start_file)
                    if file_extension in ['.png', '.jpg', '.bmp']:
                        final_file = os.path.abspath(
                            os.path.join(os.path.join('data', 'backgrounds'), start_file))
                        if not os.path.isfile(final_file):
                            shutil.copyfile(event.file, final_file)
                        background = Background(start_file)
                except Exception:
                    pass
            if event.type == pygame.MOUSEBUTTONDOWN:
                board.mouse_down(event.button)
            if event.type == pygame.MOUSEBUTTONUP:
                board.mouse_up(event.button)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    if board.player_pos == board.teleport_pos == (-1, -1):
                        board.warning(word.get("warning player teleport"))
                    elif board.player_pos == (-1, -1):
                        board.warning(word.get("warning only player"))
                    elif board.teleport_pos == (-1, -1):
                        board.warning(word.get("warning only teleport"))
                    elif board.player_pos == board.teleport_pos:
                        if board.tile_on_player == 'E':
                            board.warning(word.get("warning only teleport"))
                        else:
                            board.warning(word.get("warning only player"))
                    else:
                        board.clear_warning()
                        save_level_menu(level_name, board.get_level_map())
                if event.key == pygame.K_ESCAPE:
                    return
        if background is None:
            break
        board.mouse_pressed()
        board.key_pressed()
        board.render(surface)
        pygame.display.flip()
        FPS_CLOCK.tick(FPS)


def save_level_func(level_name, level_map):
    global background
    Level.save_level(level_name, level_map, background.name)
    background = None


def save_level_menu(default_level_name, level_map):
    submenu = pygame_menu.Menu(word.get("save level"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)
    level_name = submenu.add.text_input(f'{word.get("level name")}: ', default=default_level_name)
    submenu.add.button(word.get("save level"),
                       lambda: (save_level_func(level_name.get_value(), level_map),
                                submenu.disable()))
    submenu.add.button(word.get("back"), submenu.disable)
    submenu.mainloop(surface)


def level_editor_menu():
    submenu = pygame_menu.Menu(word.get("level editor"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)
    level_name = submenu.add.text_input(f'{word.get("level name")}: ', default='test_level')
    submenu.add.button(word.get("start"),
                       lambda: level_editor_menu__next_step(level_name.get_value()))
    submenu.add.button(word.get("back"), submenu.disable)
    submenu.mainloop(surface)


def check_width_and_height(submenu, level_name, warning, l_width, l_height, borders, gr_info):
    if not l_width.isnumeric() or not l_height.isnumeric():
        warning.set_title(word.get("warning level 0"))
        warning.show()
        return
    else:
        l_width, l_height = int(l_width), int(l_height)
    if gr_info[0] != 0:
        blocks, height = gr_info
        if height.isnumeric():
            height = int(height)
        else:
            warning.set_title(word.get("warning level 6"))
            warning.show()
            return
        if height < 1:
            warning.set_title(word.get("warning level 7"))
            warning.show()
            return
    else:
        blocks = height = 0
    if l_width < 1 or l_height < 1:
        warning.set_title(word.get("warning level 1"))
        warning.show()
    elif l_width * l_height < 2:
        warning.set_title(word.get("warning level 2"))
        warning.show()
    elif borders[0][1] != 0 and (l_width - 2) * (l_height - 2) < 2:
        warning.set_title(word.get("warning level 4"))
        warning.show()
    elif blocks != 0 and l_width * (l_height - height) < 2:
        warning.set_title(word.get("warning level 5"))
        warning.show()
    elif blocks != 0 and borders[0][1] != 0 and (l_width - 2) * (l_height - height - 1) < 2:
        warning.set_title(word.get("warning level 5"))
        warning.show()
    elif l_width * l_height > 10626:
        warning.set_title(word.get("warning level 3"))
        warning.show()
    else:
        submenu.disable()
        start_level_editor(level_name, l_width, l_height, borders[0][1], (blocks, height))


def level_editor_menu__next_step(level_name):
    filename = os.path.join(CUSTOM_LEVELS_DIRECTORY, f'{level_name}.map')
    if os.path.isfile(filename):
        start_level_editor(level_name, -1, -1)
        return
    submenu = pygame_menu.Menu(word.get("level editor"), WIDTH, HEIGHT,
                               theme=pygame_menu.themes.THEME_DARK)
    warning = submenu.add.label(word.get("warning level 1"), font_color=pygame.Color('#B33A3A'))
    warning.hide()
    l_width = submenu.add.text_input(f'{word.get("width")} {word.get("size desc")}: ',
                                     default=(WIDTH // tile_size + 1),
                                     onchange=lambda *_: warning.hide())
    l_height = submenu.add.text_input(f'{word.get("height")} {word.get("size desc")}: ',
                                      default=20, onchange=lambda *_: warning.hide())
    border_blocks = submenu.add.selector(f'{word.get("borders")}: ', word.get(f"blocks list"))
    ground_b = submenu.add.selector(f'{word.get("ground block")}: ', word.get(f"blocks list"))
    ground_h = submenu.add.text_input(f'{word.get("ground height")}: ',
                                      default=3, onchange=lambda *_: warning.hide())
    ground_h.hide()

    def change_ground(value, index):
        ground_h.hide() if value[0][1] == 0 else ground_h.show()

    ground_b.set_onchange(change_ground)
    submenu.add.button(word.get("start"), lambda: check_width_and_height(submenu, level_name,
                                                                         warning,
                                                                         l_width.get_value(),
                                                                         l_height.get_value(),
                                                                         border_blocks.get_value(),
                                                                         (ground_b.get_value()[0][1],
                                                                          ground_h.get_value())))
    submenu.add.button(word.get("back"), submenu.disable)
    submenu.mainloop(surface)


menu = pygame_menu.Menu(word.get("welcome"), WIDTH, HEIGHT,
                        theme=pygame_menu.themes.THEME_DARK)

text_input = menu.add.text_input(f'{word.get("name")}: ', default=username, onchange=save_username)

menu.add.button(word.get("play"), play_menu)
menu.add.button(word.get("tutor"), start_tutorial)
menu.add.button(word.get("level editor"), level_editor_menu)
menu.add.button(word.get("share level"), share_level_menu)
menu.add.button(word.get("settings"), settings_menu)
menu.add.button(word.get("quit"), pygame_menu.events.EXIT)
menu.mainloop(surface)
con.close()
