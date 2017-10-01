#############################################
# SCENE EXPORT - SHARED COMPONENTS
#############################################
import bpy
import bmesh
import struct
import mathutils
import math
from bpy.props import *
from . helpers import *
from . material import *
from . constants import *


# METHODS
#############################################
def do_export(operator, context, target_game):
    self = operator
    import subprocess, shutil, datetime

    addon_prefs = context.user_preferences.addons[__name__].preferences
    base_files_dir_error = _get_base_files_dir_error(addon_prefs)
    if base_files_dir_error:
        self.report({"ERROR"}, "Base files directory error: {} Check the base files directory addon preference. Aborting export.".format(base_files_dir_error))
        return {"CANCELLED"}
    base_files_dir = addon_prefs.base_files_dir

    if target_game == "THUG1":
        DEFAULT_SKY_SCN = self.skybox_name + ".scn.xbx"
        DEFAULT_SKY_TEX = self.skybox_name + ".tex.xbx"
    elif target_game == "THUG2":
        DEFAULT_SKY_SCN = self.skybox_name + ".scn.xbx"
        DEFAULT_SKY_TEX = self.skybox_name + ".tex.xbx"
    else:
        raise Exception("Unknown target game: {}".format(target_game))

    start_time = datetime.datetime.now()

    filename = self.filename
    directory = self.directory

    j = os.path.join

    def md(dir):
        if not os.path.exists(dir):
            os.makedirs(dir)

    pre_ext = ".prx" if target_game == "THUG2" else ".pre"

    self.report({'OPERATOR'}, "")
    self.report({'INFO'}, "-" * 20)
    self.report({'INFO'}, "Starting export of {} at {}".format(filename, start_time.time()))
    orig_objects, temporary_objects = [], []

    import sys
    logging_fh = logging.FileHandler(j(directory, filename + "_export.log"), mode='w')
    logging_fh.setFormatter(logging.Formatter("{asctime} [{levelname}]  {message}", style='{', datefmt="%H:%M:%S"))
    logging_ch = logging.StreamHandler(sys.stdout)
    logging_ch.setFormatter(logging.Formatter("{asctime} [{levelname}]  {message}", style='{', datefmt="%H:%M:%S"))
    global global_export_scale
    global_export_scale = operator.export_scale
    try:
        LOG.addHandler(logging_fh)
        LOG.addHandler(logging_ch)
        LOG.setLevel(logging.DEBUG)

        if self.generate_col_file or self.generate_scn_file or self.generate_scripts_files:
            orig_objects, temporary_objects = _prepare_autosplit_objects(operator, context,target_game)

        if target_game == "THUG1":
            path = j(directory, "Levels/" + filename)
        else:
            path = j(directory, filename + "col/Levels/" + filename)
        md(path)
        if self.generate_col_file:
            self.report({'OPERATOR'}, "Generating collision file... ")
            if target_game == "THUG1":
                export_col(filename + ".col", path, target_game, self)
            else:
                export_col(filename + ".col.xbx", path, target_game, self)
        if self.pack_col:
            if target_game == "THUG2":
                pack_pre(j(directory, filename + "col"),
                         j(directory, filename + "col" + pre_ext))
                self.report({'OPERATOR'}, "Exported " + j(directory, filename + "col" + pre_ext))

            if target_game == "THUG1":
                netpath = j(directory, "Levels/" + filename)
                md(netpath)
                shutil.copy(j(path, filename + ".col"), j(netpath, filename + "_net.col"))
                self.report({'OPERATOR'}, "Exported " + j(directory, filename + "_net.col"))

        if target_game == "THUG1":
            path = j(directory, "Levels/" + filename)
        else:
            path = j(directory, filename + "scn/Levels/" + filename)
        md(path)
        if self.generate_scn_file:
            self.report({'OPERATOR'}, "Generating scene file... ")
            if target_game == "THUG1":
                export_scn(filename + ".scn", path, target_game, self)
            else:
                export_scn(filename + ".scn.xbx", path, target_game, self)

        if self.properties.generate_tex_file or not os.path.exists(j(path, filename + ".tex.xbx")):
            md(path)
            self.report({'OPERATOR'}, "Generating tex file... ")
            if target_game == "THUG1":
                export_tex(filename + ".tex", path, target_game, self)
            else:
                export_tex(filename + ".tex.xbx", path, target_game, self)
        else:
            self.report({'OPERATOR'}, "Skipping tex file generation... ")

        if self.pack_scn:
            if target_game == "THUG2":
                md(path + "_sky")
                shutil.copy(
                    j(base_files_dir, 'default_sky', DEFAULT_SKY_SCN),
                    j(path + "_sky", filename + "_sky.scn.xbx"))
                shutil.copy(
                    j(base_files_dir, 'default_sky', DEFAULT_SKY_TEX),
                    j(path + "_sky", filename + "_sky.tex.xbx"))
                
                pack_pre(j(directory, filename + "scn"),
                         j(directory, filename + "scn" + pre_ext))
                self.report({'OPERATOR'}, "Exported " + j(directory, filename + "scn" + pre_ext))

            elif target_game == "THUG1":
                netpath = j(directory, "Levels/" + filename)
                md(netpath)
                md(netpath + "_sky")
                shutil.copy(j(path, filename + ".scn"), j(netpath, filename + "_net.scn"))
                if os.path.exists(j(path, filename + ".tex")):
                    shutil.copy(j(path, filename + ".tex"), j(netpath, filename + "_net.tex"))
                shutil.copy(
                    j(base_files_dir, 'default_sky', DEFAULT_SKY_SCN),
                    j(netpath + "_sky", filename + "_sky.scn"))
                shutil.copy(
                    j(base_files_dir, 'default_sky', DEFAULT_SKY_TEX),
                    j(netpath + "_sky", filename + "_sky.tex"))

                if target_game == "THUG2":
                    pack_pre(j(directory, filename + "scn_NET"),
                             j(directory, filename + "scn_NET" + pre_ext))
                    self.report({'OPERATOR'}, "Exported " + j(directory, filename + "scn_NET" + pre_ext))

        if target_game == "THUG1":
            path = j(directory, "Levels/" + filename)
        else:
            path = j(directory, filename + "qb/Levels/" + filename)
        md(path)
        compilation_successful = None
        if self.generate_scripts_files:
            self.report({'OPERATOR'}, "Generating QB files... ")
            export_qb(filename, path, target_game, self)

            old_cwd = os.getcwd()
            os.chdir(path)
            compilation_successful = True

            import platform
            wine = [] if platform.system() == "Windows" else ["wine"]

            try:
                roq_output = subprocess.run(wine + [
                    j(base_files_dir, "roq.exe"),
                    "-c",
                    filename + ".txt"
                    ], stdout=subprocess.PIPE)
                if os.path.exists(filename + ".qb"):
                    os.remove(filename + ".qb")
                if os.path.exists(filename + ".txt.qb"):
                    os.rename(filename + ".txt.qb", filename + ".qb")
                else:
                    self.report({"ERROR"}, "{}\n\nCompiler output:\nFailed to compile the QB file.".format(
                        '\n'.join(reversed(roq_output.stdout.decode().split("\r\n")))))
                    compilation_successful = False

            finally:
                os.chdir(old_cwd)

        if self.pack_scripts:
            if target_game == "THUG2":
                pack_pre(j(directory, filename + "qb"),
                         j(directory, filename + ("_scripts" if target_game == "THUG2" else "") + pre_ext))
                self.report({'OPERATOR'}, "Exported " + j(directory, filename + pre_ext))

        end_time = datetime.datetime.now()
        if (compilation_successful is None) or compilation_successful:
            self.report({'INFO'}, "Exported level {} at {} (time taken: {})".format(filename, end_time.time(), end_time - start_time))
        else:
            self.report({'WARNING'}, "Failed exporting level {} at {} (time taken: {})".format(filename, end_time.time(), end_time - start_time))
    except ExportError as e:
        self.report({'ERROR'}, "Export failed.\nExport error: {}".format(str(e)))
    except Exception as e:
        LOG.debug(e)
        raise
    finally:
        global_export_scale = 1
        LOG.removeHandler(logging_fh)
        LOG.removeHandler(logging_ch)
        _cleanup_autosplit_objects(operator, context, target_game, orig_objects, temporary_objects)
    return {'FINISHED'}

