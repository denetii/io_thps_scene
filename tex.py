#############################################
# THPS TEX (.tex) IMPORT/EXPORT
#############################################
import bpy
import os
import struct
from bpy.props import *
from . constants import *
from . helpers import *

# METHODS
#############################################
def get_all_compressed_mipmaps(image, compression_type, mm_offset):
    import bgl, math
    from contextlib import ExitStack
    assert image.channels == 4
    assert compression_type in (1, 5)

    uncompressed_data = get_all_mipmaps(image, mm_offset)
    if not uncompressed_data: return []

    images = []

    with ExitStack() as stack:
        texture_id = bgl.Buffer(bgl.GL_INT, 1)

        bgl.glGenTextures(1, texture_id)
        stack.callback(bgl.glDeleteTextures, 1, texture_id)

        img_width, img_height = image.size
        texture_data = bgl.Buffer(bgl.GL_BYTE, img_width * img_height * 4)
        try:
            level_img_width = img_width
            level_img_height = img_height
            for level, (uncomp_w, uncomp_h, uncompressed_pixels) in enumerate(uncompressed_data):
                texture_data[0:len(uncompressed_pixels)] = uncompressed_pixels

                bgl.glBindTexture(bgl.GL_TEXTURE_2D, texture_id[0])
                bgl.glTexImage2D(
                    bgl.GL_TEXTURE_2D,
                    level,
                    COMPRESSED_RGBA_S3TC_DXT1_EXT if compression_type == 1 else COMPRESSED_RGBA_S3TC_DXT5_EXT,
                    uncomp_w, #level_img_width,
                    uncomp_h, #level_img_height,
                    0,
                    bgl.GL_RGBA,
                    bgl.GL_UNSIGNED_BYTE,
                    texture_data)

                level_img_width /= 2.0
                level_img_width = math.ceil(level_img_width)
                level_img_height /= 2.0
                level_img_height = math.ceil(level_img_height)

            level = 0
            while level < 16:
                # LOG.debug('')
                buf = bgl.Buffer(bgl.GL_INT, 1)
                bgl.glGetTexLevelParameteriv(bgl.GL_TEXTURE_2D, level, bgl.GL_TEXTURE_WIDTH, buf)
                width = buf[0]
                # LOG.debug(width)
                if width < 8: break
                bgl.glGetTexLevelParameteriv(bgl.GL_TEXTURE_2D, level, bgl.GL_TEXTURE_HEIGHT, buf)
                height = buf[0]
                if height < 8: break
                bgl.glGetTexLevelParameteriv(bgl.GL_TEXTURE_2D, level, bgl.GL_TEXTURE_COMPRESSED_IMAGE_SIZE, buf)
                # buf_size = width * height * 4
                buf_size = buf[0]
                del buf
                # LOG.debug(buf_size)
                buf = bgl.Buffer(bgl.GL_BYTE, buf_size)
                bgl.glGetCompressedTexImage(bgl.GL_TEXTURE_2D, level, buf)
                images.append((width, height, buf))
                if level == 0:
                    pass # LOG.debug(images[0][:16])
                # del buf
                level += 1
        finally:
            del texture_data
        return images


#----------------------------------------------------------------------------------
def get_all_mipmaps(image, mm_offset = 0):
    import bgl
    images = []

    image.gl_load()
    image_id = image.bindcode[0]
    if image_id == 0:
        return images
    level = mm_offset # denetii - change this to shift the largest exported size down
    bgl.glBindTexture(bgl.GL_TEXTURE_2D, image_id)
    while level < 16:
        # LOG.debug('')
        buf = bgl.Buffer(bgl.GL_INT, 1)
        bgl.glGetTexLevelParameteriv(bgl.GL_TEXTURE_2D, level, bgl.GL_TEXTURE_WIDTH, buf)
        width = buf[0]
        # LOG.debug(width)
        if width < 8: break
        bgl.glGetTexLevelParameteriv(bgl.GL_TEXTURE_2D, level, bgl.GL_TEXTURE_HEIGHT, buf)
        height = buf[0]
        if height < 8: break
        del buf
        buf_size = width * height * 4
        # LOG.debug(buf_size)
        buf = bgl.Buffer(bgl.GL_BYTE, buf_size)
        bgl.glGetTexImage(bgl.GL_TEXTURE_2D, level, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, buf)
        images.append((width, height, buf))
        if level == 0:
            pass # LOG.debug(images[0][:16])
        # del buf
        level += 1
    return images


