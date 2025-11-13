from ..rfb_logger import rfb_log


class RmanSgNode(object):
    '''
    RmanSgNode and subclasses are meant to be a thin layer class around a RixSceneGraph node.

    Attributes:
        rman_scene (RmanScene) - pointer back to RmanScene instance
        sg_node (RixSgNode) - main scene graph node
        db_name (str) - unique datablock name for this node
        instances (dict) - instances that uses this sg_node
        motion_steps (list) - the full list of motion time samples that are required for this Blender object
        deform_motion_steps (list) - the full list of deformation time samples that are required for this Blender object        
        is_transforming (bool) - if this object is moving
        is_deforming (bool) - if this object is deforming
        rman_type (str) - the renderman type for this object
        is_instancer (bool) - whether this object is instancer 
        is_meshlight (bool) - if this object is a mesh light.
        is_hidden (bool) - whether this object is considered hidden
        is_frame_sensitive (bool) - indicates that the sg_node should be updated on frame changes
        shared_attrs (RixSGGroup) - attributes for this object
 
    '''
    def __init__(self, rman_scene, sg_node, db_name):
        self.rman_scene = rman_scene
        self.sg_node = sg_node
        self.db_name = db_name
        self.instances = dict()
        self.motion_steps = []
        self.deform_motion_steps = []
        self.is_transforming = False
        self.is_deforming = False
        self.rman_type = ''
        self.is_instancer = False
        self.is_meshlight = False
        self.is_hidden = False
        
        # the rman_sg_node this is instance of, if any
        self.rman_sg_node_instance = None

        # pointer to a parent group, if any
        self.rman_sg_group_parent = None        

        # group node to hold any particles this node may have
        self.rman_sg_particle_group_node = None

        # indicates that this node needs updating
        # when the frame changes. This is mostly for
        # materials and lights using the {F} frame variable
        # in texture paths
        self.is_frame_sensitive = False

        # psys
        self.bl_psys_settings = None

        # attribute scenegraph node
        self.sg_attributes = None 

    def __del__(self):
        if self.rman_scene.rman_render.rman_context.is_render_running() and self.rman_scene.rman_render.sg_scene:
            with self.rman_scene.rman.SGManager.ScopedEdit(self.rman_scene.sg_scene): 
                #rfb_log().debug("Deleting dag node: %s" % self.db_name)
                self.instances.clear()
                if isinstance(self.sg_node, self.rman_scene.rman.scenegraph.Group):
                    self.rman_scene.sg_scene.DeleteDagNode(self.sg_node)
                elif isinstance(self.sg_node, self.rman_scene.rman.scenegraph.Material):
                    self.rman_scene.sg_scene.DeleteMaterial(self.sg_node)                

    def create_sg_attributes(self, ob):
        self.sg_attributes = self.rman_scene.sg_scene.CreateGroup(ob.name)

    def clear_instances(self):
        if self.rman_scene.rman_render.rman_context.is_render_running():
            self.instances.clear()

    @property
    def rman_scene(self):
        return self.__rman_scene

    @rman_scene.setter
    def rman_scene(self, rman_scene):
        self.__rman_scene = rman_scene

    @property
    def sg_node(self):
        return self.__sg_node

    @sg_node.setter
    def sg_node(self, sg_node):
        self.__sg_node = sg_node

    @property
    def db_name(self):
        return self.__db_name

    @db_name.setter
    def db_name(self, db_name):
        self.__db_name = db_name

    @property
    def instances(self):
        return self.__instances

    @instances.setter
    def instances(self, instances):
        self.__instances = instances  

    @property
    def motion_steps(self):
        return self.__motion_steps

    @motion_steps.setter
    def motion_steps(self, motion_steps):
        self.__motion_steps = motion_steps      

    @property
    def is_transforming(self):
        return self.__is_transforming

    @is_transforming.setter
    def is_transforming(self, is_transforming):
        self.__is_transforming = is_transforming 

    @property
    def is_deforming(self):
        return self.__is_deforming

    @is_deforming.setter
    def is_deforming(self, is_deforming):
        self.__is_deforming = is_deforming        

    @property
    def rman_type(self):
        return self.__rman_type

    @rman_type.setter
    def rman_type(self, rman_type):
        self.__rman_type = rman_type                           

    @property
    def is_frame_sensitive(self):
        return self.__is_frame_sensitive

    @is_frame_sensitive.setter
    def is_frame_sensitive(self, is_frame_sensitive):
        self.__is_frame_sensitive = is_frame_sensitive           

    @property
    def is_instancer(self):
        return self.__is_instancer

    @is_instancer.setter
    def is_instancer(self, is_instancer):
        self.__is_instancer = is_instancer           

    @property
    def rman_sg_node_instance(self):
        return self.__rman_sg_node_instance

    @rman_sg_node_instance.setter
    def rman_sg_node_instance(self, rman_sg_node_instance):
        self.__rman_sg_node_instance = rman_sg_node_instance        

    @property
    def rman_sg_group_parent(self):
        return self.__rman_sg_group_parent

    @rman_sg_group_parent.setter
    def rman_sg_group_parent(self, rman_sg_group_parent):
        self.__rman_sg_group_parent = rman_sg_group_parent     

    @property
    def rman_sg_particle_group_node(self):
        return self.__rman_sg_particle_group_node

    @rman_sg_particle_group_node.setter
    def rman_sg_particle_group_node(self, rman_sg_particle_group_node):
        self.__rman_sg_particle_group_node = rman_sg_particle_group_node                

    @property
    def is_meshlight(self):
        return self.__is_meshlight

    @is_meshlight.setter
    def is_meshlight(self, is_meshlight):
        self.__is_meshlight = is_meshlight                                