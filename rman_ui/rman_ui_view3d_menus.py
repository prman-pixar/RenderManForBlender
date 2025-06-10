from .. import rfb_icons
from .. import rman_bl_nodes
from ..rfb_utils.operator_utils import get_bxdf_items, get_light_items, get_lightfilter_items
from ..rfb_utils.scene_utils import RMAN_VOL_TYPES
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import object_utils
from ..rfb_utils.envconfig_utils import envconfig
from ..rfb_utils.prefs_utils import using_qt, show_wip_qt
from ..rfb_logger import rfb_log
from ..rman_config import __RFB_CONFIG_DICT__ as rfb_config
from bpy.types import Menu
import bpy

class VIEW3D_MT_renderman_add_object_menu(Menu):
    bl_label = "RenderMan"
    bl_idname = "VIEW3D_MT_renderman_add_object_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):
        return rfb_icons.get_icon("rman_blender").icon_id          

    def draw(self, context):
        layout = self.layout

        selected_light_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if shadergraph_utils.is_rman_light(obj, include_light_filters=False):
                    selected_light_objects.append(obj)       

        layout.menu('VIEW3D_MT_RM_Add_Light_Menu', icon_value=bpy.types.VIEW3D_MT_RM_Add_Light_Menu.get_icon_id())

        if selected_light_objects:
            layout.menu('VIEW3D_MT_RM_Add_LightFilter_Menu', text='Attach Light Filter', icon_value=bpy.types.VIEW3D_MT_RM_Add_LightFilter_Menu.get_icon_id())
        else:
            layout.menu('VIEW3D_MT_RM_Add_LightFilter_Menu', icon_value=bpy.types.VIEW3D_MT_RM_Add_LightFilter_Menu.get_icon_id())

        layout.separator()
        layout.menu('VIEW3D_MT_renderman_add_object_quadrics_menu', icon='MESH_UVSPHERE')
        layout.separator()

        layout.separator()
        layout.menu('VIEW3D_MT_renderman_add_object_volumes_menu', icon_value=bpy.types.VIEW3D_MT_renderman_add_object_volumes_menu.get_icon_id())
        layout.separator()        
     
        rman_icon = rfb_icons.get_icon("rman_CreateArchive")
        op = layout.operator('object.rman_add_rman_geo', text='RIB Archive', icon_value=rman_icon.icon_id)
        op.rman_prim_type = 'DELAYED_LOAD_ARCHIVE'
        op.rman_default_name = 'RIB_Archive'    
        op.bl_prim_type = ''
        op.rman_open_filebrowser = True    

        if rfb_config['ui_preferences']['render_runprograms']['default']:
            op = layout.operator('object.rman_add_rman_geo', text='RunProgram')
            op.rman_prim_type = 'PROCEDURAL_RUN_PROGRAM'
            op.rman_default_name = 'RiRunProgram'          
            op.bl_prim_type = ''
            op.rman_open_filebrowser = True

        rman_icon = rfb_icons.get_icon("rman_alembic")
        op = layout.operator('object.rman_add_rman_geo', text='Alembic Archive', icon_value=rman_icon.icon_id)
        op.rman_prim_type = 'ALEMBIC'
        op.rman_default_name = 'rman_AlembicArchive'            
        op.bl_prim_type = ''
        op.rman_open_filebrowser = True   
        op.rman_convert_to_zup = True     

        op = layout.operator('object.rman_add_rman_geo', text='RiProcedural')
        op.rman_prim_type = 'DYNAMIC_LOAD_DSO'
        op.rman_default_name = 'RiProcedural'            
        op.bl_prim_type = ''
        op.rman_open_filebrowser = True
        
        op = layout.operator('object.rman_add_rman_geo', text='Brickmap Geometry')
        op.rman_prim_type = 'BRICKMAP'
        op.rman_default_name = 'BrickmapGeo'          
        op.bl_prim_type = ''
        op.rman_open_filebrowser = True

