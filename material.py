#############################################
# THUG1/2 MATERIAL IMPORT/CONFIGURE/EXPORT
#############################################
import bpy
import struct
import mathutils
import math
import os, sys
from bpy.props import *
from . constants import *
from . helpers import *
from . tex import *

# METHODS
#############################################
def _ensure_default_material_exists():
    if "_THUG_DEFAULT_MATERIAL_" in bpy.data.materials:
        return

    default_mat = bpy.data.materials.new(name="_THUG_DEFAULT_MATERIAL_")

    if "_THUG_DEFAULT_MATERIAL_TEXTURE_" not in bpy.data.textures:
        texture = bpy.data.textures.new("_THUG_DEFAULT_MATERIAL_TEXTURE_", "NONE")
        texture.thug_material_pass_props.color = (0.5, 0.5, 0.5)

    tex_slot = default_mat.texture_slots.add()
    tex_slot.texture = bpy.data.textures["_THUG_DEFAULT_MATERIAL_TEXTURE_"]

def _thug_material_pass_props_color_updated(self, context):
    from bl_ui.properties_material import active_node_mat
    if not context or not context.object:
        return
    mat = context.object.active_material
    if not mat:
        return
    idblock = active_node_mat(mat)
    r, g, b = self.color
    idblock.active_texture.factor_red = r * 2
    idblock.active_texture.factor_green = g * 2
    idblock.active_texture.factor_blue = b * 2

def rename_imported_materials():
    for mat in bpy.data.materials:
        if "thug_mat_name_checksum" in mat and mat["thug_mat_name_checksum"] != "":
            mat.name = mat["thug_mat_name_checksum"]

