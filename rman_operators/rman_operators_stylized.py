import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import object_utils
from ..rfb_logger import rfb_log
from .. import rman_bl_nodes
from ..rman_constants import RMAN_STYLIZED_FILTERS, RMAN_STYLIZED_PATTERNS, RMAN_UTILITY_PATTERN_NAMES 
from ..rman_constants import RMAN_STYLIZED_XPU_FILTERS, BLENDER_VERSION_MAJOR, BLENDER_VERSION_MINOR 

class PRMAN_OT_Enable_Sylized_Looks(bpy.types.Operator):
    bl_idname = "scene.rman_enable_stylized_looks"
    bl_label = "Enable Stylized Looks"
    bl_description = "Enable stylized looks. Objects still need to have a stylzed pattern connected to their material network, and stylized filters need to be added to the scene."
    bl_options = {'INTERNAL'}

    open_editor: BoolProperty(name="", default=False)
    
    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        rm.render_rman_stylized = 1
        world = scene.world
        world.update_tag()        
        bpy.ops.renderman.dspy_displays_reload('EXEC_DEFAULT')        
        if self.properties.open_editor:
            bpy.ops.scene.rman_open_stylized_editor('INVOKE_DEFAULT')

        return {"FINISHED"} 

class PRMAN_OT_Disable_Sylized_Looks(bpy.types.Operator):
    bl_idname = "scene.rman_disable_stylized_looks"
    bl_label = "Disable Stylized Looks"
    bl_description = "Disable stylized looks."
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        scene = context.scene
        rm = scene.renderman
        rm.render_rman_stylized = 0
        world = scene.world
        world.update_tag()
        bpy.ops.renderman.dspy_displays_reload('EXEC_DEFAULT')        

        return {"FINISHED"}                   

