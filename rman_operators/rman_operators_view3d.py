import bpy
import os
import subprocess
from ..rfb_utils.scene_utils import EXCLUDED_OBJECT_TYPES
from ..rfb_utils.envconfig_utils import envconfig
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import object_utils
from ..rfb_utils import string_utils
from ..rfb_utils import prefs_utils
from ..rfb_logger import rfb_log
from .. import rfb_icons
from ..rman_constants import RFB_ADDON_VERSION_STRING
from ..rfb_utils.operator_utils import get_bxdf_items, get_light_items, get_lightfilter_items, get_description
from bpy.props import EnumProperty, StringProperty, BoolProperty
import mathutils
import math
import time

class PRMAN_OT_RM_Add_RenderMan_Geometry(bpy.types.Operator):
    bl_idname = "object.rman_add_rman_geo"
    bl_label = "Add RenderMan Geometry"
    bl_description = "Add RenderMan specific geometry"
    bl_options = {"REGISTER"}

    rman_prim_type: StringProperty(name='rman_prim_type', default='QUADRIC',
        options={'HIDDEN'})
    bl_prim_type: StringProperty(name='bl_prim_type', default='',
        options={'HIDDEN'})        
    rman_quadric_type: StringProperty(name='rman_quadric_type', default='SPHERE',
        options={'HIDDEN'})
    rman_default_name: StringProperty(name='rman_default_name', default='RiPrimitive',
        options={'HIDDEN'})
    rman_open_filebrowser: BoolProperty(name='rman_open_filebrowser', default=False,
        options={'HIDDEN'})
    rman_convert_to_zup: BoolProperty(name="Convert to Z-Up", default=False,
        description="Rotate the object so it is Z-up")
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")

    filename: bpy.props.StringProperty(
        subtype="FILE_NAME",
        default="")    

    filter_glob: StringProperty(
        default="*.*",
        options={'HIDDEN'},
        )        

    @classmethod
    def description(cls, context, properties):    
        info = cls.bl_description
        if properties.rman_prim_type == 'QUADRIC':
            if properties.rman_quadric_type == 'SPHERE':
                info = "Create a RenderMan sphere quadric."
            elif properties.rman_quadric_type == 'CYLINDER':
                info = "Create a RenderMan cylinder quadric."
            elif properties.rman_quadric_type == 'CONE':
                info = "Create a RenderMan cone quadric."
            elif properties.rman_quadric_type == 'DISK':
                info = "Create a RenderMan disk quadric." 
            elif properties.rman_quadric_type == 'TORUS':
                info = "Create a RenderMan torus quadric."                 
        elif properties.rman_prim_type == 'RI_VOLUME':
            info = "Create a volume object"
        elif properties.rman_prim_type == 'DELAYED_LOAD_ARCHIVE':
            info = "Load a RIB Archive."                 
        elif properties.rman_prim_type == 'PROCEDURAL_RUN_PROGRAM':
            info = "Load a RenderMan RunProgram procedural."             
        elif properties.rman_prim_type == 'ALEMBIC':
            info = "Load an Alembic archive and use the RenderMan Alembic procedural to render it."            
        elif properties.rman_prim_type == 'DYNAMIC_LOAD_DSO':
            info = "Load a RenderMan procedural DSO."
        elif properties.rman_prim_type == 'BRICKMAP':
            info = "Create a brickmap object. This allows you to load a brickmap (.bkm) file and use it as geometry."
        elif properties.bl_prim_type == 'VOLUME':
            info = "Create a OpenVDB object."

        return info    

    def execute(self, context):

        ob = None
        nm = self.rman_default_name
        data_block = None
        if self.properties.bl_prim_type == 'VOLUME':
            data_block = bpy.data.volumes.new(nm)
                    
        ob = bpy.data.objects.new(nm, data_block)
        
        ob.empty_display_type = 'PLAIN_AXES'
        rm = ob.renderman
        rm.hide_primitive_type = True
        if self.properties.rman_prim_type:
            rm.primitive = self.properties.rman_prim_type
        if rm.primitive == 'QUADRIC':
            rm.rman_quadric_type = self.properties.rman_quadric_type 
            ob.name = 'Ri%s' % rm.rman_quadric_type.capitalize()
            if rm.rman_quadric_type == 'SPHERE':
                ob.empty_display_type = 'SPHERE'  
        else:   
            if rm.primitive == 'RI_VOLUME':
                ob.empty_display_type = 'CUBE'
                mat = shadergraph_utils.create_bxdf('PxrVolume')
                ob.renderman.rman_material_override = mat
            elif self.properties.bl_prim_type == 'VOLUME':
                mat = shadergraph_utils.create_bxdf('PxrVolume')
                ob.active_material = mat
                output = shadergraph_utils.find_node(mat, 'RendermanOutputNode')
                bxdf = output.inputs['bxdf_in'].links[0].from_node
                bxdf.densityFloatPrimVar = 'density'           

        if self.properties.rman_open_filebrowser or self.filepath != "":
            if rm.primitive == 'DELAYED_LOAD_ARCHIVE':
                ob.empty_display_type = 'CUBE'
                rm.path_archive = self.properties.filepath
                # try to get the bounding box from the RIB file
                with open(string_utils.expand_string(rm.path_archive,asFilePath=True)) as f:
                    for ln in f.readlines():
                        if not ln.startswith('##bbox: '):
                            continue
                        tokens = ln.replace('##bbox: ', '').split(' ')
                        min_x, max_x, min_y, max_y, min_z, max_z = tokens
                        max_scale = max(max(float(max_x), float(max_y)), float(max_z))
                        ob.empty_display_size = max_scale
                        break

            elif rm.primitive == 'PROCEDURAL_RUN_PROGRAM':
                rm.runprogram_path = self.properties.filepath
            elif rm.primitive == 'DYNAMIC_LOAD_DSO':
                rm.path_dso = self.properties.filepath
            elif rm.primitive == 'BRICKMAP':  
                rm.bkm_filepath = self.properties.filepath          
            elif self.properties.bl_prim_type == 'VOLUME':        
                ob.data.filepath = self.properties.filepath
            elif rm.primitive == 'ALEMBIC':        
                rm.abc_filepath = self.properties.filepath     

        if self.properties.rman_convert_to_zup:
            yup_to_zup = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
            ob.matrix_world = yup_to_zup @ ob.matrix_world                               

        context.scene.collection.objects.link(ob)
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob  
        ob.location = context.scene.cursor.location
        
        return {"FINISHED"}    
        
    def invoke(self, context, event=None):

        if self.properties.rman_open_filebrowser:
            if self.properties.rman_prim_type == 'DELAYED_LOAD_ARCHIVE':
                self.properties.filter_glob = "*.rib"     
            elif self.properties.rman_prim_type  == 'BRICKMAP': 
                self.properties.filter_glob = "*.bkm"
            elif self.properties.rman_prim_type  == 'DYNAMIC_LOAD_DSO': 
                self.properties.filter_glob = "*.so;*.dll"                
            elif self.properties.bl_prim_type == 'VOLUME':
                self.properties.filter_glob = "*.vdb"
            elif self.properties.rman_prim_type == 'ALEMBIC':
                self.properties.filter_glob = "*.abc"                
            context.window_manager.fileselect_add(self)
            return{'RUNNING_MODAL'}          
        return self.execute(context)

