#
# Copyright (c) 2012 Christophe Varoqui <christophe.varoqui@opensvc.com>
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
import checks
from rcUtilities import justcall, which
from rcGlobalEnv import rcEnv
di = __import__("rcDiskInfo"+rcEnv.sysname)
_di = di.diskInfo()

class check(checks.check):
    chk_type = "mpath"
    chk_name = "PowerPath"

    def find_svc(self, dev):
        for svc in self.svcs:
            if dev in svc.disklist():
                return svc.svcname
        return ''

    def do_check(self):
        """
	Pseudo name=emcpowerh
	Symmetrix ID=000290101523
	Logical device ID=17C6
	state=alive; policy=SymmOpt; priority=0; queued-IOs=0
	==============================================================================
	---------------- Host ---------------   - Stor -   -- I/O Path -  -- Stats ---
	###  HW Path                I/O Paths    Interf.   Mode    State  Q-IOs Errors
	==============================================================================
	   0 qla2xxx                   sdi       FA  9dB   active  alive      0      0
	   1 qla2xxx                   sds       FA  8dB   active  alive      0      0
        """

        if not which('powermt'):
            return self.undef

        cmd = ['powermt', 'display', 'dev=all']
        (out, err, ret) = justcall(cmd)
        if ret != 0:
            return self.undef

        lines = out.split('\n')
        if len(lines) < 1:
            return self.undef

        r = []
        dev = None
        name = None
        paths = []
        n = 0
        for line in lines:
            if len(line) == 0:
                # new mpath
                # - store previous
                # - reset path counter
                if dev is not None:
                    if len(paths) > 0:
                        did = _di.disk_id(paths[0])
                        if did is not None:
                            name = did
                    r.append({'chk_instance': name,
                              'chk_value': str(n),
                              'chk_svcname': self.find_svc(dev),
                             })
                    paths = []
                    dev = None
                    n = 0
            if 'Pseudo name' in line:
                l = line.split('=')
                if len(l) != 2:
                    continue
                name = l[1]
                dev = "/dev/"+name
            else:
                l = line.split()
                if len(l) < 3:
                    continue
                if l[2].startswith("sd"):
                    paths.append("/dev/"+l[2])
                if "active" in line and \
                   "alive" in line:
                    n += 1
        return r
