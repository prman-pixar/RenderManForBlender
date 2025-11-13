# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2025 Pixar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# ##### END MIT LICENSE BLOCK #####

import os
import os.path
import sys


class FilePath(str):
    """A class based on unicode to handle filepaths on various OS platforms.

    Extends:
        unicode
    """

    def __new__(cls, path):
        """Create new unicode file path in POSIX format. Windows paths will be
        converted to forward slashes.

        Arguments:
            path {str} -- a file path, in any format.
        """
        if not isinstance(path, str):
            # make sure we use python's native encoding
            # err =  'NEW: %r\n' % path
            for codec in [sys.getfilesystemencoding(), sys.getdefaultencoding()]:
                try:
                    # some unknown encoding to python native encoding
                    fpath = str(path.decode(codec))
                except (UnicodeDecodeError, UnicodeEncodeError) as err:
                    # err += '  |_ CAN NOT DECODE as %s: %r\n' % (codec, path)
                    # err += '     |_ %s\n' % err
                    continue
                else:
                    # err += '  |_ decoded as %s: %s (%r)' % (codec, fpath, fpath)
                    # err = ''
                    break
            # if err:
            #     print err
        else:
            fpath = path
        if os.sep != '/':
            fpath = fpath.replace('\\', '/')
        return str.__new__(cls, fpath)

    def os_path(self):
        """return the platform-specif path, i.e. convert to windows format if
        need be.

        Returns:
            str -- a path formatted for the current OS.
        """
        return str(os.path.normpath(self))

    def exists(self):
        """Check is the path actually exists, using os.path.

        Returns:
            bool -- True if the path exists.
        """
        return os.path.exists(self)

    def join(self, *args):
        """Combine the arguments with the current path and return a new
        FilePath object.

        Arguments:
            *args {list} -- a list of path segments.

        Returns:
            FilePath -- A new object containing the joined path.
        """
        return FilePath(os.path.join(self, *args))

    def dirname(self):
        """Returns the dirname of the current path (using os.path.dirname) as a
        FilePath object.

        Returns:
            FilePath -- the path's directory name.
        """
        return FilePath(os.path.dirname(self))

    def basename(self):
        """Return the basename, i.e. '/path/to/file.ext' -> 'file.ext'

        Returns:
            str -- The final segment of the path.
        """
        return os.path.basename(self)

    def is_writable(self):
        """Checks if the path is writable. The Write and Execute bits must
        be enabled.

        Returns:
            bool -- True is writable
        """
        return os.access(self, os.W_OK | os.X_OK)

    def expandvars(self):
        """Return a Filepath with expanded environment variables and '~'.
        """
        return FilePath(os.path.expandvars(os.path.expanduser(self)))

    def isabs(self):
        """Check if this is an absolute path.

        Returns:
            bool -- True if absolute path
        """
        return os.path.isabs(self)

    def is_ascii(self):
        try:
            self.encode('ascii')
        except (UnicodeDecodeError, UnicodeEncodeError):
            return False
        else:
            return True