class VIEW3D_MT_renderman_add_object_volumes_menu(Menu):
    bl_label = "Volumes"
    bl_idname = "VIEW3D_MT_renderman_add_object_volumes_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):
        return rfb_icons.get_icon("out_PxrVolume").icon_id                    

    def draw(self, context):
        layout = self.layout
        rman_icon = rfb_icons.get_icon('rman_openvdb')
        op = layout.operator('object.rman_add_rman_geo', text='Import OpenVDB', icon_value=rman_icon.icon_id)
        op.rman_prim_type = ''
        op.bl_prim_type = 'VOLUME'
        op.rman_default_name = 'OpenVDB'    
        op.rman_open_filebrowser = True 
        op.rman_convert_to_zup = True

        rman_icon = rfb_icons.get_node_icon('PxrVolume')
        op = layout.operator('object.rman_add_rman_geo', text='Volume Box', icon_value=rman_icon.icon_id)
        op.rman_prim_type = 'RI_VOLUME'
        op.rman_default_name = 'RiVolume'   
        op.rman_open_filebrowser = False                      


class VIEW3D_MT_renderman_add_object_quadrics_menu(Menu):
    bl_label = "Quadrics"
    bl_idname = "VIEW3D_MT_renderman_add_object_quadrics_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        op = layout.operator('object.rman_add_rman_geo', text='Sphere', icon='MESH_UVSPHERE')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'SPHERE'
        op.bl_prim_type = ''
        op.rman_open_filebrowser = False

        op = layout.operator('object.rman_add_rman_geo', text='Cylinder', icon='MESH_CYLINDER')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'CYLINDER'
        op.bl_prim_type = ''
        op.rman_open_filebrowser = False

        op = layout.operator('object.rman_add_rman_geo', text='Cone', icon='MESH_CONE')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'CONE'
        op.bl_prim_type = ''
        op.rman_open_filebrowser = False

        op = layout.operator('object.rman_add_rman_geo', text='Disk', icon='MESH_CIRCLE')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'DISK'   
        op.bl_prim_type = ''
        op.rman_open_filebrowser = False   

        op = layout.operator('object.rman_add_rman_geo', text='Torus', icon='MESH_TORUS')
        op.rman_prim_type = 'QUADRIC'
        op.rman_quadric_type = 'TORUS'  
        op.bl_prim_type = ''
        op.rman_open_filebrowser = False                               

class VIEW3D_MT_renderman_object_context_menu(Menu):
    bl_label = "RenderMan"
    bl_idname = "VIEW3D_MT_renderman_object_context_menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):
        return rfb_icons.get_icon("rman_blender").icon_id             

    def draw(self, context):
        layout = self.layout
        is_rman_running = context.scene.renderman.is_rman_running
        is_rman_interactive_running = context.scene.renderman.is_rman_interactive_running

        if is_rman_running and not is_rman_interactive_running:
            rman_icon = rfb_icons.get_icon("rman_ipr_cancel")
            layout.operator('renderman.stop_render', text="Stop Render",
                            icon_value=rman_icon.icon_id)
            return      

        selected_objects = []
        selected_light_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if shadergraph_utils.is_rman_light(obj, include_light_filters=False):                    
                    selected_light_objects.append(obj)
                elif obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                    selected_objects.append(obj)

        layout.menu('VIEW3D_MT_RM_Add_Render_Menu', icon_value=VIEW3D_MT_RM_Add_Render_Menu.get_icon_id())
        if selected_light_objects:
            layout.separator()
            layout.operator_menu_enum(
                    "object.rman_add_light_filter", 'rman_lightfilter_name', text="Attach New Light Filter", icon='LIGHT')              

        layout.separator()
        if selected_objects:
            # Add Bxdf             
            layout.menu('VIEW3D_MT_RM_Add_bxdf_Menu', text='Add New Material', icon_value=bpy.types.VIEW3D_MT_RM_Add_bxdf_Menu.get_icon_id())           

            # Make Selected Geo Emissive
            rman_meshlight = rfb_icons.get_icon("out_PxrMeshLight")
            layout.operator("object.rman_create_meshlight", text="Convert to Mesh Light",
                            icon_value=rman_meshlight.icon_id)

            # Add Subdiv Sheme
            rman_subdiv = rfb_icons.get_icon("rman_subdiv")
            layout.operator("mesh.rman_convert_subdiv",
                            icon_value=rman_subdiv.icon_id)

            layout.separator()
            layout.menu('VIEW3D_MT_RM_Add_Export_Menu', icon_value=VIEW3D_MT_RM_Add_Export_Menu.get_icon_id())

        # Diagnose        
        layout.separator()
        column = layout.column()
        column.enabled = not is_rman_interactive_running
        row = column.row()
        rman_rib = rfb_icons.get_icon('rman_rib_small')
        row.operator("renderman.open_scene_rib", text='View RIB', icon_value=rman_rib.icon_id)
        if selected_objects or selected_light_objects:
            row = column.row()
            row.operator("renderman.open_selected_rib", text='View Selected RIB', icon_value=rman_rib.icon_id)    

        layout.separator()
        layout.label(text='Groups')
        layout.menu('VIEW3D_MT_RM_Add_Selected_To_ObjectGroup_Menu', text='Trace Sets')     
        layout.menu('VIEW3D_MT_RM_Add_Selected_To_LightMixer_Menu', text='Light Mixer Groups')  
        layout.menu('VIEW3D_MT_RM_LightLinking_Menu', text='Light Linking') 
        layout.menu('VIEW3D_MT_RM_Volume_Aggregates_Menu', text='Volume Aggregates')  
        layout.separator()
        layout.menu('VIEW3D_MT_RM_Stylized_Menu', text='Stylized Looks')  

        if envconfig().getenv('RFB_DEVELOPER'):
            layout.separator()
            layout.menu('VIEW3D_MT_RM_Dev_Menu')

