from render_utils import draw_cube, draw_cylinder
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import sys
import time

sys.setrecursionlimit(10000)

# Initial positions
bed_z_pos = 0.225
gantry_y_pos = -0.6
nozzle_x_pos = 0

# Neutral positions
NEUTRAL_Y_GANTRY = -0.6
NEUTRAL_X_NOZZLE = 0.0
NEUTRAL_Z_BED = 0.225

# State variables
is_neutralizing = False
clear_stage = 0
queued_print_job = None
anim_delete = False
last_delete_time = 0
last_block_time = 0
is_printing = False
generator = None
last_step_time = 0
view_mode = False
render_printer = True

# Colors
c_legs = (0.1, 0.1, 0.1)
c_rails = (0.05, 0.05, 0.05)
c_platform = (0.6, 0.6, 0.65)
c_base = (0.4, 0.5, 0.6)
c_cylinder = (0.3, 0.4, 0.45)
c_caps = (0.1, 0.1, 0.1)
c_link = (0.1, 0.1, 0.1)
c_gantry = (0.05, 0.05, 0.05)
c_head = (0, 0.8, 0)
c_nozzle = (0.8, 0, 0)

# Constants
STEP_DELAY = 10 
DELETE_DELAY = 100 
MANUAL_PRINT_SPEED = 120
Z_OFFSET = 0.225
NOZZLE_OFFSET = 0.05 + 0.15 + 0.025
INK_OFFSET = NOZZLE_OFFSET + 0.025 + 0.01

def draw_printer_structure(blat_z, suwak_y, glowica_x):
    if render_printer:
        draw_cube((-0.5, -0.925, 0), (0.1, 0.025, 1.25), c_legs)
        draw_cube((0.5, -0.925, 0), (0.1, 0.025, 1.25), c_legs)
        draw_cube((0, -0.8825, blat_z), (1, 0.015, 1), c_platform)
        draw_cube((0, -1.05, 0), (1.5, 0.1, 1.5), c_base)
        draw_cylinder((-1.25, -1, 0), 2, 0.2, c_cylinder)
        draw_cylinder((1.25, -1, 0), 2, 0.2, c_cylinder)
        draw_cylinder((-1.25, 1, 0), 0.25, 0.2, c_caps)
        draw_cylinder((1.25, 1, 0), 0.25, 0.2, c_caps)
        draw_cube((-1.25, 0.1, 0.2), (0.05, 0.9, 0.01), c_rails)
        draw_cube((1.25, 0.1, 0.2), (0.05, 0.9, 0.01), c_rails)
        draw_cube((0, 1.1, 0), (1.2, 0.05, 0.03), c_link)
        draw_cube((0, suwak_y, Z_OFFSET), (1.4, 0.05, 0.03), c_gantry)
        draw_cube((glowica_x, suwak_y-0.05, Z_OFFSET), (0.15, 0.15, 0.15), c_head)
        draw_cube((glowica_x, suwak_y-NOZZLE_OFFSET, Z_OFFSET), (0.025, 0.025, 0.025), c_nozzle)
        draw_cube((glowica_x, suwak_y-INK_OFFSET, Z_OFFSET), (0.01, 0.01, 0.01), (0, 0, 1))

def generate_cube(n):
    SNAP = 0.02
    y_rel = -0.86 - SNAP
    for k in range(n):
        y_rel += SNAP
        yield ("SET_GANTRY_Y", y_rel + 0.26)
        for j in range(n):
            if j > 0: yield ("LAYER_DOWN",)
            z_c = j * SNAP
            for i in range(n):
                x_rel = (i - (n - 1) / 2) * SNAP
                yield ("SET_HEAD_X", x_rel)
                yield ("PRINT_BLOCK", (x_rel, y_rel, z_c))
        yield ("RESET_BED_Z", (n-1) * SNAP)
    yield ("FINISHED",)

