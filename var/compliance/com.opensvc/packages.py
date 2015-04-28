#!/usr/bin/env /opt/opensvc/bin/python
""" 
module use OSVC_COMP_PACKAGES_... vars
which define ['pkg1', 'pkg2', ...]
"""

import os
import re
import sys
import json
import pwd
import tempfile
from subprocess import *
from utilities import which

sys.path.append(os.path.dirname(__file__))

from comp import *

class CompPackages(object):
    def __init__(self, prefix='OSVC_COMP_PACKAGES_', uri=None):
        self.combo_fix = False
        self.uri = uri
        self.prefix = prefix.upper()
        self.sysname, self.nodename, x, x, self.machine = os.uname()
        self.known_archs = ['i386', 'i586', 'i686', 'x86_64', 'noarch', '*']

        if self.sysname not in ['Linux', 'AIX', 'HP-UX', 'SunOS', 'FreeBSD']:
            print >>sys.stderr, __file__, 'module not supported on', self.sysname
            raise NotApplicable()

        if 'OSVC_COMP_PACKAGES_PKG_TYPE' in os.environ and \
           os.environ['OSVC_COMP_PACKAGES_PKG_TYPE'] == "bundle":
            self.pkg_type = 'bundle'
        else:
            self.pkg_type = 'product'

        self.packages = []
        for k in [key for key in os.environ if key.startswith(self.prefix)]:
            try:
                self.packages += json.loads(self.subst(os.environ[k]))
            except ValueError:
                print >>sys.stderr, 'failed to concatenate', os.environ[k], 'to package list'

        if len(self.packages) == 0:
            raise NotApplicable()

        self.data = {}
        l = []
        for pkg in self.packages:
            if type(pkg) == dict:
                l.append(pkg['pkgname'])
                self.data[pkg['pkgname']] = pkg
        if len(l) > 0:
            self.packages = l

        vendor = os.environ.get('OSVC_COMP_NODES_OS_VENDOR', 'unknown')
        release = os.environ.get('OSVC_COMP_NODES_OS_RELEASE', 'unknown')
        if vendor in ['Debian', 'Ubuntu']:
            self.get_installed_packages = self.deb_get_installed_packages
            self.pkg_add = self.apt_fix_pkg
            self.pkg_del = self.apt_del_pkg
        elif vendor in ['CentOS', 'Redhat', 'Red Hat'] or \
             (vendor == 'Oracle' and self.sysname == 'Linux'):
            if which("yum") is None:
                print >>sys.stderr, "package manager not found (yum)"
                raise ComplianceError()
            self.combo_fix = True
            self.get_installed_packages = self.rpm_get_installed_packages
            self.pkg_add = self.yum_fix_pkg
            self.pkg_del = self.yum_del_pkg
        elif vendor == "SuSE":
            if which("zypper") is None:
                print >>sys.stderr, "package manager not found (zypper)"
                raise ComplianceError()
            self.get_installed_packages = self.rpm_get_installed_packages
            self.pkg_add = self.zyp_fix_pkg
            self.pkg_del = self.zyp_del_pkg
        elif vendor == "FreeBSD":
            if which("pkg") is None:
                print >>sys.stderr, "package manager not found (pkg)"
                raise ComplianceError()
            self.get_installed_packages = self.freebsd_pkg_get_installed_packages
            self.pkg_add = self.freebsd_pkg_fix_pkg
            self.pkg_del = self.freebsd_pkg_del_pkg
        elif vendor in ['IBM']:
            self.get_installed_packages = self.aix_get_installed_packages
            self.pkg_add = self.aix_fix_pkg
            self.pkg_del = self.aix_del_pkg
            if self.uri is None:
                print >>sys.stderr, "resource must be set"
                raise NotApplicable()
        elif vendor in ['HP']:
            self.get_installed_packages = self.hp_get_installed_packages
            self.pkg_add = self.hp_fix_pkg
            self.pkg_del = self.hp_del_pkg
        elif vendor in ['Oracle']:
            self.get_installed_packages = self.sol_get_installed_packages
            self.pkg_add = self.sol_fix_pkg
            self.pkg_del = self.sol_del_pkg
        else:
            print >>sys.stderr, vendor, "not supported"
            raise NotApplicable()

        self.load_reloc()
        self.packages = map(lambda x: x.strip(), self.packages)
        self.expand_pkgnames()
        self.installed_packages = self.get_installed_packages()

    def subst(self, v):
        if type(v) == list:
            l = []
            for _v in v:
                l.append(self.subst(_v))
            return l
        if type(v) != str and type(v) != unicode:
            return v

        p = re.compile('%%ENV:\w+%%')
        for m in p.findall(v):
            s = m.strip("%").replace('ENV:', '')
            if s in os.environ:
                _v = os.environ[s]
            elif 'OSVC_COMP_'+s in os.environ:
                _v = os.environ['OSVC_COMP_'+s]
            else:
                print >>sys.stderr, s, 'is not an env variable'
                raise NotApplicable()
            v = v.replace(m, _v)
        return v.strip()

    def load_reloc(self):
        self.reloc = {}
        for i, pkgname in enumerate(self.packages):
            l = pkgname.split(':')
            if len(l) != 2:
                continue
            self.packages[i] = l[0]
            self.reloc[l[0]] = l[1]

    def expand_pkgnames(self):
        """ Expand wildcards and implicit arch
        """
        l = []
        for pkgname in self.packages:
            if (pkgname.startswith('-') or pkgname.startswith('+')) and len(pkgname) > 1:
                prefix = pkgname[0]
                pkgname = pkgname[1:]
            else:
                prefix = ''
            l += map(lambda x: prefix+x, self.expand_pkgname(pkgname, prefix))
        self.packages = l

    def expand_pkgname(self, pkgname, prefix):
        vendor = os.environ.get('OSVC_COMP_NODES_OS_VENDOR', 'unknown')
        release = os.environ.get('OSVC_COMP_NODES_OS_RELEASE', 'unknown')
        if vendor in ['CentOS', 'Redhat', 'Red Hat'] or (vendor == 'Oracle' and release.startswith('VM ')):
            return self.yum_expand_pkgname(pkgname, prefix)
        elif vendor == 'SuSE':
            return self.zyp_expand_pkgname(pkgname, prefix)
        elif vendor in ['IBM']:
            return self.aix_expand_pkgname(pkgname, prefix)
        return [pkgname]

    def aix_expand_pkgname(self, pkgname, prefix=''):
        """
LGTOnw.clnt:LGTOnw.clnt.rte:8.1.1.6::I:C:::::N:NetWorker Client::::0::
LGTOnw.man:LGTOnw.man.rte:8.1.1.6::I:C:::::N:NetWorker Man Pages::::0::

or for rpm lpp_source:

zlib                                                               ALL  @@R:zlib _all_filesets
   @@R:zlib-1.2.7-2 1.2.7-2

        """
        if not hasattr(self, "nimcache"):
            cmd = ['nimclient', '-o', 'showres', '-a', 'resource=%s'%self.uri, '-a', 'installp_flags=L']
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            self.lpp_type = "installp"
            if "0042-175" in err:
                # not a native installp lpp_source
                cmd = ['nimclient', '-o', 'showres', '-a', 'resource=%s'%self.uri]
                p = Popen(cmd, stdout=PIPE, stderr=PIPE)
                out, err = p.communicate()
                self.lpp_type = "rpm"
            self.nimcache = out.split('\n')

        l = []
        if self.lpp_type == "rpm":
            l = self.aix_expand_pkgname_rpm(pkgname, prefix=prefix)
        elif self.lpp_type == "native":
            l = self.aix_expand_pkgname_native(pkgname, prefix=prefix)

        if len(l) == 0:
            l = [pkgname]
        return l

    def aix_expand_pkgname_rpm(self, pkgname, prefix=''):
        import fnmatch
        l = []
        for line in self.nimcache:
            line = line.strip()
            if len(line) == 0:
                continue
            words = line.split()
            if line.startswith("@@") and len(words) > 1:
                _pkgvers = words[1]
                if fnmatch.fnmatch(_pkgname, pkgname) and _pkgname not in l:
                    l.append(_pkgname)
            else:
                _pkgname = words[0]
        return l

    def aix_expand_pkgname_native(self, pkgname, prefix=''):
        import fnmatch
        l = []
        for line in self.nimcache:
            words = line.split(':')
            if len(words) < 5:
                continue
            _pkgvers = words[2]
            _pkgname = words[1].replace('-'+_pkgvers, '')
            if fnmatch.fnmatch(_pkgname, pkgname) and _pkgname not in l:
                l.append(_pkgname)
        return l

    def zyp_expand_pkgname(self, pkgname, prefix=''):
        arch_specified = False
        for arch in self.known_archs:
            if pkgname.endswith(arch):
                arch_specified = True
        cmd = ['zypper', '--non-interactive', 'packages']
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            if prefix != '-':
                print >>sys.stderr, 'can not expand (cmd error)', pkgname, err
                return []
            else:
                return [pkgname]
        lines = out.split('\n')
        if len(lines) < 2:
            if prefix != '-':
                print >>sys.stderr, 'can not expand', pkgname
                return []
            else:
                return [pkgname]
        for i, line in enumerate(lines):
            if "--+--" in line:
                break
        lines = lines[i+1:]
        l = []
        for line in lines:
            words = map(lambda x: x.strip(), line.split(" | "))
            if len(words) != 5:
                continue
            _status, _repo, _name, _version, _arch = words
            if arch_specified:
                if _name != pkgname or (arch != '*' and arch != _arch):
                    continue
            else:
                if _name != pkgname:
                    continue
            _pkgname = '.'.join((_name, _arch))
            if _pkgname in l:
                continue
            l.append(_pkgname)

        if arch_specified or len(l) == 1:
            return l

        if os.environ['OSVC_COMP_NODES_OS_ARCH'] in ('i386', 'i586', 'i686', 'ia32'):
            archs = ('i386', 'i586', 'i686', 'ia32', 'noarch')
        else:
            archs = (os.environ['OSVC_COMP_NODES_OS_ARCH'], 'noarch')

        ll = []
        for pkgname in l:
            if pkgname.split('.')[-1] in archs:
                # keep only packages matching the arch
                ll.append(pkgname)

        return ll

    def yum_expand_pkgname(self, pkgname, prefix=''):
        arch_specified = False
        for arch in self.known_archs:
            if pkgname.endswith(arch):
                arch_specified = True
        cmd = ['yum', 'list', pkgname]
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            if prefix != '-':
                print >>sys.stderr, 'can not expand (cmd error)', pkgname, err
                return []
            else:
                return [pkgname]
        lines = out.split('\n')
        if len(lines) < 2:
            if prefix != '-':
                print >>sys.stderr, 'can not expand', pkgname
                return []
            else:
                return [pkgname]
        lines = lines[1:]
        l = []
        for line in lines:
            words = line.split()
            if len(words) != 3:
                continue
            if words[0] in ("Installed", "Available", "Loaded", "Updating"):
                continue
            if words[0] in l:
                continue
            l.append((words[0], words[1]))

        ll = []
        ix86_added = False
        from distutils.version import LooseVersion as V
        for _pkgname, _version in sorted(l, key=lambda x: V(x[1]), reverse=True):
            pkgarch = _pkgname.split('.')[-1]
            if pkgarch not in ('i386', 'i586', 'i686', 'ia32'):
                #print "add", _pkgname, "because", pkgarch, "not in ('i386', 'i586', 'i686', 'ia32')"
                ll.append(_pkgname)
            elif not ix86_added:
                #print "add", _pkgname, "because", pkgarch, "not ix86_added"
                ll.append(_pkgname)
                ix86_added = True
        l = ll

        if arch_specified or len(l) == 1:
            return l

        if os.environ['OSVC_COMP_NODES_OS_ARCH'] in ('i386', 'i586', 'i686', 'ia32'):
            archs = ('i386', 'i586', 'i686', 'ia32', 'noarch')
        else:
            archs = (os.environ['OSVC_COMP_NODES_OS_ARCH'], 'noarch')

        ll = []
        for pkgname in l:
            pkgarch = pkgname.split('.')[-1]
            if pkgarch not in archs:
                # keep only packages matching the arch
                continue
            ll.append(pkgname)

        return ll

    def hp_parse_swlist(self, out):
        l = {}
        for line in out.split('\n'):
            if line.startswith('#') or len(line) == 0:
                continue
            v = line.split()
            if len(v) < 2:
                continue
            if v[0] in l:
                l[v[0]] += [(v[1], "")]
            else:
                l[v[0]] = [(v[1], "")]
        return l

    def hp_del_pkg(self, pkg):
        print >>sys.stderr, "TODO:", __fname__
        return RET_ERR

    def hp_fix_pkg(self, pkg):
        if pkg in self.reloc:
            pkg = ':'.join((pkg, self.reloc[pkg]))
        cmd = ['swinstall',
               '-x', 'allow_downdate=true',
               '-x', 'mount_all_filesystems=false',
               '-s', self.uri, pkg]
        print " ".join(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if len(out) > 0:
            print out
        if len(err) > 0:
            print >>sys.stderr, err
        if p.returncode != 0:
            return RET_ERR
        return RET_OK

    def hp_get_installed_packages(self):
        p = Popen(['swlist', '-l', self.pkg_type], stdout=PIPE)
        (out, err) = p.communicate()
        if p.returncode != 0:
            print >>sys.stderr, 'can not fetch installed packages list'
            return []
        return self.hp_parse_swlist(out).keys()

    def get_free(self, c):
        if not os.path.exists(c):
            return 0
        cmd = ["df", "-k", c]
        p = Popen(cmd, stdout=PIPE, stderr=None)
        out, err = p.communicate()
        for line in out.split():
            if "%" in line:
                l = out.split()
                for i, w in enumerate(l):
                    if '%' in w:
                        break
                try:
                    f = int(l[i-1])
                    return f
                except:
                    return 0
        return 0

    def get_temp_dir(self):
        if hasattr(self, "tmpd"):
            return self.tmpd
        candidates = ["/tmp", "/var/tmp", "/root"]
        free = {}
        for c in candidates:
            free[self.get_free(c)] = c
        max = sorted(free.keys())[-1]
        self.tmpd = free[max]
        print "selected %s as temp dir (%d KB free)" % (self.tmpd, max)
        return self.tmpd

    def download(self, pkg_name):
        import urllib
        import tempfile
        f = tempfile.NamedTemporaryFile(dir=self.get_temp_dir())
        dname = f.name
        f.close()
        try:
            os.makedirs(dname)
        except:
            pass
        fname = os.path.join(dname, "file")
        try:
            fname, headers = urllib.urlretrieve(pkg_name, fname)
        except IOError:
            import traceback
            e = sys.exc_info()
            try:
                os.unlink(fname)
                os.unlink(dname)
            except:
                pass
            raise Exception("download failed: %s" % str(e[1]))
        if 'invalid file' in headers.values():
            try:
                os.unlink(fname)
                os.unlink(dname)
            except:
                pass
            raise Exception("invalid file")
        with open(fname, 'r') as f:
            content = f.read(500)
        if content.startswith('<') and '404' in content and 'Not Found' in content:
            try:
                os.unlink(fname)
                os.unlink(dname)
            except:
                pass
            raise Exception("not found")
        import tarfile
        os.chdir(dname)
        try:
            tar = tarfile.open(fname)
        except:
            print "not a tarball"
            return fname
        try:
            tar.extractall()
        except:
            try:
                os.unlink(fname)
                os.unlink(dname)
            except:
                pass
            # must be a pkg
            return dname
        tar.close()
        os.unlink(fname)
        return dname

    def get_os_ver(self):
        cmd = ['uname', '-v']
        p = Popen(cmd, stdout=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            return 0
        lines = out.split('\n')
        if len(lines) == 0:
            return 0
        try:
            osver = float(lines[0])
        except:
            osver = 0
        return osver

    def sol_get_installed_packages(self):
        p = Popen(['pkginfo', '-l'], stdout=PIPE)
        (out, err) = p.communicate()
        if p.returncode != 0:
            print >>sys.stderr, 'can not fetch installed packages list'
            return []
        l = []
        for line in out.split('\n'):
            v = line.split(':')
            if len(v) != 2:
                continue
            f = v[0].strip()
            if f == "PKGINST":
                pkgname = v[1].strip()
                l.append(pkgname)
        return l

    def sol_del_pkg(self, pkg):
        if pkg not in self.installed_packages:
            return RET_OK
        yes = os.path.dirname(__file__) + "/yes"
        cmd = '%s | pkgrm %s' % (yes, pkg)
        print(cmd)
        r = os.system(cmd)
        if r != 0:
            return RET_ERR
        return RET_OK

    def sol_fix_pkg(self, pkg):
        data = self.data[pkg]
        if 'repo' not in data or len(data['repo']) == 0:
            print >>sys.stderr, "no repo specified in the rule"
            return RET_NA

        pkg_url = data['repo']+"/"+pkg
        print "download", pkg_url
        try:
            dname = self.download(pkg_url)
        except Exception as e:
            print >>sys.stderr, e
            return RET_ERR

        if os.path.isfile(dname):
            d = dname
        else:
            d = "."
            os.chdir(dname)

        if self.get_os_ver() < 10:
            opts = ''
        else:
            opts = '-G'
        if 'resp' in data and len(data['resp']) > 0:
            f = tempfile.NamedTemporaryFile(dir=self.get_temp_dir())
            resp = f.name
            f.close()
            with open(resp, "w") as f:
                f.write(data['resp'])
        else:
            resp = "/dev/null"
        yes = os.path.dirname(__file__) + "/yes"
        cmd = '%s | pkgadd -r %s %s -d %s all' % (yes, resp, opts, d)
        print(cmd)
        r = os.system(cmd)

        os.chdir("/")
        if os.path.isdir(dname):
            import shutil
            shutil.rmtree(dname)
        if r != 0:
            return RET_ERR
        return RET_OK

    def aix_del_pkg(self, pkg):
        cmd = ['installp', '-u', pkg]
        print " ".join(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if len(out) > 0:
            print out
        if len(err) > 0:
            print >>sys.stderr, err
        if p.returncode != 0:
            return RET_ERR
        return RET_OK

    def aix_fix_pkg(self, pkg):
        cmd = ['nimclient', '-o', 'cust',
               '-a', 'lpp_source=%s'%self.uri,
               '-a', 'installp_flags=Y',
               '-a', 'filesets=%s'%pkg]
        s = " ".join(cmd)
        print s
        r = os.system(s)
        if r != 0:
            return RET_ERR
        return RET_OK

    def aix_get_installed_packages(self):
        cmd = ['lslpp', '-Lc']
        p = Popen(cmd, stdout=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            print >>sys.stderr, 'can not fetch installed packages list'
            return []
        pkgs = []
        for line in out.split('\n'):
            l = line.split(':')
            if len(l) < 5:
                continue
            pkgvers = l[2]
            pkgname = l[1].replace('-'+pkgvers, '')
            pkgs.append(pkgname)
        return pkgs

    def freebsd_pkg_get_installed_packages(self):
        p = Popen(['pkg', 'info'], stdout=PIPE)
        (out, err) = p.communicate()
        if p.returncode != 0:
            print >>sys.stderr, 'can not fetch installed packages list'
            return []
        l = []
        for line in out.split('\n'):
            try:
                i = line.index(" ")
                line = line[:i]
                i = line.rindex("-")
                l.append(line[:i])
            except ValueError:
                pass
        return l

    def rpm_get_installed_packages(self):
        p = Popen(['rpm', '-qa', '--qf', '%{NAME}.%{ARCH}\n'], stdout=PIPE)
        (out, err) = p.communicate()
        if p.returncode != 0:
            print >>sys.stderr, 'can not fetch installed packages list'
            return []
        return out.split('\n')

    def deb_get_installed_packages(self):
        p = Popen(['dpkg', '-l'], stdout=PIPE)
        (out, err) = p.communicate()
        if p.returncode != 0:
            print >>sys.stderr, 'can not fetch installed packages list'
            return []
        l = []
        for line in out.split('\n'):
            if not line.startswith('ii'):
                continue
            pkgname = line.split()[1]
            pkgname = pkgname.split(':')[0]
            l.append(pkgname)
        return l

    def freebsd_pkg_del_pkg(self, pkg):
        cmd = ['pkg', 'remove', '-y', pkg]
        print ' '.join(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            if len(err) > 0:
                print err
            return RET_ERR
        return RET_OK

    def freebsd_pkg_fix_pkg(self, pkg):
        cmd = ['pkg', 'install', '-y', pkg]
        print ' '.join(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            if len(err) > 0:
                print err
            return RET_ERR
        return RET_OK

    def zyp_del_pkg(self, pkg):
        cmd = ['zypper', 'remove', '-y', pkg]
        print ' '.join(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            if len(err) > 0:
                print err
            return RET_ERR
        return RET_OK

    def zyp_fix_pkg(self, pkg):
        cmd = ['zypper', 'install', '-y', pkg]
        print ' '.join(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            if len(err) > 0:
                print err
            return RET_ERR
        return RET_OK

    def yum_del_pkg(self, pkg):
        if type(pkg) == list:
            cmd = ['yum', '-y', 'remove'] + pkg
        else:
            cmd = ['yum', '-y', 'remove', pkg]
        print ' '.join(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            if len(err) > 0:
                print err
            return RET_ERR
        return RET_OK

    def yum_fix_pkg(self, pkg):
        cmd = ['yum', '-y', 'install'] + pkg
        print ' '.join(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            if len(err) > 0:
                print err
            return RET_ERR
        return RET_OK

    def apt_del_pkg(self, pkg):
        r = call(['apt-get', 'remove', '-y', pkg])
        if r != 0:
            return RET_ERR
        return RET_OK

    def apt_fix_pkg(self, pkg):
        r = call(['apt-get', 'install', '--allow-unauthenticated', '-y', pkg])
        if r != 0:
            return RET_ERR
        return RET_OK

    def fixable(self):
        return RET_NA

    def fix_pkg_combo(self):
        l_add = []
        l_del = []
        for pkg in self.packages:
            if pkg.startswith('-') and len(pkg) > 1:
                l_del.append(pkg[1:])
            elif pkg.startswith('+') and len(pkg) > 1:
                l_add.append(pkg[1:])
            else:
                l_add.append(pkg)
        if len(l_add) > 0:
            r = self.pkg_add(l_add)
            if r != RET_OK:
                return r
        if len(l_del) > 0:
            r = self.pkg_del(l_del)
            if r != RET_OK:
                return r
        return RET_OK
        
    def fix_pkg(self, pkg):
        if pkg.startswith('-') and len(pkg) > 1:
            return self.pkg_del(pkg[1:])
        if pkg.startswith('+') and len(pkg) > 1:
            return self.pkg_add(pkg[1:])
        else:
            return self.pkg_add(pkg)

    def check_pkg(self, pkg, verbose=True):
        if pkg.startswith('-') and len(pkg) > 1:
            return self.check_pkg_del(pkg[1:], verbose)
        if pkg.startswith('+') and len(pkg) > 1:
            return self.check_pkg_add(pkg[1:], verbose)
        else:
            return self.check_pkg_add(pkg, verbose)

    def check_pkg_del(self, pkg, verbose=True):
        if pkg in self.installed_packages:
            if verbose:
                print >>sys.stderr, 'package', pkg, 'is installed'
            return RET_ERR
        if verbose:
            print 'package', pkg, 'is not installed'
        return RET_OK

    def check_pkg_add(self, pkg, verbose=True):
        if not pkg in self.installed_packages:
            if verbose:
                print >>sys.stderr, 'package', pkg, 'is not installed'
            return RET_ERR
        if verbose:
            print 'package', pkg, 'is installed'
        return RET_OK

    def check(self):
        r = 0
        for pkg in self.packages:
            r |= self.check_pkg(pkg)
        return r

    def fix(self):
        r = 0
        if self.combo_fix:
            return self.fix_pkg_combo()
        for pkg in self.packages:
            if self.check_pkg(pkg, verbose=False) == RET_OK:
                continue
            r |= self.fix_pkg(pkg)
        return r

if __name__ == "__main__":
    syntax = """syntax:
      %s PREFIX check|fixable|fix [uri]"""%sys.argv[0]
    if len(sys.argv) not in [3, 4]:
        print >>sys.stderr, "wrong number of arguments"
        print >>sys.stderr, syntax
        sys.exit(RET_ERR)
    try:
        argv = [sys.argv[1]]
        if len(sys.argv) == 4:
            argv.append(sys.argv[3])
        o = CompPackages(*argv)
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
    except ComplianceError:
        sys.exit(RET_ERR)
    except NotApplicable:
        sys.exit(RET_NA)
    except:
        import traceback
        traceback.print_exc()
        sys.exit(RET_ERR)

    sys.exit(RET)

