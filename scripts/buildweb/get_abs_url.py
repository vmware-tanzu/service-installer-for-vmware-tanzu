#!/usr/bin/env python3
import subprocess
import sys
import os
import json


def run_cmd(cmd, path=os.getcwd()):
    # print("running cmd : {}".format(cmd))
    # return subprocess.run(cmd.split(" "), cwd=path, check=True, capture_output=True)
    output = subprocess.Popen(
        "cd {}; {}".format(path, cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).communicate()[0]
    # print("output : {}".format(output))
    return output.decode("UTF-8")


if __name__ == "__main__":
    product_name = sys.argv[1]
    json_file = sys.argv[2]
    file_ext = "ova"
    try:
        if sys.argv[3]:
            file_ext = sys.argv[3]
    except:
        file_ext = "ova"

    with open(json_file, "r") as f:
        build_dict = json.load(f)

    url_prefix = build_dict["deliverable_urls"][product_name]
    print(
        "{}/{}".format(
            url_prefix, run_cmd("curl -s " + url_prefix + "| grep " + file_ext + "| sed 's/<\/.*//g' | sed 's/.*>//g'")
        )
    )
    # +"' | grep "+file_ext+" | sed 's/<\/.*//g' | sed 's/.*>//g"
