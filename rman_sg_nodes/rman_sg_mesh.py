from .rman_sg_node import RmanSgNode

class RmanSgMesh(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.matrix_world = None
        self.npolys = -1 
        self.npoints = -1
        self.nverts = -1
        self.is_subdiv = False
        self.subdiv_scheme = 'none'
        self.is_multi_material = False
        self.multi_material_children = []
        self.sg_mesh = None

    def __del__(self):
        if self.rman_scene.rman_render.rman_context.is_render_running() and self.rman_scene.rman_render.sg_scene:
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene): 
                self.rman_scene.sg_scene.DeleteDagNode(self.sg_mesh)
        super().__del__()

    @property
    def matrix_world(self):
        return self.__matrix_world

    @matrix_world.setter
    def matrix_world(self, mtx):
        self.__matrix_world = mtx

    @property
    def npolys(self):
        return self.__npolys

    @npolys.setter
    def npolys(self, npolys):
        self.__npolys = npolys

    @property
    def npoints(self):
        return self.__npoints

    @npoints.setter
    def npoints(self, npoints):
        self.__npoints = npoints

    @property
    def nverts(self):
        return self.__nverts

    @nverts.setter
    def nverts(self, nverts):
        self.__nverts = nverts 

    @property
    def is_subdiv(self):
        return self.__is_subdiv

    @is_subdiv.setter
    def is_subdiv(self, is_subdiv):
        self.__is_subdiv = is_subdiv    

    @property
    def subdiv_scheme(self):
        return self.__subdiv_scheme

    @subdiv_scheme.setter
    def subdiv_scheme(self, subdiv_scheme):
        self.__subdiv_scheme = subdiv_scheme                                       