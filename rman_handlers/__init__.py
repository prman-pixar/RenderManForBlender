from ..rfb_logger import rfb_log
from ..rfb_utils import texture_utils
from ..rfb_utils import string_utils
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import upgrade_utils
from ..rfb_utils.display_utils import BLENDER_TO_RMAN_DSPY
from ..rfb_utils.envconfig_utils import envconfig
from ..rman_constants import RMAN_FAKE_NODEGROUP, BLENDER_50
from bpy.app.handlers import persistent
import bpy
import os
import re
import sys
            

ORIGINAL_BL_FILEPATH = None
ORIGINAL_BL_FILE_FORMAT = None
ORIGINAL_BL_MEDIA_FORMAT = None

def set_qn_env_vars(bl_scene):
    if not bl_scene or not isinstance(bl_scene, bpy.types.Scene):
        bl_scene = bpy.context.scene
    envconfig().set_qn_env_vars(bl_scene)

@persistent
def rman_load_post(bl_scene):
    from ..rman_ui import rman_ui_light_handlers
    from ..rfb_utils import scene_utils
    
    string_utils.update_blender_tokens_cb(bl_scene)
    rman_ui_light_handlers.clear_gl_tex_cache(bl_scene)
    texture_utils.txmanager_load_cb(bl_scene)
    upgrade_utils.upgrade_scene(bl_scene)
    scene_utils.add_global_vol_aggregate()
    set_qn_env_vars(bl_scene)

@persistent
def rman_save_pre(bl_scene):
    string_utils.update_blender_tokens_cb(bl_scene)
    shadergraph_utils.save_bl_ramps(bl_scene)
    upgrade_utils.update_version(bl_scene)

@persistent
def rman_save_post(bl_scene):
    texture_utils.txmanager_pre_save_cb(bl_scene)

@persistent
def frame_change_post(bl_scene):
    # update frame number
    string_utils.update_frame_token(bl_scene.frame_current)        

@persistent
def despgraph_post_handler(bl_scene, depsgraph):    
    if len(depsgraph.updates) < 1 and depsgraph.id_type_updated('NODETREE'):    
        # Updates is empty. Assume this is a change to our ramp
        # nodes in one of our fake nodegroup
        # Since we don't know which ramp was updated, just call update_tag
        # on all of them
        rfb_log().debug("DepsgraphUpdates is empty. Assume this is a ramp edit.")
        for ng in bpy.data.node_groups:
            if not ng.name.startswith(RMAN_FAKE_NODEGROUP):
                continue
            users = bpy.context.blend_data.user_map(subset={ng})
            for o in users[ng]:
                if isinstance(o, bpy.types.Material):
                    o.node_tree.update_tag()
                elif isinstance(o, bpy.types.Light):
                    o.node_tree.update_tag()
                elif isinstance(o, bpy.types.World):
                    o.update_tag()
                elif isinstance(o, bpy.types.Camera):
                    o.update_tag()

    for update in depsgraph.updates:
        texture_utils.depsgraph_handler(update, depsgraph)
        if not bl_scene.renderman.use_blender_light_link:
            continue

        ob = update.id
        if isinstance(ob, bpy.types.Object) and ob.type == 'LIGHT':
            # check if we need to invert the light linking behavior for this light
            # light linking needs to be inverted if *all* objects in the collection are set
            # to exclude. i.e.: if all objects are excluded, the objects in the collection
            # are not illuminated, and the objects *not* in the collection are illuminated
            if ob.light_linking.receiver_collection:
                prev_val = ob.original.renderman.bl_invert_ll
                all_exclude = True
                for i, o in enumerate(ob.light_linking.receiver_collection.objects):
                    if ob.light_linking.receiver_collection.collection_objects[i].light_linking.link_state == 'INCLUDE':
                        all_exclude = False
                        break
                if prev_val != all_exclude:
                    ob.original.renderman.bl_invert_ll = all_exclude
            if ob.light_linking.blocker_collection:
                prev_val = ob.original.renderman.bl_invert_blocker_ll
                all_exclude = True
                for i, o in enumerate(ob.light_linking.blocker_collection.objects):
                    if ob.light_linking.blocker_collection.collection_objects[i].light_linking.link_state == 'INCLUDE':
                        all_exclude = False
                        break               
                if prev_val != all_exclude:
                    ob.original.renderman.bl_invert_blocker_ll = all_exclude                    
        
