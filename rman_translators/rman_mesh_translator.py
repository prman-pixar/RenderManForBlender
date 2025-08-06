from .rman_translator import RmanTranslator
from ..rman_sg_nodes.rman_sg_mesh import RmanSgMesh
from ..rfb_utils import object_utils
from ..rfb_utils import mesh_utils
from ..rfb_utils import string_utils
from ..rfb_utils import property_utils
from ..rfb_utils import scenegraph_utils
from ..rfb_utils.scene_utils import BlAttribute
from ..rfb_logger import rfb_log
from ..rman_constants import BLENDER_41

import bpy
import math
import bmesh
import numpy as np

def _get_mats_faces_(nverts, material_ids):

    mats = {}
    for face_id, num_verts in enumerate(nverts):
        mat_id = material_ids[face_id]
        if mat_id not in mats:
            mats[mat_id] = []
        mats[mat_id].append(face_id)
    return mats

def _is_multi_material_(ob, mesh):
    if len(ob.data.materials) < 2 or len(mesh.polygons) == 0:
        return False

    first_mat = mesh.polygons[0].material_index
    for p in mesh.polygons:
        if p.material_index != first_mat:
            return True
    return False

# requires facevertex interpolation
def _get_mesh_uv_(mesh, name="", ob=None):
    uvs = []
    data = "uv"
    if not name:
        uv_loop_layer = mesh.uv_layers.active
        if ob and uv_loop_layer is None:
            if not hasattr(ob.original.data, 'uv_layers'):
                return None            
            # when dealing geometry nodes, uv_layers are actually
            # on the attributes property.
            # Look up from original object what the active
            # uv layer was
            active = ob.original.data.uv_layers.active
            if active:
                uv_loop_layer = mesh.attributes.get(active.name)
                data = "vector"        
    else:
        uv_loop_layer = mesh.uv_layers.get(name, None)
        if uv_loop_layer is None:
            uv_loop_layer = mesh.attributes.get(name, None)
            data = "vector"

    if uv_loop_layer is None:
        return None

    uv_count = len(uv_loop_layer.data)
    fastuvs = np.zeros(uv_count * 2)
    uv_loop_layer.data.foreach_get(data, fastuvs)   
    uvs = fastuvs

    return uvs

def _get_mesh_vcol_(mesh, name="", ob=None):    
    if not name:
        vcol_layer = mesh.vertex_colors.active
        if ob and not vcol_layer:
            if not hasattr(ob.original.data, 'vertex_colors'):
                return None
            # same issue with uv's
            # vertex colors for geometry nodes are on the attributes
            # property
            active = ob.original.data.vertex_colors.active
            if active:
                vcol_layer = mesh.attributes.get(active.name, None)        
    else:
        vcol_layer = mesh.vertex_colors[name]
        if not vcol_layer:
            vcol_layer = mesh.attributes.get(name, None)

    if vcol_layer is None:
        return None

    vcol_count = len(vcol_layer.data)
    fastvcols = np.zeros(vcol_count * 4)
    vcol_layer.data.foreach_get("color", fastvcols) 

    delete_alpha = np.arange(3, fastvcols.size, 4)
    cols = np.delete(fastvcols, delete_alpha)

    return cols    

def _get_mesh_vattr_(mesh, name=""):
    if not name in mesh.attributes and mesh != "":
        rfb_log().error("Cannot find color attribute ")
        return None
    vattr_layer = mesh.attributes[name] if name != "" \
        else mesh.attributes.active

    if vattr_layer is None:
        return None

    vcol_count = len(vattr_layer.data)
    fastvattrs = np.zeros(vcol_count * 4)
    vattr_layer.data.foreach_get("color", fastvattrs)
 
    delete_alpha = np.arange(3, fastvattrs.size, 4)
    attrs = np.delete(fastvattrs, delete_alpha)       
    
    return attrs 

