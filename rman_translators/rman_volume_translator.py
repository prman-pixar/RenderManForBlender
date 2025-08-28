from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_volume import RmanSgVolume
from ..rfb_utils import scenegraph_utils
from ..rfb_utils import transform_utils
from ..rfb_utils import property_utils
from ..rfb_logger import rfb_log

import bpy

class RmanVolumeTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'RI_VOLUME'       

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateVolume(db_name)
        rman_sg_volume = RmanSgVolume(self.rman_scene, sg_node, db_name)

        return rman_sg_volume

    def export_deform_sample(self, rman_sg_volume, ob, time_sample):
        pass

    def update_primvar(self, ob, rman_sg_volume, prop_name):
        primvars = rman_sg_volume.sg_node.GetPrimVars()
        super().update_object_primvar(ob, primvars, prop_name)
        rman_sg_volume.sg_node.SetPrimVars(primvars)    

    def update(self, ob, rman_sg_volume):       
        rman_sg_volume.sg_node.Define(0,0,0)
        primvar = rman_sg_volume.sg_node.GetPrimVars()
        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_Ri_type, "box")
        if ob.type == 'EMPTY':
            scale = [1.0, 1.0, 1.0] #ob.scale
            display_size = ob.empty_display_size
            bound_box = [-display_size * scale[0], display_size * scale[0], -display_size * scale[1], display_size * scale[1], -display_size * scale[2], display_size * scale[2] ]
            primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_Bound, bound_box, 6)
        else:
            primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_Bound, transform_utils.convert_ob_bounds(ob.bound_box), 6)
        scenegraph_utils.export_vol_aggregate(self.rman_scene.bl_scene, primvar, ob)            
        super().export_object_primvars(ob, primvar)            
        rman_sg_volume.sg_node.SetPrimVars(primvar)           