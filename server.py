#! /usr/bin/env python

import json
import signal
from socket import error

import rospy
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, StaticFileHandler
from tornado.websocket import WebSocketHandler

from backendbase import BackendBase
from rosbackend import RosBackend


class ChallengeHandler(RequestHandler):
    def get(self):
        print "Rendering..."
        self.render("challenge.html",
                    visualization="Robot camera image"
                    )


class CommandReceiver(RequestHandler):
    def initialize(self, backend):
        self.backend = backend

    def post(self, *args, **kwargs):
        command = self.get_argument("command")
        self.backend.accept_command(command)
        print(command)


class MessageForwarder(WebSocketHandler):

    def __init__(self, *args, **kwargs):
        self.backend = kwargs.pop('backend')
        super(MessageForwarder, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        print("opening WebSocket")
        self.backend.attach_operator_text(self.handle_operator_text)
        self.backend.attach_robot_text(self.handle_robot_text)
        self.backend.attach_challenge_step(self.handle_challenge_step)
        self.backend.attach_image(self.handle_image)
        self.backend.attach_story(self.handle_story)

        print("WebSocket opened")

    def on_message(self, message):
        self.write_message(u"You said: " + message)

    def on_close(self):
        print("WebSocket closed")
        self.backend.detach_operator_text(self.handle_operator_text)
        self.backend.detach_robot_text(self.handle_robot_text)
        self.backend.detach_challenge_step(self.handle_challenge_step)
        self.backend.detach_image(self.handle_image)
        self.backend.detach_story(self.handle_story)

    def handle_operator_text(self, text):
        print "handle_operator_text({})".format(text)

        data = {"label": "operator_text", "text": text}
        data = json.dumps(data)

        self.write_message(data)

    def handle_robot_text(self, text):
        print "handle_robot_text({})".format(text)

        data = {"label": "robot_text", "text": text}
        data = json.dumps(data)

        self.write_message(data)

    def handle_challenge_step(self, step):
        print "handle_challenge_step({})".format(step)

        data = {"label": "challenge_step", "index": step}
        data = json.dumps(data)

        self.write_message(data)

    def handle_image(self, image):
        print "handle_image({})".format(len(image))

        data = {"label": "image", "image": image}
        data = json.dumps(data)

        self.write_message(data)

    def handle_story(self, title_storyline):
        print "handle_story({})".format(title_storyline)

        title, storyline = title_storyline

        data = {"label": "story", "title": title, "storyline": storyline}
        data = json.dumps(data)

        self.write_message(data)


def handle_shutdown(*arg, **kwargs):
    IOLoop.instance().stop()

if __name__ == "__main__":
    backend = RosBackend.get_instance(shutdown_hook=handle_shutdown)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGQUIT, handle_shutdown) # SIGQUIT is send by our supervisord to stop this server.
    signal.signal(signal.SIGTERM, handle_shutdown) # SIGTERM is send by Ctrl+C or supervisord's default.
    print "Shutdown handler connected"

    app = Application([
        (r"/ws", MessageForwarder, {'backend': backend}),
        (r'/', ChallengeHandler),
        (r'/command', CommandReceiver, {'backend': backend}),
        (r'/static/(.*)', StaticFileHandler, {'path': 'static/'})],
        (r'/(favicon\.ico)', StaticFileHandler, {'path': 'static/favicon.ico'}),
    debug=True,
    template_path="templates")

    address, port = "0.0.0.0", 8888
    print "Application instantiated"

    connected = False
    while not connected and not rospy.is_shutdown():
        try:
            print "Listening..."
            app.listen(port, address)
            rospy.logdebug("Listening on {addr}:{port}".format(addr=address, port=port))
            connected = True
        except error as ex:
            rospy.logerr("{ex}. Cannot start, trying in a bit".format(ex=ex))
            rospy.sleep(1)

    print "Starting IOLoop"
    IOLoop.instance().start()