def _get_mesh_vgroup_(ob, mesh, name=""):
    vgroup = ob.vertex_groups[name] if name != "" else ob.vertex_groups.active
    weights = []

    if vgroup is None:
        return None

    for v in mesh.vertices:
        if len(v.groups) == 0:
            weights.append(0.0)
        else:
            weights.extend([g.weight if g.group == vgroup.index else 0.0 for g in v.groups
                            ])

    return weights

def _get_material_ids(ob, geo):        
    fast_material_ids = np.zeros(len(geo.polygons), dtype=np.int32)
    geo.polygons.foreach_get("material_index", fast_material_ids)
    material_ids = fast_material_ids
    return material_ids

def _export_reference_pose(ob, rman_sg_mesh, rm, rixparams):
    rman__Pref = None
    rman__WPref = None
    rman__Nref = None
    rman__WNref = None

    vertex_detail = rman_sg_mesh.npoints 
    facevarying_detail = rman_sg_mesh.nverts 
    uniform_detail = rman_sg_mesh.npolys

    if rm.reference_pose:
        rp = rm.reference_pose[0]
        if rp.has_Pref:
            fastv = np.zeros(vertex_detail * 3, dtype=np.float32)
            rm.reference_pose.foreach_get("rman__Pref", fastv)
            rman__Pref = fastv
        if rp.has_WPref:
            fastv = np.zeros(vertex_detail * 3, dtype=np.float32)
            rm.reference_pose.foreach_get("rman__WPref", fastv)
            rman__WPref = fastv            

    if rm.reference_pose_normals:
        rp = rm.reference_pose_normals[0]
        num_normals = len(rm.reference_pose_normals)
        if rp.has_Nref:
            fastv = np.zeros(num_normals * 3, dtype=np.float32)
            rm.reference_pose_normals.foreach_get("rman__Nref", fastv)            
            rman__Nref = fastv
        if rp.has_WNref:
            fastv = np.zeros(num_normals * 3, dtype=np.float32)
            rm.reference_pose_normals.foreach_get("rman__WNref", fastv)            
            rman__WNref = fastv

    if rman__Pref is not None:
        if int(len(rman__Pref) / 3) == vertex_detail:
            rixparams.SetPointDetail('__Pref', rman__Pref.data, 'vertex')
        else:
            rfb_log().error("Number of Pref primvars do not match. Please re-freeze the reference position.")

    if rman__WPref is not None:
        if int(len(rman__WPref) / 3) == vertex_detail:
            rixparams.SetPointDetail('__WPref', rman__WPref.data, 'vertex')
        else:
            rfb_log().error("Number of WPref primvars do not match. Please re-freeze the reference position.")
                
    if rman__Nref is not None:
        if int(len(rman__Nref) / 3) == vertex_detail:
            rixparams.SetNormalDetail('__Nref', rman__Nref.data, 'vertex')
        elif int(len(rman__Nref) / 3) == facevarying_detail:
            rixparams.SetNormalDetail('__Nref', rman__Nref.data, 'facevarying')
        elif int(len(rman__Nref) / 3) == uniform_detail:
            rixparams.SetNormalDetail('__Nref', rman__Nref.data, 'uniform')            
        else:
            rfb_log().error("Number of Nref primvars do not match. Please re-freeze the reference position.")
        
    if rman__WNref is not None:
        if int(len(rman__WNref) /3 ) == vertex_detail:
            rixparams.SetNormalDetail('__Nref', rman__Nref.data, 'vertex')
        elif int(len(rman__WNref) /3 ) == facevarying_detail:
            rixparams.SetNormalDetail('__WNref', rman__WNref.data, 'facevarying')
        elif int(len(rman__WNref) /3 ) == uniform_detail:
            rixparams.SetNormalDetail('__WNref', rman__WNref.data, 'uniform')            
        else:
            rfb_log().error("Number of WNref primvars do not match. Please re-freeze the reference position.")
            print("%d vs %d vs %d" % (len(rman__Nref), vertex_detail, facevarying_detail))

