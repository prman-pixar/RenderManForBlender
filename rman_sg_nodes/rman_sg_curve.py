from .rman_sg_mesh import RmanSgMesh

class RmanSgCurve(RmanSgMesh):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.is_mesh = False
        self.sg_mesh_node = None

    @property
    def is_mesh(self):
        return self.__is_mesh

    @is_mesh.setter
    def is_mesh(self, is_mesh):
        self.__is_mesh = is_mesh        

    @property
    def sg_mesh_node(self):
        return self.__sg_mesh_node

    @sg_mesh_node.setter
    def sg_mesh_node(self, sg_mesh_node):
        self.__sg_mesh_node = sg_mesh_node         