from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty, IntVectorProperty

from ...rfb_utils import shadergraph_utils
from ...rfb_utils import scene_utils
from ...rfb_logger import rfb_log 
from ...rfb_utils.prefs_utils import using_qt
from ... import rman_config

import bpy

class RendermanBlColorRamp(bpy.types.PropertyGroup):
    rman_value: FloatVectorProperty(name="value",
                            default=(1.0, 1.0, 1.0, 1.0), size=4,
                            subtype="COLOR")
    position: FloatProperty(name="position", default=0.0)

class RendermanBlFloatRamp(bpy.types.PropertyGroup):
    rman_value: FloatProperty(name="value", default=0.0)
    position: FloatProperty(name="position", default=0.0)

class RendermanUserTokenGroup(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", default="")
    value: StringProperty(name="Value", default="")

class RendermanLightPointer(bpy.types.PropertyGroup):
    def validate_light_obj(self, ob):
        if shadergraph_utils.is_rman_light(ob, include_light_filters=True):
            return True
        return False

    name: StringProperty(name="name")
    light_ob: PointerProperty(type=bpy.types.Object, poll=validate_light_obj)               

class RendermanLightGroup(bpy.types.PropertyGroup):
    def update_name(self, context):
        for member in self.members:            
            member.light_ob.update_tag(refresh={'DATA'})

    def update_members_index(self, context):
        if self.members_index < 0:
            return        
        member = self.members[self.members_index]
        light_ob = member.light_ob
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        light_ob.select_set(True)
        context.view_layer.objects.active = light_ob        
        
    name: StringProperty(name="Group Name", update=update_name)
    members: CollectionProperty(type=RendermanLightPointer,
                                 name='Group Members')
    members_index: IntProperty(min=-1, default=-1,
                                 update=update_members_index) 

class RendermanObjectPointer(bpy.types.PropertyGroup):
    def update_name(self, context):
        if self.ob_pointer:
            self.ob_pointer.update_tag(refresh={'OBJECT'})        

    name: StringProperty(name="name", update=update_name)

    def update_ob_pointer(self, context):
        if not using_qt():
            self.ob_pointer.update_tag(refresh={'OBJECT'})

    ob_pointer: PointerProperty(type=bpy.types.Object, update=update_ob_pointer)   

    def update_link(self, context):
        light_ob = getattr(context, 'light_ob', None)
        if not light_ob or light_ob.type != 'LIGHT':
            return
        '''
        if not light_ob and hasattr(context, 'active_object'):
            light_ob = context.active_object
            if light_ob and light_ob.type != 'LIGHT':
                return
        if not light_ob:
            return
        '''

        ob = self.ob_pointer
        if scene_utils.set_lightlinking_properties(ob, light_ob, self.illuminate):
            if not using_qt():
                ob.update_tag(refresh={'DATA'}) 

    illuminate: EnumProperty(
        name="Illuminate",
        update=update_link,
        items=[
              ('DEFAULT', 'Default', ''),
               ('ON', 'On', ''),
               ('OFF', 'Off', '')])             

class RendermanVolumeAggregate(bpy.types.PropertyGroup):
    def update_name(self, context):
        for member in self.members:
            member.ob_pointer.update_tag(refresh={'OBJECT'})

    def update_members_index(self, context):
        if self.members_index < 0:
            return        
        member = self.members[self.members_index]
        ob = member.ob_pointer
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob                  

    name: StringProperty(name="Volume Aggregate Name", update=update_name)
    members: CollectionProperty(type=RendermanObjectPointer,
                                 name='Aggregate Members')
    members_index: IntProperty(min=-1, default=-1, update=update_members_index)

class RendermanGroup(bpy.types.PropertyGroup):
    def update_name(self, context):
        for member in self.members:
            member.ob_pointer.update_tag(refresh={'OBJECT'})

    def update_members_index(self, context):
        if self.members_index < 0:
            return        
        member = self.members[self.members_index]
        ob = member.ob_pointer
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob                  

    name: StringProperty(name="Group Name", update=update_name)
    members: CollectionProperty(type=RendermanObjectPointer,
                                 name='Group Members')
    members_index: IntProperty(min=-1, default=-1, update=update_members_index)


class LightLinking(bpy.types.PropertyGroup):

    def validate_light_obj(self, ob):
        if shadergraph_utils.is_rman_light(ob, include_light_filters=True):
            return True
        return False

    light_ob: PointerProperty(type=bpy.types.Object, poll=validate_light_obj)       

    members: CollectionProperty(type=RendermanObjectPointer,
                                 name='Group Members')    

    def update_members_index(self, context):
        if self.members_index < 0:
            return
        member = self.members[self.members_index]
        ob = member.ob_pointer
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob                                      

    members_index: IntProperty(min=-1, default=-1, update=update_members_index)                                      

class RendermanMeshPrimVar(bpy.types.PropertyGroup):
    name: StringProperty(
        name="Variable Name",
        description="Name of the exported renderman primitive variable")
    data_name: StringProperty(
        name="Data Name",
        description="Name of the Blender data to export as the primitive variable")
    data_source: EnumProperty(
        name="Data Source",
        description="Blender data type to export as the primitive variable",
        items=[('ATTRIBUTES', 'Attributes', ''),
               ('VERTEX_GROUP', 'Vertex Group', ''),
               ('VERTEX_COLOR', 'Vertex Color', ''),
               ('VERTEX_ATTR_COLOR', 'Vertex Attr Color', ''),
               ('UV_TEXTURE', 'UV Texture', '')
               ]
    )
    export_tangents: BoolProperty(
        name="Export Tangents",
        description="Export the tangent vectors for this UV Texture. The primvar name for this will be (Variable Name)_Tn and (Variable Name)_Bn, for the tangent and bitangent vectors, respectively",
        default=False
    )
class RendermanReferencePosePrimVars(bpy.types.PropertyGroup):

    has_Pref: BoolProperty(name='has_Pref', default=False)
    has_WPref: BoolProperty(name='has_WPref', default=False)
    has_Nref: BoolProperty(name='has_Nref', default=False)
    has_WNref: BoolProperty(name='has_WNref', default=False)    

    rman__Pref: FloatVectorProperty(name='rman__Pref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")

    rman__WPref: FloatVectorProperty(name='rman__WPref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")    
                                
    rman__Nref: FloatVectorProperty(name='rman__Nref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")    

    rman__WNref: FloatVectorProperty(name='rman__WNref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")        
    
class RendermanReferencePoseNormalsPrimVars(bpy.types.PropertyGroup):

    has_Nref: BoolProperty(name='has_Nref', default=False)
    has_WNref: BoolProperty(name='has_WNref', default=False)    

    rman__Nref: FloatVectorProperty(name='rman__Nref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")    

    rman__WNref: FloatVectorProperty(name='rman__WNref',
                                default=(0,0, 0), size=3,
                                subtype="XYZ")            

class RENDERMAN_UL_Array_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name)

class RendermanArrayGroup(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", default="")
    type: EnumProperty(name="Type",
        items=[
              ('float', 'float', ''),
               ('int', 'int', ''),
               ('string', 'string', ''),
               ('color', 'color', ''),
               ('vector', 'vector', ''),
               ('normal', 'normal', ''),
               ('point', 'point', '')
        ])

    value_float: FloatProperty(name="Value", default=0.0)
    value_int: IntProperty(name="Value", default=0)
    value_string: StringProperty(name="Value", default="")
    value_color: FloatVectorProperty(name="Value", default=(1.0,1.0,1.0), size=3, subtype="COLOR")
    value_vector: FloatVectorProperty(name="Value", default=(0.0,0.0,0.0), size=3, subtype="NONE")
    value_normal: FloatVectorProperty(name="Value", default=(0.0,0.0,0.0), size=3, subtype="NONE")
    value_point: FloatVectorProperty(name="Value", default=(0.0,0.0,0.0), size=3, subtype="XYZ")                                                            

class Tab_CollectionGroup(bpy.types.PropertyGroup):

    #################
    #       Tab     #
    #################

    bpy.types.Scene.rm_ipr = BoolProperty(
        name="IPR settings",
        description="Show some useful setting for the Interactive Rendering",
        default=False)

    bpy.types.Scene.rm_render = BoolProperty(
        name="Render settings",
        description="Show some useful setting for the Rendering",
        default=False)

    bpy.types.Scene.rm_render_external = BoolProperty(
        name="Render settings",
        description="Show some useful setting for external rendering",
        default=False)

    bpy.types.Scene.rm_help = BoolProperty(
        name="Help",
        description="Show some links about RenderMan and the documentation",
        default=False)

    bpy.types.Scene.rm_env = BoolProperty(
        name="Envlight",
        description="Show some settings about the selected Env light",
        default=False)

    bpy.types.Scene.rm_area = BoolProperty(
        name="AreaLight",
        description="Show some settings about the selected Area Light",
        default=False)

    bpy.types.Scene.rm_daylight = BoolProperty(
        name="DayLight",
        description="Show some settings about the selected Day Light",
        default=False)

    bpy.types.Scene.prm_cam = BoolProperty(
        name="Renderman Camera",
        description="Show some settings about the camera",
        default=False)        

classes = [      
    RendermanBlColorRamp,
    RendermanBlFloatRamp,
    RendermanUserTokenGroup,
    RendermanLightPointer,
    RendermanLightGroup,
    RendermanObjectPointer,
    RendermanGroup,
    RendermanVolumeAggregate,
    LightLinking,
    RendermanMeshPrimVar,   
    RendermanReferencePosePrimVars,
    RendermanReferencePoseNormalsPrimVars,
    Tab_CollectionGroup,
    RENDERMAN_UL_Array_List,
    RendermanArrayGroup
]

def register():

    from ...rfb_utils import register_utils

    register_utils.rman_register_classes(classes) 

def unregister():
    from ...rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)         