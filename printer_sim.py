from render_utils import draw_cube, draw_cylinder
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import sys
import time

sys.setrecursionlimit(10000)

# Ustawienia poczatkowe maszyny
bed_z_pos = 0.225
gantry_z_pos = -0.6
nozzle_x_pos = 0

# Stany animacji
anim_clear = False
clear_stage = 0
anim_delete = False
last_delete_time = 0
delete_delay = 100 # ms

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

def generate_cube(n):
    SNAP_SIZE = 0.02
    y_block_relative = -0.86 - SNAP_SIZE
    for k in range(n):
        y_block_relative += SNAP_SIZE
        target_z_suwaka = y_block_relative + 0.26
        yield ("SET_SUWAK_Y", target_z_suwaka)
        for j in range(n):
            if j > 0: yield ("LAYER_DOWN",)
            z_c_for_block = j * SNAP_SIZE
            for i in range(n):
                x_block_relative = (i - (n - 1) / 2) * SNAP_SIZE
                yield ("SET_HEAD_X", x_block_relative)
                yield ("PRINT_BLOCK", (x_block_relative, y_block_relative, z_c_for_block))
        yield ("RESET_BLAT_Z", (n-1) * SNAP_SIZE)
    yield ("FINISHED",)

def generate_sphere(n_radius):
    SNAP_SIZE = 0.02
    Y_CENTER_PRINTER = -0.86
    if n_radius < 0: n_radius = 0
    current_z_print_level = 0

    for y_idx in range(-n_radius, n_radius + 1):
        y_block_abs = Y_CENTER_PRINTER + (y_idx * SNAP_SIZE)
        yield ("SET_SUWAK_Y", y_block_abs + 0.26)
        layer_downs = 0
        current_z_print_level += 4
        n_radius_sq = n_radius**2
        yz_corner_sq_sum = (abs(y_idx) + 0.5)**2

        for z_idx in range(-n_radius, n_radius + 1):
            min_x_idx = n_radius + 1
            max_x_idx = -n_radius - 1
            found_block = False
            curr_yz_sum = yz_corner_sq_sum + (abs(z_idx) + 0.5)**2

            for x_chk in range(-n_radius, n_radius + 1):
                if (abs(x_chk) + 0.5)**2 + curr_yz_sum <= n_radius_sq:
                    found_block = True
                    min_x_idx = min(min_x_idx, x_chk)
                    max_x_idx = max(max_x_idx, x_chk)

            if not found_block: continue
            if current_z_print_level > 0:
                yield ("LAYER_DOWN",)
                layer_downs += 1
            
            z_coord = current_z_print_level * SNAP_SIZE
            for x_idx in range(min_x_idx, max_x_idx + 1):
                if (abs(x_idx) + 0.5)**2 + curr_yz_sum <= n_radius_sq:
                    x_block_abs = x_idx * SNAP_SIZE
                    yield ("SET_HEAD_X", x_block_abs)
                    yield ("PRINT_BLOCK", (x_block_abs, y_block_abs, z_coord))
            current_z_print_level += 1
        if layer_downs > 0: yield ("RESET_BLAT_Z", layer_downs * SNAP_SIZE)
    yield ("FINISHED",)

def animate_clear_process():
    global bed_z_pos, gantry_z_pos, nozzle_x_pos, clear_stage, anim_clear
    if clear_stage == 0:
        if gantry_z_pos < 0.9: gantry_z_pos = min(gantry_z_pos + 0.02, 0.9)
        else: clear_stage = 1
    elif clear_stage == 1:
        if nozzle_x_pos > 0: nozzle_x_pos = max(nozzle_x_pos - 0.01, 0)
        elif nozzle_x_pos < 0: nozzle_x_pos = min(nozzle_x_pos + 0.01, 0)
        else: clear_stage = 2
    elif clear_stage == 2:
        if bed_z_pos > 0: bed_z_pos = max(bed_z_pos - 0.01, 0.)
        elif bed_z_pos < 0: bed_z_pos = min(bed_z_pos + 0.01, 0.)
        else:
            anim_clear = False
            clear_stage = 0

