from ..rfb_logger import rfb_log
import bpy
import re
import os


def readOSO(filePath):
    try:
        from oslquery import OSLQuery as OslQuery
    except ImportError:
        try:
            from rman_thirdparty.oslquery import OslQuery
        except ImportError:
            from oslquery import OslQuery

    oinfo = OslQuery()
    oinfo.open(filePath)

    shader_meta = {}
    prop_names = []
    shader_meta["shader"] = oinfo.shadername()

    if isinstance(oinfo.nparams, int):
        # using the oslquery module from Blender
        for param in oinfo.parameters: 
            name = param.name
            type = 'struct' if param.isstruct else param.type.c_str()
            prop_names.append(name)

            IO = "in"
            if param.isoutput:
                IO = "out"

            prop_meta = {"type": type, "IO": IO}            
            prop_meta['renderman_type'] = type

            # default
            if param.value is None:
                if prop_meta['type'] == 'float':
                    prop_meta['default'] = 0.0
                elif prop_meta['type'] == 'int':
                    prop_meta['default'] = 0
                elif prop_meta['type'] in ['color', 'point', 'normal', 'vector']:
                    prop_meta['default'] = (0.0, 0.0, 0.0)
                else:
                    prop_meta['default'] = ""
            elif not param.isstruct:
                prop_meta['default'] = param.value
                if prop_meta['type'] == 'float':
                    prop_meta['default'] = float('%g' % prop_meta['default'])

            # metadata
            for mdict in param.metadata:
                if mdict.name == 'tag' and mdict.value == 'vstruct':
                    prop_meta['type'] = 'vstruct'
                elif mdict.name == 'vstructmember':
                    prop_meta['vstructmember'] =  mdict.value
                elif mdict.name == 'vstructConditionalExpr':
                    prop_meta['vstructConditionalExpr'] =  mdict.value.replace('  ', ' ')
                elif mdict.name == 'match':
                    prop_meta['match'] = mdict.value
                elif mdict.name == 'connectable':
                    prop_meta['connectable'] = bool(mdict.value)
                elif mdict.name == 'lockgeom':
                    dflt = 1
                    lockgeom = getattr(mdict, 'default', dflt)
                    lockgeom = getattr(mdict, 'lockgeom', lockgeom)
                    prop_meta['lockgeom'] = lockgeom

            shader_meta[name] = prop_meta  
    else:
        for i in range(oinfo.nparams()): 
            pdict = oinfo.getparam(i)  

            name = pdict['name']      
            type = 'struct' if pdict['isstruct'] else pdict['type']  
            prop_names.append(name)

            IO = "in"
            if pdict['isoutput']:
                IO = "out"

            prop_meta = {"type": type, "IO": IO}            
            prop_meta['renderman_type'] = type

            # default
            if pdict['default'] is None:
                if prop_meta['type'] == 'float':
                    prop_meta['default'] = 0.0
                elif prop_meta['type'] == 'int':
                    prop_meta['default'] = 0
                elif prop_meta['type'] in ['color', 'point', 'normal', 'vector']:
                    prop_meta['default'] = (0.0, 0.0, 0.0)
                else:
                    prop_meta['default'] = ""
            elif not pdict['isstruct']:
                prop_meta['default'] = pdict['default']
                if prop_meta['type'] == 'float':
                    prop_meta['default'] = float('%g' % prop_meta['default'])

            # metadata
            for mdict in pdict.get('metadata', []):
                if mdict['name'] == 'tag' and mdict['default'] == 'vstruct':
                    prop_meta['type'] = 'vstruct'
                elif mdict['name'] == 'vstructmember':
                    prop_meta['vstructmember'] = mdict['default']
                elif mdict['name'] == 'vstructConditionalExpr':
                    prop_meta['vstructConditionalExpr'] = mdict['default'].replace('  ', ' ')
                elif mdict['name'] == 'match':
                    prop_meta['match'] = mdict['default']  
                elif mdict['name'] == 'connectable':
                    prop_meta['connectable'] = bool(mdict['default'])
                elif mdict['name'] == 'lockgeom':
                    dflt = 1
                    lockgeom = mdict.get('default', dflt)
                    lockgeom = mdict.get('lockgeom', lockgeom)
                    prop_meta['lockgeom'] = lockgeom

            shader_meta[name] = prop_meta                

    return prop_names, shader_meta    