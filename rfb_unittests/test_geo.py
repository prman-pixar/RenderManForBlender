import unittest
import bpy
import numpy as np
from ..rfb_utils import mesh_utils
from ..rman_constants import BLENDER_41


class GeoTest(unittest.TestCase):

    @classmethod
    def add_tests(self, suite):
        suite.addTest(GeoTest('test_mesh_export'))

    def test_mesh_export(self):

        def test_eq(a, b, msg=None):
            if a != b:
                msg = "Mesh export test failed"
                bpy.ops.object.delete()
                raise self.failureException(msg)                 

        nverts = [4, 4, 4, 4, 4, 4]
        verts = [0, 1, 3, 2, 2, 3, 7, 6, 6, 7, 5, 4, 4, 5, 1, 0, 2, 6, 4, 0, 7, 3, 1, 5]
        P = [-1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0]
        if BLENDER_41:
            N = [-1.0, 0.0, 0.0, -1.0, 0.0, 0.0, -1.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, -1.0, 0.0, 0.0, -1.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, -1.0, 0.0, 0.0, -1.0, 0.0, 0.0, -1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0]
        else:
            N = [-1.0, -0.0, 0.0, 0.0, 1.0, 0.0, 1.0, -0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, -1.0, 0.0, -0.0, 1.0]

        mesh = mesh_utils.RmanMesh(nverts, verts, P, N)

        bpy.ops.mesh.primitive_cube_add()
        ob = bpy.context.object

        mesh_test = mesh_utils.get_mesh(ob.data, get_normals=True)

        self.addTypeEqualityFunc(mesh_utils.RmanMesh, test_eq)
        self.assertEqual(mesh, mesh_test)
        bpy.ops.object.delete()

        
