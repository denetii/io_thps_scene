#############################################
# THPS4 SCENE/COL/MTL EXPORT
#############################################
import bpy
import bmesh
from bpy.props import *
from bpy_extras.io_utils import ExportHelper
import struct
import mathutils
import math
from . import helpers
from . helpers import *
from . material import *
from . prefs import *
from . autosplit import *

# METHODS
#############################################
def _ensure_default_material_exists():
    if "_THUG_DEFAULT_MATERIAL_" in bpy.data.materials:
        return

    default_mat = bpy.data.materials.new(name="_THUG_DEFAULT_MATERIAL_")

    if "_THUG_DEFAULT_MATERIAL_TEXTURE_" not in bpy.data.textures:
        texture = bpy.data.textures.new("_THUG_DEFAULT_MATERIAL_TEXTURE_", "NONE")
        texture.thug_material_pass_props.color = (0.5, 0.5, 0.5)

    tex_slot = default_mat.th_texture_slots.add()
    tex_slot.texture = bpy.data.textures["_THUG_DEFAULT_MATERIAL_TEXTURE_"]
    
def export_scn_sectors_th4(output_file, operator=None, is_model=False):
    def w(fmt, *args):
        output_file.write(struct.pack(fmt, *args))

    depsgraph = bpy.context.evaluated_depsgraph_get()
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

        try:
            is_levelobject = ob.thug_object_class == "LevelObject"
            if is_levelobject == False and ob.name.endswith("_SCN"):
                # If using separate collision/scene mesh, check the collision mesh
                if bpy.data.objects.get(ob.name[:-4]) and bpy.data.objects.get(ob.name[:-4]).thug_object_class == "LevelObject":
                    is_levelobject = True

            if is_levelobject:
                lo_matrix = mathutils.Matrix.Identity(4)
                lo_matrix[0][0] = ob.scale[0]
                lo_matrix[1][1] = ob.scale[1]
                lo_matrix[2][2] = ob.scale[2]

            final_mesh = ob.data

            object_counter += 1

            bm.clear()
            bm.from_object(ob, depsgraph)
            bmesh.ops.triangulate(bm, faces=bm.faces)
            bm.to_mesh(final_mesh)
            final_mesh.calc_normals_split()

            flags = 0 if not is_levelobject else SECFLAGS_HAS_VERTEX_NORMALS
                
            # Check texture passes for:
            # - Environment mapped textures (normals need to be exported)
            # - Valid UV map assignments (must be in the correct order!)
            need_vertex_normals = False
            for env_test in ob.data.materials:
                if hasattr(env_test, 'thug_material_props') and env_test.thug_material_props.specular_power > 0.0:
                    need_vertex_normals = True
                        
                # Always export normals when using Underground+ materials/shaders
                if hasattr(env_test, 'thug_material_props') and env_test.thug_material_props.use_new_mats:
                    need_vertex_normals = True
                    
                if not hasattr(env_test, 'th_texture_slots'): continue
                _tmp_passes = [tex_slot for tex_slot in env_test.th_texture_slots if tex_slot][:4]
                for _tmp_tex in _tmp_passes:
                    _pprops = _tmp_tex.texture and _tmp_tex.texture.thug_material_pass_props
                    if _pprops and (_pprops.pf_environment or _pprops.pf_bump or _pprops.pf_water or _pprops.blend_mode == 'vBLEND_MODE_GLOSS_MAP'):
                        need_vertex_normals = True
                        #break
                
            if operator.always_export_normals:
                need_vertex_normals = True
            if True or len(bm.loops.layers.uv):
                flags |= SECFLAGS_HAS_TEXCOORDS
            if True or len(bm.loops.layers.color):
                flags |= SECFLAGS_HAS_VERTEX_COLORS
            if len(ob.vertex_groups) and is_model == True:
                flags |= SECFLAGS_HAS_VERTEX_WEIGHTS
            if len(ob.vertex_groups) or need_vertex_normals:
                flags |= SECFLAGS_HAS_VERTEX_NORMALS
            if ob.thug_is_shadow_volume:
                print("EXPORTING SHADOW VOLUME!")
                flags |= SECFLAGS_SHADOW_VOLUME
            #if final_mesh.thug_billboard_props.is_billboard:
            #    flags |= SECFLAGS_BILLBOARD_PRESENT
            #    flags &= ~SECFLAGS_HAS_VERTEX_NORMALS

            mats_to_faces = {}
            for face in bm.faces:
                face_list = mats_to_faces.get(face.material_index)
                if face_list:
                    face_list.append(face)
                else:
                    mats_to_faces[face.material_index] = [face]
                    
            split_verts = make_split_verts(final_mesh, bm, flags)
                       
            clean_name = get_clean_name(ob)
            if is_hex_string(clean_name):
                w("I", int(clean_name, 0))  # checksum
            else:
                w("I", crc_from_string(bytes(clean_name, 'ascii')))  # checksum
               
            w("i", -1)  # bone index
            w("I", flags)  # flags
            w("I", len([fs for fs in mats_to_faces.values() if fs]))  # number of meshes
                
            if is_levelobject:
                # bbox = get_bbox2(final_mesh.vertices, mathutils.Matrix.Identity(4))
                bbox = get_bbox2(final_mesh.vertices, lo_matrix)
            else:
                bbox = get_bbox2(final_mesh.vertices, ob.matrix_world, operator.is_park_editor)
                    
            w("6f",
                bbox[0][0], bbox[0][1], bbox[0][2],
                bbox[1][0], bbox[1][1], bbox[1][2])  # bbox
            bsphere = get_sphere_from_bbox(bbox)
            w("4f", *bsphere)  # bounding sphere

            # Export billboard data - testing
            #if flags & SECFLAGS_BILLBOARD_PRESENT:
            #    w("I", int(BILLBOARD_TYPES[ob.data.thug_billboard_props.type])) # billboard type
            #    
            #    # billboard pivot pos
            #    if ob.data.thug_billboard_props.custom_pos == True:
            #        w("3f", *to_thug_coords_ns(mathutils.Vector(ob.data.thug_billboard_props.pivot_origin))) 
            #        w("3f", *to_thug_coords_ns(mathutils.Vector(ob.data.thug_billboard_props.pivot_pos))) 
            #    else:
            #        w("3f", *mathutils.Vector( [ bsphere[0], bsphere[1], bsphere[2] ] ))
            #        w("3f", *mathutils.Vector( [ bsphere[0], bsphere[1], -bsphere[2] ] ))
            #    w("3f", *to_thug_coords_ns(mathutils.Vector(ob.data.thug_billboard_props.pivot_axis))) # billboard pivot axis
                    
            w("i", len(split_verts))
            w("i", 0) # vertex data stride, this seems to be ignored

            for v in split_verts.keys():
                if is_levelobject:
                    w("3f", *to_thug_coords(lo_matrix @ v.co))
                else:
                    w("3f", *to_thug_coords(ob.matrix_world @ v.co))

            if flags & SECFLAGS_HAS_VERTEX_NORMALS:
                if flags & SECFLAGS_HAS_VERTEX_WEIGHTS:
                    for v in split_verts.keys():
                        w("3f", *to_thug_coords_ns(v.normal))
                else:
                    for v in split_verts.keys():
                        w("3f", *to_thug_coords_ns(v.normal))
                        
            # Normals are never packed in THPS4 (I think)
            if flags & SECFLAGS_HAS_VERTEX_WEIGHTS:
                print("Exporting vertex weights...")
                for v in split_verts.keys():
                    weights = [v.weights[0][1], v.weights[1][1], v.weights[2][1], v.weights[3][1] ]
                    w("4f", *weights)
                    
                print("Exporting vertex bone indices...")
                for v in split_verts.keys():
                    w("H", int(ob.vertex_groups[v.weights[0][0]].name))
                    w("H", int(ob.vertex_groups[v.weights[1][0]].name))
                    w("H", int(ob.vertex_groups[v.weights[2][0]].name))
                    w("H", int(ob.vertex_groups[v.weights[3][0]].name))
                        
                print("Done...?")
                    
            if flags & SECFLAGS_HAS_TEXCOORDS:
                uv_total = 0
                for v in split_verts.keys():
                    if len(v.uvs) > uv_total:
                        uv_total = len(v.uvs)
                            
                w("i", (uv_total or 1) if flags & SECFLAGS_HAS_TEXCOORDS else 0)
                for v in split_verts.keys():
                    for i in range(0, uv_total):
                        w("2f", *v.uvs[i])

            VC_MULT = 255 if operator.use_vc_hack else 255
            FULL_WHITE = (1.0, 1.0, 1.0, 1.0)
            HALF_WHITE = (0.5, 0.5, 0.5, 0.5)
            if flags & SECFLAGS_HAS_VERTEX_COLORS:
                for v in split_verts.keys():
                    r, g, b, a = v.vc or FULL_WHITE
                    if is_levelobject:
                        r, g, b, a = HALF_WHITE
                    a = (int(a * 127) & 0xff) << 24
                    r = (int(r * VC_MULT) & 0xff) << 16
                    g = (int(g * VC_MULT) & 0xff) << 8
                    b = (int(b * VC_MULT) & 0xff) << 0
                    w("I", a | r | g | b)

            for mat_index, mat_faces in mats_to_faces.items():
                if len(mat_faces) == 0: continue
                # TODO fix this
                # should recalc bbox for this mesh
                #w("4f", *bsphere)
                #w("6f",
                #    bbox[0][0], bbox[0][1], bbox[0][2],
                #    bbox[1][0], bbox[1][1], bbox[1][2])  # bbox
                the_material = len(ob.material_slots) and ob.material_slots[mat_index].material
                if not the_material:
                    the_material = bpy.data.materials["_THUG_DEFAULT_MATERIAL_"]
                if is_hex_string(the_material.name):
                    mat_checksum = int(the_material.name, 0)
                else:
                    mat_checksum = crc_from_string(bytes(the_material.name, 'ascii'))
                    
                # Determine if we need to set any mesh flags
                mesh_flags = 0
                if the_material.thug_material_props.no_skater_shadow or ob.thug_no_skater_shadow:
                    mesh_flags |= 0x400
                w("I", mesh_flags)  # mesh flags
                w("L", mat_checksum)  # material checksum
                #w("I", 1)  # num of index lod levels

                strip = get_triangle_strip(final_mesh, bm, mat_faces, split_verts, flags) #(bm) #(ob)
                w("i", len(strip))
                w(str(len(strip)) + "H", *strip)

        except Exception as ex:
            raise ExportError("Failed to export scene object {}: {}".format(ob.name, str(ex))).with_traceback(ex.__traceback__)

    _saved_offset = output_file.tell()
    output_file.seek(object_amount_offset)
    w("i", object_counter)
    output_file.seek(_saved_offset)
    bm.free()

    