class PRMAN_OT_RM_Add_Subdiv_Scheme(bpy.types.Operator):
    bl_idname = "mesh.rman_convert_subdiv"
    bl_label = "Convert to RenderMan Subdiv"
    bl_description = "Convert selected object to a RenderMan subdivision surface. Note, this will take precedence over any subdiv modifiers that are already attached to the object."
    bl_options = {"REGISTER"}

    def execute(self, context):
        for ob in context.selected_objects:
            if ob.type == 'MESH':
                rm = ob.data.renderman
                rm.rman_subdiv_scheme = 'catmull-clark'
                ob.update_tag(refresh={'DATA'})

        return {"FINISHED"}    

class PRMAN_OT_RM_Add_Light(bpy.types.Operator):
    bl_idname = "object.rman_add_light"
    bl_label = "Add RenderMan Light"
    bl_description = "Add a new RenderMan light to the scene"
    bl_options = {"REGISTER", "UNDO"}

    def get_type_items(self, context):
        return get_light_items()

    rman_light_name: EnumProperty(items=get_type_items, name="Light Name")

    @classmethod
    def description(cls, context, properties):    
        info = get_description('light', properties.rman_light_name)
        return info

    def execute(self, context):
        light = bpy.data.lights.new(self.rman_light_name, 'AREA')
        light_ob = bpy.data.objects.new(self.rman_light_name, light)
        light_ob.location = context.scene.cursor.location
        
        light.renderman.renderman_light_role = 'RMAN_LIGHT'
        light.renderman.renderman_lock_light_type = True
        light.use_nodes = True
        light.renderman.use_renderman_node = True
        shadergraph_utils.hide_cycles_nodes(light)

        nt = light.node_tree
        output = nt.nodes.new('RendermanOutputNode')                 
        default = nt.nodes.new('%sLightNode' % self.rman_light_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[1])           
        output.inputs[0].hide = True
        output.inputs[2].hide = True
        output.inputs[3].hide = True          
        light.renderman.renderman_light_shader = self.rman_light_name  

        context.scene.collection.objects.link(light_ob)
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        light_ob.select_set(True)
        context.view_layer.objects.active = light_ob        

        return {"FINISHED"}

