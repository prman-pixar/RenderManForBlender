# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2025 Pixar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# ##### END MIT LICENSE BLOCK #####
import bpy
from ..rfb_utils import texture_utils
from ..rman_bl_nodes import __BL_NODES_MAP__
import re

converted_nodes = {}
report = None
__CURRENT_MATERIAL__ = None


def convert_cycles_node(nt, node, location=None):    
    node_type = node.bl_idname
    node.hide = True
    if node.name in converted_nodes:
        return nt.nodes[converted_nodes[node.name]]

    elif node_type == 'ShaderNodeGroup':
        node_name = node.bl_idname
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        convert_node_group(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    elif node_type in ['ShaderNodeRGBCurve', 'ShaderNodeVectorCurve']:
        node_name = node.bl_idname
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        convert_rgb_curve_node(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    elif node_type in _NODE_MAP_.keys():
        rman_name, convert_func = _NODE_MAP_[node_type]
        node_name = __BL_NODES_MAP__.get(rman_name, None)
        if node_name:
            rman_node = nt.nodes.new(node_name)
        else:
            # copy node
            node_name = node.bl_idname
            rman_node = nt.nodes.new(node_name)        
        if location:
            rman_node.location = location
        convert_func(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    elif node_type in ['ShaderNodeAddShader', 'ShaderNodeMixShader']:
        i = 0 if node.bl_idname == 'ShaderNodeAddShader' else 1
        node1 = node.inputs[
            0 + i].links[0].from_node if node.inputs[0 + i].is_linked else None
        node2 = node.inputs[
            1 + i].links[0].from_node if node.inputs[1 + i].is_linked else None

        node1.hide = True
        node2.hide = True
        if node.bl_idname == 'ShaderNodeAddShader':      
            node_name = __BL_NODES_MAP__.get('LamaAdd')  
            add = nt.nodes.new(node_name)
            if location:
                add.location = location            

            # make a new node for each
            rman_node1 = convert_cycles_bsdf(nt, add, node1, 0)
            rman_node2 = convert_cycles_bsdf(nt, add, node2, 1)

            nt.links.new(rman_node1.outputs["bxdf_out"],
                        add.inputs['material1'])        
            nt.links.new(rman_node2.outputs["bxdf_out"],
                        add.inputs['material2'])   

            setattr(add, "weight1", 0.5)    
            setattr(add, "weight2", 0.5)

            return add                      

        elif node.bl_idname == 'ShaderNodeMixShader': 
            node_name = __BL_NODES_MAP__.get('LamaMix')
            mixer = nt.nodes.new(node_name)
            if location:
                mixer.location = location

            convert_cycles_input(
                nt, node.inputs['Fac'], mixer, 'mix')

            # make a new node for each
            rman_node1 = convert_cycles_bsdf(nt, mixer, node1, 0)
            rman_node2 = convert_cycles_bsdf(nt, mixer, node2, 1)

            nt.links.new(rman_node1.outputs["bxdf_out"],
                        mixer.inputs['material1'])        
            nt.links.new(rman_node2.outputs["bxdf_out"],
                        mixer.inputs['material2'])          

            return mixer        


    elif node_type in _BSDF_MAP_.keys():
        rman_name, convert_func = _BSDF_MAP_[node_type]
        if not convert_func:
            # Fallback to LamaDiffuse
            node_name = __BL_NODES_MAP__.get('LamaDiffuse')
            rman_node = nt.nodes.new(node_name)            
            return rman_node

        node_name = __BL_NODES_MAP__.get(rman_name)
        rman_node = nt.nodes.new(node_name)
        convert_func(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name

        return rman_node
    # else this is just copying the osl node!
    # TODO make this an RMAN osl node
    elif node_type != 'NodeUndefined':
        node_name = node.bl_idname
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        copy_cycles_node(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    else:
        report({'ERROR'}, 'Error converting node %s of type %s.' %
               (node.name, node_type))
        return None

def set_color_space(nt, socket, rman_node, node, param_name, in_socket):
    ## FIXME: figure out a better way when we need to set
    ## colorspace to data
    from ..rfb_utils import shadergraph_utils

    if node.bl_label in ['PxrTexture'] and shadergraph_utils.is_socket_float_type(in_socket):
        setattr(node, 'filename_colorspace', 'data')    

def convert_new_geometry_node(nt, socket, cycles_node, rman_node, param_name):
    socket_nm = socket.links[0].from_socket.name
    in_socket = rman_node.inputs[param_name]
    if socket_nm == 'Backfacing':
        node_name = __BL_NODES_MAP__.get('PxrShadedSide', None)
        convert_node = nt.nodes.new(node_name)       
        convert_node.invert = 1     
        nt.links.new(convert_node.outputs['resultF'], in_socket)        
    elif socket_nm == 'Incoming':
        node_name = __BL_NODES_MAP__.get('PxrPrimvar', None)
        convert_node = nt.nodes.new(node_name)            
        convert_node.variable = 'Vn'
        convert_node.type = 'vector'
        nt.links.new(convert_node.outputs['resultP'], in_socket)
    elif socket_nm == 'Normal':
        # The Blender docs says this also includes bump mapping
        # Have to think about how to wire the result of any PxrBumps in the network
        # to here
        node_name = __BL_NODES_MAP__.get('PxrPrimvar', None)
        convert_node = nt.nodes.new(node_name)            
        convert_node.variable = 'Nn'
        convert_node.type = 'normal'
        nt.links.new(convert_node.outputs['resultP'], in_socket)
    elif socket_nm == 'Parametric':
        # From the Blender docs:
        #
        # "Parametric coordinates of the shading point on the surface. 
        # To area lights it outputs its UV coordinates in planar mapping and 
        # in spherical coordinates to point lights."
        #
        #
        node_name = __BL_NODES_MAP__.get('PxrPrimvar', None)
        convert_node = nt.nodes.new(node_name)            
        convert_node.variable = 'uvw'
        convert_node.type = 'vector'
        nt.links.new(convert_node.outputs['resultP'], in_socket)
    elif socket_nm == 'Pointiness':
        # From the Blender docs:
        #
        # "An approximation of the curvature of the mesh per vertex. Lighter 
        # values indicate convex angles, darker values indicate concave angles. 
        # It allows you to do effects like dirt maps and wear-off effects."      
        node_name = __BL_NODES_MAP__.get('PxrPrimvar', None)
        convert_node = nt.nodes.new(node_name)            
        convert_node.variable = 'curvature'
        convert_node.type = 'float'
        nt.links.new(convert_node.outputs['resultF'], in_socket)
    elif socket_nm == 'Position':
        node_name = __BL_NODES_MAP__.get('PxrPrimvar', None)
        convert_node = nt.nodes.new(node_name)            
        convert_node.variable = 'P'
        convert_node.type = 'point'
        nt.links.new(convert_node.outputs['resultP'], in_socket)
    elif socket_nm == 'Random Per Island':
        # From the Blender docs:
        #
        # "A random value for each connected component (island) of the mesh. 
        # It is useful to add variations to meshes composed of separated units like 
        # tree leaves, wood planks, or curves of multiple splines."
        #
        # Not exactly sure how to convert this. For now, we'll just use PxrVary.
        # PxrVary doesn't have a float output, so we'll just use resultR
        node_name = __BL_NODES_MAP__.get('PxrVary', None)
        convert_node = nt.nodes.new(node_name)            
        nt.links.new(convert_node.outputs['resultR'], in_socket)
    elif socket_nm == 'Tangent':
        # Tangent at the surface.
        node_name = __BL_NODES_MAP__.get('PxrPrimvar', None)
        convert_node = nt.nodes.new(node_name)            
        convert_node.variable = 'Tn'
        convert_node.type = 'vector'
        nt.links.new(convert_node.outputs['resultP'], in_socket)
    elif socket_nm == 'True Normal':
        # Geometry or flat normal of the surface.
        node_name = __BL_NODES_MAP__.get('PxrPrimvar', None)
        convert_node = nt.nodes.new(node_name)            
        convert_node.variable = 'Ngn'
        convert_node.type = 'normal'
        nt.links.new(convert_node.outputs['resultP'], in_socket)

def convert_linked_node(nt, socket, rman_node, param_name):
    location = rman_node.location - \
        (socket.node.location - socket.links[0].from_node.location)
    from_node = socket.links[0].from_node
    if from_node.bl_idname == 'ShaderNodeNewGeometry':
        # this node needs special handling
        return convert_new_geometry_node(nt, socket, from_node, rman_node, param_name)

    node = convert_cycles_node(nt, from_node, location)
    if node:
        out_socket = None

        # find the appropriate socket to hook up.
        in_socket = rman_node.inputs[param_name]
        if socket.links[0].from_socket.name in node.outputs:
            out_socket = node.outputs[socket.links[0].from_socket.name]
        else:
            from ..rfb_utils import shadergraph_utils
            for output in node.outputs:
                if shadergraph_utils.is_socket_same_type(in_socket, output):
                    out_socket = output
                    break
            else:
                output = node.outputs[0]
        
        set_color_space(nt, socket, rman_node, node, param_name, in_socket)
        nt.links.new(out_socket, in_socket)    

def convert_cycles_input(nt, socket, rman_node, param_name):
    if socket.is_linked:
        convert_linked_node(nt, socket, rman_node, param_name)

    elif hasattr(socket, 'default_value'):
        if hasattr(rman_node, 'renderman_node_type'):
            if type(getattr(rman_node, param_name)).__name__ == 'Color':
                setattr(rman_node, param_name, socket.default_value[:3])
            else:
                setattr(rman_node, param_name, socket.default_value)
        else:
            # this is a cycles node
            rman_node.inputs[param_name].default_value = socket.default_value

#########  other node conversion methods  ############


def convert_tex_image_node(nt, cycles_node, rman_node, ob=None):
    if ob is None:
        ob = __CURRENT_MATERIAL__
    bl_image = cycles_node.image
    if bl_image:
        img_path = texture_utils.get_blender_image_path(bl_image)
        if img_path != '':
            if bl_image.source == 'TILED':
                # do something
                pass

            rman_node['filename'] = img_path
            nodeID = texture_utils.generate_node_id(rman_node, 'filename', ob=ob)
            texture_utils.get_txmanager().txmanager.add_texture(nodeID, img_path, nodetype='PxrTexture') 
            txfile = texture_utils.get_txmanager().get_txfile_from_id(nodeID)

            # filter/interpolation
            if cycles_node.interpolation == 'Linear':
                rman_node['filter'] = 2
            elif cycles_node.interpolation == 'Closest':
                rman_node['filter'] = 0
            else:
                rman_node['filter'] = 1

            # mode
            mode = 'periodic'
            if cycles_node.extension == 'REPEAT':
                mode = 'periodic'
            elif cycles_node.extension == 'EXTEND':
                mode = 'clamp'
            elif cycles_node.extension == 'CLAMP':
                mode = 'black'

            txfile.params.s_mode = mode
            txfile.params.t_mode = mode
            txfile.delete_texture_files()
            txfile.build_texture_dict()   

            texture_utils.get_txmanager().txmake_all(blocking=False)         

    # can't link a vector to a manifold :(
    # if cycles_node.inputs['Vector'].is_linked:
    #    convert_cycles_input(nt, cycles_node.inputs['Vector'], rman_node, 'manifold')


def convert_tex_coord_node(nt, cycles_node, rman_node):
    return

def convert_attribute_node(nt, cycles_node, rman_node):   
    attr = getattr(cycles_node, 'attribute_name', '')
    setattr(rman_node, 'varname', attr)
    if cycles_node.outputs['Vector'].is_linked:
        setattr(rman_node, 'type', 'point')
    elif cycles_node.outputs['Color'].is_linked:
        setattr(rman_node, 'type', 'color')
    else:
        setattr(rman_node, 'type', 'float')        

def convert_mix_rgb_node(nt, cycles_node, rman_node):
    setattr(rman_node, 'clampOutput', cycles_node.use_clamp)
    convert_cycles_input(nt, cycles_node.inputs[
                         'Color1'], rman_node, 'bottomRGB')
    convert_cycles_input(nt, cycles_node.inputs['Color2'], rman_node, 'topRGB')
    convert_cycles_input(nt, cycles_node.inputs['Fac'], rman_node, 'topA')
    conversion = {'MIX': '10',
                  'ADD': '19',
                  'MULTIPLY': '18',
                  'SUBTRACT': '25',
                  'SCREEN': '23',
                  'DIVIDE': '7',
                  'DIFFERENCE': '5',
                  'DARKEN': '3',
                  'LIGHTEN': '12',
                  'OVERLAY': '20',
                  'DODGE': '15',
                  'BURN': '14',
                  'HUE': '11',
                  'SATURATION': '22',
                  'VALUE': '17',
                  'COLOR': '0',
                  'SOFT_LIGHT': '24',
                  'LINEAR_LIGHT': '16'}
    rman_op = conversion.get(cycles_node.blend_type, '10')
    setattr(rman_node, 'operation', rman_op)


def convert_node_group(nt, cycles_node, rman_node):
    rman_nt = bpy.data.node_groups.new(rman_node.name, 'ShaderNodeTree')
    rman_node.node_tree = rman_nt
    cycles_nt = cycles_node.node_tree
    # save converted nodes to temp
    global converted_nodes
    temp_converted_nodes = converted_nodes
    converted_nodes = {}

    # create the output node
    cycles_output_node = next(
        (n for n in cycles_nt.nodes if n.bl_idname == 'NodeGroupOutput'), None)
    if cycles_output_node:
        rman_output_node = rman_nt.nodes.new('NodeGroupOutput')
        rman_output_node.location = cycles_output_node.location

        # tree outputs
        for tree_output in cycles_nt.outputs:
            out_type = tree_output.__class__.__name__.replace('Interface', '')
            rman_nt.outputs.new(out_type, tree_output.name)
    # create the input node
    cycles_input_node = next(
        (n for n in cycles_nt.nodes if n.bl_idname == 'NodeGroupInput'), None)
    if cycles_input_node:
        rman_input_node = rman_nt.nodes.new('NodeGroupInput')
        rman_input_node.location = cycles_input_node.location
        # tree outputs
        for tree_input in cycles_nt.inputs:
            input_type = tree_input.__class__.__name__.replace('Interface', '')
            rman_nt.inputs.new(input_type, tree_input.name)

        converted_nodes[cycles_input_node.name] = rman_input_node.name

    # now connect up outputs
    if cycles_output_node:
        for input in cycles_output_node.inputs:
            convert_cycles_input(rman_nt, input, rman_output_node, input.name)

    converted_nodes = temp_converted_nodes

    # rename nodes in node_group
    for node in rman_nt.nodes:
        node.name = rman_nt.name + '.' + node.name

    # convert the inputs to the group
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)

    return


def convert_bump_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs[
                         'Strength'], rman_node, 'scale')
    convert_cycles_input(nt, cycles_node.inputs[
                         'Height'], rman_node, 'inputBump')
    convert_cycles_input(nt, cycles_node.inputs['Normal'], rman_node, 'inputN')
    return


def convert_normal_map_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs[
                         'Strength'], rman_node, 'bumpScale')
    convert_cycles_input(nt, cycles_node.inputs[
                         'Color'], rman_node, 'inputRGB')
    return


def convert_rgb_node(nt, cycles_node, rman_node):
    rman_node.inputRGB = cycles_node.outputs[0].default_value[:3]
    return


def convert_node_value(nt, cycles_node, rman_node):
    #rman_node.floatInput1 = cycles_node.outputs[0].default_value
    #rman_node.expression = 'floatInput1'

    val = cycles_node.outputs[0].default_value
    rman_node.input = (val, val, val)

    return


def convert_ramp_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs['Fac'], rman_node, 'splineMap')
    actual_ramp = bpy.data.node_groups[rman_node.rman_fake_node_group].nodes[0]
    actual_ramp.color_ramp.interpolation = cycles_node.color_ramp.interpolation

    elms = actual_ramp.color_ramp.elements

    e = cycles_node.color_ramp.elements[0]
    elms[0].alpha = e.alpha
    elms[0].position = e.position
    elms[0].color = e.color

    e = cycles_node.color_ramp.elements[-1]
    elms[-1].alpha = e.alpha
    elms[-1].position = e.position
    elms[-1].color = e.color

    for e in cycles_node.color_ramp.elements[1:-1]:
        new_e = actual_ramp.color_ramp.elements.new(e.position)
        new_e.alpha = e.alpha
        new_e.color = e.color

    return

def convert_math_node(nt, cycles_node, rman_node):

    rman_node.operation = cycles_node.operation
    rman_node.use_clamp = cycles_node.use_clamp

    for i in range(0,3):
        input = cycles_node.inputs[i]
        if input.is_linked:
            convert_linked_node(nt, input, rman_node, input.name)
        else:
            rman_node.inputs[i].default_value = input.default_value

    return

def convert_wireframe_node(nt, cycles_node, rman_node):

    tmp = [rman_node.wireColor[0], rman_node.wireColor[1], rman_node.wireColor[2]]
    rman_node.wireColor = [rman_node.backColor[0], rman_node.backColor[1], rman_node.backColor[2]]
    rman_node.backColor = [tmp[0], tmp[1], tmp[2]]

    input = cycles_node.inputs['Size']
    if input.is_linked:
        convert_linked_node(nt, input, rman_node, input.name)
    else:
        val = input.default_value
        rman_node.wireWidth = val * 100.0

    return    

# this needs a special case to init the stuff


def convert_rgb_curve_node(nt, cycles_node, rman_node):
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)

    rman_node.mapping.initialize()
    for i, mapping in cycles_node.mapping.curves.items():
        #    new_map = rman_node.mapping.curves.new()
        new_map = rman_node.mapping.curves[i]
        for p in mapping.points:
            new_map.points.new(p.location[0], p.location[1])
    return


