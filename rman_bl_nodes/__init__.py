from ..rfb_utils.rfb_node_desc_utils.rfb_node_desc import RfbNodeDesc
from ..rfb_utils import filepath_utils
from ..rfb_utils.filepath import FilePath
from ..rfb_utils import generate_property_utils
from ..rfb_utils.property_callbacks import *
from ..rfb_utils.rman_socket_utils import node_add_inputs
from ..rfb_utils.rman_socket_utils import node_add_outputs
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import register_utils
from ..rfb_utils.string_utils import sanitize_attr_name
from ..rfb_logger import rfb_log
from ..rfb_utils.envconfig_utils import envconfig
from .. import rfb_icons
from .. import rman_config
from ..rman_config import __RFB_CONFIG_DICT__ as rfb_config
from ..rman_properties import rman_properties_renderlayers
from ..rman_properties import rman_properties_world
from ..rman_properties import rman_properties_camera
from ..rman_constants import RFB_ARRAYS_MAX_LEN
from ..rman_constants import CYCLES_NODE_MAP
from ..rman_constants import RMAN_FAKE_NODEGROUP
from ..rman_constants import BLENDER_41
from nodeitems_utils import NodeCategory, NodeItem
from collections import OrderedDict
from copy import deepcopy
from bpy.props import *
import bpy
import os
import sys
import traceback
import nodeitems_utils
from operator import attrgetter

# registers
from . import rman_bl_nodes_sockets
from . import rman_bl_nodes_shaders
from . import rman_bl_nodes_ops
from . import rman_bl_nodes_props
from . import rman_bl_nodes_menus

__RMAN_DISPLAY_NODES__ = []
__RMAN_BXDF_NODES__ = []
__RMAN_DISPLACE_NODES__ = []
__RMAN_INTEGRATOR_NODES__ = []
__RMAN_PROJECTION_NODES__ = []
__RMAN_DISPLAYFILTER_NODES__ = []
__RMAN_SAMPLEFILTER_NODES__ = []
__RMAN_PATTERN_NODES__ = []
__RMAN_LIGHT_NODES__ = []
__RMAN_LIGHTFILTER_NODES__ = []
__RMAN_NODE_TYPES__ = dict()

__RMAN_NODE_CATEGORIES__ = dict()
__RMAN_NODE_CATEGORIES__['bxdf'] = dict()
__RMAN_NODE_CATEGORIES__['light'] = dict()
__RMAN_NODE_CATEGORIES__['pattern'] = dict()
__RMAN_NODE_CATEGORIES__['displace'] = dict()
__RMAN_NODE_CATEGORIES__['samplefilter'] = dict()
__RMAN_NODE_CATEGORIES__['displayfilter'] = dict()
__RMAN_NODE_CATEGORIES__['integrator'] = dict()
__RMAN_NODE_CATEGORIES__['projection'] = dict()


__RMAN_NODE_CATEGORIES__['bxdf']['bxdf_misc'] = (('RenderMan Misc Bxdfs', []), [])
__RMAN_NODE_CATEGORIES__['light']['light'] = (('RenderMan Lights', []), [])
__RMAN_NODE_CATEGORIES__['pattern']['patterns_misc'] = (('RenderMan Misc Patterns', []), [])
__RMAN_NODE_CATEGORIES__['displace']['displace'] = (('RenderMan Displacements', []), [])
__RMAN_NODE_CATEGORIES__['samplefilter']['samplefilter'] = (('RenderMan SampleFilters', []), [])
__RMAN_NODE_CATEGORIES__['displayfilter']['displayfilter'] = (('RenderMan DisplayFilters', []), [])
__RMAN_NODE_CATEGORIES__['integrator']['integrator'] = (('RenderMan Integrators', []), [])
__RMAN_NODE_CATEGORIES__['projection']['projection'] = (('RenderMan Projections', []), [])
  

__RMAN_NODES__ = { 
    'displaydriver': __RMAN_DISPLAY_NODES__,
    'bxdf': __RMAN_BXDF_NODES__,
    'displace': __RMAN_DISPLACE_NODES__,
    'integrator': __RMAN_INTEGRATOR_NODES__,
    'projection': __RMAN_PROJECTION_NODES__,
    'displayfilter': __RMAN_DISPLAYFILTER_NODES__, 
    'samplefilter': __RMAN_SAMPLEFILTER_NODES__,
    'pattern': __RMAN_PATTERN_NODES__,
    'light': __RMAN_LIGHT_NODES__,
    'lightfilter': __RMAN_LIGHTFILTER_NODES__
}

__RMAN_PLUGIN_MAPPING__ = {
    'displaydriver': rman_properties_renderlayers.RendermanAOV,
    'projection': rman_properties_camera.RendermanCameraSettings
}


# map RenderMan name to Blender node name
# ex: PxrStylizedControl -> PxrStylizedControlPatternNode
__BL_NODES_MAP__ = dict()

__CYCLES_NODE_DESC_MAP__ = dict()
__RMAN_NODES_ALREADY_REGISTERED__ = False