class PRMAN_OT_RM_Add_Light_Filter(bpy.types.Operator):
    bl_idname = "object.rman_add_light_filter"
    bl_label = "Add RenderMan Light Filter"
    bl_description = "Add a new RenderMan light filter to the scene"
    bl_options = {"REGISTER", "UNDO"}

    def get_type_items(self, context):
        return get_lightfilter_items()

    rman_lightfilter_name: EnumProperty(items=get_type_items, name="Light Filter Name")
    add_to_selected: BoolProperty(default=True)

    @classmethod
    def description(cls, context, properties):    
        info = get_description('lightfilter', properties.rman_lightfilter_name)
        return info    

    def create_lightfilter(self, context, create_at_cursor=True):
        light_filter = bpy.data.lights.new(self.rman_lightfilter_name, 'AREA')
        light_filter_ob = bpy.data.objects.new(self.rman_lightfilter_name, light_filter)  
        do_parent = prefs_utils.get_pref('rman_parent_lightfilter')
        if create_at_cursor:
            light_filter_ob.location = context.scene.cursor.location

        light_filter.renderman.renderman_light_role = 'RMAN_LIGHTFILTER'
        light_filter.renderman.renderman_lock_light_type = True
        light_filter.use_nodes = True
        light_filter.renderman.use_renderman_node = True
        shadergraph_utils.hide_cycles_nodes(light_filter)

        nt = light_filter.node_tree
        output = nt.nodes.new('RendermanOutputNode')
        default = nt.nodes.new('%sLightfilterNode' % self.rman_lightfilter_name)
        default.location = output.location
        default.location[0] -= 300
        nt.links.new(default.outputs[0], output.inputs[3])   
        output.inputs[0].hide = True
        output.inputs[1].hide = True
        output.inputs[2].hide = True   
        light_filter.renderman.renderman_light_filter_shader = self.rman_lightfilter_name

        context.scene.collection.objects.link(light_filter_ob)
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        light_filter_ob.select_set(True)
        context.view_layer.objects.active = light_filter_ob             

        return light_filter_ob        

    def execute(self, context):
        selected_objects = context.selected_objects
        if self.properties.add_to_selected:
            if not selected_objects:
                light_filter_ob = self.create_lightfilter(context)
            else:
                light_filter_ob = None
                do_parent = prefs_utils.get_pref('rman_parent_lightfilter')
                if not do_parent:
                    light_filter_ob = self.create_lightfilter(context)
                for ob in selected_objects:
                    rman_type = object_utils._detect_primitive_(ob)
                    if rman_type == 'LIGHT':
                        if do_parent:
                            light_filter_ob = self.create_lightfilter(context, create_at_cursor=False)
                            light_filter_ob.parent = ob
                        light_filter_item = ob.data.renderman.light_filters.add()
                        light_filter_item.linked_filter_ob = light_filter_ob
                    elif shadergraph_utils.is_mesh_light(ob):
                        mat = ob.active_material
                        if mat:
                            if do_parent:
                                light_filter_ob = self.create_lightfilter(context, create_at_cursor=False)
                                light_filter_ob.parent = ob
                            light_filter_item = mat.renderman_light.light_filters.add()
                            light_filter_item.linked_filter_ob = light_filter_ob
        else:
            light_filter_ob = self.create_lightfilter(context)

        return {"FINISHED"}        

