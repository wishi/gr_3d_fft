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
# 

#from wxPython import wx
from gnuradio import gr
from gnuradio.wxgui import stdgui2
import wx
import gnuradio.wxgui.plot as plot
import Numeric
import os
import threading
from gr_gl import *
from gr_thread_messaging import *
import time
from OpenGL.GL import *
import math
from gnuradio import gru, window


from OpenGLContext.utilities import crossProduct
from OpenGLContext.vectorutilities import normalise

#default_fftsink_size = (640,240)
default_fftsink_size = (1280,400)



class fft_sink_base(object):
    def __init__(self, input_is_real=False, baseband_freq=0, y_per_div=10, ref_level=100,
                 sample_rate=1, fft_size=512, fft_rate=20,
                 average=False, avg_alpha=None, title=''):

        # initialize common attributes
        self.baseband_freq = baseband_freq
        self.y_divs = 8
        self.y_per_div=y_per_div
        self.ref_level = ref_level
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.fft_rate = fft_rate
        self.average = average
        if avg_alpha is None:
            self.avg_alpha = 2.0 / fft_rate
        else:
            self.avg_alpha = avg_alpha
        self.title = title
        self.input_is_real = input_is_real
        (self.r_fd, self.w_fd) = os.pipe()

    def set_y_per_div(self, y_per_div):
        self.y_per_div = y_per_div

    def set_ref_level(self, ref_level):
        self.ref_level = ref_level

    def set_average(self, average):
        self.average = average
        if average:
            self.avg.set_taps(self.avg_alpha)
        else:
            self.avg.set_taps(1.0)

    def set_avg_alpha(self, avg_alpha):
        self.avg_alpha = avg_alpha

    def set_baseband_freq(self, baseband_freq):
        self.baseband_freq = baseband_freq
        

class fft_sink_f(gr.hier_block2, fft_sink_base):
    def __init__(self, fg, parent, baseband_freq=0,
                 y_per_div=10, ref_level=100, sample_rate=1, fft_size=512,
                 fft_rate=20, average=False, avg_alpha=None, title='',
                 size=default_fftsink_size):

        fft_sink_base.__init__(self, input_is_real=True, baseband_freq=baseband_freq,
                               y_per_div=y_per_div, ref_level=ref_level,
                               sample_rate=sample_rate, fft_size=fft_size,
                               fft_rate=fft_rate,
                               average=average, avg_alpha=avg_alpha, title=title)
                               
        s2p = gr.serial_to_parallel(gr.sizeof_float, fft_size)
        one_in_n = gr.keep_one_in_n(gr.sizeof_float * fft_size,
                                     int(sample_rate/fft_size/fft_rate))

        mywindow = window.blackmanharris(fft_size)
        fft = gr.fft_vfc(self.fft_size, True, mywindow)
        #fft = gr.fft_vfc(fft_size, True, True)
        c2mag = gr.complex_to_mag(fft_size)
        self.avg = gr.single_pole_iir_filter_ff(1.0, fft_size)
        log = gr.nlog10_ff(20, fft_size)
        sink = gr.file_descriptor_sink(gr.sizeof_float * fft_size, self.w_fd)

        fg.connect (s2p, one_in_n, fft, c2mag, self.avg, log, sink)
        gr.hier_block.__init__(self, fg, s2p, sink)

        self.fg = fg
        self.gl_fft_window(self)




class fft_sink_c(gr.hier_block2, fft_sink_base):
    def __init__(self, fg, parent, baseband_freq=0,
                 y_per_div=10, ref_level=100, sample_rate=1, fft_size=512,
                 fft_rate=20, average=True, avg_alpha=None, title='',
                 size=default_fftsink_size):

        fft_sink_base.__init__(self, input_is_real=False, baseband_freq=baseband_freq,
                               y_per_div=y_per_div, ref_level=ref_level,
                               sample_rate=sample_rate, fft_size=fft_size,
                               fft_rate=fft_rate,
                               average=average, avg_alpha=avg_alpha, title=title)

        s2p = gr.serial_to_parallel(gr.sizeof_gr_complex, fft_size)
        one_in_n = gr.keep_one_in_n(gr.sizeof_gr_complex * fft_size, 
                                     int(sample_rate/fft_size/fft_rate))

        mywindow = window.blackmanharris(fft_size)
        fft = gr.fft_vcc(self.fft_size, True, mywindow)
        #fft = gr.fft_vcc(fft_size, True, True)
        c2mag = gr.complex_to_mag(fft_size)
        self.avg = gr.single_pole_iir_filter_ff(1.0, fft_size)
        log = gr.nlog10_ff(20, fft_size)
        sink = gr.file_descriptor_sink(gr.sizeof_float * fft_size, self.w_fd)

        fg.connect(s2p, one_in_n, fft, c2mag, self.avg, log, sink)
        # gr.hier_block.__init__(self, fg, s2p, sink)

        #print self.r_fd

        self.fg = fg
        self.win = gl_fft_window(self)

