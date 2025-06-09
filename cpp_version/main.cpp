#include <GL/freeglut.h>
#include <cmath>
#include <set>
#include <tuple>
#include <queue>
#include <string>
#include <vector>
#include <iostream>
#include "render_utils.h"

// --- STATE VARIABLES ---
float bed_z_pos = 0.225f;
float gantry_y_pos = -0.6f;
float nozzle_x_pos = 0.0f;

const float NEUTRAL_Y_GANTRY = -0.6f;
const float NEUTRAL_X_NOZZLE = 0.0f;
const float NEUTRAL_Z_BED = 0.225f;

const float Z_OFFSET = 0.225f;
const float NOZZLE_OFFSET = 0.05f + 0.15f + 0.025f;
const float INK_OFFSET = NOZZLE_OFFSET + 0.025f + 0.01f;

bool view_mode = false;
bool render_printer = true;
bool is_printing = false;
bool is_neutralizing = false;
int clear_stage = 0;
std::string queued_print_job = "";

bool anim_delete = false;
int last_delete_time = 0;
int last_block_time = 0;
int last_step_time = 0;
const int STEP_DELAY = 10;
const int DELETE_DELAY = 100;
const int MANUAL_PRINT_SPEED = 120;

std::set<std::tuple<float, float, float>> cubes;

// --- MOUSE & CAMERA ---
bool button_down = false;
int last_mouse_x = 0;
int last_mouse_y = 0;
float cam_rot_x = 20.0f;
float cam_rot_y = 0.0f;
float cam_zoom = -5.0f;

// --- KEYBOARD STATE ---
bool keys[256] = { false };

// --- COMMAND QUEUE (Zastępuje Pythonowe 'yield') ---
enum CmdType { SET_HEAD_X, SET_GANTRY_Y, LAYER_DOWN, PRINT_BLOCK, RESET_BED_Z, FINISHED };
struct Command {
    CmdType type;
    float val, x, y, z;
};
std::queue<Command> print_queue;

// --- UTILS ---
void draw_cube(float x, float y, float z, float sx, float sy, float sz, float r, float g, float b) {
    glPushMatrix();
    glTranslatef(x, y, z);
    glScalef(sx, sy, sz);
    glColor3f(r, g, b);
    glutSolidCube(2.0);
    glColor3f(0, 0, 0);
    glutWireCube(2.01);
    glPopMatrix();
}

void draw_cylinder(float x, float y, float z, float height, float radius, float r, float g, float b) {
    glPushMatrix();
    glColor3f(r, g, b);
    glTranslatef(x, y, z);
    glRotatef(-90.0f, 1.0f, 0.0f, 0.0f);
    GLUquadric* quad = gluNewQuadric();
    gluQuadricNormals(quad, GLU_SMOOTH);
    gluDisk(quad, 0, radius, 64, 1);
    gluCylinder(quad, radius, radius, height, 64, 64);
    glTranslatef(0, 0, height);
    gluDisk(quad, 0, radius, 64, 1);
    gluDeleteQuadric(quad);
    glPopMatrix();
}

