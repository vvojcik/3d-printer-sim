import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

vertices = ((-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1),
            (1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)) 
edges = ((0, 6), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), 
         (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
faces = ((0, 1, 2 , 3), (4, 5, 6, 7), (0, 4, 7, 3), 
         (1, 5, 6, 2), (2, 6, 7, 3), (1, 5, 4, 0))

normals = [
    (-1, 0, 0), (1, 0, 0), (0, -1, 0),
    (0, 1, 0), (0, 0, 1), (0, 0, -1)
]

def draw_cube(pos, size, color):
    x, y, z = pos
    sx, sy, sz = size
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    glBegin(GL_QUADS)
    glColor3fv(color)
    for face in faces:
        for vertex in face:
            glVertex3fv(vertices[vertex])
    glEnd()

    glBegin(GL_LINES)
    glColor3fv((0, 0, 0))
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()
    glPopMatrix()

def draw_cylinder(pos, height, radius, color):
    x, y, z = pos
    glPushMatrix()
    glColor3fv(color)
    glTranslatef(x, y, z)
    glRotatef(-90, 1, 0, 0)
    quad = gluNewQuadric()
    gluQuadricNormals(quad, GLU_SMOOTH)
    gluDisk(quad, 0, radius, 64, 1)
    gluCylinder(quad, radius, radius, height, 64, 64)
    glTranslatef(0, 0, height)
    gluDisk(quad, 0, radius, 64, 1)
    gluDeleteQuadric(quad)
    glPopMatrix()