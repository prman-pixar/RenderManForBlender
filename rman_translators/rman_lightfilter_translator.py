from .rman_translator import RmanTranslator
from ..rfb_utils import property_utils
from ..rfb_utils import scenegraph_utils
from ..rfb_utils import object_utils
from ..rfb_utils import string_utils
from ..rman_sg_nodes.rman_sg_lightfilter import RmanSgLightFilter
from mathutils import Matrix
import bpy                    

class RmanLightFilterTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'LIGHTFILTER'  

    def export_object_attributes(self, ob, rman_sg_node, remove=True):
        pass

    def export_light_filters(self, ob, rman_sg_node, rm):
        light_filters = []
        multLFs = []
        maxLFs = []
        minLFs = []
        screenLFs = []
        has_cheat_shadow = False
        rman_sg_node.sg_node.SetLightFilter([])
        is_mesh_light = isinstance(ob, bpy.types.Material)

        # Remove all of the children 
        if is_mesh_light:
            rman_sg_node.sg_lightfilters.clear()
        else:
            for c in [ rman_sg_node.sg_node.GetChild(i) for i in range(0, rman_sg_node.sg_node.GetNumChildren())]:
                # This RemoveCoordinateSystem call seems to cause issues with editing. See RMAN-23355.
                # rman_sg_node.sg_node.RemoveCoordinateSystem(c)
                rman_sg_node.sg_node.RemoveChild(c)
                self.rman_scene.sg_scene.DeleteDagNode(c)         

        for lf in rm.light_filters:
            light_filter = lf.linked_filter_ob
            if light_filter:
                # check to make sure this light filter is still in the scene
                if not self.rman_scene.bl_scene.objects.get(light_filter.name, None):
                    continue

                light_filter_db_name = object_utils.get_db_name(light_filter)                
                rman_sg_lightfilter = self.rman_scene.rman_prototypes.get(light_filter.original.data.original)
                if not rman_sg_lightfilter:
                    rman_sg_lightfilter = self.export(light_filter, light_filter_db_name)
                elif not isinstance(rman_sg_lightfilter, RmanSgLightFilter):
                    # We have a type mismatch. Delete this scene graph node and re-export
                    # it as a RmanSgLightFilter
                    for k,rman_sg_group in rman_sg_lightfilter.instances.items():
                        self.rman_scene.get_root_sg_node().RemoveChild(rman_sg_group.sg_node)
                    rman_sg_lightfilter.instances.clear() 
                    del rman_sg_lightfilter
                    self.rman_scene.rman_prototypes.pop(light_filter.original.data.original)
                    rman_sg_lightfilter = self.export(light_filter, light_filter_db_name)

                sg_group = self.rman_scene.sg_scene.CreateGroup(light_filter_db_name)
                sg_group.SetInheritTransform(False)
                if is_mesh_light:
                    # This is a mesh light. Just add the transfrom to the RmanSgMaterial list
                    rman_sg_node.sg_lightfilters.append(sg_group)                  
                else:
                     # Add transform of lightfilter as a child node of the light
                    rman_sg_node.sg_node.AddChild(sg_group)
                    rman_sg_node.sg_node.AddCoordinateSystem(sg_group)
                    self.update_transform(light_filter, ob, sg_group)                    

                self.update(light_filter, rman_sg_lightfilter)
                light_filters.append(rman_sg_lightfilter.sg_filter_node)
                if not is_mesh_light and ob.original not in rman_sg_lightfilter.lights_list:
                    rman_sg_lightfilter.lights_list.append(ob.original)

                # check which, if any, combineMode this light filter wants
                lightfilter_node = light_filter.data.renderman.get_light_node()
                instance_name = rman_sg_lightfilter.sg_filter_node.handle.CStr()
                combineMode = getattr(lightfilter_node, 'combineMode', '')
                if combineMode == 'mult':
                    multLFs.append(instance_name)
                elif combineMode == 'max':
                    maxLFs.append(instance_name)
                elif combineMode == 'min':
                    minLFs.append(instance_name)
                elif combineMode == 'screen':
                    screenLFs.append(instance_name)
                if lightfilter_node.bl_label == "PxrCheatShadowLightFilter":
                    has_cheat_shadow = True

                if 'lightFilterParentShader' in lightfilter_node.prop_meta.keys():
                    # this light filter has a lightFilterParentShader param
                    # these light filters want the light shader name they are attached to
                    light_shader_name = rm.get_light_node_name()
                    rman_sg_lightfilter.sg_filter_node.params.SetString('__lightFilterParentShader', light_shader_name)

        if len(light_filters) > 1:
            # create a combiner node
            combiner = self.rman_scene.rman.SGManager.RixSGShader("LightFilter", 'PxrCombinerLightFilter', '%s-PxrCombinerLightFilter' % (rman_sg_node.db_name))
            if multLFs:
                combiner.params.SetLightFilterReferenceArray("mult", multLFs, len(multLFs))
            if maxLFs:
                combiner.params.SetLightFilterReferenceArray("max", maxLFs, len(maxLFs))                
            if minLFs:
                combiner.params.SetLightFilterReferenceArray("min", minLFs, len(minLFs))                
            if screenLFs:
                combiner.params.SetLightFilterReferenceArray("screen", screenLFs, len(screenLFs)) 

            if has_cheat_shadow:
                combiner.params.SetInteger("combineShadows", 1)
            else:
                combiner.params.Remove("combineShadows")

            light_filters.append(combiner)                                        

        if len(light_filters) > 0:
            if not is_mesh_light:
                # create a __lightFilterParent coordinate system
                # this is the coordinate system the light is in
                sg_group = self.rman_scene.sg_scene.CreateGroup('__lightFilterParent')
                rman_sg_node.sg_node.AddChild(sg_group)
                rman_sg_node.sg_node.AddCoordinateSystem(sg_group)

            # now, set the light filters list
            rman_sg_node.sg_node.SetLightFilter(light_filters)                 

    def export(self, ob, db_name):

        lightfilter_shader = ob.data.renderman.get_light_node_name()  
        sg_group = self.rman_scene.sg_scene.CreateGroup(db_name)

        sg_filter_node = self.rman_scene.rman.SGManager.RixSGShader("LightFilter", lightfilter_shader, '%s-%s' % (db_name, lightfilter_shader))
        rman_sg_lightfilter = RmanSgLightFilter(self.rman_scene, sg_group, db_name)
        rman_sg_lightfilter.sg_filter_node = sg_filter_node
        rman_sg_lightfilter.coord_sys = db_name
        rman_sg_lightfilter.rman_type = 'LIGHTFILTER'

        proto_key = object_utils.prototype_key(ob)
        self.rman_scene.rman_prototypes[proto_key] = rman_sg_lightfilter
        rman_sg_lightfilter.sg_node.SetInheritTransform(False)

        return rman_sg_lightfilter 
    
    def update_transform(self, ob, light_ob, sg_node):
        scenegraph_utils.update_lightfilter_transform(ob, light_ob, sg_node)

    def update(self, ob, rman_sg_lightfilter):
        lightfilter_node = ob.data.renderman.get_light_node()
        property_utils.property_group_to_rixparams(lightfilter_node, rman_sg_lightfilter, rman_sg_lightfilter.sg_filter_node, ob=ob.data)
        rixparams = rman_sg_lightfilter.sg_filter_node.params
        rixparams.SetString("coordsys", rman_sg_lightfilter.coord_sys)
            
        # check if this light filter belongs to a light link
        if self.rman_scene.use_blender_light_link:
            rixparams.SetString("linkingGroups", string_utils.sanitize_node_name(ob.name))            
        else:
            if ob.original.data.renderman.linkingGroups != "":
                rixparams.SetString("linkingGroups", ob.original.data.renderman.linkingGroups)
            else:
                rixparams.Remove("linkingGroups")