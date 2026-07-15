import bpy
import os
from ..rfb_logger import rfb_log
from ..rfb_utils.prefs_utils import get_pref
from ..rfb_utils import prefs_utils
from ..rfb_utils import string_utils
from ..rfb_utils import filepath_utils
from ..rman_render import RmanRender
from bpy.props import StringProperty, BoolProperty

class PRMAN_OT_Renderman_open_scene_RIB(bpy.types.Operator):
    bl_idname = 'renderman.open_scene_rib'
    bl_label = "View RIB."
    bl_description = "Generate RIB for the current frame and open in a text editor"

    def invoke(self, context, event=None):
        scene = context.scene
        rm = scene.renderman
        if not rm.is_rman_interactive_running:
            rm = scene.renderman     
            rm.enable_external_rendering = True
            anim_prev_val = rm.external_animation
            spool_prev_val = rm.queuing_system
            format_prev_val = rm.rib_format
            rm.external_animation = False
            rm.queuing_system = 'none'
            rm.rib_format = 'ASCII'
            bpy.ops.render.render(layer=context.view_layer.name)
            rm.enable_external_rendering = False
            rm.external_animation = anim_prev_val
            rm.queuing_system = spool_prev_val
            rm.rib_format = format_prev_val

            rib_output = string_utils.expand_string(rm.path_rib_output, 
                                                    asFilePath=True)   

            filepath_utils.view_file(rib_output)
        else:
            self.report({"ERROR"}, "Viewport rendering is on.")   

        return {'FINISHED'}

class PRMAN_OT_Open_Selected_RIB(bpy.types.Operator):
    bl_idname = "renderman.open_selected_rib"
    bl_label = "View Selected RIB"
    bl_description = "Open RIB for selected object"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def invoke(self, context, event=None):
        selected_objects = context.selected_objects
        if selected_objects:
            temp_dir = prefs_utils.get_bl_temp_dir()
            rib_output = os.path.join(temp_dir, 'selected.rib')
            rm = context.scene.renderman
            if not rm.is_rman_interactive_running:
                rman_render = RmanRender.get_rman_render()
                rman_render.start_export_rib_selected(context, rib_output, export_materials=True, export_all_frames=False)
                filepath_utils.view_file(rib_output)
            else:
                self.report({"ERROR"}, "Viewport rendering is on.")

        else:
            rfb_log().error("Nothing selected for RIB export.")

        return {'FINISHED'}  

class PRMAN_OT_Open_Dump_RIB(bpy.types.Operator):
    bl_idname = "renderman.open_dump_rib"
    bl_label = "View Dump RIB"
    bl_description = "Open Dump RIB"

    @classmethod
    def poll(cls, context):
        if context.engine != "PRMAN_RENDER":
            return False
        dump_rib_path = filepath_utils.get_dump_rib_path(context.scene.frame_current) 
        return os.path.exists(dump_rib_path)

    def execute(self, context):
        dump_rib_path = filepath_utils.get_dump_rib_path(context.scene.frame_current) 
        if os.path.exists(dump_rib_path):
            filepath_utils.view_file(dump_rib_path)
        else:
            self.report({"ERROR"}, "Dump RIB does not exists")

        return {'FINISHED'}            

class PRMAN_OT_ExportRIBObject(bpy.types.Operator):
    bl_idname = "export.rman_export_rib_archive"
    bl_label = "Export Object as RIB Archive"
    bl_description = "Export single object as a RIB archive for use in other blend files or for other uses"

    export_mat: BoolProperty(
        name="Export Material",
        description="Do you want to export the material?",
        default=True)

    export_all_frames: BoolProperty(
        name="Export All Frames",
        description="Export entire animation time frame",
        default=False)

    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")

    filename: bpy.props.StringProperty(
        subtype="FILE_NAME",
        default="")

    filter_glob: bpy.props.StringProperty(
        default="*.rib",
        options={'HIDDEN'},
        )            

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        selected_objects = context.selected_objects
        if selected_objects:
            export_path = self.filepath
            export_range = self.export_all_frames
            export_mats = self.export_mat
            rm = context.scene.renderman
            if not rm.is_rman_interactive_running:
                rman_render = RmanRender.get_rman_render()
                rman_render.start_export_rib_selected(context, export_path, export_materials=export_mats, export_all_frames=export_range)
            else:
                self.report({"ERROR"}, "Viewport rendering is on.")

        else:
            rfb_log().error("Nothing selected for RIB export.")

        return {'FINISHED'}

    def invoke(self, context, event=None):
        ob = context.object
        self.properties.filename = '%s.<F4>.rib' % ob.name
        context.window_manager.fileselect_add(self)
        return{'RUNNING_MODAL'}      

class PRMAN_OT_Set_RIB_Dump_Env(bpy.types.Operator):
    bl_idname = "renderman.set_rib_dump_env"
    bl_label = "Set/Unset RFB_DUMP_RIB"
    bl_description = "Set or Unset the RFB_DUMP_RIB environment variable"

    set_envvar: BoolProperty(name="", default=True)

    @classmethod
    def poll(cls, context):
        return (context.engine == "PRMAN_RENDER")
    
    def execute(self, context):
        from ..rfb_utils.envconfig_utils import envconfig

        if self.properties.set_envvar:
            envconfig().set_dump_rib_env()
        else:
            envconfig().unset_dump_rib_env()

        return {'FINISHED'}        

classes = [
    PRMAN_OT_Renderman_open_scene_RIB,
    PRMAN_OT_Open_Selected_RIB,
    PRMAN_OT_ExportRIBObject,
    PRMAN_OT_Set_RIB_Dump_Env,
    PRMAN_OT_Open_Dump_RIB
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes)
    
def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)