class VIEW3D_MT_RM_LightLinking_Menu(bpy.types.Menu):
    bl_label = "Light Linking"
    bl_idname = "VIEW3D_MT_RM_LightLinking_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):  
        return rfb_icons.get_icon("rman_blender").icon_id

    def draw(self, context):
        rm = context.scene.renderman
        layout = self.layout
        layout.operator("scene.rman_open_light_linking", text="Light Linking Editor")

        active_light = context.active_object
        selected_objects = context.selected_objects
        if active_light and active_light.type != 'LIGHT':
            pass
            '''
            if selected_objects:
                layout.separator()
                for l in scene_utils.get_all_lights(context.scene):
                    layout.context_pointer_set('light_ob', l)
                    layout.menu('VIEW3D_MT_RM_LightLinking_SubMenu', text=l.name)  
            '''
            return
        light_props = shadergraph_utils.get_rman_light_properties_group(active_light)
        if light_props is None:
            return
        if light_props.renderman_light_role not in {'RMAN_LIGHTFILTER', 'RMAN_LIGHT'}:
            return
        if using_qt() and show_wip_qt():
            return
        selected_objects = context.selected_objects
        if selected_objects:
            layout.context_pointer_set('light_ob', active_light)
            if not rm.invert_light_linking:
                layout.separator()
                op = layout.operator('renderman.update_light_link_illuminate', text="Default")
                op.illuminate = 'DEFAULT'
                op = layout.operator('renderman.update_light_link_illuminate', text="On")
                op.illuminate = 'ON'
                op = layout.operator('renderman.update_light_link_illuminate', text="Off")
                op.illuminate = 'OFF'
            layout.separator()
            op = layout.operator('renderman.update_light_link_objects', text="Link selected to %s" % active_light.name)
            op.update_type = 'ADD'
            op = layout.operator('renderman.update_light_link_objects', text="Remove Selected from %s" % active_light.name)
            op.update_type = 'REMOVE'

class VIEW3D_MT_RM_LightLinking_SubMenu(bpy.types.Menu):
    bl_label = "Light Linking Submenu"
    bl_idname = "VIEW3D_MT_RM_LightLinking_SubMenu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):  
        return rfb_icons.get_icon("rman_blender").icon_id

    def draw(self, context):
        rm = context.scene.renderman
        layout = self.layout
        active_light = context.light_ob

        selected_objects = context.selected_objects
        if selected_objects:
            layout.context_pointer_set('light_ob', active_light)
            layout.separator()
            op = layout.operator('renderman.update_light_link_illuminate', text="Default")
            op.illuminate = 'DEFAULT'
            op = layout.operator('renderman.update_light_link_illuminate', text="On")
            op.illuminate = 'ON'
            op = layout.operator('renderman.update_light_link_illuminate', text="Off")
            op.illuminate = 'OFF'
            layout.separator()
            op = layout.operator('renderman.update_light_link_objects', text="Link selected to %s" % active_light.name)
            op.update_type = 'ADD'
            op = layout.operator('renderman.update_light_link_objects', text="Remove Selected from %s" % active_light.name)
            op.update_type = 'REMOVE'      

