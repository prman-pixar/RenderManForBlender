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
from rman_utils.rman_assets import lib as ral
from rman_utils.rman_assets.core import RmanAsset
from rman_utils.filepath import FilePath

import os
import os.path
import bpy
from ..rfb_utils.envconfig_utils import envconfig
from ..rfb_utils import shadergraph_utils
from ..rfb_utils import object_utils   
from ..rfb_utils import color_manager_blender as clr_mgr
from ..rfb_utils.prefs_utils import get_pref, get_addon_prefs
from ..rfb_logger import rfb_log
from . import core as bl_pb_core

def get_host_prefs():
    return bl_pb_core.get_host_prefs()

def bl_export_check(mode, hdr=None, context=None, include_display_filters=False): # pylint: disable=unused-argument
    hostPrefs = get_host_prefs()
    if mode == 'material':
        ob = context.active_object
        mat = ob.active_material
        hostPrefs.blender_material = mat
        hostPrefs.gather_material_nodes(mat) 
        hostPrefs._nodesToExport['displayfilter'] = list()
        if include_display_filters:
            hostPrefs.gather_displayfilter_nodes(context)

    elif mode == 'lightrigs':
        lst = list()
        selected_light_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:  
                if object_utils._detect_primitive_(obj) == 'LIGHT':
                    selected_light_objects.append(obj)
        if not selected_light_objects:
            return False
        lst.extend(selected_light_objects)
        hostPrefs._nodesToExport['lightrigs'] = lst
    elif mode == 'envmap':
        if not hdr.exists():
            rfb_log().warning('hdr file does not exist: %s', hdr)
            return False
        hostPrefs._nodesToExport['envmap'] = [hdr]
        hostPrefs._defaultLabel = bl_pb_core.default_label_from_file_name(hdr)
        return True
    else:
        rfb_log().error('preExportCheck: unknown mode: %s', repr(mode))
        return False
    return True    

def bl_export_material(hostPrefs, categorypath, infodict, previewtype): # pylint: disable=unused-argument
    return bl_export_asset(hostPrefs._nodesToExport, 'nodeGraph', infodict, categorypath,
                        hostPrefs.cfg, previewtype, isLightRig=False)

def bl_export_LightRig(hostPrefs, categorypath, infodict, previewtype): # pylint: disable=unused-argument
    return bl_export_asset(hostPrefs._nodesToExport, 'nodeGraph', infodict, categorypath,
                        hostPrefs.cfg, previewtype, isLightRig=True)

def bl_export_envmap(hostPrefs, categorypath, infodict, previewtype): # pylint: disable=unused-argument
    return bl_export_asset(hostPrefs._nodesToExport, 'envMap', infodict, categorypath,
                        hostPrefs.cfg, previewtype)

def bl_load_asset(filepath):
    # early exit
    if not os.path.exists(filepath):
        raise None

    Asset = RmanAsset()
    Asset.load(filepath, localizeFilePaths=True)
    return Asset    


def bl_import_asset(Asset):
    assetType = Asset.type()

    hostPrefs = get_host_prefs()
    import_displayfilters = hostPrefs.import_displayfilters
    hostPrefs.import_displayfilters = False

    if assetType == "nodeGraph":
        mat = None
        path = os.path.dirname(Asset.path())
        if Asset.displayFilterList() and import_displayfilters:
            bl_pb_core.create_displayfilter_nodes(Asset)
        if Asset.nodeList():
            paths = path.split('/')
            if 'Materials' in paths:
                mat,nt,newNodes = bl_pb_core.createNodes(Asset)
                bl_pb_core.connectNodes(Asset, nt, newNodes)
            elif 'LightRigs' in paths:
                newNodes = bl_pb_core.import_light_rig(Asset)

        return mat

    elif assetType == "envMap":
        scene = bpy.context.scene
        dome_lights = [ob for ob in scene.objects if ob.type == 'LIGHT' \
            and ob.data.renderman.get_light_node_name() == 'PxrDomeLight']

        selected_dome_lights = [ob for ob in dome_lights if ob.select_get()]
        env_map_path = Asset.envMapPath()

        if not selected_dome_lights:
            if not dome_lights:
                # create a new dome light              
                bpy.ops.object.rman_add_light(rman_light_name='PxrDomeLight')
                ob = bpy.context.view_layer.objects.active
                plugin_node = ob.data.renderman.get_light_node()
                plugin_node.lightColorMap = env_map_path                    

            elif len(dome_lights) == 1:
                light = dome_lights[0].data
                plugin_node = light.renderman.get_light_node()
                plugin_node.lightColorMap = env_map_path
            else:
                rfb_log().error('More than one dome in scene.  Not sure which to use')
        else:
            for light in selected_dome_lights:
                light = dome_lights[0].data
                plugin_node = light.renderman.get_light_node()
                plugin_node.lightColorMap = env_map_path

    else:
        raise bl_pb_core.RmanAssetBlenderError("Unknown asset type : %s" % assetType)

    return ''    

