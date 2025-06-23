from game import main
import pygame
from pygame.locals import *
import sys
import math

WIDTH = 640
HEIGHT = 480
FPS = 120

pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Neco Adventures")
clock = pygame.time.Clock()


def draw_rotated_ellipse(surface, color, rect, angle):
    temp_surface = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.ellipse(temp_surface, color, (0, 0, rect[2], rect[3]))

    rotated_surface = pygame.transform.rotate(temp_surface, angle)
    rotated_rect = rotated_surface.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + rect[3] // 2))
    surface.blit(rotated_surface, rotated_rect.topleft)


def terminate():
    pygame.quit()
    sys.exit()


INTRO_MUSIC = "music/The_Green_Kingdom_-_Untitled_OST_Hot_Line_Miami_2_70196730.mp3"  # Replace with your music file


def start_screen():
    try:
        pygame.mixer.music.load(INTRO_MUSIC)
        pygame.mixer.music.play(-1)  # -1 = loop indefinitely
    except pygame.error as e:
        print(f"Could not load music: {e}")

    intro_text = ["Продолжить", "Новая игра", "Выход"]

    # Store rects for each menu item
    menu_rects = []
    selected_item = None

    bg = pygame.image.load("img/neco_title_wip1.png").convert()
    screen.blit(bg, (0, 0))

    font = pygame.font.Font(None, 28)
    text_coord = 67

    # Render menu items and store their rects
    for i, line in enumerate(intro_text):
        string_rendered = font.render(line, 1, pygame.Color('black'))
        intro_rect = string_rendered.get_rect()
        text_coord += 10
        intro_rect.top = text_coord
        intro_rect.x = 300
        text_coord += intro_rect.height

        rotated_text = pygame.transform.rotate(string_rendered, -7)
        rotated_rect = rotated_text.get_rect(center=intro_rect.center)

        screen.blit(rotated_text, rotated_rect)
        menu_rects.append((rotated_rect, i))  # Store rect and index

    while True:
        # Redraw background to clear previous highlights
        screen.blit(bg, (0, 0))

        # Get mouse position
        mouse_pos = pygame.mouse.get_pos()
        selected_item = None

        # Highlight and handle menu items
        for rect, index in menu_rects:
            # Check if mouse is over this item
            if rect.collidepoint(mouse_pos):
                selected_item = index
                # Draw highlight
                pygame.draw.rect(screen, (200, 200, 200, 128), rect, 2)

            # Render the text again (with potential different color if selected)
            color = pygame.Color('red') if index == selected_item else pygame.Color('black')
            string_rendered = font.render(intro_text[index], 1, color)
            rotated_text = pygame.transform.rotate(string_rendered, -7)
            screen.blit(rotated_text, rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                print(mouse_pos)
                if event.button == 1:  # Left mouse button
                    for rect, index in menu_rects:
                        if rect.collidepoint(event.pos):
                            return index  # Return the selected menu index
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    terminate()
                elif event.key == pygame.K_RETURN:
                    if selected_item is not None:
                        return selected_item

        pygame.display.flip()
        clock.tick(FPS)


# Call the function and handle the return value
selected_option = start_screen()
pygame.mixer.music.stop()
if selected_option == 0:
    # Продолжить
    main()
elif selected_option == 1:
    # Новая игра
    main()
elif selected_option == 2:
    # Выход
    terminate()
