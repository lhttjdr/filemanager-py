#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
FileName: demo.py
Author：lhttjdr@gmail.com
Create date: 19, Sept. 2014
Description：It's a simple tornado server for demostration.
'''
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import settings
from tornado.web import MissingArgumentError

from filemanager import BrowserHandler

class DefaultHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")
            
def main():
    #tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r"/", DefaultHandler),
        (r"/browser/?", BrowserHandler),
        (settings.TEMPLATE_URL, tornado.web.StaticFileHandler, dict(path = settings.TEMPLATE_PATH))
    ], static_path=settings.STATIC_PATH, template_path=settings.TEMPLATE_PATH)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.bind(80, "0.0.0.0")
    http_server.start()
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()