import bpy

from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty, PointerProperty
    
from ... import rman_bl_nodes
from ... import rman_config
from ...rfb_utils import scene_utils
from ...rfb_utils.property_callbacks import update_displays_func
from ... import rfb_icons
from ...rman_config import RmanBasePropertyGroup

class RendermanDspyChannel(RmanBasePropertyGroup, bpy.types.PropertyGroup):
    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_dspychan') 

    def update_name(self, context):
        self.channel_name = self.name
        update_displays_func(None, context)

    name: StringProperty(name='Channel Name', update=update_name)
    channel_name: StringProperty(update=update_displays_func)

    channel_source: StringProperty(name="Channel Source",
            description="Source definition for the channel",
            default="lpe:C[<.D><.S>][DS]*[<L.>O]",
            update=update_displays_func
            )

    channel_type: EnumProperty(name="Channel Type",
            description="Channel type",
            items=[
                ("color", "color", ""),
                ("float", "float", ""),
                ("vector", "vector", ""),
                ("normal", "normal", ""),
                ("point", "point", ""),
                ("integer", "integer", "")],
            default="color",
            update=update_displays_func
            )            

    is_custom: BoolProperty(name="Custom", default=False)

    custom_lpe_string: StringProperty(
        name="lpe String",
        description="This is where you enter the custom lpe string",
        update=update_displays_func)

    def object_groups(self, context):
        items = []
        items.append((" ", " ", ""))
        rm = context.scene.renderman
        for i, ogrp in enumerate(rm.object_groups):
            if i == 0:
                continue
            items.append((ogrp.name, ogrp.name, ""))
        return items        

    object_group: EnumProperty(name='Object Group', items=object_groups)       
    light_group: StringProperty(name='Light Group', default='', update=update_displays_func)
    lpe_group: StringProperty(name='LPE Group', default='', update=update_displays_func)

class RendermanDspyChannelPointer(bpy.types.PropertyGroup):
    dspy_chan_idx: IntProperty(default=-1, name="Display Channel Index")

class RendermanAOV(RmanBasePropertyGroup, bpy.types.PropertyGroup):

    name: StringProperty(name='Display Name')
    rman_config_name: StringProperty(name='rman_config_name',
                                    default='rman_properties_aov') 


    def displaydriver_items(self, context):
        items = []   
        # default to OpenEXR   
        rman_icon = rfb_icons.get_icon(name='out_d_openexr', dflt='out_rmanDisplay') 
        items.append(('openexr', 'openexr', '', rman_icon.icon_id, 0)) 
        i = 1
        for n in rman_bl_nodes.__RMAN_DISPLAY_NODES__:
            dspy = n.name.split('d_')[1]
            if dspy == 'openexr':
                continue
            rman_icon = rfb_icons.get_icon(name='out_%s' % n, dflt='out_rmanDisplay')
            items.append((dspy, dspy, '', rman_icon.icon_id, i))
            i += 1
        return items

    displaydriver: EnumProperty(
        name="Display Driver",
        description="Display driver for rendering",
        items=displaydriver_items)

    dspy_channels_index: IntProperty(min=-1, default=-1)   
    dspy_channels: CollectionProperty(type=RendermanDspyChannelPointer, name="Display Channels") 

class RendermanRenderLayerSettings(bpy.types.PropertyGroup):

    use_renderman: BoolProperty(name="use_renderman", default=False)
    custom_aovs: CollectionProperty(type=RendermanAOV,
                                     name='Custom AOVs')
    custom_aov_index: IntProperty(min=-1, default=-1)
    dspy_channels: CollectionProperty(type=RendermanDspyChannel,
                                     name='Display Channels')                                          


classes = [
    RendermanRenderLayerSettings          
]

props_classes = [
    (RendermanDspyChannel, 'rman_properties_dspychan'),    
    (RendermanDspyChannelPointer, ''),
    (RendermanAOV, 'rman_properties_aov')
]

def register():

    from ...rfb_utils import register_utils  

    for cls,cfg_name in props_classes:
        if cfg_name:
            cls._add_properties(cls, cfg_name)
        register_utils.rman_register_class(cls)    

    register_utils.rman_register_classes(classes)

    bpy.types.ViewLayer.renderman = PointerProperty(
        type=RendermanRenderLayerSettings, name="Renderman RenderLayer Settings")           

def unregister():

    del bpy.types.ViewLayer.renderman

    from ...rfb_utils import register_utils      

    for cls,cfg_name in props_classes:       
        register_utils.rman_unregister_class(cls) 

    register_utils.rman_unregister_classes(classes)