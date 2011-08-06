#!/usr/bin/env python
#
# Copyright 2003,2004,2005 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
from Image import *

#
# py_zpr class handles the mouse navigation for (z)oom, (p)an, (r)otate
#
# based upon and ported from gltzpr,
# by Nigel Stewart, http://www.nigels.com/glt/gltzpr/
#
# Though selection mechanism has been stripped out
#

class py_zpr:
   def __init__(self):
      self._left = 0.0
      self._right = 0.0
      self._bottom = 0.0
      self._top = 0.0
      self._zNear = -10.0
      self._zFar = 10.0

      self._mouseX = 0
      self._mouseY = 0
      self._mouseLeft = False
      self._mouseMiddle = False
      self._mouseRight = False

      self._dragPosX = 0.0
      self._dragPosY = 0.0
      self._dragPosZ = 0.0

      self._matrix = []

      self.getMatrix()

      glutReshapeFunc(self.zprReshape)
      glutMouseFunc(self.zprMouse)
      glutMotionFunc(self.zprMotion)

   def zprReshape(self, w, h):
      glViewport(0,0,w,h)

      self._top = 1.0
      self._bottom = -1.0
      self._left = -w/h
      self._right = -self._left

      glMatrixMode(GL_PROJECTION)
      glLoadIdentity()
      glOrtho(self._left,self._right,self._bottom,self._top,self._zNear,self._zFar)
      glMatrixMode(GL_MODELVIEW)
    
   def zprMouse(self, button, state, x, y):

      self._mouseX = x
      self._mouseY = y

      if (state == GLUT_UP):
         if (button == GLUT_LEFT_BUTTON): self._mouseLeft = False
         elif (button == GLUT_MIDDLE_BUTTON): self._mouseMiddle = False
         elif (button == GLUT_RIGHT_BUTTON): self._mouseRight = False
      elif (state == GLUT_DOWN):
         if (button == GLUT_LEFT_BUTTON): self._mouseLeft = True
         elif (button == GLUT_MIDDLE_BUTTON): self._mouseMiddle = True
         elif (button == GLUT_RIGHT_BUTTON): self._mouseRight = True

      vp = glGetIntegerv(GL_VIEWPORT)
      (self._dragPosX, self._dragPosY, self._dragPosZ) = self.pos(x,y,vp)
      glutPostRedisplay()

   def zprMotion(self, x, y):
      changed = False
      dx = x - self._mouseX
      dy = y - self._mouseY

      vp = glGetIntegerv(GL_VIEWPORT)

      if (dx == 0) and (dy == 0): return

      if (self._mouseMiddle) or (self._mouseLeft and self._mouseRight):
         
         # ROTATE
         ax = dy
         ay = dx
         az = 0.0;
         angle = self.vlen(ax,ay,az) / (vp[2] + 1) * 180.0
         
         glRotatef(angle,ax,ay,az)
         
         changed = True
         
      elif(self._mouseLeft):

         # TRANSLATE
         (px,py,pz) = self.pos(x,y,vp)
         
         glLoadIdentity()
         glTranslatef(px-self._dragPosX,py-self._dragPosY,pz-self._dragPosZ)
         glMultMatrixd(self._matrix)
         
         self._dragPosX = px
         self._dragPosY = py
         self._dragPosZ = pz
         
         changed = True;

      elif (self._mouseRight):            

         # ZOOM
         s = Numeric.exp(dy * 0.01)

         glScale(s,s,s)
         changed = True

      self._mouseX = x;
      self._mouseY = y;

      if (changed):
         self.getMatrix()
         glutPostRedisplay()


   def vlen(self,x,y,z):
      return Numeric.sqrt(x*x+y*y+z*z)

   def pos(self,x,y,viewport):
      #Use the ortho projection and viewport information
      #to map from mouse co-ordinates back into world
      #co-ordinates

      px = ((float(x) - viewport[0]) / viewport[2])
      py = ((float(y) - viewport[1]) / viewport[3])

      px = self._left + (px * (self._right - self._left) )
      py = self._top + (py * (self._bottom - self._top) )
      pz = self._zNear

      return(px,py,pz)

   def getMatrix(self):
      self._matrix = glGetDoublev(GL_MODELVIEW_MATRIX)

#
#
# The basic setup and display class
#
#