def get_cycles_node_desc(node):
    from ..rfb_utils.filepath import FilePath

    global __CYCLES_NODE_DESC_MAP__

    mapping = CYCLES_NODE_MAP.get(node.bl_idname, None)
    if not mapping:
        return (None, None)

    node_desc = __CYCLES_NODE_DESC_MAP__.get(mapping, None)  
    if not node_desc:
        shader_path = FilePath(filepath_utils.get_cycles_shader_path()).join(FilePath('%s.oso' % mapping))
        node_desc = RfbNodeDesc(shader_path) 
        __CYCLES_NODE_DESC_MAP__[mapping] = node_desc   

    return (mapping, node_desc)

def class_generate_properties(node, parent_name, node_desc, generate_array_ui=True):
    prop_names = []
    prop_meta = {}
    ui_structs = {}
    output_meta = OrderedDict()

    if "__annotations__" not in node.__dict__:
            setattr(node, "__annotations__", {})

    # pxr osl and seexpr need these to find the code
    if parent_name in ["PxrOSL"]:
        # Enum for internal, external type selection
        EnumName = "codetypeswitch"
        if parent_name == 'PxrOSL':
            EnumProp = EnumProperty(items=(('EXT', "External", ""),
                                           ('INT', "Internal", "")),
                                    name="Shader Location", default='INT')
        else:
            EnumProp = EnumProperty(items=(('NODE', "Node", ""),
                                           ('INT', "Internal", "")),
                                    name="Expr Location", default='NODE')

        EnumMeta = {'renderman_name': 'filename',
                    'name': 'codetypeswitch',
                    'renderman_type': 'string',
                    'default': '', 'label': 'codetypeswitch',
                    'type': 'enum', 'options': '',
                    'widget': 'mapper', '__noconnection': True}
        node.__annotations__[EnumName] = EnumProp
        prop_names.append(EnumName)
        prop_meta[EnumName] = EnumMeta
        # Internal file search prop
        InternalName = "internalSearch"
        InternalProp = StringProperty(name="Shader to use",
                                      description="Storage space for internal text data block",
                                      default="")
        InternalMeta = {'renderman_name': 'filename',
                        'name': 'internalSearch',
                        'renderman_type': 'string',
                        'default': '', 'label': 'internalSearch',
                        'type': 'string', 'options': '',
                        'widget': 'fileinput', '__noconnection': True}
        node.__annotations__[InternalName] = InternalProp
        prop_names.append(InternalName)
        prop_meta[InternalName] = InternalMeta
        # External file prop
        codeName = "shadercode"
        codeProp = StringProperty(name='External File', default='',
                                  subtype="FILE_PATH", description='')
        codeMeta = {'renderman_name': 'filename',
                    'name': 'ShaderCode', 'renderman_type': 'string',
                    'default': '', 'label': 'ShaderCode',
                    'type': 'string', 'options': '',
                    'widget': 'fileinput', '__noconnection': True}
        node.__annotations__[codeName] = codeProp
        prop_names.append(codeName)
        prop_meta[codeName] = codeMeta

    # inputs

    for node_desc_param in node_desc.params:

        update_function = None
        if node_desc.node_type == 'integrator':
            update_function = update_integrator_func
        elif node_desc.node_type == 'samplefilter':
            update_function = update_samplefilters_func
        elif node_desc.node_type == 'displayfilter':
            update_function = update_displayfilters_func            
        else:
            update_function = update_func_with_inputs if 'enable' in node_desc_param.name else update_func         

        if not update_function:
            update_function = update_func

        if node_desc_param.has_ui_struct:
            ui_struct_nm = node_desc_param.uiStruct
            ui_struct = ui_structs.get(ui_struct_nm, [])
            if not ui_struct:
                generate_property_utils.generate_uistruct_property(node, ui_struct_nm, prop_names, prop_meta)
            ui_struct.append(node_desc_param.name)
            ui_structs[ui_struct_nm] = ui_struct 
            sub_prop_names = []
            param_name = node_desc_param._name  
            if isinstance(node_desc_param.default, list):
                node_desc_param.default = node_desc_param.default[0]

            for i in range(0, RFB_ARRAYS_MAX_LEN+1):      
                ndp = deepcopy(node_desc_param)
                ndp._name = '%s[%d]' % (param_name, i)
                if hasattr(ndp, 'label'):
                    ndp.label = '%s' % (ndp.label)
                ndp.size = None
                name, meta, prop = generate_property_utils.generate_property(node, ndp, update_function=update_function)
                meta['renderman_array_name'] = param_name
                meta['ui_struct'] = ui_struct_nm
                sub_prop_names.append(ndp._name)
                prop_meta[ndp._name] = meta
                ndp_name_attr = sanitize_attr_name(ndp._name)
                node.__annotations__[ndp_name_attr] = prop  

            setattr(node, param_name, sub_prop_names)   
            continue            
           
        if node_desc_param.is_array() and generate_array_ui:
            # this is an array 
            if generate_property_utils.generate_array_property(node, prop_names, prop_meta, node_desc_param, update_function=update_function):
                continue

        name, meta, prop = generate_property_utils.generate_property(node, node_desc_param, update_function=update_function)
        if name is None:
            continue          
        if hasattr(node_desc_param, 'page') and node_desc_param.page != '':
            page = node_desc_param.page
            tokens = page.split('|')
            sub_prop_names = prop_names
            page_name = 'page_%s' % tokens[0].replace(' ', '')
            page_name_label = tokens[0]
                 
            if page_name not in prop_meta:
                # For pages, add a BoolProperty called '[page_name].uio'
                # This determines whether the page is opened or closed
                sub_prop_names.append(page_name)
                prop_meta[page_name] = {'renderman_type': 'page', 'renderman_name': page_name, 'label': page_name_label}
                ui_label = "%s_uio" % page_name
                dflt = getattr(node_desc_param, 'page_open', False)  
                page_name_attr = sanitize_attr_name(ui_label)              
                node.__annotations__[page_name_attr] = BoolProperty(name=ui_label, default=dflt)
                setattr(node, page_name, [])   

                # If this a PxrSurface node, add an extra BoolProperty to control
                # enabling/disabling each lobe. This is similar to the enable*
                # parameters on PxrLayer
                if parent_name == 'PxrSurface' and 'Globals' not in page_name:
                    enable_param_name = 'enable' + page_name_label.replace(' ', '')
                    if enable_param_name not in prop_meta:
                        prop_meta[enable_param_name] = {
                            'renderman_type': 'enum', 'renderman_name': enable_param_name, 'label': page_name_label}
                        default = page_name_label == 'Diffuse'
                        enable_param_prop = BoolProperty(name="Enable " + page_name_label,
                                            default=bool(default),
                                            description="Enable " + page_name_label,
                                            update=update_func_with_inputs)
                        node.__annotations__[enable_param_name] = enable_param_prop        
                        page_prop_names = getattr(node, page_name)   
                        if enable_param_name not in page_prop_names:     
                            page_prop_names.append(enable_param_name)
                            setattr(node, page_name, page_prop_names) 

            if len(tokens) > 1:

                for i in range(1, len(tokens)):
                    parent_page = page_name
                    page_name += '_' + tokens[i].replace(' ', '')
                    page_name_label = tokens[i]
                    if page_name not in prop_meta:
                        prop_meta[page_name] = {'renderman_type': 'page', 'renderman_name': page_name, 'label': page_name_label}
                        ui_label = "%s_uio" % page_name
                        dflt = getattr(node_desc_param, 'page_open', False) 
                        page_name_attr = sanitize_attr_name(ui_label) 
                        node.__annotations__[page_name_attr] = BoolProperty(name=ui_label, default=dflt)
                        setattr(node, page_name, [])
                    
                    sub_prop_names = getattr(node, parent_page)
                    if page_name not in sub_prop_names:
                        sub_prop_names.append(page_name)
                        setattr(node, parent_page, sub_prop_names)

            sub_prop_names = getattr(node, page_name)
            sub_prop_names.append(name)
            setattr(node, page_name, sub_prop_names)           
            prop_meta[name] = meta
            node.__annotations__[name] = prop  

        else:
            prop_names.append(name)
            prop_meta[name] = meta
            node.__annotations__[name] = prop

    # outputs
    for node_desc_param in node_desc.outputs:
        renderman_type = node_desc_param.type
        prop_name = node_desc_param.name

        output_prop_meta = dict()
        if hasattr(node_desc_param, 'vstructmember'):
            output_prop_meta['vstructmember'] = node_desc_param.vstructmember
        if hasattr(node_desc_param, 'vstructConditionalExpr'):
            output_prop_meta['vstructConditionalExpr'] = node_desc_param.vstructConditionalExpr
        if hasattr(node_desc_param, 'vstruct'):
            output_prop_meta['vstruct'] = True
        if hasattr(node_desc_param, 'struct_name'):
            output_prop_meta['struct_name'] = node_desc_param.struct_name            
        if node_desc_param.is_array():
            output_prop_meta['arraySize'] = node_desc_param.size
        else:
            output_prop_meta['arraySize'] = -1
        output_prop_meta['name'] = node_desc_param.name
        output_meta[prop_name] = output_prop_meta
        output_meta[prop_name]['renderman_type'] = renderman_type       
            
    setattr(node, 'prop_names', prop_names)
    setattr(node, 'prop_meta', prop_meta)
    setattr(node, 'output_meta', output_meta)
    setattr(node, "ui_structs", ui_structs)

