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

def get_dump_rib_path(frame):
    if rman_constants.RFB_PLATFORM == "windows":
        return "C:/tmp/blender.%04d.rib" % frame
    else:
        return "/var/tmp/blender.%04d.rib" % frame

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

# A python double-quoted string literal, honouring backslash escapes. Anything simpler goes wrong on
# real traces: [^"\s]* silently skips any path containing a space, and [^"]* runs a value like
# "say \"hi\"" together with whatever follows it, because it stops at the escaped quote.
DISGUST_STRING_PAT = re.compile(r'"((?:[^"\\]|\\.)*)"')

# What Disgust escapes when it writes a string, so these are what have to be undone to get a path
# back, and redone when one is written. Backslash is first in each direction, which is what keeps the
# escapes from being applied to each other's output.
_DISGUST_ESCAPES = (('\\', '\\\\'), ('"', '\\"'), ('\n', '\\n'), ('\r', '\\r'), ('\t', '\\t'))


def unescape_disgust_string(s):
    """Turn the text inside a trace's string literal back into the value it stands for.

    A windows path arrives here as C:\\\\tex\\\\wood.tex -- doubled backslashes -- so testing it
    against the filesystem or copying it needs the real C:\\tex\\wood.tex.
    """
    out = []
    i = 0
    unescape = {'\\': '\\', '"': '"', 'n': '\n', 'r': '\r', 't': '\t'}
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            out.append(unescape.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def escape_disgust_string(s):
    """Escape a value the way Disgust would, for writing back into a trace."""
    for plain, escaped in _DISGUST_ESCAPES:
        s = s.replace(plain, escaped)
    return s


def trace_path(*parts):
    """Join path components for writing into a trace or a zip, always with forward slashes.

    os.path.join gives backslashes on windows, and neither destination wants them. A trace is meant
    to be portable -- localizing an asset to assets\\wood.tex packages a scene that only replays on
    windows, which defeats the point -- and the zip format requires "/" as its separator, so a
    backslash entry reads as a filename containing a backslash rather than as a directory.

    This matches what the rest of this module already does: filesystem_path() and
    get_token_blender_file_path() both end by replacing backslashes with forward slashes.
    """
    return '/'.join(p for p in parts if p).replace('\\', '/')


def trace_basename(p):
    """The last component of a path, whichever separator it uses.

    os.path.basename only understands the host's separator, so on posix it returns a whole
    C:\\tex\\wood.tex unchanged. A trace can carry a path from either convention.
    """
    return p.replace('\\', '/').rstrip('/').rpartition('/')[2]


def localize_disugst_trace(disgust_trace, out_file, asset_dirs, remove_files, z):
    """Try to localize all paths in the disgust_trace
    by searching for all double-quoted string literals

    Traces used to spell every string UString("..."), and this looked for exactly that. They now
    carry plain python literals, so a bare "..." is what has to be matched -- with the old pattern
    this function silently became a no-op and packaged traces kept their absolute, machine-local
    paths.

    Only double quotes are searched. That is what distinguishes a value from the rest of a
    parameter tuple: a trace writes ('String', 'filename', ["/path/to.tex"]), with the type and
    parameter name single-quoted and only the value double-quoted.

    The text inside a literal is escaped, so it is unescaped before being tested against the
    filesystem and re-escaped on the way back in. Paths containing spaces are handled; paths
    containing a double quote are not, and neither is anything else that would be unusual enough in
    a filename to be worth guessing about.

    Args:
    - disgust_trace (str): path to the python disgust trace
    - out_file (str): path to copy the python disgust trace for packaging
    - asset_dirs (list): list of asset directories in the packaging directory
    - remove_files (list): the list of files that need to be deleted after packaging
    - z (ZipFile): the output zip file

    """

    pat = DISGUST_STRING_PAT
    f = open(out_file, "w")
    out_path = os.path.dirname(out_file)
    asset_path = os.path.join(out_path, 'assets')

    with open(disgust_trace) as df:
        lines = df.readlines()
        for line in lines:
            # finditer, not findall: both the escaped text inside the literal and the literal
            # including its quotes are needed -- the first to substitute a path, the second to
            # replace the whole thing with an os.path.join(...) expression.
            matches = list(re.finditer(pat, line))
            if matches:
                write_line = line # make a copy of the line
                for match in matches:
                    escaped_str = match.group(1)  # as it appears in the trace, still escaped
                    match_str = unescape_disgust_string(escaped_str)  # the value it stands for
                    if 'rl.CreateDisplay' in write_line and '/' in match_str:
                        # for display lines, change the path to just the basename

                        if os.path.isfile(match_str):
                            # copy rendered images, but add the substring 
                            # .original to them
                            asset_file = trace_basename(match_str)
                            tokens = os.path.splitext(asset_file)
                            asset_file = '%s.original%s' % (tokens[0], tokens[-1])
                            diskpath = os.path.join(out_path, asset_file)
                            arcname = asset_file
                            shutil.copyfile(match_str, diskpath)
                            z.write(diskpath, arcname=arcname)    
                            remove_files.append(diskpath)                        
                        
                        write_line = write_line.replace(
                            escaped_str, escape_disgust_string(trace_basename(match_str)))
                    # isfile, not exists: now that every double-quoted value is inspected, a
                    # directory-valued parameter such as searchpath:texture reaches here, and
                    # shutil.copyfile on a directory raises.
                    elif os.path.isfile(match_str):
                        if envconfig().rmantree in match_str:
                            # if RMANTREE is line, just substitue with:
                            # os.path.join(os.environ['RMANTREE], ...
                            path = match_str.replace(envconfig().rmantree, "")
                            # Either separator: on windows what is left begins with a backslash, and
                            # leaving it there makes the join below drop RMANTREE altogether --
                            # ntpath.join("C:/rmantree", "\\lib\\x.oso") is "C:\\lib\\x.oso".
                            path = path.lstrip('/\\')
                            path = ('os.path.join(os.environ["RMANTREE"], "'
                                    + escape_disgust_string(trace_path(path)) + '")')
                            write_line = write_line.replace(match.group(0), path)
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
                                # From the directory's own name, not from splitting diskpath on "/":
                                # os.path.join gives backslashes on windows, so that split returned a
                                # single element and indexing [-2] raised -- and where the path did
                                # happen to contain a "/" it picked the grandparent instead.
                                relpath = trace_path(trace_basename(asset_dir), asset_file)
                                write_line = write_line.replace(
                                    escaped_str, escape_disgust_string(relpath))
                                break         
                        if not exists:
                            # file doesn't exist in our asset_dirs
                            # copy to the "assets" sub dir, and modify the line
                            diskpath = os.path.join(asset_path, asset_file)
                            arcname = trace_path('assets', asset_file)
                            shutil.copyfile(match_str, diskpath)
                            z.write(diskpath, arcname=arcname)
                            write_line = write_line.replace(
                                escaped_str, escape_disgust_string(arcname))
                            remove_files.append(diskpath)
                f.write(write_line)
            else:
                # no match, write the line as is
                f.write(line)
