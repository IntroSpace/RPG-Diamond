import os
import sys
import random

import pygame
import pygame_menu

pygame.init()
surface = pygame.display.set_mode((1920, 1080))
pygame.key.set_repeat(1, 20)
ACC = 0.3
FRIC = -0.10
COUNT = 0
vec = pygame.math.Vector2
FPS = 60
FPS_CLOCK = pygame.time.Clock()
pygame.display.set_caption("Game")


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


class Background(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.bgimage = pygame.transform.scale(load_image('background.png'), (1920, 1080))
        self.bgY = 0
        self.bgX = 0

    def render(self):
        surface.blit(self.bgimage, (self.bgX, self.bgY))


class Ground(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.transform.scale(load_image("ground.png"), (1920, 600))
        self.rect = self.image.get_rect()
        self.rect.y = 480

    def render(self):
        surface.blit(self.image, (self.rect.x, self.rect.y))


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()


class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()


def set_difficulty(value, difficulty):
    pass


def start_the_game():
    background = Background()
    ground = Ground()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                pass
            if event.type == pygame.KEYDOWN:
                pass
        surface.fill((0, 0, 0))
        background.render()
        ground.render()
        pygame.display.flip()
        FPS_CLOCK.tick(FPS)


menu = pygame_menu.Menu('Welcome', 1920, 1080,
                        theme=pygame_menu.themes.THEME_DARK)

menu.add.text_input('Name :', default='John Doe')
menu.add.selector('Difficulty :', [('Hard', 3), ('Medium', 2), ('Easy', 1)], onchange=set_difficulty)
menu.add.button('Play', start_the_game)
menu.add.button('Quit', pygame_menu.events.EXIT)
menu.mainloop(surface)