def generate_node_type(node_desc, is_oso=False):
    ''' Dynamically generate a node type from pattern '''

    name = node_desc.name
    nodeType = node_desc.node_type

    nodeDict = {'bxdf': rman_bl_nodes_shaders.RendermanBxdfNode,
                'pattern': rman_bl_nodes_shaders.RendermanPatternNode,
                'displace': rman_bl_nodes_shaders.RendermanDisplacementNode,
                'light': rman_bl_nodes_shaders.RendermanLightNode,
                'lightfilter': rman_bl_nodes_shaders.RendermanLightfilterNode,
                'samplefilter': rman_bl_nodes_shaders.RendermanSamplefilterNode,
                'displayfilter': rman_bl_nodes_shaders.RendermanDisplayfilterNode,
                'integrator': rman_bl_nodes_shaders.RendermanIntegratorNode,
                'projection': rman_bl_nodes_shaders.RendermanProjectionNode}

    if nodeType not in nodeDict.keys():
        return (None, None)

    typename = '%s%sNode' % (name, nodeType.capitalize())
    ntype = type(typename, (nodeDict[nodeType],), {})

    ntype.bl_label = name
    ntype.typename = typename
    description = getattr(node_desc, 'help')
    if not description:
        description = name
    ntype.bl_description = description

    # Node sizes
    node_size_defaults = rfb_config['node_size_preferences']['default']

    bl_width_default, bl_width_min, bl_width_max, bl_height_default, bl_height_min, bl_height_max = node_size_defaults
    if name in rfb_config['node_size_preferences']:
        node_size_defaults = rfb_config['node_size_preferences'][name]
        bl_width_default, bl_width_min, bl_width_max, bl_height_default, bl_height_min, bl_height_max = node_size_defaults

    if bl_width_default > 0.0:
        ntype.bl_width_default = bl_width_default
    if bl_width_min > 0.0:
        ntype.bl_width_min = bl_width_min     
    if bl_width_max > 0.0:
        ntype.bl_width_max = bl_width_max    
    if bl_height_default > 0.0:
        ntype.bl_height_default = bl_height_default    
    if bl_height_min > 0.0:
        ntype.bl_height_min = bl_height_min    
    if bl_height_max > 0.0:
        ntype.bl_height_max = bl_height_max    

    def init(self, context):
        from ..rfb_utils import collection_utils

        # add input/output sockets to nodes, based on type
        if self.renderman_node_type == 'bxdf':
            self.outputs.new('RendermanNodeSocketBxdf', "bxdf_out", identifier="Bxdf")
            node_add_inputs(self, name, self.prop_names)
            node_add_outputs(self)
        elif self.renderman_node_type == 'light':
            node_add_inputs(self, name, self.prop_names)
            self.outputs.new('RendermanNodeSocketLight', "light_out", identifier="Light")
        elif self.renderman_node_type == 'lightfilter':
            node_add_inputs(self, name, self.prop_names)
            self.outputs.new('RendermanNodeSocketLightFilter', "lightfilter_out", identifier="LightFilter")            
        elif self.renderman_node_type == 'displace':
            self.outputs.new('RendermanNodeSocketDisplacement', "displace_out", identifier="Displacement")
            node_add_inputs(self, name, self.prop_names)
        elif self.renderman_node_type == 'displayfilter':
            self.outputs.new('RendermanNodeSocketDisplayFilter', "displayfilter_out", identifier="DisplayFilter")
            node_add_inputs(self, name, self.prop_names)            
        elif self.renderman_node_type == 'samplefilter':
            self.outputs.new('RendermanNodeSocketSampleFilter', "samplefilter_out", identifier="SampleFilter")
            node_add_inputs(self, name, self.prop_names)    
        elif self.renderman_node_type == 'integrator':
            self.outputs.new('RendermanNodeSocketIntegrator', "integrator_out", identifier="Integrator")
            node_add_inputs(self, name, self.prop_names)     
        elif self.renderman_node_type == 'projection':
            self.outputs.new('RendermanNodeSocketProjection', "projection_out", identifier="Projection")
            node_add_inputs(self, name, self.prop_names)                                   
        elif name == "PxrOSL":
            self.outputs.clear()
        # else pattern            
        else:
            node_add_inputs(self, name, self.prop_names)
            node_add_outputs(self)

        # deal with non-connectable arrays
        array_props = self.__annotations__.get('__ARRAYS__', [])
        for prop_name in array_props:
            meta = self.prop_meta[prop_name]
            if not meta.get('__noconnection', False):
                continue            
            dflt = meta['default']
            arraySize = meta.get('arraySize', None)
            if arraySize is None or arraySize < 0:
                arraySize = len(dflt)
            param_type = meta['renderman_array_type']
            for i in range(arraySize):
                coll_nm = '%s_collection' % prop_name
                coll_idx_nm = '%s_collection_index' % prop_name
                collection = getattr(self, coll_nm)
                index = getattr(self, coll_idx_nm)        
                param_array_name = '%s[%d]' % (prop_name, i)
                param_array_label = '%s[%d]' % (prop_name, i)                                       
                elem = collection.add()
                index = len(collection)-1
                setattr(self, coll_idx_nm, index)
                elem.name = '%s[%d]' % (prop_name, len(collection)-1)  
                elem.type = param_type
                item = collection[-1]
                item.type = param_type
                setattr(self, 'value_%s' % item.type, dflt[i])               

        
        # deal with any ramps necessary
        color_rman_ramps = self.__annotations__.get('__COLOR_RAMPS__', [])
        float_rman_ramps = self.__annotations__.get('__FLOAT_RAMPS__', [])

        if color_rman_ramps or float_rman_ramps:
            node_group = bpy.data.node_groups.new(
                RMAN_FAKE_NODEGROUP, 'ShaderNodeTree') 
            node_group.use_fake_user = True             
            self.rman_fake_node_group_ptr = node_group    
            self.rman_fake_node_group = node_group.name    

            for ramp_name in color_rman_ramps:
                n = node_group.nodes.new('ShaderNodeValToRGB')

                knots = None
                knots_name = '%s_Knots' % ramp_name
                cols = None
                cols_name = '%s_Colors' % ramp_name
                for node_desc_param in node_desc.params:
                    if node_desc_param.name == knots_name:
                        knots = node_desc_param
                    elif node_desc_param.name == cols_name:
                        cols = node_desc_param
                elements = n.color_ramp.elements
                prev_val = None
                for i in range(0, len(knots.default)):
                    if not prev_val:
                        prev_val = cols.default[i]
                    elif prev_val == cols.default[i]:
                        continue
                    prev_val = cols.default[i]
                    if i == 0:
                        elem = elements[0]
                        elem.position = knots.default[i]
                    else:
                        elem = elements.new(knots.default[i])
                    elem.color = (cols.default[i][0], cols.default[i][1], cols.default[i][2], 1.0)
                
                setattr(self, ramp_name, n.name)

            for ramp_name in float_rman_ramps:
                n = node_group.nodes.new('ShaderNodeVectorCurve') 

                knots = None
                knots_name = '%s_Knots' % ramp_name
                vals = None
                vals_name = '%s_Floats' % ramp_name
                for node_desc_param in node_desc.params:
                    if node_desc_param.name == knots_name:
                        knots = node_desc_param
                    elif node_desc_param.name == vals_name:
                        vals = node_desc_param                
                curve = n.mapping.curves[0]
                n.mapping.clip_min_x = 0.0
                n.mapping.clip_min_y = 0.0
                points = curve.points
                prev_val = None
                for i in range(0, len(knots.default)):
                    if not prev_val:
                        prev_val = vals.default[i]
                    elif prev_val == vals.default[i]:
                        continue      
                    prev_val = vals.default[i]    
                    if i == 0:
                        point = points[0]
                        point.location[0] = knots.default[i]
                        point.location[1] = vals.default[i]
                    else:
                        points.new(knots.default[i], vals.default[i])

                setattr(self, ramp_name, n.name)        

            self.__annotations__['__COLOR_RAMPS__'] = color_rman_ramps
            self.__annotations__['__FLOAT_RAMPS__'] =  float_rman_ramps

        update_conditional_visops(self)


    def free(self):
        if self.rman_fake_node_group_ptr:
            bpy.data.node_groups.remove(self.rman_fake_node_group_ptr)
        elif self.rman_fake_node_group in bpy.data.node_groups:
            bpy.data.node_groups.remove(bpy.data.node_groups[self.rman_fake_node_group])

    ntype.init = init
    ntype.free = free
    
    if "__annotations__" not in ntype.__dict__:
            setattr(ntype, "__annotations__", {})

    # the name of our fake node group to hold all of our ramp nodes
    ntype.__annotations__['rman_fake_node_group'] = StringProperty('__rman_ramps__', default='')
    ntype.__annotations__['rman_fake_node_group_ptr']  = PointerProperty(type=bpy.types.NodeTree)

    ntype.__annotations__['plugin_name'] = StringProperty(name='Plugin Name',
                                       default=name, options={'HIDDEN'})

    has_textured_params = False
    rman_textured_params = list()
    if node_desc.textured_params:
        has_textured_params = True
        ntype.__annotations__['txm_id'] = StringProperty(name='txm_id', default="")
        for param in node_desc.textured_params:
            if param.has_ui_struct:
                for i in range(RFB_ARRAYS_MAX_LEN+1):
                    nm = '%s[%d]' % (param.name, i)
                    rman_textured_params.append(nm)
            else:
                rman_textured_params.append(param.name)
    
    setattr(ntype, 'rman_textured_params', rman_textured_params)
    ntype.__annotations__['rman_has_textured_params'] = BoolProperty(
                name="rman_has_textured_params",
                default=has_textured_params)        

    class_generate_properties(ntype, name, node_desc)
    if nodeType == 'light':
        ntype.__annotations__['light_primary_visibility'] = BoolProperty(
            name="Light Primary Visibility",
            description="Camera visibility for this light",
            default=True)
    elif nodeType in ['samplefilter', 'displayfilter']:
        callback_fn = update_samplefilters_func
        if nodeType == 'displayfilter':
            callback_fn = update_displayfilters_func
        ntype.__annotations__['is_active'] = BoolProperty(
            name="Active",
            description="Enable or disable this filter",
            update=callback_fn,
            default=True)        

    register_utils.rman_register_class(ntype)

    if nodeType == 'pattern' and is_oso:
        # This is mainly here for backwards compatability
        #
        # Originally, we postfix the class name with OSLNode
        # when loading OSL pattern nodes. However, this would have
        # caused problems when all of our C++ pattern nodes
        # become OSL shaders; older scenes that were using the C++
        # patterns will break because the old class name will not 
        # exist anymore.
        #
        # We now register every pattern node with the none postfix
        # name. However, this will now break all of the scenes that
        # were created during the 24.0 beta, including our example scenes.
        # Rather than try to come up with some fancy post load handler, just
        # register the pattern node again with the postfix name. 
        #
        # This code should definitely be removed in the future.
        osl_node_typename = '%s%sOSLNode' % (name, nodeType.capitalize())
        osl_node_type = type(osl_node_typename, (nodeDict[nodeType],), {})

        osl_node_type.bl_label = name
        osl_node_type.typename = typename
        osl_node_type.init = init
        osl_node_type.free = free     
        osl_node_type.bl_description = ntype.bl_description   
        if "__annotations__" not in osl_node_type.__dict__:
                setattr(osl_node_type, "__annotations__", {})            
        osl_node_type.__annotations__['rman_fake_node_group'] = StringProperty('__rman_ramps__', default='')
        osl_node_type.__annotations__['rman_fake_node_group_ptr']  = PointerProperty(type=bpy.types.NodeTree)

        osl_node_type.__annotations__['plugin_name'] = StringProperty(name='Plugin Name',
                                        default=name, options={'HIDDEN'})

        if has_textured_params:
            osl_node_type.__annotations__['txm_id'] = StringProperty(name='txm_id', default="")
       
        setattr(osl_node_type, 'rman_textured_params', rman_textured_params)
        osl_node_type.__annotations__['rman_has_textured_params'] = BoolProperty(
                    name="rman_has_textured_params",
                    default=has_textured_params)                                                
                
        class_generate_properties(osl_node_type, name, node_desc)
        register_utils.rman_register_class(osl_node_type)

    return (typename, ntype)