#----------------------------------------------------------------------------------
def do_export_model(operator, context, target_game):
    self = operator
    import subprocess, shutil, datetime

    addon_prefs = context.user_preferences.addons[__name__].preferences
    base_files_dir_error = _get_base_files_dir_error(addon_prefs)
    if base_files_dir_error:
        self.report({"ERROR"}, "Base files directory error: {} Check the base files directory addon preference. Aborting export.".format(base_files_dir_error))
        return {"CANCELLED"}
    base_files_dir = addon_prefs.base_files_dir

    if not target_game == "THUG1" and not target_game == "THUG2":
        raise Exception("Unknown target game: {}".format(target_game))

    start_time = datetime.datetime.now()

    filename = self.filename
    directory = self.directory

    j = os.path.join

    def md(dir):
        if not os.path.exists(dir):
            os.makedirs(dir)

    self.report({'OPERATOR'}, "")
    self.report({'INFO'}, "-" * 20)
    self.report({'INFO'}, "Starting export of {} at {}".format(filename, start_time.time()))
    orig_objects, temporary_objects = [], []

    import sys
    logging_fh = logging.FileHandler(j(directory, filename + "_export.log"), mode='w')
    logging_fh.setFormatter(logging.Formatter("{asctime} [{levelname}]  {message}", style='{', datefmt="%H:%M:%S"))
    logging_ch = logging.StreamHandler(sys.stdout)
    logging_ch.setFormatter(logging.Formatter("{asctime} [{levelname}]  {message}", style='{', datefmt="%H:%M:%S"))
    global global_export_scale
    global_export_scale = operator.export_scale
    try:
        LOG.addHandler(logging_fh)
        LOG.addHandler(logging_ch)
        LOG.setLevel(logging.DEBUG)

        orig_objects, temporary_objects = _prepare_autosplit_objects(operator, context,target_game)

        path = j(directory, "Models/" + filename)
        md(path)
        # Generate COL file
        self.report({'OPERATOR'}, "Generating collision file... ")
        if target_game == "THUG2":
            export_col(filename + ".col.xbx", path, target_game, self)
        else:
            export_col(filename + ".col", path, target_game, self)
        
        # Generate SCN/MDL file
        self.report({'OPERATOR'}, "Generating scene file... ")
        if target_game == "THUG2":
            export_scn(filename + ".mdl.xbx", path, target_game, self)
        else:
            export_scn(filename + ".mdl", path, target_game, self)

        # Generate TEX file
        self.report({'OPERATOR'}, "Generating tex file... ")
        if target_game == "THUG2":
            export_tex(filename + ".tex.xbx", path, target_game, self)
        else:
            export_tex(filename + ".tex", path, target_game, self)
            
        
        # Maybe generate QB file
        compilation_successful = None
        if self.generate_scripts_files:
            self.report({'OPERATOR'}, "Generating QB files... ")
            export_model_qb(filename, path, target_game, self)

            old_cwd = os.getcwd()
            os.chdir(path)
            compilation_successful = True

            import platform
            wine = [] if platform.system() == "Windows" else ["wine"]

            try:
                roq_output = subprocess.run(wine + [
                    j(base_files_dir, "roq.exe"),
                    "-c",
                    filename + ".txt"
                    ], stdout=subprocess.PIPE)
                if os.path.exists(filename + ".qb"):
                    os.remove(filename + ".qb")
                if os.path.exists(filename + ".txt.qb"):
                    os.rename(filename + ".txt.qb", filename + ".qb")
                else:
                    self.report({"ERROR"}, "{}\n\nCompiler output:\nFailed to compile the QB file.".format(
                        '\n'.join(reversed(roq_output.stdout.decode().split("\r\n")))))
                    compilation_successful = False

            finally:
                os.chdir(old_cwd)

        end_time = datetime.datetime.now()
        if (compilation_successful is None) or compilation_successful:
            self.report({'INFO'}, "Exported model {} at {} (time taken: {})".format(filename, end_time.time(), end_time - start_time))
        else:
            self.report({'WARNING'}, "Failed exporting model {} at {} (time taken: {})".format(filename, end_time.time(), end_time - start_time))
    except ExportError as e:
        self.report({'ERROR'}, "Export failed.\nExport error: {}".format(str(e)))
    except Exception as e:
        LOG.debug(e)
        raise
    finally:
        global_export_scale = 1
        LOG.removeHandler(logging_fh)
        LOG.removeHandler(logging_ch)
        _cleanup_autosplit_objects(operator, context, target_game, orig_objects, temporary_objects)
    return {'FINISHED'}