class PRMAN_OT_Attach_Stylized_Pattern(bpy.types.Operator):
    bl_idname = "node.rman_attach_stylized_pattern"
    bl_label = "Attach Stylized Pattern"
    bl_description = "Attach a stylized pattern node to your material network."
    bl_options = {'INTERNAL'}

    def rman_stylized_patterns(self, context):
        items = []
        for f in RMAN_STYLIZED_PATTERNS:
            items.append((f, f, ""))
        return items      

    stylized_pattern: EnumProperty(name="", items=rman_stylized_patterns)

    def add_manifolds(self, nt, pattern_node):
        pxr_to_float3_nm = rman_bl_nodes.__BL_NODES_MAP__['PxrToFloat3']
        pxr_manifold3d_nm = rman_bl_nodes.__BL_NODES_MAP__['PxrManifold3D']
        pxr_projector_nm = rman_bl_nodes.__BL_NODES_MAP__['PxrProjector']

        pxr_manifold3d = nt.nodes.new(pxr_manifold3d_nm) 
        pxr_to_float3_1 = nt.nodes.new(pxr_to_float3_nm) 

        nt.links.new(pxr_manifold3d.outputs['resultX'], pxr_to_float3_1.inputs['inputR'])
        nt.links.new(pxr_manifold3d.outputs['resultY'], pxr_to_float3_1.inputs['inputG'])
        nt.links.new(pxr_manifold3d.outputs['resultZ'], pxr_to_float3_1.inputs['inputB'])
        nt.links.new(pxr_to_float3_1.outputs['resultRGB'], pattern_node.inputs['inputPtriplanar'])
        pxr_to_float3_1.inputs['inputR'].ui_open = False
        pxr_to_float3_1.inputs['inputG'].ui_open = False
        pxr_to_float3_1.inputs['inputB'].ui_open = False
        pattern_node.inputs['inputPtriplanar'].ui_open = False

        pxr_to_float3_2 = nt.nodes.new(pxr_to_float3_nm) 
        pxr_projector = nt.nodes.new(pxr_projector_nm) 

        pxr_projector.coordsys = "NDC"
        nt.links.new(pxr_projector.outputs['resultS'], pxr_to_float3_2.inputs['inputR'])
        nt.links.new(pxr_projector.outputs['resultT'], pxr_to_float3_2.inputs['inputG'])
        nt.links.new(pxr_to_float3_2.outputs['resultRGB'], pattern_node.inputs['inputTextureCoords'])    
        pxr_to_float3_2.inputs['inputR'].ui_open = False
        pxr_to_float3_2.inputs['inputG'].ui_open = False
        pattern_node.inputs['inputTextureCoords'].ui_open = False
        
    def add_utility_slot(self, node, prop_name, coll_nm, coll_idx_nm, param_array_type):
        context_override = bpy.context.copy()
        context_override["node"] = node
        with bpy.context.temp_override(**context_override):
            bpy.ops.renderman.add_remove_array_elem(
                                                    'EXEC_DEFAULT', 
                                                    action='ADD',
                                                    param_name=prop_name,
                                                    collection=coll_nm,
                                                    collection_index=coll_idx_nm,
                                                    elem_type=param_array_type)  

    def attach_pattern(self, context, ob):
        mat = object_utils.get_active_material(ob)
        if mat is None:
            context_override = context.copy()
            context_override["selected_object"] = ob
            with bpy.context.temp_override(**context_override):
                bpy.ops.object.rman_add_bxdf('EXEC_DEFAULT', bxdf_name='PxrSurface')
            mat = object_utils.get_active_material(ob)

        if mat is None:
            self.report({'ERROR'}, 'Cannot find a material for: %s' % ob.name)
            return {"FINISHED"} 
        
        nt = mat.node_tree
        output = shadergraph_utils.is_renderman_nodetree(mat)
        if not output:
            context_override = context.copy()
            context_override["selected_object"] = ob
            with bpy.context.temp_override(**context_override):            
                bpy.ops.object.rman_add_bxdf('EXEC_DEFAULT', bxdf_name='PxrSurface')
            mat = object_utils.get_active_material(ob)
            nt = mat.node_tree
            output = shadergraph_utils.is_renderman_nodetree(mat)
            
        socket = output.inputs[0]
        if not socket.is_linked:
            return

        link = socket.links[0]
        node = link.from_node 
        prop_name = ''

        pattern_node_name = None
        pattern_settings = None
        if self.properties.stylized_pattern in RMAN_STYLIZED_PATTERNS:
            pattern_node_name = rman_bl_nodes.__BL_NODES_MAP__[self.properties.stylized_pattern]
        else:
            return

        for nm in RMAN_UTILITY_PATTERN_NAMES:
            if not hasattr(node, nm):
                continue
            prop_name = nm

            if shadergraph_utils.has_stylized_pattern_node(ob, node=node):
                continue

            prop_meta = node.prop_meta[prop_name]
            if prop_meta['renderman_type'] == 'array':
                coll_nm = '%s_collection' % prop_name  
                coll_idx_nm = '%s_collection_index' % prop_name
                param_array_type = prop_meta['renderman_array_type'] 

                attr = getattr(node, coll_nm)
                
                if len(attr) < 1:
                    self.add_utility_slot(node, prop_name, coll_nm, coll_idx_nm, param_array_type)                

                pattern_node = nt.nodes.new(pattern_node_name)   

                if pattern_settings:
                    for param_name, param_settings in pattern_settings['params'].items():
                        val = param_settings['value']
                        setattr(pattern_node, param_name, val)

                sub_prop_nm = '%s[0]' % (prop_name)     
                socket = node.inputs[sub_prop_nm]
                # check if the first element has something connected
                if socket.is_linked:
                    # if there is something connected, shift everything over one
                    self.add_utility_slot(node, prop_name, coll_nm, coll_idx_nm, param_array_type)
                    for i in range(len(attr)-1, 0, -1):
                        prev_socket = node.inputs['%s[%d]' % (prop_name, i-1)]
                        cur_socket = node.inputs['%s[%d]' % (prop_name, i)]
                        if prev_socket.is_linked:
                            from_socket = prev_socket.links[0].from_socket
                            nt.links.new(from_socket, cur_socket) 
                            nt.links.remove(prev_socket.links[0])

                # now, link stylized pattern to the first element
                nt.links.new(pattern_node.outputs['resultAOV'], node.inputs[sub_prop_nm]) 
                
                # Add manifolds
                if self.properties.stylized_pattern == "PxrStylizedControl":
                    self.add_manifolds(nt, pattern_node)                   

            else:
                if node.inputs[prop_name].is_linked:
                    continue

                pattern_node = nt.nodes.new(pattern_node_name) 

                if pattern_settings:                 
                    for param_name, param_settings in pattern_settings['params'].items():
                        val = param_settings['value']
                        setattr(pattern_node, param_name, val)
            
                nt.links.new(pattern_node.outputs['resultAOV'], node.inputs[prop_name])

                # Add manifolds      
                if self.properties.stylized_pattern == "PxrStylizedControl":
                    self.add_manifolds(nt, pattern_node)         
    
    def execute(self, context):
        selected_objects = context.selected_objects

        obj = getattr(context, "selected_obj", None)
        if obj:
            self.attach_pattern(context, obj)         
        else:
            for ob in selected_objects:
                self.attach_pattern(context, ob)         

        return {"FINISHED"}         

