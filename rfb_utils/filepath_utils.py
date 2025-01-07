import bpy
import os
import shutil
import sys
import webbrowser
import re
from ..rfb_logger import rfb_log
from .prefs_utils import get_pref
from . import string_utils
from .. import rman_constants
from .envconfig_utils import envconfig

def view_file(file_path):
    
    rman_editor = get_pref('rman_editor', '')

    if rman_editor:
        rman_editor = get_real_path(rman_editor)
        command = rman_editor + " " + file_path
        try:
            os.system(command)
            return
        except Exception:
            rfb_log().error("File or text editor not available. (Check and make sure text editor is in system path.)")        


    if rman_constants.RFB_PLATFORM == "windows":
        try:
            os.startfile(file_path)
            return
        except:
            pass
    else:
        if rman_constants.RFB_PLATFORM == "macOS":
            opener = 'open -t'
        else:
            opener = os.getenv('EDITOR', 'xdg-open')
            opener = os.getenv('VIEW', opener)
        try:
            command = opener + " " + file_path
            os.system(command)
            return
        except Exception as e:
            rfb_log().error("Open file command failed: %s" % command)
            pass
        
    # last resort, try webbrowser
    try:
        webbrowser.open(file_path)
    except Exception as e:
        rfb_log().error("Open file with web browser failed: %s" % str(e))    

def get_cycles_shader_path():
    # figure out the path to Cycles' shader path
    # hopefully, this won't change between versions
    path = ''
    version  = '%d.%d' % (bpy.app.version[0], bpy.app.version[1])
    binary_path = os.path.dirname(bpy.app.binary_path)
    rel_config_path = os.path.join(version, rman_constants.CYCLES_SHADERS_PATH)
    if rman_constants.RFB_PLATFORM == "windows":
        path = os.path.join(binary_path, rel_config_path)
    elif rman_constants.RFB_PLATFORM  == "macOS":                
        path = os.path.join(binary_path, '..', 'Resources', rel_config_path )
    else:
        path = os.path.join(binary_path, rel_config_path)        

    return path

def get_token_blender_file_path(p):
    # Same as filesystem_path below, but substitutes the relative Blender path
    # with the <blend_dir> token
    if not get_pref('rman_use_blend_dir_token', True):
        return filesystem_path(p)
    if p.startswith('//'):
        pout = bpy.path.abspath(p)
        if p != pout:
            regex = r"^//"
            pout = re.sub(regex, '<blend_dir>/', p, 0, re.MULTILINE)
    else:
        blend_dir = string_utils.get_var('blend_dir')
        if blend_dir == '':
            pout = p
        elif blend_dir.endswith('/'):
            pout = p.replace(blend_dir, '<blend_dir>')
        else:    
            pout = p.replace(blend_dir, '<blend_dir>/')

    return pout.replace('\\', '/')
 
def filesystem_path(p):
    #Resolve a relative Blender path to a real filesystem path
    pout = p
    if pout.startswith('//'):
        pout = bpy.path.abspath(pout)

    if os.path.isabs(pout):
        pout = os.path.realpath(pout)

    return pout.replace('\\', '/')

def get_real_path(path):
    # This looks weird in that we're simply returning filesystem_path
    # However, originally the code for these two functions were slightly different
    # There's too many places that get_real_path is called, so just leave this as is
    return filesystem_path(path)

def localize_disugst_trace(disgust_trace, out_file, asset_dirs, remove_files, z):
    """Try to localize all paths in the disgust_trace
    by searching for all instances of UString

    Args:
    - disgust_trace (str): path to the python disgust trace
    - out_file (str): path to copy the python disgust trace for packaging
    - asset_dirs (list): list of asset directories in the packaging directory
    - remove_files (list): the list of files that need to be deleted after packaging
    - z (ZipFile): the output zip file

    """

    pat = re.compile(r"UString\((\"\S*\")\)")
    f = open(out_file, "w")
    out_path = os.path.dirname(out_file)
    asset_path = os.path.join(out_path, 'assets')

    with open(disgust_trace) as df:
        lines = df.readlines()
        for line in lines:
            matches = re.findall(pat, line)
            if matches:
                write_line = line # make a copy of the line
                for m in matches:     
                    match_str = m[1:-1] # remove quotes         
                    if 'rl.CreateDisplay' in write_line and '/' in match_str:
                        # for display lines, change the path to just the basename

                        if os.path.exists(match_str):
                            # copy rendered images, but add the substring 
                            # .original to them
                            asset_file = os.path.basename(match_str)
                            tokens = os.path.splitext(asset_file)
                            asset_file = '%s.original%s' % (tokens[0], tokens[-1])
                            diskpath = os.path.join(out_path, asset_file)
                            arcname = asset_file
                            shutil.copyfile(match_str, diskpath)
                            z.write(diskpath, arcname=arcname)    
                            remove_files.append(diskpath)                        
                        
                        write_line = write_line.replace(match_str, os.path.basename(match_str) )
                    elif os.path.exists(match_str):
                        if envconfig().rmantree in match_str:
                            # if RMANTREE is line, just substitue with:
                            # os.path.join(os.environ['RMANTREE], ...
                            path = match_str.replace(envconfig().rmantree, "")
                            if path[0] == '/':
                                path = path[1:]
                            path = 'os.path.join(os.environ["RMANTREE"], "' + path + '")'
                            write_line = write_line.replace(m, path)
                            continue

                        # check if this asset already exists in our asset_dirs
                        asset_file = os.path.basename(match_str)
                        exists = False
                        for asset_dir in asset_dirs:
                            diskpath = os.path.join(asset_dir, asset_file)
                            if os.path.exists(diskpath):
                                # path exists in our assets dir.
                                # make sure to use a relative path
                                exists = True
                                paths = diskpath.split('/')
                                relpath = os.path.join(paths[-2], paths[-1])
                                write_line = write_line.replace(match_str, relpath)
                                break         
                        if not exists:
                            # file doesn't exist in our asset_dirs
                            # copy to the "assets" sub dir, and modify the line
                            diskpath = os.path.join(asset_path, asset_file)
                            arcname = os.path.join('assets', asset_file)
                            shutil.copyfile(match_str, diskpath)
                            z.write(diskpath, arcname=arcname)
                            write_line = write_line.replace(match_str, arcname)
                            remove_files.append(diskpath)
                f.write(write_line)
            else:
                # no match, write the line as is
                f.write(line)
