#############################################
# THUG1 SCENE EXPORT
#############################################
import bpy
import bmesh
import struct
import mathutils
import math
from bpy.props import *
from . helpers import *
from . material import *
from bpy_extras.io_utils import ExportHelper


# METHODS
#############################################
def export_scn_sectors(output_file, operator=None):
    def w(fmt, *args):
        output_file.write(struct.pack(fmt, *args))

    bm = bmesh.new()
    p = Printer()
    out_objects = [o for o in bpy.data.objects
                   if (o.type == "MESH"
                    and getattr(o, 'thug_export_scene', True)
                    and not o.get("thug_autosplit_object_no_export_hack", False))]

    object_counter = 0
    object_amount_offset = output_file.tell()
    w("i", 0)
    for ob in out_objects:
        LOG.debug("Exporting scene object: {}".format(ob.name))
        # bpy.ops.object.mode_set(mode="OBJECT")
        original_object = ob
        original_object_name = ob.name
        is_levelobject = ob.thug_object_class == "LevelObject"
        if is_levelobject:
            lo_matrix = mathutils.Matrix.Identity(4)
            lo_matrix[0][0] = ob.scale[0]
            lo_matrix[1][1] = ob.scale[1]
            lo_matrix[2][2] = ob.scale[2]
        ob.name = "TEMP_OBJECT___"
        try:
            final_mesh = ob.to_mesh(bpy.context.scene, True, 'PREVIEW')
            temporary_object = _make_temp_obj(final_mesh)
            temporary_object.name = original_object_name
            try:
                bpy.context.scene.objects.link(temporary_object)
                temporary_object.matrix_world = ob.matrix_world

                if _need_to_flip_normals(ob):
                    _flip_normals(temporary_object)

                if (operator and
                    operator.generate_vertex_color_shading and
                    len(temporary_object.data.polygons) != 0 and
                    not ob.get("thug_this_is_autosplit_temp_object")):
                    _generate_lambert_shading(temporary_object)

                ob = temporary_object
                object_counter += 1
                final_mesh = ob.data
                
                bm.clear()
                bm.from_mesh(final_mesh)
                bmesh.ops.triangulate(bm, faces=bm.faces)
                bm.to_mesh(final_mesh)
                final_mesh.calc_normals_split()
                bm.clear()
                bm.from_mesh(final_mesh)
                
                flags = 0 if not is_levelobject else SECFLAGS_HAS_VERTEX_NORMALS
                
                tx_uv_layers = []
                tx_uv_passes = []
                # Does this object have env mapped texture passes? If so, we need to export vertex normals
                # this requirement apparently doesn't exist in THUG2
                ob_has_env_map = False
                for env_test in ob.data.materials:
                    if not hasattr(env_test, 'texture_slots'): continue
                    
                    # Collect all unique texture passes that reference a unique UV map
                    _tmp_uvs = [tex_slot for tex_slot in env_test.texture_slots if tex_slot and tex_slot.use and tex_slot.use_map_color_diffuse][:4]
                    
                    for ts in _tmp_uvs:
                        if ts.uv_layer not in tx_uv_layers:
                            tx_uv_layers.append(ts.uv_layer)
                            tx_uv_passes.append(ts)
                            
                    _tmp_passes = [tex_slot.texture for tex_slot in env_test.texture_slots if tex_slot and tex_slot.use and tex_slot.use_map_color_diffuse][:4]
                    for _tmp_tex in _tmp_passes:
                        _pprops = _tmp_tex and _tmp_tex.thug_material_pass_props
                        if _pprops and _pprops.pf_environment:
                            ob_has_env_map = True
                            break
                            
                if True or len(bm.loops.layers.uv):
                    flags |= SECFLAGS_HAS_TEXCOORDS
                if True or len(bm.loops.layers.color):
                    flags |= SECFLAGS_HAS_VERTEX_COLORS
                    #flags |= SECFLAGS_HAS_VERTEX_NORMALS
                if len(original_object.vertex_groups):
                    flags |= SECFLAGS_HAS_VERTEX_WEIGHTS
                if len(original_object.vertex_groups) or ob_has_env_map:
                    flags |= SECFLAGS_HAS_VERTEX_NORMALS

                mats_to_faces = {}
                for face in bm.faces:
                    face_list = mats_to_faces.get(face.material_index)
                    if face_list:
                        face_list.append(face)
                    else:
                        mats_to_faces[face.material_index] = [face]

                #split_verts = make_split_verts(final_mesh, bm, flags)
                
                _all_nonsplit_verts = set()
                for mat_index, mat_faces in mats_to_faces.items():
                    for face in mat_faces:
                        for vert in face.verts:
                            _all_nonsplit_verts.add(vert)
                    #nonsplit_verts = {vert for face in mat_faces for vert in face.verts}
                    
                split_verts = make_split_verts(
                    final_mesh,
                    bm,
                    flags,
                    verts=_all_nonsplit_verts)
                        
                if get_clean_name(ob).endswith("_SCN"): # This is from an imported level, so drop the _SCN part
                    w("I", crc_from_string(bytes(get_clean_name(ob)[:-4], 'ascii')))  # checksum
                else:
                    w("I", crc_from_string(bytes(get_clean_name(ob), 'ascii')))  # checksum
                w("i", -1)  # bone index
                w("I", flags)  # flags
                w("I", len([fs for fs in mats_to_faces.values() if fs]))  # number of meshes
                
                if is_levelobject:
                    # bbox = get_bbox2(final_mesh.vertices, mathutils.Matrix.Identity(4))
                    bbox = get_bbox2(final_mesh.vertices, lo_matrix)
                else:
                    bbox = get_bbox2(final_mesh.vertices, ob.matrix_world)
                    
                w("6f",
                    bbox[0][0], bbox[0][1], bbox[0][2],
                    bbox[1][0], bbox[1][1], bbox[1][2])  # bbox
                bsphere = get_sphere_from_bbox(bbox)
                w("4f", *bsphere)  # bounding sphere

                w("i", len(split_verts))
                w("i", 0) # vertex data stride, this seems to be ignored

                for v in split_verts.keys():
                    w("3f", *to_thug_coords(ob.matrix_world * v.co))

                if flags & SECFLAGS_HAS_VERTEX_NORMALS:
                    if flags & SECFLAGS_HAS_VERTEX_WEIGHTS:
                    # Apparently, normals are supposed to be packed in weighted mesh
                    # but for some reason, this never seems to be the case!
                        for v in split_verts.keys():
                            w("3f", *to_thug_coords_ns(v.normal))
                    else:
                        for v in split_verts.keys():
                            w("3f", *to_thug_coords_ns(v.normal))
                        
                # Let me know if this works!
                if flags & SECFLAGS_HAS_VERTEX_WEIGHTS:
                    print("Exporting vertex weights...")
                    for v in split_verts.keys():
                        packed_weights = (
                            (int(v.weights[0][1] * 1023.0) & 0x7FF),
                            ((int(v.weights[1][1] * 1023.0) & 0x7FF) << 11),
                            ((int(v.weights[2][1] * 511.0) & 0x3FF) << 22))
                        packed_weights = packed_weights[0] | packed_weights[1] | packed_weights[2]
                        w("I", packed_weights)
                    
                    print("Exporting vertex bone indices...")
                    for v in split_verts.keys():
                        w("H", int(original_object.vertex_groups[v.weights[0][0]].name))
                        w("H", int(original_object.vertex_groups[v.weights[1][0]].name))
                        w("H", int(original_object.vertex_groups[v.weights[2][0]].name))
                        w("H", int(original_object.vertex_groups[v.weights[3][0]].name))
                        #for group, weight in v.weights:
                        #    #print("Bone index: " + str(int(original_object.vertex_groups[group].name) * 3))
                            #w("H", int(original_object.vertex_groups[group].name) * 3)
                        
                    print("Done...")
                    
                if len(ob.data.materials) > 0:
                    passes = tx_uv_passes
                    #passes = [tex_slot for tex_slot in ob.active_material.texture_slots if tex_slot and tex_slot.use][:4]
                else:
                    passes = []
                w("i", (len(passes) or 1) if flags & SECFLAGS_HAS_TEXCOORDS else 0)
                if flags & SECFLAGS_HAS_TEXCOORDS:
                    for v in split_verts.keys():
                        for tex_slot in passes:
                            uv_index = 0
                            if tex_slot.uv_layer:
                                uv_index = get_index(
                                    bm.loops.layers.uv.values(),
                                    tex_slot.uv_layer,
                                    lambda layer: layer.name)
                            w("2f", *v.uvs[uv_index])
                        if not passes:
                            w("2f", *v.uvs[0])
                        # w("2f", *(-v.uv))

                VC_MULT = 256 if operator.use_vc_hack else 128
                FULL_WHITE = (1.0, 1.0, 1.0, 1.0)
                if flags & SECFLAGS_HAS_VERTEX_COLORS:
                    for v in split_verts.keys():
                        r, g, b, a = v.vc or FULL_WHITE
                        a = (int(a * VC_MULT) & 0xff) << 24
                        r = (int(r * VC_MULT) & 0xff) << 16
                        g = (int(g * VC_MULT) & 0xff) << 8
                        b = (int(b * VC_MULT) & 0xff) << 0
                        w("I", a | r | g | b)

                for mat_index, mat_faces in mats_to_faces.items():
                    if len(mat_faces) == 0: continue
                    # TODO fix this
                    # should recalc bbox for this mesh
                    w("4f", *bsphere)
                    w("6f",
                        bbox[0][0], bbox[0][1], bbox[0][2],
                        bbox[1][0], bbox[1][1], bbox[1][2])  # bbox
                    w("I", 0)  # flags
                    the_material = len(ob.material_slots) and ob.material_slots[mat_index].material
                    if not the_material:
                        the_material = bpy.data.materials["_THUG_DEFAULT_MATERIAL_"]
                    mat_checksum = crc_from_string(bytes(the_material.name, 'ascii'))
                    w("L", mat_checksum)  # material checksum
                    w("I", 1)  # num of index lod levels

                    strip = get_triangle_strip(final_mesh, bm, mat_faces, split_verts, flags) #(bm) #(ob)
                    w("i", len(strip))
                    w(str(len(strip)) + "H", *strip)
            finally:
                if bpy.context.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.context.scene.objects.unlink(temporary_object)
                bpy.data.objects.remove(temporary_object)
                bpy.data.meshes.remove(final_mesh)
        finally:
            original_object.name = original_object_name
        
    _saved_offset = output_file.tell()
    output_file.seek(object_amount_offset)
    w("i", object_counter)
    output_file.seek(_saved_offset)
    bm.free()