def export_tangents(ob, geo, rixparams, uvmap="", name=""):
    # also export the tangent and bitangent vectors
    try:
        if uvmap == "":
            geo.calc_tangents(uvmap=geo.uv_layers.active.name)         
        else:
            geo.calc_tangents(uvmap=uvmap)
        loops = len(geo.loops)
        fasttangent = np.zeros(loops*3, dtype=np.float32)
        geo.loops.foreach_get('tangent', fasttangent)
        tangents = fasttangent 

        fastbitangent = np.zeros(loops*3, dtype=np.float32)
        geo.loops.foreach_get('bitangent', fastbitangent)
        bitangent = fastbitangent    
        geo.free_tangents()    

        if name == "":
            rixparams.SetVectorDetail('Tn', tangents.data, 'facevarying')
            rixparams.SetVectorDetail('Bn', bitangent.data, 'facevarying')    
        else:
            rixparams.SetVectorDetail('%s_Tn' % name, tangents.data, 'facevarying')
            rixparams.SetVectorDetail('%s_Bn' % name, bitangent.data, 'facevarying')                
    except RuntimeError as err:
        rfb_log().debug("Can't export tangent vectors: %s" % str(err))       

def _get_primvars_(ob, rman_sg_mesh, geo, rixparams):
    #rm = ob.data.renderman
    # Stange problem here : ob seems to not be in sync with the scene
    # when a geometry node is active...
    rm = ob.original.data.renderman

    facevarying_detail = rman_sg_mesh.nverts 

    if rm.export_default_uv:
        uvs = _get_mesh_uv_(geo, ob=ob)
        if uvs is not None and uvs.any():
            detail = "facevarying" if (facevarying_detail*2) == len(uvs) else "vertex"
            rixparams.SetFloatArrayDetail("st", uvs.data, 2, detail)
            if rm.export_default_tangents:
                export_tangents(ob, geo, rixparams)    

    if rm.export_default_vcol:
        vcols = _get_mesh_vcol_(geo, ob=ob)
        if vcols is not None and vcols.any():
            detail = "facevarying" if facevarying_detail == len(vcols) else "vertex"
            rixparams.SetColorDetail("Cs", vcols, detail)

    # reference pose
    if hasattr(rm, 'reference_pose'):
        _export_reference_pose(ob, rman_sg_mesh, rm, rixparams)

    output_all_primvars = getattr(rm, 'output_all_primvars', False)
    if output_all_primvars:
        # export all of the attributes
        detail_map = { facevarying_detail: 'facevarying',
                    rman_sg_mesh.npoints: 'vertex', rman_sg_mesh.npolys: 'uniform',
                    1: "constant"}
        attrs_dict = dict()
        BlAttribute.parse_attributes(attrs_dict, ob, detail_map)
        BlAttribute.set_rman_primvars(rixparams, attrs_dict)

        # vertex group
        for nm in ob.vertex_groups.keys():
            weights = _get_mesh_vgroup_(ob, geo, nm)
            if weights and len(weights) > 0:
                detail = "facevarying" if facevarying_detail == len(weights) else "vertex"
                rixparams.SetFloatDetail(nm, weights, detail)        
        
    else:
        # custom prim vars
        for p in rm.prim_vars:
            if p.data_source == 'ATTRIBUTES':
                if p.data_name in geo.attributes:
                    detail_map = { facevarying_detail: 'facevarying',
                    rman_sg_mesh.npoints: 'vertex', rman_sg_mesh.npolys: 'uniform',
                    1: 'constant'}
                    rman_attr = BlAttribute.parse_attribute(geo.attributes[p.data_name], detail_map)
                    if rman_attr:
                        if p.name != "":
                            rman_attr.rman_name = string_utils.sanitize_node_name(p.name)
                        BlAttribute.set_rman_primvar(rixparams, rman_attr)
            elif p.data_source == 'VERTEX_COLOR':
                vcols = _get_mesh_vcol_(geo, p.data_name)
                
                if vcols is not None and vcols.any():
                    detail = "facevarying" if facevarying_detail == len(vcols) else "vertex"
                    rixparams.SetColorDetail(p.name, vcols.data, detail)
                
            elif p.data_source == 'UV_TEXTURE':
                uvs = _get_mesh_uv_(geo, p.data_name)
                if uvs is not None and uvs.any():
                    detail = "facevarying" if (facevarying_detail*2) == len(uvs) else "vertex"
                    rixparams.SetFloatArrayDetail(p.name, uvs.data, 2, detail)
                    if p.export_tangents:
                        export_tangents(ob, geo, rixparams, uvmap=p.data_name, name=p.name) 

            elif p.data_source == 'VERTEX_GROUP':
                weights = _get_mesh_vgroup_(ob, geo, p.data_name)
                if weights and len(weights) > 0:
                    detail = "facevarying" if facevarying_detail == len(weights) else "vertex"
                    rixparams.SetFloatDetail(p.name, weights, detail)
            elif p.data_source == 'VERTEX_ATTR_COLOR':
                vattr = _get_mesh_vattr_(geo, p.data_name)            
                if vattr and len(vattr) > 0:
                    detail = "facevarying" if facevarying_detail == len(vattr) else "vertex"
                    rixparams.SetColorDetail(p.data_name, vattr, detail)

    rm_scene = rman_sg_mesh.rman_scene.bl_scene.renderman
    property_utils.set_primvar_bl_props(rixparams, rm, inherit_node=rm_scene)

