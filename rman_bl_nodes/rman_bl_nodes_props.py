import bpy
from bpy.props import PointerProperty, StringProperty, BoolProperty, \
    EnumProperty, IntProperty, IntVectorProperty, FloatProperty, FloatVectorProperty, \
    CollectionProperty, BoolVectorProperty
from .. import rman_bl_nodes
from .. import rfb_icons
from ..rfb_utils.shadergraph_utils import is_renderman_nodetree
from ..rfb_utils import shadergraph_utils
from ..rman_constants import RMAN_AREA_LIGHT_TYPES

class RENDERMAN_UL_Dspy_MetaData_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name)

class RendermanDspyMetaGroup(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", default="")
    type: EnumProperty(name="Type",
        items=[
              ('float', 'float', ''),
               ('int', 'int', ''),
               ('string', 'string', ''),
               ('v2f', 'v2f', ''),
               ('v2i', 'v2i', ''),
               ('v3f', 'v3f', ''),
               ('v3i', 'v3i', ''),
               ('box2f', 'box2f', ''),
               ('box2i', 'box2i', ''),
               ('m33f', 'm33f', ''),
               ('m44f', 'm44f', '')])

    value_float: FloatProperty(name="Value", default=0.0)
    value_int: IntProperty(name="Value", default=0)
    value_string: StringProperty(name="Value", default="")
    value_v2f: FloatVectorProperty(name="Value", size=2, default=(0.0, 0.0))
    value_v3f: FloatVectorProperty(name="Value", size=3, default=(0.0, 0.0, 0.0))
    value_v2i: IntVectorProperty(name="Value", size=2, default=(0, 0))
    value_v3i: IntVectorProperty(name="Value", size=3, default=(0, 0, 0))
    value_box2f: FloatVectorProperty(name="Value", size=4, default=(0.0, 0.0, 0.0, 0.0))
    value_box2i: IntVectorProperty(name="Value", size=4, default=(0, 0, 0, 0))
    value_m33f: FloatVectorProperty(name="Value", size=9, default=[0.0]*9)
    value_m44f: FloatVectorProperty(name="Value", size=16, default=[0.0]*16)    

class RendermanPluginSettings(bpy.types.PropertyGroup):
    pass

class RendermanLightFilter(bpy.types.PropertyGroup):

    def get_name(self):
        if self.linked_filter_ob:
            return self.linked_filter_ob.name
        return ''    

    name: StringProperty(default='', get=get_name)

    def update_linked_filter_ob(self, context):
        pass          

    def validate_obj(self, ob):
        if ob.type == 'LIGHT' and ob.data.renderman.renderman_light_role == 'RMAN_LIGHTFILTER':
            return True
        return False
    
    linked_filter_ob: PointerProperty(name='Light Filter', 
                        description='Light Filter',
                        type=bpy.types.Object,
                        update=update_linked_filter_ob,
                        poll=validate_obj
                        )    

class RendermanPortalLightPointer(bpy.types.PropertyGroup):

    def get_name(self):
        if self.linked_portal_ob:
            return self.linked_portal_ob.name
        return ''

    name: StringProperty(default='', get=get_name)

    def update_linked_portal_ob(self, context):
        if self.linked_portal_ob:     
            self.linked_portal_ob.update_tag(refresh={'DATA'})        

    def validate_obj(self, ob):        
        if ob.type == 'LIGHT':
            rm = ob.data.renderman
            if rm.renderman_light_role == 'RMAN_LIGHT' and rm.get_light_node_name() == 'PxrPortalLight':              
                return True
        return False
    
    linked_portal_ob: PointerProperty(name='Portal Light', 
                        description='Portal Light',
                        type=bpy.types.Object,
                        update=update_linked_portal_ob,
                        poll=validate_obj
                        )                            

class RendermanLightSettings(bpy.types.PropertyGroup):

    def get_light_node(self):
        '''
        Get the light shader node
        '''
        light = self.id_data
        output = None
        nt = light.node_tree
        if not nt:
            return None
        output = is_renderman_nodetree(light)

        if not output:
            return None

        if self.renderman_light_role == 'RMAN_LIGHT':
            socket = output.inputs[1]
            if socket.is_linked:
                return socket.links[0].from_node
        else:
            socket = output.inputs[3]
            if socket.is_linked:
                return socket.links[0].from_node    

        return None        

    def get_light_node_name(self):
        '''
        Get light shader name
        '''
        node = self.get_light_node()
        if node:
            return node.bl_label
        return ''

    light_node: StringProperty(
        name="Light Node",
        default='')

    def update_vis(self, context):
        light = self.id_data

    use_renderman_node: BoolProperty(
        name="Use RenderMans Light Node",
        description="Will enable RenderMan light Nodes, opening more options",
        default=False
    )

    def renderman_light_role_update(self, context):
        if self.renderman_light_role == 'RMAN_LIGHT':
            self.renderman_light_shader_update(context)
        else:
            self.renderman_light_filter_shader_update(context)

    renderman_light_role: EnumProperty(
        name="Light Type",
        items=[('RMAN_LIGHT', 'Light', 'RenderMan Light'),
               ('RMAN_LIGHTFILTER', 'Filter', 'RenderMan Light Filter')],
        update=renderman_light_role_update,
        default='RMAN_LIGHT'        
    )    

    def renderman_light_shader_update(self, context):
        light = self.id_data      
        light_shader = self.get_light_node_name()
          
        if hasattr(light, 'size'):
            light.size = 0.0

        if light_shader not in RMAN_AREA_LIGHT_TYPES:
            light.type = 'POINT'

    def get_rman_light_shaders(self, context):
        items = []
        i = 0
        rman_light_icon = rfb_icons.get_light_icon("PxrRectLight")
        items.append(('PxrRectLight', 'PxrRectLight', '', rman_light_icon.icon_id, i))
        for n in rman_bl_nodes.__RMAN_LIGHT_NODES__:
            if n.name != 'PxrRectLight':
                i += 1
                light_icon = rfb_icons.get_light_icon(n.name)
                items.append( (n.name, n.name, '', light_icon.icon_id, i))
        return items

    renderman_light_shader: EnumProperty(
        name="RenderMan Light",
        items=get_rman_light_shaders,
        update=renderman_light_shader_update
    )

    def renderman_light_filter_shader_update(self, context):
        light = self.id_data
        light_shader = self.get_light_node_name()

        if hasattr(light, 'size'):
            light.size = 0.0
        light.type = 'POINT'
          
    def get_rman_light_filter_shaders(self, context):
        items = []
        i = 0
        rman_light_icon = rfb_icons.get_lightfilter_icon("_PxrRodLightFilter")
        items.append(('PxrRodLightFilter', 'PxrRodLightFilter', '', rman_light_icon.icon_id, i))
        for n in rman_bl_nodes.__RMAN_LIGHTFILTER_NODES__:
            if n.name not in ['PxrRodLightFilter', 'PxrBlockerLightFilter', 'PxrGoboLightFilter']:
                i += 1
                light_icon = rfb_icons.get_lightfilter_icon(n.name)
                items.append( (n.name, n.name, '', light_icon.icon_id, i))
        return items        

    renderman_light_filter_shader: EnumProperty(
        name="RenderMan Light Filter",
        items=get_rman_light_filter_shaders,
        update=renderman_light_filter_shader_update
    )    

    light_filters: CollectionProperty(
        type=RendermanLightFilter
    )
    light_filters_index: IntProperty(min=-1, default=-1)

    portal_lights: CollectionProperty(type=RendermanPortalLightPointer)

    def update_portal_lights_index(self, context):
        if self.portal_lights_index < 0:
            return

        if self.portal_lights_index > len(self.portal_lights) - 1:
            return

        portal_ptr = self.portal_lights[self.portal_lights_index]
        if not portal_ptr.linked_portal_ob:
            self.portal_lights.remove(self.portal_lights_index)
            self.portal_lights_index = -1
        

    portal_lights_index: IntProperty(min=-1, default=-1, update=update_portal_lights_index)

    def update_dome_light_portal(self, context):       
        if self.dome_light_portal:
            candidate = None
            dome_light = self.dome_light_portal
            rm = dome_light.data.renderman
            for portal_ptr in rm.portal_lights:
                if not portal_ptr.linked_portal_ob:
                    candidate = portal_ptr
                    break

            if not candidate:
                candidate = rm.portal_lights.add()
            ob = context.object
            candidate.linked_portal_ob = ob
            self.dome_light_portal.update_tag(refresh={'DATA'})
            ob.update_tag(refresh={'DATA'})
        else:
            # try and remove the portal light on the dome light
            for obj in bpy.data.objects:
                if not obj.type == 'LIGHT':
                    continue
                rm = obj.data.renderman
                if rm.get_light_node_name() != 'PxrDomeLight':
                    continue
                if len(rm.portal_lights) < 1:
                    continue
                for i, portal_ptr in enumerate(rm.portal_lights):
                    if not portal_ptr.linked_portal_ob:
                        continue
                    portal = portal_ptr.linked_portal_ob
                    rm = portal.data.renderman
                    if not rm.dome_light_portal:
                        portal_ptr.linked_portal_ob = None
                        setattr(rm, 'portal_lights_index', i)
        
    def validate_dome_light(self, ob):        
        if ob.type == 'LIGHT':
            rm = ob.data.renderman
            if rm.renderman_light_role == 'RMAN_LIGHT' and rm.get_light_node_name() == 'PxrDomeLight':              
                return True
        return False    

    dome_light_portal: PointerProperty(name="Dome Light",
                                    type=bpy.types.Object,
                                    description="Dome light to parent this portal light to.",
                                    poll=validate_dome_light,
                                    update=update_dome_light_portal)

    rman_coneAngleDepth: FloatProperty(name="Cone Angle Depth",
                                        default=5.0,
                                        min=0.0,
                                        max=10.0,                                
                                        precision=3,
                                        description="The depth of the cone angle drawn in the viewport"
    )

    rman_coneAngleOpacity: FloatProperty(name="Cone Angle Opacity",
                                        default=0.5,
                                        min=0.1,
                                        max=1.0,                                
                                        precision=3,
                                        description="The opaqueness of the cone angle drawn in the viewport"
    )    

    def get_vp_scale(self):
        from ..rman_config import __RFB_CONFIG_DICT__ as rfb_config

        nm = self.get_light_node_name()
        val = self.get('rman_vp_scale', 1.0)        
        scale = rfb_config['vp_light_scale'].get(nm, {'scale': 1.0})["scale"]
        return val * scale

    rman_vp_scale: FloatProperty(name="Viewport Scale",
                                        default=1.0,
                                        min=1.0,
                                        max=100.0,                                
                                        precision=3,
                                        description="Scale of the drawing of the light in the viewport. This is useful for scaling infinite lights, such as PxrDomeLight. Does not affect the size of the light in the renderer."
    )    

    rman_vp_draw_texture: BoolProperty(
        name="Draw Texture",
        description="If on, draw the light as textured light in the viewport. Note, the 'Draw Textured Lights' pref takes precedence over this control.",
        default=True)

    light_primary_visibility: BoolProperty(
        name="Light Primary Visibility",
        description="Camera visibility for this light",
        update=update_vis,
        default=True)


    mute: BoolProperty(
        name="Mute",
        description="Turn off this light",
        default=False)

    def update_solo(self, context):
        light = self.id_data
        scene = context.scene

        # if the scene solo is on already find the old one and turn off
        scene.renderman.solo_light = self.solo
        if self.solo:
            if scene.renderman.solo_light:
                for ob in scene.objects:
                    if shadergraph_utils.is_rman_light(ob, include_light_filters=False):
                        rm = shadergraph_utils.get_rman_light_properties_group(ob)
                        if rm != self and rm.solo:
                            rm.solo = False
                            break

    solo: BoolProperty(
        name="Solo",
        update=update_solo,
        description="Turn on only this light",
        default=False)

    renderman_lock_light_type: BoolProperty(
        name="Lock Type",
        default=False,
        description="Lock from changing light shader and light role."
    )

    linkingGroups: StringProperty(
        name="linkingGroups",
        default = "",
        description="What linking groups this light filter belongs to. These work in conjunction to the 'lightfilter:subset' attrbiute"
    )

    # OLD PROPERTIES

    shadingrate: FloatProperty(
        name="Light Shading Rate",
        description="Shading Rate for lights.  Keep this high unless banding or pixellation occurs on detailed light maps",
        default=100.0)

    # illuminate
    illuminates_by_default: BoolProperty(
        name="Illuminates by default",
        description="The light illuminates objects by default",
        default=True)    

    renderman_type: EnumProperty(
        name="Light Type",
        items=[
               ('AREA', 'Light', 'Area Light'),
               ('ENV', 'Dome', 'Dome Light'),
               ('SKY', 'Env Daylight', 'Simulated Sky'),
               ('DIST', 'Distant', 'Distant Light'),
               ('SPOT', 'Spot', 'Spot Light'),
               ('POINT', 'Point', 'Point Light'),
               ('PORTAL', 'Portal', 'Portal Light'),
               ('FILTER', 'Filter', 'RenderMan Light Filter'),
               ('UPDATED', 'UPDATED', '')],
        default='UPDATED'
    )

    area_shape: EnumProperty(
        name="Area Shape",
        items=[('rect', 'Rectangle', 'Rectangle'),
               ('disk', 'Disk', 'Disk'),
               ('sphere', 'Sphere', 'Sphere'), 
               ('cylinder', 'Cylinder', 'Cylinder')],
        default='rect'
    )

    filter_type: EnumProperty(
        name="Area Shape",
        items=[('barn', 'Barn', 'Barn'),
               ('blocker', 'Blocker', 'Blocker'),
               #('combiner', 'Combiner', 'Combiner'),
               ('cookie', 'Cookie', 'Cookie'),
               ('gobo', 'Gobo', 'Gobo'),
               ('intmult', 'Multiply', 'Multiply'),
               ('ramp', 'Ramp', 'Ramp'),
               ('rod', 'Rod', 'Rod')
               ],
        default='blocker'
    )        

class RendermanDisplayFilterSettings(bpy.types.PropertyGroup):

    def get_filter_name(self):
        return self.filter_type.replace('_settings', '')

    def get_filter_node(self):
        return getattr(self, self.filter_type + '_settings')

    def displayfilter_items(self, context):
        items = []
        for n in rman_bl_nodes.__RMAN_DISPLAYFILTER_NODES__ :
            items.append((n.name, n.name, ''))
        return items        

    filter_type: EnumProperty(items=displayfilter_items, name='Filter')


class RendermanSampleFilterSettings(bpy.types.PropertyGroup):

    def get_filter_name(self):
        return self.filter_type.replace('_settings', '')

    def get_filter_node(self):
        return getattr(self, self.filter_type + '_settings')

    def samplefilter_items(self, context):
        items = []
        for n in rman_bl_nodes.__RMAN_SAMPLEFILTER_NODES__ :
            items.append((n.name, n.name, ''))
        return items               

    filter_type: EnumProperty(items=samplefilter_items, name='Filter')

classes = [
           RENDERMAN_UL_Dspy_MetaData_List,
           RendermanDspyMetaGroup,
           RendermanLightFilter,
           RendermanPortalLightPointer,
           RendermanLightSettings,
           RendermanPluginSettings,
           RendermanDisplayFilterSettings,
           RendermanSampleFilterSettings
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes)

    bpy.types.Light.renderman = PointerProperty(
        type=RendermanLightSettings, name="Renderman Light Settings")
    # light settings for mesh lights, that are a part of a material   
    bpy.types.Material.renderman_light = PointerProperty(
        type=RendermanLightSettings, name="Renderman Light Settings")        

def unregister():
    from ..rfb_utils import register_utils
    
    register_utils.rman_unregister_classes(classes) 
