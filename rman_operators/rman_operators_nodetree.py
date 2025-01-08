import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from .. import rman_cycles_convert
from ..rfb_utils import shadergraph_utils
from .. import rman_bl_nodes
from ..rfb_logger import rfb_log
from ..rfb_utils.operator_utils import get_bxdf_items, get_projection_items
from ..rman_render import RmanRender
from mathutils import Matrix
import math

class SHADING_OT_convert_all_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "material.rman_convert_all_cycles_shaders"
    bl_label = "Convert All Cycles to RenderMan"
    bl_description = "Convert all Cycles nodetrees to RenderMan. This is not guaranteed to work. It is still recommended to use RenderMan only nodes."
    bl_options = {'INTERNAL'}

    def execute(self, context):
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                mat.use_nodes = True            
            nt = mat.node_tree
            if shadergraph_utils.is_renderman_nodetree(mat):
                continue
            output = nt.nodes.new('RendermanOutputNode')
            try:
                if not rman_cycles_convert.convert_cycles_nodetree(mat, output):
                    pxr_disney_node = rman_bl_nodes.__BL_NODES_MAP__['PxrDisneyBsdf']
                    default = nt.nodes.new(pxr_disney_node)
                    default.location = output.location
                    default.location[0] -= 300
                    nt.links.new(default.outputs[0], output.inputs[0])
            except Exception as e:
                self.report({'ERROR'}, "Error converting " + mat.name)
                #self.report({'ERROR'}, str(e))
                # uncomment to debug conversion
                import traceback
                traceback.print_exc()

            for n in nt.nodes:
                n.select = False      

        # convert cycles vis settings
        for ob in context.scene.objects:
            if hasattr(ob, 'cycles_visibility'):
                if not ob.cycles_visibility.camera:
                    ob.renderman.rman_visibilityCamera = "0"
                if not ob.cycles_visibility.diffuse or not ob.cycles_visibility.glossy:
                    ob.renderman.rman_visibilityIndirect = "0"
                if not ob.cycles_visibility.transmission:
                    ob.renderman.rman_visibilityTransmission = "0"
            else:
                if not ob.visible_camera:
                    ob.renderman.rman_visibilityCamera = "0"
                if not ob.visible_diffuse or not ob.visible_glossy:
                    ob.renderman.rman_visibilityIndirect = "0"
                if not ob.visible_transmission:
                    ob.renderman.rman_visibilityTransmission = "0"                

            if ob.type == 'LIGHT' and not ob.data.use_nodes:
                if ob.data.type == 'POINT':
                    scale = ob.data.shadow_soft_size * 2
                    ob.scale = [scale, scale, scale]      
                    
        for light in bpy.data.lights:
            if light.renderman.use_renderman_node:
                continue
            if not light.use_nodes:
                light.use_nodes = True
            light_type = light.type
            light.renderman.light_primary_visibility = False
            nt = light.node_tree

            light_shader = ''
            if light_type == 'SUN':
                light_shader = 'PxrDistantLight'  
            elif light_type == 'HEMI':
                light_shader = 'PxrDomeLight'
            elif light_type == 'AREA':
                if light.shape == 'DISK':
                    light_shader = 'PxrDiskLight'
                elif light.shape == 'ELLIPSE':
                    light_shader = 'PxrSphereLight'
                else:
                    light_shader = 'PxrRectLight'
            elif light_type == 'SPOT':
                light_shader = 'PxrDiskLight'
            elif light_type == 'POINT':
                light_shader = 'PxrSphereLight' 
            else:
                light_shader = 'PxrRectLight'            

            #light.type = 'AREA'
            if hasattr(light, 'size'):
                light.size = 0.0
            light.type = 'POINT'

            light.renderman.use_renderman_node = True
            shadergraph_utils.hide_cycles_nodes(light)

            output = nt.nodes.new('RendermanOutputNode')
            node_name = rman_bl_nodes.__BL_NODES_MAP__[light_shader]
            default = nt.nodes.new(node_name)

            default.location = output.location
            default.location[0] -= 300
            nt.links.new(default.outputs[0], output.inputs[1])    

            output.inputs[0].hide = True
            output.inputs[2].hide = True
            output.inputs[3].hide = True      
            light.renderman.renderman_light_role = 'RMAN_LIGHT' 

            if light_type == 'SPOT':
                node = light.renderman.get_light_node()
                node.coneAngle = math.degrees(light.spot_size)
                node.coneSoftness = light.spot_blend                    

            for n in nt.nodes:
                n.select = False   

        return {'FINISHED'}