def bl_export_asset(nodes, atype, infodict, category, cfg, renderPreview='std',
                 alwaysOverwrite=False, isLightRig=False):
    """Exports a nodeGraph or envMap as a RenderManAsset.

    Args:
        nodes (dict) -- dictionary containing the nodes to export
        atype (str) -- Asset type : 'nodeGraph' or 'envMap'
        infodict (dict) -- dict with 'label', 'author' & 'version'
        category (str) -- Category as a path, i.e.: "/Lights/LookDev"

    Kwargs:
        renderPreview (str) -- Render an asset preview ('std', 'fur', None).\
                        Render the standard preview swatch by default.\
                        (default: {'std'})
        alwaysOverwrite {bool) -- Will ask the user if the asset already \
                        exists when not in batch mode. (default: {False})
    """
    label = infodict['metadict']['label']
    Asset = RmanAsset(assetType=atype, label=label, previewType=renderPreview,
                              storage=infodict.get('storage', None),
                              convert_to_tex=infodict.get('convert_to_tex', True)
    )

    # On save, we can get the current color manager to store the config.
    color_mgr = clr_mgr.color_manager()
    ocio_config = {
        'config': color_mgr.cfg_name,
        'path': color_mgr.config_file_path(),
        'rules': color_mgr.conversion_rules,
        'aliases': color_mgr.aliases
    }
    rfb_log().debug('ocio_config %s', '=' * 80)
    rfb_log().debug('     config = %s', ocio_config['config'])
    rfb_log().debug('       path = %s', ocio_config['path'])
    rfb_log().debug('      rules = %s', ocio_config['rules'])
    Asset.ocio = ocio_config    

    hostPrefs = get_host_prefs()    

    # Add user metadata
    #
    for k, v in infodict['metadict'].items():
        if k == 'label':
            continue
        Asset.addMetadata(k, v)

    # Compatibility data
    # This will help other application decide if they can use this asset.
    #
    prmanversion = envconfig().build_info.version()
    Asset.setCompatibility(hostName='Blender',
                           hostVersion=bpy.app.version_string,
                           rendererVersion=prmanversion)                           

    # parse maya scene
    #
    if atype == "nodeGraph":
        if not isLightRig:
            bl_pb_core.export_material_preset(hostPrefs.blender_material, nodes['material'], hostPrefs.renderman_output_node, Asset)
            if nodes['displayfilter']:
                bl_pb_core.export_displayfilter_nodes(hostPrefs.bl_world, nodes['displayfilter'], Asset)
        else:
            bl_pb_core.export_light_rig(nodes['lightrigs'], Asset)
    elif atype == "envMap":
        bl_pb_core.parse_texture(nodes['envmap'][0], Asset)
    else:
        raise bl_pb_core.RmanRmanAssetBlenderError("%s is not a known asset type !" % atype)

    #  Get path to our library
    #
    assetPath = ral.getAbsCategoryPath(cfg, category)

    #  Create our directory
    #
    assetDir = bl_pb_core.asset_name_from_label(str(label))
    dirPath = assetPath.join(assetDir)
    if not dirPath.exists():
        os.mkdir(dirPath)

    #   Check if we are overwriting an existing asset
    #
    jsonfile = dirPath.join("asset.json")

    #  Save our json file
    #
    # print("export_asset: %s..." %   dirPath)
    Asset.save(jsonfile, compact=False)
    ral.renderAssetPreview(Asset, progress=None, rmantree=envconfig().rmantree)

    return True