def main():
    clock = pygame.time.Clock()
    global bed_z_pos, gantry_z_pos, nozzle_x_pos, anim_clear, anim_delete, last_delete_time

    is_printing = False
    generator = None
    last_step_time = 0
    step_delay = 100 # ms

    pygame.init()
    pygame.font.init()
    screen_width, screen_height = 1840, 1000
    display = pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("3D Printer Simulator - OpenGL")

    glClearColor(1, 1, 1, 1)
    gluPerspective(45, (screen_width / screen_height), 0.1, 500)
    glEnable(GL_DEPTH_TEST)
    glTranslatef(0, 0, -5)

    button_down = False
    cubes = set()

    cube_display = glGenLists(1)
    glNewList(cube_display, GL_COMPILE)
    draw_cube((0, 0, 0), (0.01, 0.01, 0.01), (0, 0, 1))
    glEndList()

    fps_font = pygame.font.Font(None, 36)
    frame_times = []
    fps_update_interval = 1.0 
    last_fps_update_time = time.time()
    displayed_fps = 0

    while True:
        current_time = time.time()
        frame_times.append(current_time)
        while frame_times and frame_times[0] < current_time - (fps_update_interval + 0.5):
            frame_times.pop(0)

        if current_time - last_fps_update_time > fps_update_interval:
            if len(frame_times) > 1:
                time_span = frame_times[-1] - frame_times[0]
                if time_span > 0: displayed_fps = (len(frame_times) - 1) / time_span
            else: displayed_fps = 0
            last_fps_update_time = current_time

        button_down = pygame.mouse.get_pressed()[0] == 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c and not is_printing:
                    generator = generate_cube(4); is_printing = True
                if event.key == pygame.K_v and not is_printing:
                    generator = generate_sphere(5); is_printing = True
                if event.key == pygame.K_r:
                    anim_clear = True
                if event.key == pygame.K_DELETE and cubes:
                    anim_delete = True
                    last_delete_time = pygame.time.get_ticks()
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0: gantry_z_pos = min(gantry_z_pos + 0.02, 0.9)
                elif event.y < 0: gantry_z_pos = max(gantry_z_pos - 0.02, -0.6)
            if event.type == pygame.MOUSEMOTION:
                if button_down and (event.rel[0] != 0 or event.rel[1] != 0):
                    glRotatef(event.rel[1] * 0.1, 1, 0, 0)
                    glRotatef(event.rel[0] * 0.1, 0, 1, 0)

        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_SPACE]:
            now = time.time()
            snap = 0.02
            x = round(nozzle_x_pos / snap) * snap
            y = round((gantry_z_pos - 0.26) / snap) * snap
            z_offset = round(-(bed_z_pos - 0.225) / snap) * snap
            rounded_pos = (x, y, z_offset)
            if rounded_pos not in cubes: cubes.add(rounded_pos)

        if not anim_clear and not is_printing:
            if keys[pygame.K_s] and bed_z_pos > -0.595: bed_z_pos -= 0.02
            if keys[pygame.K_w] and bed_z_pos < 1.045: bed_z_pos += 0.02
            if keys[pygame.K_a] and nozzle_x_pos > -0.825: nozzle_x_pos -= 0.02
            if keys[pygame.K_d] and nozzle_x_pos < 0.825: nozzle_x_pos += 0.02

        if is_printing:
            now_ticks = pygame.time.get_ticks()
            if now_ticks - last_step_time >= step_delay:
                try:
                    command = next(generator)
                    if command[0] == "SET_HEAD_X": nozzle_x_pos = command[1]
                    elif command[0] == "SET_SUWAK_Y": gantry_z_pos = command[1]
                    elif command[0] == "LAYER_DOWN": bed_z_pos -= 0.02
                    elif command[0] == "PRINT_BLOCK": cubes.add(command[1])
                    elif command[0] == "FINISHED":
                        is_printing = False; generator = None; anim_clear = True
                    elif command[0] == "RESET_BLAT_Z": bed_z_pos += command[1]
                    last_step_time = now_ticks
                except StopIteration:
                    is_printing = False; generator = None

        if anim_clear: animate_clear_process()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        draw_printer_structure(bed_z_pos, gantry_z_pos, nozzle_x_pos)

        for x_c, y_c, z_c in cubes:
            glPushMatrix()
            glTranslatef(x_c, y_c, z_c + bed_z_pos)
            glCallList(cube_display)
            glPopMatrix()

        if anim_delete:
            now_ticks = pygame.time.get_ticks()
            if now_ticks - last_delete_time >= delete_delay:
                if cubes:
                    cubes.pop()
                    last_delete_time = now_ticks
                else:
                    anim_delete = False

        # FPS UI
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        gluOrtho2D(0, screen_width, 0, screen_height)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glDisable(GL_DEPTH_TEST); glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        fps_text = fps_font.render(f"FPS: {displayed_fps:.1f}", True, (0, 0, 0), (255,255,255,180))
        glRasterPos2i(10, screen_height - fps_text.get_height() - 10)
        glDrawPixels(fps_text.get_width(), fps_text.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, pygame.image.tostring(fps_text, "RGBA", True))

        glEnable(GL_DEPTH_TEST); glDisable(GL_BLEND)
        glMatrixMode(GL_PROJECTION); glPopMatrix()
        glMatrixMode(GL_MODELVIEW); glPopMatrix()

        pygame.display.flip()
        clock.tick(60)

if __name__ == '__main__':
    main()