class SHADING_OT_convert_cycles_to_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "material.rman_convert_cycles_shader"
    bl_label = "Convert Cycles Shader"
    bl_description = "Try to convert the current Cycles Shader to RenderMan. This is not guaranteed to work. It is still recommended to use RenderMan only nodes."
    bl_options = {'INTERNAL'}

    idtype: StringProperty(name="ID Type", default="material")
    bxdf_name: StringProperty(name="Bxdf Name", default="LamaSurface")

    def execute(self, context):
        idtype = self.properties.idtype
        if idtype == 'node_editor':
            idblock = context.space_data.id
            idtype = 'material'
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]
            if not idblock:
                # try getting material from context.object
                ob = context.object
                rm = ob.renderman
                idblock = rm.rman_material_override            

        if not idblock.use_nodes:
            idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':
            output = nt.nodes.new('RendermanOutputNode')
            if idblock.grease_pencil:
                shadergraph_utils.convert_grease_pencil_mat(idblock, nt, output)

            elif not rman_cycles_convert.convert_cycles_nodetree(idblock, output):
                bxdf_node_name = rman_bl_nodes.__BL_NODES_MAP__[self.properties.bxdf_name]
                default = nt.nodes.new(bxdf_node_name)
                default.location = output.location
                default.location[0] -= 300
                nt.links.new(default.outputs[0], output.inputs[0])

                if idblock.renderman.copy_color_params:
                    default.diffuseColor = idblock.diffuse_color
                    default.diffuseGain = idblock.diffuse_intensity
                    default.enablePrimarySpecular = True
                    default.specularFaceColor = idblock.specular_color

            output.inputs[3].hide = True

        for n in nt.nodes:
            n.select = False               
                      
        return {'FINISHED'}

