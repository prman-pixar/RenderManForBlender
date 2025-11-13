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

from bpy.props import *
from bpy.types import PropertyGroup
from ..rfb_logger import rfb_log
import bpy.utils
import os

class RendermanPresetMetaData(PropertyGroup):

    key: StringProperty(name="Key", default='')
    value: StringProperty(name="Value", default='')

class RendermanPreset(PropertyGroup):
    '''This class represents a single RendderMan preset on disk

    Attributes:
        name (bpy.props.StringProperty) - name of the preset
        label (bpy.props.StringProperty) - the preset's label
        thumb_path (bpy.props.StringProperty) - the path to the thumbnail for this preset
        path (bpy.props.StringProperty) - the path to the preset on disk
        json_path (bpy.props.StringProperty) - the path to the preset's JSON file on disk
        author (bpy.props.StringProperty) - the preset's author
        version (bpy.props.StringProperty) - the preset's version
        created (bpy.props.StringProperty) - the preset's creation timestamp
    '''


    bl_label = "RenderMan Preset"
    bl_idname = 'RendermanPreset'
    
    name: StringProperty(default='', name="Name")
    label: StringProperty(default='', name="Label")
    author: StringProperty(default='', name="Author")
    version: StringProperty(default='', name="Version")
    created: StringProperty(default='', name="Created")
    resolution: StringProperty(default='', name="Resolution")
    preset_metadata: CollectionProperty(type=RendermanPresetMetaData,
                                      name="Meta Data")

    thumb_path: StringProperty(subtype='FILE_PATH')
    path: StringProperty(subtype='FILE_PATH')
    json_path: StringProperty(subtype='FILE_PATH')
    icon_id: IntProperty(default=-1)


class RendermanPresetCategory(PropertyGroup):
    '''This class represents a single preset category

    Attributes
        name (bpy.props.StringProperty) - category name
        path (bpy.props.StringProperty) - full path on disk to this category in the presets library
        rel_path (bpy.props.StringProperty) - relative path on disk to this category in the presets library
    '''

    bl_label = "RenderMan Preset Category"
    bl_idname = 'RendermanPresetCategory'

    name: StringProperty(default='')    
    path: StringProperty(default='', name='Path', subtype="FILE_PATH")
    rel_path: StringProperty(default='', name='Rel Path', subtype="FILE_PATH")

classes = [
    RendermanPresetMetaData,
    RendermanPreset,
    RendermanPresetCategory
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes) 

def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)   