class VIEW3D_MT_RM_Volume_Aggregates_Menu(bpy.types.Menu):
    bl_label = "Volume Aggregates"
    bl_idname = "VIEW3D_MT_RM_Volume_Aggregates_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):  
        return rfb_icons.get_icon("rman_blender").icon_id

    def draw(self, context):
        rm = context.scene.renderman
        layout = self.layout
        rman_vol_agg = rfb_icons.get_icon("rman_vol_aggregates")   
        layout.operator("scene.rman_open_vol_aggregates_editor", text="Volume Aggregates Editor", icon_value=rman_vol_agg.icon_id)
        layout.separator()
        if using_qt() and show_wip_qt():
            return        
        op = layout.operator("renderman.add_remove_volume_aggregates", text="Create New Group")
        op.context="scene.renderman"
        op.collection="vol_aggregates"
        op.collection_index="vol_aggregates_index"
        op.defaultname='VolumeAggreagte_%d' % len(rm.vol_aggregates)  
        selected_objects = list()
        for ob in context.selected_objects:
            if object_utils._detect_primitive_(ob) in RMAN_VOL_TYPES:
                selected_objects.append(ob)
        if not selected_objects:
            return
        vol_aggregates = rm.vol_aggregates
        if vol_aggregates:
            layout.separator()
            layout.label(text='Add Selected To: ')   
            for i, v in enumerate(vol_aggregates):
                if i == 0:
                    continue
                op = layout.operator('renderman.add_to_vol_aggregate', text=v.name)
                op.vol_aggregates_index = i
                op.do_scene_selected = True

class VIEW3D_MT_RM_Stylized_Menu(bpy.types.Menu):
    bl_label = "Stylized Looks"
    bl_idname = "VIEW3D_MT_RM_Stylized_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):  
        return rfb_icons.get_icon("rman_blender").icon_id

    def draw(self, context):
        rm = context.scene.renderman
        layout = self.layout
        '''
        if rm.render_rman_stylized: 
            layout.operator_menu_enum('node.rman_attach_stylized_pattern', 'stylized_pattern')
            layout.operator("scene.rman_open_stylized_editor", text="Stylized Looks Editor")    
        else:
            op = layout.operator("scene.rman_enable_stylized_looks", text="Enable Stylized Looks")   
            op.open_editor = True
        ''' 
        if rm.render_rman_stylized: 
            layout.operator_menu_enum('node.rman_attach_stylized_pattern', 'stylized_pattern')
        layout.operator("scene.rman_open_stylized_editor", text="Stylized Looks Editor")    
            

class VIEW3D_MT_RM_Add_Render_Menu(bpy.types.Menu):
    bl_label = "Render"
    bl_idname = "VIEW3D_MT_RM_Add_Render_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):  
        return rfb_icons.get_icon("rman_blender").icon_id

    def draw(self, context):
        layout = self.layout
        rm = context.scene.renderman

        if not rm.is_rman_interactive_running:
            rman_rerender_controls = rfb_icons.get_icon("rman_ipr_on")
            op = layout.operator('renderman.start_ipr', text="IPR",
                            icon_value=rman_rerender_controls.icon_id)                
            op.render_to_it = False
            op = layout.operator('renderman.start_ipr', text="IPR to it",
                            icon_value=rman_rerender_controls.icon_id)                
            op.render_to_it = True            
            rman_render_icon = rfb_icons.get_icon("rman_render")
            layout.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)        
        else:
            rman_rerender_controls = rfb_icons.get_icon("rman_ipr_cancel")
            layout.operator('renderman.stop_ipr', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id) 
            rman_icon = rfb_icons.get_icon('rman_refresh')    
            layout.operator('renderman.refresh_ipr', text="Refresh IPR",
                            icon_value=rman_icon.icon_id)              
            layout.separator()
            rman_icon = rfb_icons.get_icon('rman_vp_viz')
            layout.menu('PRMAN_MT_Viewport_Integrator_Menu', icon_value=rman_icon.icon_id)
            layout.menu('PRMAN_MT_Viewport_Refinement_Menu', icon='IMPORT')
            if rm.is_rman_viewport_rendering:
                rman_icon = rfb_icons.get_icon('rman_vp_resolution')
                layout.menu('PRMAN_MT_Viewport_Res_Mult_Menu', icon_value=rman_icon.icon_id)
                rman_icon = rfb_icons.get_icon('rman_vp_aovs')
                layout.menu('PRMAN_MT_Viewport_Channel_Sel_Menu', icon_value=rman_icon.icon_id)
                rman_icon = rfb_icons.get_icon('rman_vp_crop')
                layout.operator("renderman_viewport.cropwindow", icon_value=rman_icon.icon_id)
                rman_icon = rfb_icons.get_icon('rman_vp_snapshot')
                layout.operator("renderman_viewport.snapshot", icon_value=rman_icon.icon_id)
                layout.operator('renderman_viewport.enhance', icon='VIEW_ZOOM')                
            # texture cache clear      
            rman_icon = rfb_icons.get_icon('rman_lightning_grey')
            layout.operator('rman_txmgr_list.clear_all_cache', icon_value=rman_icon.icon_id)                 