class SHADING_OT_add_renderman_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "material.rman_add_rman_nodetree"
    bl_label = "Add RenderMan Nodetree"
    bl_description = "Add a RenderMan shader node tree"
    bl_options = {'INTERNAL'}    

    idtype: StringProperty(name="ID Type", default="material")

    def get_type_items(self, context):
        return get_bxdf_items()

    bxdf_name: EnumProperty(items=get_type_items, name="Material") 

    def execute(self, context):
        idtype = self.properties.idtype
        if idtype == 'node_editor':
            idblock = context.space_data.id
            idtype = 'material'
        elif idtype == 'world':
            idblock = context.scene.world
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]
            if not idblock:
                # try getting material from context.object
                ob = context.object
                rm = ob.renderman
                idblock = rm.rman_material_override

        # nt = bpy.data.node_groups.new(idblock.name,
        #                              type='RendermanPatternGraph')
        #nt.use_fake_user = True
        if not idblock.use_nodes:
            idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':
            shadergraph_utils.hide_cycles_nodes(idblock)
            output = nt.nodes.new('RendermanOutputNode')
            if idblock.grease_pencil:
                shadergraph_utils.convert_grease_pencil_mat(idblock, nt, output)

            else:
                bxdf_node_name = rman_bl_nodes.__BL_NODES_MAP__[self.properties.bxdf_name]
                default = nt.nodes.new(bxdf_node_name)
                default.location = output.location
                default.location[0] -= 300
                nt.links.new(default.outputs[0], output.inputs[0])

                if self.properties.bxdf_name == 'PxrLayerSurface':
                    shadergraph_utils.create_pxrlayer_nodes(nt, default)

                default.update_mat(idblock)    

            output.inputs[3].hide = True
                      
        elif idtype == 'light':
            light_type = idblock.type
            light = idblock

            light_shader = ''
            if light_type == 'SUN':
                light_shader = 'PxrDistantLight'  
            elif light_type == 'HEMI':
                light_shader = 'PxrDomeLight'
            elif light_type == 'AREA':
                if light.shape == 'DISK':
                    light_shader = 'PxrDiskLight'
                elif light.shape == 'ELLIPSE':
                    light_shader = 'PxrSphereLight'
                else:
                    light_shader = 'PxrRectLight'
            elif light_type == 'SPOT':
                light_shader = 'PxrDiskLight'
            elif light_type == 'POINT':
                light_shader = 'PxrSphereLight' 
                ob = context.object
                scale = light.shadow_soft_size * 2
                ob.scale = [scale, scale, scale]             
            else:
                light_shader = 'PxrRectLight'

            #light.type = 'AREA'
            if hasattr(light, 'size'):
                light.size = 0.0
            light.type = 'POINT'

            light.renderman.use_renderman_node = True
            shadergraph_utils.hide_cycles_nodes(light)

            output = nt.nodes.new('RendermanOutputNode')
            default = nt.nodes.new('%sLightNode' %
                                    light_shader)
            default.location = output.location
            default.location[0] -= 300
            nt.links.new(default.outputs[0], output.inputs[1])    

            output.inputs[0].hide = True
            output.inputs[2].hide = True
            output.inputs[3].hide = True

            light.renderman.renderman_light_role = 'RMAN_LIGHT'
            if light_type == 'SPOT':
                node = context.light.renderman.get_light_node()
                node.coneAngle = math.degrees(light.spot_size)
                node.coneSoftness = light.spot_blend       

        elif idtype == 'world':
            # world
            shadergraph_utils.hide_cycles_nodes(idblock)
            idblock.renderman.use_renderman_node = True
            if shadergraph_utils.find_node(idblock, 'RendermanIntegratorsOutputNode'):
                return {'FINISHED'}
            output = nt.nodes.new('RendermanIntegratorsOutputNode')
            node_name = rman_bl_nodes.__BL_NODES_MAP__.get('PxrPathTracer')
            default = nt.nodes.new(node_name)
            default.location = output.location
            default.location[0] -= 200
            nt.links.new(default.outputs[0], output.inputs[0]) 

            sf_output = nt.nodes.new('RendermanSamplefiltersOutputNode')
            sf_output.location = default.location
            sf_output.location[0] -= 300

            df_output = nt.nodes.new('RendermanDisplayfiltersOutputNode')
            df_output.location = sf_output.location
            df_output.location[0] -= 300

            rman_cycles_convert.convert_world_nodetree(idblock, context, df_output)

        # unselect all nodes
        for n in nt.nodes:
            n.select = False            

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Select a Material")
        col.prop(self, 'bxdf_name')      

    def invoke(self, context, event):

        idtype = self.properties.idtype
        if idtype == 'node_editor':
            idblock = context.space_data.id
            idtype = 'material'
        elif idtype == 'world':
            idblock = context.scene.world
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]
            if not idblock:
                # try getting material from context.object
                ob = context.object
                rm = ob.renderman
                idblock = rm.rman_material_override            

        if not idblock.use_nodes:
            idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':      
            if idblock.grease_pencil:
                return self.execute(context)  
            wm = context.window_manager
            return wm.invoke_props_dialog(self)  
        return self.execute(context)

class SHADING_OT_add_integrator_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "material.rman_add_integrator_nodetree"
    bl_label = "Add RenderMan Integrator Nodetree"
    bl_description = "Add a RenderMan Integrator node tree"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        
        world = context.scene.world
        if not world.use_nodes:
            world.use_nodes = True
        nt = world.node_tree
       
        # world
        world.renderman.use_renderman_node = True
        if shadergraph_utils.find_node(world, 'RendermanIntegratorsOutputNode'):
            return {'FINISHED'}
        shadergraph_utils.hide_cycles_nodes(world)
        output = nt.nodes.new('RendermanIntegratorsOutputNode')
        node_name = rman_bl_nodes.__BL_NODES_MAP__.get('PxrPathTracer')
        default = nt.nodes.new(node_name)
        default.location = output.location
        default.location[0] -= 200
        nt.links.new(default.outputs[0], output.inputs[0]) 

        # unselect all nodes
        for n in nt.nodes:
            n.select = False            

        return {'FINISHED'}

    def invoke(self, context, event): 
        return self.execute(context)        

