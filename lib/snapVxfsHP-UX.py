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
import os

from rcGlobalEnv import rcEnv
from rcUtilities import which, qcall, protected_mount
import rcExceptions as ex
import snap

class Snap(snap.Snap):
    def lv_exists(self, device):
        if qcall(['lvdisplay', device]) == 0:
            return True
        return False

    def lv_info(self, device):
        (ret, buff) = self.call(['lvdisplay', device])
        if ret != 0:
            return (None, None, None)
        vg_name = None
        lv_name = None
        lv_size = 0
        for line in buff.split('\n'):
            if "VG Name" in line:
                vg_name = line.split()[-1]
            if "LV Name" in line:
                lv_name = line.split()[-1]
            if "LV Size" in line:
                lv_size = int(line.split()[-1])
        return (vg_name, lv_name, lv_size)

    def snapcreate(self, m):
        snap_name = ''
        snap_mnt = ''
        (vg_name, lv_name, lv_size) = self.lv_info(m.device)
        if lv_name is None:
            self.log.error("can not snap %s: not a logical volume"%m.device)
            raise ex.syncNotSnapable
        snap_name = 'osvc_sync_'+os.path.basename(lv_name)
        if self.lv_exists(os.path.join(vg_name, snap_name)):
            self.log.error("snap of %s already exists"%(lv_name))
            raise ex.syncSnapExists
        (ret, buff) = self.vcall(['lvcreate', '-L', str(lv_size//10)+'M', '-n', snap_name, vg_name])
        if ret != 0:
            raise ex.syncSnapCreateError
        snap_mnt = '/service/tmp/osvc_sync_'+os.path.basename(vg_name)+'_'+os.path.basename(lv_name)
        if not os.path.exists(snap_mnt):
            os.makedirs(snap_mnt, 0755)
        snap_dev = os.path.join(vg_name, snap_name)
        (ret, buff) = self.vcall(['mount', '-F', 'vxfs', '-o', 'ro,snapof='+m.device, snap_dev, snap_mnt])
        if ret != 0:
            raise ex.syncSnapMountError
        self.snaps[m.mountPoint] = dict(lv_name=lv_name,
                                        vg_name=vg_name,
                                        snap_name=snap_name,
                                        snap_mnt=snap_mnt,
                                        snap_dev=snap_dev)

    def snapdestroykey(self, s):
        if protected_mount(self.snaps[s]['snap_mnt']):
            self.log.error("the snapshot is no longer mounted in %s. panic."%self.snaps[s]['snap_mnt'])
            raise ex.excError

        """ fuser on HP-UX outs to stderr ...
        """
        cmd = ['fuser', '-kc', self.snaps[s]['snap_mnt']]
        ret = qcall(cmd)

        cmd = ['umount', self.snaps[s]['snap_mnt']]
        (ret, out) = self.vcall(cmd)
        cmd = ['lvremove', '-f', self.snaps[s]['snap_dev']]
        (ret, buff) = self.vcall(cmd)

