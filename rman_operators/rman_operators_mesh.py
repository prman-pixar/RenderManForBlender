from ..rfb_logger import rfb_log
from ..rfb_utils import mesh_utils
import bpy
from bpy.props import BoolProperty
from mathutils import Vector, Matrix

class PRMAN_OT_Renderman_mesh_reference_pose(bpy.types.Operator):
    bl_idname = 'mesh.freeze_reference_pose'
    bl_label = "Freeze Reference Pose"
    bl_description = "Use the mesh's points and normals for the current frame as the reference pose. This essentially adds the __Pref, __NPref, __Nref and __WNref primitive variables."

    add_Pref: BoolProperty(name='Add __Pref', default=True)
    add_WPref: BoolProperty(name='Add __WPref', default=True)
    add_Nref: BoolProperty(name='Add __Nref', default=True)
    add_WNref: BoolProperty(name='Add __WNref', default=True)

    @classmethod
    def poll(cls, context):
        if context.engine != "PRMAN_RENDER":
            return False        
        if context.object is None:
            return False
        if context.mesh is None:
            return False
        return True

    def execute(self, context):
        mesh = context.mesh
        ob = context.object
        rm = mesh.renderman
        rm.reference_pose.clear()
        rm.reference_pose_normals.clear()
        
        matrix_world = ob.matrix_world
        if not self.add_Pref and not self.add_WPref and not self.add_Nref and not self.add_WNref:
            return {'FINISHED'}

        rman_mesh = mesh_utils.get_mesh(mesh, get_normals=True)
        if self.add_Pref or self.add_WPref:
            Plist = rman_mesh.P.reshape((-1,3))
            for P in Plist:
                rp = rm.reference_pose.add()
                if self.add_Pref:
                    rp.has_Pref = True
                    rp.rman__Pref = P

                if self.add_WPref:
                    rp.has_WPref = True
                    v = Vector(P)
                    v = matrix_world @ v
                    rp.rman__WPref = v

        if self.add_Nref or self.add_WNref:
            Nlist = rman_mesh.N.reshape((-1,3))
            for N in Nlist:
                rp = rm.reference_pose_normals.add()
                if self.add_Nref:
                    rp.has_Nref = True
                    rp.rman__Nref = N
            
                if self.add_WNref:
                    rp.has_WNref = True
                    n = Vector(N)
                    n = matrix_world @ n
                    rp.rman__WNref = n                    

        ob.update_tag(refresh={'DATA'})
        return {'FINISHED'}

    def invoke(self, context, event=None):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

classes = [
    PRMAN_OT_Renderman_mesh_reference_pose
]

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes)
    
def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)
