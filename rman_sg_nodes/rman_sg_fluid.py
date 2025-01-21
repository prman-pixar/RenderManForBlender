from .rman_sg_node import RmanSgNode

class RmanSgFluid(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.rman_sg_volume_node = None
        self.rman_sg_liquid_node = None
        
    def __del__(self):
        super().__del__()
        pass
        '''
        if self.rman_scene.rman_render.rman_context.is_render_running() and self.rman_scene.sg_scene:
            self.rman_scene.sg_scene.DeleteDagNode(self.rman_sg_volume_node)
            self.rman_scene.sg_scene.DeleteDagNode(self.rman_sg_liquid_node)
            super().__del__()
        '''