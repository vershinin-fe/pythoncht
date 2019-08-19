# coding=UTF-8

# General modules.
import os, os.path
import logging
import sys
from threading import Timer
import string
import random

# Tornado modules.
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.auth
import tornado.options
import tornado.escape
from tornado import gen

# Redis modules.
import brukva

# Import application modules.
from base import BaseHandler
from auth import LoginHandler
from auth import LogoutHandler

# Define port from command line parameter.
tornado.options.define("port", default=8888, help="defines port to listen", type=int)

class MainHandler(BaseHandler):
    """
    Main request handler
    """
    @tornado.web.asynchronous
    def get(self, room=None):
        if not room:
            self.redirect("/room/1")
            return

        self.room = str(room)
        self._get_current_user(callback=self.on_auth)


    def on_auth(self, user):
        if not user:
            self.redirect("/login")
            return

        self.application.client.lrange(self.room, -50, -1, self.on_conversation_found)


    def on_conversation_found(self, result):
        if isinstance(result, Exception):
            raise tornado.web.HTTPError(500)

        messages = []
        for message in result:
            messages.append(tornado.escape.json_decode(message))

        content = self.render_string("messages.html", messages=messages)
        self.render_default("index.html", content=content, chat=1)



class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    """
    WebSocket Handler
    """
    @gen.engine
    def open(self, room='root'):
        if not room:
            self.write_message({'error': 1, 'textStatus': 'Error: No room specified'})
            self.close()
            return
        self.room = str(room)
        self.new_message_send = False
        self.client = redis_connect()
        self.client.subscribe(self.room)
        self.subscribed = True
        self.client.listen(self.on_messages_published)
        logging.info('New user connected to chat room ' + room)

    def on_messages_published(self, message):
        """
        Callback for Redis subscription
        """
        m = tornado.escape.json_decode(message.body)
        self.write_message(dict(messages=[m]))

    def on_message(self, data):
        """
        Receiving message via WebSocket
        """
        logging.info('Received new message %r', data)
        try:
            datadecoded = tornado.escape.json_decode(data)
            message = {
                '_id': ''.join(random.choice(string.ascii_uppercase) for i in range(12)),
                'from': self.get_secure_cookie('username'),
                'body': tornado.escape.linkify(datadecoded["body"]),
            }
            if not message['from']:
                logging.warning("Error: Authentication missing")
                message['from'] = 'Guest'
        except Exception, err:
            self.write_message({'error': 1, 'textStatus': 'Bad input data ... ' + str(err) + data})
            return

        try:
            message_encoded = tornado.escape.json_encode(message)
            self.application.client.rpush(self.room, message_encoded)
            self.application.client.publish(self.room, message_encoded)
        except Exception, err:
            e = str(sys.exc_info()[0])
            self.write_message({'error': 1, 'textStatus': 'Error writing to database: ' + str(err)})
            return

        self.write_message(message)
        return


    def on_close(self):
        logging.info("socket closed, cleaning up resources now")
        if hasattr(self, 'client'):
            if self.subscribed:
                self.client.unsubscribe(self.room)
                self.subscribed = False
            # https://github.com/evilkost/brukva/issues/25
            t = Timer(0.1, self.client.disconnect)
            t.start()

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/room/([a-zA-Z0-9]*)$", MainHandler),
            (r"/login", LoginHandler),
            (r"/logout", LogoutHandler),
            (r"/socket", ChatSocketHandler),
            (r"/socket/([a-zA-Z0-9]*)$", ChatSocketHandler)
        ]

        settings = dict(
            cookie_secret = "43osdETzKXasdQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url = "/login",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies= True,
            autoescape="xhtml_escape",
            db_name = 'chat',
            apptitle = 'Python Websocket Chat',
        )

        tornado.web.Application.__init__(self, handlers, **settings)
        self.usernames = {}
        self.client = redis_connect()


def redis_connect():
    """
    Redis connection
    """
    herokuredis_url = os.getenv('HEROKUREDIS_URL', None)
    if herokuredis_url == None:
        REDIS_HOST = 'localhost'
        REDIS_PORT = 6379
        REDIS_PWD = None
        REDIS_USER = None
    else:
        redis_url = herokuredis_url
        redis_url = redis_url.split('redis://')[1]
        redis_url = redis_url.split('/')[0]
        REDIS_USER, redis_url = redis_url.split(':', 1)
        REDIS_PWD, redis_url = redis_url.split('@', 1)
        REDIS_HOST, REDIS_PORT = redis_url.split(':', 1)
    client = brukva.Client(host=REDIS_HOST, port=int(REDIS_PORT), password=REDIS_PWD)
    client.connect()
    return client



def main():
    tornado.options.parse_command_line()
    application = Application()
    application.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
