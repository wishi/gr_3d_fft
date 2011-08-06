#!/usr/bin/env python
#
# Copyright 2005 Free Software Foundation, Inc.
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

from gnuradio import gr
from gnuradio import usrp
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from gnuradio.wxgui import stdgui2
from optparse import OptionParser
import wx
from grc_gnuradio import wxgui as grc_wxgui
from gnuradio import uhd 

from gl_time_fftsink import *

class app_flow_graph (stdgui2.std_top_block):
    def __init__(self, frame, panel, vbox, argv):
       
        stdgui2.std_top_block.__init__(self,frame,panel,vbox,argv)

        
       
        
        parser = OptionParser (option_class=eng_option)
        parser.add_option ("-d", "--decim", type="int", default=16,
                           help="set fgpa decimation rate to DECIM")
        parser.add_option ("-c", "--ddc-freq", type="eng_float", default=-5.75e6,
                           help="set Rx DDC frequency to FREQ", metavar="FREQ")
        parser.add_option ("-m", "--mux", type="intx", default=0x32103210,
                           help="set fpga FR_RX_MUX register to MUX")
        parser.add_option ("-g", "--gain", type="eng_float", default=20,
                           help="set Rx PGA gain in dB (default 0 dB)")
        (options, args) = parser.parse_args ()

        # self.u = usrp.source_c (0, options.decim, 1, options.mux, 0)
        self.u = uhd.usrp_source(
                device_addr="",     # auto discovery
                io_type=uhd.io_type.COMPLEX_FLOAT32,
                num_channels=1,
        )
        
        self.u.set_center_freq(options.ddc_freq)

       
        input_rate = 100000000 / options.decim
        self.u.set_samp_rate(input_rate)

        # block = fft_sink_c(self, panel, title="gr_gl", fft_size=512, sample_rate=input_rate)
        #fft_win = block.win

        block = fft_sink_c(self, panel, title="gr_gl", fft_size=512, sample_rate=input_rate,
                           average=True, avg_alpha=(0.005), baseband_freq=0)
        fft_win = block.win
        
        self.connect (self.u, block)

def main ():
    app = stdgui2.stdapp(app_flow_graph, "3d")
    app.MainLoop ()

if __name__ == '__main__':
    main ()