class SHADING_OT_add_displayfilters_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "material.rman_add_displayfilters_nodetree"
    bl_label = "Add RenderMan Display Filters Nodetree"
    bl_description = "Add a RenderMan display filters node tree. Note, a PxrBackgroundDisplayFilter will be automatically added for you, that will inherit the world color."
    bl_options = {'INTERNAL'}

    def execute(self, context):
        
        world = context.scene.world
        if not world.use_nodes:
            world.use_nodes = True
        nt = world.node_tree
       
        world.renderman.use_renderman_node = True
        if shadergraph_utils.find_node(world, 'RendermanDisplayfiltersOutputNode'):
            return {'FINISHED'}
        shadergraph_utils.hide_cycles_nodes(world)
        df_output = nt.nodes.new('RendermanDisplayfiltersOutputNode')
        df_output.location = df_output.location
        df_output.location[0] -= 300

        node_name = rman_bl_nodes.__BL_NODES_MAP__.get('PxrBackgroundDisplayFilter')
        filter_color = world.color
        bg = nt.nodes.new(node_name)
        bg.backgroundColor = filter_color
        bg.location = df_output.location
        bg.location[0] -= 300
        nt.links.new(bg.outputs[0], df_output.inputs[0])          

        # unselect all nodes
        for n in nt.nodes:
            n.select = False            

        return {'FINISHED'}

    def invoke(self, context, event): 
        return self.execute(context)  

class SHADING_OT_world_convert_material(bpy.types.Operator):

    ''''''
    bl_idname = "world.rman_convert_material"
    bl_label = "Convert World Material"
    bl_description = "Try to convert the world material"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        
        world = context.scene.world
        if not world.use_nodes:
            world.use_nodes = True
        nt = world.node_tree
        shadergraph_utils.hide_cycles_nodes(world)
        output = nt.nodes.new('RendermanIntegratorsOutputNode')
        node_name = rman_bl_nodes.__BL_NODES_MAP__.get('PxrPathTracer')
        default = nt.nodes.new(node_name)
        default.location = output.location
        default.location[0] -= 200
        nt.links.new(default.outputs[0], output.inputs[0]) 

        sf_output = nt.nodes.new('RendermanSamplefiltersOutputNode')
        sf_output.location = default.location
        sf_output.location[0] -= 300

        df_output = nt.nodes.new('RendermanDisplayfiltersOutputNode')
        df_output.location = sf_output.location
        df_output.location[0] -= 300     
       
        rman_cycles_convert.convert_world_nodetree(world, context, df_output)

        # unselect all nodes
        for n in nt.nodes:
            n.select = False   

        return {'FINISHED'}

    def invoke(self, context, event): 
        return self.execute(context)        



class SHADING_OT_add_samplefilters_nodetree(bpy.types.Operator):

    ''''''
    bl_idname = "material.rman_add_samplefilters_nodetree"
    bl_label = "Add RenderMan Sample Filters Nodetree"
    bl_description = "Add a RenderMan sample filters node tree"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        
        world = context.scene.world
        if not world.use_nodes:
            world.use_nodes = True
        nt = world.node_tree

        world.renderman.use_renderman_node = True
        if shadergraph_utils.find_node(world, 'RendermanSamplefiltersOutputNode'):
            return {'FINISHED'}
        shadergraph_utils.hide_cycles_nodes(world)
        sf_output = nt.nodes.new('RendermanSamplefiltersOutputNode')
        sf_output.location = sf_output.location
        sf_output.location[0] -= 300

        # unselect all nodes
        for n in nt.nodes:
            n.select = False            

        return {'FINISHED'}

    def invoke(self, context, event): 
        return self.execute(context)        


class PRMAN_OT_New_bxdf(bpy.types.Operator):
    bl_idname = "node.rman_new_bxdf"
    bl_label = "New RenderMan Material"
    bl_description = "Create a new material with a new RenderMan Bxdf"
    bl_options = {"REGISTER", "UNDO"}

    idtype: StringProperty(name="ID Type", default="material")
    
    def get_type_items(self, context):
        return get_bxdf_items()  

    bxdf_name: EnumProperty(items=get_type_items, name="Bxdf Name")

    def execute(self, context):
        ob = context.object
        bxdf_name = self.bxdf_name
        mat = bpy.data.materials.new(bxdf_name)
        ob.active_material = mat
        if not mat.use_nodes:
            mat.use_nodes = True
        nt = mat.node_tree
        shadergraph_utils.hide_cycles_nodes(mat)
        output = nt.nodes.new('RendermanOutputNode')
        bxdf_node_name = rman_bl_nodes.__BL_NODES_MAP__[bxdf_name]        
        default = nt.nodes.new(bxdf_node_name)
        default.location = output.location
        default.location[0] -= 300
        default.select = False
        nt.links.new(default.outputs[0], output.inputs[0])
        if self.bxdf_name == 'PxrLayerSurface':
            shadergraph_utils.create_pxrlayer_nodes(nt, default)

        output.inputs[3].hide = True
        default.update_mat(mat)

        return {"FINISHED"}  

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Select a Material")
        col.prop(self, 'bxdf_name')      

    def invoke(self, context, event):

        idtype = self.properties.idtype
        if idtype == 'node_editor':
            idblock = context.space_data.id
            idtype = 'material'
        else:
            context_data = {'material': context.material,
                            'light': context.light, 'world': context.scene.world}
            idblock = context_data[idtype]

        if not idblock.use_nodes:
            idblock.use_nodes = True
        nt = idblock.node_tree

        if idtype == 'material':      
            if context.material.grease_pencil:
                return self.execute(context)  
            wm = context.window_manager
            return wm.invoke_props_dialog(self)  
        return self.execute(context)      

