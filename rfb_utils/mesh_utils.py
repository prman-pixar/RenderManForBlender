import numpy as np
from ..rman_constants import BLENDER_41

class RmanMesh:
    def __init__(self, *args, **kwargs):
        self.nverts = args[0]
        self.verts = args[1]
        self.P = args[2]
        self.N = args[3]

        self.npolys = len(self.nverts)
        self.npoints = int(len(self.P) / 3)
        self.numnverts = len(self.verts)
        if self.N is not None:
            self.nnormals = int(len(self.N) / 3)

    def __eq__(self, other):
        if self.nverts != other.nverts or self.verts != other.verts or self.P != other.P or self.N != other.N:
            return False
        return True


def get_mesh_points_(mesh):
    '''
    Get just the points for the input mesh.

    Arguments:
    mesh (bpy.types.Mesh) - Blender mesh

    Returns:
    (numpy.ndarray) - the points on the mesh
    '''

    nvertices = len(mesh.vertices)
    P = np.zeros(nvertices*3, dtype=np.float32)
    mesh.vertices.foreach_get('co', P)
    return P

def get_mesh(mesh, get_normals=False):
    '''
    Get the basic primvars needed to render a mesh.

    Arguments:
    mesh (bpy.types.Mesh) - Blender mesh
    get_normals (bool) - Whether or not normals are needed

    Returns:
    (list) - this includes nverts (the number of vertices for each face), 
            vertices list, points, and normals
    '''

    P = get_mesh_points_(mesh)
    N = None  

    npolygons = len(mesh.polygons)
    fastnvertices = np.zeros(npolygons, dtype=np.int32)
    mesh.polygons.foreach_get('loop_total', fastnvertices)
    nverts = fastnvertices

    loops = len(mesh.loops)
    fastvertices = np.zeros(loops, dtype=np.int32)
    mesh.loops.foreach_get('vertex_index', fastvertices)
    verts = fastvertices

    if get_normals:
        if BLENDER_41:
            # Blender 4.1 no longer has the calc_normals_split function
            # It's recommended to always use the corner_normals collection
            fastnormals = np.zeros(loops*3, dtype=np.float32)
            mesh.corner_normals.foreach_get('vector', fastnormals)
            N = fastnormals                
        else:
            fastsmooth = np.zeros(npolygons, dtype=np.int32)
            mesh.polygons.foreach_get('use_smooth', fastsmooth)

            if mesh.use_auto_smooth or True in fastsmooth:
                mesh.calc_normals_split()
                fastnormals = np.zeros(loops*3, dtype=np.float32)
                mesh.loops.foreach_get('normal', fastnormals)
                N = fastnormals
            else:        
                fastnormals = np.zeros(npolygons*3, dtype=np.float32)
                mesh.polygons.foreach_get('normal', fastnormals)
                N = fastnormals

    rman_mesh = RmanMesh(nverts, verts, P, N)
    return rman_mesh