def read_materials(reader, printer, num_materials, directory, operator, output_file=None, texture_map=None, texture_prefix=None):
    import os
    r = reader
    p = printer

    for i in range(num_materials):
        p("material {}", i)
        mat_checksum = p("  material checksum: {}", hex(r.u32()))
        mat_name_checksum = p("  material name checksum: {}", hex(r.u32()))
        blender_mat = bpy.data.materials.new(str(mat_checksum))
        ps = blender_mat.thug_material_props
        blender_mat["thug_mat_name_checksum"] = mat_name_checksum

        num_passes = p("  material passes: {}", r.u32())
        # MATERIAL_PASSES[mat_name_checksum] = num_passes
        ps.alpha_cutoff = p("  alpha cutoff: {}", r.u32() % 256)
        ps.sorted = p("  sorted: {}", r.bool())
        ps.draw_order = p("  draw order: {}", r.f32())
        ps.single_sided = p("  single_sided: {}", r.bool())
        ps.no_backface_culling = p("  no backface culling: {}", r.bool())
        ps.z_bias = p("  z bias: {}", r.i32())

        ps.grassify = p("  grassify: {}", r.bool())
        if ps.grassify:
            ps.grass_height = p("  grass height: {}", r.f32())
            ps.grass_layers = p("  grass layers: {}", r.i32())

        ps.specular_power = p("  specular power: {}", r.f32())
        if ps.specular_power > 0.0:
            ps.specular_color = p("  specular color: {}", r.read("3f"))

        blender_mat.use_transparency = True
        blender_mat.diffuse_color = (1, 1, 1)
        blender_mat.diffuse_intensity = 1
        blender_mat.specular_intensity = 0
        blender_mat.alpha = 0

        for j in range(num_passes):
            blender_tex = bpy.data.textures.new("{}/{}".format(mat_name_checksum, j), "IMAGE")
            tex_slot = blender_mat.texture_slots.add()
            tex_slot.texture = blender_tex
            pps = blender_tex.thug_material_pass_props
            p("  pass #{}", j)
            tex_checksum = p("    pass texture checksum: {}", r.u32())
            actual_tex_checksum = hex(tex_checksum)
            image_name = str(actual_tex_checksum) #+ ".png"
            blender_tex.image = bpy.data.images.get(image_name)
            full_path = os.path.join(directory, image_name)
            full_path2 = os.path.join(directory, str("tex\\{:08x}.tga".format(tex_checksum)))
            full_path3 = os.path.join(directory, str("tex\\{:08x}.png".format(tex_checksum)))
            if not blender_tex.image:
                if os.path.exists(full_path):
                    blender_tex.image = bpy.data.images.load(full_path)
                elif os.path.exists(full_path2):
                    blender_tex.image = bpy.data.images.load(full_path2)
                elif os.path.exists(full_path3):
                    blender_tex.image = bpy.data.images.load(full_path3)
                #else:
                #    blender_tex.image = bpy.data.images.new(image_name)
            tex_slot.uv_layer = str(j)

            if False and output_file and (True or texture_map) and j == 0:
                """
                output_file.write("map_Kd {}.tex_{}.tga\n".format(
                    texture_prefix,
                    texture_map.get(tex_checksum, 0)))
                """
                output_file.write("map_Kd {}.tga\n".format(tex_checksum))
            pass_flags = p("    pass material flags: {}", r.u32())
            p("    pass has color: {}", r.bool())
            pps.color = p("    pass color: {}", r.read("3f"))
            # p("    pass alpha register: {}", r.u64())
            pps.blend_mode = BLEND_MODES[r.u32()]
            pps.blend_fixed_alpha = r.u32() & 0xFF

            if j == 0:
                tex_slot.use_map_alpha = True

            tex_slot.blend_type = {
                "vBLEND_MODE_ADD": "ADD",
                "vBLEND_MODE_ADD_FIXED": "ADD",
                "vBLEND_MODE_SUBTRACT": "SUBTRACT",
                "vBLEND_MODE_SUB_FIXED": "SUBTRACT",
                "vBLEND_MODE_BRIGHTEN": "LIGHTEN",
                "vBLEND_MODE_BRIGHTEN_FIXED": "LIGHTEN",
            }.get(pps.blend_mode, "MIX")

            pps.u_addressing = "Repeat" if p("    pass u addressing: {}", r.u32()) == 0 else "Clamp"
            pps.v_addressing = "Repeat" if p("    pass v addressing: {}", r.u32()) == 0 else "Clamp"

            if blender_tex.image:
                    blender_tex.image.use_clamp_x = pps.u_addressing == "Clamp"
                    blender_tex.image.use_clamp_y = pps.v_addressing == "Clamp"

            pps.envmap_multiples = p("    pass envmap uv tiling multiples: {}", r.read("2f"))
            pps.filtering_mode = r.u32()
            p("    pass filtering mode: {}", pps.filtering_mode)
            pps.test_passes = pass_flags

            if pass_flags & MATFLAG_TEXTURED:
                pps.pf_textured = True
            if pass_flags & MATFLAG_TRANSPARENT:
                pps.pf_transparent = True
            else:
                pps.pf_transparent = False
            if pass_flags & MATFLAG_ENVIRONMENT:
                pps.pf_environment = True
            if pass_flags & MATFLAG_DECAL:
                pps.pf_decal = True
            if pass_flags & MATFLAG_SMOOTH:
                pps.pf_smooth = True
                
            if pass_flags & MATFLAG_PASS_IGNORE_VERTEX_ALPHA:
                pps.ignore_vertex_alpha = True

            if pass_flags & MATFLAG_UV_WIBBLE:
                p("    pass has uv wibble!", None)
                pps.has_uv_wibbles = True
                uvs = pps.uv_wibbles
                uvs.uv_velocity = r.read("2f")
                uvs.uv_frequency = r.read("2f")
                uvs.uv_amplitude = r.read("2f")
                uvs.uv_phase = r.read("2f")

            if j == 0 and pass_flags & MATFLAG_VC_WIBBLE:
                p("    pass has vc wibble!", None)
                for k in range(r.u32()):
                    num_keys = r.u32()
                    r.i32()
                    r.read(str(num_keys * 2) + "i") # sVCWibbleKeyframe

            if pass_flags & MATFLAG_PASS_TEXTURE_ANIMATES:
                p("    pass texture animates!", None)
                pps.has_animated_texture = True
                at = pps.animated_texture
                num_keyframes = r.i32()
                at.period = r.i32()
                at.iterations = r.i32()
                at.phase = r.i32()

                for k in range(num_keyframes):
                    atkf = at.keyframes.add()
                    atkf.time = r.u32()
                    atkf.image = hex(r.u32())

            if tex_checksum:  # mipmap info
                p("    mmag: {}", r.u32())
                p("    mmin: {}", r.u32())
                p("    k: {}", r.f32())
                p("    l: {}", r.f32())
            else:
                r.read("4I")


