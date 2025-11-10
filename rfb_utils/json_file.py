"""
Load and save JSON data.
No exception handling at all: should be handled by the caller.
"""

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

import json
from collections import OrderedDict


def load(file_path, ordered=False):
    """Load a JSON file from disk.

    Args:
    - file_path (FilePath): The fully qualified file path.

    Returns:
    - dict: The JSON data
    """

    fh = open(file_path, mode='r')
    data = None
    if ordered:
        data = json.load(fh, object_pairs_hook=OrderedDict)
    else:
        data = json.load(fh)
    fh.close()
    return data


def save(data, file_path):
    """Save a dict as a JSON file.

    Args:
    - data (dict): The JSON data.

    Returns:
    - None
    """
    fh = open(file_path, mode='w')
    json.dump(data, fh)
    fh.close()