# OPERATORS
#############################################
class SceneToTHUGFiles(bpy.types.Operator): #, ExportHelper):
    bl_idname = "export.scene_to_thug_xbx"
    bl_label = "Scene to THUG1 level files"
    # bl_options = {'REGISTER', 'UNDO'}

    def report(self, category, message):
        LOG.debug("OP: {}: {}".format(category, message))
        super().report(category, message)

    filename = StringProperty(name="File Name")
    directory = StringProperty(name="Directory")

    generate_vertex_color_shading = BoolProperty(name="Generate vertex color shading", default=False)
    use_vc_hack = BoolProperty(name="Vertex color hack"
        , description = "Doubles intensity of vertex colours. Enable if working with an imported scene that appears too dark in game."
        , default=False)
    autosplit_everything = BoolProperty(name="Autosplit All"
        , description = "Applies the autosplit setting to all objects in the scene, with default settings."
        , default=False)
    is_park_editor = BoolProperty(
        name="Is Park Editor",
        description="Use this option when exporting a park editor dictionary.",
        default=False)
    generate_tex_file = BoolProperty(
        name="Generate a .tex file",
        default=True)
    generate_scn_file = BoolProperty(
        name="Generate a .scn file",
        default=True)
    pack_scn = BoolProperty(
        name="Pack the scene .pre",
        default=True)
    generate_col_file = BoolProperty(
        name="Generate a .col file",
        default=True)
    pack_col = BoolProperty(
        name="Pack the col .pre",
        default=True)
    generate_scripts_files = BoolProperty(
        name="Generate scripts",
        default=True)
    pack_scripts = BoolProperty(
        name="Pack the scripts .pre",
        default=True)