void draw_printer_structure() {
    if (!render_printer) return;
    draw_cube(-0.5f, -0.925f, 0.0f, 0.1f, 0.025f, 1.25f, 0.1f, 0.1f, 0.1f);
    draw_cube(0.5f, -0.925f, 0.0f, 0.1f, 0.025f, 1.25f, 0.1f, 0.1f, 0.1f);
    draw_cube(0.0f, -0.8825f, bed_z_pos, 1.0f, 0.015f, 1.0f, 0.6f, 0.6f, 0.65f);
    draw_cube(0.0f, -1.05f, 0.0f, 1.5f, 0.1f, 1.5f, 0.4f, 0.5f, 0.6f);
    draw_cylinder(-1.25f, -1.0f, 0.0f, 2.0f, 0.2f, 0.3f, 0.4f, 0.45f);
    draw_cylinder(1.25f, -1.0f, 0.0f, 2.0f, 0.2f, 0.3f, 0.4f, 0.45f);
    draw_cylinder(-1.25f, 1.0f, 0.0f, 0.25f, 0.2f, 0.1f, 0.1f, 0.1f);
    draw_cylinder(1.25f, 1.0f, 0.0f, 0.25f, 0.2f, 0.1f, 0.1f, 0.1f);
    draw_cube(-1.25f, 0.1f, 0.2f, 0.05f, 0.9f, 0.01f, 0.05f, 0.05f, 0.05f);
    draw_cube(1.25f, 0.1f, 0.2f, 0.05f, 0.9f, 0.01f, 0.05f, 0.05f, 0.05f);
    draw_cube(0.0f, 1.1f, 0.0f, 1.2f, 0.05f, 0.03f, 0.1f, 0.1f, 0.1f);
    draw_cube(0.0f, gantry_y_pos, Z_OFFSET, 1.4f, 0.05f, 0.03f, 0.05f, 0.05f, 0.05f);
    draw_cube(nozzle_x_pos, gantry_y_pos - 0.05f, Z_OFFSET, 0.15f, 0.15f, 0.15f, 0.0f, 0.8f, 0.0f);
    draw_cube(nozzle_x_pos, gantry_y_pos - NOZZLE_OFFSET, Z_OFFSET, 0.025f, 0.025f, 0.025f, 0.8f, 0.0f, 0.0f);
    draw_cube(nozzle_x_pos, gantry_y_pos - INK_OFFSET, Z_OFFSET, 0.01f, 0.01f, 0.01f, 0.0f, 0.0f, 1.0f);
}

// --- GENERATORS ---
void generate_cube_cmds(int n) {
    float SNAP = 0.02f;
    float y_rel = -0.86f - SNAP;
    for (int k = 0; k < n; k++) {
        y_rel += SNAP;
        print_queue.push({ SET_GANTRY_Y, y_rel + 0.26f, 0, 0, 0 });
        for (int j = 0; j < n; j++) {
            if (j > 0) print_queue.push({ LAYER_DOWN, 0, 0, 0, 0 });
            float z_c = j * SNAP;
            for (int i = 0; i < n; i++) {
                float x_rel = (i - (n - 1) / 2.0f) * SNAP;
                print_queue.push({ SET_HEAD_X, x_rel, 0, 0, 0 });
                print_queue.push({ PRINT_BLOCK, 0, x_rel, y_rel, z_c });
            }
        }
        print_queue.push({ RESET_BED_Z, (n - 1) * SNAP, 0, 0, 0 });
    }
    print_queue.push({ FINISHED, 0, 0, 0, 0 });
}

void generate_sphere_cmds(int radius) {
    float SNAP = 0.02f;
    float Y_START = -0.86f;
    for (int k_y = -radius; k_y <= radius; k_y++) {
        float y_rel = Y_START + (k_y + radius) * SNAP;
        float target_y = std::max((float)(y_rel + INK_OFFSET), NEUTRAL_Y_GANTRY);
        print_queue.push({ SET_GANTRY_Y, target_y, 0, 0, 0 });
        for (int k_z = -radius; k_z <= radius; k_z++) {
            if (k_z > -radius) print_queue.push({ LAYER_DOWN, 0, 0, 0, 0 });
            float z_c = k_z * SNAP;
            for (int k_x = -radius; k_x <= radius; k_x++) {
                float x_rel = k_x * SNAP;
                if ((k_x * k_x + k_y * k_y + k_z * k_z) <= radius * radius) {
                    print_queue.push({ SET_HEAD_X, x_rel, 0, 0, 0 });
                    print_queue.push({ PRINT_BLOCK, 0, x_rel, y_rel, z_c + 0.02f * radius });
                }
            }
        }
        if (k_y < radius) print_queue.push({ RESET_BED_Z, (2 * radius) * SNAP, 0, 0, 0 });
    }
    print_queue.push({ FINISHED, 0, 0, 0, 0 });
}

