import logging
import os
from pathlib import Path

import paramiko

from common.util.base_cmd_helper import BaseCmdHelper

# TODO: Replace with correct logger impl
logger = logging.getLogger()
logging.getLogger("paramiko").setLevel(logging.WARNING)


def pretty_boundary(func):
    def inner(*args, **kwargs):
        print("-" * 80)
        result = func(*args, **kwargs)
        print("-" * 80)
        return result

    return inner


class SshCmdHelper(BaseCmdHelper):
    def __init__(self, hostname, username, password, container_mode_enabled=False):
        self.ssh = paramiko.SSHClient()  # will create the object
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # no known_hosts error
        self.ssh.connect(hostname, username=username, password=password)
        self._on_host = not container_mode_enabled

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.ssh.close()

    @pretty_boundary
    def run_cmd(self, cmd: str, ignore_errors=False):
        if not self._on_host:
            cmd = f"cat <<EOF | docker exec --interactive arcas-tkg bash\n{cmd.strip()}\nEOF"
        logger.debug(f"Running cmd: {cmd}")
        tran = self.ssh.get_transport()
        chan = tran.open_session()
        chan.set_combine_stderr(True)
        chan.get_pty()
        f = chan.makefile()
        chan.exec_command(cmd)
        for line in iter(lambda: f.readline(2048), ""):
            # logger.debug(line.strip("\n"))
            print(line, end="")
        error_code = chan.recv_exit_status()
        if error_code != 0 and not ignore_errors:
            logger.error(f"exit code: {error_code}\n Error executing: {cmd}")
            raise Exception(f"Error executing command: {cmd}")
        return error_code

    @pretty_boundary
    def run_cmd_output(self, cmd: str) -> tuple:
        if not self._on_host:
            cmd = f"cat <<EOF | docker exec --interactive arcas-tkg bash\n{cmd.strip()}\nEOF"
        logger.debug(f"Running cmd: {cmd.strip()}")
        tran = self.ssh.get_transport()
        with tran.open_session() as chan:
            chan.set_combine_stderr(True)
            chan.get_pty()
            f = chan.makefile()
            chan.exec_command(cmd)
            output = f.read().decode()
            logger.debug(f"Received output: \n{output}")
            if chan.recv_exit_status() != 0:
                logger.error(f"exit code: {chan.recv_exit_status()}\n Error executing: {cmd}")
            return chan.recv_exit_status(), output

    @pretty_boundary
    def copy_file(self, src_path: str, dst_path: str):
        self._create_dir_on_host()
        tmp_location = os.path.join("/tmp/arcas", Path(dst_path).name)
        dst = dst_path if self._on_host else tmp_location
        logger.info(f"Copying local file {src_path} to remote path: {dst}")
        sftp = self.ssh.open_sftp()
        sftp.put(src_path, dst)
        sftp.close()
        if not self._on_host:
            logger.info("Copying file to container")
            self.run_cmd(cmd=f"docker cp {tmp_location} arcas-tkg:{dst_path}", on_host=True)

    @pretty_boundary
    def copy_file_from_remote(self, src_path: str, dst_path: str):
        self._create_dir_on_host()
        tmp_location = os.path.join("/tmp/arcas", Path(src_path).name)
        if not self._on_host:
            logger.info("Copying file to host")
            self.run_cmd(cmd=f"docker cp arcas-tkg:{src_path} {tmp_location}", on_host=True)
        sftp = self.ssh.open_sftp()
        src = src_path if self._on_host else tmp_location
        logger.info(f"Copying remote file {src} to local path: {dst_path}")
        sftp.get(src, dst_path)
        sftp.close()

    def _create_dir_on_host(self, path="/tmp/arcas"):
        """
        Create a directory on host, irrespective of whether docker mode is enabled in the spec
        :param path: (Optional) Absolute path of directory to be created. Default: /tmp/arcas
        :return:
        """
        val = self._on_host is True
        self._on_host = True
        self.run_cmd(f"mkdir -p {path}", ignore_errors=True)
        self._on_host = val
