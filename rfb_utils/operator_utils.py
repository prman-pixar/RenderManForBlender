from .. import rman_bl_nodes
from ..rfb_icons import get_bxdf_icon, get_light_icon, get_lightfilter_icon, get_projection_icon
from ..rman_constants import RMAN_BL_NODE_DESCRIPTIONS

def get_description(category, node_name):
    description = None
    for n in rman_bl_nodes.__RMAN_NODES__.get(category, list()):
        if n.name == node_name:
            if n.help:
                description = n.help
            break
    if not description:
        description = RMAN_BL_NODE_DESCRIPTIONS.get(node_name, node_name)
    return description


def get_bxdf_items():
 
    items = []
    i = 1
    for bxdf_cat, bxdfs in rman_bl_nodes.__RMAN_NODE_CATEGORIES__['bxdf'].items():
        if not bxdfs[1]:
            continue
        tokens = bxdf_cat.split('_')
        bxdf_category = ' '.join(tokens[1:])      
        items.append(('', bxdf_category.capitalize(), '', 0, 0))
        for n in bxdfs[1]:
            rman_bxdf_icon = get_bxdf_icon(n.name)
            items.append( (n.name, n.name, '', rman_bxdf_icon.icon_id, i))       
            i += 1

    return items     

def get_light_items():
    rman_light_icon = get_light_icon("PxrRectLight")
    items = []
    i = 0
    dflt = 'PxrRectLight'
    items.append((dflt, dflt, '', rman_light_icon.icon_id, i))
    for n in rman_bl_nodes.__RMAN_LIGHT_NODES__:
        if n.name == 'PxrMeshLight':
            continue
        if n.name != dflt:
            i += 1
            light_icon = get_light_icon(n.name)
            description = get_description('light', n.name)
            description = RMAN_BL_NODE_DESCRIPTIONS.get(n.name, n.name)
            if n.help:
                description = n.help            
            items.append( (n.name, n.name, description, light_icon.icon_id, i))
    return items    

def get_lightfilter_items():
    items = []
    i = 0
    rman_light_icon = get_lightfilter_icon("PxrRodLightFilter")
    dflt = 'PxrRodLightFilter'
    items.append((dflt, dflt, '', rman_light_icon.icon_id, i))
    for n in rman_bl_nodes.__RMAN_LIGHTFILTER_NODES__:
        if n.name != dflt and n.name not in ['PxrBlockerLightFilter', 'PxrGoboLightFilter']:
            i += 1
            light_icon = get_lightfilter_icon(n.name)
            description = RMAN_BL_NODE_DESCRIPTIONS.get(n.name, n.name)
            if n.help:
                description = n.help
            items.append( (n.name, n.name, description, light_icon.icon_id, i))
    return items    

def get_projection_items():
    items = []
    i = 0
    proj_icon = get_projection_icon("PxrCamera")
    dflt = 'PxrCamera'
    items.append((dflt, dflt, '', proj_icon.icon_id, i))
    for n in rman_bl_nodes.__RMAN_PROJECTION_NODES__:
        if n.name != dflt:
            i += 1
            proj_icon = get_projection_icon(n.name)
            description = RMAN_BL_NODE_DESCRIPTIONS.get(n.name, n.name)
            if n.help:
                description = n.help            
            items.append( (n.name, n.name, description, proj_icon.icon_id, i))
    return items        