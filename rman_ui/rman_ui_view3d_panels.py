from .. import rfb_icons
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import draw_utils
from ..rfb_utils import prefs_utils
from ..rfb_logger import rfb_log
from .rman_ui_base import _RManPanelHeader
from ..rman_render import RmanRender
from ..rman_constants import RFB_HELP_URL
import bpy

class PRMAN_PT_Renderman_UI_Panel(bpy.types.Panel, _RManPanelHeader):
    '''Adds a RenderMan panel to the RenderMan VIEW_3D side tab
    '''

    bl_label = "RenderMan"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Renderman"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        # Render
        is_rman_interactive_running = rm.is_rman_interactive_running

        if is_rman_interactive_running:
            row = layout.row(align=True)
            rman_rerender_controls = rfb_icons.get_icon("rman_ipr_cancel")
            row.operator('renderman.stop_ipr', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)   
        elif rm.is_rman_running:
            row = layout.row(align=True)
            rman_rerender_controls = rfb_icons.get_icon("rman_ipr_cancel")
            row.operator('renderman.stop_render', text="Stop Render",
                            icon_value=rman_rerender_controls.icon_id)              
        else:

            row = layout.row(align=True)
            rman_render_icon = rfb_icons.get_icon("rman_render")
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)

            row.prop(context.scene, "rm_render", text="",
                    icon=draw_utils.get_open_close_icon(context.scene.rm_render))

            if context.scene.rm_render:
                scene = context.scene
                rd = scene.render

                box = layout.box()
                box.use_property_split = True
                box.use_property_decorate = False
                row = box.row(align=True)

                # Display Driver
                row.prop(rm, "render_into")

                row = box.row(align=True)
                row.prop(rm, "do_holdout_matte", text="Render Holdouts")
                
                # animation
                row = box.row(align=True)
                rman_batch = rfb_icons.get_icon("rman_batch")
                row.operator("render.render", text="Render Animation",
                            icon_value=rman_batch.icon_id).animation = True

            row = layout.row(align=True)
            rman_rerender_controls = rfb_icons.get_icon("rman_ipr_on")
            op = row.operator('renderman.start_ipr', text="Start IPR to 'it'",
                            icon_value=rman_rerender_controls.icon_id)    
            op.render_to_it = True                            

            row = layout.row(align=True)
            rman_batch = rfb_icons.get_icon("rman_batch")

            row.operator("renderman.batch_render",
                        text="External Render", icon_value=rman_batch.icon_id)

            row.prop(context.scene, "rm_render_external", text="",
                    icon=draw_utils.get_open_close_icon(context.scene.rm_render_external))
            if context.scene.rm_render_external:
                scene = context.scene
                rd = scene.render

                box = layout.box()
                row = box.row(align=True)

                # animation
                row = box.row(align=True)
                row.prop(rm, "external_animation")

                row = box.row(align=True)
                row.enabled = rm.external_animation
                row.prop(scene, "frame_start", text="Start")
                row.prop(scene, "frame_end", text="End")

                # spool render
                row = box.row(align=True)
                col = row.column()
                col.prop(rm, "queuing_system", text='')            
   
        layout.separator()

        # Create Camera
        row = layout.row(align=True)
        row.operator("object.add_prm_camera",
                     text="Add Camera", icon='CAMERA_DATA')

        row.prop(context.scene, "prm_cam", text="",
                 icon=draw_utils.get_open_close_icon(context.scene.prm_cam))

        if context.scene.prm_cam:
            ob = bpy.context.object
            box = layout.box()
            row = box.row(align=True)
            row.menu("PRMAN_MT_Camera_List_Menu",
                     text="Camera List", icon='CAMERA_DATA')

            if ob.type == 'CAMERA':

                row = box.row(align=True)
                row.prop(ob, "name", text="", icon='LIGHT_HEMI')
                row.prop(ob, "hide_viewport", text="")
                row.prop(ob, "hide_render",
                         icon='RESTRICT_RENDER_OFF', text="")
                row.operator("object.delete_cameras",
                             text="", icon='PANEL_CLOSE')

                row = box.row(align=True)
                row.scale_x = 2
                row.operator("view3d.object_as_camera", text="", icon='CURSOR')

                row.scale_x = 2
                row.operator("view3d.view_camera", text="", icon='HIDE_OFF')

                if context.space_data.lock_camera == False:
                    row.scale_x = 2
                    row.operator("wm.context_toggle", text="",
                                 icon='UNLOCKED').data_path = "space_data.lock_camera"
                elif context.space_data.lock_camera == True:
                    row.scale_x = 2
                    row.operator("wm.context_toggle", text="",
                                 icon='LOCKED').data_path = "space_data.lock_camera"

                row.scale_x = 2
                row.operator("view3d.camera_to_view",
                             text="", icon='VIEW3D')

                row = box.row(align=True)
                row.label(text="Depth Of Field :")

                row = box.row(align=True)
                row.prop(context.object.data.dof, "focus_object", text="")
                #row.prop(context.object.data.cycles, "aperture_type", text="")

                row = box.row(align=True)
                row.prop(context.object.data.dof, "focus_distance", text="Distance")

            else:
                row = layout.row(align=True)
                row.label(text="No Camera Selected")

        selected_objects = []
        selected_light_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if shadergraph_utils.is_rman_light(obj, include_light_filters=False):                    
                    selected_light_objects.append(obj)
                elif obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                    selected_objects.append(obj)

        if selected_objects:
            layout.separator()
            layout.label(text="Seleced Objects:")
            box = layout.box()

            # Add Bxdf                 
            box.menu('VIEW3D_MT_RM_Add_bxdf_Menu', text='Add New Material', icon_value=bpy.types.VIEW3D_MT_RM_Add_bxdf_Menu.get_icon_id())                 

            # Make Selected Geo Emissive
            rman_meshlight = rfb_icons.get_icon("out_PxrMeshLight")
            box.operator("object.rman_create_meshlight", text="Convert to Mesh Light",
                         icon_value=rman_meshlight.icon_id)

            # Add Subdiv Sheme
            rman_subdiv = rfb_icons.get_icon("rman_subdiv")
            box.operator("mesh.rman_convert_subdiv",
                         text="Convert to Subdiv", icon_value=rman_subdiv.icon_id)

            # Add/Create RIB Box /
            # Create Archive node
            box.menu('VIEW3D_MT_RM_Add_Export_Menu', icon_value=bpy.types.VIEW3D_MT_RM_Add_Export_Menu.get_icon_id())

        layout.separator()
        layout.label(text="Lights:")
        box = layout.box()

        box.menu('VIEW3D_MT_RM_Add_Light_Menu', text='Add Light', icon_value=bpy.types.VIEW3D_MT_RM_Add_Light_Menu.get_icon_id())
        box.menu('VIEW3D_MT_RM_Add_LightFilter_Menu', text='Add Light Filter', icon_value=bpy.types.VIEW3D_MT_RM_Add_LightFilter_Menu.get_icon_id())               

        # Editors
        layout.separator()
        layout.label(text="Editors:")
        box = layout.box()
        box.operator('scene.rman_open_light_mixer_editor', text='Light Mixer')
        box.operator('scene.rman_open_light_linking', text='Light Linking')
        box.operator('scene.rman_open_groups_editor', text='Trace Sets')
        rman_vol_agg = rfb_icons.get_icon("rman_vol_aggregates")
        box.operator('scene.rman_open_vol_aggregates_editor', text='Volume Aggregates', icon_value=rman_vol_agg.icon_id)

        layout.separator()
        layout.label(text="Apps:")
        box = layout.box()
        rman_it = rfb_icons.get_icon("rman_it")
        box.operator("renderman.start_it", icon_value=rman_it.icon_id)  
        rman_lq = rfb_icons.get_icon("rman_localqueue")
        box.operator("renderman.start_localqueue", icon_value=rman_lq.icon_id)          
        rman_lapp = rfb_icons.get_icon("rman_licenseapp")
        box.operator("renderman.start_licenseapp", icon_value=rman_lapp.icon_id)        
        
        # Diagnose
        layout.separator()
        layout.label(text='Diagnose:')
        box = layout.box()
        box.enabled = not is_rman_interactive_running
        rman_rib = rfb_icons.get_icon('rman_rib_small')
        box.operator("renderman.open_scene_rib", text='View RIB', icon_value=rman_rib.icon_id)
        if selected_objects or selected_light_objects:
            box.operator("renderman.open_selected_rib", text='View Selected RIB', icon_value=rman_rib.icon_id)

        # Utilities
        layout.separator()
        layout.label(text='Utilities:')
        box = layout.box()
        rman_addon_prefs = rfb_icons.get_icon('rman_loadplugin')
        op = box.operator("preferences.addon_show", text="Addon Preferences", icon_value=rman_addon_prefs.icon_id)
        op.module = "RenderManForBlender"
        rman_pack_scene = rfb_icons.get_icon('rman_package_scene')
        box.operator("renderman.scene_package", icon_value=rman_pack_scene.icon_id)
        box.operator("renderman.upgrade_scene", icon='FILE_REFRESH')

        layout.separator()
        # RenderMan Doc
        layout.label(text="Help:")
        rman_help = rfb_icons.get_icon("rman_help")
        layout.operator("wm.url_open", text="RenderMan Docs",
                        icon_value=rman_help.icon_id).url = RFB_HELP_URL
        rman_info = rfb_icons.get_icon("rman_blender")
        layout.operator("renderman.about_renderman", icon_value=rman_info.icon_id)