class PRMAN_OT_New_Material_Override(bpy.types.Operator):
    bl_idname = "node.rman_new_material_override"
    bl_label = "New RenderMan Material Override"
    bl_description = "Create a new material override"
    bl_options = {"REGISTER", "UNDO"}
    
    def get_type_items(self, context):
        return get_bxdf_items()  

    bxdf_name: EnumProperty(items=get_type_items, name="Bxdf Name")

    def execute(self, context):
        ob = context.object
        bxdf_name = self.bxdf_name
        mat = bpy.data.materials.new(bxdf_name)
        ob.renderman.rman_material_override = mat
        if not mat.use_nodes:
            mat.use_nodes = True
        nt = mat.node_tree
        shadergraph_utils.hide_cycles_nodes(mat)

        output = nt.nodes.new('RendermanOutputNode')
        output.select = False
        bxdf_node_name = rman_bl_nodes.__BL_NODES_MAP__[bxdf_name]        
        default = nt.nodes.new(bxdf_node_name)
        default.location = output.location
        default.location[0] -= 300
        default.select = False
        nt.links.new(default.outputs[0], output.inputs[0])
        if self.bxdf_name == 'PxrLayerSurface':
            shadergraph_utils.create_pxrlayer_nodes(nt, default)

        output.inputs[3].hide = True
        default.update_mat(mat)
        ob.update_tag(refresh={'OBJECT'})

        return {"FINISHED"}  

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Select a Material")
        col.prop(self, 'bxdf_name')      

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self)        

class PRMAN_OT_Force_Material_Refresh(bpy.types.Operator):
    bl_idname = "node.rman_force_material_refresh"
    bl_label = "Force Refresh"
    bl_description = "Force Material to Refresh during IPR. Use this if your material is not responding to edits."
    
    def execute(self, context):
        rr = RmanRender.get_rman_render()
        if rr.rman_context.is_live_rendering():
            mat = getattr(context, "material", None)
            if mat:
                rr.rman_scene_sync.update_material(mat)

        return {"FINISHED"} 

class PRMAN_OT_Force_Light_Refresh(bpy.types.Operator):
    bl_idname = "node.rman_force_light_refresh"
    bl_label = "Force Refresh"
    bl_description = "Force Light to Refresh during IPR. Use this if your light is not responding to edits."
    
    def execute(self, context):
        rr = RmanRender.get_rman_render()
        if rr.rman_context.is_live_rendering():
            light = getattr(context, "light")
            if light:
                users = context.blend_data.user_map(subset={light}, value_types={'OBJECT'})
                for ob in users[light]:
                    rr.rman_scene_sync.update_light(ob)

        return {"FINISHED"}       
        
class PRMAN_OT_Force_LightFilter_Refresh(bpy.types.Operator):
    bl_idname = "node.rman_force_lightfilter_refresh"
    bl_label = "Force Refresh"
    bl_description = "Force Light Filter to Refresh during IPR. Use this if your light filter is not responding to edits."
    
    def execute(self, context):
        rr = RmanRender.get_rman_render()
        if rr.rman_context.is_live_rendering():
            light_filter = getattr(context, "light_filter")
            if light_filter:
                users = context.blend_data.user_map(subset={light_filter}, value_types={'OBJECT'})
                for ob in users[light_filter]:                
                    rr.rman_scene_sync.update_light_filter(ob)

        return {"FINISHED"}  

