import os
from functools import wraps
from http import HTTPStatus

import jwt
from flask import current_app, request

from common.login_auth.users import Users
from common.util.request_api_util import RequestApiUtil


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if "x-access-tokens" in request.headers:
            token = request.headers["x-access-tokens"]

        if not token:
            response = RequestApiUtil.create_json_object(
                "A valid token is missing",
                response_type="ERROR",
                status_code=HTTPStatus.UNAUTHORIZED,
            )

            return response, 401
        try:
            data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = Users.query.filter_by(public_id=data["public_id"]).first()
            home_dir = os.path.join("/home", current_user.name)
            if not os.path.exists(home_dir):
                os.makedirs(home_dir)
            file = "current_user.txt"
            if not os.path.exists(file):
                with open(file, "w") as outfile:
                    outfile.write(current_user.name)
            else:
                with open(file, "r") as outfile:
                    data = outfile.read()
                if data != current_user.name:
                    with open(file, "w") as outfile:
                        outfile.write(current_user.name)
        except Exception:
            current_app.logger.error("Token is invalid")
            response = RequestApiUtil.create_json_object(
                "Token is invalid",
                response_type="ERROR",
                status_code=HTTPStatus.UNAUTHORIZED,
            )

            return response, HTTPStatus.UNAUTHORIZED

        return f(current_user, *args, **kwargs)

    return decorator