class VIEW3D_MT_RM_Add_Export_Menu(bpy.types.Menu):
    bl_label = "Export"
    bl_idname = "VIEW3D_MT_RM_Add_Export_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):  
        return rfb_icons.get_icon("rman_CreateArchive").icon_id

    def draw(self, context):
        layout = self.layout

        rman_archive = rfb_icons.get_icon("rman_CreateArchive")
        layout.operator("export.rman_export_rib_archive",
                        icon_value=rman_archive.icon_id)  
        layout.operator("renderman.bake_selected_brickmap", text="Bake Object to Brickmap")      

class VIEW3D_MT_RM_Add_Selected_To_ObjectGroup_Menu(bpy.types.Menu):
    bl_label = "Trace Sets"
    bl_idname = "VIEW3D_MT_RM_Add_Selected_To_ObjectGroup_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'   

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        op = layout.operator("scene.rman_open_groups_editor", text="Trace Sets Editor")
        if using_qt() and show_wip_qt():
            return
        selected_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                    selected_objects.append(obj)          

        if not selected_objects:
            return                  

        layout.separator()
        op = layout.operator('renderman.add_remove_object_groups', text='Create New Trace Set')
        op.context = 'scene.renderman'
        op.collection = 'object_groups'
        op.collection_index = 'object_groups_index'
        op.defaultname = 'objectGroup_%d' % len(scene.renderman.object_groups)
        op.action = 'ADD'         

        obj_grps = scene.renderman.object_groups
        if obj_grps:
            layout.separator()
            layout.label(text='Add Selected To: ')                    

            for i, obj_grp in enumerate(obj_grps.keys()):
                op = layout.operator('renderman.add_to_group', text=obj_grp)
                op.do_scene_selected = True     
                op.open_editor = not using_qt()
                op.group_index = i

class VIEW3D_MT_RM_Add_Selected_To_LightMixer_Menu(bpy.types.Menu):
    bl_label = "Light Mixer"
    bl_idname = "VIEW3D_MT_RM_Add_Selected_To_LightMixer_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'    

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.operator('scene.rman_open_light_mixer_editor', text='Light Mixer Editor') 
        layout.separator()
        if using_qt() and show_wip_qt():
            return        
        selected_light_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if shadergraph_utils.is_rman_light(obj, include_light_filters=False):
                    selected_light_objects.append(obj)                    

        if not selected_light_objects:
            return                        

        op = layout.operator('collection.add_remove', text='Create Light Mixer Group')
        op.context = 'scene.renderman'
        op.collection = 'light_mixer_groups'
        op.collection_index = 'light_mixer_groups_index'
        op.defaultname = 'mixerGroup_%d' % len(scene.renderman.light_mixer_groups)
        op.action = 'ADD'
  
        lgt_mixer_grps = scene.renderman.light_mixer_groups
        if lgt_mixer_grps:
            layout.separator()
            layout.label(text='Add Selected To: ')
            for i, obj_grp in enumerate(lgt_mixer_grps.keys()):
                op = layout.operator('renderman.add_light_to_light_mixer_group', text=obj_grp)
                op.do_scene_selected = True   
                op.open_editor = True
                op.group_index = i     

