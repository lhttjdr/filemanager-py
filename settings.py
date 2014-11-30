#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
FileName: settings.py
Author：lhttjdr@gmail.com
Create date: 19, Sept. 2014
Description：the settings of the demo
'''
import os.path
BASE_PATH = os.path.dirname(__file__).rstrip(os.sep)+'/'
FILE_MANAGER_PATH = os.path.join(BASE_PATH, "static/filemanager/")
TEMPLATE_PATH = os.path.join(BASE_PATH, "template")
TEMPLATE_URL = r"/template/(.*)"
STATIC_PATH = os.path.join(BASE_PATH, "static")
