#!/opt/opensvc/bin/python
""" 
module use OSVC_COMP_USER_... vars
which define {'username':{'propname':'propval',... }, ...}

example: 
{"tibco":{"shell":"/bin/ksh","gecos":"agecos",},
 "tibco1":{"shell":"/bin/tcsh","gecos":"another gecos",},
}

supported dictionnary keys:
- uid
- gid
- gecos
- home
- shell
"""

import os
import sys
import json
import pwd
import re
from utilities import which

try:
    import spwd
    cap_shadow = True
except:
    cap_shadow = False

from subprocess import Popen, list2cmdline

sys.path.append(os.path.dirname(__file__))

from comp import *

class CompUser(object):
    def __init__(self, prefix='OSVC_COMP_USER_'):
        self.prefix = prefix.upper()
        self.pwt = {
            'shell': 'pw_shell',
            'home': 'pw_dir',
            'uid': 'pw_uid',
            'gid': 'pw_gid',
            'gecos': 'pw_gecos',
            'password': 'pw_passwd',
        }
        self.spwt = {
            'spassword': 'sp_pwd',
        }
        self.usermod_p = {
            'shell': '-s',
            'home': '-m -d',
            'uid': '-u',
            'gid': '-g',
            'gecos': '-c',
            'password': '-p',
            'spassword': '-p',
        }
        self.sysname, self.nodename, x, x, self.machine = os.uname()

        if self.sysname not in ['SunOS', 'Linux', 'HP-UX', 'AIX']:
            print >>sys.stderr, 'module not supported on', self.sysname
            raise NotApplicable()

        self.users = {}
        for k in [ key for key in os.environ if key.startswith(self.prefix)]:
            try:
                self.users.update(json.loads(os.environ[k]))
            except ValueError:
                print >>sys.stderr, 'user syntax error on var[', k, '] = ',os.environ[k]

        if len(self.users) == 0:
            print >>sys.stderr, "no applicable variable found in rulesets", self.prefix
            raise NotApplicable()

        p = re.compile('%%ENV:\w+%%')
        for user, d in self.users.items():
            for k in d:
                if type(d[k]) not in [str, unicode]:
                    continue
                for m in p.findall(d[k]):
                    s = m.strip("%").replace('ENV:', '')
                    if s in os.environ:
                        v = os.environ[s]
                    elif 'OSVC_COMP_'+s in os.environ:
                        v = os.environ['OSVC_COMP_'+s]
                    else:
                        print >>sys.stderr, s, 'is not an env variable'
                        raise NotApplicable()
                    d[k] = d[k].replace(m, v)

        if not cap_shadow:
            for user, d in self.users.items():
                if "spassword" in d and len(d["spassword"]) > 0 and \
                   ("password" not in d or len(d["password"]) == 0):
                    self.users[user]["password"] = self.users[user]["spassword"]
                    del self.users[user]["spassword"]

    def fixable(self):
        if not which('usermod'):
            print >>sys.stderr, "usermod program not found"
            return RET_ERR
        return RET_OK

    def fix_item(self, user, item, target):
        cmd = ['usermod'] + self.usermod_p[item].split() + [str(target), user]
        print list2cmdline(cmd)
        p = Popen(cmd)
        out, err = p.communicate()
        r = p.returncode
        if which('pwconv'):
            p = Popen(['pwconv'])
            p.communicate()
        if which('grpconv'):
            p = Popen(['grpconv'])
            p.communicate()
        if r == 0:
            return RET_OK
        else:
            return RET_ERR

    def check_item(self, user, item, target, current, verbose=False):
        if type(current) == int and current < 0:
            current += 4294967296
        if target == current:
            if verbose:
                print 'user', user, item+':', current
            return RET_OK
        else:
            if verbose:
                print >>sys.stderr, 'user', user, item+':', current, 'target:', target
            return RET_ERR

    def check_user(self, user, props):
        r = 0
        try:
            userinfo=pwd.getpwnam(user)
        except KeyError:
            if self.try_create_user(props):
                print >>sys.stderr, 'user', user, 'does not exist'
                return RET_ERR
            else:
                print >>sys.stderr, 'user', user, 'does not exist and not enough info to create it'
                return RET_ERR

        for prop in self.pwt:
            if prop in props:
                r |= self.check_item(user, prop, props[prop], getattr(userinfo, self.pwt[prop]), verbose=True)

        if not cap_shadow:
            return r

        try:
            usersinfo=spwd.getspnam(user)
        except KeyError:
            if "spassword" in props:
                print >>sys.stderr, user, "not declared in /etc/shadow"
                r |= RET_ERR
            usersinfo = None

        if usersinfo is not None:
            for prop in self.spwt:
                if prop in props:
                    r |= self.check_item(user, prop, props[prop], getattr(usersinfo, self.spwt[prop]), verbose=True)
        return r

    def try_create_user(self, props):
        #
        # don't try to create user if passwd db is not 'files'
        # beware: 'files' db is the implicit default
        #
        if 'db' in props and props['db'] != 'files':
            return False
        return True

    def create_user(self, user, props):
        cmd = ['useradd']
        for item in props:
            prop = str(props[item])
            if len(prop) == 0:
                continue
            cmd = cmd + self.usermod_p[item].split() + [prop]
        cmd += [user]
        print list2cmdline(cmd)
        p = Popen(cmd)
        out, err = p.communicate()
        r = p.returncode
        if r == 0:
            return RET_OK
        else:
            return RET_ERR

    def fix_user(self, user, props):
        r = 0
        try:
            userinfo = pwd.getpwnam(user)
        except KeyError:
            if self.try_create_user(props):
                return self.create_user(user, props)
            else:
                print 'user', user, 'does not exist and not enough info to create it'
                return RET_OK

        for prop in self.pwt:
            if prop in props and \
               self.check_item(user, prop, props[prop], getattr(userinfo, self.pwt[prop])) != RET_OK:
                r |= self.fix_item(user, prop, props[prop])

        if not cap_shadow:
            return r

        try:
            usersinfo = spwd.getspnam(user)
        except KeyError:
            if "spassword" in props:
                self.fix_item(user, "spassword", props["spassword"])
                usersinfo = spwd.getspnam(user)
            else:
                usersinfo = None

        if usersinfo is not None:
            for prop in self.spwt:
                if prop in props and \
                    self.check_item(user, prop, props[prop], getattr(usersinfo, self.spwt[prop])) != RET_OK:
                    r |= self.fix_item(user, prop, props[prop])
        return r

    def check(self):
        r = 0
        for user, props in self.users.items():
            r |= self.check_user(user, props)
        return r

    def fix(self):
        r = 0
        for user, props in self.users.items():
            r |= self.fix_user(user, props)
        return r

if __name__ == "__main__":
    syntax = """syntax:
      %s PREFIX check|fixable|fix"""%sys.argv[0]
    if len(sys.argv) != 3:
        print >>sys.stderr, "wrong number of arguments"
        print >>sys.stderr, syntax
        sys.exit(RET_ERR)
    try:
        o = CompUser(sys.argv[1])
        if sys.argv[2] == 'check':
            RET = o.check()
        elif sys.argv[2] == 'fix':
            RET = o.fix()
        elif sys.argv[2] == 'fixable':
            RET = o.fixable()
        else:
            print >>sys.stderr, "unsupported argument '%s'"%sys.argv[2]
            print >>sys.stderr, syntax
            RET = RET_ERR
    except NotApplicable:
        sys.exit(RET_NA)
    except:
        import traceback
        traceback.print_exc()
        sys.exit(RET_ERR)

    sys.exit(RET)

