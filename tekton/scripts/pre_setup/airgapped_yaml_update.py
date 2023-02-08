#!/usr/local/bin/python3

#  Copyright 2022 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

__author__ = "Abhishek Inani"

import os
import sys

import ruamel.yaml
from ruamel.yaml import YAML
from pathlib import Path
import re

from os.path import dirname, abspath


ROOT_DIR = dirname(dirname(dirname(abspath(__file__))))
TASK_DIR = os.path.join(ROOT_DIR, "tasks")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "templates")

KIND_YAML_FILE = "cluster_resources/kind-init-config.yaml"
TEMPLATE_YAML_FILES = [f"{TEMPLATE_DIR}/day0-pipeline-run-template.yaml",
                       f"{TEMPLATE_DIR}/day2-all-pipeline-run-template.yaml",
                       f"{TEMPLATE_DIR}/day2-mgmt-pipeline-run-template.yaml"]
TASKS_YAML_FILES = [f"{TASK_DIR}/mgmt_setup.yml",
                    f"{TASK_DIR}/shared_cluster_setup.yml",
                    f"{TASK_DIR}/wld_setup.yml",
                    f"{TASK_DIR}/extensions_setup.yml",
                    f"{TASK_DIR}/mgmt-upgrade.yml",
                    f"{TASK_DIR}/shared-upgrade.yml",
                    f"{TASK_DIR}/workload-upgrade.yml",
                    f"{TASK_DIR}/extensions_upgrade.yml"]
TEKTON_RELEASE_YAML_FILES = ["release.yaml",
                             "release_dashboard.yaml",
                             "release_trigger.yaml",
                             "nginx_deploy.yaml",
                             "release_polling_operator.yaml"]
GIT_CLONE_YAML_FILE = f"{TASK_DIR}/git-pvtclone.yml"
GIT_COMMIT_YAML_FILE = f"{TASK_DIR}/git_commit.yml"

class NonAliasingRTRepresenter(ruamel.yaml.representer.RoundTripRepresenter):
    def ignore_aliases(self, data):
        return True

