#!/usr/bin/python2.6
#
# Copyright (c) 2010 Christophe Varoqui <christophe.varoqui@free.fr>'
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
import os
from rcUtilities import justcall
"""
"""

def dataset_exists(device, type):
    "return True if dataset exists else return False"
    (out, err, ret) = justcall('zfs get -H -o value type'.split()+[device])
    if ret == 0 and out.split('\n')[0] == type :
        return True
    else:
        return False

def zfs_getprop(dataset='undefinedds', propname='undefinedprop'):
    cmd = [ 'zfs', 'get', '-Hp', '-o', 'value', propname, dataset ]
    (stdout, stderr, retcode) = justcall(cmd)
    if retcode == 0 :
        return stdout.split("\n")[0]
    else:
        return ""

def zfs_setprop(dataset='undefinedds', propname='undefinedprop', propval='undefinedval'):
    if zfs_getprop(dataset, propname) == propval :
        return True
    cmd = [ 'zfs', 'set', propname + '='+ propval, dataset ]
    print cmd
    (stdout, stderr, retcode) = justcall(cmd)
    if retcode == 0 :
        return True
    else:
        print 'status: ' , retcode
        print 'stdout: ' + stdout
        print 'stderr: ' + stderr
        return False


