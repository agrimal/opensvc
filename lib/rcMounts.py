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
from subprocess import *
import os
import logging
import rcLinuxLoop
from rcGlobalEnv import *
from rcUtilities import *

class Mount:
	def __init__(self, dev, mnt, type, mnt_opt):
		self.dev = dev
		self.mnt = mnt
		self.type = type
		self.mnt_opt = mnt_opt

def match_mount(i, dev, mnt):
	"""Given a line of 'mount' output, returns True if (dev, mnt) matches
	this line. Returns False otherwize. Also care about weirdos like loops
	and binds, ...
	"""
	if i.mnt != mnt:
		return False
	if i.dev == dev:
		return True
	if i.dev == rcLinuxLoop.file_to_loop(dev):
		return True
	return False

class Mounts:
	mounts = []

	def mount(self, dev, mnt):
		for i in self.mounts:
			if match_mount(i, dev, mnt):
				return i
		return None

	def has_mount(self, dev, mnt):
		for i in self.mounts:
			if match_mount(i, dev, mnt):
				return 0
		return 1

	def has_param(self, param, value):
		for i in self.mounts:
			if getattr(i, param) == value:
				return i
		return None

	def __init__(self):
		out = Popen(['mount'], stdout=PIPE).communicate()[0]
		for l in out.split('\n'):
			if len(l.split()) != 6:
				return
			dev, null, mnt, null, type, mnt_opt = l.split()
			m = Mount(dev, mnt, type, mnt_opt.strip('()'))
			self.mounts.append(m)
