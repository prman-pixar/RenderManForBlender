from bpy.props import (StringProperty, BoolProperty, EnumProperty, PointerProperty)

from ...rfb_utils.draw_utils import draw_node_properties_recursive, get_open_close_icon
from ...rfb_utils import shadergraph_utils
from ...rfb_utils import object_utils
from ...rfb_logger import rfb_log
from ... import rfb_icons
from ...rman_operators.rman_operators_collections import return_empty_list   
from ...rman_config import __RFB_CONFIG_DICT__ as rfb_config
from ...rman_ui.rman_ui_base import PRManButtonsPanel 
from ...rman_constants import RMAN_STYLIZED_FILTERS, RMAN_STYLIZED_PATTERNS, RMAN_UTILITY_PATTERN_NAMES 
from ...rman_constants import RMAN_STYLIZED_XPU_FILTERS, BLENDER_VERSION_MAJOR, BLENDER_VERSION_MINOR 

import bpy
import re


class PRMAN_OT_Renderman_Open_Stylized_Help(bpy.types.Operator):
    bl_idname = "renderman.rman_stylized_help"
    bl_label = "Stylized Help" 
    bl_description = "Get help on how to use RenderMan Stylzied Looks"

    def execute(self, context):
        return{'FINISHED'}     

    def draw(self, context):
        layout = self.layout       
        box = layout.box()
        box.scale_y = 0.4
        rman_icon = rfb_icons.get_node_icon('PxrStylizedControl')
        box.label(text="RenderMan Stylized Looks HOWTO", icon_value = rman_icon.icon_id)
        rman_icon = rfb_icons.get_icon('help_stylized_1')
        box.template_icon(rman_icon.icon_id, scale=10.0)
        box.label(text="")
        box.label(text="To start using RenderMan Stylized Looks, click the Enable Stylized Looks.")
        box.label(text="")
        box.label(text="Stylized looks requires BOTH a stylized pattern node") 
        box.label(text="be connected in an object's shading material network")
        box.label(text="and one of the stylized display filters be present in the scene.")
        box.label(text="")
        box.label(text="In the RenderMan Stylized Editor, the Patterns tab allows you to")
        box.label(text="search for an object in the scene and attach a PxrStylizedControl pattern.")
        box.label(text="You can use the drop down list or use the eye dropper to select an object in the viewport.")
        box.label(text="If no material is present, a PxrSurface material will automatically be created for you.")
        box.label(text="The stylized pattern allows for per-object control.")
        box.label(text="")
        box.label(text="The Filters tab allows you to add one of the stylized display filters.")
        box.label(text="The filters can be turned on and off, individually.")
        box.label(text="As mentioned in earlier, both the patterns and the filters need to be present.")
        box.label(text="So you need to add at least one filter for the stylized looks to work.")       
        rman_help = rfb_icons.get_icon("rman_help")
        split = layout.split(factor=0.98)
        row = split.row()
        col = row.column()
        col = row.column()
        col.label(text="")        
        row.operator("wm.url_open", text="RenderMan Docs",
                        icon_value=rman_help.icon_id).url = "https://rmanwiki.pixar.com/display/RFB24"

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=500)  
    
class RendermanStylizedSettings(bpy.types.PropertyGroup):
    
    def validate_obj(self, ob):
        if ob.type in ['CAMERA', 'ARMATURE', 'LIGHT']:
            return False
        return True    
    selected_object: PointerProperty(name='Selected Object', 
                        type=bpy.types.Object,
                        poll=validate_obj)

    stylized_tabs: EnumProperty(
        name="",
        items=[
            ('patterns', 'Patterns', 'Add or edit stylized patterns attached to objects in the scene'),
            ('filters', 'Filters', 'Add or edit stylized display filters in the scene'),
        ]
    ) 

