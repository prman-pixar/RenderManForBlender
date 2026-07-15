from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_openvdb import RmanSgOpenVDB
from ..rfb_utils import filepath_utils
from ..rfb_utils import transform_utils
from ..rfb_utils import string_utils
from ..rfb_utils import scenegraph_utils
from ..rfb_utils import property_utils
from ..rfb_logger import rfb_log
import json
import os
class RmanOpenVDBTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'VOLUME' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateVolume(db_name)
        sg_node.Define(0,0,0)
        rman_sg_openvdb = RmanSgOpenVDB(self.rman_scene, sg_node, db_name)

        return rman_sg_openvdb

    def export_deform_sample(self, rman_sg_openvdb, ob, time_sample):
        pass

    def update_primvar(self, ob, rman_sg_openvdb, prop_name):
        db = ob.data
        primvars = rman_sg_openvdb.sg_node.GetPrimVars()
        if prop_name in db.renderman.prop_meta:
            rm = db.renderman
            meta = rm.prop_meta[prop_name]
            rm_scene = self.rman_scene.bl_scene.renderman
            property_utils.set_primvar_bl_prop(primvars, prop_name, meta, rm, inherit_node=rm_scene)        
        else:
            super().update_object_primvar(ob, primvars, prop_name)
        rman_sg_openvdb.sg_node.SetPrimVars(primvars)

    def update(self, ob, rman_sg_openvdb):
        db = ob.data
        rm = db.renderman

        bounds = transform_utils.convert_ob_bounds(ob.bound_box)
        if bounds == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0):
            rfb_log().debug("Bounds for volume is 0.0")
            bounds = None
        primvar = rman_sg_openvdb.sg_node.GetPrimVars()
        primvar.Clear()
        if db.filepath == '':
            return

        grids = db.grids
        if not grids.is_loaded:
            if not grids.load():
                rfb_log().error("Could not load grids and metadata for volume: %s" % ob.name)  
                return

        if len(grids) < 1:
            rfb_log().error("Grids length=0: %s" % ob.name)
            return    

        active_index = grids.active_index
        active_grid = grids[active_index]  
        if active_grid.data_type not in ['FLOAT', 'DOUBLE']:  
            rfb_log().error("Active grid is not of float type: %s" % ob.name) 
            return                      
        
        if bounds:
            primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_Bound, [-1e30, 1e30, -1e30, 1e30, -1e30, 1e30], 6)

        openvdb_file = filepath_utils.get_real_path(db.filepath)
        if db.is_sequence:
            # if we have a sequence, get the current frame filepath from the grids
            openvdb_file = filepath_utils.get_real_path(grids.frame_filepath)  
            rman_sg_openvdb.is_frame_sensitive = True
        else:
            rman_sg_openvdb.is_frame_sensitive = False

        openvdb_attrs = dict()
        openvdb_attrs['filterWidth'] = getattr(rm, 'openvdb_filterwidth')
        openvdb_attrs['densityMult'] = getattr(rm, 'openvdb_densitymult')
        openvdb_attrs['densityRolloff'] = getattr(rm, 'openvdb_densityrolloff')

        json_attrs = str(json.dumps(openvdb_attrs))


        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_Ri_type, "blobbydso:impl_openvdb")  
        string_args = []
        string_args.append(openvdb_file)
        string_args.append("%s:fogvolume" % active_grid.name)
        string_args.append('')
        string_args.append(json_attrs)
        primvar.SetStringArray(self.rman_scene.rman.Tokens.Rix.k_blobbydso_stringargs, string_args, len(string_args))

        for i, grid in enumerate(grids):
            if grid.data_type in ['FLOAT', 'DOUBLE']:
                primvar.SetFloatDetail(grid.name, [], "varying")
            elif grid.data_type in ['VECTOR_FLOAT', 'VECTOR_DOUBLE', 'VECTOR_INT']:
                primvar.SetVectorDetail(grid.name, [], "varying")
            elif grid.data_type in ['INT', 'INT64', 'BOOLEAN']:
                primvar.SetIntegerDetail(grid.name, [], "varying")
            elif grid.data_type == 'STRING':
                primvar.SetStringDetail(grid.name, [], "uniform")

        scenegraph_utils.export_vol_aggregate(self.rman_scene.bl_scene, primvar, ob)     

        primvar.SetInteger("volume:dsominmax", rm.volume_dsominmax)
        primvar.SetInteger("volume:dsovelocity", rm.volume_dsovelocity)
        super().export_object_primvars(ob, primvar)
        rman_sg_openvdb.sg_node.SetPrimVars(primvar)