def export_ugplus_material(m, output_file, target_game, operator=None):
    def w(fmt, *args):
        output_file.write(struct.pack(fmt, *args))
    
    mprops = m.thug_material_props
    if is_hex_string(m.name):
        checksum = int(m.name, 0)
    else:
        checksum = crc_from_string(bytes(m.name, 'ascii'))
    
    w("I", checksum)  # material checksum
    w("I", checksum)  # material name checksum
    w("I", 4)  # material passes
    w("I", mprops.alpha_cutoff)  # alpha cutoff (actually an unsigned byte)
    w("?", mprops.sorted)  # sorted?
    w("f", mprops.draw_order)  # draw order
    w("?", mprops.single_sided)  # single sided
    w("?", mprops.no_backface_culling)  # no backface culling
    w("i", mprops.z_bias)  # z-bias

    #grassify = False
    w("?", mprops.grassify)  # grassify
    if mprops.grassify:  # if grassify
        print("EXPORTING GRASS MATERIAL!")
        w("f", mprops.grass_height)  # grass height
        w("i", mprops.grass_layers)  # grass layers

    shader_id = -5.40 # PBR
    if mprops.ugplus_shader == 'Water':
        shader_id = -1.08
    elif mprops.ugplus_shader == 'Skybox':
        shader_id = -8.15
    w("f", shader_id)  # specular power (used to mark the shader ID for the new shaders)

    export_textures = []
    # Now we export the textures in a specific order, depending on the shader
    if mprops.ugplus_shader == 'PBR':
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_normal, 'flags': MATFLAG_BUMP_SIGNED_TEXTURE })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_reflection, 'flags': MATFLAG_BUMP_LOAD_MATRIX })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_diffuse, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_detail, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_lightmap, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_rainmask, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_snowmask, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_snow, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_specular, 'flags': 0 })
        
    elif mprops.ugplus_shader == 'Skybox':
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_diffuse, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_diffuse_evening, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_diffuse_night, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_diffuse_morning, 'flags': 0 })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_diffuse_cloud, 'flags': 0 })
        
    elif mprops.ugplus_shader == 'Water':
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_fallback, 'flags': MATFLAG_WATER_EFFECT })
        export_textures.append({ 'mat_node': mprops.ugplus_matslot_reflection, 'flags': MATFLAG_BUMP_LOAD_MATRIX })
 
    # Export all the textures we need for the shader, as gathered above
    tex_count = -1
    for node in export_textures:
        tex_count += 1
        tex = node['mat_node']
        tex_flags = node['flags']
        
        # Use the name of the texture image, or generate the color name (will be generated during .tex export)
        if tex.tex_image == None or tex.tex_image.name == '':
            colortex_name = 'io_thps_scene_Color_' + ''.join('{:02X}'.format(int(255*a)) for a in tex.tex_color)
            tex_checksum = crc_from_string(bytes(colortex_name, 'ascii'))
            
        elif is_hex_string(tex.tex_image.name):
            tex_checksum = int(tex.tex_image.name, 0)
        else:
            tex_checksum = crc_from_string(bytes(tex.tex_image.name, 'ascii'))
        
        # If the texture count is beyond the 4 texture limit, we are simply exporting frames for an animated texture
        # which is created at the bottom of this loop
        if tex_count > 3:
            w("I", (tex_count - 3))
            w("I", tex_checksum)  # texture checksum
            continue
            
        w("I", tex_checksum)  # texture checksum
        pass_flags = MATFLAG_SMOOTH | MATFLAG_TEXTURED
        pass_flags |= tex_flags
        if tex_count == 3 and len(export_textures) > 4:
            pass_flags |= MATFLAG_PASS_TEXTURE_ANIMATES
            
        w("I", pass_flags)  # flags # 4132
        w("?", True)  # has color flag; seems to be ignored
        w("3f",  *(m.diffuse_color / 2.0))  # color
        
        #w("I", globals()[pprops.blend_mode] if pprops else vBLEND_MODE_DIFFUSE)
        w("I", vBLEND_MODE_BLEND)
        #w("I", pprops.blend_fixed_alpha if pprops else 0)
        w("I", 0)

        w("I", 0)  # u adressing (wrap, clamp, etc)
        w("I", 0)  # v adressing
        w("2f", *((3.0, 3.0)))  # envmap multiples
        w("I", 65540)  # filtering mode
        
        # If we're going beyond pass 4, place additional textures in the animated texture slot for pass 4
        if tex_count == 3 and len(export_textures) > 4:
            w("i", len(export_textures) - 3)
            w("i", 108) # period
            w("i", 0) # iterations
            w("i", 0) # phase
            #for keyframe in at.keyframes:
            # Export the first animated frame here, since it will be the 4th texture slot we want anyway
            w("I", tex_count - 3)
            w("I", tex_checksum)  # texture checksum
            
            continue

        w("I", 1)  # MMAG
        w("I", 4)  # MMIN
        w("f", -8.0)  # K
        w("f", -8.0)  # L
    
    if tex_count > 3:
        # Need to write these after for the final texture pass if the material uses more than 4 passes
        w("I", 1)  # MMAG
        w("I", 4)  # MMIN
        w("f", -8.0)  # K
        w("f", -8.0)  # L
        
        
