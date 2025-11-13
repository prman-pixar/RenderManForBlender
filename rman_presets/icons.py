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
import bpy
import bpy.utils.previews
from ..rfb_utils.prefs_utils import get_pref
from ..rfb_utils.envconfig_utils import envconfig
import json

asset_previews = bpy.utils.previews.new()
__RMAN_MAT_FLAT_PATH__ = 'lib/rmanAssetResources/icons'
__RMAN_MAT_FLAT_FILENAME__ = 'rman_Mat_default_big_100.png'

def get_presets_for_category(preset_category):
    items = list(preset_category.presets)
    
    if get_pref('presets_show_subcategories', False):
        for sub_category in preset_category.sub_categories:
            items.extend(get_presets_for_category(sub_category))

    return items

def get_icon(path):
    global asset_previews
    thumb = asset_previews.get(path, None)
    if not thumb:
        flat_icon_path = os.path.join(envconfig().rmantree, __RMAN_MAT_FLAT_PATH__)
        flat_icon_thumb = asset_previews.get(flat_icon_path, None)
        if not flat_icon_thumb:
            flat_icon_thumb_path = os.path.join(flat_icon_path, __RMAN_MAT_FLAT_FILENAME__)
            flat_icon_thumb = asset_previews.load(flat_icon_path, flat_icon_thumb_path, 'IMAGE', force_reload=True)     

        return flat_icon_thumb
    return thumb  

def get_preset_icon(preset_path):
    global asset_previews
    flat_icon_path = os.path.join(envconfig().rmantree, __RMAN_MAT_FLAT_PATH__)
    flat_icon_thumb = asset_previews.get(flat_icon_path, None)
    if not flat_icon_thumb:
        flat_icon_thumb_path = os.path.join(flat_icon_path, __RMAN_MAT_FLAT_FILENAME__)
        flat_icon_thumb = asset_previews.load(flat_icon_path, flat_icon_thumb_path, 'IMAGE', force_reload=True)
    
    path = preset_path
    if path not in asset_previews:
        thumb_path = os.path.join(path, 'asset_100.png')
        if os.path.exists(thumb_path):
            thumb = asset_previews.load(path, thumb_path, 'IMAGE', force_reload=True)
        else:
            thumb = flat_icon_thumb
    else:
        thumb = asset_previews[path]   

    return thumb      