def register_plugin_to_parent(ntype, name, node_desc, plugin_type, parent):

    class_generate_properties(ntype, name, node_desc, generate_array_ui=False)
    setattr(ntype, 'renderman_node_type', plugin_type)
    
    if "__annotations__" not in parent.__dict__:
            setattr(parent, "__annotations__", {})

    # register and add to scene_settings
    register_utils.rman_register_class(ntype)
    settings_name = "%s_settings" % name
    parent.__annotations__["%s_settings" % name] = PointerProperty(type=ntype, name="%s Settings" % name)
    
    if "__annotations__" not in rman_properties_world.RendermanWorldSettings.__dict__:
            setattr(rman_properties_world.RendermanWorldSettings, "__annotations__", {})

def register_plugin_types(node_desc):

    items = []

    if node_desc.node_type not in __RMAN_PLUGIN_MAPPING__:
        return
    parent = __RMAN_PLUGIN_MAPPING__[node_desc.node_type]
    name = node_desc.name
    if node_desc.node_type == 'displaydriver':
        # remove the d_ prefix
        name = name.split('d_')[1]
    typename = name + node_desc.node_type.capitalize() + 'Settings'
    ntype = type(typename, (rman_bl_nodes_props.RendermanPluginSettings,), {})
    ntype.bl_label = name
    ntype.typename = typename
    ntype.bl_idname = typename
    description = getattr(node_desc, 'help')
    if not description:
        description = name
    ntype.bl_description = description    

    try:
        if "__annotations__" not in ntype.__dict__:
            setattr(ntype, "__annotations__", {})
        ntype.__annotations__['plugin_name'] = StringProperty(name='Plugin Name',
                                        default=name, options={'HIDDEN'})
        register_plugin_to_parent(ntype, name, node_desc, node_desc.node_type, parent)
    except Exception as e:
        rfb_log().error("Error registering plugin ", name)
        traceback.print_exc()

