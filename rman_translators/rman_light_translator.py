from .rman_translator import RmanTranslator
from .rman_lightfilter_translator import RmanLightFilterTranslator
from ..rman_sg_nodes.rman_sg_light import RmanSgLight
from ..rman_sg_nodes.rman_sg_lightfilter import RmanSgLightFilter
from ..rfb_utils import string_utils
from ..rfb_utils import property_utils
from ..rfb_utils import transform_utils
from ..rfb_utils import object_utils
from ..rfb_utils import scene_utils
from ..rfb_logger import rfb_log
from mathutils import Matrix
import math
import bpy

s_orientTransform = [0, 0, -1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1]

s_orientPxrLight = [-1.0, 0.0, -0.0, 0.0,
                    -0.0, -1.0, -0.0, 0.0,
                    0.0, 0.0, -1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0]

s_orientPxrDomeLight = [0.0, 1.0, 0.0, 0.0, 
                        -1.0, 0.0, 0.0, 0.0, 
                        0.0, -0.0, 1.0, 0.0, 
                        0.0, 0.0, 0.0, 1.0]

s_orientPxrEnvDayLight = [-0.0, 1.0, 0.0, 0.0, 
                          1.0, 0.0, -0.0, 0.0, 
                          0.0, 0.0, 1.0, 0.0, 
                          0.0, 0.0, 0.0, 1.0]

s_orientPxrEnvDayLightInv = [-0.0, 1.0, -0.0, 0.0,
                            -0.0, 0.0, 1.0, -0.0,
                            -1.0, -0.0, 0.0, -0.0,
                            0.0, -0.0, -0.0, 1.0]

class RmanLightTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'LIGHT'  

    def export_object_attributes(self, ob, rman_sg_node, remove=True):
        pass

    def export(self, ob, db_name):

        light = ob.data
        rm = light.renderman        
        sg_node = self.rman_scene.sg_scene.CreateAnalyticLight(db_name)                
        rman_sg_light = RmanSgLight(self.rman_scene, sg_node, db_name)
        if self.rman_scene.do_motion_blur:
            rman_sg_light.is_transforming = object_utils.is_transforming(ob)
        return rman_sg_light

    def update_light_filters(self, ob, rman_sg_light):
        light = ob.original.data
        rm = light.renderman      
        lightfilter_translator = self.rman_scene.rman_translators['LIGHTFILTER']
        lightfilter_translator.export_light_filters(ob, rman_sg_light, rm)

    def update_light_attributes(self, ob, rman_sg_light):
        light = ob.data
        rm = light.renderman             

        primary_vis = rm.light_primary_visibility
        attrs = rman_sg_light.sg_node.GetAttributes()
        attrs.SetInteger("visibility:camera", int(primary_vis))
        attrs.SetInteger("visibility:transmission", 0)
        attrs.SetInteger("visibility:indirect", 0)
        obj_groups_str = "World,%s" % string_utils.sanitize_node_name(ob.name_full)
        attrs.SetString(self.rman_scene.rman.Tokens.Rix.k_grouping_membership, obj_groups_str)

        rman_sg_light.sg_node.SetAttributes(attrs)

    def update(self, ob, rman_sg_light):

        light = ob.original.data
        rm = light.renderman  

        # light filters
        self.update_light_filters(ob, rman_sg_light)
        
        light_shader = rm.get_light_node()

        sg_node = None            
        light_shader_name = ''
        is_bl_light = False
        if light_shader:
            light_shader_name = rm.get_light_node_name()

            if light_shader_name == 'PxrDomeLight':
                # check if there are portals attached to this dome light
                # if there are, set the light shader to None and return
                any_portals = False

                for portal_pointer in rm.portal_lights:
                    if portal_pointer.linked_portal_ob:
                        any_portals = True
                        break

                if any_portals:
                    rman_sg_light.sg_node.SetLight(None)
                    return

            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Light", light_shader_name , rman_sg_light.db_name)
            property_utils.property_group_to_rixparams(light_shader, rman_sg_light, sg_node, ob=ob)
            
            rixparams = sg_node.params
            rman_sg_light.sg_node.SetLight(sg_node)
            self.update_light_attributes(ob, rman_sg_light) 

            # check to see if this a portal light
            if light_shader_name == 'PxrPortalLight':
                portal_parent = rm.dome_light_portal

                # if this portal light is attached to a dome light, 
                # inherit the dome light's parameters
                if portal_parent:
                    portal_parent = portal_parent.original
                    parent_node = portal_parent.data.renderman.get_light_node()

                    rixparams.SetString('portalName', rman_sg_light.db_name)
                    property_utils.portal_inherit_dome_params(light_shader, portal_parent, parent_node, rixparams)

                    # Calculate the portalToDome matrix
                    portal_mtx = transform_utils.convert_matrix4x4(s_orientPxrLight) * transform_utils.convert_matrix4x4(ob.matrix_world)
                    dome_mtx = transform_utils.convert_matrix4x4(s_orientPxrDomeLight) *  transform_utils.convert_matrix4x4(portal_parent.matrix_world)
                    inv_dome_mtx = self.rman_scene.rman.Types.RtMatrix4x4()
                    dome_mtx.Inverse(inv_dome_mtx)
                    portalToDome = portal_mtx * inv_dome_mtx
                    rixparams.SetMatrix('portalToDome', portalToDome)

                    rman_sg_light.sg_node.SetLight(sg_node)
                else:
                    # If this portal light is not attached to a dome light
                    # Set the light shader to None
                    rman_sg_light.sg_node.SetLight(None)

        else:
            is_bl_light = True
            names = {'POINT': 'PxrSphereLight', 'SUN': 'PxrDistantLight',
                    'SPOT': 'PxrDiskLight', 'HEMI': 'PxrDomeLight', 'AREA': 'PxrRectLight'}
            light_shader_name = names[light.type]
            sg_node = self.rman_scene.rman.SGManager.RixSGShader("Light", light_shader_name , "light")
            rixparams = sg_node.params            
            if light.type == 'SUN':
                exposure = 0
                rixparams.SetFloat("exposure", 0.0)
            else:
                exposure = light.energy  # / 200.0
                rixparams.SetFloat("intensity", exposure)
            rixparams.SetColor("lightColor", string_utils.convert_val(light.color))
            if light.type not in ['HEMI', 'SUN']:
                rixparams.SetInteger('areaNormalize', 1)

            rman_sg_light.sg_node.SetLight(sg_node)
            self.update_light_attributes(ob, rman_sg_light)

        if  light_shader_name in ("PxrRectLight", 
                                "PxrDiskLight",
                                "PxrPortalLight",
                                "PxrSphereLight",
                                "PxrDistantLight",
                                "PxrPortalLight",
                                "PxrCylinderLight"):

            if is_bl_light:
                m = transform_utils.convert_to_blmatrix(s_orientPxrLight)
                if light_shader_name == 'PxrSphereLight':                    
                    m = m @ Matrix.Scale(light.shadow_soft_size * 2, 4)
                rman_sg_light.sg_node.SetOrientTransform(transform_utils.convert_matrix4x4(m))
            else:
                rman_sg_light.sg_node.SetOrientTransform(s_orientPxrLight)                  
            

        elif light_shader_name == 'PxrEnvDayLight': 
            if int(light_shader.month) != 0:   
                m = transform_utils.convert_to_blmatrix(s_orientPxrEnvDayLight)
                rman_sg_light.sg_node.SetOrientTransform(transform_utils.convert_matrix4x4(m))    
        elif light_shader_name == 'PxrDomeLight':
            rman_sg_light.sg_node.SetOrientTransform(s_orientPxrDomeLight)

        if self.rman_scene.use_blender_light_link:
            # check for shadow light linking
            if ob.original.light_linking.blocker_collection:
                shadow_subset = []
                shadow_exclude = []                
                for i, o in enumerate(ob.light_linking.blocker_collection.objects):             
                    if ob.light_linking.blocker_collection.collection_objects[i].light_linking.link_state == 'EXCLUDE':
                        shadow_exclude.append(string_utils.sanitize_node_name(ob.name)+"_shadowExcludeSubset" )
                    else:
                        shadow_subset.append(string_utils.sanitize_node_name(ob.name)+"_shadowSubset" )
        
                if shadow_subset:
                    sg_node.params.SetString("shadowSubset", ob.original.name+"_shadowSubset")
                else:
                    sg_node.params.Remove("shadowSubset")
                if shadow_exclude:
                    sg_node.params.SetString("shadowExcludeSubset", ob.original.name+"_shadowExcludeSubset")
                else:
                    sg_node.params.Remove("shadowExcludeSubset")                
            else:
                sg_node.params.Remove("shadowSubset")
                sg_node.params.Remove("shadowExcludeSubset")
            rman_sg_light.sg_node.SetLight(sg_node)