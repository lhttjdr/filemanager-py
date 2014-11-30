#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
FileName: logic.py
Author：lhttjdr@gmail.com
Create date: 19, Sept. 2014
Description：the core operations of directory and file, without any web interactions
'''
import json
import os, time
import operator
import re
import copy

from utils import html_to_text
from utils import htmlspecialchars,htmlspecialchars_decode

try:
    from PIL import Image
except:
    raise EnvironmentError('Must have the PIL (Python Imaging Library).')

import inspect
def get_current_function_name():
    return inspect.stack()[1][3]

import urllib
def urlencode(url):
    return urllib.parse.quote(url)

def urldecode(url):
    return urllib.parse.unquote(url)
    
# NOTICE: This class must has nothing to do with the web server
# Thus, the information of server and the parameters of get/post method
# must be passed in, and the respond to http request should be relegated to invoker 
class Filemanager():
    
    ### all configuration
    config = {} #configuration of filemanager
    
    ### language
    language = {}   #translation of messages
    languages = []  # list of available languages
    
    ### param
    get = {}    # parameters of get method
    post = {}   # parameters of post method
    params = {} # query string
    
    ### file or directory detail information
    properties = {}
    item = {}   
    
    ### privilege configuration
    allowed_actions = {}    # privilege control
    
    ### path information
    filemanager_root = ''   # the path file manager installed
    server_root = '' # the full path of web root
    doc_root = ''   # the full path of root directory to browser
    file_root = ''  # the relative path of root directory to browser
    separator = 'userfiles'     # under which directory exists the cache folder
                                # actually it's the basename of file root
    ### log
    logger = False  # whether the function of log is enabled
    logfile = '/log/filemanager.log'    # the default path for log
    user_ip = ''
    
    # thumbnail configuration
    cachefolder = '_thumbs/'    #the default name of directory for thumbnails
    thumbnail_width = 64    #the default size of thumbnails
    thumbnail_height = 64
    
    def __init__(self,serverConfig):
        if "filemanager_root" in serverConfig:
            self.filemanager_root=serverConfig["filemanager_root"]
        else:
            return self.error("The root of FileManger is not configured.")
        if "server_root" in serverConfig:
            self.server_root=serverConfig["server_root"]
        with open(self.filemanager_root + "scripts/filemanager.config.js.default",encoding="utf-8") as f:
            config_default = json.load(f)
        with open(self.filemanager_root + "scripts/filemanager.config.js",encoding="utf-8") as f:
            config = json.load(f)
        self.config = copy.deepcopy(config_default)
        self.config.update(config)
        if self.config['options']['fileRoot']:
            self.file_root = self.config['options']['fileRoot']
            if self.config['options']['serverRoot']:
                self.doc_root = self.server_root
            else:
                self.doc_root = self.server_root + self.file_root.lstrip('/')
        else:
            self.file_root = ''
            self.doc_root = self.server_root
        self.separator = os.path.split(self.doc_root.rstrip('/'))[-1]
        # this is a template
        self.properties = {
                'Date Created': None,
                'Date Modified': None,
                'Height': None,
                'Width': None,
                'Size': None
        }
        # Log actions or not?
        if 'logger' in self.config['options'] and self.config['options']['logger']:
            if 'logfile' in self.config['options']:
                self.logfile = self.config['options']['logfile']
            self.enableLog()
            
        self.__log(get_current_function_name() + ' self.doc_root value ' + self.doc_root)
        self.__log(get_current_function_name() + ' self.separator value ' + self.separator)

        self.setParams()
        self.setPermissions()
        self.availableLanguages()
        self.loadLanguageFile()
        
    def error(self, string):
        self.__log( get_current_function_name() + ' - error message : ' + string)
        return {
            'Error':string,
            'Code':'-1',
            'Properties':self.properties
        }


    def lang(self, string):
        if string in self.language and self.language[string]!='':
            return self.language[string]
        else:
            return 'Language string error on ' + string

    # get
    def getinfo(self):
        # initalize the self.item
        self.item = {}
        self.item['properties'] = copy.deepcopy(self.properties)
        # get detail information, fill into self.item
        self.get_file_info('', False)
        path = self.get['path']
        return {
                'Path':path,
                'Filename':self.item['filename'],
                'File Type':self.item['filetype'],
                'Preview':self.item['preview'],
                'Properties':self.item['properties'],
                'Error':"",
                'Code':0
        }
        
    # get the information of folder
    def getfolder(self):
        array = {} # the list to be returned
        filesDir = [] # the flies and directories under current path
        current_path = self.getFullPath() # change to full path
        if not self.isValidPath(current_path): # check whether current path is under the root
            return self.error("No way.")
        if not os.path.isdir(current_path): # check whether current path already exists
            return self.error(self.lang('DIRECTORY_NOT_EXIST') % self.get['path'])
        try:
            filesDir=os.listdir(current_path)
        except os.error:
            return self.error(self.lang('UNABLE_TO_OPEN_DIRECTORY') % self.get['path'])
        # By default: Sorting files by name ('default' or 'NAME_DESC' cases from self.config['options']['fileSorting']
        auxiliary_list = [(x.lower(), x) for x in filesDir]
        auxiliary_list.sort()
        filesDir[:]=[x[1] for x in auxiliary_list]
        
        for file in filesDir:
            # if a directory
            if os.path.isdir(current_path + file):
                if file not in self.config['exclude']['unallowed_dirs'] and not re.match(self.config['exclude']['unallowed_dirs_REGEXP'], file):
                    dirPath=self.get['path'] + file +'/'
                    fullDirPath=self.getFullPath(self.get['path'] + file +'/')
                    fileStat=os.stat(fullDirPath)
                    array[dirPath] = {
                            'Path':  self.get['path'] + file +'/',
                            'Filename': file,
                            'File Type': 'dir',
                            'Preview':  self.config['icons']['path'] + self.config['icons']['directory'],
                            'Properties': {
                                    'Date Created':  time.strftime(self.config['options']['dateFormat'], time.localtime(fileStat.st_ctime)),
                                    'Date Modified':  time.strftime(self.config['options']['dateFormat'], time.localtime(fileStat.st_mtime)),
                                    'filemtime':  fileStat.st_mtime,
                                    'Height': None,
                                    'Width': None,
                                    'Size': None
                            },
                            'Error': "",
                            'Code': 0
                        }
            elif (file not in self.config['exclude']['unallowed_files']) and (None == re.match(self.config['exclude']['unallowed_files_REGEXP'], file)):
                self.item = {}
                self.item['properties'] = copy.deepcopy(self.properties)
                self.get_file_info(self.get['path'] + file, True)
                if 'type' not in self.params or ('type' in self.params and self.params['type'].lower()=='images' and self.item['filetype'].lower() in map(lambda x: x.lower(), self.config['images']['imagesExt'])):
                    if self.config['upload']['imagesOnly']== False or (self.config['upload']['imagesOnly']== True and self.item['filetype'].lower() in map(lambda x: x.lower(), self.config['images']['imagesExt'])):
                        array[self.get['path'] + file] = {
                                'Path': self.get['path'] + file,
                                'Filename': self.item['filename'],
                                'File Type': self.item['filetype'],
                                'Preview': self.item['preview'],
                                'Properties': self.item['properties'],
                                'Error': "",
                                'Code': 0
                            }
        return self.sortFiles(array)

        
    # get file content
    def editfile(self):
        current_path = self.getFullPath()
        if not self.has_permission('edit') or not self.isValidPath(current_path) or not self.isEditable(current_path):
            return self.error("No way.")
        self.__log(get_current_function_name() + ' - editing file '+ current_path)
        file = open(current_path,'r')
        try:
            content = file.read()
            content = htmlspecialchars(content)
            return {
                'Error': "",
                'Code': 0,
                'Path': self.get['path'],
                'Content': content
            }
        except Exception:
            return self.error(self.lang('ERROR_OPENING_FILE'))
        finally:
            file.close()
    # save content to file
    def savefile(self):
        current_path = self.getFullPath(self.post['path'])
        if not self.has_permission('edit') or not self.isValidPath(current_path) or not self.isEditable(current_path):
            return self.error("No way.")
        if not os.access(current_path,os.W_OK):
            self.error(self.lang('ERROR_WRITING_PERM'))
        self.__log(get_current_function_name() + ' - saving file '+ current_path)
        content =  htmlspecialchars_decode(self.post['content'])
        try:
            f=open(current_path,'w+',newline='\n')
            f.write(content)
            return{
                'Error': "",
                'Code': 0,
                'Path': self.formatPath(self.post['path'])
            }
        except:
            self.error(self.lang('ERROR_SAVING_FILE'))
        finally:
            f.close()
        

    def rename(self):
        suffix=''
        if self.get['old'][-1]=='/':
            self.get['old'] = self.get['old'][0:-1]
            suffix='/'
        tmp = self.get['old'].split('/')
        filename = tmp[-1]
        path = self.get['old'].replace('/' + filename,'')
        new_file = self.getFullPath(path + '/' + self.get['new'])+ suffix
        old_file = self.getFullPath(self.get['old']) + suffix
        if not self.has_permission('rename') or not self.isValidPath(old_file):
            return self.error("No way.")
        # For file only - we check if the new given extension is allowed regarding the security Policy settings
        if os.path.isfile(old_file) and self.config['security']['allowChangeExtensions'] and  not self.isAllowedFileType(new_file):
            return self.error(self.lang('INVALID_FILE_TYPE'))
        self.__log(get_current_function_name() + ' - renaming '+ old_file+ ' to ' + new_file)
        if os.path.exists(new_file):
            if suffix=='/' and os.path.isdir(new_file):
                return self.error(self.lang('DIRECTORY_ALREADY_EXISTS') % self.get['new'])
            if suffix=='' and os.path.isfile(new_file):
                return self.error(self.lang('FILE_ALREADY_EXISTS') % self.get['new'])
        try:
            os.rename(old_file,new_file)
        except os.error:
            if os.path.isdir(old_file):
                self.error(self.lang('ERROR_RENAMING_DIRECTORY') % filename,self.get['new'])
            else:
                self.error(self.lang('ERROR_RENAMING_FILE') % filename,self.get['new'])
        return{
                'Error': "",
                'Code': 0,
                'Old Path': self.get['old'],
                'Old Name': filename,
                'New Path': path + '/' + self.get['new']+suffix,
                'New Name': self.get['new']
        }

        
    def move(self):
        oldPath = self.getFullPath(self.get['old'])
        # the last directory should be regarded as a file, so the last / must be removed
        tmp=self.get['old'].rstrip('/').split('/')
        fileName=tmp.pop()
        path = '/' + '/'.join(tmp) + '/'
        # new path
        if self.get['new'][0] == "/":
            newPath = self.file_root + urldecode(self.get['new']) +'/'
        else:
            # make path relative from old dir
            newPath =  path + urldecode(self.get['new']) + '/'
        newPath = re.sub('/+', '/', newPath)
        newPath = self.expandPath(newPath, False)
        #!important! check that we are still under ROOT dir
        if not newPath.startswith(self.file_root):
            return self.error(self.lang('INVALID_DIRECTORY_OR_FILE'))
        if not self.has_permission('move') or not self.isValidPath(oldPath):
            return self.error("No way.")
        newRelativePath=newPath.replace(self.doc_root,'')
        # check if file already exists
        print(newPath)
        newPath=self.getFullPath(newPath)
        print(oldPath)
        print(newPath)
        print(newPath+'/'+fileName)
        if os.path.exists(newPath+'/'+fileName):
            if os.path.isdir(newPath+'/'+fileName):
                return self.error(self.lang('DIRECTORY_ALREADY_EXISTS') % self.get['new'].rstrip('/')+'/'+fileName)
            else:
                return self.error(self.lang('FILE_ALREADY_EXISTS') % self.get['new'].rstrip('/')+'/'+fileName)
        # create dir if not exists
        if not os.path.exists(newPath):
            try:
                os.makedirs(newPath,0o755)
            except Exception:
                return self.error(self.lang('UNABLE_TO_CREATE_DIRECTORY') % newPath)
        # move
        self.__log(get_current_function_name() + ' - moving '+ oldPath+ ' to directory ' + newPath)
        try:
            os.rename(oldPath,newPath+fileName)
        except os.error:
            if os.path.isdir(oldPath):
                return self.error(self.lang('ERROR_RENAMING_DIRECTORY') % (path,self.get['new']))
            else:
                return self.error(self.lang('ERROR_RENAMING_FILE') % (path+fileName,self.get['new']))
        return {
                'Error': "",
                'Code': 0,
                'Old Path': path,
                'Old Name': fileName,
                'New Path': self.formatPath(newRelativePath),
                'New Name': fileName,
        }
        

    def delete(self):
        current_path = self.getFullPath()
        thumbnail_path = self.get_thumbnail_path(current_path)

        if not self.has_permission('delete') or not self.isValidPath(current_path):
            return self.error("No way.")
        if os.path.isdir(current_path):
            self.unlinkRecursive(current_path)
            # we remove thumbnails if needed
            self.__log(get_current_function_name() + ' - deleting thumbnails folder '+ thumbnail_path)
            self.unlinkRecursive(thumbnail_path)
            self.__log(get_current_function_name() + ' - deleting folder '+ current_path)
            return {
                'Error': "",
                'Code': 0,
                'Path': self.formatPath(self.get['path'])
            }
        elif os.path.exists(current_path):
            os.remove(current_path)
            # delete thumbail if exists
            self.__log(get_current_function_name() + ' - deleting thumbnail file '+ thumbnail_path)
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            self.__log(get_current_function_name() + ' - deleting file '+ current_path);
            return {
                'Error': "",
                'Code': 0,
                'Path': self.formatPath(self.get['path'])
            }
        else:
            return self.error(self.lang('INVALID_DIRECTORY_OR_FILE'))
    
    def replace(self,FILES):
        if 'fileR' not in FILES:
            # if fileSize limit set by the user is greater than size allowed in php.ini file, we apply server restrictions
            # and log a warning into file
            if self.config['upload']['fileSizeLimit'] > self.getMaxUploadFileSize():
                self.__log(get_current_function_name() + ' [WARNING] : file size limit set by user is greater than size allowed in php.ini file : '+ str(self.config['upload']['fileSizeLimit']) + 'Mb > '+ str(self.getMaxUploadFileSize()) +'Mb.')
                self.config['upload']['fileSizeLimit'] = self.getMaxUploadFileSize()
                return self.error(self.lang('UPLOAD_FILES_SMALLER_THAN') % self.config['upload']['fileSizeLimit'] + self.lang('mb'))
            return self.error(self.lang('INVALID_FILE_UPLOAD') + ' '+ self.lang('UPLOAD_FILES_SMALLER_THAN') % self.config['upload']['fileSizeLimit'] + self.lang('mb'))
        send_file=FILES['fileR'][0]
        # we determine max upload size if not set
        if self.config['upload']['fileSizeLimit'] == 'auto':
            self.config['upload']['fileSizeLimit'] = self.getMaxUploadFileSize()

        if len(send_file['body']) > int(self.config['upload']['fileSizeLimit']) * 1024 * 1024:
            return self.error(self.lang('UPLOAD_FILES_SMALLER_THAN') % self.config['upload']['fileSizeLimit'] + self.lang('mb'))
        
        # we check the given file has the same extension as the old one
        newExt=send_file['filename'].split('.').pop().lower()
        oldExt=self.post['newfilepath'].split('.').pop().lower()
        if  newExt != oldExt:
            return self.error(self.lang('ERROR_REPLACING_FILE') + ' '+ newExt)
        
        # we check if extension is allowed regarding the security Policy settings
        if not self.isAllowedFileType(send_file['filename']):
            return self.error(self.lang('INVALID_FILE_TYPE'))
        
        # we check if only images are allowed
        if self.config['upload']['imagesOnly'] or ('type' in self.params and self.params['type'].lower()=='images'):
            if not send_file['content_type'].startswith('image'):
                return self.error(self.lang('UPLOAD_IMAGES_ONLY'))
            if send_file['content_type'] not in ['image/gif', 'image/jpeg', 'image/pjpeg', 'image/png', 'image/x-png']:
                return self.error(self.lang('UPLOAD_IMAGES_TYPE_JPEG_GIF_PNG'))
        send_file['filename'] = self.cleanString(send_file['filename'],['.','-'])

        current_path = self.getFullPath(self.post['newfilepath'])
        
        if not self.has_permission('replace') or not self.isValidPath(current_path):
            self.error("No way.")

        with open(current_path,"wb+") as f:
            f.write(send_file['body'])

        # we delete thumbnail if file is image and thumbnail already
        if self.is_image(current_path) and os.path.exists(self.get_thumbnail(current_path)):
            os.remove(self.get_thumbnail(current_path))

        # automatically resize image if it's too big
        imagePath = current_path
        if self.is_image(imagePath) and self.config['images']['resize']['enabled']:
            image=Image.open(imagePath)
            if image.size[0] > self.config['images']['resize']['maxWidth'] or image.size[1] > self.config['images']['resize']['maxHeight']:
                image.resize((self.config['images']['resize']['maxWidth'], self.config['images']['resize']['maxHeight']),Image.BILINEAR)
                image.save(imagePath)
                
                self.__log(get_current_function_name() + ' - resizing image : '+ send_file['filename']+ ' into '+ current_path)

        os.chmod(current_path, 0o644)

        self.__log(get_current_function_name() + ' - replacing file '+ current_path)
        
        return {
                'Path': os.path.dirname(self.post['newfilepath']),
                'Name': os.path.basename(self.post['newfilepath']),
                'Error': "",
                'Code': 0
        }


    def add(self,FILES):
        if 'newfile' not in FILES:
            # if fileSize limit set by the user is greater than size allowed in php.ini file, we apply server restrictions
            # and log a warning into file
            if self.config['upload']['fileSizeLimit'] > self.getMaxUploadFileSize():
                self.__log(get_current_function_name() + ' [WARNING] : file size limit set by user is greater than size allowed in php.ini file : '+ self.config['upload']['fileSizeLimit'] + 'Mb > '+ self.getMaxUploadFileSize() +'Mb.')
                self.config['upload']['fileSizeLimit'] = self.getMaxUploadFileSize()
                return self.error(self.lang('UPLOAD_FILES_SMALLER_THAN') % self.config['upload']['fileSizeLimit'] + self.lang('mb'))
            return self.error(self.lang('INVALID_FILE_UPLOAD') + ' '+ self.lang('UPLOAD_FILES_SMALLER_THAN') % self.config['upload']['fileSizeLimit'] + self.lang('mb'))
        send_file=FILES['newfile'][0]
        # we determine max upload size if not set
        if self.config['upload']['fileSizeLimit'] == 'auto':
            self.config['upload']['fileSizeLimit'] = self.getMaxUploadFileSize()

        if len(send_file['body']) > int(self.config['upload']['fileSizeLimit']) * 1024 * 1024:
            return self.error(self.lang('UPLOAD_FILES_SMALLER_THAN') % self.config['upload']['fileSizeLimit'] + self.lang('mb'))
        
        # we check if extension is allowed regarding the security Policy settings
        if not self.isAllowedFileType(send_file['filename']):
            return self.error(self.lang('INVALID_FILE_TYPE'))
        
        # we check if only images are allowed
        if self.config['upload']['imagesOnly'] or ('type' in self.params and self.params['type'].lower()=='images'):
            if not send_file['content_type'].startswith('image'):
                return self.error(self.lang('UPLOAD_IMAGES_ONLY'))
            if send_file['content_type'] not in ['image/gif', 'image/jpeg', 'image/pjpeg', 'image/png', 'image/x-png']:
                return self.error(self.lang('UPLOAD_IMAGES_TYPE_JPEG_GIF_PNG'))
        send_file['filename'] = self.cleanString(send_file['filename'],['.','-'])

        current_path = self.getFullPath(self.post['currentpath'])

        if not self.isValidPath(current_path):
            return self.error("No way.")
        
        # auto rename using a number
        if not self.config['upload']['overwrite']:
            send_file['filename'] = self.checkFilename(current_path,send_file['filename'])

        with open(current_path + send_file['filename'],"wb+") as f:
            f.write(send_file['body'])

        # automatically resize image if it's too big
        imagePath = current_path + send_file['filename']
        if self.is_image(imagePath) and self.config['images']['resize']['enabled']:
            image=Image.open(imagePath)
            if image.size[0] > self.config['images']['resize']['maxWidth'] or image.size[1] > self.config['images']['resize']['maxHeight']:
                image.resize((self.config['images']['resize']['maxWidth'], self.config['images']['resize']['maxHeight']),Image.BILINEAR)
                image.save(imagePath)
                
                self.__log(get_current_function_name() + ' - resizing image : '+ send_file['filename']+ ' into '+ current_path)

        os.chmod(current_path + send_file['filename'], 0o644)

        self.__log(get_current_function_name() + ' - adding file '+ send_file['filename'] +' into '+ current_path)
        return {
                'Path': self.post['currentpath'],
                'Name': send_file['filename'],
                'Error': "",
                'Code': 0
        }
        

    def addfolder(self):   
        current_path = self.getFullPath()
        if not self.isValidPath(current_path):
            return self.error("No way.")
        newdir = self.cleanString(self.get['name'])
        if os.path.isdir(current_path + newdir):
            return self.error(self.lang('DIRECTORY_ALREADY_EXISTS') % self.get['name'])
        try:
            os.makedirs(current_path + newdir,0o755)
        except Exception:
            return self.error(self.lang('UNABLE_TO_CREATE_DIRECTORY') % newdir)
        self.__log(get_current_function_name() + ' - adding folder '+ current_path + newdir)
        return {
            'Parent': self.get['path'],
            'Name': self.get['name'],
            'Error': "",
            'Code': 0
        }
            
    def download(self):
        current_path = self.getFullPath()
        if not self.has_permission('download') or not self.isValidPath(current_path):
            return self.error("No way.")
        # we check if extension is allowed regarding the security Policy settings
        if not self.isAllowedFileType(os.path.basename(current_path)):
            return self.error(self.lang('INVALID_FILE_TYPE'))
        if 'path' in self.get and os.path.exists(current_path):
            self.__log(get_current_function_name() + ' - downloading '+ current_path)
            return current_path
        else:
            return self.error(self.lang('FILE_DOES_NOT_EXIST') % current_path)

    def preview(self, thumbnail):
        current_path = self.getFullPath()
        if 'path' in self.get and os.path.exists(current_path):
            # if thumbnail is set to true we return the thumbnail
            if self.config['options']['generateThumbnails'] and thumbnail:
                # get thumbnail (and create it if needed)
                returned_path = self.get_thumbnail(current_path)
            else:
                returned_path = current_path
            return returned_path
        else:
            return self.error(self.lang('FILE_DOES_NOT_EXIST') % current_path)

    def getMaxUploadFileSize(self):
        # TODO: these settings should be determined automatically by the web server
        # As for tornado, the tmpfile is stored in memory, so the limitation is 100Mb
        # A good choice is use nginx, so here should use some API to get the nginx configuration
        # instead of defining a dict as below.
        nginx={
            'upload_max_filesize': 100,
            'post_max_size': 100,
            'memory_limit': 1024
        }
        upload_mb = min(v for k,v in nginx.items())

        self.__log(get_current_function_name() + ' - max upload file size is '+ str(upload_mb)+ 'Mb')

        return upload_mb


    def setParams(self,http_refer=None):
        tmp = http_refer if http_refer else '/'
        tmp = tmp.split('#')[0]
        tmp = tmp.split('?')
        params = {}
        if len(tmp) > 1 and tmp[1]!='':
            params_tmp = tmp[1].split('&')
            if params_tmp:
                for value in params_tmp:
                    tmp = value.split('=')
                    if len(tmp)>1 and tmp[0]!='' and tmp[1]!='':
                        params[tmp[0]] = tmp[1]
        self.params = params

    
    def setPermissions(self):
        self.allowed_actions = self.config['options']['capabilities']
        if self.config['edit']['enabled']:
            self.allowed_actions.append('edit')


    def get_file_info(self, path='', thumbnail = False):
        if path=='':
            current_path = self.get['path']
        else:
            current_path = path        
        fullPath=self.getFullPath(current_path)
        fileStat=os.stat(fullPath)
        tmp = current_path.split('/')
        self.item['filename'] = tmp[-1]
        tmp = self.item['filename'].split('.')
        self.item['filetype'] = tmp[-1]
        self.item['filemtime'] = fileStat.st_mtime
        self.item['filectime'] = fileStat.st_ctime
        self.item['preview'] = self.config['icons']['path'] + self.config['icons']['default']
        if os.path.isdir(current_path):
            self.item['preview'] = self.config['icons']['path'] + self.config['icons']['directory']
        elif self.item['filetype'].lower() in map(lambda x:x.lower(), self.config['images']['imagesExt']):
            # svg should not be previewed as raster formats images
            if self.item['filetype'] == 'svg':
                self.item['preview'] = current_path
            else:
                self.item['preview'] = '/browser?mode=preview&path='+urlencode(current_path)+'&'+ str(time.mktime(time.localtime()))
                if thumbnail:
                    self.item['preview'] += '&thumbnail=true'
            self.item['properties']['Size'] = fileStat.st_size
            if self.item['properties']['Size']:
                image = Image.open(fullPath)
                (width,height)=image.size
                #fileType=image.format
            else:
                self.item['properties']['Size'] = 0
                width, height = 0, 0
            self.item['properties']['Height'] = height;
            self.item['properties']['Width'] = width
        elif os.path.exists(self.filemanager_root+self.config['icons']['path'] + self.item['filetype'].lower() + '.png'):
            self.item['preview'] = self.config['icons']['path'] + self.item['filetype'].lower() + '.png'
            self.item['properties']['Size'] = fileStat.st_size
            if not self.item['properties']['Size']:
                self.item['properties']['Size'] = 0
        else:
            self.item['properties']['Size'] = fileStat.st_size
        self.item['properties']['filemtime'] = fileStat.st_mtime
        self.item['properties']['Date Modified'] = time.strftime(self.config['options']['dateFormat'],time.localtime(self.item['filemtime']))


    def getFullPath(self, path = '', manual=False):
        if not path:
            if 'path' in self.get:
                path = self.get['path']
        if manual:
            full_path = self.doc_root + urldecode(path).lstrip('/')
        else:
            full_path = self.doc_root + urldecode(path).replace(self.file_root, '').lstrip('/')
        return full_path


    def formatPath(self, path, manual=False):
        if manual:
            return path.split(self.separator)[-1]
        else:
            return path

    def sortFiles(self,array):
        # handle 'NAME_ASC'
        if self.config['options']['fileSorting'] == 'NAME_ASC':
            array = array[::-1]
        # handle 'TYPE_ASC' and 'TYPE_DESC'
        if self.config['options']['fileSorting'].find('TYPE_') != -1 or self.config['options']['fileSorting'] == 'default':
            a = {}
            b = {}            
            for key,item in array.items():
                if operator.eq(item["File Type"], "dir"):
                    a[key]=item
                else:
                    b[key]=item
            if self.config['options']['fileSorting'] == 'TYPE_ASC':
                array = dict(a, **b)
            if self.config['options']['fileSorting'] == 'TYPE_DESC' or self.config['options']['fileSorting'] == 'default':
                array = dict(b, **a)
        # handle 'MODIFIED_ASC' and 'MODIFIED_DESC'
        if self.config['options']['fileSorting'].find('MODIFIED_') != -1:
            auxiliary_list = [(['Properties']['filemtime'], x) for x in array]
            if self.config['options']['fileSorting'] == 'MODIFIED_ASC':
                auxiliary_list.sort()
            if self.config['options']['fileSorting'] == 'MODIFIED_DESC':
                auxiliary_list.sort(reverse=True)
            array[:]=[x[1] for x in auxiliary_list]
        return array
        
        
    def isValidPath(self, path):
        return path.startswith(self.doc_root)

    def unlinkRecursive(self, path,deleteRootToo=True):
        if not os.path.exists(path) or not os.path.isdir(path):
            return
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        if deleteRootToo:
            os.rmdir(path)

    def isAllowedFileType(self,file):
        fext=self.splitPathInfo(file)["extension"].lstrip('.')
        # if there is no extension AND no extension file are not allowed
        if not fext and not self.config['security']['allowNoExtension']:
            return False
        exts = map(lambda x:x.lower(), self.config['security']['uploadRestrictions'])
        if self.config['security']['uploadPolicy'] == 'DISALLOW_ALL':
            return fext.lower() in exts
        if self.config['security']['uploadPolicy'] == 'ALLOW_ALL':
            return  fext.lower() not in exts
        return True

    def cleanString(self, string, allowed = []):
        mapping = {
            'Š':'S', 'š':'s', 'Đ':'Dj', 'đ':'dj', 'Ž':'Z', 'ž':'z', 'Č':'C', 'č':'c', 'Ć':'C', 'ć':'c',
            'À':'A', 'Á':'A', 'Â':'A', 'Ã':'A', 'Ä':'A', 'Å':'A', 'Æ':'A', 'Ç':'C', 'È':'E', 'É':'E',
            'Ê':'E', 'Ë':'E', 'Ì':'I', 'Í':'I', 'Î':'I', 'Ï':'I', 'Ñ':'N', 'Ò':'O', 'Ó':'O', 'Ô':'O',
            'Õ':'O', 'Ö':'O', 'Ő':'O', 'Ø':'O', 'Ù':'U', 'Ú':'U', 'Û':'U', 'Ü':'U', 'Ű':'U', 'Ý':'Y',
            'Þ':'B', 'ß':'Ss','à':'a', 'á':'a', 'â':'a', 'ã':'a', 'ä':'a', 'å':'a', 'æ':'a', 'ç':'c',
            'è':'e', 'é':'e', 'ê':'e', 'ë':'e', 'ì':'i', 'í':'i', 'î':'i', 'ï':'i', 'ð':'o', 'ñ':'n',
            'ò':'o', 'ó':'o', 'ô':'o', 'õ':'o', 'ö':'o', 'ő':'o', 'ø':'o', 'ù':'u', 'ú':'u', 'ű':'u',
            'û':'u', 'ü':'u', 'ý':'y', 'ý':'y', 'þ':'b', 'ÿ':'y', 'Ŕ':'R', 'ŕ':'r', ' ':'_', "'":'_', '/':''
        }
        allow = r"\\".join(allowed) if allowed else r""
        regex1=re.compile(r"[^"+allow+"_a-zA-Z0-9]",re.UNICODE)
        # allow only latin alphabet with cyrillic
        # "[^{allow}_a-zA-Z0-9\x{0430}-\x{044F}\x{0410}-\x{042F}]"   
        regex2=re.compile(r'[_]+',re.UNICODE)
        pattern = re.compile("|".join([re.escape(k) for k in mapping.keys()]), re.M)
        if isinstance(string,dict):
            cleaned = {}
            for key,clean in string.items():
                clean = pattern.sub(lambda x: mapping[x.group(0)], clean)
                if self.config['options']['chars_only_latin']:
                    clean = regex1.sub('', clean)
                cleaned[key] = regex2.sub('_', clean) # remove double underscore
        else:
            clean = pattern.sub(lambda x: mapping[x.group(0)], string)
            if self.config['options']['chars_only_latin']:
                    clean = regex1.sub('', clean)
            cleaned = regex2.sub('_', clean) # remove double underscore
        return cleaned

    def has_permission(self,action):
        return action in self.allowed_actions

    def get_thumbnail_path(self, path):
        pinfo=self.splitPathInfo(path)
        parts = pinfo['path'].split(self.separator)
        thumbnail_path = ''.join([pinfo['drive'],parts[0],self.separator,'/_thumbs',parts[1]])
        thumbnail_name = ''.join([pinfo["file"],'_'+str(self.thumbnail_width)+'x'+str(self.thumbnail_height)+'px',pinfo['extension']])
        if os.path.isdir(path):
            thumbnail_fullpath = thumbnail_path
        else:
            thumbnail_fullpath = thumbnail_path + thumbnail_name
        return thumbnail_fullpath

    def get_thumbnail(self, path) :
        thumbnail_fullpath = self.get_thumbnail_path(path)    
        # if thumbnail does not exist we generate it
        if not os.path.exists(thumbnail_fullpath):
            # create folder if it does not exist
            Dir= os.path.split(thumbnail_fullpath.strip('/'))[0]
            if not os.path.isdir(Dir):
                os.makedirs(Dir, 0o755)
        img = Image.open(path)
        img.thumbnail((self.thumbnail_width, self.thumbnail_height),Image.ANTIALIAS)
        img.save(thumbnail_fullpath)
        self.__log(get_current_function_name() + ' - generating thumbnail :  '+ thumbnail_fullpath)
        return thumbnail_fullpath

        
    def sanitize(self, var, preserve = None):
        sanitized = html_to_text(var).replace('http://', '').replace('https://', '')
        if preserve != 'parent_dir':
            sanitized.replace('../', '')
        return sanitized

    # search
    def checkFilename(self,path,filename,i=''):
        if not os.path.exists(path + filename):
            return filename
        else:
            _i = i
            tmp = filename.split(str(i)+'.')
            i = 1 if i=='' else i + 1
            filename=filename.replace(str(_i) + '.' + tmp[-1], str(i) + '.' + tmp[-1])
            return self.checkFilename(path,filename,i)

    def loadLanguageFile(self) :
        # we load langCode var passed into URL if present and if exists
        # else, we use default configuration var
        lang = self.config['options']['culture']
        if 'langCode' in self.params and self.params['langCode'] in self.languages:
            lang = self.params['langCode']
        if os.path.exists(self.filemanager_root+'scripts/languages/'+lang +'.js'):
            with open(self.filemanager_root+ 'scripts/languages/'+lang+'.js',encoding="utf-8") as f:
                self.language = json.load(f)
        else:
            with open(self.filemanager_root+ 'scripts/languages/en.js',encoding="utf-8") as f:
                self.language = json.load(f)
        
    def availableLanguages(self):
        Dir=self.filemanager_root + 'scripts/languages/'
        for file in os.listdir(Dir):
            self.languages.append(os.path.splitext(file)[0])

    def is_image(self, path):
        try:
            img=Image.open(path)
            return img.format in ['GIF', 'JPEG' ,'PNG' , 'BMP']
        except:
            return False


    def isEditable(self, path):
        print(self.splitPathInfo(path)['extension'].lstrip('.'))
        return self.splitPathInfo(path)['extension'].lstrip('.') \
            in map(lambda x:x.lower(), self.config['edit']['editExt'])

    def __log(self, msg):
        if self.logger == True:
            with open(self.server_root+self.logfile.lstrip('/'), 'a+', encoding='utf-8',newline='') as fp:
                fp.write("[" + time.strftime("%b-%d-%y %H:%M:%S", time.localtime()) + "]#"+  self.user_ip + "#" + msg +os.linesep)

    def enableLog(self, logfile = ''):
        self.logger = True
        if logfile:
            self.logfile = logfile
        self.__log(get_current_function_name() + ' - Log enabled (in '+ self.logfile+ ' file)')

    def disableLog(self):
        self.logger = False
        self.__log(get_current_function_name() + ' - Log disabled')

    def splitPathInfo(self,path):
        drive, tail=os.path.splitdrive(path)
        pathName, tail=os.path.split(tail)
        fileName, extension=os.path.splitext(tail)
        return {
            "drive":drive,
            "path":self.expandPath(pathName.rstrip('/')+'/'),
            "file":fileName,
            "extension":extension
        }
        
    def expandPath(self, path, clean = False):
        todo  = path.split('/')
        fullPath = []
        for Dir in todo:
            if Dir == '..':
                if not fullPath:
                    return False
                fullPath.pop()
            else:
                if clean:
                    Dir = self.cleanString(Dir,allowed=["-","+","&","."])
                fullPath.append(Dir)
        return '/'.join(fullPath)