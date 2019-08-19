# coding=UTF-8

# Tornado modules.
import tornado.web

# General modules.
import logging


class BaseHandler(tornado.web.RequestHandler):

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)

    def _get_current_user(self, callback):
        user_id = self.get_secure_cookie("user")
        if not user_id:
            logging.warning("Cookie not found")
            callback(user=None)
            return

        def query_callback(result):
            if result == "null" or not result:
                logging.warning("User not found")
                user = {}
            else:
                user = tornado.escape.json_decode(result)
            self._current_user = user
            callback(user=user)

        self.application.client.get("user:" + user_id, query_callback)
        return


    def render_default(self, template_name, **kwargs):
        if not hasattr(self, '_current_user'):
            self._current_user = None
        kwargs['user'] = self._current_user
        kwargs['path'] = self.request.path;
        if hasattr(self, 'room'):
            kwargs['room'] = int(self.room)
        else: kwargs['room'] = None
        kwargs['apptitle'] = self.application.settings['apptitle']

        if not self.request.connection.stream.closed():
            try:
                self.render(template_name, **kwargs)
            except: pass