def copy_cycles_node(nt, cycles_node, rman_node):
    #print("copying %s node" % cycles_node.bl_idname)
    # TODO copy props
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)
    return

#########  BSDF conversion methods  ############

def convert_principled_bsdf_to_disney(nt, node, rman_node):
    inputs = node.inputs

    # INPUTS: ['Base Color', 'Subsurface', 'Subsurface Radius', 
    # 'Subsurface Color', 'Metallic', 'Specular', 'Specular Tint', 
    # 'Roughness', 'Anisotropic', 'Anisotropic Rotation', 'Sheen', 
    # 'Sheen Tint', 'Clearcoat', 'Clearcoat Roughness', 'IOR', 
    # 'Transmission', 'Transmission Roughness', 'Emission', 'Alpha', 
    # 'Normal', 'Clearcoat Normal', 'Tangent']

    convert_cycles_input(nt, inputs['Base Color'], rman_node, "baseColor")
    convert_cycles_input(nt, inputs['Subsurface'], rman_node, "subsurface")
    convert_cycles_input(nt, inputs['Subsurface Color'], rman_node, "subsurfaceColor")
    convert_cycles_input(nt, inputs['Metallic'], rman_node, "metallic")
    convert_cycles_input(nt, inputs['Specular'], rman_node, "specReflectScale")
    convert_cycles_input(nt, inputs['Specular Tint'], rman_node, "specularTint")
    convert_cycles_input(nt, inputs['Roughness'], rman_node, "roughness")
    convert_cycles_input(nt, inputs['Anisotropic'], rman_node, "anisotropic")
    convert_cycles_input(nt, inputs['Sheen'], rman_node, "sheen")
    convert_cycles_input(nt, inputs['Sheen Tint'], rman_node, "sheenTint")
    convert_cycles_input(nt, inputs['Clearcoat'], rman_node, "clearcoat")
    convert_cycles_input(nt, inputs['Clearcoat Roughness'], rman_node, "clearcoatGloss")
    convert_cycles_input(nt, inputs['IOR'], rman_node, "ior")
    convert_cycles_input(nt, inputs['Emission'], rman_node, "emitColor")
    convert_cycles_input(nt, inputs['Alpha'], rman_node, "presence")
    convert_cycles_input(nt, inputs['Normal'], rman_node, "bumpNormal")
    
def convert_principled_bsdf_to_lama(nt, node, final_mix_node):
    inputs = node.inputs
    nodes_list = list()

    node_name = __BL_NODES_MAP__.get('PxrBlenderPrincipledInputs', None)
    rman_node = nt.nodes.new(node_name)     
    rman_node.location = final_mix_node.location
    rman_node.location[0] -= 1440.0    

    convert_cycles_input(nt, inputs['Base Color'], rman_node, "BaseColor")
    convert_cycles_input(nt, inputs['Subsurface'], rman_node, "Subsurface")
    convert_cycles_input(nt, inputs['Subsurface Radius'], rman_node, "SubsurfaceRadius")
    convert_cycles_input(nt, inputs['Subsurface Color'], rman_node, "SubsurfaceColor")
    convert_cycles_input(nt, inputs['Metallic'], rman_node, "Metallic")
    convert_cycles_input(nt, inputs['Specular'], rman_node, "Specular")
    convert_cycles_input(nt, inputs['Specular Tint'], rman_node, "SpecularTint")
    convert_cycles_input(nt, inputs['Roughness'], rman_node, "Roughness")
    convert_cycles_input(nt, inputs['Anisotropic'], rman_node, "Anisotropic")
    convert_cycles_input(nt, inputs['Anisotropic Rotation'], rman_node, "AnisotropicRotation")
    convert_cycles_input(nt, inputs['Sheen'], rman_node, "Sheen")
    convert_cycles_input(nt, inputs['Sheen Tint'], rman_node, "SheenTint")
    convert_cycles_input(nt, inputs['Clearcoat'], rman_node, "Clearcoat")
    convert_cycles_input(nt, inputs['Clearcoat Roughness'], rman_node, "ClearcoatRoughness")
    convert_cycles_input(nt, inputs['IOR'], rman_node, "IOR")
    convert_cycles_input(nt, inputs['Emission'], rman_node, "Emission")
    convert_cycles_input(nt, inputs['Normal'], rman_node, "Normal")
    convert_cycles_input(nt, inputs['Clearcoat Normal'], rman_node, "ClearcoatNormal")

    # diffuse
    node_name = __BL_NODES_MAP__.get('LamaDiffuse', None)
    diffuse_node = nt.nodes.new(node_name) 
    diffuse_node.name = 'Diffuse'
    diffuse_node.location = final_mix_node.location
    diffuse_node.location[0] -= 1280.0
    nodes_list.append(diffuse_node)
    
    nt.links.new(rman_node.outputs["out_baseColor"], diffuse_node.inputs["diffuseColor"])
    nt.links.new(rman_node.outputs["out_roughness"], diffuse_node.inputs["roughness"])
    nt.links.new(rman_node.outputs["out_normal"], diffuse_node.inputs["diffuseNormal"])

    # subsurface
    node_name = __BL_NODES_MAP__.get('LamaSSS', None)
    sss_node = nt.nodes.new(node_name) 
    sss_node.location = final_mix_node.location
    sss_node.location[0] -= 1280.0    
    sss_node.location[1] -= 240.0 
    nodes_list.append(sss_node)    
    
    nt.links.new(rman_node.outputs["out_sssColor"], sss_node.inputs["sssColor"])
    nt.links.new(rman_node.outputs["out_normal"], sss_node.inputs["sssNormal"])
    nt.links.new(rman_node.outputs["out_sssRadius"], sss_node.inputs["sssRadius"])

    # diff or sss mix
    node_name = __BL_NODES_MAP__.get('LamaMix', None)
    diff_sss_mix_node = nt.nodes.new(node_name) 
    diff_sss_mix_node.name = 'mix_sss'
    diff_sss_mix_node.location = final_mix_node.location
    diff_sss_mix_node.location[0] -= 1120.0      
    nodes_list.append(diff_sss_mix_node)        

    nt.links.new(diffuse_node.outputs["bxdf_out"], diff_sss_mix_node.inputs["material1"])
    nt.links.new(sss_node.outputs["bxdf_out"], diff_sss_mix_node.inputs["material2"])
    nt.links.new(rman_node.outputs["out_sssMix"], diff_sss_mix_node.inputs["mix"])    

    # sheen
    node_name = __BL_NODES_MAP__.get('LamaSheen', None)
    sheen_node = nt.nodes.new(node_name) 
    sheen_node.location = final_mix_node.location
    sheen_node.location[0] -= 1120.0    
    sheen_node.location[1] -= 240.0     
    nodes_list.append(sheen_node)

    nt.links.new(rman_node.outputs["out_sheenColor"], sheen_node.inputs["sheenColor"])
    nt.links.new(rman_node.outputs["out_normal"], sheen_node.inputs["sheenNormal"])

    # diff sheen add
    node_name = __BL_NODES_MAP__.get('LamaAdd', None)
    diff_sheen_add_node = nt.nodes.new(node_name) 
    diff_sheen_add_node.name = 'plus_sheen'
    diff_sheen_add_node.location = final_mix_node.location
    diff_sheen_add_node.location[0] -= 960.0  
    nodes_list.append(diff_sheen_add_node)       

    nt.links.new(diff_sss_mix_node.outputs["bxdf_out"], diff_sheen_add_node.inputs["material1"])
    nt.links.new(sheen_node.outputs["bxdf_out"], diff_sheen_add_node.inputs["material2"])
    nt.links.new(rman_node.outputs["out_sheenWeight"], diff_sheen_add_node.inputs["weight2"])  

    # specular
    node_name = __BL_NODES_MAP__.get('LamaConductor', None)
    specular_node = nt.nodes.new(node_name)   
    specular_node.name = 'Specular'
    specular_node.location = final_mix_node.location
    specular_node.location[0] -= 960.0
    specular_node.location[1] -= 240.0        
    nodes_list.append(specular_node)       

    nt.links.new(rman_node.outputs["out_specF0"], specular_node.inputs["reflectivity"])  
    nt.links.new(rman_node.outputs["out_roughness"], specular_node.inputs["roughness"])
    nt.links.new(rman_node.outputs["out_normal"], specular_node.inputs["conductorNormal"])
    nt.links.new(rman_node.outputs["out_anisotropic"], specular_node.inputs["anisotropy"])
    nt.links.new(rman_node.outputs["out_anisotropicRotation"], specular_node.inputs["anisotropyRotation"])

    # sheen spec add
    node_name = __BL_NODES_MAP__.get('LamaAdd', None)
    sheen_spec_add_node = nt.nodes.new(node_name) 
    sheen_spec_add_node.name = 'plus_spec'
    sheen_spec_add_node.location = final_mix_node.location
    sheen_spec_add_node.location[0] -= 800.0    
    nodes_list.append(sheen_spec_add_node)       

    nt.links.new(diff_sheen_add_node.outputs["bxdf_out"], sheen_spec_add_node.inputs["material1"])
    nt.links.new(specular_node.outputs["bxdf_out"], sheen_spec_add_node.inputs["material2"])
    nt.links.new(rman_node.outputs["out_diffuseWeight"], sheen_spec_add_node.inputs["weight1"])  
    nt.links.new(rman_node.outputs["out_specularWeight"], sheen_spec_add_node.inputs["weight2"])  


    # transmission
    node_name = __BL_NODES_MAP__.get('LamaDielectric', None)
    transmission_node = nt.nodes.new(node_name) 
    transmission_node.name = 'Transmission'
    transmission_node.location = final_mix_node.location
    transmission_node.location[0] -= 800.0    
    transmission_node.location[1] -= 240.0      
    nodes_list.append(transmission_node)   

    nt.links.new(rman_node.outputs["out_baseColor"], transmission_node.inputs["transmissionTint"])
    nt.links.new(rman_node.outputs["out_roughness"], transmission_node.inputs["roughness"])
    nt.links.new(rman_node.outputs["out_normal"], transmission_node.inputs["dielectricNormal"])

    # spec transmission add
    node_name = __BL_NODES_MAP__.get('LamaAdd', None)
    spec_transmission_add_node = nt.nodes.new(node_name) 
    spec_transmission_add_node.name = 'plus_transmission'
    spec_transmission_add_node.location = final_mix_node.location
    spec_transmission_add_node.location[0] -= 640.0      
    nodes_list.append(spec_transmission_add_node)

    nt.links.new(sheen_spec_add_node.outputs["bxdf_out"], spec_transmission_add_node.inputs["material1"])
    nt.links.new(transmission_node.outputs["bxdf_out"], spec_transmission_add_node.inputs["material2"])
    nt.links.new(rman_node.outputs["out_finalTransmission"], spec_transmission_add_node.inputs["weight2"])  

    # coat
    node_name = __BL_NODES_MAP__.get('LamaDielectric', None)
    coat_node = nt.nodes.new(node_name)   
    coat_node.name = 'Clearcoat'
    coat_node.location = final_mix_node.location
    coat_node.location[0] -= 640.0    
    coat_node.location[1] -= 240.0     
    nodes_list.append(coat_node)

    nt.links.new(rman_node.outputs["out_clearcoatRoughness"], coat_node.inputs["roughness"])
    nt.links.new(rman_node.outputs["out_clearcoatNormal"], coat_node.inputs["dielectricNormal"])       

    # transmission coat add
    node_name = __BL_NODES_MAP__.get('LamaAdd', None)
    transmission_coat_add_node = nt.nodes.new(node_name) 
    transmission_coat_add_node.name = 'plus_coat'
    transmission_coat_add_node.location = final_mix_node.location
    transmission_coat_add_node.location[0] -= 480.0       
    nodes_list.append(transmission_coat_add_node)

    nt.links.new(spec_transmission_add_node.outputs["bxdf_out"], transmission_coat_add_node.inputs["material1"])
    nt.links.new(coat_node.outputs["bxdf_out"], transmission_coat_add_node.inputs["material2"])
    nt.links.new(rman_node.outputs["out_clearcoat"], transmission_coat_add_node.inputs["weight2"])     

    # emission
    node_name = __BL_NODES_MAP__.get('LamaEmission', None)
    emission_node = nt.nodes.new(node_name) 
    emission_node.location = final_mix_node.location
    emission_node.location[0] -= 480.0    
    emission_node.location[1] -= 240.0       
    nodes_list.append(emission_node)

    nt.links.new(rman_node.outputs["out_emissionColor"], emission_node.inputs["emissionColor"])   

    # final mix node
    nt.links.new(transmission_coat_add_node.outputs["bxdf_out"], final_mix_node.inputs["material1"]) 
    nt.links.new(emission_node.outputs["bxdf_out"], final_mix_node.inputs["material2"])   
    nt.links.new(rman_node.outputs["out_emissionMix"], final_mix_node.inputs["mix"])   

    # close ui_open connections
    # with the number of connections to PxrBlenderPrincipledInputs, close all
    # ui_open properties, otherwise we're redrawing the same PxrBlenderPrincipledInputs multiple times
    for n in nodes_list:
        for i in n.inputs:
            i.ui_open = False
   
def convert_diffuse_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    rman_node.name = 'diffuse_bsdf'
    convert_cycles_input(nt, inputs['Color'], rman_node, "diffuseColor")
    convert_cycles_input(nt, inputs['Roughness'],
                         rman_node, "roughness")
    convert_cycles_input(nt, inputs['Normal'], rman_node, "diffuseNormal")    

def convert_glossy_bsdf(nt, node, rman_node):
    inputs = node.inputs       
    rman_node.name = 'glossy_bsdf' 
    convert_cycles_input(nt, inputs['Color'], rman_node, "reflectivity")
    convert_cycles_input(nt, inputs['Color'], rman_node, "edgeColor")
    convert_cycles_input(nt, inputs['Roughness'],
                         rman_node, "roughness")
    convert_cycles_input(
        nt, inputs['Normal'], rman_node, "conductorNormal")                         

    if type(node).__class__ == 'ShaderNodeBsdfAnisotropic':
        convert_cycles_input(
            nt, inputs['Anisotropy'], rman_node, "anisotropy")                         

def convert_glass_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    rman_node.name = 'glass_bsdf'
    setattr(rman_node, 'fresnelMode', "1")
    convert_cycles_input(nt, inputs['Color'], rman_node, "reflectionTint")
    convert_cycles_input(nt, inputs['Roughness'],
                         rman_node, "roughness")
    convert_cycles_input(nt, inputs['IOR'],
                         rman_node, "IOR")       
    convert_cycles_input(nt, inputs['Normal'], rman_node, "dielectricNormal")                                             

def convert_refraction_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    rman_node.name = 'refraction_bsdf'
    setattr(rman_node, 'fresnelMode', "1")
    convert_cycles_input(nt, inputs['Color'], rman_node, "reflectionTint")
    convert_cycles_input(nt, inputs['Roughness'],
                         rman_node, "roughness")
    convert_cycles_input(nt, inputs['IOR'],
                         rman_node, "IOR")       
    convert_cycles_input(nt, inputs['Normal'], rman_node, "dielectricNormal")                                             

def convert_transparent_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    rman_node.name = 'transparent_bsdf'
    convert_cycles_input(nt, inputs['Color'], rman_node, "reflectionTint") 
    setattr(rman_node, 'reflectivity', 1.0)
    setattr(rman_node, 'isThin', 1)                                           

def convert_translucent_bsdf(nt, node, rman_node):
    inputs = node.inputs    
    convert_cycles_input(nt, inputs['Color'], rman_node, "reflectionTint")   
    convert_cycles_input(nt, inputs['Normal'], rman_node, "translucentNormal")                                             

def convert_sss_bsdf(nt, node, rman_node):

    inputs = node.inputs    
    rman_node.name = 'sss_bsdf'
    convert_cycles_input(nt, inputs['Color'], rman_node, "sssColor")
    convert_cycles_input(nt, inputs['Radius'],
                         rman_node, "radius")
    convert_cycles_input(nt, inputs['Scale'],
                         rman_node, "scale")                         
    convert_cycles_input(nt, inputs['IOR'],
                         rman_node, "IOR")       
    convert_cycles_input(nt, inputs['Normal'], rman_node, "sssNormal")                                             

def convert_velvet_bsdf(nt, node, rman_node):
    inputs = node.inputs   
    rman_node.name = 'velvet_bsdf'
    convert_cycles_input(nt, inputs['Color'], rman_node, "sheenColor")      
    convert_cycles_input(nt, inputs['Normal'], rman_node, "sheenNormal")           

def convert_emission_bsdf(nt, node, rman_node):
    inputs = node.inputs  
    rman_node.name = 'emission_bsdf'
    convert_cycles_input(nt, inputs['Color'], rman_node, "emissionColor")  
    if not node.inputs['Color'].is_linked and not node.inputs['Strength']:
        emission_color = getattr(rman_node, 'emissionColor')
        emission_color = inputs['Strength'] * emission_color
        setattr(rman_node, 'emissionColor', emission_color)       

def convert_hair_bsdf(nt, node, rman_node):
    inputs = node.inputs   
    if node.component == 'Reflection':
        convert_cycles_input(nt, inputs['Color'], rman_node, "colorR")   
        convert_cycles_input(nt, inputs['Offset'], rman_node, "offset")
        setattr(rman_node, 'colorTT', (0.0, 0.0, 0.0))
        setattr(rman_node, 'gainTT', 0.0)
        setattr(rman_node, 'gainTRT', 0.0)
        setattr(rman_node, 'gainTRRT', 0.0)
    else:
        convert_cycles_input(nt, inputs['Color'], rman_node, "colorTT")   
        convert_cycles_input(nt, inputs['Offset'], rman_node, "offset")
        setattr(rman_node, 'gainR', 0.0)
        setattr(rman_node, 'gainTRT', 0.0)
        setattr(rman_node, 'gainTRRT', 0.0)        

def convert_hair_principled_bsdf(nt, node, rman_node):
    inputs = node.inputs  
    if node.parametrization == 'COLOR':
        convert_cycles_input(nt, inputs['Color'], rman_node, "colorTT")         
        convert_cycles_input(nt, inputs['IOR'], rman_node, "IOR")         
        convert_cycles_input(nt, inputs['Offset'], rman_node, "offset")
    elif node.parametrization == 'MELANIN':         
        # use PxrHairColor
        node_name = __BL_NODES_MAP__.get('PxrHairColor')
        hair_color = nt.nodes.new(node_name)
        convert_cycles_input(nt, inputs['Melanin'], hair_color, "melanin")   
        convert_cycles_input(nt, inputs['Melanin Redness'], hair_color, "redness")
        convert_cycles_input(nt, inputs['Random Color'], hair_color, "randomMelanin")  
        convert_cycles_input(nt, inputs['Tint'], hair_color, "dye")  
        nt.links.new(hair_color.outputs['resultDiff'], rman_node.inputs["colorR"])
        nt.links.new(hair_color.outputs['resultTT'], rman_node.inputs["colorTT"])
        setattr(hair_color, 'hairIndexPrimvar', 'index')

        convert_cycles_input(nt, inputs['IOR'], rman_node, "IOR")         
        convert_cycles_input(nt, inputs['Offset'], rman_node, "offset")   
        setattr(rman_node, 'remapColorTT', False)     

def convert_volume_principled(nt, node, rman_node):
    inputs = node.inputs   
    rman_node.name = 'volume_principled'
    convert_cycles_input(nt, inputs['Color'], rman_node, "diffuseColor")  
    if inputs['Density Attribute'].default_value != "":
        convert_cycles_input(nt, inputs['Density Attribute'], rman_node, "densityFloatPrimVar")  
    else:
        convert_cycles_input(nt, inputs['Density'], rman_node, "densityFloat")  
        setattr(rman_node, 'densityFloatPrimVar', '')

    convert_cycles_input(nt, inputs['Emission Color'], rman_node, "emitColor")
    convert_cycles_input(nt, inputs['Anisotropy'], rman_node, "anisotropy")        

_BSDF_MAP_ = {
    'ShaderNodeBsdfDiffuse': ('LamaDiffuse', convert_diffuse_bsdf),
    'ShaderNodeBsdfGlossy': ('LamaConductor', convert_glossy_bsdf),
    'ShaderNodeBsdfAnisotropic': ('LamaConductor', convert_glossy_bsdf),
    'ShaderNodeBsdfGlass': ('LamaDielectric', convert_glass_bsdf),
    'ShaderNodeBsdfRefraction': ('LamaDielectric', convert_refraction_bsdf),
    'ShaderNodeBsdfTransparent': ('LamaDielectric', convert_transparent_bsdf),
    'ShaderNodeBsdfTranslucent': ('LamaTranslucent', convert_translucent_bsdf),
    'ShaderNodeBsdfVelvet': ('LamaSheen', convert_velvet_bsdf),
    'ShaderNodeSubsurfaceScattering': ('LamaSSS', convert_sss_bsdf), 
    'ShaderNodeBsdfHair': ('LamaHairChiang', convert_hair_bsdf),
    'ShaderNodeEmission': ('LamaEmission', convert_emission_bsdf),
    'ShaderNodeBsdfHairPrincipled': ('LamaHairChiang', convert_hair_principled_bsdf),
    'ShaderNodeVolumePrincipled': ('PxrVolume', convert_volume_principled),
    "ShaderNodeBsdfPrincipled": ('LamaMix', convert_principled_bsdf_to_lama ),
    'ShaderNodeGroup': (None, None)
}

# we only convert the important shaders, all others are copied from cycles osl
_NODE_MAP_ = {
    'ShaderNodeTexImage': ('PxrTexture', convert_tex_image_node),
    'ShaderNodeMixRGB': ('PxrBlend', convert_mix_rgb_node),
    'ShaderNodeNormalMap': ('PxrNormalMap', convert_normal_map_node),
    'ShaderNodeGroup': ('PxrNodeGroup', convert_node_group),
    'ShaderNodeBump': ('PxrBump', convert_bump_node),
    'ShaderNodeValToRGB': ('PxrRamp', convert_ramp_node),
    'ShaderNodeMath': ('', convert_math_node),
    'ShaderNodeRGB': ('PxrHSL', convert_rgb_node),
    'ShaderNodeValue': ('PxrToFloat', convert_node_value),
    'ShaderNodeAttribute': ('PxrPrimvar', convert_attribute_node),
    'ShaderNodeWireframe': ('PxrWireframe', convert_wireframe_node)
}