class RmanMeshTranslator(RmanTranslator):

    def __init__(self, rman_scene):
        super().__init__(rman_scene)
        self.bl_type = 'MESH' 

    def _get_subd_tags_(self, ob, mesh, primvar):
        rm = mesh.renderman

        tags = ['interpolateboundary', 'facevaryinginterpolateboundary']
        nargs = [1, 0, 0, 1, 0, 0]
        intargs = [ int(ob.data.renderman.rman_subdivInterp),
                int(ob.data.renderman.rman_subdivFacevaryingInterp)]
        floatargs = []
        stringargs = []   

        # get creases
        edges_len = len(mesh.edges)
        creases = np.zeros(edges_len, dtype=np.float32)
        if BLENDER_41:
            if mesh.edge_creases:
                mesh.edge_creases.data.foreach_get('value', creases)
        else:
            mesh.edges.foreach_get('crease', creases)
        if (creases > 0.0).any():
            # we have edges where their crease is > 0.0
            # grab only those edges
            crease_edges = np.zeros(edges_len*2, dtype=np.int32)
            mesh.edges.foreach_get('vertices', crease_edges)
            crease_edges = np.reshape(crease_edges, (edges_len, 2))
            crease_edges = crease_edges[creases > 0.0]
            
            # squared, to match blender appareance better
            #: range 0 - 10 (infinitely sharp)
            creases = creases * creases * 10.0
            
            creases = creases[creases > 0.0]
            edges_subset_len = len(creases) 

            tags.extend(['crease'] * edges_subset_len)
            nargs.extend([2, 1, 0] * edges_subset_len)
            intargs.extend(crease_edges.flatten().tolist())
            floatargs.extend(creases.tolist())   

        primvar.SetStringArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtags, tags, len(tags))
        primvar.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtagnargs, nargs, len(nargs))
        primvar.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtagintargs, intargs, len(intargs))
        primvar.SetFloatArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtagfloatargs, floatargs, len(floatargs))
        primvar.SetStringArray(self.rman_scene.rman.Tokens.Rix.k_Ri_subdivtagstringtags, stringargs, len(stringargs))        

    def export(self, ob, db_name):
        if len(ob.data.polygons) < 1:
            return None
        
        sg_node = self.rman_scene.sg_scene.CreateGroup('')
        rman_sg_mesh = RmanSgMesh(self.rman_scene, sg_node, db_name)
        rman_sg_mesh.sg_mesh = self.rman_scene.sg_scene.CreateMesh(db_name)
        rman_sg_mesh.sg_node.AddChild(rman_sg_mesh.sg_mesh)

        if self.rman_scene.do_motion_blur:
            rman_sg_mesh.is_transforming = object_utils.is_transforming(ob)
            rman_sg_mesh.is_deforming = object_utils._is_deforming_(ob, self.rman_scene.bl_scene)

        return rman_sg_mesh

    def export_deform_sample(self, rman_sg_mesh, ob, time_sample, sg_node=None):

        mesh = None
        mesh = ob.to_mesh()
        if not sg_node:
            sg_node = rman_sg_mesh.sg_mesh
        primvar = sg_node.GetPrimVars()
        P = mesh_utils.get_mesh_points_(mesh)
        npoints = len(P)

        if rman_sg_mesh.npoints != npoints:
            primvar.SetTimes([])
            sg_node.SetPrimVars(primvar)
            rman_sg_mesh.is_transforming = False
            rman_sg_mesh.is_deforming = False
            if rman_sg_mesh.is_multi_material:
                for c in rman_sg_mesh.multi_material_children:
                    pvar = c.GetPrimVars()
                    pvar.SetTimes( [] )                               
                    c.SetPrimVars(pvar)            
            return       

        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex", time_sample)                            

        sg_node.SetPrimVars(primvar)

        if rman_sg_mesh.is_multi_material:
            for c in rman_sg_mesh.multi_material_children:
                pvar = c.GetPrimVars()
                pvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P, "vertex", time_sample)                                  
                c.SetPrimVars(pvar)

        ob.to_mesh_clear()    

    def update_primvar(self, ob, rman_sg_mesh, prop_name):
        mesh = ob.to_mesh()
        primvars = rman_sg_mesh.sg_mesh.GetPrimVars()
        if prop_name in mesh.renderman.prop_meta:
            rm = mesh.renderman
            meta = rm.prop_meta[prop_name]
            rm_scene = self.rman_scene.bl_scene.renderman
            property_utils.set_primvar_bl_prop(primvars, prop_name, meta, rm, inherit_node=rm_scene)        
        else:
            super().update_object_primvar(ob, primvars, prop_name)
        rman_sg_mesh.sg_mesh.SetPrimVars(primvars)
        ob.to_mesh_clear()

    def update(self, ob, rman_sg_mesh, input_mesh=None, sg_node=None):
        rm = ob.original.data.renderman
        mesh = input_mesh
        if not mesh:
            mesh = ob.to_mesh()
            if not mesh:
                return True

        if not sg_node:
            sg_node = rman_sg_mesh.sg_mesh

        rman_sg_mesh.is_subdiv = object_utils.is_subdmesh(ob.original)
        use_smooth_normals = getattr(rm, 'rman_smoothnormals', False)
        get_normals = (rman_sg_mesh.is_subdiv == 0 and not use_smooth_normals)
        rman_mesh = mesh_utils.get_mesh(mesh, get_normals=get_normals)
        nverts = rman_mesh.nverts
        verts = rman_mesh.verts
        P = rman_mesh.P
        N = rman_mesh.N
        
        # if this is empty continue:
        if not nverts.any():
            if not input_mesh:
                ob.to_mesh_clear()
            rman_sg_mesh.npoints = 0
            rman_sg_mesh.npolys = 0
            rman_sg_mesh.nverts = 0
            rman_sg_mesh.is_transforming = False
            rman_sg_mesh.is_deforming = False
            rman_sg_mesh.sg_node.RemoveChild(rman_sg_mesh.sg_mesh)
            return None
        
        # double check that sg_mesh has been added
        # as a child
        if rman_sg_mesh.sg_node.GetNumChildren() < 1:
            rman_sg_mesh.sg_node.AddChild(rman_sg_mesh.sg_mesh)

        npolys = rman_mesh.npolys 
        npoints = rman_mesh.npoints 
        numnverts = rman_mesh.numnverts 

        rman_sg_mesh.npoints = npoints
        rman_sg_mesh.npolys = npolys
        rman_sg_mesh.nverts = numnverts

        sg_node.Define( npolys, npoints, numnverts )
        rman_sg_mesh.is_multi_material = _is_multi_material_(ob, mesh)
            
        primvar = sg_node.GetPrimVars()
        primvar.Clear()

        if rman_sg_mesh.is_deforming and len(rman_sg_mesh.deform_motion_steps) > 1:
            super().set_primvar_times(rman_sg_mesh.deform_motion_steps, primvar)
        
        primvar.SetPointDetail(self.rman_scene.rman.Tokens.Rix.k_P, P.data, "vertex")
        _get_primvars_(ob, rman_sg_mesh, mesh, primvar)   

        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_nvertices, nverts.data, "uniform")
        primvar.SetIntegerDetail(self.rman_scene.rman.Tokens.Rix.k_Ri_vertices, verts.data, "facevarying")                  

        if rman_sg_mesh.is_subdiv:
            creases = self._get_subd_tags_(ob, mesh, primvar)
            sg_node.SetScheme(rm.rman_subdiv_scheme) 

        else:
            sg_node.SetScheme(None)

        if not rman_sg_mesh.is_subdiv:
            if N.any():
                if rman_mesh.nnormals == numnverts:
                    primvar.SetNormalDetail(self.rman_scene.rman.Tokens.Rix.k_N, N.data, "facevarying")         
                else:
                    primvar.SetNormalDetail(self.rman_scene.rman.Tokens.Rix.k_N, N.data, "uniform")         
        subdiv_scheme = getattr(rm, 'rman_subdiv_scheme', 'none')
        rman_sg_mesh.subdiv_scheme = subdiv_scheme

        super().export_object_primvars(ob, primvar)

        if rman_sg_mesh.is_multi_material:
            material_ids = _get_material_ids(ob, mesh)
            i = 1
            mat_faces_dict = _get_mats_faces_(nverts, material_ids)
            min_idx = min(mat_faces_dict.keys()) # find the minimun material index
            for mat_id, faces in mat_faces_dict.items():
                # If the face has a mat index that is higher than the number of
                # material slots, use the last material. This is what
                # Eevee/Cycles does.
                mat = None
                if mat_id >= len(ob.data.materials):
                    mat = ob.data.materials[-1]
                else:
                    mat = ob.data.materials[mat_id]
                    
                if mat:
                    sg_material = self.rman_scene.rman_materials.get(mat.original, None)

                if mat_id == min_idx:
                    primvar.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_shade_faceset, faces, len(faces))
                    if mat:
                        scenegraph_utils.set_material(sg_node, sg_material.sg_node, sg_material, mat=mat, ob=ob)
                else:                
                    sg_sub_mesh =  self.rman_scene.sg_scene.CreateMesh("%s-%d" % (rman_sg_mesh.db_name, i))
                    i += 1
                    sg_sub_mesh.Define( npolys, npoints, numnverts )                   
                    if rman_sg_mesh.is_subdiv:
                        sg_sub_mesh.SetScheme(self.rman_scene.rman.Tokens.Rix.k_catmullclark)
                    pvars = sg_sub_mesh.GetPrimVars()  
                    if rman_sg_mesh.is_deforming and len(rman_sg_mesh.deform_motion_steps) > 1:
                        super().set_primvar_times(rman_sg_mesh.deform_motion_steps, pvars)
                    pvars.Inherit(primvar)
                    pvars.SetIntegerArray(self.rman_scene.rman.Tokens.Rix.k_shade_faceset, faces, len(faces))                    
                    sg_sub_mesh.SetPrimVars(pvars)
                    if mat:
                        scenegraph_utils.set_material(sg_sub_mesh, sg_material.sg_node, sg_material, mat=mat, ob=ob)
                    sg_node.AddChild(sg_sub_mesh)
                    rman_sg_mesh.multi_material_children.append(sg_sub_mesh)
        else:
            rman_sg_mesh.multi_material_children = []

        sg_node.SetPrimVars(primvar)

        if not input_mesh:
            ob.to_mesh_clear()  

        return True    