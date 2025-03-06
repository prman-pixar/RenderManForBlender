from .rman_ui_base import _RManPanelHeader,ShaderPanel,ShaderNodePanel, CollectionPanel 
from ..rfb_utils.shadergraph_utils import is_renderman_nodetree, gather_nodes, find_node_pointer
from ..rfb_utils.draw_utils import panel_node_draw,draw_nodes_properties_ui,draw_node_properties_recursive
from ..rfb_utils.draw_utils import show_node_sticky_params, show_node_match_params
from ..rfb_utils.prefs_utils import get_pref
from ..rman_cycles_convert import do_cycles_convert
from .. import rfb_icons
from ..rman_render import RmanRender
import bpy
from bpy.types import Panel

class MATERIAL_PT_renderman_preview(ShaderPanel, Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_options = {'DEFAULT_CLOSED'}
    bl_context = "material"
    bl_label = "Preview"

    @classmethod
    def poll(cls, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return        
        mat = getattr(context, 'material', None)
        if not mat:
            return False        
        rr = RmanRender.get_rman_render()
        if rr.rman_context.is_interactive_running():
            return False    
        return get_pref('rman_do_preview_renders', False)

    def draw(self, context):
        layout = self.layout
        mat = context.material
        row = layout.row()

        if mat:
            row.template_preview(context.material, show_buttons=1)

        layout.separator()
        split = layout.split()

        col = split.column(align=True)
        col.label(text="Viewport Color:")
        col.prop(mat, "diffuse_color", text="")

        col = split.column(align=True)
        col.label(text="Viewport Specular:")
        col.prop(mat, "specular_color", text="")
        #FIXME col.prop(mat, "specular_hardness", text="Hardness")

class MATERIAL_PT_renderman_material_refresh(ShaderPanel, Panel):
    bl_context = "material"
    bl_label = "Refresh"   

    @classmethod
    def poll(cls, context):
        mat = getattr(context, 'material', None)
        if not mat:
            return False
        rr = RmanRender.get_rman_render()
        if not rr.rman_context.is_live_rendering():
            return False
        if rr.rman_context.is_swatch_rendering():
            return False
        return True

    def draw(self, context):
        mat = context.material
        layout = self.layout
        rr = RmanRender.get_rman_render()
        if rr.rman_context.is_live_rendering():
            layout.context_pointer_set("material", mat)
            layout.operator("node.rman_force_material_refresh", text='Force Refresh')

class DATA_PT_renderman_light_refresh(ShaderPanel, Panel):
    bl_context = "data"
    bl_label = "Refresh"

    @classmethod
    def poll(cls, context):
        light = getattr(context, 'light', None)
        if not light:
            return False
        rr = RmanRender.get_rman_render()
        if not rr.rman_context.is_live_rendering():
            return False
        if rr.rman_context.is_swatch_rendering():
            return False            
        return True    

    def draw(self, context):
        layout = self.layout
        light = getattr(context, 'light', None)
        if not light:
            return False
        rr = RmanRender.get_rman_render()
        if light.renderman.renderman_light_role == 'RMAN_LIGHT':
            layout.context_pointer_set("light", light)
            layout.operator("node.rman_force_light_refresh", text='Force Refresh')
        else:
            layout.context_pointer_set("light_filter", light)
            layout.operator("node.rman_force_lightfilter_refresh", text='Force Refresh')

class MATERIAL_PT_renderman_shader_surface(ShaderPanel, Panel):
    bl_context = "material"
    bl_label = "Bxdf"
    shader_type = 'Bxdf'

    def draw(self, context):
        mat = context.material
        layout = self.layout
        if context.material.renderman and context.material.node_tree:
            nt = context.material.node_tree
            rman_output_node = is_renderman_nodetree(mat)

            if rman_output_node:             
                if rman_output_node.solo_node_pointer != '':
                    solo_node, solo_nt = find_node_pointer(nt, rman_output_node.solo_node_pointer)
                    if solo_node:

                        split = layout.split(factor=0.25)
                        split.context_pointer_set("nodetree", solo_nt)  
                        split.context_pointer_set("node", rman_output_node)  
                        rman_icon = rfb_icons.get_icon('rman_solo_on')   
                        split.label(text=solo_node.name , icon_value=rman_icon.icon_id)  
                        
                        split = split.split(factor=0.95)
                        split.menu('NODE_MT_renderman_node_solo_output_menu', text='Select Output')
                        op = split.operator('node.rman_set_node_solo', text='', icon='FILE_REFRESH')
                        op.refresh_solo = True 
                        layout.separator()
                        
                        layout.separator()
                        draw_node_properties_recursive(layout, context, nt, solo_node, level=0)
                        return 

                # Filter Toggle
                split = layout.split(factor=0.05)
                col = split.column()
                filter_icon = 'FILTER'
                filter_parameters = getattr(rman_output_node, 'bxdf_filter_parameters', False)
                filter_method = getattr(rman_output_node, 'bxdf_filter_method', 'NONE')
                col.context_pointer_set('node', rman_output_node)
                pressed = filter_parameters
                op = col.operator('node.rman_toggle_filter_params', depress=pressed, icon=filter_icon, text='')
                op.prop_name = 'bxdf_filter_parameters'

                if filter_parameters:
                    col = split.column()
                    col.prop(rman_output_node, 'bxdf_filter_method', text='')

                    if filter_method == 'MATCH':
                        col = split.column()
                        col.prop(rman_output_node, 'bxdf_match_expression', text='') 
                        col = split.column() 
                        col.prop(rman_output_node, 'bxdf_match_on', text='')    
                    else:
                        col = split.column()
                        col = split.column()                      

                layout.separator()
                input_name = 'bxdf_in'
                if not rman_output_node.inputs[input_name].is_linked:
                    panel_node_draw(layout, context, mat,
                                    'RendermanOutputNode', 'Bxdf')  
                elif not filter_parameters or filter_method == 'NONE':
                    panel_node_draw(layout, context, mat,
                                    'RendermanOutputNode', 'Bxdf')                      
                elif filter_method == 'STICKY':
                    bxdf_node = rman_output_node.inputs[input_name].links[0].from_node
                    nodes = gather_nodes(bxdf_node)
                    for node in nodes:
                        prop_names = getattr(node, 'prop_names', list())
                        show_node_sticky_params(layout, node, prop_names, context, nt, rman_output_node)   
                elif filter_method == 'MATCH':
                    expr = rman_output_node.bxdf_match_expression
                    if expr == '':
                        return
                    bxdf_node = rman_output_node.inputs[input_name].links[0].from_node
                    nodes = gather_nodes(bxdf_node)
                    for node in nodes:
                        prop_names = getattr(node, 'prop_names', list())
                        show_node_match_params(layout, node, expr, rman_output_node.bxdf_match_on,
                                            prop_names, context, nt)      
                else:   
                    panel_node_draw(layout, context, mat,
                                    'RendermanOutputNode', 'Bxdf')

            else:
                if not panel_node_draw(layout, context, mat, 'ShaderNodeOutputMaterial', 'Surface'):
                    layout.prop(mat, "diffuse_color")
            layout.separator()

        else:
            # if no nodetree we use pxrdisney
            mat = context.material
            rm = mat.renderman

            row = layout.row()
            row.prop(mat, "diffuse_color")

            layout.separator()
        if mat and not is_renderman_nodetree(mat):
            rm = mat.renderman
            row = layout.row()
            #row.prop(rm, "copy_color_params")
            
            row = layout.row(align=True)
            col = row.column()
            rman_icon = rfb_icons.get_icon('rman_graph')
            col.operator(
                'material.rman_add_rman_nodetree', icon_value=rman_icon.icon_id).idtype = "material"
            if do_cycles_convert():
                col = row.column()                
                op = col.operator('material.rman_convert_cycles_shader').idtype = "material"
                if not mat.grease_pencil:
                    layout.operator('material.rman_convert_all_cycles_shaders')


class MATERIAL_PT_renderman_shader_light(ShaderPanel, Panel):
    bl_context = "material"
    bl_label = "Light Emission"
    shader_type = 'Light'
    COMPAT_ENGINES = {'PRMAN_RENDER'}

    @classmethod
    def poll(cls, context):
        mat = getattr(context, 'material', None)
        if not mat:
            return False
        if not mat.node_tree: 
            return False    
        output = is_renderman_nodetree(mat)
        if not output:
            return False
        if not output.inputs[1].is_linked:
            return False

        from_node = output.inputs[1].links[0].from_node
        return from_node.bl_label == 'PxrMeshLight'

    def draw(self, context):
        if context.material.node_tree:
            nt = context.material.node_tree
            mat = context.material
            rman_output_node = is_renderman_nodetree(mat)
            if not rman_output_node:
                return            
            layout = self.layout

            # Filter Toggle
            split = layout.split(factor=0.05)
            col = split.column()
            filter_icon = 'FILTER'
            filter_parameters = getattr(rman_output_node, 'light_filter_parameters', False)
            filter_method = getattr(rman_output_node, 'light_filter_method', 'NONE')
            col.context_pointer_set('node', rman_output_node)
            pressed = filter_parameters
            op = col.operator('node.rman_toggle_filter_params', depress=pressed, icon=filter_icon, text='')
            op.prop_name = 'light_filter_parameters'

            if filter_parameters:
                col = split.column()
                col.prop(rman_output_node, 'light_filter_method', text='')

                if filter_method == 'MATCH':
                    col = split.column()
                    col.prop(rman_output_node, 'light_match_expression', text='')     
                    col = split.column() 
                    col.prop(rman_output_node, 'light_match_on', text='')   
                else:
                    col = split.column()
                    col = split.column()                                
                
            input_name = 'light_in'
            if not rman_output_node.inputs[input_name].is_linked:
                draw_nodes_properties_ui(
                    layout, context, nt, input_name=input_name)
            elif not filter_parameters or filter_method == 'NONE':
                draw_nodes_properties_ui(
                    layout, context, nt, input_name=input_name)                 
            elif filter_method == 'STICKY':
                light_node = rman_output_node.inputs[input_name].links[0].from_node
                nodes = gather_nodes(light_node)
                for node in nodes:
                    prop_names = getattr(node, 'prop_names', list())
                    show_node_sticky_params(layout, node, prop_names, context, nt, rman_output_node)
            elif filter_method == 'MATCH':
                expr = rman_output_node.light_match_expression
                if expr == '':
                    return                
                light_node = rman_output_node.inputs[input_name].links[0].from_node
                nodes = gather_nodes(light_node)
                for node in nodes:
                    prop_names = getattr(node, 'prop_names', list())
                    show_node_match_params(layout, node, expr, rman_output_node.disp_match_on,
                                        prop_names, context, nt)
            else:
                draw_nodes_properties_ui(
                    layout, context, nt, input_name=input_name)     
                 
class MATERIAL_PT_renderman_shader_displacement(ShaderPanel, Panel):
    bl_context = "material"
    bl_label = "Displacement"
    shader_type = 'Displacement'
    COMPAT_ENGINES = {'PRMAN_RENDER'}

    def draw(self, context):
        if context.material.node_tree:
            nt = context.material.node_tree
            mat = context.material
            rman_output_node = is_renderman_nodetree(mat)
            if not rman_output_node:
                return
            layout = self.layout

            # Filter Toggle
            split = layout.split(factor=0.05)
            col = split.column()
            filter_icon = 'FILTER'
            filter_parameters = getattr(rman_output_node, 'disp_filter_parameters', False)
            filter_method = getattr(rman_output_node, 'disp_filter_method', 'NONE')
            col.context_pointer_set('node', rman_output_node)
            pressed = filter_parameters            
            op = col.operator('node.rman_toggle_filter_params', depress=pressed, icon=filter_icon, text='')
            op.prop_name = 'disp_filter_parameters'

            if filter_parameters:
                col = split.column()
                col.prop(rman_output_node, 'disp_filter_method', text='')

                if filter_method == 'MATCH':
                    col = split.column()
                    col.prop(rman_output_node, 'disp_match_expression', text='') 
                    col = split.column() 
                    col.prop(rman_output_node, 'disp_match_on', text='')         
                else:
                    col = split.column()
                    col = split.column()                                
                
            input_name = 'displace_in'
            if not rman_output_node.inputs[input_name].is_linked:
                draw_nodes_properties_ui(
                    layout, context, nt, input_name=input_name)
            elif not filter_parameters or filter_method == 'NONE':
                draw_nodes_properties_ui(
                    layout, context, nt, input_name=input_name)                 
            elif filter_method == 'STICKY':
                disp_node = rman_output_node.inputs[input_name].links[0].from_node
                nodes = gather_nodes(disp_node)
                for node in nodes:
                    prop_names = getattr(node, 'prop_names', list())
                    show_node_sticky_params(layout, node, prop_names, context, nt, rman_output_node)
            elif filter_method == 'MATCH':
                expr = rman_output_node.disp_match_expression
                if expr == '':
                    return                
                disp_node = rman_output_node.inputs[input_name].links[0].from_node
                nodes = gather_nodes(disp_node)
                for node in nodes:
                    prop_names = getattr(node, 'prop_names', list())
                    show_node_match_params(layout, node, expr, rman_output_node.disp_match_on,
                                        prop_names, context, nt)
            else:
                draw_nodes_properties_ui(
                    layout, context, nt, input_name=input_name)                      

class DATA_PT_renderman_light(ShaderPanel, Panel):
    bl_context = "data"
    bl_label = "Light"
    shader_type = 'light'

    def draw(self, context):
        layout = self.layout

        light = context.light
        if not light.renderman.use_renderman_node:
            layout.prop(light, "type", expand=True)
            layout.prop(light, "color")
            layout.prop(light, "energy")
            if light.type == 'POINT':
                layout.prop(light, "shadow_soft_size")
            layout.label(text='')
            layout.operator('material.rman_add_rman_nodetree').idtype = 'light'
            return
        else:       
            row = layout.row()
            col = row.column()
            light_shader = light.renderman.get_light_node_name()
            if light.renderman.renderman_light_role == 'RMAN_LIGHT':
                rman_light_icon = rfb_icons.get_light_icon(light_shader)
            else:
                rman_light_icon = rfb_icons.get_lightfilter_icon(light_shader)
            col.label(text="%s" % light_shader, icon_value=rman_light_icon.icon_id)

class PRMAN_PT_context_material(_RManPanelHeader, Panel):
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_label = ""
    bl_context = "material"
    bl_options = {'HIDE_HEADER'}
    COMPAT_ENGINES = {'PRMAN_RENDER'}

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type == 'GPENCIL':
            return False
        else:
            return (context.material or context.object) and _RManPanelHeader.poll(context)

    def draw(self, context):
        layout = self.layout

        mat = context.material
        ob = context.object
        slot = context.material_slot
        space = context.space_data

        if ob:
            is_sortable = len(ob.material_slots) > 1
            rows = 1
            if (is_sortable):
                rows = 4

            row = layout.row()

            row.template_list("MATERIAL_UL_matslots", "", ob, "material_slots", ob, "active_material_index", rows=rows)

            col = row.column(align=True)
            col.operator("object.material_slot_add", icon='ADD', text="")
            col.operator("object.material_slot_remove", icon='REMOVE', text="")

            col.menu("MATERIAL_MT_context_menu", icon='DOWNARROW_HLT', text="")

            if is_sortable:
                col.separator()

                col.operator("object.material_slot_move", icon='TRIA_UP', text="").direction = 'UP'
                col.operator("object.material_slot_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

            if ob.mode == 'EDIT':
                row = layout.row(align=True)
                row.operator("object.material_slot_assign", text="Assign")
                row.operator("object.material_slot_select", text="Select")
                row.operator("object.material_slot_deselect", text="Deselect")

        split = layout.split(factor=0.65)

        if ob:
            split.template_ID(ob, "active_material", new="material.new")
            row = split.row()

            if slot:
                row.prop(slot, "link", text="")
            else:
                row.label()
        elif mat:
            split.template_ID(space, "pin_id")
            split.separator()
       
class DATA_PT_renderman_node_shader_light(ShaderNodePanel, Panel):
    bl_label = "Light Parameters"
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER' and hasattr(context, "light") \
            and context.light is not None and hasattr(context.light, 'renderman') \
            and context.light.renderman.renderman_light_role != 'RMAN_LIGHTFILTER'    


    def draw(self, context):
        layout = self.layout
        light = context.light
        layout.prop(light.renderman, 'light_primary_visibility')
        if light.node_tree:
            nt = light.node_tree
            draw_nodes_properties_ui(
                self.layout, context, nt, input_name='light_in')          

class DATA_PT_renderman_node_shader_lightfilter(ShaderNodePanel, Panel):
    bl_label = "Light Filter Parameters"
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER' and hasattr(context, "light") \
            and context.light is not None and hasattr(context.light, 'renderman') \
            and context.light.renderman.renderman_light_role == 'RMAN_LIGHTFILTER'    

    def draw(self, context):
        layout = self.layout
        light = context.light

        if light.node_tree:
            nt = light.node_tree
            draw_nodes_properties_ui(
                self.layout, context, nt, input_name='lightfilter_in')     

class RENDERMAN_UL_LightFilters(CollectionPanel):
    def draw_item(self, layout, context, item):        
        layout.prop(item, 'linked_filter_ob')    

        lightfilter = item.linked_filter_ob
        if lightfilter:
            if context.scene.objects.get(lightfilter.name) == None:
                # This is pure yuck. We shouldn't be modifying the scene
                # during a draw routine. However, we can still be referencing
                # an object that's already been removed.
                bpy.data.objects.remove(lightfilter)
                return

            if lightfilter.data.node_tree:
                col = layout.column()
                rr = RmanRender.get_rman_render()
                if rr.rman_context.is_live_rendering():
                    col.context_pointer_set("light_filter", lightfilter)
                    col.operator("node.rman_force_lightfilter_refresh", text='Force Refresh')              

                nt = lightfilter.data.node_tree
                draw_nodes_properties_ui(
                    self.layout, context, nt, input_name='lightfilter_in')
        else:
            layout.label(text='No light filter linked')            

    def draw(self, context):
        layout = self.layout
        light = context.light

        self._draw_collection(context, layout, light.renderman, "",
                              "renderman.add_remove_lightfilter", "light", "light_filters",
                              "light_filters_index")

class DATA_PT_renderman_node_filters_light(RENDERMAN_UL_LightFilters, Panel):
    bl_label = "Light Filters"
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER' and hasattr(context, "light") \
            and context.light is not None and hasattr(context.light, 'renderman') \
            and context.light.renderman.renderman_light_role != 'RMAN_LIGHTFILTER'

class RENDERMAN_UL_Porta_Lights(CollectionPanel):
    def draw_item(self, layout, context, item):        
        #layout.prop(item, 'linked_portal_ob')    

        portal = item.linked_portal_ob
        if portal:
            if context.scene.objects.get(portal.name) == None:
                # This is pure yuck. We shouldn't be modifying the scene
                # during a draw routine. However, we can still be referencing
                # an object that's already been removed.
                bpy.data.objects.remove(portal)
                return

            if portal.data.node_tree:
                nt = portal.data.node_tree
                draw_nodes_properties_ui(
                    self.layout, context, nt, input_name='lightfilter_in')
        else:
            layout.label(text='No portal light linked')            

    def draw(self, context):
        layout = self.layout
        light = context.light

        self._draw_collection(context, layout, light.renderman, "",
                              "", "light", "portal_lights",
                              "portal_lights_index")            

class DATA_PT_renderman_node_portal_light(RENDERMAN_UL_Porta_Lights, Panel):
    bl_label = "Portal Lights"
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER' and hasattr(context, "light") \
            and context.light is not None and hasattr(context.light, 'renderman') \
            and context.light.renderman.renderman_light_role == 'RMAN_LIGHT' \
            and context.light.renderman.get_light_node_name() == 'PxrDomeLight'    

class DATA_PT_renderman_node_dome_light(ShaderNodePanel, Panel):
    bl_label = "Dome Lights"
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER' and hasattr(context, "light") \
            and context.light is not None and hasattr(context.light, 'renderman') \
            and context.light.renderman.renderman_light_role == 'RMAN_LIGHT' \
            and context.light.renderman.get_light_node_name() == 'PxrPortalLight'        

    def draw(self, context):
        layout = self.layout
        light = context.light                 
        rm = light.renderman

        layout.prop(rm, 'dome_light_portal')

class DATA_PT_renderman_node_shader_light_viewport(ShaderNodePanel, Panel):
    bl_label = "Viewport"
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER' and hasattr(context, "light") \
            and context.light is not None and hasattr(context.light, 'renderman') \
            and context.light.renderman.renderman_light_role != 'RMAN_LIGHTFILTER' \
            and context.light.renderman.get_light_node_name() in ['PxrRectLight', 'PxrCylinderLight', 'PxrSphereLight', 'PxrDiskLight']

    def draw(self, context):
        layout = self.layout
        light = context.light
        node = light.renderman.get_light_node()
        if getattr(node, 'coneAngle', 90.0) >= 90.0:
            layout.enabled = False
        layout.prop(light.renderman, 'rman_coneAngleDepth')  
        layout.prop(light.renderman, 'rman_coneAngleOpacity') 
class MATERIAL_PT_renderman_shader_light_filters(RENDERMAN_UL_LightFilters, Panel):
    bl_context = "material"
    bl_label = "Light Filters"
    bl_parent_id = 'MATERIAL_PT_renderman_shader_light'

    def draw(self, context):
        layout = self.layout
        mat = context.material

        self._draw_collection(context, layout, mat.renderman_light, "",
                              "renderman.add_meshlight_lightfilter", "material", "light_filters",
                              "light_filters_index")    


classes = [
    MATERIAL_PT_renderman_preview,
    MATERIAL_PT_renderman_material_refresh,
    DATA_PT_renderman_light_refresh,
    MATERIAL_PT_renderman_shader_surface,
    MATERIAL_PT_renderman_shader_light,
    MATERIAL_PT_renderman_shader_displacement,
    DATA_PT_renderman_light,
    DATA_PT_renderman_node_shader_light,
    DATA_PT_renderman_node_shader_lightfilter,
    DATA_PT_renderman_node_filters_light,
    DATA_PT_renderman_node_portal_light,
    DATA_PT_renderman_node_dome_light,
    DATA_PT_renderman_node_shader_light_viewport,    
    PRMAN_PT_context_material,
    MATERIAL_PT_renderman_shader_light_filters
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes) 

def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)   