def draw_patterns_tab(context, layout, use_selected_objects=False): 
    scene = context.scene   
    rm = scene.renderman
    rm_stylized = scene.renderman_stylized        
   
    row = layout.row()
    row.separator()   

    # if use selected objects is true we only
    # show whether the current selected object is a stylized object
    if use_selected_objects:
        if context.selected_objects:
            ob = context.selected_objects[0]
            if ob:
                row = layout.row(align=True)
                col = row.column()
                col.label(text=ob.name)

                node = shadergraph_utils.has_stylized_pattern_node(ob)
                mat = object_utils.get_active_material(ob)
                if node and mat:
                    col.separator()
                    col.label(text=node.name)
                    col.separator()
                    draw_node_properties_recursive(layout, context, mat.node_tree, node, level=1, single_node_view=False)
                else:
                    col.context_pointer_set('selected_obj', ob)  
                    col.operator_menu_enum('node.rman_attach_stylized_pattern', 'stylized_pattern')                
    else:
        row.prop(rm_stylized, 'selected_object')
        if rm_stylized.selected_object:

            layout.separator()      

            row = layout.row(align=True)
            col = row.column()
            ob = rm_stylized.selected_object
            col.label(text=ob.name)
            node = shadergraph_utils.has_stylized_pattern_node(ob)
            if node:
                mat = object_utils.get_active_material(ob)
                col.separator()
                col.label(text=node.name)
                col.separator()
                draw_node_properties_recursive(layout, context, mat.node_tree, node, level=1, single_node_view=False)
            else:
                col.context_pointer_set('selected_obj', ob)             
                col.operator_menu_enum('node.rman_attach_stylized_pattern', 'stylized_pattern')                      

def draw_filters_tab(context, layout):
    scene = context.scene   
    world = scene.world
    nt = world.node_tree             
    rm_stylized = scene.renderman_stylized       
    is_xpu = scene.renderman.renderVariant == "xpu"
    
    row = layout.row(align=True)
    col = row.column()
    col.operator_menu_enum('node.rman_add_stylized_filter', 'filter_name')            

    layout.separator()  
    output = shadergraph_utils.find_node(world, 'RendermanDisplayfiltersOutputNode')
    layout.separator()        
    rm = world.renderman
    nt = world.node_tree      
    row = layout.row(align=True)
    row.label(text="Display Filters")
    if not output:
        split = layout.split()
        row = split.row()           
        row.label(text="No Stylized Display Filters", icon="ERROR")
    col = row.column()
    if output:
        for i, socket in enumerate(output.inputs):
            if not socket.is_linked:
                continue
            link = socket.links[0]
            node = link.from_node       
            if node.bl_label not in  RMAN_STYLIZED_FILTERS + RMAN_STYLIZED_XPU_FILTERS:
                continue
            split = layout.split()
            row = split.row()
            col = row.column()                 
            icon = get_open_close_icon(not node.hide)           
            col.prop(node, "hide", icon=icon, icon_only=True, invert_checkbox=True, emboss=False)         
            col = row.column()
            col.label(text=node.name)

            if socket.is_linked:
                col = row.column()
                col.enabled = (i != 0)
                col.context_pointer_set("node", output)
                col.context_pointer_set("nodetree", nt)
                col.context_pointer_set("socket", socket)             
                op = col.operator("node.rman_move_displayfilter_node_up", text="", icon="TRIA_UP")
                op.index = i
                col = row.column()
                col.context_pointer_set("node", output)
                col.context_pointer_set("nodetree", nt)
                col.context_pointer_set("socket", socket)             
                col.enabled = (i != len(output.inputs)-1)
                op = col.operator("node.rman_move_displayfilter_node_down", text="", icon="TRIA_DOWN")
                op.index = i

                col = row.column()
                col.context_pointer_set("node", output)
                col.context_pointer_set("nodetree", nt)
                col.context_pointer_set("socket", socket)                 
                op = col.operator("node.rman_remove_displayfilter_node_socket", text="", icon="REMOVE")
                op.index = i     
                op.do_delete = True                
                        
            if node.hide is False:
                layout.prop(node, "is_active")
                if node.is_active:             
                    draw_node_properties_recursive(layout, context, nt, node, level=1)         

    if not is_xpu:
        return        

    output = shadergraph_utils.find_node(world, 'RendermanSamplefiltersOutputNode')
    layout.separator()         
    row = layout.row(align=True)
    row.label(text="Sample Filters")
    if not output:
        split = layout.split()
        row = split.row()    
        row.label(text="No Stylized Sample Filters", icon="ERROR")    
    col = row.column()

    if output:
        for i, socket in enumerate(output.inputs):
            if not socket.is_linked:
                continue
            link = socket.links[0]
            node = link.from_node       
            if node.bl_label not in  RMAN_STYLIZED_FILTERS + RMAN_STYLIZED_XPU_FILTERS:
                continue
            split = layout.split()
            row = split.row()
            col = row.column()                 
            icon = get_open_close_icon(not node.hide)           
            col.prop(node, "hide", icon=icon, icon_only=True, invert_checkbox=True, emboss=False)         
            col = row.column()
            col.label(text=node.name)

            if socket.is_linked:
                col = row.column()
                col.enabled = (i != 0)
                col.context_pointer_set("node", output)
                col.context_pointer_set("nodetree", nt)
                col.context_pointer_set("socket", socket)             
                op = col.operator("node.rman_move_samplefilter_node_up", text="", icon="TRIA_UP")
                op.index = i
                col = row.column()
                col.context_pointer_set("node", output)
                col.context_pointer_set("nodetree", nt)
                col.context_pointer_set("socket", socket)             
                col.enabled = (i != len(output.inputs)-1)
                op = col.operator("node.rman_move_samplefilter_node_down", text="", icon="TRIA_DOWN")
                op.index = i

                col = row.column()
                col.context_pointer_set("node", output)
                col.context_pointer_set("nodetree", nt)
                col.context_pointer_set("socket", socket)                 
                op = col.operator("node.rman_remove_samplefilter_node_socket", text="", icon="REMOVE")
                op.index = i                   
                        
            if node.hide is False:
                layout.prop(node, "is_active")
                if node.is_active:             
                    draw_node_properties_recursive(layout, context, nt, node, level=1)                         


