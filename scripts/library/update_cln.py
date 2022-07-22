#!/usr/bin/env python3

from ansible.module_utils.basic import AnsibleModule
import sys
import subprocess
import os

def run_cmd(cmd, path=os.getcwd()):
    output = subprocess.Popen(
        "cd {}; {}".format(path, cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).communicate()[0]
    return output.decode('UTF-8')

def get_cln(project_name, branch):
    return run_cmd('git ls-remote git@gitlab.eng.vmware.com:core-build/{}.git {}'.format(project_name, branch)).split("\t")[0]

def main():
    module = AnsibleModule(
        argument_spec=dict(
            products=dict(type="dict", required=True),
            file_path=dict(type="str", required=True)
        )
    )
    result = dict(changed=False)

    for product in module.params['products']:
        sys.path.append("/".join(module.params['file_path'].split("/")[:-1]))
        spec = __import__(module.params['file_path'].split("/")[-1].split(".py")[0])
        spec_dict = {}
        exec('spec_dict["cln"] = spec.{}_CLN'.format(product.replace('-', '_').upper()))
        exec('spec_dict["branch"]  = spec.{}_BRANCH'.format(product.replace('-', '_').upper()))
        new_cln = get_cln(module.params['products'][product], spec_dict["branch"])
        if spec_dict["cln"] != new_cln:
            # Read in the file
            with open(module.params['file_path'], 'r') as file :
                filedata = file.read()
            # Replace the target string
            filedata = filedata.replace(spec_dict["cln"], new_cln)
            # Write the file out again
            with open(module.params['file_path'], 'w') as file:
                file.write(filedata)
            # run_cmd("sed -i 's/{}/{}/g' {}".format(spec_dict["cln"], new_cln, module.params['file_path']))
            result["changed"] = True
    module.exit_json(**result)


if __name__ == "__main__":
    main()
