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

import threading
import time
import exceptions

#
# Global messaging scheme
#

class subscriber:
    def __init__(self):
        self.data_tuple = ()
        self.data_valid = False
        self.cond = threading.Condition()
        self.first = True
        
    def wait_data(self):
        if(not self.first):
            self.cond.release()
        self.cond.acquire()
        while(self.data_valid == False):
            self.cond.wait()
            
        self.data_valid = False

    def finish_data(self):
        self.cond.release()

class subscription_service:
    def __init__(self):
        self.clients = []

    def add_client(self, client):
        # create a condition for the thread, and add it
        self.clients.append(client)

    def send_data(self, data_tuple):
        # throw a runtime error if no subscribers
        if(len(self.clients) == 0):
            raise exceptions.RuntimeError, "There are no subscribers!"

        # for each subscriber, acquire the lock
        for client in self.clients:
            client.cond.acquire()
            client.data_tuple = data_tuple
            client.data_valid = True
            client.cond.notify()
            client.cond.release()