def draw_stylized(context, layout, use_selected_objects=False):

    scene = context.scene 
    rm = scene.renderman   
    rm_stylized = scene.renderman_stylized      
    split = layout.split()
    row = split.row()
    col = row.column()
    col.prop(rm, 'render_rman_stylized', text='Enable Stylized Looks')
    col = row.column()
    icon = rfb_icons.get_icon('rman_help')
    col.operator("renderman.rman_stylized_help", text="", icon_value=icon.icon_id)
    if not rm.render_rman_stylized:
        return

    row = layout.row(align=True)
    row.prop_tabs_enum(rm_stylized, 'stylized_tabs', icon_only=False)

    if rm_stylized.stylized_tabs == "patterns":
        draw_patterns_tab(context, layout, use_selected_objects=use_selected_objects)
    else:
        draw_filters_tab(context, layout)

class PRMAN_OT_Renderman_Open_Stylized_Editor(bpy.types.Operator):

    bl_idname = "scene.rman_open_stylized_editor"
    bl_label = "RenderMan Stylized Editor"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine in {'PRMAN_RENDER'} 
         
    def execute(self, context):
        return{'FINISHED'}   

    def draw(self, context):

        layout = self.layout  
        draw_stylized(context, layout)
        
    def cancel(self, context):
        if self.event and self.event.type == 'LEFTMOUSE':
            bpy.ops.scene.rman_open_stylized_editor('INVOKE_DEFAULT')
            
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = None

    def invoke(self, context, event):
        wm = context.window_manager
        width = rfb_config['editor_preferences']['stylizedlooks_editor']['width']
        self.event = event
        return wm.invoke_props_dialog(self, width=width)
    
class PRMAN_PT_Renderman_Stylized_Panel(PRManButtonsPanel, bpy.types.Panel):
    bl_label = "RenderMan Stylized Looks"
    bl_context = "scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):

        layout = self.layout  
        draw_stylized(context, layout, use_selected_objects=True)
  

classes = [
    PRMAN_OT_Renderman_Open_Stylized_Help,
    PRMAN_OT_Renderman_Open_Stylized_Editor,
    RendermanStylizedSettings,
    PRMAN_PT_Renderman_Stylized_Panel
]

def register():
    from ...rfb_utils import register_utils

    register_utils.rman_register_classes(classes)

    bpy.types.Scene.renderman_stylized = PointerProperty(
        type=RendermanStylizedSettings, name="Renderman Stylized Settings")       

def unregister():
    from ...rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)                              