class RENDER_PT_renderman_live_stats(bpy.types.Panel, _RManPanelHeader):
    bl_label = "RenderMan Live Statistics"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Renderman"

    def draw(self, context):

        layout = self.layout
        scene = context.scene
        rm = scene.renderman         
        rr = RmanRender.get_rman_render()
        prefs = prefs_utils.get_addon_prefs()
        if prefs_utils.using_qt():
            layout.separator()
            layout.operator("renderman.rman_open_stats")  
            layout.prop(prefs, 'rman_roz_stats_print_level')        
        else:    
            layout.prop(prefs, 'rman_roz_stats_print_level')    
            server_id = rr.stats_mgr.assign_server_id_func()
            if server_id:
                layout.label(text='Connected: %s' % server_id)
            else:
                layout.label(text='No render active')            
      
            box = layout.box()

            for label in rr.stats_mgr.stats_to_draw:
                data = rr.stats_mgr.render_live_stats[label]        
                box.label(text='%s: %s' % (label, data))        
            #if rr.rman_running:   
            if rr.rman_context.is_render_running():
                box.prop(rm, 'roz_stats_iterations', slider=True, text='Iterations (%d / %d)' % (rr.stats_mgr._iterations, rr.stats_mgr._maxSamples))
                box.prop(rm, 'roz_stats_progress', slider=True)            
            '''
            if rr.stats_mgr.web_socket_enabled:
                if rr.stats_mgr.is_connected():
                    for label in rr.stats_mgr.stats_to_draw:
                        data = rr.stats_mgr.render_live_stats[label]        
                        box.label(text='%s: %s' % (label, data))        
                    #if rr.rman_running:   
                    if rr.rman_context.is_render_running():
                        box.prop(rm, 'roz_stats_iterations', slider=True, text='Iterations (%d / %d)' % (rr.stats_mgr._iterations, rr.stats_mgr._maxSamples))
                        box.prop(rm, 'roz_stats_progress', slider=True)
                
                    prefs = prefs_utils.get_addon_prefs()
                    layout.prop(prefs, 'rman_roz_stats_print_level')
                else:
                    box.label(text='(not connected)')
                    layout.operator('renderman.attach_stats_render')
            else:
                box.label(text='(live stats disabled)')                        
            '''
 
classes = [
    PRMAN_PT_Renderman_UI_Panel,
    RENDER_PT_renderman_live_stats
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes) 

def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)     