def export_materials(output_file, target_game, operator=None):
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
        
        # Export shader 
        if mprops.use_new_mats and mprops.ugplus_shader != 'None':
            LOG.debug("exporting new material system properties...")
            export_ugplus_material(m, output_file, target_game, operator)
            continue 
            
        #denetii - only include texture slots that affect the diffuse color in the Blender material
        passes = [tex_slot.texture for tex_slot in m.texture_slots if tex_slot and tex_slot.use and tex_slot.use_map_color_diffuse]
        if len(passes) > 4:
            if operator:
                operator.report(
                    {"WARNING"},
                    "Material {} has more than 4 passes (enabled texture slots). Using only the first 4.".format(m.name))
            passes = passes[:4]
        if not passes and m.name != "_THUG_DEFAULT_MATERIAL_":
            if operator:
                operator.report({"WARNING"}, "Material {} has no passes (enabled texture slots). Using it's diffuse color.".format(m.name))
                passes = [None]

        if is_hex_string(m.name):
            checksum = int(m.name, 0)
        else:
            checksum = crc_from_string(bytes(m.name, 'ascii'))
        
        w("I", checksum)  # material checksum
        w("I", checksum)  # material name checksum
        w("I", len(passes) or 1)  # material passes
        w("I", mprops.alpha_cutoff)  # alpha cutoff (actually an unsigned byte)
        w("?", mprops.sorted)  # sorted?
        w("f", mprops.draw_order)  # draw order
        w("?", mprops.single_sided)  # single sided
        w("?", mprops.no_backface_culling)  # no backface culling
        w("i", mprops.z_bias)  # z-bias

        #grassify = False
        w("?", mprops.grassify)  # grassify
        if mprops.grassify:  # if grassify
            print("EXPORTING GRASS MATERIAL!")
            w("f", mprops.grass_height)  # grass height
            w("i", mprops.grass_layers)  # grass layers

        w("f", mprops.specular_power)  # specular power
        if mprops.specular_power > 0.0:
            w("3f", *mprops.specular_color)  # specular color

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
            w("3f",  *(pprops.color if pprops else m.diffuse_color / 2.0))  # color

            # alpha register values, first u32 - a BLEND_MODE, second u32 - fixed alpha (clipped to u8)
            # w("Q", 5)
            w("I", globals()[pprops.blend_mode] if pprops else vBLEND_MODE_DIFFUSE)
            w("I", pprops.blend_fixed_alpha if pprops else 0)

            w("I", 0 if (not pprops) or pprops.u_addressing == "Repeat" else 1)  # u adressing (wrap, clamp, etc)
            w("I", 0 if (not pprops) or pprops.v_addressing == "Repeat" else 1)  # v adressing
            w("2f", *(pprops.envmap_multiples if pprops else (3.0, 3.0)))  # envmap multiples
            w("I", 65540)  # filtering mode

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



#----------------------------------------------------------------------------------
def _material_pass_settings_draw(self, context):
    if not context.object:
        return
    ob = context.object
    if not ob.active_material or not ob.active_material.active_texture:
        return
    attrs = [
        "color",
        "blend_mode",
        "blend_fixed_alpha",
        "u_addressing",
        "v_addressing"]
        #"filtering_mode",
        #"test_passes"]
    pass_props = ob.active_material.active_texture.thug_material_pass_props
    for attr in attrs:
        self.layout.prop(
            pass_props,
            attr)
            
    box = self.layout.box().column(True)
    box.row().prop(pass_props, "pf_textured")
    img = getattr(ob.active_material.active_texture, 'image', None)
    if img and pass_props.pf_textured:
        box.row().prop(img.thug_image_props, 'compression_type')
    box.row().prop(pass_props, "pf_bump")
    box.row().prop(pass_props, "pf_water")
    box.row().prop(pass_props, "pf_environment")
    if pass_props.pf_environment:
        box.row().prop(pass_props, "envmap_multiples")
    box.row().prop(pass_props, "pf_decal")
    box.row().prop(pass_props, "pf_smooth")
    box.row().prop(pass_props, "pf_transparent")
    box.row().prop(pass_props, "ignore_vertex_alpha")
    box.row().prop(pass_props, "has_uv_wibbles")
    box.row().prop(pass_props, 'has_animated_texture')
    
    if pass_props.has_uv_wibbles:
        box = self.layout.box().column(True)
        box.row().prop(pass_props.uv_wibbles, "uv_velocity")
        box.row().prop(pass_props.uv_wibbles, "uv_frequency")
        box.row().prop(pass_props.uv_wibbles, "uv_amplitude")
        box.row().prop(pass_props.uv_wibbles, "uv_phase")
    if pass_props.has_animated_texture:
        at = pass_props.animated_texture

        box = self.layout.box()
        col = box.column(True)
        col.prop(at, "period")
        col.prop(at, "iterations")
        col.prop(at, "phase")
        row = box.row(True)
        row.operator("object.thug_add_texture_keyframe", text="Add")
        row.operator("object.thug_remove_texture_keyframe", text="Remove")
        box.row().template_list("THUGAnimatedTextureKeyframesUIList", "", at, "keyframes", at, "keyframes_index", rows=1)
        # box.row().operator(at, "keyframes")

