# coding=UTF-8

# Tornado modules.
import tornado.web
import tornado.escape

# Import application modules.
from base import BaseHandler

# General modules.
import logging

class LoginHandler(BaseHandler):

    @tornado.web.asynchronous
    def post(self):
        try:
            user = dict()
            user["email"] = self.get_argument("email", default="")
            user["name"] = self.get_argument("name", default="")
        except:
            self.redirect("/login")

        self._on_auth(user)

    @tornado.web.asynchronous
    def get(self):
        self.render_default("login.html")

    def _on_auth(self, user):
        def on_user_find(result, user=user):
            if result == "null" or not result:
                self.application.client.set("user:" + user["email"], tornado.escape.json_encode(user))
            else:
                dbuser = tornado.escape.json_decode(result)
                dbuser.update(user)
                user = dbuser
                self.application.client.set("user:" + user["email"], tornado.escape.json_encode(user))

            self.set_secure_cookie("user", user["email"])
            self.set_secure_cookie("username", user["name"])
            self.application.usernames[user["email"]] = user.get("name") or user["email"]

            if self.request.connection.stream.closed():
                logging.warning("Waiter disappeared")
                return

            self.redirect("/")

        self.application.client.get("user:" + user["email"], on_user_find)

class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect("/")