################################################################################

class input_watcher (threading.Thread):
    def __init__ (self, gl_fft_win):
        threading.Thread.__init__(self)
        self.gl_fft_win = gl_fft_win

        self.file_descriptor = gl_fft_win.file_descriptor
        self.fft_size = gl_fft_win.fft_size
        self.keep_running = True

        self.sample_rate = gl_fft_win.sample_rate
        self.baseband_freq = gl_fft_win.baseband_freq
        self.input_is_real = gl_fft_win.input_is_real

        #print self.file_descriptor

        self.points_subscriptions = subscription_service()
        self.points_subscriptions.add_client(self.gl_fft_win)

        self.stop_after = 2
        self.stop_after_count = self.stop_after
        
        self.start ()

    def run (self):
        while (self.keep_running):
            s = os.read (self.file_descriptor, gr.sizeof_float * self.fft_size)
            
            # if the pipe dies, then quit
            if not s:
                self.keep_running = False
                break
            
            dB = Numeric.fromstring (s, Numeric.Float32)
            L = len(dB)

            x = max(abs(self.sample_rate), abs(self.baseband_freq))

            if x >= 1e9:
                self.sf = 1e-9
                self.units = "GHz"
            elif x >= 1e6:
                self.sf = 1e-6
                self.units = "MHz"
            else:
                self.sf = 1e-3
                self.units = "kHz"
                
            if self.input_is_real:     # only plot 1/2 the points

                self.x_vals = ((Numeric.arrayrange (L/2)
                           * (self.sample_rate * self.sf / L))
                          + self.baseband_freq * self.sf)
                self.y_vals = dB[0:L/2]

                #points = Numeric.zeros((len(self.x_vals), 2), Numeric.Float64)
                #points[:,0] = self.x_vals
                #points[:,1] = self.y_vals
            else:
                # the "negative freqs" are in the second half of the array
                self.x_vals = ((Numeric.arrayrange (-L/2, L/2)
                           * (self.sample_rate * self.sf / L))
                          + self.baseband_freq * self.sf)
                self.y_vals = Numeric.concatenate ((dB[L/2:], dB[0:L/2]))
                #points = Numeric.zeros((len(self.x_vals), 2), Numeric.Float64)
                #points[:,0] = self.x_vals
                #points[:,1] = self.y_vals

                        
            # scale points 
            self.points_subscriptions.send_data((self.x_vals*40, self.y_vals/2))

            # post a glut redisplay
            # scale x,y vals a bit
            #self.gl_fft_win.x_vals = self.x_vals*30
            #self.gl_fft_win.y_vals = self.y_vals/2
            #self.gl_fft_win.redisplay()
            
########################################################################################

class gl_fft_window:
    def __init__(self,fftsink):
        self.gl_thread = gl_fft_thread(fftsink)

            
