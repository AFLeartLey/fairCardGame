import pygame
from pygame.locals import *
import sys
SCREEN_SIZE = (800, 600)

def main():
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    pygame.display.set_caption("Simple Pygame Window")
    font = pygame.font.SysFont("Noto Sans SC", 36)

    while True:
        screen.fill((0, 0, 0))  # Fill the screen with black

        text = font.render("Hello, Pygame!", True, (255, 255, 255))
        screen.blit(text, (SCREEN_SIZE[0] // 2 - text.get_width() // 2, SCREEN_SIZE[1] // 2 - text.get_height() // 2))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
  
if __name__ == "__main__":
    main()