import os
import sys
from itertools import product

import pygame
import pygame_menu

colors = {0: pygame.Color('black'),
          1: pygame.Color('white'),
          2: pygame.Color('red')}

pygame.init()
surface = pygame.display.set_mode((1920, 1080))
pygame.key.set_repeat(1, 20)


class Board:
    # создание поля
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.board = [[0] * width for _ in range(height)]
        # значения по умолчанию
        self.left = 10
        self.top = 10
        self.cell_size = 30

    # настройка внешнего вида
    def set_view(self, left, top, cell_size):
        self.left = left
        self.top = top
        self.cell_size = cell_size

    def render(self, screen):
        for x, y in product(range(self.width), range(self.height)):
            pygame.draw.rect(screen,
                             colors[1],
                             (self.left + x * self.cell_size, self.top + y * self.cell_size,
                              self.cell_size, self.cell_size),
                             1)
            if self.board[y][x] == 0:
                surface.blit(grass_image, (self.left + x * self.cell_size, self.top + y * self.cell_size))

    def get_cell(self, mouse_pos):
        x, y = mouse_pos

        cell = (x - self.left) // self.cell_size, (y - self.top) // self.cell_size
        if 0 <= cell[0] < self.width and 0 <= cell[1] < self.height:
            return cell

    def on_click(self, cell_coords):
        pass

    def get_click(self, mouse_pos):
        try:
            cell = self.get_cell(mouse_pos)
            self.on_click(cell)
        except TypeError:
            return


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


image = load_image("creature.png", -1)
grass_image = pygame.transform.scale(load_image("grass.png"), (40, 40))


def set_difficulty(value, difficulty):
    pass


def start_the_game():
    board = Board(80, 80)
    fps = 60
    pos = [0, 0]
    clock = pygame.time.Clock()
    board.set_view(0, 0, 40)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                pass
            if event.type == pygame.KEYDOWN:
                if pygame.key.get_pressed()[pygame.K_DOWN]:
                    pos[1] += 10
                if pygame.key.get_pressed()[pygame.K_UP]:
                    pos[1] -= 10
                if pygame.key.get_pressed()[pygame.K_RIGHT]:
                    pos[0] += 10
                if pygame.key.get_pressed()[pygame.K_LEFT]:
                    pos[0] -= 10
        surface.fill((0, 0, 0))
        board.render(surface)
        surface.blit(image, pos)
        pygame.display.flip()
        clock.tick(fps)


menu = pygame_menu.Menu('Welcome', 1920, 1080,
                        theme=pygame_menu.themes.THEME_DARK)

menu.add.text_input('Name :', default='John Doe')
menu.add.selector('Difficulty :', [('Hard', 3), ('Medium', 2), ('Easy', 1)], onchange=set_difficulty)
menu.add.button('Play', start_the_game)
menu.add.button('Quit', pygame_menu.events.EXIT)
menu.mainloop(surface)