void set_neutral_position() {
    if (clear_stage == 0) {
        if (gantry_y_pos < NEUTRAL_Y_GANTRY) gantry_y_pos = std::min(gantry_y_pos + 0.02f, NEUTRAL_Y_GANTRY);
        else clear_stage = 1;
    }
    else if (clear_stage == 1) {
        if (nozzle_x_pos > NEUTRAL_X_NOZZLE) nozzle_x_pos = std::max(nozzle_x_pos - 0.01f, NEUTRAL_X_NOZZLE);
        else if (nozzle_x_pos < NEUTRAL_X_NOZZLE) nozzle_x_pos = std::min(nozzle_x_pos + 0.01f, NEUTRAL_X_NOZZLE);
        else clear_stage = 2;
    }
    else if (clear_stage == 2) {
        if (bed_z_pos > NEUTRAL_Z_BED) bed_z_pos = std::max(bed_z_pos - 0.01f, NEUTRAL_Z_BED);
        else if (bed_z_pos < NEUTRAL_Z_BED) bed_z_pos = std::min(bed_z_pos + 0.01f, NEUTRAL_Z_BED);
        else {
            is_neutralizing = false;
            clear_stage = 0;
            if (queued_print_job == "cube") { generate_cube_cmds(4); is_printing = true; queued_print_job = ""; }
            else if (queued_print_job == "sphere") { generate_sphere_cmds(10); is_printing = true; queued_print_job = ""; }
        }
    }
}

// --- RENDERING TEXT ---
void renderBitmapString(float x, float y, void* font, const char* string) {
    const char* c;
    glRasterPos2f(x, y);
    for (c = string; *c != '\0'; c++) {
        glutBitmapCharacter(font, *c);
    }
}

// --- MOUSE INPUT ---
void mouseClick(int button, int state, int x, int y) {
    if (button == GLUT_LEFT_BUTTON) {
        if (state == GLUT_DOWN) {
            button_down = true;
            last_mouse_x = x;
            last_mouse_y = y;
        }
        else if (state == GLUT_UP) {
            button_down = false;
        }
    }
}

void mouseMotion(int x, int y) {
    if (button_down) {
        float dx = (float)(x - last_mouse_x);
        float dy = (float)(y - last_mouse_y);
        cam_rot_y += dx * 0.1f;
        cam_rot_x += dy * 0.1f;
        last_mouse_x = x;
        last_mouse_y = y;
    }
}

void mouseWheel(int wheel, int direction, int x, int y) {
    if (view_mode) {
        cam_zoom += direction * 0.2f;
    }
    else if (!is_neutralizing && !is_printing) {
        if (direction > 0) gantry_y_pos = std::min(gantry_y_pos + 0.02f, 0.9f);
        else gantry_y_pos = std::max(gantry_y_pos - 0.02f, -0.6f);
    }
}

// --- KEYBOARD INPUT ---
void keyDown(unsigned char key, int x, int y) {
    keys[key] = true;

    if (key == 'e') {
        view_mode = !view_mode;
        render_printer = !view_mode;
    }
    if (!view_mode) {
        if (key == 'c' && !is_printing && !is_neutralizing && queued_print_job == "") {
            queued_print_job = "cube";
            is_neutralizing = true;
        }
        if (key == 'v' && !is_printing && !is_neutralizing && queued_print_job == "") {
            queued_print_job = "sphere";
            is_neutralizing = true;
        }
        if (key == 'r') {
            is_neutralizing = true;
        }
        if (key == 127) { // Klawisz DELETE (ASCII 127)
            if (!cubes.empty()) {
                anim_delete = true;
                last_delete_time = glutGet(GLUT_ELAPSED_TIME);
            }
        }
    }
}

void keyUp(unsigned char key, int x, int y) {
    keys[key] = false;
}

