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

# METHODS
#############################################
def read_materials(reader, printer, num_materials, directory, operator, output_file=None, texture_map=None, texture_prefix=None):
    import os
    r = reader
    p = printer

    for i in range(num_materials):
        p("material {}", i)
        mat_checksum = p("  material checksum: {}", r.u32())
        blender_mat = bpy.data.materials.new(str(mat_checksum))
        ps = blender_mat.thug_material_props
        p("  material name checksum: {}", r.u32())

        if False and output_file:
            output_file.write("newmtl {}\n".format(mat_checksum))

        num_passes = p("  material passes: {}", r.u32())
        # MATERIAL_PASSES[mat_checksum] = num_passes
        ps.alpha_cutoff = p("  alpha cutoff: {}", r.u32() % 256)
        ps.sorted = p("  sorted: {}", r.bool())
        ps.draw_order = p("  draw order: {}", r.f32())
        ps.single_sided = p("  single_sided: {}", r.bool())
        ps.no_backface_culling = p("  no backface culling: {}", r.bool())
        ps.z_bias = p("  z bias: {}", r.i32())

        grassify = p("  grassify: {}", r.bool())
        if grassify:
            p("  grass height: {}", r.f32())
            p("  grass layers: {}", r.i32())

        ps.specular_power = p("  specular power: {}", r.f32())
        if ps.specular_power > 0.0:
            ps.specular_color = p("  specular color: {}", r.read("3f"))

        blender_mat.use_transparency = True
        blender_mat.diffuse_color = (1, 1, 1)
        blender_mat.diffuse_intensity = 1
        blender_mat.specular_intensity = 0
        blender_mat.alpha = 0

        for j in range(num_passes):
            blender_tex = bpy.data.textures.new("{}/{}".format(mat_checksum, j), "IMAGE")
            tex_slot = blender_mat.texture_slots.add()
            tex_slot.texture = blender_tex
            pps = blender_tex.thug_material_pass_props
            p("  pass #{}", j)
            tex_checksum = p("    pass texture checksum: {}", r.u32())
            image_name = str(tex_checksum) + ".png"
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
                    atkf.image = str(r.u32())

            if tex_checksum:  # mipmap info
                p("    mmag: {}", r.u32())
                p("    mmin: {}", r.u32())
                p("    k: {}", r.f32())
                p("    l: {}", r.f32())
            else:
                r.read("4I")

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
        "v_addressing",
        "filtering_mode",
        "test_passes"]
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




# PROPERTIES
#############################################
class THUGMaterialSettingsTools(bpy.types.Panel):
    bl_label = "TH Material Settings"
    bl_region_type = "TOOLS"
    bl_space_type = "VIEW_3D"
    bl_category = "THUG Tools"

    @classmethod
    def poll(cls, context):
        return context.object and context.user_preferences.addons[__name__].preferences.material_settings_tools

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
        return context.object and context.user_preferences.addons[__name__].preferences.material_pass_settings_tools

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