class PRMAN_OT_Add_Stylized_Filter(bpy.types.Operator):
    bl_idname = "node.rman_add_stylized_filter"
    bl_label = "Add Stylized Filter"
    bl_description = "Add a stylized filter to the scene."
    bl_options = {'INTERNAL'}

    def rman_stylized_filters(self, context):
        items = []
        scene = context.scene
        world = scene.world        
        if scene.renderman.renderVariant == "xpu":
            filters = RMAN_STYLIZED_XPU_FILTERS
        else:
            filters = RMAN_STYLIZED_FILTERS
        for f in filters:
            items.append((f, f, ""))

        return items

    filter_name: EnumProperty(items=rman_stylized_filters, name="Filter Name")
    node_name: StringProperty(name="", default="")
    
    def execute(self, context):
        scene = context.scene
        world = scene.world
        nt = world.node_tree
        is_xpu = scene.renderman.renderVariant == "xpu"
        filter_name = self.properties.filter_name
        if is_xpu and filter_name == "PxrStylizedHatchingSampleXPU":
            output = shadergraph_utils.find_node(world, 'RendermanSamplefiltersOutputNode')
            if not output:
                bpy.ops.material.rman_add_rman_nodetree('EXEC_DEFAULT', idtype='world')
                output = shadergraph_utils.find_node(world, 'RendermanSamplefiltersOutputNode')    
        else:            
            output = shadergraph_utils.find_node(world, 'RendermanDisplayfiltersOutputNode')
            if not output:
                bpy.ops.material.rman_add_rman_nodetree('EXEC_DEFAULT', idtype='world')
                output = shadergraph_utils.find_node(world, 'RendermanDisplayfiltersOutputNode')           


        filter_node_name = rman_bl_nodes.__BL_NODES_MAP__[filter_name]
        filter_node = nt.nodes.new(filter_node_name) 

        free_socket = None
        for i, socket in enumerate(output.inputs):
            if not socket.is_linked:
                free_socket = socket
                break

        if not free_socket:
            bpy.ops.node.rman_add_displayfilter_node_socket('EXEC_DEFAULT')
            free_socket = output.inputs[len(output.inputs)-1]

        nt.links.new(filter_node.outputs[0], free_socket)
        if self.properties.node_name != "":
            filter_node.name = self.properties.node_name

        world.update_tag()

        return {"FINISHED"}       

classes = [
    PRMAN_OT_Enable_Sylized_Looks,
    PRMAN_OT_Disable_Sylized_Looks,
    PRMAN_OT_Attach_Stylized_Pattern,
    PRMAN_OT_Add_Stylized_Filter
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes)

def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)  