def generate_sphere(radius):
    SNAP = 0.02
    Y_START = -0.86
    for k_y in range(-radius, radius + 1):
        y_rel = Y_START + (k_y + radius) * SNAP
        target_y = max(y_rel + INK_OFFSET, NEUTRAL_Y_GANTRY)
        yield ("SET_GANTRY_Y", target_y)
        for k_z in range(-radius, radius + 1):
            if k_z > -radius: yield ("LAYER_DOWN",)
            z_c = k_z * SNAP
            for k_x in range(-radius, radius + 1):
                x_rel = k_x * SNAP
                if (k_x**2 + k_y**2 + k_z**2) <= radius**2:
                    yield ("SET_HEAD_X", x_rel)
                    yield ("PRINT_BLOCK", (x_rel, y_rel, z_c + 0.02*radius))
        if k_y < radius:
            yield ("RESET_BED_Z", (2 * radius) * SNAP)
    yield ("FINISHED",)

def set_neutral_position():
    global bed_z_pos, gantry_y_pos, nozzle_x_pos, clear_stage, is_neutralizing
    global is_printing, generator, queued_print_job
    if clear_stage == 0:
        if gantry_y_pos < NEUTRAL_Y_GANTRY:
            gantry_y_pos = min(gantry_y_pos + 0.02, NEUTRAL_Y_GANTRY)
        else: clear_stage = 1
    elif clear_stage == 1:
        if nozzle_x_pos > NEUTRAL_X_NOZZLE:
            nozzle_x_pos = max(nozzle_x_pos - 0.01, NEUTRAL_X_NOZZLE)
        elif nozzle_x_pos < NEUTRAL_X_NOZZLE:
            nozzle_x_pos = min(nozzle_x_pos + 0.01, NEUTRAL_X_NOZZLE)
        else: clear_stage = 2
    elif clear_stage == 2:
        if bed_z_pos > NEUTRAL_Z_BED:
            bed_z_pos = max(bed_z_pos - 0.01, NEUTRAL_Z_BED)
        elif bed_z_pos < NEUTRAL_Z_BED:
            bed_z_pos = min(bed_z_pos + 0.01, NEUTRAL_Z_BED)
        else:
            is_neutralizing = False
            clear_stage = 0
            if queued_print_job == "cube":
                generator = generate_cube(4)
                is_printing = True
                queued_print_job = None
            elif queued_print_job == "sphere":
                generator = generate_sphere(10)
                is_printing = True
                queued_print_job = None

