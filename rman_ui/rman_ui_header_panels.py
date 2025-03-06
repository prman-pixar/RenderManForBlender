from .. import rfb_icons
from ..rfb_utils.shadergraph_utils import is_renderman_nodetree, find_soloable_node, find_blimage_nodes
import bpy

class PRMAN_HT_DrawRenderHeaderInfo(bpy.types.Header):
    '''Adds a render button or stop IPR button to the Info
    UI panel
    '''

    bl_space_type = "INFO"

    def draw(self, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return
        layout = self.layout
        rm = context.scene.renderman
        
        if not rm.is_rman_interactive_running:

            # Render
            row = layout.row(align=True)
            rman_render_icon = rfb_icons.get_icon("rman_render")            
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)
        else:
            row = layout.row(align=True)
            rman_rerender_controls = rfb_icons.get_icon("rman_ipr_cancel")
            row.operator('renderman.stop_ipr', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)      


class NODE_MT_renderman_node_editor_menu(bpy.types.Menu):
    bl_label = "RenderMan"
    bl_idname = "NODE_MT_renderman_node_editor_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def add_arrange_op(self, layout):
        rman_icon = rfb_icons.get_icon('rman_graph') 
        layout.operator('node.button', icon_value=rman_icon.icon_id) 
        layout.operator('node.na_align_nodes', icon_value=rman_icon.icon_id) 

    def draw(self, context):
        layout = self.layout

        if not hasattr(context.space_data, 'id'):
            return

        if type(context.space_data.id) == bpy.types.Material:
            mat = context.space_data.id
            rman_output_node = is_renderman_nodetree(mat)

            if not rman_output_node:           
                rman_icon = rfb_icons.get_icon('rman_graph') 
                layout.operator(
                    'material.rman_add_rman_nodetree', icon_value=rman_icon.icon_id).idtype = "node_editor"
            else:
                rman_icon = rfb_icons.get_icon("out_PxrSurface")
                layout.operator('node.rman_new_bxdf', text='New Bxdf', icon_value=rman_icon.icon_id).idtype = "node_editor"
                nt = context.space_data.edit_tree
                layout.context_pointer_set("mat", mat)
                layout.context_pointer_set("nodetree", nt)  
                layout.context_pointer_set("node", rman_output_node) 
                if find_blimage_nodes(nt):
                    rman_icon = rfb_icons.get_icon('rman_blender')  
                    layout.operator('node.convert_blimage_nodes', icon_value=rman_icon.icon_id)
                selected_node = find_soloable_node(nt)
                if selected_node:                     
                    rman_icon = rfb_icons.get_icon('rman_solo_on')
                    layout.context_pointer_set("selected_node", selected_node)
                    op = layout.operator('node.rman_set_node_solo', text='Solo %s' % selected_node.name, icon_value=rman_icon.icon_id)
                    op.refresh_solo = False

                if rman_output_node.solo_node_pointer != '':   
                    layout.context_pointer_set("selected_node", None)
                    op = layout.operator('node.rman_set_node_solo', text='Reset Solo', icon='FILE_REFRESH')
                    op.refresh_solo = True     
            
                #self.add_arrange_op(layout)                                    

        elif type(context.space_data.id) == bpy.types.World:
            if not context.space_data.id.renderman.use_renderman_node:
                layout.operator(
                    'material.rman_add_rman_nodetree', text="Add RenderMan Nodes").idtype = "world"  
            else:
                pass
                #self.add_arrange_op(layout)                
        else:
            pass
            #self.add_arrange_op(layout)

class NODE_HT_DrawRenderHeaderNode(bpy.types.Header):
    '''
    Adds a New RenderMan Material button or Convert to RenderMan button to 
    the node editor UI.
    '''

    bl_space_type = "NODE_EDITOR"

    def draw(self, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return
        layout = self.layout
        row = layout.row(align=True)

        if not hasattr(context.space_data, 'id'):
            return

        if type(context.space_data.id) == bpy.types.Material:
            rman_output_node = is_renderman_nodetree(context.space_data.id)            

            if not rman_output_node:           
                rman_icon = rfb_icons.get_icon('rman_graph') 
                row.operator(
                    'material.rman_add_rman_nodetree', text="", icon_value=rman_icon.icon_id).idtype = "node_editor"
            else:
                pass


        elif type(context.space_data.id) == bpy.types.World:
            if not context.space_data.id.renderman.use_renderman_node:
                rman_icon = rfb_icons.get_icon('rman_graph') 
                row.operator(
                    'material.rman_add_rman_nodetree', text="", icon_value=rman_icon.icon_id).idtype = "world"                

class PRMAN_HT_DrawRenderHeaderImage(bpy.types.Header):
    '''Adds a render button or stop IPR button to the image editor
    UI
    '''

    bl_space_type = "IMAGE_EDITOR"

    def draw(self, context):
        if context.scene.render.engine != "PRMAN_RENDER":
            return
        layout = self.layout

        if not context.scene.renderman.is_rman_interactive_running:

            # Render
            row = layout.row(align=True)
            rman_render_icon = rfb_icons.get_icon("rman_render")       
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)    

        else:
            row = layout.row(align=True)
            rman_rerender_controls = rfb_icons.get_icon("rman_ipr_cancel")
            row.operator('renderman.stop_ipr', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)  

def rman_add_node_editor_menu(self, context):
    layout = self.layout
    rman_icon = rfb_icons.get_icon("rman_blender")    
    layout.menu('NODE_MT_renderman_node_editor_menu', text='RenderMan', icon_value=rman_icon.icon_id)

classes = [
    #PRMAN_HT_DrawRenderHeaderInfo,
    NODE_HT_DrawRenderHeaderNode,
    NODE_MT_renderman_node_editor_menu,
    #PRMAN_HT_DrawRenderHeaderImage,
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes) 

    bpy.types.NODE_MT_context_menu.prepend(rman_add_node_editor_menu)

def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)       

    bpy.types.NODE_MT_context_menu.remove(rman_add_node_editor_menu)