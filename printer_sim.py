from render_utils import draw_cube, draw_cylinder
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import sys

sys.setrecursionlimit(10000)

bed_z_pos = 0.225
gantry_z_pos = -0.6
nozzle_x_pos = 0

def draw_printer_structure(blat_z, suwak_z, glowica_x):
    draw_cube((-0.5, -0.925, 0), (0.1, 0.025, 1.25), (0, 0, 0))
    draw_cube((0.5, -0.925, 0), (0.1, 0.025, 1.25), (0, 0, 0))
    draw_cylinder((-1.25, -1, 0), 2, 0.2, (0.3529, 0.4314, 0.4902))
    draw_cylinder((1.25, -1, 0), 2, 0.2, (0.3529, 0.4314, 0.4902))
    draw_cube((-1.25, 0.1, 0.2), (0.05, 0.9, 0.01), (0, 0, 0))
    draw_cube((1.25, 0.1, 0.2), (0.05, 0.9, 0.01), (0, 0, 0))
    draw_cylinder((-1.25, 1, 0), 0.25, 0.2, (0, 0, 0))
    draw_cylinder((1.25, 1, 0), 0.25, 0.2, (0, 0, 0))
    draw_cube((0, 1.1, 0), (1.2, 0.05, 0.03), (0, 0, 0))
    draw_cube((0, suwak_z, 0.225), (1.4, 0.05, 0.03), (0, 0, 0))
    draw_cube((glowica_x, suwak_z-0.05, 0.225), (0.15, 0.15, 0.15), (0, 1, 0))
    draw_cube((glowica_x, suwak_z-0.225, 0.225), (0.025, 0.025, 0.025), (1, 0, 0))

def main():
    global bed_z_pos, gantry_z_pos, nozzle_x_pos
    pygame.init()
    screen_width, screen_height = 1840, 1000
    display = pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("3D Printer Simulator - OpenGL")

    glClearColor(1, 1, 1, 1)
    gluPerspective(45, (screen_width / screen_height), 0.1, 500)
    glEnable(GL_DEPTH_TEST)
    glTranslatef(0, 0, -5)

    clock = pygame.time.Clock()
    button_down = False

    while True:
        button_down = pygame.mouse.get_pressed()[0] == 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0: gantry_z_pos = min(gantry_z_pos + 0.02, 0.9)
                elif event.y < 0: gantry_z_pos = max(gantry_z_pos - 0.02, -0.6)
            if event.type == pygame.MOUSEMOTION:
                if button_down and (event.rel[0] != 0 or event.rel[1] != 0):
                    glRotatef(event.rel[1] * 0.1, 1, 0, 0)
                    glRotatef(event.rel[0] * 0.1, 0, 1, 0)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_s] and bed_z_pos > -0.595: bed_z_pos -= 0.02
        if keys[pygame.K_w] and bed_z_pos < 1.045: bed_z_pos += 0.02
        if keys[pygame.K_a] and nozzle_x_pos > -0.825: nozzle_x_pos -= 0.02
        if keys[pygame.K_d] and nozzle_x_pos < 0.825: nozzle_x_pos += 0.02

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        draw_printer_structure(bed_z_pos, gantry_z_pos, nozzle_x_pos)
        pygame.display.flip()
        clock.tick(60)

if __name__ == '__main__':
    main()