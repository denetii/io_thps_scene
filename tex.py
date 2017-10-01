#############################################
# THPS TEX (.tex) IMPORT/EXPORT
#############################################
import bpy
from bpy.props import *
from . constants import *
from . helpers import Reader, Printer

# METHODS
#############################################
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
        checksum = p("  checksum: {}", r.u32())

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
                    blend_img = bpy.data.images.new(str(checksum) + ".png", img_width, img_height, alpha=True)
                    blend_img.pixels = [pal_col for pal_idx in data_bytes for pal_col in pal_colors[pal_idx]]
            elif j == 0 and dxt_version in (1, 5):
                data_bytes = r.buf[r.offset:r.offset+data_size]

                blend_img = bpy.data.images.new(str(checksum) + ".png", img_width, img_height, alpha=True)
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


#----------------------------------------------------------------------------------
def export_tex(filename, directory, target_game, operator=None):
    import time

    def w(fmt, *args):
        outp.write(struct.pack(fmt, *args))

    # denetii - only export images that are from materials with enabled texture slots
    # this should avoid exporting normal/spec map textures used for baking
    out_materials = bpy.data.materials[:]
    out_images = []
    for m in out_materials:
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
            LOG.debug("compression: {}".format(dxt))
            if operator.mipmap_offset:
                mm_offset = operator.mipmap_offset
            else:
                mm_offset = 0
            mipmaps = get_all_compressed_mipmaps(image, dxt, mm_offset) if do_compression else get_all_mipmaps(image, mm_offset)
            for idx, (mw, mh, mm) in enumerate(mipmaps):
                LOG.debug("mm #{}: {}x{} bytes: {}".format(idx, mw, mh, len(mm)))
            if not do_compression:
                mipmaps = [(mw, mh, mm) for mw, mh, mm in mipmaps if mw <= 1024 and mh <= 1024]
                LOG.debug("after culling: {}".format(len(mipmaps)))
            if not mipmaps:
                continue
            exported_images_count += 1
            width, height, _ = mipmaps[0]
            mipmaps = [mm for mw, mh, mm in mipmaps]
            LOG.debug("width, height: {}, {}".format(width, height))

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
            LOG.debug("time taken: {}{}".format(time.clock() - start_time, "sec"))

        outp.seek(4)
        w("I", exported_images_count)



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