def export_materials_th4(output_file, target_game, operator=None, is_model=False):
    def w(fmt, *args):
        output_file.write(struct.pack(fmt, *args))

    # out_objects = [o for o in bpy.data.objects if o.type == "MESH"]
    # out_materials = {o.active_material for o in out_objects if o.active_material}

    _ensure_default_material_exists()

    out_materials = bpy.data.materials[:]

    num_materials = len(out_materials)
    w("I", num_materials)
    for m in out_materials:
        LOG.debug("writing material: {}".format(m.name))
        mprops = m.thug_material_props
        
        #denetii - only include texture slots that affect the diffuse color in the Blender material
        passes = [tex_slot.texture for tex_slot in m.th_texture_slots if tex_slot]
        if len(passes) > 4:
            if operator:
                operator.report(
                    {"WARNING"},
                    "Material {} has more than 4 passes (enabled texture slots). Using only the first 4.".format(m.name))
            passes = passes[:4]
        if not passes and m.name != "_THUG_DEFAULT_MATERIAL_":
            if operator:
                if not m.name.startswith('io_thps_scene_'):
                    operator.report({"WARNING"}, "Material {} has no passes (enabled texture slots). Using it's diffuse color.".format(m.name))
                passes = [None]

        if is_hex_string(m.name):
            checksum = int(m.name, 0)
        else:
            checksum = crc_from_string(bytes(m.name, 'ascii'))
        
        w("I", checksum)  # material checksum
        #w("I", checksum)  # material name checksum
        w("I", len(passes) or 1)  # material passes
        w("I", mprops.alpha_cutoff)  # alpha cutoff (actually an unsigned byte)
        w("?", mprops.sorted)  # sorted?
        w("f", mprops.draw_order)  # draw order
        w("?", mprops.single_sided)  # single sided
        #w("?", mprops.no_backface_culling)  # no backface culling
        #w("i", mprops.z_bias)  # z-bias

        #grassify = False
        w("?", False)  # grassify
        if False:  # if grassify
            print("EXPORTING GRASS MATERIAL!")
            w("f", mprops.grass_height)  # grass height
            w("i", mprops.grass_layers)  # grass layers

        #w("f", mprops.specular_power)  # specular power
        #if mprops.specular_power > 0.0:
        #    w("3f", *mprops.specular_color)  # specular color

        # using_default_texture = not passes
        
        for texture in passes:
            pprops = texture and texture.thug_material_pass_props
            tex_checksum = 0
            if texture and hasattr(texture, 'image') and texture.image:
                if is_hex_string(texture.image.name):
                    tex_checksum = int(texture.image.name, 0)
                else:
                    tex_checksum = crc_from_string(bytes(texture.image.name, 'ascii'))

            w("I", tex_checksum)  # texture checksum
            pass_flags = 0 # MATFLAG_SMOOTH
            if tex_checksum and pprops.pf_textured:
                pass_flags |= MATFLAG_TEXTURED
            if pprops and pprops.has_uv_wibbles:
                pass_flags |= MATFLAG_UV_WIBBLE
            if (pprops and
                pprops.has_animated_texture and
                len(pprops.animated_texture.keyframes)):
                pass_flags |= MATFLAG_PASS_TEXTURE_ANIMATES
            if pprops and pprops.pf_transparent:
                pass_flags |= MATFLAG_TRANSPARENT
            if pprops and pprops.ignore_vertex_alpha:
                pass_flags |= MATFLAG_PASS_IGNORE_VERTEX_ALPHA
            if pprops and pprops.pf_decal:
                pass_flags |= MATFLAG_DECAL
            if pprops and pprops.pf_smooth:
                pass_flags |= MATFLAG_SMOOTH
            if pprops and pprops.pf_environment:
                pass_flags |= MATFLAG_ENVIRONMENT
            if pprops and pprops.pf_bump:
                print("EXPORTING BUMP MAP TEXTURE!")
                #pass_flags |= MATFLAG_BUMP_SIGNED_TEXTURE
                pass_flags |= MATFLAG_NORMAL_TEST
                #pass_flags |= MATFLAG_BUMP_LOAD_MATRIX
            if pprops and pprops.pf_water:
                print("EXPORTING WATER TEXTURE!")
                pass_flags |= MATFLAG_WATER_EFFECT
                
            w("I", pass_flags)  # flags # 4132
            w("?", True)  # has color flag; seems to be ignored
            pass_color = [pprops.color[0],pprops.color[1],pprops.color[2]] if pprops else [m.diffuse_color[0],m.diffuse_color[1],m.diffuse_color[2]]
            w("3f",  *(pass_color))  # color

            # alpha register values, first u32 - a BLEND_MODE, second u32 - fixed alpha (clipped to u8)
            # w("Q", 5)
            w("I", globals()[pprops.blend_mode] if pprops else vBLEND_MODE_DIFFUSE)
            w("I", pprops.blend_fixed_alpha if pprops else 0)

            w("I", 0 if (not pprops) or pprops.u_addressing == "Repeat" else 1)  # u adressing (wrap, clamp, etc)
            w("I", 0 if (not pprops) or pprops.v_addressing == "Repeat" else 1)  # v adressing
            #w("2f", *(pprops.envmap_multiples if pprops else (3.0, 3.0)))  # envmap multiples
            w("I", 65540)  # filtering mode

            ambient_rgb = [128.0, 128.0, 128.0]
            diffuse_rgb = [128.0, 128.0, 128.0]
            specular_rgb = [128.0, 128.0, 128.0]
            w("3f", *ambient_rgb)
            w("3f", *diffuse_rgb)
            w("3f", *specular_rgb)
            
            # uv wibbles
            if pprops and pass_flags & MATFLAG_UV_WIBBLE:
                w("2f", *pprops.uv_wibbles.uv_velocity)
                w("2f", *pprops.uv_wibbles.uv_frequency)
                w("2f", *pprops.uv_wibbles.uv_amplitude)
                w("2f", *pprops.uv_wibbles.uv_phase)

            # vertex color wibbles

            # anims
            if pass_flags & MATFLAG_PASS_TEXTURE_ANIMATES:
                at = pprops.animated_texture
                w("i", len(at.keyframes))
                w("i", at.period)
                w("i", at.iterations)
                w("i", at.phase)
                for keyframe in at.keyframes:
                    w("I", keyframe.time)
                    w("I", crc_from_string(bytes(keyframe.image, 'ascii')))

            w("I", 1)  # MMAG
            w("I", 4)  # MMIN
            w("f", -8.0)  # K
            w("f", -8.0)  # L