class AirgappedYamlUpdate:
    """To Update YAML files if it's Airgapped deployment"""
    def __init__(self) -> None:
        self.harbor_url = None
        self.read_harbor_url()
        self.kind_yaml_file = os.path.join(ROOT_DIR, KIND_YAML_FILE)
        self.tmplt_yaml_files = [yaml_file for yaml_file in TEMPLATE_YAML_FILES]
        self.tasks_yaml_files = [yaml_file for yaml_file in TASKS_YAML_FILES]
        self.tkn_release_yaml_files = [os.path.join(Path.home(), "tkn_utils_v0.40.2", yaml_file)
                                       for yaml_file in TEKTON_RELEASE_YAML_FILES]
        self.default_harbor_url = "harbor.tsv.local"
        self.yaml = YAML()
        self.yaml.Representer = NonAliasingRTRepresenter
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def read_harbor_url(self):
        """
        Method to read harbor URL from values.yaml file
        """
        print("Reading harbor URL from values.yaml file")
        try:
            with open(f"{ROOT_DIR}/values.yaml", "r") as fp:
                content = fp.read()

            for line in content.split("\n"):
                if "harbor_url:" in line:
                    self.harbor_url = line.split(":")[1].strip(" ")
                    print(f"Harbor URL configured as : {self.harbor_url}")
                    break
            else:
                print(f"Harbor URL not found in values.yaml file")
                sys.exit(1)
        except Exception as e:
            print(f"Exception: [ {e} ]")

    def update_all_yamls(self):
        """Method to drive updating YAML files for airgapped deployment"""
        state = []
        state.append(self.update_kind_yaml_file())
        state.append(self.update_pipeline_template_files())
        state.append(self.update_tasks_yaml_files())
        state.append(self.update_git_clone_yaml_file())
        state.append(self.update_git_commit_yaml_file())
        state.append(self.update_tkn_release_yaml_files())
        # Currently these YAMLs not need to checked in private repo, if requried in future will enable this message
        #self.list_yaml_files_to_commit_in_git()
        return all(state)

    def update_kind_yaml_file(self):
        """Method to update kind cluster yaml file with airgapped deployment"""
        em_yaml_str = f"""
        extraMounts:
            - containerPath: /etc/docker/certs.d/{self.harbor_url}
              hostPath: /etc/docker/certs.d/{self.harbor_url}
        """
        print(f"Updating {self.kind_yaml_file}...")
        em_dict = self.yaml.load(em_yaml_str)

        cd_config_str = f"""
                containerdConfigPatches:
                  - |-  
                    [plugins.\"io.containerd.grpc.v1.cri\".registry.configs.\"{self.harbor_url}\".tls]
                      cert_file = \"/etc/docker/certs.d/{self.harbor_url}/{self.harbor_url}.cert\"
                      key_file  = \"/etc/docker/certs.d/{self.harbor_url}/{self.harbor_url}.key\""""
        cd_dict = self.yaml.load(cd_config_str)

        kind_yaml = self.yaml.load(Path(self.kind_yaml_file))
        kind_yaml["nodes"][0].update(em_dict)
        kind_yaml.update(cd_dict)
        with open(self.kind_yaml_file, 'w') as fp:
            self.yaml.dump(kind_yaml, fp)
        return True

    def update_pipeline_template_files(self):
        """Method to update day0 pipeline template file"""
        tmplt_str = """
        podTemplate:
          dnsPolicy: \"None\"
          dnsConfig:
            nameservers:
              #@ for/end ns in data.values.nameservers:
              - \#@ ns
            searches:
              #@ for/end domain in data.values.searchdomains:
              - \#@ domain
            options:
              - name: ndots
                value: \"5\""""
        tmplt_dict = self.yaml.load(tmplt_str)
        for yaml_file in self.tmplt_yaml_files:
            print(f"Updating {yaml_file}...")
            tmple_yml = self.yaml.load(Path(yaml_file))
            tmple_yml["spec"].update(tmplt_dict)
            with open(yaml_file, 'w') as fp:
                fp.write("#@ load(\"@ytt:data\", \"data\")\n")
                fp.write("---\n")
                self.yaml.dump(tmple_yml, fp)

            with open(yaml_file, 'r') as f:
                content = f.read()
            content = re.sub(r"\\#@", "#@", content)

            with open(yaml_file, 'w') as fp:
                fp.write(content)
        return True

    def update_tasks_yaml_files(self):
        """Method to update tasks YAML file"""
        vol_mnt_str = f"""
             - mountPath: /certs/client
               name: dind-certs
             - mountPath: /etc/docker/certs.d/{self.harbor_url}
               name: docker-host
             """
        vol_mnt_dict = self.yaml.load(vol_mnt_str)

        vol_str = """
                     - name: dind-certs
                       emptyDir: {}"""
        vol_str = vol_str + f"""
                     - name: docker-host
                       hostPath:
                         path: /etc/docker/certs.d/{self.harbor_url}
                         type: Directory"""
        vol_dict = self.yaml.load(vol_str)
        for yaml_file in self.tasks_yaml_files:
            print(f"Updating {yaml_file}...")
            loaded_yml = self.yaml.load(Path(yaml_file))
            del loaded_yml["spec"]["steps"][0]["volumeMounts"]
            loaded_yml["spec"]["steps"][0]["volumeMounts"] = vol_mnt_dict

            del loaded_yml["spec"]["sidecars"][0]["volumeMounts"]
            loaded_yml["spec"]["sidecars"][0]["volumeMounts"] = vol_mnt_dict

            del loaded_yml["spec"]["volumes"]
            loaded_yml["spec"]["volumes"] = vol_dict
            with open(yaml_file, 'w') as fp:
                self.yaml.dump(loaded_yml, fp)
        return True

    def update_git_clone_yaml_file(self):
        """Method to update Git Yaml file for cloning in air gapped setup"""
        print(f"Updating {GIT_CLONE_YAML_FILE}...")
        with open(GIT_CLONE_YAML_FILE, "r") as fp:
            content = fp.read()

        content = re.sub("git clone", "git -c http.sslVerify=false clone", content)

        with open(GIT_CLONE_YAML_FILE, "w") as fp1:
            fp1.write(content)
        return True

    def update_git_commit_yaml_file(self):
        """Method to update Git Yaml file for committing in air gapped setup"""
        # Read harbor_url from values.yaml file
        print(f"Updating {GIT_COMMIT_YAML_FILE}...")
        with open(GIT_COMMIT_YAML_FILE, "r") as fp:
            content = fp.read()

        content = re.sub("git push", "git -c http.sslVerify=false push", content)

        with open(GIT_COMMIT_YAML_FILE, "w") as fp1:
            fp1.write(content)
        return True

    def update_tkn_release_yaml_files(self):
        """Method to update Tekton release YAML files"""
        for yaml_file in self.tkn_release_yaml_files:
            print(f"Updating {yaml_file}...")
            with open(yaml_file, 'r') as fp:
                content = fp.read()

            content = re.sub(self.default_harbor_url, self.harbor_url, content)

            with open(yaml_file, 'w') as fp1:
                fp1.write(content)
        return True

    def list_yaml_files_to_commit_in_git(self):
        """Method to list all updated YAML files need to be committed in git private repo"""
        print("Following Updated YAML Files need to be commit in GIT private repo")
        print(self.kind_yaml_file)
        for yaml_file in self.tmplt_yaml_files:
            print(yaml_file)
        for yaml_file in self.tasks_yaml_files:
            print(yaml_file)

if __name__ == "__main__":
    ag_yaml_obj = AirgappedYamlUpdate()
    ag_yaml_obj.update_all_yamls()
