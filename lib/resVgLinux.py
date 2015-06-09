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
import re
import os
import rcExceptions as ex
import resDg
from rcGlobalEnv import rcEnv
from rcUtilitiesLinux import major, get_blockdev_sd_slaves, \
                             devs_to_disks
from rcUtilities import which, justcall

class Vg(resDg.Dg):
    def __init__(self,
                 rid=None,
                 name=None,
                 type=None,
                 optional=False,
                 disabled=False,
                 tags=set([]),
                 always_on=set([]),
                 monitor=False,
                 restart=0,
                 subset=None):
        self.label = "vg "+name
        self.tag = rcEnv.nodename
        resDg.Dg.__init__(self,
                          rid=rid,
                          name=name,
                          type='disk.vg',
                          always_on=always_on,
                          optional=optional,
                          disabled=disabled,
                          tags=tags,
                          monitor=monitor,
                          restart=restart,
                          subset=subset)

    def is_child_dev(self, device):
        l = device.split("/")
        if len(l) != 4 or l[1] != "dev":
            return False
        if l[2] == "mapper":
            dmname = l[3]
            if "-" not in dmname:
                return False
            i = 0
            dmname.replace("--", "#")
            _l = dmname.split("-")
            if len(_l) != 2:
                return False
            vgname = _l[0].replace("#", "-")
        else:
            vgname = l[2]
        if vgname == self.name:
            return True
        return False  

    def has_it(self):
        try:
            r = self._has_it()
        except ex.excError as e:
            self.log.debug(str(e))
            return False
        return r

    def vgdisplay(self):
        """Returns True if the volume is present
        """
        cmd = ['vgdisplay', self.name]
        out, err, ret = justcall(cmd)
        return ret, out, err

    def _has_it(self):
        ret, out, err = self.vgdisplay()
        if ret == 0:
            return True
        if "not found" in err:
            return False
        raise ex.excError(err)

    def is_up(self):
        """Returns True if the volume group is present and activated
        """
        if not self.has_it():
            return False
        cmd = [ 'lvs', '--noheadings', '-o', 'lv_attr', self.name ]
        (ret, out, err) = self.call(cmd)
        if len(out) == 0 and ret == 0:
            # no lv ... happens in provisioning, where lv are not created yet
            return True
        if re.search(' ....a.', out, re.MULTILINE) is not None:
            return True
        return False

    def test_vgs(self):
        cmd = ['vgs', '-o', 'tags', '--noheadings', self.name]
        out, err, ret = justcall(cmd)
        if "not found" in err:
            return False
        if ret != 0:
            raise ex.excError
        return True

    def remove_tag(self, tag):
        cmd = [ 'vgchange', '--deltag', '@'+tag, self.name ]
        (ret, out, err) = self.vcall(cmd)
        if ret != 0:
            raise ex.excError

    def list_tags(self, tags=[]):
        tmo = 5
        try:
            self.wait_for_fn(self.test_vgs, tmo, 1, errmsg="vgs is still reporting the vg as not found after %d seconds"%tmo)
        except ex.excError as e:
            self.log.warning(str(e))
            cmd = ["pvscan"]
            ret, out, err = self.vcall(cmd)
        cmd = ['vgs', '-o', 'tags', '--noheadings', self.name]
        (ret, out, err) = self.call(cmd)
        if ret != 0:
            raise ex.excError
        out = out.strip(' \n')
        curtags = out.split(',')
        return curtags

    def remove_tags(self, tags=[]):
        for tag in tags:
            tag = tag.lstrip('@')
            if len(tag) == 0:
                continue
            self.remove_tag(tag)

    def add_tags(self):
        cmd = [ 'vgchange', '--addtag', '@'+self.tag, self.name ]
        (ret, out, err) = self.vcall(cmd)
        if ret != 0:
            raise ex.excError

    def do_start(self):
        curtags = self.list_tags()
        tags_to_remove = set(curtags) - set([self.tag])
        if len(tags_to_remove) > 0:
            self.remove_tags(tags_to_remove)
        if self.tag not in curtags:
            self.add_tags()
        if self.is_up():
            self.log.info("%s is already up" % self.label)
            return 0
        self.can_rollback = True
        cmd = [ 'vgchange', '-a', 'y', self.name ]
        (ret, out, err) = self.vcall(cmd)
        if ret != 0:
            raise ex.excError

    def remove_dev_holders(self, devpath, tree):
        dev = tree.get_dev_by_devpath(devpath)
        holders_devpaths = set()
        holder_devs = dev.get_children_bottom_up()
        for dev in holder_devs:
            if devpath in dev.devpath:
                continue
            holders_devpaths |= set(dev.devpath)
        holders_handled_by_resources = self.svc.devlist(filtered=False) & holders_devpaths
        if len(holders_handled_by_resources) > 0:
            raise ex.excError("resource %s has holders handled by other resources: %s" % (self.rid, ", ".join(holders_handled_by_resources)))
        for dev in holder_devs:
            dev.remove(self)

    def remove_holders(self):
        import glob
        import rcDevTreeLinux
        tree = rcDevTreeLinux.DevTree()
        tree.load()
        for lvdev in glob.glob("/dev/mapper/%s-*"%self.name.replace("-", "--")):
             self.remove_dev_holders(lvdev, tree)

    def do_stop(self):
        if not self.is_up():
            self.log.info("%s is already down" % self.label)
            return
        self.remove_holders()
        curtags = self.list_tags()
        self.remove_tags(curtags)
        cmd = [ 'vgchange', '-a', 'n', self.name ]
        (ret, out, err) = self.vcall(cmd, err_to_info=True)
        if ret == 0:
            return

        import time
        for i in range(3, 0, -1):
            if self.is_up() and i > 0:
                time.sleep(1)
                (ret, out, err) = self.vcall(cmd, err_to_info=True)
                if ret == 0:
                    return
                continue
            break
        if i == 0:
            self.log.error("deactivation failed to release all logical volumes")
            raise ex.excError

    def devlist(self):
        if not self.has_it():
            return set()
        if self.devs != set():
            return self.devs

        self.devs = set()

        cmd = ['vgs', '--noheadings', '-o', 'pv_name', self.name]
        (ret, out, err) = self.call(cmd, cache=True)
        if ret == 0:
            self.devs |= set(out.split())

        cmd = ['vgs', '--noheadings', '-o', 'lv_name', self.name]
        (ret, out, err) = self.call(cmd, cache=True)
        if ret == 0:
            lvs = out.split()
            for lv in lvs:
                devs = []
                lvp = "/dev/"+self.name+"/"+lv
                if os.path.exists(lvp):
                    devs.append(lvp)
            self.devs |= set(devs)

        if len(self.devs) > 0:
            self.log.debug("found devs %s held by vg %s" % (self.devs, self.name))

        return self.devs

    def disklist(self):
        if not self.has_it():
            return set()
        if self.disks != set():
            return self.disks

        self.disks = set()

        pvs = self.devlist()
        self.disks = devs_to_disks(self, pvs)
        self.log.debug("found disks %s held by vg %s" % (self.disks, self.name))
        return self.disks

    def provision(self):
        m = __import__("provVgLinux")
        prov = getattr(m, "ProvisioningVg")(self)
        prov.provisioner()