#----------------------------------------------------------------------------------
def _material_settings_draw(self, context):
    if not context.object: return
    ob = context.object
    if not ob.active_material: return
    mps = ob.active_material.thug_material_props
    row = self.layout.row()
    row.prop(mps, "terrain_type")
    row = self.layout.row()
    row.prop(mps, "alpha_cutoff")
    row.prop(mps, "sorted")
    row = self.layout.row()
    row.prop(mps, "z_bias")
    row.prop(mps, "single_sided")
    row = self.layout.row()
    row.prop(mps, "draw_order")
    row.prop(mps, "no_backface_culling")
    row = self.layout.row()
    row.prop(mps, "specular_power")
    row = self.layout.row()
    row.prop(mps, "specular_color")
    self.layout.row().prop(mps, "grassify", toggle=True, icon="HAIR")
    if mps.grassify:
        row = self.layout.row()
        col = row.column(True)
        col.prop(mps, "grass_height")
        col.prop(mps, "grass_layers")


    self.layout.row().prop(mps, "use_new_mats", toggle=True, icon="MATERIAL")
    if mps.use_new_mats:
        box = self.layout.box().column()
        row = box.row(True)
        row.prop(mps, "ugplus_shader")
        if mps.ugplus_shader == 'PBR':
            ugplus_matslot_draw(mps.ugplus_matslot_diffuse, box.row(True), title='Diffuse')
            ugplus_matslot_draw(mps.ugplus_matslot_detail, box.row(True), title='Detail')
            ugplus_matslot_draw(mps.ugplus_matslot_normal, box.row(True), title='Normal/Bump')
            ugplus_matslot_draw(mps.ugplus_matslot_specular, box.row(True), title='Specular')
            ugplus_matslot_draw(mps.ugplus_matslot_reflection, box.row(True), title='Reflection')
            ugplus_matslot_draw(mps.ugplus_matslot_lightmap, box.row(True), title='Lightmap')
            #ugplus_matslot_draw(mps.ugplus_matslot_smoothness, box.row(True), title='Smoothness')
            ugplus_matslot_draw(mps.ugplus_matslot_rainmask, box.row(True), title='Rain Mask')
            ugplus_matslot_draw(mps.ugplus_matslot_snowmask, box.row(True), title='Snow Mask')
            ugplus_matslot_draw(mps.ugplus_matslot_snow, box.row(True), title='Snow')
        elif mps.ugplus_shader == 'Water':
            ugplus_matslot_draw(mps.ugplus_matslot_fallback, box.row(True), title='Fallback')
            ugplus_matslot_draw(mps.ugplus_matslot_reflection, box.row(True), title='Reflection')
        elif mps.ugplus_shader == 'Skybox':
            ugplus_matslot_draw(mps.ugplus_matslot_diffuse, box.row(True), title='Diffuse (Day)')
            ugplus_matslot_draw(mps.ugplus_matslot_diffuse_evening, box.row(True), title='Evening')
            ugplus_matslot_draw(mps.ugplus_matslot_diffuse_night, box.row(True), title='Night')
            ugplus_matslot_draw(mps.ugplus_matslot_diffuse_morning, box.row(True), title='Morning')
            ugplus_matslot_draw(mps.ugplus_matslot_cloud, box.row(True), title='Cloud')
            

# PROPERTIES
#############################################
class THUGImageProps(bpy.types.PropertyGroup):
    compression_type = EnumProperty(items=(
        ("DXT1", "DXT1", "DXT1. 1-bit alpha. 1:8 compression for RGBA, 1:6 for RGB."),
        ("DXT5", "DXT5", "DXT5. Full alpha. 1:4 compression.")),
    name="Compression Type",
    default="DXT1")
#----------------------------------------------------------------------------------
class AddTextureKeyframe(bpy.types.Operator):
    bl_idname = "object.thug_add_texture_keyframe"
    bl_label = "Add THUG Texture Keyframe"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        if not context:
            return False
        ob = context.object
        if not ob:
            return False
        mat = ob.active_material
        if not mat:
            return False
        tex = mat.active_texture
        if not tex:
            return False
        mpp = tex.thug_material_pass_props
        if not mpp or not mpp.has_animated_texture:
            return False
        return True

    def execute(self, context):
        at = context.object.active_material.active_texture.thug_material_pass_props.animated_texture
        at.keyframes.add()
        at.keyframes_index = len(at.keyframes) - 1
        return {"FINISHED"}

#----------------------------------------------------------------------------------
class RemoveTextureKeyframe(bpy.types.Operator):
    bl_idname = "object.thug_remove_texture_keyframe"
    bl_label = "Remove THUG Texture Keyframe"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        if not context:
            return False
        ob = context.object
        if not ob:
            return False
        mat = ob.active_material
        if not mat:
            return False
        tex = mat.active_texture
        if not tex:
            return False
        mpp = tex.thug_material_pass_props
        if not mpp or not mpp.has_animated_texture:
            return False
        return True

    def execute(self, context):
        at = context.object.active_material.active_texture.thug_material_pass_props.animated_texture
        at.keyframes.remove(at.keyframes_index)
        at.keyframes_index = max(0, min(at.keyframes_index, len(at.keyframes) - 1))
        return {"FINISHED"}

#----------------------------------------------------------------------------------
class THUGAnimatedTextureKeyframesUIList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(0.33)
        split.prop(item, "time")
        split.prop_search(item, "image", bpy.data, "images", text="")
#----------------------------------------------------------------------------------
class THUGAnimatedTextureKeyframe(bpy.types.PropertyGroup):
    time = IntProperty(name="Time", min=0)
    image = StringProperty(name="Image")
#----------------------------------------------------------------------------------
class THUGAnimatedTexture(bpy.types.PropertyGroup):
    period = IntProperty(name="Period")
    iterations = IntProperty(name="Iterations")
    phase = IntProperty(name="Phase")

    keyframes = CollectionProperty(type=THUGAnimatedTextureKeyframe)
    keyframes_index = IntProperty()