class PRMAN_OT_RM_Add_bxdf(bpy.types.Operator):
    bl_idname = "object.rman_add_bxdf"
    bl_label = "Add BXDF"
    bl_description = "Add a new Bxdf to selected object"
    bl_options = {"REGISTER", "UNDO"}

    def get_type_items(self, context):
        return get_bxdf_items()  

    bxdf_name: EnumProperty(items=get_type_items, name="Bxdf Name")

    @classmethod
    def description(cls, context, properties):
        info = get_description('bxdf', properties.bxdf_name)
        return info

    def execute(self, context):
        selected_object = getattr(context, "selected_obj", None)
        if selected_object:
            selection = [selected_object]
        else:
            selection = bpy.context.selected_objects if hasattr(
                bpy.context, 'selected_objects') else []
        bxdf_name = self.properties.bxdf_name
        mat = shadergraph_utils.create_bxdf(bxdf_name)
        for obj in selection:
            if(obj.type not in EXCLUDED_OBJECT_TYPES):
                if obj.type == 'EMPTY':
                    obj.renderman.rman_material_override = mat
                else:
                    material_slots = getattr(obj, 'material_slots', None)
                    if material_slots is None:
                        continue
                    if len(material_slots) < 1:
                        obj.active_material = mat
                    else:
                        material_slot = material_slots[0]
                        material_slot.material = mat
                        obj.active_material_index = 0
                        obj.active_material = mat      
        return {"FINISHED"}  

class PRMAN_OT_RM_Create_MeshLight(bpy.types.Operator):
    bl_idname = "object.rman_create_meshlight"
    bl_label = "Create Mesh Light"
    bl_description = "Convert the selected object to a mesh light"
    bl_options = {"REGISTER", "UNDO"}

    def create_mesh_light_material(self, context):
        mat = bpy.data.materials.new("PxrMeshLight")
        mat.use_nodes = True
        nt = mat.node_tree
        shadergraph_utils.hide_cycles_nodes(mat)

        output = nt.nodes.new('RendermanOutputNode')
        geoLight = nt.nodes.new('PxrMeshLightLightNode')
        geoLight.location[0] -= 300
        geoLight.location[1] -= 420
        if(output is not None):
            nt.links.new(geoLight.outputs[0], output.inputs[1])

        # add PxrBlack Bxdf
        default = nt.nodes.new('PxrBlackBxdfNode')
        default.location = output.location
        default.location[0] -= 300
        if (default is not None):
            nt.links.new(default.outputs[0], output.inputs[0])

        output.inputs[3].hide = True        
        default.update_mat(mat)    

        return mat

    def execute(self, context):
        selection = bpy.context.selected_objects 

        for obj in selection:
            if(obj.type not in EXCLUDED_OBJECT_TYPES):
                if shadergraph_utils.is_mesh_light(obj):
                    continue
                if obj.type == 'EMPTY':
                    continue
                mat = self.create_mesh_light_material(context)
                material_slots = getattr(obj, 'material_slots', None)

                if material_slots is None:
                    continue
                if len(material_slots) < 1:
                    obj.active_material = mat
                else:
                    material_slot = material_slots[0]
                    material_slot.material = mat
                    obj.active_material_index = 0
                    obj.active_material = mat             

        return {"FINISHED"}

