from . import rman_properties_scene
from . import rman_properties_misc
from . import rman_properties_object
from . import rman_properties_mesh
from . import rman_properties_material
from . import rman_properties_curve
from . import rman_properties_world
from . import rman_properties_renderlayers
from . import rman_properties_camera
from . import rman_properties_particles
from . import rman_properties_volume

def pre_register():
    # These properties have to be registered before
    # we start parsing our shading nodes
    rman_properties_misc.register() 

def register():
  
    rman_properties_renderlayers.register()    
    rman_properties_scene.register()
    rman_properties_object.register()
    rman_properties_mesh.register()
    rman_properties_material.register()
    rman_properties_curve.register()
    rman_properties_world.register()
    rman_properties_camera.register()
    rman_properties_particles.register()
    rman_properties_volume.register()

def unregister():
    rman_properties_misc.unregister()    
    rman_properties_renderlayers.unregister()
    rman_properties_scene.unregister()
    rman_properties_object.unregister()
    rman_properties_mesh.unregister()
    rman_properties_material.unregister()
    rman_properties_curve.unregister()
    rman_properties_world.unregister()
    rman_properties_camera.unregister()
    rman_properties_particles.unregister()
    rman_properties_volume.unregister()