@persistent
def render_pre(bl_scene):
    '''
    render_pre handler that changes the Blender filepath attribute
    to what the user wants in the workspace editor (path_comp_image_output)
    '''
    global ORIGINAL_BL_FILEPATH
    global ORIGINAL_BL_FILE_FORMAT
    global ORIGINAL_BL_MEDIA_FORMAT

    if bl_scene.render.engine != 'PRMAN_RENDER':
        return

    ORIGINAL_BL_FILEPATH = bl_scene.render.filepath
    ORIGINAL_BL_FILE_FORMAT = bl_scene.render.image_settings.file_format         
    filepath = string_utils.expand_string(bl_scene.renderman.path_comp_image_output, frame='#')
    bl_scene.render.use_file_extension = True
    bl_scene.render.filepath = filepath
    if BLENDER_50: 
        ORIGINAL_BL_MEDIA_FORMAT = bl_scene.render.image_settings.media_type
        bl_scene.render.image_settings.media_type = 'IMAGE'
    if ORIGINAL_BL_FILE_FORMAT not in BLENDER_TO_RMAN_DSPY:
        # user has selected a image format we don't support, fallback to OpenEXR
        bl_scene.render.image_settings.file_format = 'OPEN_EXR'            

@persistent
def render_post(bl_scene):
    '''
    render_post handler that puts the Blender filepath attribute back
    to its original value. 
    '''

    global ORIGINAL_BL_FILEPATH
    global ORIGINAL_BL_FILE_FORMAT
    global ORIGINAL_BL_MEDIA_FORMAT

    if bl_scene.render.engine != 'PRMAN_RENDER':
        return    
    if BLENDER_50:
        bl_scene.render.image_settings.media_type = ORIGINAL_BL_MEDIA_FORMAT
    bl_scene.render.filepath = ORIGINAL_BL_FILEPATH
    bl_scene.render.image_settings.file_format = ORIGINAL_BL_FILE_FORMAT

@persistent
def render_stop(bl_scene):
    from .. import rman_render
    rr = rman_render.RmanRender.get_rman_render()
    if rr.rman_context.is_regular_rendering():
        rfb_log().debug("Render stop handler called. Try to stop the renderer.")
        rr.stop_render()

def register():

    # load_post handler
    if rman_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(rman_load_post)

    # save_pre handler
    if rman_save_pre not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(rman_save_pre)

    # save_post handler       
    if rman_save_post not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(rman_save_post)      

    # depsgraph_update_post handler
    if despgraph_post_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(despgraph_post_handler)

    if frame_change_post not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(frame_change_post)        

    if render_pre not in bpy.app.handlers.render_pre:
        bpy.app.handlers.render_pre.append(render_pre)

    if render_post not in bpy.app.handlers.render_post:
        bpy.app.handlers.render_post.append(render_post) 

    if not bpy.app.background:
        if render_stop not in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.append(render_stop)

        if render_stop not in bpy.app.handlers.render_cancel:
            bpy.app.handlers.render_cancel.append(render_stop)

def unregister():

    if rman_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(rman_load_post)

    if rman_save_pre in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(rman_save_pre)

    if rman_save_post in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(rman_save_post)

    if despgraph_post_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(despgraph_post_handler)     

    if frame_change_post in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(frame_change_post)

    if render_pre in bpy.app.handlers.render_pre:
        bpy.app.handlers.render_pre.remove(render_pre)

    if render_post in bpy.app.handlers.render_post:
        bpy.app.handlers.render_post.remove(render_post)            

    if render_stop in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.remove(render_stop)

    if render_stop in bpy.app.handlers.render_cancel:
        bpy.app.handlers.render_cancel.remove(render_stop)

    from . import rman_it_handlers
    rman_it_handlers.remove_ipr_to_it_handlers()                