class RendermanShaderNodeCategory(NodeCategory):

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        if rd.engine != 'PRMAN_RENDER':
            return False        
        return context.space_data.tree_type == 'ShaderNodeTree' and context.space_data.shader_type in ['OBJECT', 'WORLD']

class RendermanNodeItem(NodeItem):
    '''
    Custom NodeItem class so that we can modify the way the category menus
    are drawn.
    '''

    def draw(self, item, layout, context):
        # skip everything but our submenu item
        if item.nodetype != '__RenderMan_Node_Menu__':
            return
        if context.space_data.shader_type == 'OBJECT':
            light = getattr(context, 'light', None)
            if light:
                nt = light.node_tree                        
                layout.context_pointer_set("nodetree", nt)                 
                layout.menu('NODE_MT_RM_Pattern_Category_Menu')
                return

            mat = getattr(context, 'material', None)
            if not mat:
                return
            if not shadergraph_utils.is_renderman_nodetree(mat):
                rman_icon = rfb_icons.get_icon('rman_graph')
                layout.operator(
                    'material.rman_add_rman_nodetree', icon_value=rman_icon.icon_id).idtype = "material"
            else:
                nt = mat.node_tree                        
                layout.context_pointer_set("nodetree", nt) 
                layout.menu('NODE_MT_RM_Bxdf_Category_Menu')
                layout.menu('NODE_MT_RM_Displacement_Category_Menu')
                layout.menu('NODE_MT_RM_Pattern_Category_Menu')
                layout.menu('NODE_MT_RM_PxrSurface_Category_Menu')
                layout.menu('NODE_MT_RM_Light_Category_Menu')

        elif context.space_data.shader_type == 'WORLD':
            world = context.scene.world
            if not world.renderman.use_renderman_node:
                rman_icon = rfb_icons.get_icon('rman_graph')
                layout.operator('material.rman_add_rman_nodetree', icon_value=rman_icon.icon_id).idtype = 'world'
            else:
                nt = world.node_tree
                layout.context_pointer_set("nodetree", nt) 
                layout.menu('NODE_MT_RM_Integrators_Category_Menu')
                layout.menu('NODE_MT_RM_SampleFilter_Category_Menu')
                layout.menu('NODE_MT_RM_DisplayFilter_Category_Menu')