class gl_fft_thread (glDisplay, threading.Thread, subscriber):
    def __init__(self, fftsink):
        threading.Thread.__init__(self)
        subscriber.__init__(self)
        
        self.file_descriptor = fftsink.r_fd
        self.fft_size = fftsink.fft_size
        self.sample_rate = fftsink.sample_rate
        self.baseband_freq = fftsink.baseband_freq
        self.input_is_real = fftsink.input_is_real
        self.ok_flag = False
        self.z_pos = 0

        #
        # points to keep
        #
        self.x_vals = []
        self.y_vals = []
        self.y_vals_last = []

        # we keep a list of display lists... once
        # a plot is compiled, we keep it for later
        # display
        self.gl_disp_lists = []

        #
        # plot history size is the number of slices to display
        # thickness is the open gl thickness for each in the zx plane
        # plot_history_len is a counter used to record how many
        #   z-rows of data have been recorded. Only tracked up until
        #   plot history size, and helps us to pipeline the calculations
        #   a bit
        #
        self.plot_history_size = 20
        self.z_thickness = 3.0
        self.plot_history_len = 0

        #
        # In the plotting pipeline, we generate a list of quadrilaterals
        # for every new row of data added
        # We calculate normals for each quad, and also save the previous
        # one... We need this, when we actually tell openGL to build a
        # display list for a new row, we need to create an average of normals
        # for each point to get the colors right
        #
        self.quad_list = []
        self.last_quad_list = []

        #
        # keep a state variable for the grids display list,
        # so we can set it up after we have some notion of
        # the max value
        #
        self.grids_setup = False

        # setup opengl lighting for plot
        self.plot_spec = (0.774587, 0.774597, 0.774597)
        self.plot_shine = 0.80

        # keep max/min for all plots in the history to calc color range,
        # xy-plane grid
        self.mins_y = []
        self.maxes_y = []        

        #
        # this is an overall translation applied to all things
        # drawn. It's calculated later
        #
        # It's really intended just to shift the y_range
        # to be centered midway between max and min
        #
        # and the z range in the middle of the plot history
        #
        self.x_translate_amount = 0.0
        self.y_translate_amount = 0.0
        self.z_translate_amount = 0.0
              
        self.start()

    def run(self):
        # start thread for input watcher
        self.iwatcher = input_watcher(self)

        # LAST step, call parent constructor. This will enter
        # into gl main loop
        glDisplay.__init__(self)

    def redisplay(self):
        #self.x_vals = x_vals
        #self.y_vals = y_vals
        
        glutPostRedisplay()

    def idle(self):        
        #
        # idle condition is to wait for data and
        # display when received
        #
        # Not the best way to go... fix later
        #

        subscriber.wait_data(self)
        (self.x_vals, self.y_vals) = self.data_tuple
        subscriber.finish_data(self)
        glutPostRedisplay()
        
    def display(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if(len(self.x_vals) > 0):
            #glPushMatrix()
            #glTranslatef(0,-20,0)

            self.create_plot()
            #glPopMatrix()
            
            # FOR TESTING
            #glPushMatrix()
            #glTranslatef(0,0,0)
            #glutSolidTeapot(0.5)
            #glPopMatrix()
                
        glutSwapBuffers()
        glFlush()

    def create_plot(self):
        z_start = 0
        z_end = z_start - self.z_thickness

        if(self.plot_history_len < 1):
            #
            # We just save the very first plot of points
            # And track the min and max for color calculation
            #
            
            self.plot_history_len += 1
            self.y_vals_last = self.y_vals

            # save mins, maxes
            self.mins_y.append(min(self.y_vals))
            self.maxes_y.append(max(self.y_vals))

        if(self.plot_history_len < 2):
            #
            # We now have enough to start calculating the points for quads,
            # colors, their surface normals,
            # but not enough to generate the point normals
            #
            # For each point, we need to average the normals of the four
            # surrounding surfaces
            #
            self.plot_history_len += 1

            self.last_quad_list = self.precalculate_strip(self.z_thickness,
                                                          self.x_vals,
                                                          self.y_vals,
                                                          self.y_vals_last)
            
            # save y_vals for next time
            self.y_vals_last = self.y_vals

            # save mins, maxes
            self.mins_y.append(min(self.y_vals))
            self.maxes_y.append(max(self.y_vals))

        elif(self.plot_history_len <= self.plot_history_size):
            #
            # We accumulate enough plots to populate the whole area
            #
            # With three rows of points available (two rows of quads),
            # We can now compute average normals for the middle set of points
            #
            self.plot_history_len += 1
            
            self.quad_list = self.precalculate_strip(self.z_thickness,
                                                     self.x_vals,
                                                     self.y_vals,
                                                     self.y_vals_last)
            
            # save y_vals for next time
            self.y_vals_last = self.y_vals

            # save mins, maxes
            self.mins_y.append(min(self.y_vals))
            self.maxes_y.append(max(self.y_vals))

            # Start to build and compile gl display list
            self.gl_disp_lists.append(self.gen_disp_list(self.quad_list, self.last_quad_list))

            # Save quad list for next round
            self.last_quad_list = self.quad_list
            
        else:
            #
            # Precalculate for next time
            #
            self.quad_list = self.precalculate_strip(self.z_thickness,
                                                     self.x_vals,
                                                     self.y_vals,
                                                     self.y_vals_last)
            
            # save y_vals for next time
            self.y_vals_last = self.y_vals

            #
            # We have enough plots to plot the whole area
            #
            # First we'll plot what we have, then generate a new one

            # setup the grids if the first time
            if(self.grids_setup == False):
                # set translate amount now too
                self.x_translate_amount = 0.0
                self.y_translate_amount = -(max(self.maxes_y) - min(self.mins_y))/2
                self.z_translate_amount = self.z_thickness*self.plot_history_size/2

                self.grids_setup = True
                self.setup_zx_grid(x_start=self.x_vals[0],
                                   x_end = self.x_vals[len(self.x_vals)-1],
                                   x_rules = 20,
                                   z_thickness = self.z_thickness,
                                   z_plot_history_size = self.plot_history_size)

                self.setup_xy_grid(x_start=self.x_vals[0],
                                   x_end=self.x_vals[len(self.x_vals)-1],
                                   x_rules=20,
                                   y_end = max(self.maxes_y),
                                   y_rules = 10,
                                   z_thickness = self.z_thickness,
                                   z_plot_history_size = self.plot_history_size)

                
            glPushMatrix()

            # apply overall translation
            glTranslatef(self.x_translate_amount,
                         self.y_translate_amount,
                         self.z_translate_amount)

            # plot the grids
            glCallList(self.zx_grid_list)
            glCallList(self.xy_grid_list)

            # we can start drawing. First draw, then replace
            glPushMatrix()
            for i in range(len(self.gl_disp_lists)):
                glTranslatef(0.0, 0.0, -self.z_thickness)
                glCallList(self.gl_disp_lists[i])
            glPopMatrix()

            glPopMatrix()

            if(self.pause_redisplay == False):
                # delete oldest one, move rest over, generate and add new one
                glDeleteLists(self.gl_disp_lists[0],1)
                self.gl_disp_lists = self.gl_disp_lists[1:]

                # Start to build and compile gl display list
                self.gl_disp_lists.append(self.gen_disp_list(self.quad_list, self.last_quad_list))

                # Save quad list for next round
                self.last_quad_list = self.quad_list

                # save mins, maxes
                self.mins_y = self.mins_y[1:]
                self.maxes_y = self.maxes_y[1:]
                self.mins_y.append(min(self.y_vals))
                self.maxes_y.append(max(self.y_vals))

            
    #
    # h: 0 to 360
    # s: 0 to 1
    # v: 0 to 1
    #

    def HSVtoRGB(self, h, s, v):
        #
        # This HSV to RGB calculator
        # is adapted from GltColor::fromHSV
        #
        # OpenGL C++ Toolkit 0.7c
        # http://www.nigels.com/glt/
        #
        # Also see:
        # http://www.cs.rit.edu/~ncs/color/t_convert.html
        
        if(s == 0.0):
            return (v,v,v)

        h /= 60.0
        i = int(math.floor(h))
        f = h - i
        p = v * (1.0 - s)
        q = v * (1.0 - (s * f))
        t = v * (1.0 - (s * (1.0 - f) ) )

        if(i == 0):
            return (v,t,p)
        elif(i == 1):
            return (q,v,p)
        elif(i == 2):
            return (p,v,t)
        elif(i == 3):
            return (p,q,v)
        elif(i == 4):
            return (t,p,v)
        else:
            return (v,p,q)

    def calc_rgb_from_y(self, y_val, y_range, y_min):

        # fix saturation, value (brightness)
        sat = 1.0
        brightness_max = 0.4

        # calc hue
        hue = ((y_val - y_min)/y_range) * 360

        # shift up hue a little bit
        hue += 50

        # lets make it dimmer if lower color, but max out
        value = (hue/500) * brightness_max

        # clip so it's in range 0 - 360
        if(hue > 360):
            hue = 360
        elif(hue < 100):
            hue = 100

        # we want to go the other way, change the angle
        hue = 360 - hue

        # convert to rgb
        rgb = self.HSVtoRGB(hue, sat, value)

        return rgb

    def precalculate_strip(self,z_thickness,x_vals,y_vals,y_vals_last):
        last_z_val = z_thickness
        len_x_vals = len(x_vals)
      
        miny = min(self.mins_y)
        maxy = max(self.maxes_y)
        if(miny < 0):
            miny = 0
        rangey = (maxy - miny)
       
        point_list = []

        #
        # Pre-compute everything, surface normals, colors, points
        # This is mainly so we can calc proper average normals later
        # When we plot the points
        #
        for j in range(len_x_vals):
            # for convenience, get y_val
            y_val_last = y_vals_last[j]
            y_val = y_vals[j]

            # compute three vertices
            # vertex 0 is curr x, last y, last z
            # vertex 1 is curr x, curr y, curr z (0)
            #
            # And later,
            #
            # vertex 2 is last x, last y, curr z (0)
            v1 = [x_vals[j], y_val_last, last_z_val]
            v0 = [x_vals[j], y_val, 0.0]

            # calculate the hues of the new verticies based upon y and the range of y
            rgb0 = self.calc_rgb_from_y(y_val_last, rangey, miny)
            rgb1 = self.calc_rgb_from_y(y_val, rangey, miny)

            
            # if it's the first set of points, compute surface normal pointing straight up
            if(j == 0):
                surf_normal = (0.0,1.0,0.0)
            else:
                #
                # compute third vertex, use it for surface normal calculation
                #
                # [v2 - v1] x [v1 - v0]
                #
                v2 = [x_vals[j - 1], y_vals_last[j - 1], 0.0]

                v2v1 = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
                v1v0 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
                
                (surf_normx, surf_normy, surf_normz, mystery) = crossProduct(v2v1,v1v0)
                surf_normlen = math.sqrt(surf_normx*surf_normx +
                                    surf_normy*surf_normy +
                                    surf_normz*surf_normz)
                surf_normal = (surf_normx/surf_normlen,
                               surf_normy/surf_normlen,
                               surf_normz/surf_normlen)

            # save it all
            point_list.append((v0,v1,rgb0,rgb1,surf_normal))

        return point_list

    def gen_disp_list(self, quad_list, last_quad_list):
        # we're actually generating the one for last quad list now,
        # we use the current only for its normals

        tmp_list = glGenLists(1);
        glNewList(tmp_list, GL_COMPILE);

        glBegin(GL_QUAD_STRIP)

        len_quad_list = len(quad_list)
        for i in range(len_quad_list):

            if(i == 0):
                # for first set of points, do nothing special, use the surface normal
                (v0,v1,rgb0,rgb1,surf_norm) = last_quad_list[i]
                point_norm = surf_norm

                #print "First set: ",v0,v1
            elif(i < (len_quad_list - 1)):
                # otherwise, we need to average the surrounding quads
                (v0,v1,rgb0,rgb1,(surf_norm_a_x, surf_norm_a_y, surf_norm_a_z)) = last_quad_list[i]
                (v2,v3,rgb2,rgb3,(surf_norm_b_x, surf_norm_b_y, surf_norm_b_z)) = last_quad_list[i + 1]

                (v4,v5,rgb4,rgb5,(surf_norm_c_x, surf_norm_c_y, surf_norm_c_z)) = quad_list[i]
                (v6,v7,rgb6,rgb7,(surf_norm_d_x, surf_norm_d_y, surf_norm_d_z)) = quad_list[i + 1]

                normx = (surf_norm_a_x + surf_norm_b_x + surf_norm_c_x + surf_norm_d_x)/4
                normy = (surf_norm_a_y + surf_norm_b_y + surf_norm_c_y + surf_norm_d_y)/4
                normz = (surf_norm_a_z + surf_norm_b_z + surf_norm_c_z + surf_norm_d_z)/4

                point_norm = (normx,normy,normz)
            else:
                # otherwise, the last set of points just use the surface norm too
                (v0,v1,rgb0,rgb1,surf_norm) = last_quad_list[i]
                point_norm = surf_norm
                
            # set the normal
            glNormal3fv(point_norm)

            # set each color, then draw the point
            glColor3fv(rgb0)
            glVertex3fv(tuple(v1))
            glColor3fv(rgb1)
            glVertex3fv(tuple(v0))

        glEnd()

        glEndList()
        
        return tmp_list