class PRMAN_OT_Renderman_start_it(bpy.types.Operator):
    bl_idname = 'renderman.start_it'
    bl_label = "'it'"
    bl_description = "Start RenderMan's it"

    def execute(self, context):
        it_path = envconfig().rman_it_path
        if not it_path:
            self.report({"ERROR"},
                        "Could not find 'it'.")
        else:
            environ = envconfig().copyenv()
            subprocess.Popen([it_path], env=environ, close_fds=True)
        return {'FINISHED'}        

class PRMAN_OT_Renderman_start_localqueue(bpy.types.Operator):
    bl_idname = 'renderman.start_localqueue'
    bl_label = "Local Queue"
    bl_description = "Start LocalQueue"

    def execute(self, context):
        lq_path = envconfig().rman_lq_path
        if not lq_path:
            self.report({"ERROR"},
                        "Could not find LocalQueue.")
        else:
            environ = envconfig().copyenv()
            subprocess.Popen([lq_path], env=environ, close_fds=True)
        return {'FINISHED'}        

class PRMAN_OT_Renderman_start_licenseapp(bpy.types.Operator):
    bl_idname = 'renderman.start_licenseapp'
    bl_label = "LicenseApp"
    bl_description = "Start LicenseApp"

    def execute(self, context):
        lapp_path = envconfig().rman_license_app_path
        if not lapp_path:
            self.report({"ERROR"},
                        "Could not find LicenseApp.")
        else:
            environ = envconfig().copyenv()
            subprocess.Popen([lapp_path], env=environ, close_fds=True)
        return {'FINISHED'}           

class PRMAN_OT_Select_Cameras(bpy.types.Operator):
    bl_idname = "object.select_cameras"
    bl_label = "Select Cameras"

    Camera_Name: bpy.props.StringProperty(default="")

    def execute(self, context):

        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[self.Camera_Name].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[self.Camera_Name]

        return {'FINISHED'}


class PRMAN_MT_Camera_List_Menu(bpy.types.Menu):
    #bl_idname = "object.camera_list_menu"
    bl_label = "Camera list"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        cameras = [
            obj for obj in bpy.context.scene.objects if obj.type == "CAMERA"]

        if len(cameras):
            for cam in cameras:
                name = cam.name
                op = layout.operator(
                    "object.select_cameras", text=name, icon='CAMERA_DATA')
                op.Camera_Name = name

        else:
            layout.label(text="No Camera in the Scene")

class PRMAN_OT_Deletecameras(bpy.types.Operator):
    bl_idname = "object.delete_cameras"
    bl_label = "Delete Cameras"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        type_camera = bpy.context.object.data.type
        bpy.ops.object.delete()

        camera = [obj for obj in bpy.context.scene.objects if obj.type ==
                  "CAMERA" and obj.data.type == type_camera]

        if len(camera):
            camera[0].select = True
            bpy.context.view_layer.objects.active = camera[0]
            return {"FINISHED"}

        else:
            return {"FINISHED"}


class PRMAN_OT_AddCamera(bpy.types.Operator):
    bl_idname = "object.add_prm_camera"
    bl_label = "Add Camera"
    bl_description = "Add a Camera in the Scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        bpy.context.space_data.lock_camera = False

        bpy.ops.object.camera_add()

        bpy.ops.view3d.object_as_camera()

        bpy.ops.view3d.view_camera()

        bpy.ops.view3d.camera_to_view()

        bpy.context.object.data.clip_end = 10000
        bpy.context.object.data.lens = 85

        return {"FINISHED"}