#    filepath = StringProperty()
    skybox_name = StringProperty(name="Skybox name", default="THUG_Sky")
    export_scale = FloatProperty(name="Export scale", default=1)
    mipmap_offset = IntProperty(
        name="Mipmap offset",
        description="Offsets generation of mipmaps (default is 0). For example, setting this to 1 will make the base texture 1/4 the size. Use when working with very large textures.",
        min=0, max=4, default=0)

    def execute(self, context):
        return do_export(self, context, "THUG1")

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        wm.fileselect_add(self)

        return {'RUNNING_MODAL'}
        
#----------------------------------------------------------------------------------
class SceneToTHUGModel(bpy.types.Operator): #, ExportHelper):
    bl_idname = "export.scene_to_thug_model"
    bl_label = "Scene to THUG1 model"
    # bl_options = {'REGISTER', 'UNDO'}

    def report(self, category, message):
        LOG.debug("OP: {}: {}".format(category, message))
        super().report(category, message)

    filename = StringProperty(name="File Name")
    directory = StringProperty(name="Directory")

    generate_vertex_color_shading = BoolProperty(name="Generate vertex color shading", default=True)
    is_park_editor = BoolProperty(name="Is Park Editor", default=False, options={'HIDDEN'})
    use_vc_hack = BoolProperty(name="Vertex color hack"
        , description = "Doubles intensity of vertex colours. Enable if working with an imported scene that appears too dark in game."
        , default=False)
    autosplit_everything = BoolProperty(name="Autosplit All"
        , description = "Applies the autosplit setting to all objects in the scene, with default settings."
        , default=False)
    generate_scripts_files = BoolProperty(
        name="Generate scripts",
        default=True)
    export_scale = FloatProperty(name="Export scale", default=1)
    mipmap_offset = IntProperty(
        name="Mipmap offset",
        description="Offsets generation of mipmaps (default is 0). For example, setting this to 1 will make the base texture 1/4 the size. Use when working with very large textures.",
        min=0, max=4, default=0)
        
    def execute(self, context):
        return do_export_model(self, context, "THUG1")

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        wm.fileselect_add(self)

        return {'RUNNING_MODAL'}