class PRMAN_OT_Add_Projection_Nodetree(bpy.types.Operator):
    bl_idname = "node.rman_add_projection_nodetree"
    bl_label = "New Projection"
    bl_description = "Attach a RenderMan projection plugin"
    bl_options = {"REGISTER"}

    def get_type_items(self, context):
        return get_projection_items()  

    proj_name: EnumProperty(items=get_type_items, name="Projection")    
    
    def execute(self, context):
        cam = context.camera

        nt = bpy.data.node_groups.new(cam.name, 'ShaderNodeTree')
        output = nt.nodes.new('RendermanProjectionsOutputNode')
        output.select = False
        cam.renderman.rman_nodetree = nt

        proj_node_name = rman_bl_nodes.__BL_NODES_MAP__[self.proj_name]    
        default = nt.nodes.new(proj_node_name)
        default.location = output.location
        default.location[0] -= 300
        default.select = False
        nt.links.new(default.outputs[0], output.inputs[0])      
        cam.update_tag()  

        return {"FINISHED"}          

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Select a Projection")
        col.prop(self, 'proj_name')      

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self)       

class PRMAN_OT_Fix_Ramp(bpy.types.Operator):
    bl_idname = "node.rman_fix_ramp"
    bl_label = "Fix Ramp"
    bl_description = "Try to fix this broken ramp. This may be needed if you are linking in a material from another blend file."
    bl_options = {"INTERNAL"}

    def execute(self, context):
        node = context.node

        node_group = bpy.data.node_groups.get(node.rman_fake_node_group, None)
        if not node_group:
            node_group = bpy.data.node_groups.new(
                node.rman_fake_node_group, 'ShaderNodeTree') 
            node_group.use_fake_user = True                 

        node.rman_fake_node_group_ptr = node_group
        color_rman_ramps = node.__annotations__.get('__COLOR_RAMPS__', [])
        float_rman_ramps = node.__annotations__.get('__FLOAT_RAMPS__', [])
        
        for prop_name in color_rman_ramps:             
            n = node_group.nodes.new('ShaderNodeValToRGB')
            bl_ramp_prop = getattr(node, '%s_bl_ramp' % prop_name)
            prop = getattr(node, prop_name)       
            ramp_name =  prop
            n.name = ramp_name
            if len(bl_ramp_prop) < 1:
                continue            

            elements = n.color_ramp.elements
            for i in range(0, len(bl_ramp_prop)):
                r = bl_ramp_prop[i]
                if i == 0 or i == 1:
                    elem = elements[i]
                    elem.position = r.position
                else:
                    elem = elements.new(r.position)
                elem.color = r.rman_value            

        for prop_name in float_rman_ramps:
            n = node_group.nodes.new('ShaderNodeVectorCurve') 
            bl_ramp_prop = getattr(node, '%s_bl_ramp' % prop_name)
            prop = getattr(node, prop_name)       
            ramp_name =  prop
            n.name = ramp_name
            if len(bl_ramp_prop) < 1:
                continue            

            curve = n.mapping.curves[0]
            points = curve.points
            for i in range(0, len(bl_ramp_prop)):
                r = bl_ramp_prop[i]
                if i == 0 or i == 1:
                    point = points[i]
                    point.location[0] = r.position
                    point.location[1] = r.rman_value
                else:
                    points.new(r.position, r.rman_value)                 

        return {"FINISHED"}

class PRMAN_OT_Fix_All_Ramps(bpy.types.Operator):
    bl_idname = "node.rman_fix_all_ramps"
    bl_label = "Fix All Ramps"
    bl_description = "Try to fix all broken ramps in the scene. This may be needed if you are linking in a material from another blend file."
    bl_options = {"INTERNAL"}

    def execute(self, context):

        shadergraph_utils.reload_bl_ramps(None, check_library=False)
        return {"FINISHED"}        
    
class PRMAN_OT_Select_Nodetree_Node(bpy.types.Operator):
    bl_idname = "node.rman_select_nodetree_node"
    bl_label = ""
    bl_description = "View the connected node"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        node = context.node
        nt = getattr(context, 'nodetree', node.id_data)
        for n in nt.nodes:
            n.select = False
        node.select = True

        return {"FINISHED"}    

class PRMAN_OT_Select_Nodetree_Reset(bpy.types.Operator):
    bl_idname = "node.rman_select_nodetree_reset"
    bl_label = ""
    bl_description = "Go back to the base node"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        node = context.node
        nt = getattr(context, 'nodetree', node.id_data)
        for n in nt.nodes:
            n.select = False

        return {"FINISHED"}       
    
