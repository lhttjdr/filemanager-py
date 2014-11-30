FileManager-in-Python
=====================

A python version of FileManager, and a demo of it on tornado

You can find the original version of FileManager at the following page:
https://github.com/simogeo/Filemanager

It is designed for several languages such like php, asp, perl etc., but unfortunately, I need a python one. According to its **Preamble** in **Installation and Setup** section, only PHP and MVC connectors are now up-to-date. So I convert the php connector to a python one.


Because php is a dynamic server-side scripting language, it contains a set of uniform operations for web development. When it comes to python, each kind of server or framework, like django,tornado,flask etc. may have its own implement. To solve this problem, I split the connector into two parts, one of which has nothings to do with web server.


Compared with the php version, my project have several differences, because the class FileManager are supposed to do nothing about web server. So, in the initialization, some additional parameters need be passed in.


By the way, some path in the JavaScript file should not be hard coded, I think. Now, I just modify them to work well with my demo project. Maybe they need a flexible and elegant design.