#----------------------------------------------------------------------------------
class THUGUVWibbles(bpy.types.PropertyGroup):
    uv_velocity = FloatVectorProperty(name="UV velocity", size=2, default=(1.0, 1.0), soft_min=-100, soft_max=100)
    uv_frequency = FloatVectorProperty(name="UV frequency", size=2, default=(0.0, 0.0), soft_min=-100, soft_max=100)
    uv_amplitude = FloatVectorProperty(name="UV amplitude", size=2, default=(0.0, 0.0), soft_min=-100, soft_max=100)
    uv_phase = FloatVectorProperty(name="UV phase", size=2, default=(0.0, 0.0), soft_min=-100, soft_max=100)
#----------------------------------------------------------------------------------
class THUGMaterialSettingsTools(bpy.types.Panel):
    bl_label = "TH Material Settings"
    bl_region_type = "TOOLS"
    bl_space_type = "VIEW_3D"
    bl_category = "THUG Tools"

    @classmethod
    def poll(cls, context):
        return context.object and context.user_preferences.addons[ADDON_NAME].preferences.material_settings_tools

    def draw(self, context):
        if not context.object: return
        ob = context.object

        rows = 1
        is_sortable = len(ob.material_slots) > 1
        if is_sortable:
            rows = 4

        row = self.layout.row()
        row.template_list("MATERIAL_UL_matslots", "", ob, "material_slots", ob, "active_material_index", rows=rows)
        col = row.column(align=True)
        col.operator("object.material_slot_add", icon='ZOOMIN', text="")
        col.operator("object.material_slot_remove", icon='ZOOMOUT', text="")
        col.menu("MATERIAL_MT_specials", icon='DOWNARROW_HLT', text="")
        if is_sortable:
            col.separator()
            col.operator("object.material_slot_move", icon='TRIA_UP', text="").direction = 'UP'
            col.operator("object.material_slot_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

        self.layout.template_ID(ob, "active_material", new="material.new")

        if ob.mode == 'EDIT':
            row = self.layout.row(align=True)
            row.operator("object.material_slot_assign", text="Assign")
            row.operator("object.material_slot_select", text="Select")
            row.operator("object.material_slot_deselect", text="Deselect")

        # self.layout.template_preview(context.object.active_material)
        _material_settings_draw(self, context)

#----------------------------------------------------------------------------------
class THUGMaterialSettings(bpy.types.Panel):
    bl_label = "TH Material Settings"
    bl_region_type = "WINDOW"
    bl_space_type = "PROPERTIES"
    bl_context = "material"

    def draw(self, context):
        _material_settings_draw(self, context)
#----------------------------------------------------------------------------------
class THUGMaterialPassSettingsTools(bpy.types.Panel):
    bl_label = "TH Material Pass Tools"
    bl_region_type = "TOOLS"
    bl_space_type = "VIEW_3D"
    bl_category = "THUG Tools"

    @classmethod
    def poll(self, context):
        return context.object and context.user_preferences.addons[ADDON_NAME].preferences.material_pass_settings_tools

    def draw(self, context):
        from bl_ui.properties_material import active_node_mat
        mat = context.object.active_material
        if not mat:
            self.layout.label("You need a material to configure it's passes.")
            return
        idblock = active_node_mat(mat)
        self.layout.template_list("TEXTURE_UL_texslots", "", idblock, "texture_slots", idblock, "active_texture_index", rows=2)
        self.layout.template_ID(idblock, "active_texture", new="texture.new")
        _material_pass_settings_draw(self, context)

#----------------------------------------------------------------------------------
class THUGMaterialPassSettings(bpy.types.Panel):
    bl_label = "TH Material Pass Settings"
    bl_region_type = "WINDOW"
    bl_space_type = "PROPERTIES"
    bl_context = "texture"

    def draw(self, context):
        _material_pass_settings_draw(self, context)

def set_ugplus_materialslot(self, context):
    if self.tex_image:
        self.tex_image_name = self.tex_image.name
    else:
        self.tex_image_name = ''
#----------------------------------------------------------------------------------
class UGPlusMaterialSlotProps(bpy.types.PropertyGroup):
    #tex_image = StringProperty(name="Texture", description="Texture to be used.")
    tex_image = PointerProperty(name="Texture", type=bpy.types.Image, update=set_ugplus_materialslot)
    tex_image_name = StringProperty(name="ImageName")
    tex_color = FloatVectorProperty(name="Color",
                           subtype='COLOR',
                           default=(1.0, 1.0, 1.0, 1.0),
                           size=4,
                           min=0.0, max=1.0,
                           description="Color used if no texture provided.")
                           
    
def ugplus_matslot_draw(self, layout, title, mat_icon='FILE_IMAGE'):
    #self.tex_image.description = 'test'
    col = layout.column(align=True)
    #col.prop_search(self, 'tex_image', bpy.data, "images", text=title, icon=mat_icon)
    #col.operator("image.open")
    col.scale_x = 0.3
    col.label(title)
    col = layout.column(align=True)
    col.scale_x = 0.5
    col.template_ID(self, "tex_image", open="image.open")
    col = layout.column(align=True)
    col.scale_x = 0.2
    col.prop(self, 'tex_color', text='')
    
#----------------------------------------------------------------------------------
class THUGMaterialProps(bpy.types.PropertyGroup):
    alpha_cutoff = IntProperty(
        name="Alpha Cutoff", min=0, max=255, default=1,
        description="The pixels will alpha lower than this will be discarded.")
    sorted = BoolProperty(name="Sorted", default=False)
    draw_order = FloatProperty(
        name="Draw Order",
        default=-1.0,
        description="The lesser the draw order the earlier the texture will be drawn. Used for sorting transparent textures.")
    single_sided = BoolProperty(name="Single Sided", default=False,
        description="If the material is not using the Diffuse blend mode this can be toggled to force it to be single sided.")
    no_backface_culling = BoolProperty(name="No Backface Culling", default=False,
        description="Makes material with Diffuse blend mode double sided")
    z_bias = IntProperty(name="Z-Bias", default=0,
        description="Adjust this value to prevent Z-fighting on overlapping meshes.")
    specular_power = FloatProperty(name="Specular Power", default=0.0)
    specular_color = FloatVectorProperty(name="Specular Color", subtype="COLOR", min=0, max=1)
    grassify = BoolProperty(name="Grass Effect", description="Use generated grass particles on this material.")
    grass_height = FloatProperty(name="Grass Height", min=0.0, max=1000.0, description="Height of the grass particles.")
    grass_layers = IntProperty(name="Grass Layers", min=0, max=5, description="Number of layers.")
    terrain_type = EnumProperty(
        name="Terrain Type",
        description="The terrain type that will be used for faces using this material when their terrain type is set to \"Auto\".",
        items=[(tt, tt, tt) for tt in TERRAIN_TYPES])

    ###############################################################
    # NEW MATERIAL SYSTEM PROPERTIES
    ###############################################################
    use_new_mats = BoolProperty(name="Use New Material System", description="Use the new material/shader setup for Underground+ (THUG PRO coming soon).")
    ugplus_shader = EnumProperty(
        name="Shader",
        description="The shader to use for this material. Changes the available texture fields.",
        items=[
        ("None", "None", ""),
        ("PBR", "Fake PBR", "General material shader. Allows you to control diffuse, bump mapping, specular highlights, and weather masks."),
        ("Skybox", "Skybox", "Skybox shader supporting 4 separate textures based on TOD."),
        ("Water", "Water", "Water effect shader, creates an animated water surface."),
        ])
    ugplus_matslot_diffuse = PointerProperty(type=UGPlusMaterialSlotProps, name="Diffuse", description="Base texture.")
    ugplus_matslot_detail = PointerProperty(type=UGPlusMaterialSlotProps, name="Detail", description="Detail texture which is multiplied onto the diffuse pass.")
    ugplus_matslot_normal = PointerProperty(type=UGPlusMaterialSlotProps, name="Bump/Normal", description="Bump/normal map (currently renders as bump map).")
    ugplus_matslot_specular = PointerProperty(type=UGPlusMaterialSlotProps, name="Specular", description="Intensity of specular reflections.")
    # Eventually, roughness will be a separate texture that is mixed into the alpha channel for the normal texture, 
    # but for now let's just 
    #ugplus_matslot_smoothness = PointerProperty(type=UGPlusMaterialSlotProps, name="Smoothness", description="Sharpness of specular reflections.")
    ugplus_matslot_reflection = PointerProperty(type=UGPlusMaterialSlotProps, name="Reflection", description="Texture used for specular reflections.")
    ugplus_matslot_lightmap = PointerProperty(type=UGPlusMaterialSlotProps, name="Lightmap", description="Texture used for specular reflections.")
    ugplus_matslot_rainmask = PointerProperty(type=UGPlusMaterialSlotProps, name="Rain Mask", description="Mask used for rain effect.")
    ugplus_matslot_snowmask = PointerProperty(type=UGPlusMaterialSlotProps, name="Snow Mask", description="Mask used for snow effect.")
    ugplus_matslot_snow = PointerProperty(type=UGPlusMaterialSlotProps, name="Snow", description="Snow texture.")
        
    ugplus_matslot_fallback = PointerProperty(type=UGPlusMaterialSlotProps, name="Fallback", description="Texture used on lower graphics settings/lower shader detail settings.")
    ugplus_matslot_diffuse_night = PointerProperty(type=UGPlusMaterialSlotProps, name="Night", description="Texture used when the TOD is night.")
    ugplus_matslot_diffuse_evening = PointerProperty(type=UGPlusMaterialSlotProps, name="Evening", description="Texture used when the TOD is evening.")
    ugplus_matslot_diffuse_morning = PointerProperty(type=UGPlusMaterialSlotProps, name="Evening", description="Texture used when the TOD is morning.")
    ugplus_matslot_diffuse_cloud = PointerProperty(type=UGPlusMaterialSlotProps, name="Cloud", description="Texture used when weather effects (rain, snow) are active.")
    ###############################################################
    
#----------------------------------------------------------------------------------
class THUGMaterialPassProps(bpy.types.PropertyGroup):
    color = FloatVectorProperty(
        name="Color", subtype="COLOR",
        default=(0.5, 0.5, 0.5),
        min=0.0, max=1.0,
        update=_thug_material_pass_props_color_updated)
    blend_mode = EnumProperty(items=(
     ("vBLEND_MODE_DIFFUSE", "DIFFUSE", "( 0 - 0 ) * 0 + Src"),
     # ( 0 - 0 ) * 0 + Src
     ("vBLEND_MODE_ADD", "ADD", "( Src - 0 ) * Src + Dst"),
     # ( Src - 0 ) * Src + Dst
     ("vBLEND_MODE_ADD_FIXED", "ADD_FIXED", "( Src - 0 ) * Fixed + Dst"),
     # ( Src - 0 ) * Fixed + Dst
     ("vBLEND_MODE_SUBTRACT", "SUBTRACT", "( 0 - Src ) * Src + Dst"),
     # ( 0 - Src ) * Src + Dst
     ("vBLEND_MODE_SUB_FIXED", "SUB_FIXED", "( 0 - Src ) * Fixed + Dst"),
     # ( 0 - Src ) * Fixed + Dst
     ("vBLEND_MODE_BLEND", "BLEND", "( Src * Dst ) * Src + Dst"),
     # ( Src * Dst ) * Src + Dst
     ("vBLEND_MODE_BLEND_FIXED", "BLEND_FIXED", "( Src * Dst ) * Fixed + Dst"),
     # ( Src * Dst ) * Fixed + Dst
     ("vBLEND_MODE_MODULATE", "MODULATE", "( Dst - 0 ) * Src + 0"),
     # ( Dst - 0 ) * Src + 0
     ("vBLEND_MODE_MODULATE_FIXED", "MODULATE_FIXED", "( Dst - 0 ) * Fixed + 0"),
     # ( Dst - 0 ) * Fixed + 0
     ("vBLEND_MODE_BRIGHTEN", "BRIGHTEN", "( Dst - 0 ) * Src + Dst"),
     # ( Dst - 0 ) * Src + Dst
     ("vBLEND_MODE_BRIGHTEN_FIXED", "BRIGHTEN_FIXED", "( Dst - 0 ) * Fixed + Dst"),
     # ( Dst - 0 ) * Fixed + Dst
     ("vBLEND_MODE_GLOSS_MAP", "GLOSS_MAP", ""),                             # Specular = Specular * Src    - special mode for gloss mapping
     ("vBLEND_MODE_BLEND_PREVIOUS_MASK", "BLEND_PREVIOUS_MASK", ""),                   # ( Src - Dst ) * Dst + Dst
     ("vBLEND_MODE_BLEND_INVERSE_PREVIOUS_MASK", "BLEND_INVERSE_PREVIOUS_MASK", ""),           # ( Dst - Src ) * Dst + Src
     ("vBLEND_MODE_MODULATE_COLOR", "MODULATE_COLOR", ""),
     ("vBLEND_MODE_ONE_INV_SRC_ALPHA", "ONE_INV_SRC_ALPHA", ""),
    ), name="Blend Mode", default="vBLEND_MODE_DIFFUSE")
    blend_fixed_alpha = IntProperty(name="Fixed Alpha", min=0, max=255)
    u_addressing = EnumProperty(items=(
        ("Repeat", "Repeat", ""),
        ("Clamp", "Clamp", ""),
    ), name="U Addressing", default="Repeat")
    v_addressing = EnumProperty(items=(
        ("Repeat", "Repeat", ""),
        ("Clamp", "Clamp", ""),
    ), name="V Addressing", default="Repeat")
    
    pf_textured = BoolProperty(name="Textured", default=True)
    pf_environment = BoolProperty(name="Environment texture", default=False) 
    pf_bump = BoolProperty(name="Bump texture", default=False) 
    pf_water = BoolProperty(name="Water texture", default=False) 
    pf_decal = BoolProperty(name="Decal", default=False) 
    pf_smooth = BoolProperty(name="Smooth", default=True) 
    pf_transparent = BoolProperty(name="Use Transparency", default=True)
    ignore_vertex_alpha = BoolProperty(name="Ignore Vertex Alpha", default=False)
    envmap_multiples = FloatVectorProperty(name="Envmap Multiples", size=2, default=(3.0, 3.0), min=0.1, max=10.0)
    
    filtering_mode = IntProperty(name="Filtering Mode", min=0, max=100000)
    test_passes = IntProperty(name="Material passes (test)", min=0, max=100000)
    # filtering mode?

    has_uv_wibbles = BoolProperty(name="Has UV Wibbles", default=False)
    uv_wibbles = PointerProperty(type=THUGUVWibbles)

    has_animated_texture = BoolProperty(name="Has Animated Texture", default=False)
    animated_texture = PointerProperty(type=THUGAnimatedTexture)
    