class PRMAN_OT_Renderman_open_stats(bpy.types.Operator):
    bl_idname = 'renderman.open_stats'
    bl_label = "Open Frame Stats"
    bl_description = "Open Current Frame stats file"

    def execute(self, context):
        scene = context.scene
        rm = scene.renderman        
        output_dir = string_utils.expand_string(rm.path_rib_output, 
                                                asFilePath=True)  
        output_dir = os.path.dirname(output_dir)            
        bpy.ops.wm.url_open(
            url="file://" + os.path.join(output_dir, 'stats.%04d.xml' % scene.frame_current))
        return {'FINISHED'}

class PRMAN_OT_Renderman_Open_About_Renderman(bpy.types.Operator):
    bl_idname = "renderman.about_renderman"
    bl_label = "About RenderMan" 
    bl_description = "About RenderMan"

    def get_notices(self, context):
        items = []
        items.append(('NULL', 'Select Notce', ''))
        notices_files = []
        notices_path = os.path.join(envconfig().rmantree, 'etc', 'notices')
        for (_, _, filenames) in os.walk(notices_path):
            notices_files.extend(filenames)
            break

        for nfl in notices_files:
            if nfl != "NOTICE":
                items.append((nfl, nfl, ''))
        return items

    notice_files: EnumProperty(name="Notice",
                            items=get_notices
    )

    def execute(self, context):
        return{'FINISHED'}     

    def _read_notice(self, box):
        if self.notice_files == 'NULL':
            return
        notices_path = os.path.join(envconfig().rmantree, 'etc', 'notices', self.notice_files)

        try:
            my_file = open(notices_path, 'r')
            lines = my_file.readlines()
            for line in lines:
                line = line.replace('\r', '')
                line = line.replace('\n', '')
                box.label(text='%s' % line)
            my_file.close()
        except IOError:
            return

    def draw(self, context):
        layout = self.layout     
        box = layout.box()
        box.scale_y = 0.4
        rman_icon = rfb_icons.get_icon('rman_blender')
        box.template_icon(rman_icon.icon_id, scale=10.0)
        box.label(text="")
        
        box.label(text='Version: %s' % envconfig().build_info.version())
        box.label(text='Linked: %s %s' % (envconfig().build_info.date(),
                                       envconfig().build_info.id()))
        box.label(text='Build: %s' % envconfig().build_info.name())
        box.label(text='Blender Addon Version: %s' % RFB_ADDON_VERSION_STRING)
        box.label(text='Scene Version: %s' % context.scene.renderman.renderman_version)
        
        timedata = time.localtime()
        thisyear = time.strftime("%Y", timedata)
        box.label(text='Copyright (c) 1996-%s Pixar Animation Studios' % thisyear)
        box.label(text='')
        box.label(text='The RenderMan rendering software may ship with and/or ')
        box.label(text='portions of the RenderMan rendering software may')
        box.label(text='include open source software. The following are')
        box.label(text='notices for and (if applicable) licenses governing the')
        box.label(text='open source software.')

        layout.prop(self, 'notice_files') 
        box = layout.box()
        box.scale_y = 0.4        
        self._read_notice(box)        

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)          

classes = [
    PRMAN_OT_RM_Add_RenderMan_Geometry,
    PRMAN_OT_RM_Add_Subdiv_Scheme,
    PRMAN_OT_RM_Add_Light,
    PRMAN_OT_RM_Add_Light_Filter,
    PRMAN_OT_RM_Add_bxdf,
    PRMAN_OT_RM_Create_MeshLight,
    PRMAN_OT_Renderman_start_it,
    PRMAN_OT_Renderman_start_localqueue,
    PRMAN_OT_Renderman_start_licenseapp,
    PRMAN_OT_Select_Cameras,
    PRMAN_MT_Camera_List_Menu,
    PRMAN_OT_Deletecameras,
    PRMAN_OT_AddCamera,    
    PRMAN_OT_Renderman_open_stats,
    PRMAN_OT_Renderman_Open_About_Renderman
]            

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes)
    
def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)