def read_tex(reader, printer):
    import bgl
    global name_format
    r = reader
    p = printer

    p("tex file version: {}", r.i32())
    num_textures = p("num textures: {}", r.i32())

    already_seen = set()

    for i in range(num_textures):
        p("texture #{}", i)
        checksum = p("  checksum: {}", hex(r.u32()))

        if checksum in already_seen:
            p("Duplicate checksum!", None)
        else:
            already_seen.add(checksum)

        # tex_map[checksum] = i

        img_width = p("  width: {}", r.u32())
        img_height = p("  height: {}", r.u32())
        levels = p("  levels: {}", r.u32())
        texel_depth = p("  texel depth: {}", r.u32())
        pal_depth = p("  palette depth: {}", r.u32())
        dxt_version = p("  dxt version: {}", r.u32())
        pal_size = p("  palette depth: {}", r.u32())

        if dxt_version == 2:
            dxt_version = 1

        if pal_size > 0:
            if pal_depth == 32:
                pal_colors = []
                for j in range(pal_size//4):
                    cb, cg, cr, ca = r.read("4B")
                    pal_colors.append((cr/255.0, cb/255.0, cb/255.0, ca/255.0))
            else:
                r.read(str(pal_size) + "B")

        for j in range(levels):
            data_size = r.u32()
            if j == 0 and dxt_version == 0:
                data_bytes = r.buf[r.offset:r.offset+data_size]
                if pal_size > 0 and pal_depth == 32 and texel_depth == 8:
                    data_bytes = swizzle(data_bytes, img_width, img_height, 8, 0, True)
                    blend_img = bpy.data.images.new(str(checksum), img_width, img_height, alpha=True)
                    blend_img.pixels = [pal_col for pal_idx in data_bytes for pal_col in pal_colors[pal_idx]]
            elif j == 0 and dxt_version in (1, 5):
                data_bytes = r.buf[r.offset:r.offset+data_size]

                blend_img = bpy.data.images.new(str(checksum), img_width, img_height, alpha=True)
                blend_img.gl_load()
                blend_img.thug_image_props.compression_type = "DXT5" if dxt_version == 5 else "DXT1"
                image_id = blend_img.bindcode[0]
                if image_id == 0:
                    print("Got 0 bindcode for " + blend_img.name)
                else:
                    buf = bgl.Buffer(bgl.GL_BYTE, len(data_bytes))
                    buf[:] = data_bytes
                    bgl.glBindTexture(bgl.GL_TEXTURE_2D, image_id)
                    bgl.glCompressedTexImage2D(
                        bgl.GL_TEXTURE_2D,
                        0,
                        COMPRESSED_RGBA_S3TC_DXT5_EXT if dxt_version == 5 else COMPRESSED_RGBA_S3TC_DXT1_EXT,
                        img_width, #level_img_width,
                        img_height, #level_img_height,
                        0,
                        len(data_bytes),
                        buf)
                    del buf

                    buf_size = img_width * img_height * 4
                    # LOG.debug(buf_size)
                    buf = bgl.Buffer(bgl.GL_FLOAT, buf_size)
                    bgl.glGetTexImage(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, bgl.GL_FLOAT, buf)
                    blend_img.pixels = buf
                    blend_img.pack(as_png=True)
                    del buf

            r.offset += data_size

def get_colortex(color):
    colortex_name = 'io_thps_scene_Color_' + ''.join('{:02X}'.format(int(255*a)) for a in color)
    if bpy.data.images.get(colortex_name):
        return bpy.data.images.get(colortex_name)
    size = 16, 16
    img = bpy.data.images.new(name=colortex_name, width=size[0], height=size[1])
    img.thug_image_props.compression_type = 'DXT5'
    pixels = [None] * size[0] * size[1]
    for x in range(size[0]):
        for y in range(size[1]):
            r = color[0]
            g = color[1]
            b = color[2]
            a = color[3]
            pixels[(y * size[0]) + x] = [r, g, b, a]
    pixels = [chan for px in pixels for chan in px]
    img.pixels = pixels
    #img.use_fake_user = True
    return img.name

def cleanup_colortex():
    for image in bpy.data.images:
        if image.name.startswith('io_thps_scene_Color_'):
            image.user_clear()
            bpy.data.images.remove(image)

def set_image_compression(matslot, compression):
    if matslot.tex_image:
        matslot.tex_image.thug_image_props.compression_type = compression
        
#----------------------------------------------------------------------------------
def export_tex(filename, directory, target_game, operator=None):
    import time

    def w(fmt, *args):
        outp.write(struct.pack(fmt, *args))

    # denetii - only export images that are from materials with enabled texture slots
    # this should avoid exporting normal/spec map textures used for baking
    #out_materials = bpy.data.materials[:]
    out_materials = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH': continue
        if not hasattr(ob, 'thug_export_scene') or ob.thug_export_scene == False: continue
        for mat in ob.data.materials:
            if not hasattr(mat, 'name') or mat.name in out_materials: continue
            out_materials.append(mat.name)
            
    out_images = []
    for m_name in out_materials:
        m = bpy.data.materials[m_name]
        if hasattr(m.thug_material_props, 'ugplus_shader') and m.thug_material_props.ugplus_shader != '':
            # Make sure we always export textures which are plugged into the new material/shader system
            # Also need to generate a texture based on a specified color, if no texture was used
            export_textures = []
            if m.thug_material_props.ugplus_shader == 'PBR':
                export_textures.append(m.thug_material_props.ugplus_matslot_normal)
                set_image_compression(m.thug_material_props.ugplus_matslot_normal, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_reflection)
                export_textures.append(m.thug_material_props.ugplus_matslot_diffuse)
                set_image_compression(m.thug_material_props.ugplus_matslot_diffuse, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_detail)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap)
                export_textures.append(m.thug_material_props.ugplus_matslot_weathermask)
                export_textures.append(m.thug_material_props.ugplus_matslot_snow)
                export_textures.append(m.thug_material_props.ugplus_matslot_specular)
                
            if m.thug_material_props.ugplus_shader == 'PBR_Lightmapped':
                export_textures.append(m.thug_material_props.ugplus_matslot_normal)
                set_image_compression(m.thug_material_props.ugplus_matslot_normal, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_reflection)
                export_textures.append(m.thug_material_props.ugplus_matslot_diffuse)
                set_image_compression(m.thug_material_props.ugplus_matslot_diffuse, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_detail)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap2)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap3)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap4)
                export_textures.append(m.thug_material_props.ugplus_matslot_weathermask)
                export_textures.append(m.thug_material_props.ugplus_matslot_snow)
                export_textures.append(m.thug_material_props.ugplus_matslot_specular)
                
            elif m.thug_material_props.ugplus_shader == 'Skybox':
                export_textures.append(m.thug_material_props.ugplus_matslot_diffuse)
                export_textures.append(m.thug_material_props.ugplus_matslot_diffuse_evening)
                export_textures.append(m.thug_material_props.ugplus_matslot_diffuse_night)
                export_textures.append(m.thug_material_props.ugplus_matslot_diffuse_morning)
                
            elif m.thug_material_props.ugplus_shader == 'Cloud':
                export_textures.append(m.thug_material_props.ugplus_matslot_cloud)
                
            elif m.thug_material_props.ugplus_shader == 'Water':
                export_textures.append(m.thug_material_props.ugplus_matslot_fallback)
                export_textures.append(m.thug_material_props.ugplus_matslot_reflection)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap2)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap3)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap4)
                export_textures.append(m.thug_material_props.ugplus_matslot_detail)
                
            elif m.thug_material_props.ugplus_shader == 'Water_Custom':
                export_textures.append(m.thug_material_props.ugplus_matslot_normal)
                set_image_compression(m.thug_material_props.ugplus_matslot_normal, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_normal2)
                set_image_compression(m.thug_material_props.ugplus_matslot_normal2, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_fallback)
                export_textures.append(m.thug_material_props.ugplus_matslot_reflection)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap2)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap3)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap4)
                export_textures.append(m.thug_material_props.ugplus_matslot_detail)
                
            elif m.thug_material_props.ugplus_shader == 'Water_Displacement':
                export_textures.append(m.thug_material_props.ugplus_matslot_normal)
                set_image_compression(m.thug_material_props.ugplus_matslot_normal, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_normal2)
                set_image_compression(m.thug_material_props.ugplus_matslot_normal2, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_displacement)
                set_image_compression(m.thug_material_props.ugplus_matslot_displacement, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_displacement2)
                set_image_compression(m.thug_material_props.ugplus_matslot_displacement2, 'DXT5')
                export_textures.append(m.thug_material_props.ugplus_matslot_fallback)
                export_textures.append(m.thug_material_props.ugplus_matslot_reflection)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap2)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap3)
                export_textures.append(m.thug_material_props.ugplus_matslot_lightmap4)
                export_textures.append(m.thug_material_props.ugplus_matslot_detail)
            
            for tex in export_textures:
                if tex.tex_image == None or tex.tex_image == '':
                    out_images.append(get_colortex(tex.tex_color))
                else:
                    out_images.append(tex.tex_image.name)
                
        # denetii - only include texture slots that affect the diffuse color in the Blender material
        passes = [tex_slot.texture for tex_slot in m.texture_slots if tex_slot and tex_slot.use and tex_slot.use_map_color_diffuse]
        if len(passes) > 4:
            if operator:
                passes = passes[:4]
        if not passes and m.name != "_THUG_DEFAULT_MATERIAL_":
            if operator:
                passes = []
        for texture in passes:
            if texture and hasattr(texture, 'image') and texture.image and texture.image.users and texture.image.type in ('IMAGE', 'UV_TEST') and texture.image.source in ('FILE', 'GENERATED') and not texture.image.name in out_images:
                out_images.append(texture.image.name)
        
    output_file = os.path.join(directory, filename)
    with open(output_file, "wb") as outp:
        exported_images = [img for img in bpy.data.images
                           if img.name in out_images]
        w("2I", 777, 0)

        exported_images_count = 0
        for image in exported_images:
            if image.channels != 4:
                if operator:
                    operator.report({"WARNING"}, "Image \"{}\" has {} channels. Expected 4. Skipping export.".format(image.name, image.channels))
                continue
            start_time = time.clock()
            LOG.debug("exporting texture: {}".format(image.name))

            # Names formatted as hex are the original checksums from a tex file import, so we should
            # export with the same value for compatibility with CAS items
            if is_hex_string(image.name):
                checksum = int(image.name, 0)
            else:
                checksum = crc_from_string(bytes(image.name, 'ascii'))
            width, height = image.size
            do_compression = (width / 4.0).is_integer() and (height / 4.0).is_integer()
            if do_compression:
                dxt = {
                    "DXT1": 1,
                    "DXT5": 5,
                }[image.thug_image_props.compression_type]
            else:
                dxt = 0
            #LOG.debug("compression: {}".format(dxt))
            if operator.mipmap_offset:
                mm_offset = operator.mipmap_offset
                if operator.only_offset_lightmap and not image.name.startswith('LM_'):
                    mm_offset = 0
            else:
                mm_offset = 0
            mipmaps = get_all_compressed_mipmaps(image, dxt, mm_offset) if do_compression else get_all_mipmaps(image, mm_offset)
            #for idx, (mw, mh, mm) in enumerate(mipmaps):
                #LOG.debug("mm #{}: {}x{} bytes: {}".format(idx, mw, mh, len(mm)))
            if not do_compression:
                mipmaps = [(mw, mh, mm) for mw, mh, mm in mipmaps if mw <= 1024 and mh <= 1024]
                #LOG.debug("after culling: {}".format(len(mipmaps)))
            if not mipmaps:
                continue
            exported_images_count += 1
            width, height, _ = mipmaps[0]
            mipmaps = [mm for mw, mh, mm in mipmaps]
            #LOG.debug("width, height: {}, {}".format(width, height))

            mip_levels = len(mipmaps)
            texel_depth = 32
            palette_depth = 0
            palette_size = 0

            channels = image.channels
            assert channels == 4

            w("I", checksum)
            w("I", width)
            w("I", height)
            w("I", mip_levels)
            w("I", texel_depth)
            w("I", palette_depth)
            w("I", dxt)
            w("I", palette_size)

            for mipmap in mipmaps:
                w("I", len(mipmap))
                pixels = mipmap # image.pixels[:]
                if dxt != 0:
                    for i in range(0, len(pixels), 2**16):
                        sub_pixels = pixels[i:i + 2**16]
                        w(str(len(sub_pixels)) + "B", *sub_pixels)
                    continue

                out_pixels = []
                _append = out_pixels.append

                for i in range(0, len(mipmap), 4):
                    j = i # i * channels
                    """
                    r = int(pixels[j] * 255) & 0xff
                    g = int(pixels[j + 1] * 255) & 0xff
                    b = int(pixels[j + 2] * 255) & 0xff
                    a = (int(pixels[j + 3] / 2.0 * 255.0) & 0xff) if channels == 4 else 255
                    """
                    r = int(pixels[j]) & 0xff
                    g = int(pixels[j + 1]) & 0xff
                    b = int(pixels[j + 2]) & 0xff
                    a = (int(pixels[j + 3] / 2.0) & 0xff)
                    _append(a << 24 | r << 16 | g << 8 | b)
                if False and target_game != "THUG2":
                    swizzled = swizzle(out_pixels, width, height, 8, 0, False)
                    w(str(len(swizzled)) + "I", *swizzled)
                else:
                    w(str(len(out_pixels)) + "I", *out_pixels)
            del mipmaps[:]
            #LOG.debug("time taken: {}{}".format(time.clock() - start_time, "sec"))

        outp.seek(4)
        w("I", exported_images_count)

    # Remove temp solid-color images generated during export
    cleanup_colortex()


# OPERATORS
#############################################
class THUG2TexToImages(bpy.types.Operator):
    bl_idname = "io.thug2_tex"
    bl_label = "THPS Xbox/PC .tex"
    # bl_options = {'REGISTER', 'UNDO'}

    filename = StringProperty(name="File Name")
    directory = StringProperty(name="Directory")

    def execute(self, context):
        filename = self.filename
        directory = self.directory

        import os

        p = Printer()
        p("Reading .TEX file: {}", os.path.join(directory, filename))
        with open(os.path.join(directory, filename), "rb") as inp:
            r = Reader(inp.read())
            read_tex(r, p)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        wm.fileselect_add(self)

        return {'RUNNING_MODAL'}