// --- LOGIC TICK ---
void update(int value) {
    int now = glutGet(GLUT_ELAPSED_TIME);

    // WASD Manual movement
    if (!view_mode) {
        if (keys[' ']) { // Spacja
            if (now - last_block_time > (1000 / MANUAL_PRINT_SPEED)) {
                float snap = 0.02f;
                float x = round(nozzle_x_pos / snap) * snap;
                float y = round((gantry_y_pos - INK_OFFSET) / snap) * snap;
                float z = round(-(bed_z_pos - Z_OFFSET) / snap) * snap;
                cubes.insert(std::make_tuple(x, y, z));
                last_block_time = now;
            }
        }
        if (!is_neutralizing && !is_printing) {
            if (keys['s'] && bed_z_pos > -0.595f) bed_z_pos -= 0.02f;
            if (keys['w'] && bed_z_pos < 1.045f) bed_z_pos += 0.02f;
            if (keys['a'] && nozzle_x_pos > -0.825f) nozzle_x_pos -= 0.02f;
            if (keys['d'] && nozzle_x_pos < 0.825f) nozzle_x_pos += 0.02f;
        }

        // Logic for printing
        if (is_printing) {
            if (now - last_step_time >= STEP_DELAY) {
                if (!print_queue.empty()) {
                    Command cmd = print_queue.front();
                    print_queue.pop();
                    switch (cmd.type) {
                    case SET_HEAD_X: nozzle_x_pos = cmd.val; break;
                    case SET_GANTRY_Y: gantry_y_pos = cmd.val; break;
                    case LAYER_DOWN: bed_z_pos -= 0.02f; break;
                    case PRINT_BLOCK: cubes.insert(std::make_tuple(cmd.x, cmd.y, cmd.z)); break;
                    case RESET_BED_Z: bed_z_pos += cmd.val; break;
                    case FINISHED: is_printing = false; is_neutralizing = true; break;
                    }
                    last_step_time = now;
                }
            }
        }

        if (is_neutralizing) set_neutral_position();
    }

    // Deleting animation
    if (anim_delete) {
        if (now - last_delete_time >= DELETE_DELAY) {
            if (!cubes.empty()) {
                cubes.erase(std::prev(cubes.end()));
                last_delete_time = now;
            }
            else {
                anim_delete = false;
            }
        }
    }

    glutPostRedisplay();
    glutTimerFunc(16, update, 0); // ~60 FPS
}

// --- MAIN RENDER ---
void display() {
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glLoadIdentity();

    glTranslatef(0.0f, 0.0f, cam_zoom);
    glRotatef(cam_rot_x, 1.0f, 0.0f, 0.0f);
    glRotatef(cam_rot_y, 0.0f, 1.0f, 0.0f);

    draw_printer_structure();

    for (const auto& cube : cubes) {
        draw_cube(std::get<0>(cube), std::get<1>(cube), std::get<2>(cube) + bed_z_pos, 0.01f, 0.01f, 0.01f, 0.0f, 0.0f, 1.0f);
    }

    // Render Text UI
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glLoadIdentity();
    gluOrtho2D(0, glutGet(GLUT_WINDOW_WIDTH), 0, glutGet(GLUT_WINDOW_HEIGHT));
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
    glLoadIdentity();
    glDisable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    glColor3f(0.0f, 0.0f, 0.0f);
    char text[128];
    snprintf(text, sizeof(text), "Nozzle XYZ: (%.3f, %.3f, %.3f)", nozzle_x_pos, gantry_y_pos - INK_OFFSET, Z_OFFSET);
    renderBitmapString(10.0f, glutGet(GLUT_WINDOW_HEIGHT) - 30.0f, GLUT_BITMAP_HELVETICA_18, text);

    glDisable(GL_BLEND);
    glEnable(GL_DEPTH_TEST);
    glPopMatrix();
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);

    glutSwapBuffers();
}

int main(int argc, char** argv) {
    glutInit(&argc, argv);
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH);
    glutInitWindowSize(1840, 1000);
    glutCreateWindow("3D Printer Simulator - C++ Native Port");

    glEnable(GL_DEPTH_TEST);
    glClearColor(1.0f, 1.0f, 1.0f, 1.0f);
    glMatrixMode(GL_PROJECTION);
    gluPerspective(45.0, 1840.0 / 1000.0, 0.1, 500.0);
    glMatrixMode(GL_MODELVIEW);

    glutDisplayFunc(display);

    // Podpięcie wszystkich wejść od użytkownika
    glutKeyboardFunc(keyDown);
    glutKeyboardUpFunc(keyUp);
    glutMouseFunc(mouseClick);
    glutMotionFunc(mouseMotion);
    glutMouseWheelFunc(mouseWheel);

    glutTimerFunc(16, update, 0);

    glutMainLoop();
    return 0;
}