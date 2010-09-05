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

from svc import Svc
from freezer import Freezer
import svcBuilder
import xmlrpcClient

class Node(Svc, Freezer):
    """ Defines a cluster node.  It contain list of Svc.
        Implements node-level actions and checks.
    """
    def __init__(self):
        self.svcs = svcBuilder.build_services()
        self.force = False
        Freezer.__init__(self, '')
        self.action_desc = {
          'syncservices':   'send var files, config files and configured replications to other nodes for each node service',
          'updateservices': 'refresh var files associated with services',
          'pushasset':      'push asset information to collector',
          'pushservices':   'push service configuration to collector',
          'pushstats':      'push performance metrics to collector',
          'pushpkg':        'push package/version list to collector',
          'prkey':          'display persistent reservation key of this node',
          'checks':         'run node sanity checks, push results to collector',
        }

    def format_desc(self):
        from textwrap import TextWrapper
        wrapper = TextWrapper(subsequent_indent="%19s"%"", width=78)
        desc = "Supported commands:\n"
        for a in sorted(self.action_desc):
            if not hasattr(self, a):
                continue
            text = "  %-16s %s\n"%(a, self.action_desc[a])
            desc += wrapper.fill(text)
            desc += '\n'
        return desc

    def __iadd__(self, s):
        if not isinstance(s, Svc):
                pass
        self.svcs.append(s)
        return self

    def action(self, a):
        return getattr(self, a)()

    def pushstats(self):
        xmlrpcClient.push_stats(force=self.force)

    def pushpkg(self):
        xmlrpcClient.push_pkg()

    def pushasset(self):
        xmlrpcClient.push_asset()

    def syncservices(self):
        for svc in self.svcs:
            svc.action('syncall')

    def updateservices(self):
        for svc in self.svcs:
            svc.action('presync')

    def pushservices(self):
        for svc in self.svcs:
            svc.action('push')

    def prkey(self):
        from rcGlobalEnv import rcEnv
        m = __import__('hostid'+rcEnv.sysname)
        print m.hostid()

    def checks(self):
        import checks
        c = checks.checks(self.svcs)
        c.do_checks()

if __name__ == "__main__" :
    for n in (Node,) :
        help(n)