#----------------------------------------------------------------------------------
def export_scn(filename, directory, target_game, operator=None):
    def w(fmt, *args):
        outp.write(struct.pack(fmt, *args))

    output_file = os.path.join(directory, filename)
    with open(output_file, "wb") as outp:
        w("3I", 1, 1, 1)

        export_materials(outp, target_game, operator)
        if target_game == "THUG2":
            export_scn_sectors_ug2(outp, operator)
        elif target_game == "THUG1":
            export_scn_sectors(outp, operator)
        else:
            raise Exception("Unknown target game: {}".format(target_game))

        w("i", 0)  # number of hierarchy objects

#----------------------------------------------------------------------------------
def export_col(filename, directory, target_game, operator=None):
    from io import BytesIO
    p = Printer()
    output_file = os.path.join(directory, filename)

    bm = bmesh.new()
    def triang(o):
        final_mesh = o.to_mesh(bpy.context.scene, True, 'PREVIEW')
        if _need_to_flip_normals(o):
            temporary_object = _make_temp_obj(final_mesh)
            try:
                bpy.context.scene.objects.link(temporary_object)
                # temporary_object.matrix_world = o.matrix_world
                _flip_normals(temporary_object)
            finally:
                if bpy.context.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.context.scene.objects.unlink(temporary_object)
                bpy.data.objects.remove(temporary_object)

        bm.clear()
        bm.from_mesh(final_mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        bpy.data.meshes.remove(final_mesh)

    out_objects = [o for o in bpy.data.objects
                   if (o.type == "MESH"
                    and getattr(o, 'thug_export_collision', True)
                    and not o.get("thug_autosplit_object_no_export_hack", False))]
    total_verts = 0 # sum(len(bm.verts) for o in out_objects if [triang(o)])
    total_faces = 0 # sum(len(bm.faces) for o in out_objects if [triang(o)])

    with open(output_file, "wb") as outp:
        def w(fmt, *args):
            outp.write(struct.pack(fmt, *args))

        verts_out = BytesIO()
        intensities_out = BytesIO()
        faces_out = BytesIO()
        thug2_thing_out = BytesIO()
        nodes_out = BytesIO()

        w("i", 10 if target_game == "THUG2" else 9) # version
        w("i", len(out_objects)) # num objects
        total_verts_offset = outp.tell()
        w("i", total_verts)
        w("i", total_faces) # large faces
        w("i", 0) # small faces
        w("i", total_verts) # large verts
        w("i", 0) # small verts
        w("i", 0) # padding

        obj_face_offset = 0
        obj_vert_offset = 0
        obj_bsp_offset = 0
        obj_intensity_offset = 0

        bsp_nodes_size = 0
        node_face_index_offset = 0
        node_faces = []

        DBG = lambda *args: LOG.debug(" ".join(str(arg) for arg in args))

        for o in out_objects:
            def w(fmt, *args):
                outp.write(struct.pack(fmt, *args))

            LOG.debug("Exporting object: {}".format(o.name))
            triang(o)
            total_verts += len(bm.verts)
            total_faces += len(bm.faces)

            if "thug_checksum" in o:
                w("i", o["thug_checksum"])
            else:
                w("I", crc_from_string(bytes(get_clean_name(o), 'ascii')))
            w("H", o.thug_col_obj_flags)
            if len(bm.verts) > 2**16:
                raise ExportError("Too many vertices in an object: {} (has {}, max is {}). Consider using Autosplit.".format(o.name, len(bm.verts), 2**16))
            w("H", len(bm.verts))
            MAX_TRIS = 6000 # min(6000, 2**16)
            #if (len(bm.faces) * (3 if target_game == "THUG2" else 1)) > MAX_TRIS:
            if len(bm.faces) > MAX_TRIS:
                raise ExportError("Too many tris in an object: {} (has {}, max is {}). Consider using Autosplit.".format(
                    o.name,
                    len(bm.faces),
                    MAX_TRIS))
                    # 2**16 // (3 if target_game == "THUG2" else 1)))
            w("H", len(bm.faces))
            w("?", False) # use face small
            w("?", False) # use fixed verts
            w("I", obj_face_offset)
            obj_face_offset += SIZEOF_LARGE_FACE * len(bm.faces)
            obj_matrix = get_scale_matrix(o) if o.thug_object_class == "LevelObject" else o.matrix_world
            if operator.is_park_editor: 
                # AFAIK we don't modify the bounding box for dictionary collision, only the scene.
                # But if this changes I'll update it here!
                bbox = get_bbox2(bm.verts, obj_matrix)
            else:
                bbox = get_bbox2(bm.verts, obj_matrix)
            w("4f", *bbox[0])
            w("4f", *bbox[1])
            w("I", obj_vert_offset)
            obj_vert_offset += SIZEOF_FLOAT_VERT * len(bm.verts)
            w("I", obj_bsp_offset)
            obj_bsp_tree = make_bsp_tree(o, bm.faces[:])
            obj_bsp_offset += len(list(iter_tree(obj_bsp_tree))) * SIZEOF_BSP_NODE
            w("I", obj_intensity_offset)
            obj_intensity_offset += len(bm.verts)
            w("I", 0) # padding

            def w(fmt, *args):
                verts_out.write(struct.pack(fmt, *args))

            for v in bm.verts:
                w("3f", *to_thug_coords(obj_matrix * v.co))

            def w(fmt, *args):
                intensities_out.write(struct.pack(fmt, *args))

            intensities_out.write(b'\xff' * len(bm.verts))

            def w(fmt, *args):
                faces_out.write(struct.pack(fmt, *args))

            cfl = bm.faces.layers.int.get("collision_flags")
            ttl = bm.faces.layers.int.get("terrain_type")

            # bm.verts.ensure_lookup_table()
            for face in bm.faces:
                w("H", face[cfl] if cfl else 0)
                tt = _resolve_face_terrain_type(o, bm, face)
                w("H", tt)
                for vert in face.verts:
                    w("H", vert.index)

            if target_game == "THUG2":
                def w(fmt, *args):
                    thug2_thing_out.write(struct.pack(fmt, *args))

                thug2_thing_out.write(b'\x00' * len(bm.faces))

            def w(fmt, *args):
                nodes_out.write(struct.pack(fmt, *args))

            bsp_nodes_start = bsp_nodes_size
            node_list, node_indices = tree_to_list(obj_bsp_tree)
            for idx, node in enumerate(node_list):
                # assert idx == node_indices[id(node)]
                # DBG(node_indices[id(node)])
                bsp_nodes_size += SIZEOF_BSP_NODE
                if isinstance(node, BSPLeaf):
                    w("B", 3)  # the axis it is split on (0 = X, 1 = Y, 2 = Z, 3 = Leaf)
                    w("B", 0)  # padding
                    w("H", len(node.faces) * (3 if False and target_game == "THUG2" else 1))
                    w("I", node_face_index_offset)
                    # exported |= set(node.faces)
                    for face in node.faces:
                        # assert bm.faces[face.index] == face
                        node_faces.append(face.index)
                    node_face_index_offset += len(node.faces) * (3 if False and target_game == "THUG2" else 1)
                else:
                    split_axis_and_point = (
                        (node.split_axis & 0x3) |
                        # 1 |
                        (int(node.split_point * 16.0) << 2)
                        )
                    w("i", split_axis_and_point)
                    w("I", (bsp_nodes_start + node_indices[id(node.left)] * SIZEOF_BSP_NODE))

        def w(fmt, *args):
            outp.write(struct.pack(fmt, *args))

        tmp_offset = outp.tell()
        outp.seek(total_verts_offset)
        w("i", total_verts)
        w("i", total_faces)
        w("i", 0) # small faces
        w("i", total_verts)
        outp.seek(tmp_offset)

        LOG.debug("offset obj list: {}".format(outp.tell()))
        outp.write(b'\x00' * calc_alignment_diff(outp.tell(), 16))

        LOG.debug("offset verts: {}".format(outp.tell()))
        outp.write(verts_out.getbuffer())

        LOG.debug("offset intensities: {}".format(outp.tell()))
        # intensity
        outp.write(intensities_out.getbuffer())

        alignment_diff = calc_alignment_diff(outp.tell(), 4)
        if alignment_diff != 0:
            LOG.debug("A: ".format(alignment_diff))
        outp.write(b'\x00' * alignment_diff)
        # outp.write(b'\x00' * calc_alignment_diff(SIZEOF_FLOAT_VERT * total_verts + total_verts), 4)

        LOG.debug("offset faces: {}".format(outp.tell()))
        outp.write(faces_out.getbuffer())

        if target_game == "THUG2":
            # alignment_diff = calc_alignment_diff(total_verts, 4)
            alignment_diff = calc_alignment_diff(outp.tell(), 2)
            if alignment_diff != 0:
                LOG.debug("B: {}".format(alignment_diff))
            outp.write(b'\x00' * alignment_diff)
        else:
            # LOG.debug("B TH1!")
            if total_faces & 1:
                outp.write(b'\x00' * 2)

        if target_game == "THUG2":
            LOG.debug("offset thug2 thing: {}".format(outp.tell()))
            outp.write(thug2_thing_out.getbuffer())

            alignment_diff = calc_alignment_diff(outp.tell(), 4)
            if alignment_diff != 0:
                LOG.debug("C: {}".format(alignment_diff))
            outp.write(b'\x00' * alignment_diff)

        LOG.debug("offset nodes: {}".format(outp.tell()))

        w("I", bsp_nodes_size)
        outp.write(nodes_out.getbuffer())

        for face in node_faces:
            w("H", face)

    bm.free()

#----------------------------------------------------------------------------------
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


#----------------------------------------------------------------------------------
def get_sphere_from_bbox(bbox):
    bbox_min, bbox_max = bbox

    sphere_x = (bbox_min[0] + bbox_max[0]) / 2.0
    sphere_y = (bbox_min[1] + bbox_max[1]) / 2.0
    sphere_z = (bbox_min[2] + bbox_max[2]) / 2.0
    sphere_radius = (
        (sphere_x - bbox_min[0]) ** 2 +
        (sphere_y - bbox_min[1]) ** 2 +
        (sphere_z - bbox_min[2]) ** 2) ** 0.5

    return (sphere_x, sphere_y, sphere_z, sphere_radius)


#----------------------------------------------------------------------------------
def get_bbox2(vertices, matrix=mathutils.Matrix.Identity(4), is_park_editor=False):
    min_x = float("inf")
    min_y = float("inf")
    min_z = float("inf")
    max_x = -float("inf")
    max_y = -float("inf")
    max_z = -float("inf")
    for v in vertices:
        v = to_thug_coords(matrix * v.co)
        # v = v.co
        min_x = min(v[0], min_x)
        min_y = min(v[1], min_y)
        min_z = min(v[2], min_z)
        max_x = max(v[0], max_x)
        max_y = max(v[1], max_y)
        max_z = max(v[2], max_z)
        
    # bounding box is calculated differently for park dictionaries!
    if is_park_editor: 
        print("bounding box was: " + str(min_x) + "x" + str(min_z) + ", " + str(max_x) + "x" + str(max_z))
        new_min_x = (min_x / 60.0)
        new_min_z = (min_z / 60.0)
        new_max_x = (max_x / 60.0)
        new_max_z = (max_z / 60.0)
        
        if new_min_x < 0: min_x = float(round(new_min_x) * 60);
        else: min_x = float(round(new_min_x) * 60);
        if new_min_z < 0: min_z = float(round(new_min_z) * 60);
        else: min_z = float(round(new_min_z) * 60);
        
        if new_max_x < 0: max_x = float(round(new_max_x) * 60);
        else: max_x = float(round(new_max_x) * 60);
        if new_max_z < 0: max_z = float(round(new_max_z) * 60);
        else: max_z = float(round(new_max_z) * 60);
        
        # Fix bounding boxes that aren't aligned at center
        if (max_x + min_x) > 0: min_x = (max_x * -1.0)
        elif (max_x + min_x) < 0: max_x = (min_x * -1.0)
        if (max_z + min_z) > 0: min_z = (max_z * -1.0)
        elif (max_z + min_z) < 0: max_z = (min_z * -1.0)
        
        # This handles half-size dimensions
        #if (min_x + min_z) % 120 != 0:
        #    if(min_x != min_z and min_x > min_z): min_x -= 60
        #    else: min_z -= 60
        #if (max_x + max_z) % 120 != 0:
        #    if(max_x != max_z and max_x > max_z): max_z += 60
        #    else: max_x += 60
            
        min_y = 0.0
        print("NEW bounding box is: " + str(min_x) + "x" + str(min_z) + ", " + str(max_x) + "x" + str(max_z))
    return ((min_x, min_y, min_z, 1.0), (max_x, max_y, max_z, 1.0))

#----------------------------------------------------------------------------------
def calc_alignment_diff(offset, alignment):
    assert offset >= 0 and alignment >= 0
    if offset % alignment == 0:
        return 0
    return alignment - (offset % alignment)
