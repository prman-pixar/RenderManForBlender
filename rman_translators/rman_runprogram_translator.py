from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_runprogram import RmanSgRunProgram

class RmanRunProgramTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'PROCEDURAL_RUN_PROGRAM' 

    def export(self, ob, db_name):

        sg_node = self.rman_scene.sg_scene.CreateProcedural(db_name)
        sg_node.Define(self.rman_scene.rman.Tokens.Rix.k_RunProgram, None)
        rman_sg_runprogram = RmanSgRunProgram(self.rman_scene, sg_node, db_name)

        return rman_sg_runprogram

    def export_deform_sample(self, rman_sg_runprogram, ob, time_sample):
        pass


    def update(self, ob, rman_sg_runprogram):
        rm = ob.renderman
        path_runprogram = rm.path_runprogram
        bounds = (-100000, 100000, -100000, 100000, -100000, 100000 )

        primvar = rman_sg_runprogram.sg_node.GetPrimVars()
        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_filename, path_runprogram)
        primvar.SetString(self.rman_scene.rman.Tokens.Rix.k_data, rm.runprogram_args)
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_bound, bounds, 6)
        super().export_object_primvars(ob, primvar)
        rman_sg_runprogram.sg_node.SetPrimVars(primvar)        
