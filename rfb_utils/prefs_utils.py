from ..rman_constants import RFB_PREFS_NAME, BLENDER_PYTHON_VERSION_MAJOR, BLENDER_PYTHON_VERSION_MINOR
import bpy
import sys
import os

IMPORT_QT_SUCCEED = None

def get_addon_prefs():
    try:
        addon = bpy.context.preferences.addons[RFB_PREFS_NAME]
        return addon.preferences
    except:
        # try looking for all variants of RFB_PREFS_NAME
        for k, v in bpy.context.preferences.addons.items():
            if RFB_PREFS_NAME in k:
                return v
        return None
    
def _have_pyside():
    global IMPORT_QT_SUCCEED
    if IMPORT_QT_SUCCEED is None:
        for p in sys.path:
            for root, dirnames, files in os.walk(p):
                for d in dirnames:
                    if 'PySide' in d:
                        IMPORT_QT_SUCCEED = True
                        break

    return IMPORT_QT_SUCCEED

def using_qt():
    if bpy.app.background:
        return False
    if not _have_pyside():
        return False
    return get_pref('rman_ui_framework') == 'QT'

def show_wip_qt():
    if bpy.app.background:
        return False
    if not _have_pyside():
        return False        
    return get_pref('rman_show_wip_qt')

def single_node_view():
    return get_pref('rman_single_node_view')

def get_pref(pref_name='', default=None):
    """ Return the value of a preference

    Args:
        pref_name (str) - name of the preference to look up
        default (AnyType) - default to return, if pref_name doesn't exist

    Returns:
        (AnyType) - preference value.
    """

    prefs = get_addon_prefs()
    if not prefs:
        if default is None:
            from ..preferences import __DEFAULTS__
            default = __DEFAULTS__.get(pref_name, None)
        return default
    return getattr(prefs, pref_name, default)

def get_bl_temp_dir():
    return bpy.context.preferences.filepaths.temporary_directory