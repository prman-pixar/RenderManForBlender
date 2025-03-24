from bpy.props import (StringProperty, BoolProperty, EnumProperty)

from ...rfb_utils.draw_utils import draw_node_properties_recursive
from ...rfb_utils import shadergraph_utils
from ...rfb_utils import object_utils
from ...rfb_logger import rfb_log
from ... import rfb_icons
from ...rman_operators.rman_operators_collections import return_empty_list   
from ...rman_config import __RFB_CONFIG_DICT__ as rfb_config
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
        box.label(text="You can use the drop down list or do a filter search to select the object you want to stylized.")
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

class PRMAN_OT_Renderman_Open_Stylized_Editor(bpy.types.Operator):

    bl_idname = "scene.rman_open_stylized_editor"
    bl_label = "RenderMan Stylized Editor"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine in {'PRMAN_RENDER'} 

    def updated_object_selected_name(self, context):
        ob = context.scene.objects.get(self.selected_obj_name, None)
        if not ob:
            return
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob       

    def obj_list_items(self, context):
        pattern = re.compile(self.object_search_filter)        
        scene = context.scene
        rm = scene.renderman

        if self.do_object_filter and self.object_search_filter == '':
            return return_empty_list(label='No Objects Found')        

        items = []
        for ob in context.scene.objects:
            if ob.type in ['LIGHT', 'CAMERA']:
                continue

            mat = object_utils.get_active_material(ob)
            if not mat:
                items.append((ob.name, ob.name, ''))
                continue

            if not shadergraph_utils.is_renderman_nodetree(mat):
                items.append((ob.name, ob.name, ''))
                continue

            if self.do_object_filter and not re.match(pattern, ob.name):
                continue
            if not shadergraph_utils.has_stylized_pattern_node(ob):
                items.append((ob.name, ob.name, ''))
        if not items:
            return return_empty_list(label='No Objects Found')               
        elif self.do_object_filter:
            items.insert(0, ('0', 'Results (%d)' % len(items), '', '', 0))
        else:
            items.insert(0, ('0', 'Select Object', '', '', 0))
        return items  

    def update_do_object_filter(self, context):
        self.selected_obj_name = '0'            

    do_object_filter: BoolProperty(name="Object Filter", 
                                description="Search and add multiple objects",
                                default=False,
                                update=update_do_object_filter)    
    object_search_filter: StringProperty(name="Object Filter Search", default="")       
    selected_obj_name: EnumProperty(name="", items=obj_list_items, update=updated_object_selected_name)    

    def current_filters(self, context):
        items = []
        scene = context.scene   
        world = scene.world
        nt = world.node_tree

        nodes = shadergraph_utils.find_all_stylized_filters(world)

        for node in nodes:
            items.append((node.name, node.name, ""))

        if len(items) < 1:
            items.append(('0', '', '', '', 0))

        return items  

    stylized_filter: EnumProperty(
        name="",
        items=current_filters
    )    

    stylized_tabs: EnumProperty(
        name="",
        items=[
            ('patterns', 'Patterns', 'Add or edit stylized patterns attached to objects in the scene'),
            ('filters', 'Filters', 'Add or edit stylized display filters in the scene'),
        ]
    )

    def get_stylized_objects(self, context):
        items = []
        scene = context.scene 
        for ob in scene.objects:
            node = shadergraph_utils.has_stylized_pattern_node(ob)
            if node:
                items.append((ob.name, ob.name, ''))

        if len(items) < 1:
            items.append(('0', '', '', '', 0))                

        return items      

    stylized_objects: EnumProperty(
        name="",
        items=get_stylized_objects
    )
         
    def execute(self, context):
        return{'FINISHED'}   


    def draw_patterns_tab(self, context): 
        scene = context.scene   
        rm = scene.renderman
        selected_objects = context.selected_objects        

        layout = self.layout           

        row = layout.row()
        row.separator()   

        row.prop(self, 'do_object_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_object_filter:
            row.prop(self, 'selected_obj_name', text='')
            col = row.column()

            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                pass
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])  
                col.operator_menu_enum('node.rman_attach_stylized_pattern', 'stylized_pattern')                

        else:
            row.prop(self, 'object_search_filter', text='', icon='VIEWZOOM')
            row = layout.row()  
            row.prop(self, 'selected_obj_name')
            col = row.column()

            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                pass
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])             
                col.operator_menu_enum('node.rman_attach_stylized_pattern', 'stylized_pattern')            

        if self.properties.stylized_objects != '0':                

            layout.separator()
            row = layout.row(align=True)
            col = row.column()
            col.label(text='Stylized Objects')           

            row = layout.row(align=True)
            col = row.column()
            col.prop(self, 'stylized_objects')

            ob = scene.objects.get(self.properties.stylized_objects, None)
            node = shadergraph_utils.has_stylized_pattern_node(ob)
            mat = object_utils.get_active_material(ob)
            col.separator()
            col.label(text=node.name)
            col.separator()
            draw_node_properties_recursive(layout, context, mat.node_tree, node, level=1, single_node_view=False)

    def draw_filters_tab(self, context):
        scene = context.scene   
        world = scene.world
        nt = world.node_tree             
        layout = self.layout            
        
        row = layout.row(align=True)
        col = row.column()
        col.context_pointer_set('op_ptr', self) 
        col.operator_menu_enum('node.rman_add_stylized_filter', 'filter_name')            

        layout.separator()  
        output = shadergraph_utils.find_node(world, 'RendermanDisplayfiltersOutputNode')
        if not output:
            row = layout.row()
            row.label(text="No Stylized Filters")
            return 

        layout.separator()
        row = layout.row()
        row.label(text="Scene Filters")            
        row = layout.row()

        layout.prop(self, 'stylized_filter')
        selected_stylized_node = None
        if self.properties.stylized_filter != '':
            nodes = shadergraph_utils.find_all_stylized_filters(world)
            for node in nodes:
                if node.name == self.properties.stylized_filter:
                    selected_stylized_node = node
                    break
        
        if selected_stylized_node:
            rman_icon = rfb_icons.get_displayfilter_icon(node.bl_label) 
            layout.prop(selected_stylized_node, "is_active")
            layout.prop(node, 'name')
            if selected_stylized_node.is_active:
                draw_node_properties_recursive(layout, context, nt, selected_stylized_node, level=1, single_node_view=False)             

    def draw(self, context):

        layout = self.layout  
        scene = context.scene 
        rm = scene.renderman         
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
        row.prop_tabs_enum(self, 'stylized_tabs', icon_only=False)

        if self.properties.stylized_tabs == "patterns":
            self.draw_patterns_tab(context)
        else:
            self.draw_filters_tab(context)
        
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

classes = [
    PRMAN_OT_Renderman_Open_Stylized_Help,
    PRMAN_OT_Renderman_Open_Stylized_Editor
]

def register():
    from ...rfb_utils import register_utils

    register_utils.rman_register_classes(classes)

def unregister():
    from ...rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)                              