class NODE_MT_RM_CATEGORY(bpy.types.Menu):
    bl_label = "RenderMan"
    bl_idname = "NODE_MT_RM_CATEGORY"

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == 'PRMAN_RENDER'
    
    @classmethod
    def get_icon_id(cls):
        return rfb_icons.get_icon("rman_blender").icon_id      

    def draw(self, context):
        layout = self.layout
        if context.space_data.shader_type == 'OBJECT':
            light = getattr(context, 'light', None)
            if light:
                nt = light.node_tree                        
                layout.context_pointer_set("nodetree", nt)                 
                layout.menu('NODE_MT_RM_Pattern_Category_Menu')
                return

            mat = getattr(context, 'material', None)
            if not mat:
                return
            if not shadergraph_utils.is_renderman_nodetree(mat):
                rman_icon = rfb_icons.get_icon('rman_graph')
                layout.operator(
                    'material.rman_add_rman_nodetree', icon_value=rman_icon.icon_id).idtype = "material"
            else:
                nt = mat.node_tree                        
                layout.context_pointer_set("nodetree", nt) 
                layout.menu('NODE_MT_RM_Bxdf_Category_Menu')
                layout.menu('NODE_MT_RM_Displacement_Category_Menu')
                layout.menu('NODE_MT_RM_Pattern_Category_Menu')
                layout.menu('NODE_MT_RM_PxrSurface_Category_Menu')
                layout.menu('NODE_MT_RM_Light_Category_Menu')

        elif context.space_data.shader_type == 'WORLD':
            world = context.scene.world
            if not world.renderman.use_renderman_node:
                rman_icon = rfb_icons.get_icon('rman_graph')
                layout.operator('material.rman_add_rman_nodetree', icon_value=rman_icon.icon_id).idtype = 'world'
            else:
                nt = world.node_tree
                layout.context_pointer_set("nodetree", nt) 
                layout.menu('NODE_MT_RM_Integrators_Category_Menu')
                layout.menu('NODE_MT_RM_SampleFilter_Category_Menu')
                layout.menu('NODE_MT_RM_DisplayFilter_Category_Menu')     