class glDisplay (py_zpr):
   def __init__(self):
      # glut init stuff
      glutInit([])

      glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)

      glShadeModel(GL_SMOOTH)
      glutInitWindowSize(1200, 800)
      #glutInitWindowSize(600,400)
      self.win = glutCreateWindow('gr_gl display')
      py_zpr.__init__(self)

      self.pause_redisplay = False

      # this is the default view
      self.default_matrix = [[ 0.02 , 0.0 , -0.02 , 0.0 ],
                             [ 0.0 , 0.02 , 0.01 , 0.0 ],
                             [ 0.02 , -0.01 , 0.02 , 0.0 ],
                             [ 0.03 , -0.08 , 0.0 , 1.0 ]]

      glutDisplayFunc(self.display)
      glutKeyboardFunc(self.keyboard)
      glutIdleFunc(self.idle)
      self.gl_init()

      self.grid_color = (0.05,0.05,0.05)
      
      glutMainLoop()

   def __del__(self):
      glutDestroyWindow(self.win)

   def compile_data(self, data_callback):
      self.display_list = glGenLists(1)
      glNewList(self.display_list, GL_COMPILE)
      self.zx_grid()
      data_callback()
      glEndList()

   def get_predefined_view(self,key):
      matrix = []
      
      if key == "M":
         # During display, hit m
         # copy and paste matrix here
         # paste model view matrix here
         matrix = self.default_matrix
      elif key == "1":
         matrix = [[ 0.02 , 0.0 , 0.0 , 0.0 ],
                   [ 0.0 , 0.02 , 0.0 , 0.0 ],
                   [ 0.0 , 0.0 , 0.02 , 0.0 ],
                   [ -0.06 , 0.05, 0.0 , 1.0 ]]
      elif key == "2":
         matrix = [[ 0.02 , 0.0 , 0.0 , 0.0 ],
                   [ -0.0 , 0.0 , 0.02 , 0.0 ],
                   [ -0.0 , -0.02 , 0.0 , 0.0 ],
                   [ 0.06 , 0.05 , 0.0 , 1.0 ]]
      elif key == "3":
         matrix = self.default_matrix
      elif key == "4":
         matrix = [[ 0.01 , 0.0 , 0.01 , 0.0 ],
                   [ -0.0 , 0.02 , 0.01 , 0.0 ],
                   [ -0.01 , -0.0 , 0.01 , 0.0 ],
                   [ -0.06 , 0.15 , 0.0 , 1.0 ]]

      return matrix
      
   def keyboard(self, key, x, y):
      #print "Key GOT: ",key,x,y

      if key == "m":
         matrix = glGetDoublev(GL_MODELVIEW_MATRIX)
         for i in range(4):
            for j in range(4):
               matrix[i][j] = round(matrix[i][j],2)
         
         print "Modelview Matrix:\n"
         print "matrix = [[",matrix[0][0],",",matrix[0][1],",",matrix[0][2],",",matrix[0][3],"],"
         print "          [",matrix[1][0],",",matrix[1][1],",",matrix[1][2],",",matrix[1][3],"],"
         print "          [",matrix[2][0],",",matrix[2][1],",",matrix[2][2],",",matrix[2][3],"],"
         print "          [",matrix[3][0],",",matrix[3][1],",",matrix[3][2],",",matrix[3][3],"]]"

      elif key == " ":
         if(self.pause_redisplay == False):
            self.pause_redisplay = True
         else:
            self.pause_redisplay = False

      else:
         # look for a predefined view
         matrix = self.get_predefined_view(key)
         if(len(matrix) != 0):
            glMatrixMode(GL_MODELVIEW)
            glLoadMatrixf(matrix)
            py_zpr.getMatrix(self)
            glutPostRedisplay()
 
   def idle(self):
      glutPostRedisplay()
      #overide me
      #print "Default Idle Callback"
      i = 1
   
   def gl_init(self):      
      light_ambient = [0.4, 0.4, 0.4, 1.0]
      light_diffuse = [0.5, 0.5, 0.5, 1.0]
      light_specular = [0.4, 0.4, 0.4, 1.0]
      light_position = [15.0, 15.0, 15.0]

      light2_position = [-15.0, 15.0, 15.0]

      glMatrixMode(GL_PROJECTION)
      glLoadIdentity()
      
      glClearColor(0, 0, 0, 0)
      glMatrixMode(GL_MODELVIEW)
      glLoadIdentity()

      glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
      glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
      glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)
      glLightfv(GL_LIGHT0, GL_POSITION, light_position)

      glLightfv(GL_LIGHT1, GL_AMBIENT, light_ambient)
      glLightfv(GL_LIGHT1, GL_DIFFUSE, light_diffuse)
      glLightfv(GL_LIGHT1, GL_SPECULAR, light_specular)
      glLightfv(GL_LIGHT1, GL_POSITION, light2_position)


      glEnable(GL_COLOR_MATERIAL)
      glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

      glFrontFace(GL_CW)
      glEnable(GL_LIGHTING)
      glEnable(GL_LIGHT0)
      glEnable(GL_LIGHT1)
      glEnable(GL_DEPTH_TEST)
      glDisable(GL_BLEND)

      glEnable(GL_TEXTURE_2D)

      glShadeModel(GL_SMOOTH)

      # set the default view
      #glMatrixMode(GL_MODELVIEW)
      glLoadMatrixf(self.default_matrix)
      py_zpr.getMatrix(self)

                       
   def setup_zx_grid(self, x_start=-20.0, x_end=20.0, x_rules=20, z_thickness=0.1, z_plot_history_size=20):
      x_each = (x_end - x_start)/x_rules

      # we'll extend x by 2 rules on either side for readibility
      x_start -= 2 * x_each
      x_end += 2 * x_each
      x_rules += 4

      y_pos = 2.0

      # we'll extend z also by two in front
      # not the most recent plot is in the back
      z_end = z_thickness * 2
      z_rules = z_plot_history_size + 1
      z_start = z_end - z_thickness*z_rules

      #grid_spec = (0.0, 0.0, 0.0)

      self.zx_grid_list = glGenLists(1)
      glNewList(self.zx_grid_list, GL_COMPILE);

      #glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, grid_spec)
      glColor3fv(self.grid_color)
      glNormal3f(0.0,1.0,0.0)

      glBegin(GL_LINES)

      #plot x rules first
      for i in range(x_rules + 1):
         x_pos = float(i*x_each + x_start)
         glVertex3f(x_pos, y_pos, z_start)
         glVertex3f(x_pos, y_pos, z_end)

      #now plot z rules
      for i in range(z_rules + 1):
         z_pos = float(i*z_thickness + z_start)
         glVertex3f(x_start, y_pos, z_pos)
         glVertex3f(x_end, y_pos, z_pos)
         
      glEnd()
      glEndList()

   def setup_xy_grid(self, x_start=-20.0, x_end=20.0, x_rules=20,
                     y_end=20.0, y_rules = 10,
                     z_thickness=0.1, z_plot_history_size=20):
      
      x_each = (x_end - x_start)/x_rules

      # we'll extend x by 2 rules on either side for readibility
      x_start -= 2 * x_each
      x_end += 2 * x_each
      x_rules += 4

      # we'll extend y also by two up top
      y_start = 2.0
      y_each = (y_end - y_start)/y_rules
      y_end += 2 * y_each

      # z is fixed at the current plot
      z_pos = -z_thickness * (z_plot_history_size - 1)

      #grid_spec = (0.0, 0.0, 0.0)

      self.xy_grid_list = glGenLists(1)
      glNewList(self.xy_grid_list, GL_COMPILE);

      #glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, grid_spec)
      glColor3fv(self.grid_color)
      glNormal3f(0.0,0.0,1.0)

      glBegin(GL_LINES)

      #plot x rules first
      for i in range(x_rules + 1):
         x_pos = float(i*x_each + x_start)
         glVertex3f(x_pos, y_start, z_pos)
         glVertex3f(x_pos, y_end, z_pos)

      #now plot y rules
      for i in range(y_rules + 3):
         y_pos = float(i*y_each + y_start)
         glVertex3f(x_start, y_pos, z_pos)
         glVertex3f(x_end, y_pos, z_pos)
         
      glEnd()
      glEndList()

   def display(self):
      glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
      #glCallList(self.display_list)

      self.img_map_plane()

      glutSwapBuffers()
      glFlush()
      
#
# demo class
#

class demo_class(glDisplay):
   def __init__(self):
      self.grid_ready = False
      glDisplay.__init__(self)
      
   def idle(self):
      if (self.grid_ready == False):
         self.setup_zx_grid()
         self.setup_xy_grid()
         self.grid_ready = True
      
   def display(self):
      glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

      teapot_amb = (1.0, 0.05, 0.05, 1.0)
      teapot_diff = (0.8, 0.2, 0.2)
      teapot_spec = (0.774587, 0.774597, 0.774597)
      teapot_shine = 0.80

      #glMaterialfv(GL_FRONT, GL_AMBIENT, teapot_amb)
      #glMaterialfv(GL_FRONT, GL_DIFFUSE, teapot_diff)
      glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, teapot_spec)
      glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, teapot_shine * 128.0)         

      glColor3f(0.8,0.0,0.0)
      glutSolidTeapot(1.0)

      if(self.grid_ready == True):
         glCallList(self.zx_grid_list)
         glCallList(self.xy_grid_list)

      glutSwapBuffers()
      glFlush()

def main ():
   gl = demo_class()

if __name__ == '__main__':
    main ()