class PRMAN_MT_Select_Nodetree_Downstream(bpy.types.Menu):
    bl_label = "Select Downstream Node"
    bl_idname = "PRMAN_MT_Select_Nodetree_Downstream"
    bl_description = "Select a downstream node"

    @classmethod
    def poll(cls, context):
        return context.engine == "PRMAN_RENDER"

    def draw(self, context):
        layout = self.layout
        node = context.node
        any_connections = False

        for socket in node.outputs:
            if socket.is_linked:
                any_connections = True
                link = socket.links[0]
                to_node = link.to_node
            
                layout.context_pointer_set("node", to_node)
                layout.operator_context = 'EXEC_DEFAULT'
                op = layout.operator('node.rman_select_nodetree_node', text="%s (%s -> %s)" % (to_node.name, link.from_socket.name, link.to_socket.name))
        if not any_connections:
            layout.label(text="No Nodes")

class PRMAN_MT_Select_Nodetree_Upstream(bpy.types.Menu):
    bl_label = "Select Upstream Node"
    bl_idname = "PRMAN_MT_Select_Nodetree_Upstream"
    bl_description = "Select an upstream node"

    @classmethod
    def poll(cls, context):
        return context.engine == "PRMAN_RENDER"

    def draw(self, context):
        layout = self.layout
        node = context.node
        any_connections = False

        for socket in node.inputs:
            if socket.is_linked:
                any_connections = True
                link = socket.links[0]
                from_node = link.from_node

                layout.context_pointer_set("node", from_node)
                layout.operator_context = 'EXEC_DEFAULT'
                op = layout.operator('node.rman_select_nodetree_node', text="%s (%s -> %s)" % (from_node.name, link.from_socket.name, link.to_socket.name))
        if not any_connections:
            layout.label(text="No Nodes")            
class PRMAN_OT_Convert_BlImage_Nodes(bpy.types.Operator):
    bl_idname = "node.convert_blimage_nodes"
    bl_label = "Convert Image Nodes"
    bl_description = "Convert all selected Blender Image Nodes to PxrTexture. Note, we do not convert any upstream nodes that are connected to the image node's Vector input socket."
    bl_options = {"INTERNAL"}

    def execute(self, context):
        from ..rman_bl_nodes import __BL_NODES_MAP__
        from ..rman_cycles_convert import cycles_convert

        node = context.node
        mat = context.mat
        nt = getattr(context, 'nodetree', node.id_data)
        nodes = shadergraph_utils.find_blimage_nodes(nt)
        for n in nodes:
            node_name = __BL_NODES_MAP__.get('PxrTexture', None)
            rman_node = nt.nodes.new(node_name)
            rman_node.location[0] = n.location[0]
            rman_node.location[1] = n.location[1]
            cycles_convert.convert_tex_image_node(nt, n, rman_node, ob=mat)

            # hook up color and alpha sockets
            for k,v in {'Color': 'resultRGB', 'Alpha': 'resultA'}.items():
                socket = n.outputs[k]
                for l in socket.links:
                    # only connect to rman nodes
                    if not hasattr(l.to_node, 'renderman_node_type'):
                        continue
                    to_socket = l.to_socket
                    nt.links.new(rman_node.outputs[v], to_socket)

            nt.nodes.remove(n)

        return {"FINISHED"}    


classes = [
    SHADING_OT_convert_all_renderman_nodetree,
    SHADING_OT_convert_cycles_to_renderman_nodetree,
    SHADING_OT_add_renderman_nodetree,
    SHADING_OT_add_integrator_nodetree,
    SHADING_OT_add_displayfilters_nodetree,
    SHADING_OT_world_convert_material,
    SHADING_OT_add_samplefilters_nodetree,
    PRMAN_OT_New_bxdf,
    PRMAN_OT_New_Material_Override,
    PRMAN_OT_Force_Material_Refresh,
    PRMAN_OT_Force_Light_Refresh,
    PRMAN_OT_Force_LightFilter_Refresh,
    PRMAN_OT_Add_Projection_Nodetree,
    PRMAN_OT_Fix_Ramp,
    PRMAN_OT_Fix_All_Ramps,
    PRMAN_OT_Select_Nodetree_Node,
    PRMAN_OT_Select_Nodetree_Reset,
    PRMAN_MT_Select_Nodetree_Downstream,
    PRMAN_MT_Select_Nodetree_Upstream,
    PRMAN_OT_Convert_BlImage_Nodes    
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes)

def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)