def main():
    global bed_z_pos, gantry_y_pos, nozzle_x_pos, is_neutralizing, anim_delete
    global last_delete_time, last_step_time, is_printing, last_block_time
    global generator, queued_print_job, INK_OFFSET, Z_OFFSET, view_mode, render_printer

    button_down = False
    cubes = set()
    clock = pygame.time.Clock()
    pygame.init()
    pygame.font.init()
    width, height = 1840, 1000
    display = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("3D Printer Simulator - OpenGL")
    glClearColor(1, 1, 1, 1)
    gluPerspective(45, (width / height), 0.1, 500)
    glEnable(GL_DEPTH_TEST)
    glTranslatef(0, 0, -5)
    
    cube_display = glGenLists(1)
    glNewList(cube_display, GL_COMPILE)
    draw_cube((0, 0, 0), (0.01, 0.01, 0.01), (0, 0, 1))
    glEndList()

    while True:
        button_down = pygame.mouse.get_pressed()[0] == 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    view_mode = not view_mode
                    render_printer = not view_mode
                if not view_mode:
                    if event.key == pygame.K_c:
                        if not is_printing and not is_neutralizing and queued_print_job is None:
                            queued_print_job = "cube"
                            is_neutralizing = True
                    if event.key == pygame.K_v:
                        if not is_printing and not is_neutralizing and queued_print_job is None:
                            queued_print_job = "sphere"
                            is_neutralizing = True
                    if event.key == pygame.K_r:
                        is_neutralizing = True
                    if event.key == pygame.K_DELETE:
                        if cubes:
                            anim_delete = True
                            last_delete_time = pygame.time.get_ticks()
            if event.type == pygame.MOUSEWHEEL:
                if view_mode:
                    glTranslatef(0, 0, event.y * 0.1)
                elif not is_neutralizing and not is_printing:
                    if event.y > 0: gantry_y_pos = min(gantry_y_pos + 0.02, 0.9)
            if event.type == pygame.MOUSEMOTION:
                if button_down and (event.rel[0] != 0 or event.rel[1] != 0):
                    glRotatef(event.rel[1] * 0.1, 1, 0, 0)
                    glRotatef(event.rel[0] * 0.1, 0, 1, 0)

        if not view_mode:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                now = time.time()
                if now - last_block_time > (1/MANUAL_PRINT_SPEED):
                    snap = 0.02
                    x = round(nozzle_x_pos / snap) * snap
                    y = round((gantry_y_pos - INK_OFFSET) / snap) * snap
                    z = round(-(bed_z_pos - Z_OFFSET) / snap) * snap
                    if (x, y, z) not in cubes:
                        cubes.add((x, y, z))
                    last_block_time = now

            if not is_neutralizing and not is_printing:
                if keys[pygame.K_s] and bed_z_pos > -0.595: bed_z_pos -= 0.02
                if keys[pygame.K_w] and bed_z_pos < 1.045: bed_z_pos += 0.02
                if keys[pygame.K_a] and nozzle_x_pos > -0.825: nozzle_x_pos -= 0.02
                if keys[pygame.K_d] and nozzle_x_pos < 0.825: nozzle_x_pos += 0.02

            if is_printing:
                now_ticks = pygame.time.get_ticks()
                if now_ticks - last_step_time >= STEP_DELAY:
                    try:
                        cmd = next(generator)
                        if cmd[0] == "SET_HEAD_X": nozzle_x_pos = cmd[1]
                        elif cmd[0] == "SET_GANTRY_Y": gantry_y_pos = cmd[1]  # <--- TUTAJ BYŁ BŁĄD, POPRAWIONE
                        elif cmd[0] == "LAYER_DOWN": bed_z_pos -= 0.02
                        elif cmd[0] == "PRINT_BLOCK": cubes.add(cmd[1])
                        elif cmd[0] == "FINISHED":
                            is_printing = False; generator = None; is_neutralizing = True
                        elif cmd[0] == "RESET_BED_Z": bed_z_pos += cmd[1]
                        last_step_time = now_ticks
                    except StopIteration:
                        is_printing = False; generator = None

            if is_neutralizing: set_neutral_position()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        draw_printer_structure(bed_z_pos, gantry_y_pos, nozzle_x_pos)
        
        for cx, cy, cz in cubes:
            glPushMatrix()
            glTranslatef(cx, cy, cz + bed_z_pos)
            glCallList(cube_display)
            glPopMatrix()

        if anim_delete:
            now_ticks = pygame.time.get_ticks()
            if now_ticks - last_delete_time >= DELETE_DELAY:
                if cubes:
                    cubes.pop()
                    last_delete_time = now_ticks
                else: anim_delete = False

        # UI Overlay
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        gluOrtho2D(0, width, 0, height)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glDisable(GL_DEPTH_TEST); glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        font = pygame.font.Font(None, 36)
        fps_surf = font.render(f"FPS: {clock.get_fps():.2f}", True, (0, 0, 0), (255, 255, 255, 180))
        glRasterPos2i(10, height - fps_surf.get_height() - 10)
        glDrawPixels(fps_surf.get_width(), fps_surf.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, pygame.image.tostring(fps_surf, "RGBA", True))

        font_sm = pygame.font.Font(None, 28)
        ink_text = f"Nozzle XYZ: ({nozzle_x_pos:.3f}, {gantry_y_pos-INK_OFFSET:.3f}, {Z_OFFSET:.3f})"
        ink_surf = font_sm.render(ink_text, True, (0, 0, 0), (255, 255, 255, 180))
        glRasterPos2i(10, height - fps_surf.get_height() - ink_surf.get_height() - 15)
        glDrawPixels(ink_surf.get_width(), ink_surf.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, pygame.image.tostring(ink_surf, "RGBA", True))

        glEnable(GL_DEPTH_TEST); glDisable(GL_BLEND)
        glMatrixMode(GL_PROJECTION); glPopMatrix()
        glMatrixMode(GL_MODELVIEW); glPopMatrix()

        pygame.display.flip()
        clock.tick(60)

if __name__ == '__main__': main()