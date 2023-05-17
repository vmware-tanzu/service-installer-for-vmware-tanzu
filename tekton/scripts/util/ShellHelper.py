#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import subprocess
import re
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
from util.logger_helper import LoggerHelper, log
from pathlib import Path

logger = LoggerHelper.get_logger(Path(__file__).stem)

def runShellCommandAndReturnOutput(fin):
    try:
        logger.debug(f"Command to execute: \n\"{' '.join(fin)}\"")
        proc = subprocess.Popen(
            fin,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE
        )
        output, err = proc.communicate()
        formatted_output = output.decode("utf-8").rstrip("\n\r").replace("\x1b[0m", "").replace("\x1b[1m", "")
        if err:
            returnCode = 1
        elif formatted_output.__contains__("error"):
            returnCode = 1
        else:
            returnCode = 0
        logger.debug(f"Output: \n {'*' * 10}Output Start{'*' * 10}\n{formatted_output}\n{'*' * 10}Output End{'*' * 10}")

    except subprocess.CalledProcessError as e:
        returnCode = 1
        formatted_output = e.output
    return formatted_output.rstrip("\n\r"), returnCode

def runProcess(fin):
    logger.info(f"Running command:\n\"{' '.join(fin)}\"")
    p = Popen(fin, stdout=PIPE,
              stderr=STDOUT)
    stream = ""
    stream2 = ""
    for line in p.stdout:
        std = line.decode("utf-8").replace("\n", "")
        stream2 += std+"\n"
        logger.info(std)
        if std.strip(" ").startswith("Error"):
            stream += std+"\n"
            stream2 = stream
    out = p.poll()
    if out != 0:
        if out is not None:
            raise AssertionError("Failed " + str(stream2))

def runShellCommandWithPolling(fin):
    try:
        proc = subprocess.Popen(
            fin
        )
        proc.wait()
        output = proc.poll()
        if output != 0:
            raise AssertionError("Failed " + str(output))
    except subprocess.CalledProcessError as e:
        returnCode = 1
        output = e.output
    return output


def runShellCommandAndReturnOutputAsList(fin):
    try:
        logger.debug(f"Command to execute: \n\"{' '.join(fin)}\"")
        proc = subprocess.Popen(
            fin,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE
        )

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
    formatted_output = output.decode("utf-8").rstrip("\n\r").replace("\x1b[0m", "").replace("\x1b[1m", "")
    logger.debug(f"Output Received: \n {'*'*10}Output Start{'*'*10}\n{formatted_output}\n{'*'*10}Output End{'*'*10}")
    return formatted_output.split("\n"), returnCode


def runShellCommandAndReturnOutputAsListWithChangedDir(fin, ndir):
    try:
        proc = subprocess.Popen(
            fin, cwd=ndir,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE
        )
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


def grabPipeOutputChagedDir(listMainCommand, listOfPipeCommand, ndir):
    try:
        ps = subprocess.Popen(listMainCommand, cwd=ndir, stdout=subprocess.PIPE)
        output = subprocess.check_output(listOfPipeCommand, cwd=ndir, stdin=ps.stdout)
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
    except:
        return False


def grabKubectlCommand(listOfCmd, regex):
    s = "'\"]"
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
    except:
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


def runProcessTmcMgmt(fin):
    p = Popen(fin, stdout=PIPE,
              stderr=STDOUT)
    stream = ""
    stream2 = ""
    for line in p.stdout:
        std = line.decode("utf-8").replace("\n", "")
        stream2 += std+"\n"
        logger.info(std)
        if std.strip(" ").startswith("Error"):
            stream += std+"\n"
            stream2 = stream
    out = p.poll()
    if out != 0:
        if out is not None:
            return "FAIL"
    return "PASS"
