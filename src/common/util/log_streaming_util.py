import subprocess

from flask import Blueprint, Response, current_app, send_file

from common.login_auth.authentication import token_required
from common.operation.constants import Paths

log_stream = Blueprint("log_stream", __name__, static_folder="log_stream")


def flask_logger():
    last_100_logs = subprocess.Popen(
        ["tail", "-10", Paths.SIVT_LOG_FILE], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    output1, err = last_100_logs.communicate()
    output1 = output1.decode("utf-8")
    """creates logging information"""
    pro = subprocess.Popen(["tail", "-n0", "-f", Paths.SIVT_LOG_FILE], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # pro can be none
    while True:
        yield output1
        line = pro.stdout.readline()
        if (pro.poll() is not None) or (len(line) == 0):
            pro.kill()
            break
        output = line.strip()
        output1 = output.decode("utf-8")


@log_stream.route("/api/tanzu/streamLogs", methods=["GET"])
@token_required
def stream(current_user):
    """returns logging information"""
    return Response(flask_logger(), mimetype="text/event-stream")


@log_stream.route("/api/tanzu/downloadLogs", methods=["GET"])
@token_required
def download_log_bundle(current_user):
    path = Paths.SIVT_LOG_FILE
    current_app.logger.info(f"*************Downloading log files {path}************")
    return send_file(path, as_attachment=True)
