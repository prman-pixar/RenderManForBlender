from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_points import RmanSgPoints
from ..rfb_utils import mesh_utils

class RmanPointsTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'POINTS' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreatePoints(db_name)
        rman_sg_points = RmanSgPoints(self.rman_scene, sg_node, db_name)

        return rman_sg_points

    def export_deform_sample(self, rman_sg_points, ob, time_sample):
        mesh = None
        mesh = ob.to_mesh()

        P = mesh_utils.get_mesh_points_(mesh)

        primvar = rman_sg_points.sg_node.GetPrimVars()
        npoints = int(len(P) / 3 )

        if rman_sg_points.npoints != npoints:
            primvar.SetTimes([])
            rman_sg_points.sg_node.SetPrimVars(primvar)
            rman_sg_points.is_transforming = False
            rman_sg_points.is_deforming = False        
            return         
        
        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex", time_sample)

        rman_sg_points.sg_node.SetPrimVars(primvar) 

        ob.to_mesh_clear()       

    def update(self, ob, rman_sg_points, input_mesh=None):
        mesh = input_mesh
        rm = ob.renderman
        if not mesh:
            mesh = ob.to_mesh()        

        P = mesh_utils.get_mesh_points_(mesh)

        # if this is empty continue:
        if P is None or len(P) < 1:
            if not input_mesh:
                ob.to_mesh_clear()
            rman_sg_points.sg_node = None
            rman_sg_points.is_transforming = False
            rman_sg_points.is_deforming = False
            return None        

        npoints = int(len(P) /3 )
        rman_sg_points.sg_node.Define(npoints)
        rman_sg_points.npoints = npoints

        primvar = rman_sg_points.sg_node.GetPrimVars()
        primvar.Clear()      

        super().set_primvar_times(rman_sg_points.motion_steps, primvar)

        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex")
        primvar.SetFloatDetail(self.rman_scene.rman.Tokens.Rix.k_constantwidth, rm.primitive_point_width, "constant")
        super().export_object_primvars(ob, primvar)            
        rman_sg_points.sg_node.SetPrimVars(primvar)         

        if not input_mesh:
            ob.to_mesh_clear()           
