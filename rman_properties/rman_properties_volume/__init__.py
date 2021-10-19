from bpy.props import BoolProperty, PointerProperty, StringProperty, EnumProperty

from ...rfb_logger import rfb_log 
from ...rman_config import RmanBasePropertyGroup
from ...rfb_utils import filepath_utils
import os
import bpy

class RendermanVolumeGeometrySettings(RmanBasePropertyGroup, bpy.types.PropertyGroup):
    
    def check_openvdb(self):
        ob = bpy.context.object
        if ob.type != 'VOLUME':
            return False        
        volume = bpy.context.volume
        openvdb_file = filepath_utils.get_real_path(volume.filepath)
        return os.path.exists(openvdb_file)

    has_openvdb: BoolProperty(name='', get=check_openvdb)

    def get_mipmap_vdb_path(self):
        ob = bpy.context.object
        if ob.type != 'VOLUME':
            return False        
        volume = bpy.context.volume        
        openvdb_file = filepath_utils.get_real_path(volume.filepath)
        if not os.path.exists(openvdb_file):
            return ''
        mipmap_filepath = '%s_mipmap.vdb' % os.path.splitext(openvdb_file)[0]
        if os.path.exists(mipmap_filepath):
            return mipmap_filepath
        return ''

    rman_mipmap_vdb_path: StringProperty(name='', get=get_mipmap_vdb_path)

classes = [         
    RendermanVolumeGeometrySettings
]           

def register():

    for cls in classes:
        cls._add_properties(cls, 'rman_properties_volume')
        bpy.utils.register_class(cls)  

    bpy.types.Volume.renderman = PointerProperty(
        type=RendermanVolumeGeometrySettings,
        name="Renderman Voume Geometry Settings")

def unregister():

    del bpy.types.Volume.renderman

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass