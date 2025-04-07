from . import scene_utils
from .rman_socket_utils import node_add_inputs
from .rman_socket_utils import node_add_outputs
from .rman_socket_utils import update_inputs
from .shadergraph_utils import has_lobe_enable_props
from . import scenegraph_utils
from ..rfb_logger import rfb_log
import bpy
import re

TX_ATLAS_UDIM_EXPR = re.compile(r'([_\.])(1\d{3})([_\.])')

def assetid_update_func(self, context, param_name):
    from . import texture_utils
    from . import filepath_utils

    node = self.node if hasattr(self, 'node') else self

    # get the real path if the value is the weird Blender relative path
    file_path = None
    if param_name in node:
        file_path = filepath_utils.get_token_blender_file_path(node[param_name])
        if '<udim>' in file_path:
            # replace <udim> with <UDIM>
            file_path = file_path.replace('<udim>', '<UDIM>')
        else:
            # see if we can automatically detect a udim and subst with <UDIM>
            file_path = re.sub(TX_ATLAS_UDIM_EXPR, '\\1<UDIM>\\3', file_path)
        node[param_name] = file_path
    else:
        file_path = getattr(node, param_name, '')

    if not hasattr(node, 'renderman_node_type'):
        return
    ob = scene_utils.find_node_owner(node, context)
    if not ob:
        return

    category = node.renderman_node_type
    if isinstance(ob, bpy.types.Material):
        node_type = node.bl_label
    elif isinstance(ob, bpy.types.World):
        node_type = node.bl_label
    elif isinstance(ob, bpy.types.NodeTree):
        node_type = node.bl_label
    elif isinstance(ob, bpy.types.Object):
        if ob.type == 'LIGHT':
            light = ob.data
            node_type = light.renderman.get_light_node_name()

    texture_utils.get_txmanager().add_texture(node, ob, param_name, file_path, node_type=node_type, category=category)

    if file_path:
        # update colorspace param from txmanager
        txfile = texture_utils.get_txmanager().get_txfile(node, param_name, ob=ob)

        if txfile:
            params = txfile.params          
            param_colorspace = '%s_colorspace'  % param_name
            try:
                mdict = texture_utils.get_txmanager().txmanager.color_manager.colorspace_names()
                val = 0
                for i, nm in enumerate(mdict):
                    if nm == params.ocioconvert:
                        val = i+1
                        break

                node[param_colorspace] = val
            except AttributeError:
                pass              

    if hasattr(node, 'id_data'):        
        if category in ['projection']:
            # if this is from a projection node, we need to tell
            # the camera to update
            users = context.blend_data.user_map(subset={node.id_data})
            for o in users[node.id_data]:
                o.update_tag()    
        else:    
            node.id_data.update_tag()
    elif isinstance(ob, bpy.types.Material):
        node.update_mat(ob)
    elif isinstance(ob, bpy.types.World):
        ob.update_tag()
    elif isinstance(ob, bpy.types.Object):
        ob.update_tag(refresh={'DATA'})

def update_conditional_visops(node):
    for param_name, prop_meta in getattr(node, 'prop_meta').items():
        conditionalVisOps = prop_meta.get('conditionalVisOps', None)
        if conditionalVisOps:
            cond_expr = conditionalVisOps.get('expr', None)
            if cond_expr:
                try:
                    hidden = not eval(cond_expr)
                    if prop_meta.get('conditionalLockOps', None):
                        setattr(node, '%s_disabled' % param_name, hidden)
                        prop_disabled = hidden
                        if hasattr(node, 'inputs') and param_name in node.inputs:
                            node.inputs[param_name].hide = hidden   
                            node.inputs[param_name].hide_value = hidden
                    else:                    
                        setattr(node, '%s_hidden' % param_name, hidden)
                        if hasattr(node, 'inputs') and param_name in node.inputs:
                            node.inputs[param_name].hide = hidden
                            node.inputs[param_name].hide_value = hidden
                except:
                    rfb_log().debug("Error in conditional visop: %s" % (cond_expr))

def update_func_with_inputs(self, context):
    # check if this prop is set on an input
    node = self.node if hasattr(self, 'node') else self

    if hasattr(node, 'id_data'):
        node.id_data.update_tag()
    elif context and hasattr(context, 'active_object'):
        if context.active_object:
            if context.active_object.type in ['CAMERA', 'LIGHT']:
                context.active_object.update_tag(refresh={'DATA'})

    if context and hasattr(context, 'material'):
        mat = context.material
        if mat:
            node.update_mat(mat)
    elif context and hasattr(context, 'node'):
        mat = context.space_data.id
        if mat:
            node.update_mat(mat)

    if has_lobe_enable_props(node):
        node_add_inputs(node, node.name, node.prop_names)
    else:
        update_inputs(node)

    # update the conditional_vis_ops
    update_conditional_visops(node)        

    # set any inputs that are visible and param is hidden to hidden
    prop_meta = getattr(node, 'prop_meta')
    if hasattr(node, 'inputs'):
        for input_name, socket in node.inputs.items():
            if input_name not in prop_meta:
                continue
            if 'hidden' in prop_meta[input_name]:
                socket.hide = prop_meta[input_name]['hidden']

def update_array_size_func(self, context):
    '''
    Callback function for changes to array size/length property

    If there's a change in the size, we first remove all of the input/sockets
    from the ShadingNode related to arrays. We then re-add the input/socktes
    with the new size via the rman_socket_utils.node_add_inputs function. 
    We need to do this because Blender seems to draw all inputs in the node
    properties panel. This is a problem if the array size gets smaller.
    '''

    # check if this prop is set on an input
    node = self.node if hasattr(self, 'node') else self
    if hasattr(node, 'id_data'):
        node.id_data.update_tag()
    elif context and hasattr(context, 'active_object'):
        if context.active_object:
            if context.active_object.type in ['CAMERA', 'LIGHT']:
                context.active_object.update_tag(refresh={'DATA'})

    if context and hasattr(context, 'material'):
        mat = getattr(context, 'material', None)
        if mat:
            node.update_mat(mat)
    elif context and hasattr(context, 'node'):
        mat = getattr(context.space_data, 'id', None)
        if mat:
            node.update_mat(mat)

    links = dict()
    
    # first remove all sockets/inputs from the node related to arrays
    ui_structs = getattr(node, 'ui_structs', dict())    
    for prop_name,meta in node.prop_meta.items():
        is_ui_struct = meta.get('is_ui_struct', False)
        renderman_type = meta.get('renderman_type', '')
        if is_ui_struct:
            ui_struct_members = ui_structs[prop_name]
            for member in ui_struct_members:
                sub_prop_names = getattr(node, member)                  
                for nm in sub_prop_names:
                    if nm in node.inputs.keys():
                        socket = node.inputs[nm]
                        if socket.is_linked:
                            links[nm] = {"from_node": socket.links[0].from_node, "from_socket": socket.links[0].from_socket}
                        node.inputs.remove(node.inputs[nm])          
        elif renderman_type == 'array':
            sub_prop_names = getattr(node, prop_name)
            for nm in sub_prop_names:
                if nm in node.inputs.keys():
                    socket = node.inputs[nm]
                    if socket.is_linked:
                        links[nm] = {"from_node": socket.links[0].from_node, "from_socket": socket.links[0].from_socket}                    
                    node.inputs.remove(node.inputs[nm])

    # now re-add all sockets/inputs
    node_add_inputs(node, node.name, node.prop_names)

    # update the conditional_vis_ops
    update_conditional_visops(node)          

    # set any inputs that are visible and param is hidden to hidden
    prop_meta = getattr(node, 'prop_meta')
    if hasattr(node, 'inputs'):
        for input_name, socket in node.inputs.items():
            if 'hidden' in prop_meta[input_name]:
                socket.hide = prop_meta[input_name]['hidden']    

    # reconnect any links that were linked before:
    for nm, link in links.items():
        if nm in node.inputs:
            socket = node.inputs[nm]
            if not socket.hide:
                node.id_data.links.new(link['from_socket'], socket)

def update_func(self, context):
    # check if this prop is set on an input
    node = self.node if hasattr(self, 'node') else self

    if hasattr(node, 'id_data'):
        node_type = getattr(node, 'renderman_node_type', '')
        if node_type in ['projection']:
            # if this is from a projection node, we need to tell
            # the camera to update
            users = context.blend_data.user_map(subset={node.id_data})
            for o in users[node.id_data]:
                o.update_tag()
        else:
            node.id_data.update_tag()
    elif context and hasattr(context, 'active_object'):
        if context.active_object:
            if context.active_object.type in ['CAMERA', 'LIGHT']:
                context.active_object.update_tag(refresh={'DATA'})

    if context and hasattr(context, 'material'):
        mat = getattr(context, 'material', None)
        if mat:
            node.update_mat(mat)

    elif context and hasattr(context, 'node'):
        mat = getattr(context.space_data, 'id', None)
        if mat:
            node.update_mat(mat)
    # update the conditional_vis_ops
    update_conditional_visops(node)

    # set any inputs that are visible and param is hidden to hidden
    prop_meta = getattr(node, 'prop_meta')
    if hasattr(node, 'inputs'):
        for input_name, socket in node.inputs.items():
            if input_name not in prop_meta:
                continue 
            if 'hidden' in prop_meta[input_name] \
                    and prop_meta[input_name]['hidden'] and not socket.hide:
                socket.hide = True      

def update_integrator_func(self, context):
    node = self.node if hasattr(self, 'node') else self
    update_conditional_visops(node)
    scenegraph_utils.update_sg_integrator(context)           

def update_samplefilters_func(self, context):
    node = self.node if hasattr(self, 'node') else self
    update_conditional_visops(node)
    scenegraph_utils.update_sg_samplefilters(context)    

def update_displayfilters_func(self, context):
    node = self.node if hasattr(self, 'node') else self
    update_conditional_visops(node)
    scenegraph_utils.update_sg_displayfilters(context)        

def update_options_func(self, s, context):
    scenegraph_utils.update_sg_options(s, context)

def update_root_node_func(self, s, context):
    scenegraph_utils.update_sg_root_node(s, context)

def update_riattr_func(self, s, context):
    ob = None
    if not hasattr(context, 'object'):
        ob = self.id_data
        if ob is None:
            return
    scenegraph_utils.update_sg_node_riattr(s, context, bl_object=ob)    

def update_primvar_func(self, s, context):
    ob = None
    if not hasattr(context, 'object'):
        ob = self.id_data    
        if ob is None:
            return
    scenegraph_utils.update_sg_node_primvar(s, context, bl_object=ob)      

def update_displays_func(self, context):
    scenegraph_utils.update_sg_displays(context)