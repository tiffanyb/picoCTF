"""
Flask routing
"""

from flask import Flask, request, session, send_from_directory, render_template
from werkzeug.contrib.fixers import ProxyFix
from flask_mail import Mail


import api
import json
import mimetypes
import os.path

from datetime import datetime
from api.common import WebSuccess, WebError
from api.annotations import api_wrapper, require_login, require_teacher, require_admin, check_csrf
from api.annotations import block_before_competition, block_after_competition
from api.annotations import log_action

import api.routes.user
import api.routes.team
import api.routes.stats
import api.routes.admin
import api.routes.group
import api.routes.problem
import api.routes.achievements


app = Flask(__name__, static_path="/")
app.wsgi_app = ProxyFix(app.wsgi_app)

# Loads default_settings
app.config.from_pyfile('default_settings.py')

# Override defaults with settings file passed in the environment variable
# Ensure if you using a custom configuration that you have this set for all
# uses of the api, including things like picoCTF-platform/scripts/load_problems.py
app.config.from_envvar('APP_SETTINGS_FILE', silent=True)

log = api.logger.use(__name__)

def config_app(*args, **kwargs):
    """
    Return the app object configured correctly.
    This needed to be done for gunicorn.
    """

    settings = api.config.get_settings()

    if settings["email"]["enable_email"]:
        app.config["MAIL_SERVER"] = settings["email"]["smtp_url"]
        app.config["MAIL_PORT"] = settings["email"]["smtp_port"]
        app.config["MAIL_USERNAME"] = settings["email"]["email_username"]
        app.config["MAIL_PASSWORD"] = settings["email"]["email_password"]
        app.config["MAIL_DEFAULT_SENDER"] = settings["email"]["from_addr"]
        app.config["MAIL_USE_TLS"] = settings["email"]["smtp_security"] == "TLS"
        app.config["MAIL_USE_SSL"] = settings["email"]["smtp_security"] == "SSL"

        api.email.mail = Mail(app)

    app.register_blueprint(api.routes.user.blueprint, url_prefix="/api/user")
    app.register_blueprint(api.routes.team.blueprint, url_prefix="/api/team")
    app.register_blueprint(api.routes.stats.blueprint, url_prefix="/api/stats")
    app.register_blueprint(api.routes.admin.blueprint, url_prefix="/api/admin")
    app.register_blueprint(api.routes.group.blueprint, url_prefix="/api/group")
    app.register_blueprint(api.routes.problem.blueprint, url_prefix="/api/problems")
    app.register_blueprint(api.routes.achievements.blueprint, url_prefix="/api/achievements")

    api.logger.setup_logs({"verbose": 2})
    return app

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, *')
    response.headers.add('Cache-Control', 'no-cache')
    response.headers.add('Cache-Control', 'no-store')
    if api.auth.is_logged_in():
        if 'token' in session:
            response.set_cookie('token', session['token'])
        else:
            csrf_token = api.common.token()
            session['token'] = csrf_token
            response.set_cookie('token', csrf_token)

    # JB: This is a hack. We need a better solution
    if request.path[0:19] != "/api/autogen/serve/":
        response.mimetype = 'appication/json'
    return response

@app.route('/api/time', methods=['GET'])
@api_wrapper
def get_time():
    return WebSuccess(data=int(datetime.utcnow().timestamp()))
