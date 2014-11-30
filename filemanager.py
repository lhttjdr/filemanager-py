#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
FileName: filemanager.py
Author：lhttjdr@gmail.com
Create date: 19, Sept. 2014
Description：the core operations of web interactions
'''
import tornado.web
import settings
from tornado.web import MissingArgumentError

from logic import *

class BrowserHandler(tornado.web.RequestHandler):
    
    filemanager=Filemanager({
        "server_root":settings.BASE_PATH.replace(os.path.sep,'/'),
        "filemanager_root":settings.FILE_MANAGER_PATH.replace(os.path.sep,'/')
    })
    
    def getvar(self, var, preserve = None):
        fm=self.__class__.filemanager
        try:
            arg=self.get_query_argument(var)
            if arg:
                fm.get[var] = fm.sanitize(arg, preserve)
                return True
            else:
                fm.error(fm.lang('INVALID_VAR') % var)
                return False
        except MissingArgumentError:
            fm.error(fm.lang('INVALID_VAR') % var)
            return False

    def postvar(self, var, sanitize = True):
        fm=self.__class__.filemanager
        try:
            arg=self.get_body_argument(var)
            if not arg or (var != 'content' and arg==''):
                fm.error(fm.lang('INVALID_VAR') % var)
                return False
            else:
                if(sanitize):
                    fm.post[var] = fm.sanitize(arg)
                else:
                    fm.post[var] = arg
                return True
        except MissingArgumentError:
            fm.error(fm.lang('INVALID_VAR') % var)
            return False

    def get(self):
        fm=self.__class__.filemanager
        fm.setParams(self.request.full_url())
        fm.user_ip=self.request.remote_ip
        try:
            mode=self.get_query_argument('mode')
            if mode:
                if mode=="getinfo": #done
                    if self.getvar('path'):
                        self.write(json.dumps(fm.getinfo()))
                elif mode=="getfolder":  #need fix
                    if self.getvar('path'):
                        self.write(json.dumps(fm.getfolder()))
                elif mode=="rename":
                    if self.getvar('old') and self.getvar('new'):
                        self.write(json.dumps(fm.rename()))
                elif mode=="move":
                    # allow "../"
                    if self.getvar('old') and self.getvar('new', 'parent_dir') and self.getvar('root'):
                        self.write(json.dumps(fm.move()))
                elif mode=="editfile": #done
                    if self.getvar('path'):
                        self.write(json.dumps(fm.editfile()))
                elif mode=='delete': #done
                    if self.getvar('path'):
                        self.write(json.dumps(fm.delete()))
                elif mode=="addfolder":
                    if self.getvar('path') and self.getvar('name'):
                        self.write(json.dumps(fm.addfolder()))
                elif mode=="download": #done
                    if self.getvar('path'):
                        file_name=fm.download()
                        if not isinstance(file_name,str):
                            self.write(json.dumps(file_name))
                        else:
                            buf_size = 4096
                            self.set_header('Content-Type','application/octet-stream')
                            self.set_header("Content-Transfer-Encoding","Binary");
                            self.set_header("Content-length",os.path.getsize(file_name))
                            self.set_header('Content-Disposition','attachment; filename="'+ os.path.split(file_name)[-1] + '"')
                            with open(file_name, 'rb') as f:
                                while True:
                                    data = f.read(buf_size)
                                    if not data:
                                        break
                                    self.write(data)
                            self.finish()
                elif mode=="preview": #done
                    if self.getvar('path'):
                        try:
                            self.get_query_argument('thumbnail')
                            thumbnail = True
                        except MissingArgumentError:
                            thumbnail = False
                        finally:
                            file_name = fm.preview(thumbnail)
                            if not isinstance(file_name,str):
                                self.write(json.dumps(file_name))
                            else:
                                buf_size = 4096
                                self.set_header('Content-Type', 'image/'+(os.path.splitext(file_name)[-1]).lstrip('.').lower())
                                self.set_header("Content-Transfer-Encoding","Binary")
                                self.set_header("Content-length",os.path.getsize(file_name))
                                self.set_header('Content-Disposition','inline; filename="' + os.path.split(file_name)[-1] + '"')
                                with open(file_name, 'rb') as f:
                                    while True:
                                        data = f.read(buf_size)
                                        if not data:
                                            break
                                        self.write(data)
                                self.finish()
                elif mode=="maxuploadfilesize":
                    fm.getMaxUploadFileSize()
                else:
                    self.write(json.dumps(fm.error(fm.lang('MODE_ERROR'))))
        except MissingArgumentError:
            fm.loadLanguageFile()
            self.render("filemanager.html")

    def post(self):
        fm=self.__class__.filemanager
        fm.setParams(self.request.full_url())
        fm.user_ip=self.request.remote_ip
        try:
            mode=self.get_body_argument('mode')
            if mode:
                if mode=="add":
                    if self.postvar('currentpath'):
                        self.write('<textarea>'+json.dumps(fm.add(self.request.files))+'</textarea>')
                elif mode=="replace":
                    if self.postvar('newfilepath'):
                        self.write('<textarea>'+json.dumps(fm.replace(self.request.files))+'</textarea>')
                elif mode=="savefile":
                    if self.postvar('content', False) and self.postvar('path'):
                        self.write(json.dumps(fm.savefile()))
                else:
                    self.write(json.dumps(fm.error(fm.lang('MODE_ERROR'))))
        except MissingArgumentError:
            self.write(json.dumps(fm.error(fm.lang('INVALID_ACTION'))))
