# -*- coding: utf8 -*-

"""
The module implementing the DockerLib class.
"""
import os
from distutils.version import LooseVersion as V

import json
import re
import rcStatus
import rcExceptions as ex

from rcUtilities import which, justcall, lazy, unset_lazy
from rcGlobalEnv import rcEnv
from svcBuilder import conf_get_string_scope, conf_get_boolean_scope

os.environ['LANG'] = 'C'

class DockerLib(object):
    """
    Instanciated as the 'dockerlib' Svc lazy attribute, this class abstracts
    docker daemon ops.
    """
    def __init__(self, svc=None):
        self.svc = svc
        self.max_wait_for_dockerd = 5
        self.docker_info_done = False

        try:
            self.docker_daemon_private = \
                conf_get_boolean_scope(svc, svc.config, 'DEFAULT', 'docker_daemon_private')
        except ex.OptNotFound:
            self.docker_daemon_private = True
        if rcEnv.sysname != "Linux":
            self.docker_daemon_private = False

        try:
            self.docker_exe_init = \
                conf_get_string_scope(svc, svc.config, 'DEFAULT', 'docker_exe')
        except ex.OptNotFound:
            self.docker_exe_init = None

        try:
            self.dockerd_exe_init = \
                conf_get_string_scope(svc, svc.config, 'DEFAULT', 'dockerd_exe')
        except ex.OptNotFound:
            self.dockerd_exe_init = None

        try:
            self.docker_data_dir = \
                conf_get_string_scope(svc, svc.config, 'DEFAULT', 'docker_data_dir')
        except ex.OptNotFound:
            self.docker_data_dir = None

        try:
            self.docker_daemon_args = \
                conf_get_string_scope(svc, svc.config, 'DEFAULT', 'docker_daemon_args').split()
        except ex.OptNotFound:
            self.docker_daemon_args = []

        try:
            self.docker_swarm_args = \
                conf_get_string_scope(svc, svc.config, 'DEFAULT', 'docker_swarm_args').split()
        except ex.OptNotFound:
            self.docker_swarm_args = []

        try:
            self.docker_swarm_managers = \
                conf_get_string_scope(svc, svc.config, 'DEFAULT', 'docker_swarm_managers').split()
        except ex.OptNotFound:
            self.docker_swarm_managers = []

        if self.docker_data_dir:
            if "--exec-opt" not in self.docker_daemon_args and self.docker_min_version("1.7"):
                self.docker_daemon_args += ["--exec-opt", "native.cgroupdriver=cgroupfs"]

        if "--token" in self.docker_swarm_args:
            raise ex.excError("--token must not be specified in DEFAULT.docker_swarm_args")

        self.docker_var_d = os.path.join(rcEnv.pathvar, self.svc.svcname)

        if not os.path.exists(self.docker_var_d):
            os.makedirs(self.docker_var_d)
        elif self.docker_daemon_private:
            self.docker_socket = "unix://"+os.path.join(self.docker_var_d, 'docker.sock')
        else:
            self.docker_socket = None

        if self.docker_daemon_private:
            self.docker_pid_file = os.path.join(self.docker_var_d, 'docker.pid')
        else:
            self.docker_pid_file = None
            lines = [line for line in self.docker_info.splitlines() if "Root Dir" in line]
            try:
                self.docker_data_dir = lines[0].split(":")[-1].strip()
            except IndexError:
                self.docker_data_dir = None

        self.docker_cmd = [self.docker_exe]
        if self.docker_socket:
            self.docker_cmd += ['-H', self.docker_socket]

    def get_ps(self, refresh=False):
        """
        Return the 'docker ps' output from cache or from the command
        execution depending on <refresh>.
        """
        if refresh:
            unset_lazy(self, "docker_ps")
        return self.docker_ps

    @lazy
    def docker_ps(self):
        """
        The "docker ps" output.
        """
        cmd = self.docker_cmd + ['ps', '-a', '--no-trunc']
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)
        return out

    def docker_node_rm(self, ref):
        """
        Execute "docker node rm <ref>"
        """
        cmd = self.docker_cmd + ['node', 'rm', ref]
        self.svc.log.debug("remove replaced node %s" % ref)
        self.svc.log.debug(" ".join(cmd))
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)

    @lazy
    def docker_service_ls(self):
        """
        The "docker service ls" output.
        """
        cmd = self.docker_cmd + ['service', 'ls']
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)
        return out

    def docker_service_ps(self, service):
        """
        The "docker service ps <service>" output.
        """
        if service is None:
            return ""
        cmd = self.docker_cmd + ['service', 'ps', service]
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)
        return out

    def service_ps_data(self, service):
        lines = self.docker_service_ps(service).splitlines()
        if len(lines) < 2:
            return []
        ids = []
        for line in lines[1:]:
            if "\_" in line:
                # don't care about "history" lines
                continue
            line = line.strip().split()
            if len(line) == 0:
                continue
            ids.append(line[0])
        data = self.docker_inspect(ids)

        # discard lines with left nodes
        node_ids = self.node_ids()
        data = [inst for inst in data if "NodeID" in inst and inst["NodeID"] in node_ids]
        return data

    def docker_node_ls(self):
        """
        The "docker node ls" output.
        """
        cmd = self.docker_cmd + ['node', 'ls', '-q']
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)
        return out

    def node_ids(self):
        return self.docker_node_ls().strip().splitlines()

    def node_ls_data(self):
        cmd = self.docker_cmd + ['node', 'inspect'] + self.node_ids()
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)
        return json.loads(out)

    def node_data(self):
        cmd = self.docker_cmd + ['node', 'inspect', rcEnv.nodename]
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)
        return json.loads(out)[0]

    @lazy
    def service_ls_data(self):
        """
        A hash of services data as found in "docker service ls",
        indexed by service name.
        """
        lines = self.docker_service_ls.splitlines()
        if len(lines) < 2:
            return
        header = lines[0].strip().split()
        try:
            service_id_idx = header.index('ID')
            service_name_idx = header.index('NAME')
            service_mode_idx = header.index('MODE')
            service_replicas_idx = header.index('REPLICAS')
            service_image_idx = header.index('IMAGE')
        except (IndexError, ValueError):
            return
        ref_len = len(header)
        data = {}
        for line in lines[1:]:
            line = line.strip().split()
            if len(line) != ref_len:
                continue
            service_name = line[service_name_idx].strip()
            data[service_name] = {
                "name": service_name,
                "id": line[service_id_idx].strip(),
                "mode": line[service_mode_idx].strip(),
                "replicas": line[service_replicas_idx].strip().split("/"),
                "image": line[service_image_idx].strip(),
            }
        return data

    @lazy
    def container_id_by_name(self):
        """
        A hash of instances data as found in "docker ps", indexed by
        instance id.
        """
        lines = self.docker_ps.splitlines()
        if len(lines) < 2:
            return
        try:
            start = lines[0].index('NAMES')
        except (IndexError, ValueError):
            return
        data = {}
        for line in lines[1:]:
            if len(line.strip()) == 0:
                continue
            try:
                names = line[start:].strip().split(',')
            except IndexError:
                continue
            for name in names:
                # swarm names are preffixed by <nodename>/
                elements = name.split("/")
                container_name = elements[-1]
                if len(elements) == 2:
                    swarm_node = elements[0]
                else:
                    swarm_node = None
                data[container_name] = {
                    "id": line.split()[0],
                    "swarm_node": swarm_node,
                }
        return data

    def get_container_id_by_name(self, resource, refresh=False):
        """
        Return the container id for the <resource> container resource.
        Lookup in docker ps by docker name <svcname>.container.<n> where
        <n> is the identifier part of the resource id.
        """
        if refresh:
            unset_lazy(self, "docker_ps")
            unset_lazy(self, "container_id_by_name")
        if resource.docker_service:
            prefix = resource.service_name+"."
            if self.container_id_by_name is None:
                return
            for container_name, data in self.container_id_by_name.items():
                if container_name.startswith(prefix):
                    return data["id"]
        else:
            if self.container_id_by_name is None or \
                resource.container_name not in self.container_id_by_name:
                return
            data = self.container_id_by_name[resource.container_name]
            return data["id"]

    def get_service_id_by_name(self, resource, refresh=False):
        """
        Return the service id for the <resource> container resource.
        Lookup in docker service ls by docker name <svcname>_container_<n>
        where <n> is the identifier part of the resource id.
        """
        if refresh:
            unset_lazy(self, "docker_service_ls")
            unset_lazy(self, "service_ls_data")
        if self.service_ls_data is None or \
           resource.service_name not in self.service_ls_data:
            return
        data = self.service_ls_data[resource.service_name]
        return data["id"]


    @lazy
    def docker_info(self):
        """
        The output of "docker info".
        """
        cmd = [self.docker_exe, "info"]
        return justcall(cmd)[0]

    @lazy
    def docker_version(self):
        """
        The docker version.
        """
        cmd = [self.docker_exe, "--version"]
        out = justcall(cmd)[0]
        elements = out.split()
        if len(elements) < 3:
            return False
        return elements[2].rstrip(",")

    def docker_min_version(self, version):
        """
        Return True if the docker version is at least <version>.
        """
        if V(self.docker_version) >= V(version):
            return True
        return False

    def get_running_service_ids(self, refresh=False):
        """
        Return the list of running docker services id.
        """
        if refresh:
            unset_lazy(self, "running_service_ids")
            unset_lazy(self, "docker_service_ls")
            unset_lazy(self, "service_ls_data")
        return self.running_service_ids

    @lazy
    def running_service_ids(self):
        """
        The list of running docker services id.
        """
        if self.service_ls_data is None:
            return []
        return [service["id"] for service in self.service_ls_data.values()]

    def get_running_instance_ids(self, refresh=False):
        """
        Return the list of running docker instances id.
        """
        if refresh:
            unset_lazy(self, "running_instance_ids")
        return self.running_instance_ids

    @lazy
    def running_instance_ids(self):
        """
        The list of running docker instances id.
        """
        cmd = self.docker_cmd + ['ps', '-q', '--no-trunc']
        out = justcall(cmd)[0]
        return out.replace('\n', ' ').split()

    def get_run_image_id(self, resource, run_image=None):
        """
        Return the full docker image id
        """
        if run_image is None and hasattr(resource, "run_image"):
            run_image = resource.run_image
        if len(run_image) == 12 and re.match('^[a-f0-9]*$', run_image):
            return run_image
        if run_image.startswith("sha256:"):
            return run_image

        try:
            image_name, image_tag = run_image.split(':')
        except ValueError:
            return

        if self.docker_min_version("1.13"):
            data = self.docker_image_inspect(run_image)
            if data is None:
                self.docker_pull(run_image)
                data = self.docker_image_inspect(run_image)
            if data is None:
                raise ValueError("image %s not pullable" % run_image)
            return data["Id"]

        cmd = self.docker_cmd + ['images', '--no-trunc', image_name]
        results = justcall(cmd)
        if results[2] != 0:
            return run_image
        for line in results[0].splitlines():
            elements = line.split()
            if len(elements) < 3:
                continue
            if elements[0] == image_name and elements[1] == image_tag:
                return elements[2]
        return run_image

    def docker_pull(self, ref):
        self.svc.log.info("pulling docker image %s" % ref)
        cmd = self.docker_cmd + ['pull', ref]
        results = justcall(cmd)
        if results[2] != 0:
            raise ex.excError(results[1])

    @lazy
    def images(self):
        """
        The hash of docker images, indexed by image id.
        """
        cmd = self.docker_cmd + ['images', '--no-trunc']
        results = justcall(cmd)
        if results[2] != 0:
            return
        data = {}
        for line in results[0].splitlines():
            elements = line.split()
            if len(elements) < 3:
                continue
            if elements[2] == "IMAGE":
                continue
            data[elements[2]] = elements[0]+':'+elements[1]
        return data

    def info(self):
        """
        Return the keys contributed to resinfo.
        """
        if self.docker_info_done:
            return []
        data = []
        data += self._docker_info_version()
        data += self._docker_info_drivers()
        data += self._docker_info_images()
        return data

    def _docker_info_version(self):
        """
        Return the docker version key conttributed to resinfo.
        """
        return [[
            "",
            "docker_version",
            self.docker_version
        ]]

    def _docker_info_drivers(self):
        """
        Return the docker drivers keys conttributed to resinfo.
        """
        data = []
        lines = self.docker_info.splitlines()
        for line in lines:
            elements = line.split(": ")
            if len(elements) < 2:
                continue
            if elements[0] == "Storage Driver":
                data.append(["", "storage_driver", elements[1]])
            if elements[0] == "Execution Driver":
                data.append(["", "exec_driver", elements[1]])
        return data

    def _docker_info_images(self):
        """
        Return the per-container resource resinfo keys.
        """
        data = []
        images_done = []

        # referenced images
        for resource in self.svc.get_resources("container.docker"):
            image_id = self.get_run_image_id(resource)
            images_done.append(image_id)
            data.append([resource.rid, "run_image", resource.run_image])
            data.append([resource.rid, "docker_image_id", image_id])
            data.append([resource.rid, "docker_instance_id", resource.container_id])

        # unreferenced images
        for image_id in self.images:
            if image_id in images_done:
                continue
            data.append(["", "docker_image_id", image_id])
        self.docker_info_done = True

        return data

    def image_userfriendly_name(self, resource):
        """
        Return the container resource docker image name if possible,
        else return the image id.
        """
        if ':' in resource.run_image:
            return resource.run_image
        if self.images is None:
            return resource.run_image
        if resource.run_image in self.images:
            return self.images[resource.run_image]
        return resource.run_image

    def docker_inspect(self, container_id):
        """
        Return the "docker inspect" data dict.
        """
        if isinstance(container_id, list):
            cmd = self.docker_cmd + ['inspect'] + container_id
            out = justcall(cmd)[0]
            data = json.loads(out)
            return data
        else:
            cmd = self.docker_cmd + ['inspect', container_id]
            out = justcall(cmd)[0]
            data = json.loads(out)
            return data[0]

    def docker_service_inspect(self, service_id):
        """
        Return the "docker service inspect" data dict.
        """
        cmd = self.docker_cmd + ['service', 'inspect', service_id]
        out = justcall(cmd)[0]
        data = json.loads(out)
        return data[0]

    def docker_image_inspect(self, image_id):
        """
        Return the "docker image inspect" data dict.
        """
        cmd = self.docker_cmd + ['image', 'inspect', image_id]
        out = justcall(cmd)[0]
        data = json.loads(out)
        if len(data) == 0:
            return
        return data[0]

    def repotag_to_image_id(self, repotag):
        data = self.docker_image_inspect(repotag)
        if data is None:
            return
        return data["Id"]

    def docker_stop(self):
        """
        Stop the docker daemon if possible.
        """
        def can_stop():
            """
            Return True if the docker daemon can be stopped.
            """
            if not self.docker_daemon_private:
                return False
            if not self.docker_running():
                return False
            if self.docker_data_dir is None:
                return False
            if not os.path.exists(self.docker_pid_file):
                return False
            if len(self.get_running_instance_ids(refresh=True)) > 0:
                return False
            return True

        if not can_stop():
            return

        try:
            with open(self.docker_pid_file, 'r') as ofile:
                pid = int(ofile.read())
        except (OSError, IOError):
            self.svc.log.warning("can't read %s. skip docker daemon kill",
                                 self.docker_pid_file)
            return

        self.svc.log.info("no more container handled by docker daemon (pid %d)."
                          " shut it down", pid)
        import signal
        import time
        tries = 10
        os.kill(pid, signal.SIGTERM)
        while self.docker_running() and tries > 0:
            tries -= 1
            time.sleep(1)
        if tries == 0:
            self.svc.log.warning("dockerd did not stop properly. send a kill "
                                 "signal")
            os.kill(pid, signal.SIGKILL)

    @lazy
    def dockerd_cmd(self):
        """
        The docker daemon startup command, adapted to the docker version.
        """
        if self.docker_min_version("1.13"):
            cmd = [
                self.dockerd_exe,
                '-H', self.docker_socket,
                '-g', self.docker_data_dir,
                '-p', self.docker_pid_file
            ]
        elif self.docker_min_version("1.8"):
            cmd = [
                self.docker_exe, 'daemon',
                '-H', self.docker_socket,
                '-g', self.docker_data_dir,
                '-p', self.docker_pid_file
            ]
        else:
            cmd = self.docker_cmd + [
                '-r=false', '-d',
                '-g', self.docker_data_dir,
                '-p', self.docker_pid_file
            ]
        if self.docker_min_version("1.9") and '--exec-root' not in str(self.docker_daemon_args):
            cmd += ["--exec-root", self.docker_data_dir]
        cmd += self.docker_daemon_args
        return cmd

    def _docker_data_dir_resource(self):
        """
        Return the service fs resource handling the docker data dir, or
        None if any.
        """
        mntpts = []
        mntpt_res = {}
        for resource in self.svc.get_resources('fs'):
            mntpts.append(resource.mount_point)
            mntpt_res[resource.mount_point] = resource
        for mntpt in sorted(mntpts, reverse=True):
            if mntpt.startswith(self.docker_data_dir):
                return mntpt_res[mntpt]

    def docker_start(self, verbose=True):
        """
        Start the docker daemon if in private mode and not already running.
        """
        if not self.docker_daemon_private:
            return
        import lock
        lockfile = os.path.join(rcEnv.pathlock, 'docker_start')
        try:
            lockfd = lock.lock(timeout=15, delay=1, lockfile=lockfile)
        except lock.LOCK_EXCEPTIONS as exc:
            self.svc.log.error("dockerd start lock acquire failed: %s",
                               str(exc))
            return

        # Sanity checks before deciding to start the daemon
        if self.docker_running():
            lock.unlock(lockfd)
            return

        if self.docker_data_dir is None:
            lock.unlock(lockfd)
            return

        resource = self._docker_data_dir_resource()
        if resource is not None:
            state = resource._status()
            if state not in (rcStatus.UP, rcStatus.STDBY_UP):
                self.svc.log.warning("the docker daemon data dir is handled by the %s "
                                     "resource in %s state. can't start the docker "
                                     "daemon", resource.rid, rcStatus.Status(state))
                lock.unlock(lockfd)
                return

        if os.path.exists(self.docker_pid_file):
            self.svc.log.warning("removing leftover pid file %s", self.docker_pid_file)
            os.unlink(self.docker_pid_file)

        # Now we can start the daemon, creating its data dir if necessary
        cmd = self.dockerd_cmd

        if verbose:
            self.svc.log.info("starting docker daemon")
            self.svc.log.info(" ".join(cmd))
        import subprocess
        subprocess.Popen(
            ['nohup'] + cmd,
            stdout=open('/dev/null', 'w'),
            stderr=open('/dev/null', 'a'),
            preexec_fn=os.setpgrp
        )

        import time
        try:
            for _ in range(self.max_wait_for_dockerd):
                if self._docker_working():
                    return
                time.sleep(1)
        finally:
            lock.unlock(lockfd)

    def docker_running(self):
        """
        Return True if the docker daemon is running.
        """
        if self.docker_daemon_private:
            return self._docker_running_private()
        else:
            return self._docker_running_shared()

    def _docker_running_shared(self):
        """
        Return True if the docker daemon is running.
        """
        if self.docker_info == "":
            return False
        return True

    def _docker_running_private(self):
        """
        Return True if the docker daemon is running.
        """
        if not os.path.exists(self.docker_pid_file):
            self.svc.log.debug("docker_running: no pid file %s", self.docker_pid_file)
            return False
        try:
            with open(self.docker_pid_file, "r") as ofile:
                buff = ofile.read()
        except IOError as exc:
            if exc.errno == 2:
                return False
            return ex.excError("docker_running: "+str(exc))
        self.svc.log.debug("docker_running: pid found in pid file %s", buff)
        exe = os.path.join(os.sep, "proc", buff, "exe")
        try:
            exe = os.path.realpath(exe)
        except OSError:
            self.svc.log.debug("docker_running: no proc info in /proc/%s", buff)
            try:
                os.unlink(self.docker_pid_file)
            except OSError:
                pass
            return False
        if "docker" not in exe:
            self.svc.log.debug("docker_running: pid found but owned by a "
                               "process that is not a docker (%s)", exe)
            try:
                os.unlink(self.docker_pid_file)
            except OSError:
                pass
            return False
        return True

    def _docker_working(self):
        """
        Return True if the docker daemon responds to a simple 'info' request.
        """
        cmd = self.docker_cmd + ['info']
        ret = justcall(cmd)[2]
        if ret != 0:
            return False
        return True

    @lazy
    def docker_exe(self):
        """
        Return the docker executable to use, using the service configuration
        docker_exe as the first choice, and a docker.io or docker exe found
        in PATH as a fallback.
        """
        if self.docker_exe_init and which(self.docker_exe_init):
            return self.docker_exe_init
        elif which("docker.io"):
            return "docker.io"
        elif which("docker"):
            return "docker"
        else:
            raise ex.excInitError("docker executable not found")

    @lazy
    def dockerd_exe(self):
        if self.dockerd_exe_init and which(self.dockerd_exe_init):
            return self.dockerd_exe_init
        elif which("dockerd"):
            return "dockerd"
        else:
            raise ex.excInitError("dockerd executable not found")

    def join_token(self, ttype):
        self.docker_start()
        cmd = self.docker_cmd + ["swarm", "join-token", ttype]
        results = justcall(cmd)
        if results[2] != 0:
            raise ex.excError(results[1])
        token = None
        for line in results[0].splitlines():
            if "--token" in line:
                token = line.split()[1]
                continue
            if token and ":" in line:
                addr = line.strip()
                return {"token": token, "addr": addr}
        raise ex.excError("unable to determine the swarm worker join token")

    def swarm_initialized(self):
        if self.swarm_node_role == "none":
            return False
        return True

    def join_token_dump_file(self, ttype):
        return os.path.join(rcEnv.paths.pathvar, self.svc.svcname, "swarm_" + ttype + "_join_token")

    def dump_join_tokens(self):
        for ttype in ("manager", "worker"):
            with open(self.join_token_dump_file(ttype), "w") as fp:
                fp.write(json.dumps(self.join_token(ttype)))

    def load_join_token(self, ttype):
        fpath = self.join_token_dump_file(ttype)
        if not os.path.exists(fpath):
            raise ex.excError("the join token has not been transfered by the flex primary node")
        with open(fpath, "r") as fp:
            data = json.load(fp)
        return data

    @lazy
    def files_to_sync(self):
        fpaths = []
        self.dump_join_tokens()
        for ttype in ("manager", "worker"):
            fpath = self.join_token_dump_file(ttype)
            if os.path.exists(fpath):
                fpaths.append(fpath)
        return fpaths

    def init_swarm(self):
        if self.swarm_initialized():
            return
        if rcEnv.nodename == self.svc.flex_primary:
            self.init_swarm_leader()
        elif rcEnv.nodename in self.docker_swarm_managers:
            self.init_swarm_manager()
        else:
            self.init_swarm_worker()
        unset_lazy(self, "swarm_node_role")

    def init_swarm_leader(self):
        cmd = self.docker_cmd + ['swarm', 'init']
        if len(self.docker_swarm_args) > 0:
            cmd += self.docker_swarm_args
        self.svc.log.info(" ".join(cmd))
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)

    def init_swarm_manager(self):
        data = self.load_join_token("manager")
        cmd = self.docker_cmd + ['swarm', 'join', '--token', data["token"], data["addr"]]
        if len(self.docker_swarm_args) > 0:
            cmd += self.docker_swarm_args
        self.svc.log.info(" ".join(cmd))
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)

    def init_swarm_worker(self):
        data = self.load_join_token("worker")
        cmd = self.docker_cmd + ['swarm', 'join', '--token', data["token"], data["addr"]]
        if len(self.docker_swarm_args) > 0:
            cmd += self.docker_swarm_args
        self.svc.log.info(" ".join(cmd))
        out, err, ret = justcall(cmd)
        if ret != 0:
            raise ex.excError(err)

    def docker_swarm_leave(self):
        if self.swarm_node_role == "none":
            return
        cmd = self.docker_cmd + ['swarm', 'leave']
        ret, out, err = self.svc.vcall(cmd)
        if ret != 0:
            raise ex.excError(err)
        unset_lazy(self, "swarm_node_role")

    @lazy
    def swarm_node_role(self):
        """
        Return
        * none : no role in the swarm, not joined yet
        * worker
        * leader
        * reachable
        """
        if not self.docker_running():
            return "none"
        cmd = self.docker_cmd + ['node', 'ls']
        out, err, ret = justcall(cmd)
        if ret != 0:
            if "docker swarm" in err:
                return "none"
            else:
                return "worker"
        for line in out.splitlines():
            line = line.replace(" * ", " ")
            line = line.strip().split()
            if len(line) < 4:
                continue
            if line[1] != rcEnv.nodename:
                continue
            if line[-1] in ("Leader", "Reachable"):
                return line[-1].lower()
            else:
                return "unknown"

    def nodes_purge(self):
        """
        Remove lingering nodes, ie those in down state and
        with an active instance matching the hostname.
        """
        if self.swarm_node_role != "leader":
            return
        nodes = self.node_ls_data()
        down = {}
        for node in nodes:
            nodename = node["Description"]["Hostname"]
            if node["Status"]["State"] != "down":
                continue
            if nodename not in down:
                down[nodename] = []
            down[nodename].append(node["ID"])
        for node in nodes:
            nodename = node["Description"]["Hostname"]
            if node["Status"]["State"] != "ready":
                continue
            if nodename not in down:
                continue
            for node_id in down[nodename]:
                self.docker_node_rm(node_id)
