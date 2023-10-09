# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import re
import subprocess
from subprocess import PIPE, STDOUT, Popen

from flask import current_app


def runShellCommandAndReturnOutput(fin):
    try:
        if isinstance(fin, str):
            fin = fin.split(" ")
        proc = subprocess.Popen(fin, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        output, err = proc.communicate()
        if err:
            returnCode = 1
        elif output.decode("utf-8").lower().__contains__("error"):
            returnCode = 1
        else:
            returnCode = 0
    except subprocess.CalledProcessError as e:
        returnCode = 1
        output = e.output
    return output.decode("utf-8").rstrip("\n\r"), returnCode


def runProcess(fin):
    if isinstance(fin, str):
        fin = fin.split(" ")
    p = Popen(fin, stdout=PIPE, stderr=STDOUT)
    stream = ""
    stream2 = ""
    for line in p.stdout:
        std = line.decode("utf-8").replace("\n", "")
        stream2 += std + "\n"
        current_app.logger.info(std)
        if std.strip(" ").startswith("Error"):
            stream += std + "\n"
            stream2 = stream
    out = p.poll()
    if out != 0:
        if out is not None:
            raise AssertionError("Failed " + str(stream2))


def runProcessTmcMgmt(fin):
    if isinstance(fin, str):
        fin = fin.split(" ")
    p = Popen(fin, stdout=PIPE, stderr=STDOUT)
    stream = ""
    stream2 = ""
    for line in p.stdout:
        std = line.decode("utf-8").replace("\n", "")
        stream2 += std + "\n"
        current_app.logger.info(std)
        if std.strip(" ").startswith("Error"):
            stream += std + "\n"
            stream2 = stream
    out = p.poll()
    if out != 0:
        if out is not None:
            return "FAIL"
    return "PASS"


def runShellCommandWithPolling(fin):
    try:
        proc = subprocess.Popen(fin)
        proc.wait()
        output = proc.poll()
        # current_app.logger.info(output)
        if output != 0:
            current_app.logger.error(output)
            raise AssertionError("Failed " + str(output))
    except subprocess.CalledProcessError as e:
        output = e.output
    return output


def runShellCommandAndReturnOutputAsList(fin):
    try:
        if isinstance(fin, str):
            fin = fin.split(" ")
        proc = subprocess.Popen(fin, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        output, err = proc.communicate()
        if err:
            returnCode = 1
        elif output.decode("utf-8").lower().__contains__("error"):
            returnCode = 1
        else:
            returnCode = 0
    except subprocess.CalledProcessError as e:
        returnCode = 1
        output = e.output
    return output.decode("utf-8").rstrip("\n\r").replace("\x1b[0m", "").replace("\x1b[1m", "").split("\n"), returnCode


def runShellCommandAndReturnOutputAsJson(fin):
    try:
        if isinstance(fin, str):
            fin = fin.split(" ")
        proc = subprocess.Popen(fin, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        output, err = proc.communicate()
        if err:
            returnCode = 1
        elif output.decode("utf-8").lower().__contains__("error"):
            returnCode = 1
        else:
            returnCode = 0
    except subprocess.CalledProcessError as e:
        returnCode = 1
        output = e.output
    return output.decode("utf-8"), returnCode


def runShellCommandAndReturnOutputAsListWithChangedDir(fin, dir):
    try:
        proc = subprocess.Popen(fin, cwd=dir, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        output, err = proc.communicate()
        if err:
            returnCode = 1
        elif output.decode("utf-8").lower().__contains__("error"):
            returnCode = 1
        else:
            returnCode = 0
    except subprocess.CalledProcessError as e:
        returnCode = 1
        output = e.output
    return output.decode("utf-8").rstrip("\n\r").replace("\x1b[0m", "").replace("\x1b[1m", "").split("\n"), returnCode


def grabPipeOutputChagedDir(listMainCommand, listOfPipeCommand, dir):
    try:
        ps = subprocess.Popen(listMainCommand, cwd=dir, stdout=subprocess.PIPE)
        output = subprocess.check_output(listOfPipeCommand, cwd=dir, stdin=ps.stdout)
        ps.wait()
        if output.decode("utf-8").lower().__contains__("error"):
            returnCode = 1
        else:
            returnCode = 0
    except subprocess.CalledProcessError as e:
        returnCode = 1
        output = e.output
    string = output.decode("utf-8").rstrip("\n\r").replace("\x1b[0m", "").replace("\x1b[1m", "").split("\n")
    return string, returnCode


def verifyPodsAreRunning(podName, listing, regex):
    try:
        if type(listing) is str:
            if str(listing).__contains__(podName) and str(listing).__contains__(regex):
                return True
        else:
            for i in listing:
                if str(i).__contains__(podName) and str(i).__contains__(regex):
                    return True
        return False
    except Exception:
        return False


def grabKubectlCommand(listOfCmd, regex):
    s = "'\"]"
    if isinstance(listOfCmd, str):
        listOfCmd = listOfCmd.split(" ")
    command = runShellCommandAndReturnOutputAsList(listOfCmd)
    if command[1] != 0:
        return None
    else:
        string = ""
        for s in command[0]:
            string += s
    return re.search(regex, string).group(1).replace(s, "")


def grabIpAddress(listMainCommand, lisofPipeCommand, regex):
    try:
        command = grabPipeOutput(listMainCommand, lisofPipeCommand)
        if command[1] == 1:
            return None
        else:
            string = command[0]
        return re.findall(regex, string)[1]
    except Exception:
        return None


def grabPipeOutput(listMainCommand, listOfPipeCommand):
    try:
        ps = subprocess.Popen(listMainCommand, stdout=subprocess.PIPE)
        output = subprocess.check_output(listOfPipeCommand, stdin=ps.stdout)
        ps.wait()
        if output.decode("utf-8").lower().__contains__("error"):
            returnCode = 1
        else:
            returnCode = 0
    except subprocess.CalledProcessError as e:
        returnCode = 1
        output = e.output
    string = output.decode("utf-8").rstrip("\n\r")
    return string, returnCode