def add_renderman_category(self, context):
    rd = context.scene.render
    if rd.engine != 'PRMAN_RENDER':
        return    

    layout = self.layout
    layout.menu('NODE_MT_RM_CATEGORY', text='RenderMan', icon_value=bpy.types.VIEW3D_MT_renderman_add_object_menu.get_icon_id())          


def register_rman_nodes():
    global __RMAN_NODE_CATEGORIES__

    rman_disabled_nodes = rfb_config['disabled_nodes']

    rfb_log().debug("Registering RenderMan Plugin Nodes:")
    path_list = envconfig().get_shader_registration_paths()
    visited = set()
    for path in path_list:
        for root, dirnames, filenames in os.walk(path):
            # Prune this branch if we've already visited it (e.g., one path
            # in the path list is actually a subdirectory of another).
            real = os.path.realpath(root)
            if real in visited:
                dirnames[:] = []
                continue
            visited.add(real)

            rfb_log().debug("  Loading from: %s" % root)
            for filename in sorted(filenames):        
                if filename.endswith(('.args', '.oso')):
                    # skip registering these nodes
                    if filename in rman_disabled_nodes:
                        continue       
                    is_oso = False 
                    is_args = True 
                    if filename.endswith('.oso'):
                        is_oso = True
                        is_args = False

                    rfb_log().debug("\t    Parsing: %s" % filename)
                    node_desc = RfbNodeDesc(FilePath(root).join(FilePath(filename)))

                    # apply any overrides
                    rman_config.apply_args_overrides(filename, node_desc)

                    __RMAN_NODES__[node_desc.node_type].append(node_desc)
                    rfb_log().debug("\t    %s Loaded" % node_desc.name)

                    # These plugin types are special. They are not actually shading
                    # nodes that can be used in Blender's shading editor, but 
                    # we still create PropertyGroups for them so they can be inserted
                    # into the correct UI panel.
                    if node_desc.node_type in ['displaydriver']: 
                        register_plugin_types(node_desc)
                        continue
                    
                    typename, nodetype = generate_node_type(node_desc, is_oso=is_oso)
                    if not typename and not nodetype:
                        continue

                    if typename and nodetype:
                        __RMAN_NODE_TYPES__[typename] = nodetype
                        __BL_NODES_MAP__[node_desc.name] = typename

                    # categories
                    node_item = RendermanNodeItem(typename, label=nodetype.bl_label)
                    if node_desc.node_type == 'pattern': 
                        classification = getattr(node_desc, 'classification', '')                                                       
                        if classification and classification != '':
                            tokens = classification.split('/')                                
                            category = tokens[-1].lower()
                            category_nice_name = category.capitalize()
                            # category seems empty. Put in misc
                            if category == '':
                                category = 'misc'                                      
                            lst = __RMAN_NODE_CATEGORIES__['pattern'].get('patterns_%s' % category, None)
                            if not lst:
                                lst = (('RenderMan %s Patterns' % category_nice_name, []), [])
                            lst[0][1].append(node_item)
                            lst[1].append(node_desc)
                            __RMAN_NODE_CATEGORIES__['pattern']['patterns_%s' % category] = lst                                         

                        else:
                            __RMAN_NODE_CATEGORIES__['pattern']['patterns_misc'][0][1].append(node_item)
                            __RMAN_NODE_CATEGORIES__['pattern']['patterns_misc'][1].append(node_desc)
                    elif node_desc.node_type == 'bxdf':
                        classification = getattr(node_desc, 'classification', '')
                        if classification and classification != '':
                            tokens = classification.split(':')
                            category = ''
                            
                            # first, find rendernode
                            for token in tokens:
                                if token.startswith('rendernode'):
                                    category = token
                                    continue
                            # if we didn't find anything, put this into the misc. cateogry   
                            if category == '' or ('bxdf' not in category):
                                __RMAN_NODE_CATEGORIES__['bxdf']['bxdf_misc'][0][1].append(node_item)
                                __RMAN_NODE_CATEGORIES__['bxdf']['bxdf_misc'][1].append(node_desc)
                                continue
                           
                            # now, split on /, and look for bxdf
                            tokens = category.split('/')
                            i = 0
                            for i,token in enumerate(tokens):
                                if token == 'bxdf':
                                    # found bxdf, all the tokens after are the category
                                    i += 1
                                    break

                            category = '_'.join(tokens[i:])
                            category_nice_name = ''
                            for token in tokens[i:]:
                                if category_nice_name != '':
                                    category_nice_name += '/'
                                category_nice_name += token.capitalize()
                            lst = __RMAN_NODE_CATEGORIES__['bxdf'].get('bxdf_%s' % category, None)
                            if not lst:
                                lst = (('RenderMan %s Bxdf' % category_nice_name, []), [])
                            lst[0][1].append(node_item)
                            lst[1].append(node_desc)
                            __RMAN_NODE_CATEGORIES__['bxdf']['bxdf_%s' % category] = lst    
                        else:
                            __RMAN_NODE_CATEGORIES__['bxdf']['bxdf_misc'][0][1].append(node_item)
                            __RMAN_NODE_CATEGORIES__['bxdf']['bxdf_misc'][1].append(node_desc)
                    elif node_desc.node_type == 'displace':
                        __RMAN_NODE_CATEGORIES__['displace']['displace'][0][1].append(node_item)
                        __RMAN_NODE_CATEGORIES__['displace']['displace'][1].append(node_desc)
                    elif node_desc.node_type == 'light':
                        __RMAN_NODE_CATEGORIES__['light']['light'][0][1].append(node_item)
                        __RMAN_NODE_CATEGORIES__['light']['light'][1].append(node_desc)     
                    elif node_desc.node_type == 'samplefilter':
                        __RMAN_NODE_CATEGORIES__['samplefilter']['samplefilter'][0][1].append(node_item)      
                        __RMAN_NODE_CATEGORIES__['samplefilter']['samplefilter'][1].append(node_desc)      
                    elif node_desc.node_type == 'displayfilter':
                        __RMAN_NODE_CATEGORIES__['displayfilter']['displayfilter'][0][1].append(node_item)
                        __RMAN_NODE_CATEGORIES__['displayfilter']['displayfilter'][1].append(node_desc)                                                                
                    elif node_desc.node_type == 'integrator':
                        __RMAN_NODE_CATEGORIES__['integrator']['integrator'][0][1].append(node_item)  
                        __RMAN_NODE_CATEGORIES__['integrator']['integrator'][1].append(node_desc)    
                    elif node_desc.node_type == 'projection':
                        __RMAN_NODE_CATEGORIES__['projection']['projection'][0][1].append(node_item)  
                        __RMAN_NODE_CATEGORIES__['projection']['projection'][1].append(node_desc)                             

    rfb_log().debug("Finished Registering RenderMan Plugin Nodes.")


