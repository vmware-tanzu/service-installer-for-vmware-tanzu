#!/usr/local/bin/python3

#  Copyright 2022 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

__author__ = "Abhishek Inani"

import os
import shlex
import tarfile
import zipfile
import argparse
import glob
import subprocess
from pathlib import Path

class DependentTarProcessing:
    """To process dependent tar of tekton dependencies"""
    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--tar_file", help="Tar file name present in $HOME directory. Default sivt_tekton_airgapped_dependencies.tar",
                                 default="sivt_tekton_airgapped_dependencies.tar")
        self.parser.add_argument("--harbor_url", help="Harbor URL", required=True)
        args = self.parser.parse_args()

        self.tar_file = args.tar_file
        self.harbor_url = args.harbor_url
        self.default_root_dir = Path.home()
        self.default_harbor_url = "harbor.tsv.local"
        self.img_dict = {"docker":"dind",
                         "git-init":"v0.40.2",
                         "kubeconfigwriter":"v0.40.2",
                         "controller":"v0.40.2",
                         "imagedigestexporter":"v0.40.2",
                         "pullrequest-init":"v0.40.2",
                         "entrypoint":"v0.40.2",
                         "workingdirinit":"v0.40.2",
                         "nop":"v0.40.2",
                         "webhook":"v0.40.2",
                         "cloud-sdk":"latest",
                         "distroless/busybox":"latest",
                         "kindest/node":"v1.22.0",
                         "dashboard":"v0.29.2",
                         "ingress_nginx/controller":"v1.4.0",
                         "ingress_nginx/kube_webhook_certgen":"v20220916",
                         "triggers/eventlistener":"v0.21.0",
                         "triggers/controller":"v0.21.0",
                         "triggers/webhook":"v0.21.0",
                         "polling/tekton-polling-operator":"v0.4.0"}

    def process_dependent_tar(self) -> bool:
        """
        Method to process dependent tar of tekton
        :return: None
        """
        try:
            untar_dir = os.path.join(self.default_root_dir,
                                   self.extract_file_module(os.path.join(self.default_root_dir, self.tar_file)))
            tar_files = [file for file in glob.glob(f"{untar_dir}/*.tar")]
            self.docker_load_tar(tar_files)
            self.docker_tag()
            self.docker_push_to_harbor()
            self.cleanup_docker()
        except Exception as e:
            print(f"Exception occurred as {e}")
            return False

    def docker_load_tar(self, tar_files: list):
        """
        Method to tag the docker images
        """
        print(f"Loading the tar images to Docker........")
        for tar_file in tar_files:
            load_cmd = f"docker load -i {tar_file}"
            DependentTarProcessing.execute(shlex.split(load_cmd))

    def docker_tag(self):
        """
        Method to tag the docker images
        """
        print(f"Tagging the images to Docker........")
        tag_cmd = ""
        for img, tag in self.img_dict.items():
            if img in ["docker", "kindest/node"]:
                tag_cmd = f"docker image tag {img}:{tag} {self.harbor_url}/tekton_dep/{img}:{tag}"
            else:
                tag_cmd = f"docker image tag {self.default_harbor_url}/tekton_dep/{img}:{tag} {self.harbor_url}/tekton_dep/{img}:{tag}"
            DependentTarProcessing.execute(shlex.split(tag_cmd))

    def docker_push_to_harbor(self):
        """
        Method to push the docker images to harbor
        """
        print(f"Pushing the images to Harbor........")
        try:
            hrbr_login_cmd = f"docker login {self.harbor_url}"
            out, ret = DependentTarProcessing.execute(shlex.split(hrbr_login_cmd), capture_output=True)
            if "Login Succeeded" in out:
                for img, tag in self.img_dict.items():
                    push_cmd = f"docker push {self.harbor_url}/tekton_dep/{img}:{tag}"
                    DependentTarProcessing.execute(shlex.split(push_cmd))
            else:
                print("Couldn't login to harbor. Please check certificates")
        except Exception as e:
            print(f"Exception as [ {e} ]")

    def cleanup_docker(self):
        """
        Method to cleanup the docker images
        """
        print(f"Clean images in Docker........")
        clean_cmd = ""
        try:
            for img, tag in self.img_dict.items():
                if img in ["docker", "kindest/node"]:
                    clean_cmd = f"docker rmi {img}:{tag}"
                else:
                    clean_cmd = f"docker rmi {self.default_harbor_url}/tekton_dep/{img}:{tag}"
                DependentTarProcessing.execute(shlex.split(clean_cmd))
        except Exception as e:
            print(f"Exception as [ {e} ]")


    @staticmethod
    def extract_file_module(fname: str) -> str:
        """
        Method to extract the content of .tar, .tar.gz/tgz, .tar.bz2/tbz, .zip format files to current directory

        :param fname: file to be extracted
        :return: Extracted file directory name

        Pros:
         - Check if provided file is really in given format or dummy file, raise exception in case dummy file
         - Uses tarfile and zipfile builtin library of Python
         - Return extracted file directory
         - Uses context manager to safely close the tar and zip objects without user's intervention
        """
        print(f"Extracting : {fname} .....")
        try:
            if fname.endswith(".tar.gz") or fname.endswith('.tgz'):
                print("Detected package is .tar.gz")
                with tarfile.open(fname, "r:gz") as tar:
                    tar.extractall(path=Path.home())
                    return tar.getnames()[0]
            elif fname.endswith(".tar"):
                print("Detected package is .tar")
                with tarfile.open(fname, "r:") as tar:
                    tar.extractall(path=Path.home())
                    return tar.getnames()[0]
            elif fname.endswith(".tar.bz2") or fname.endswith('.tbz'):
                print("Detected package is .tar.bz2")
                with tarfile.open(fname, "r:bz2") as tar:
                    tar.extractall(path=Path.home())
                    return tar.getnames()[0]
            elif fname.endswith(".zip"):
                print("Detected package is .zip")
                with zipfile.ZipFile(fname, "r") as zip1:
                    zip1.extractall(path=Path.home())
                    return zip1.namelist()[0].split('/')[0]
            else:
                raise ValueError(f'Could not extract {fname} as no appropriate extractor is found')
        except FileNotFoundError as fnf:
            raise Exception(f'Extraction failed: {fnf}')

    @staticmethod
    def execute(cmd, capture_output=False):
        """"
        Method to execute commands using subprocess module"""
        print(f"Command to execute: \n\"{' '.join(cmd)}\"")
        if capture_output:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stderr=subprocess.STDOUT,
                    stdout=subprocess.PIPE
                )
                output = proc.communicate()[0]
                formatted_output = output.decode("utf-8").rstrip("\n\r").replace("\x1b[0m", "").replace("\x1b[1m", "")
                print(
                    f"Output: \n {'*' * 10}Output Start{'*' * 10}\n{formatted_output}\n{'*' * 10}Output End{'*' * 10}")
                return_code = 1 if formatted_output.__contains__("error") else 0
            except subprocess.CalledProcessError as e:
                return_code = 1
                formatted_output = e.output
            return formatted_output.rstrip("\n\r"), return_code
        else:
            popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
            for stdout_line in iter(popen.stdout.readline, ""):
                print(stdout_line)
            popen.stdout.close()
            return_code = popen.wait()
            if return_code:
                raise subprocess.CalledProcessError(return_code, cmd)


if __name__ == "__main__":
    tar_proc = DependentTarProcessing()
    tar_proc.process_dependent_tar()

