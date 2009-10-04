#
# Copyright (c) 2009 Christophe Varoqui <christophe.varoqui@free.fr>'
# Copyright (c) 2009 Cyril Galibern <cyril.galibern@free.fr>'
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
import socket
import os

class ip:
	def is_alive(self):
		count=1
		timeout=5
		cmd = [ 'ping', '-c', count, '-W', timeout, self.addr ]
		if os.spawnlp(os.P_WAIT, cmd) != 0:
			return True
		return False

	def __init__(self, name, dev):
		self.name = name
		self.dev = dev
		self.addr = socket.gethostbyname(name)