def register_node_categories():

    node_categories = []    
    all_items = []
    all_items.append(RendermanNodeItem('__RenderMan_Node_Menu__', label='RenderMan'))

    # we still need to register our nodes for our category
    # otherwise, they won't show up in th search
    for k,v in __RMAN_NODE_CATEGORIES__.items():
        for name, ((desc, items), lst) in v.items():
            if items:
                if k == 'light':
                    # we only want PxrMeshLight
                    for i in items:
                        if i.label == 'PxrMeshLight':
                            all_items.append(i)
                            break
                else:
                    all_items.extend(items)

    shader_category = RendermanShaderNodeCategory('RenderMan', 'RenderMan', items=all_items)
    node_categories.append(shader_category)
    nodeitems_utils.register_node_categories("RENDERMANSHADERNODES",
                                            node_categories)   

def register():
    rman_bl_nodes_props.register()
    global __RMAN_NODES_ALREADY_REGISTERED__
    if not __RMAN_NODES_ALREADY_REGISTERED__:
        register_rman_nodes()
        __RMAN_NODES_ALREADY_REGISTERED__ = True    
    register_node_categories()
    rman_bl_nodes_sockets.register()
    rman_bl_nodes_shaders.register()
    rman_bl_nodes_ops.register()
    rman_bl_nodes_menus.register()

    if BLENDER_41:
        register_utils.rman_register_class(NODE_MT_RM_CATEGORY)
        bpy.types.NODE_MT_add.append(add_renderman_category)

def unregister():
    try:
        nodeitems_utils.unregister_node_categories("RENDERMANSHADERNODES")
    except RuntimeError:
        rfb_log().debug('Could not unregister node categories class: RENDERMANSHADERNODES')
        pass               

    rman_bl_nodes_props.unregister()
    rman_bl_nodes_sockets.unregister()    
    rman_bl_nodes_shaders.unregister()
    rman_bl_nodes_ops.unregister()  
    rman_bl_nodes_menus.unregister()