class VIEW3D_MT_RM_Add_Light_Menu(bpy.types.Menu):
    bl_label = "Light"
    bl_idname = "VIEW3D_MT_RM_Add_Light_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls): 
        return rfb_icons.get_icon("rman_arealight").icon_id        

    def draw(self, context):
        layout = self.layout

        for nm, nm, description, icon, i in get_light_items():
            op = layout.operator('object.rman_add_light', text=nm, icon_value=icon)
            op.rman_light_name = nm                                      

class VIEW3D_MT_RM_Add_LightFilter_Menu(bpy.types.Menu):
    bl_label = "Light Filter"
    bl_idname = "VIEW3D_MT_RM_Add_LightFilter_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):  
        return rfb_icons.get_icon("rman_lightfilter").icon_id             

    def draw(self, context):
        layout = self.layout

        for nm, nm, description, icon, i in get_lightfilter_items():
            op = layout.operator('object.rman_add_light_filter', text=nm, icon_value=icon)
            op.rman_lightfilter_name = nm                             

class VIEW3D_MT_RM_Add_bxdf_Menu(bpy.types.Menu):
    bl_label = "Material"
    bl_idname = "VIEW3D_MT_RM_Add_bxdf_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    @classmethod
    def get_icon_id(cls):
        return rfb_icons.get_icon("out_PxrSurface").icon_id              

    def draw(self, context):
        layout = self.layout

        for nm, label, description, icon, i in get_bxdf_items():
            if not nm:
                layout.separator()
                layout.label(text=label)
                continue
            op = layout.operator('object.rman_add_bxdf', text=nm, icon_value=icon)
            op.bxdf_name = nm         

class VIEW3D_MT_RM_Dev_Menu(bpy.types.Menu):
    bl_label = "Developer"
    bl_idname = "VIEW3D_MT_RM_Dev_Menu"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'

    def draw(self, context):
        layout = self.layout
        layout.operator('renderman.start_debug_server') 
        layout.operator('renderman.run_unit_tests')
        layout.operator('renderman.rfb_zip_addon')     

def rman_add_object_menu(self, context):

    rd = context.scene.render
    if rd.engine != 'PRMAN_RENDER':
        return    

    layout = self.layout
    layout.menu('VIEW3D_MT_renderman_add_object_menu', text='RenderMan', icon_value=bpy.types.VIEW3D_MT_renderman_add_object_menu.get_icon_id())

def rman_object_context_menu(self, context):

    rd = context.scene.render
    layout = self.layout      
    if rd.engine != 'PRMAN_RENDER':
        layout.operator('renderman.use_renderman', text='Use RenderMan', icon_value=rfb_icons.get_icon("rman_blender").icon_id)        
        layout.separator()
    else:
        layout.menu('VIEW3D_MT_renderman_object_context_menu', text='RenderMan', icon_value=bpy.types.VIEW3D_MT_renderman_add_object_menu.get_icon_id())    

classes = [
    VIEW3D_MT_renderman_add_object_menu,
    VIEW3D_MT_renderman_add_object_quadrics_menu,
    VIEW3D_MT_renderman_add_object_volumes_menu,
    VIEW3D_MT_renderman_object_context_menu,
    VIEW3D_MT_RM_Add_Selected_To_ObjectGroup_Menu,
    VIEW3D_MT_RM_Add_Selected_To_LightMixer_Menu,
    VIEW3D_MT_RM_Add_Light_Menu,
    VIEW3D_MT_RM_Add_LightFilter_Menu,
    VIEW3D_MT_RM_Add_bxdf_Menu,
    VIEW3D_MT_RM_Add_Export_Menu,
    VIEW3D_MT_RM_Add_Render_Menu,
    VIEW3D_MT_RM_Stylized_Menu,
    VIEW3D_MT_RM_LightLinking_Menu,
    VIEW3D_MT_RM_LightLinking_SubMenu,
    VIEW3D_MT_RM_Volume_Aggregates_Menu,
    VIEW3D_MT_RM_Dev_Menu
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes)  

    bpy.types.VIEW3D_MT_add.prepend(rman_add_object_menu)
    bpy.types.VIEW3D_MT_object_context_menu.prepend(rman_object_context_menu)


def unregister():
    bpy.types.VIEW3D_MT_add.remove(rman_add_object_menu)
    bpy.types.VIEW3D_MT_object_context_menu.remove(rman_object_context_menu)

    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes) 