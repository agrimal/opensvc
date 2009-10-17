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
# To change this template, choose Tools | Templates
# and open the template in the editor.

import resources as res

class Mount(res.Resource):
    """Define a mount resource 
    """
    def __init__(self,mountPoint=None,device=None,fsType=None,mntOpt=None,optional=False,\
                disabled=False):
        res.Resource.__init__(self,"mount",optional,disabled)
        self.mountPoint = mountPoint
        self.device = device
        self.fsType = fsType
        self.mntOpt = mntOpt
        self.id = 'fs ' + device + '@' + mountPoint

    def __str__(self):
        return "%s mnt=%s dev=%s fsType=%s mntOpt=%s" % (res.Resource.__str__(self),\
                self.mountPoint, self.device, self.fsType, self.mntOpt)

if __name__ == "__main__":
    for c in (Mount,) :
        help(c)
    print """   m=Mount("/mnt1","/dev/sda1","ext3","rw")   """
    m=Mount("/mnt1","/dev/sda1","ext3","rw")
    print "show m", m


