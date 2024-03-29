#############################################
# SCENE EXPORT - SHARED COMPONENTS
#############################################
import bpy
import bmesh
import struct
import mathutils
import math
import threading
import traceback

from . import helpers, collision, prefs, material, autosplit
from bpy.props import *
from . prefs import *
from . autosplit import *
from . helpers import *
from . collision import *
from . material import *
from . constants import *
from . qb import *
from . level_manifest import *
from . export_thug1 import export_scn_sectors
from . export_thug2 import export_scn_sectors_ug2
from . export_thps4 import *

class ExportThread(threading.Thread):
    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self):
        super(ExportThread, self).join()
        if self.exc:
            raise self.exc
        return self.ret

# METHODS
#############################################
def append_referenced_assets(directory, target_game, addon_prefs):
    from pathlib import Path
    import shutil
    
    def maybe_copy_file(source_path, dest_path):
        if not os.path.exists(os.path.dirname(dest_path)):
            os.makedirs(os.path.dirname(dest_path))
        if not os.path.exists(dest_path):
            shutil.copy(source_path, dest_path)
            
    asset_objs = [o for o in bpy.data.objects if o.type == 'EMPTY' and o.thug_export_scene]
    asset_paths = []
    for ob in asset_objs:
        if ob.thug_empty_props.empty_type == "GameObject" and ob.thug_go_props.go_model != "":
            asset_paths.append(ob.thug_go_props.go_model)
        elif ob.thug_empty_props.empty_type == "Pedestrian" and ob.thug_ped_props.ped_model != "":
            asset_paths.append(ob.thug_ped_props.ped_model)
        elif ob.thug_empty_props.empty_type == "Vehicle" and ob.thug_veh_props.veh_model != "":
            asset_paths.append(ob.thug_veh_props.veh_model)
            
    j = os.path.join
        
    ext_suffix = ""
    dest_suffix = ".xbx"
    game_paths = []
    if target_game == 'THUG1':
        game_paths.append(addon_prefs.game_data_dir_thug1)
    elif target_game == 'THUG2':
        game_paths.append(addon_prefs.game_data_dir_thug2)
        game_paths.append(addon_prefs.game_data_dir_thugpro)
        ext_suffix = ".xbx"
    else:
        print("Unable to read game files - target game is {}".format(target_game))
        return
        
    asset_files = [
        [ '.col' + ext_suffix, '.col' + dest_suffix ]
        ,[ '.mdl' + ext_suffix, '.mdl' + dest_suffix ]
        ,[ '.skin' + ext_suffix, '.skin' + dest_suffix ]
        ,[ '.tex' + ext_suffix, '.tex' + dest_suffix ]
        ,[ '.qb', '.qb' ]
    ]
    pack_files = []
    for path in asset_paths:
        for game_path in game_paths:
            base_asset_path = j(game_path, 'Models', os.path.dirname(path))
            try:
                file_base = Path(base_asset_path).resolve().stem
                print('{}: {}'.format(base_asset_path, file_base))
                model_path = j(directory, "Models", os.path.dirname(path))
                print('{}'.format(model_path))
                
                # Search for col/mdl/skin/qb/tex files
                for asset_file in asset_files:
                    source_file_path = j(base_asset_path, file_base + asset_file[0])
                    dest_file_path = j(directory, 'Models', os.path.dirname(path), file_base + asset_file[1])
                    if os.path.exists(source_file_path) and dest_file_path not in pack_files:
                        maybe_copy_file(source_file_path, dest_file_path)
                        pack_files.append(dest_file_path)
                        
            except FileNotFoundError:
                continue
        
    return pack_files
        

def pack_pre(root_dir, files, output_file):
    pack = struct.pack
    with open(output_file, "wb") as outp:
        outp.write(pack("I", 0))
        outp.write(pack("I", 0xABCD0003))  # version
        outp.write(pack("I", len(files)))  # num files

        for file in files:
            adjusted_fn = bytes(os.path.relpath(file, root_dir), 'ascii') + b"\x00"
            if len(adjusted_fn) % 4 != 0:
                adjusted_fn = adjusted_fn + (b'\x00' * (4 - (len(adjusted_fn) % 4)))

            with open(file, "rb") as inp:
                data = inp.read()
            outp.write(pack("I", len(data)))  # data size
            outp.write(pack("I", 0))  # compressed data size
            outp.write(pack("I", len(adjusted_fn)))  # file name size
            outp.write(pack("I", crc_from_string(bytes(os.path.relpath(file, root_dir), 'ascii'))))  # file name checksum
            outp.write(adjusted_fn)  # file name
            outp.write(data)  # data

            offs = outp.tell()
            if offs % 4 != 0:
                outp.write(b'\x00' * (4 - (offs % 4)))

        total_bytes = outp.tell()
        outp.seek(0)
        outp.write(pack("I", total_bytes))

#----------------------------------------------------------------------------------
def do_export(operator, context, target_game):
    is_model = False
    self = operator
    import subprocess, shutil, datetime

    addon_prefs = bpy.context.preferences.addons[ADDON_NAME].preferences

    if target_game == "THPS4":
        DEFAULT_SKY_SCN = self.skybox_name + "scn.dat"
        DEFAULT_SKY_TEX = self.skybox_name + "tex.dat"
    elif target_game == "THUG1":
        DEFAULT_SKY_SCN = self.skybox_name + ".scn.xbx"
        DEFAULT_SKY_TEX = self.skybox_name + ".tex.xbx"
    elif target_game == "THUG2":
        DEFAULT_SKY_SCN = self.skybox_name + ".scn.xbx"
        DEFAULT_SKY_TEX = self.skybox_name + ".tex.xbx"
    else:
        raise Exception("Unknown target game: {}".format(target_game))

    global PROPNAME_POSITION
    PROPNAME_POSITION = "Position" if target_game in [ "THPS3", "THPS4" ] else "Pos"
    
    start_time = datetime.datetime.now()

    filename = self.filename
    directory = self.directory

    j = os.path.join

    def md(dir):
        if not os.path.exists(dir):
            os.makedirs(dir)

    ext_pre = (".prx" if target_game == "THUG2" else ".pre")
    ext_col = (".col" if (target_game == "THUG1" and not self.pack_pre) else ".col.xbx" )
    ext_scn = (".scn" if (target_game == "THUG1" and not self.pack_pre) else ".scn.xbx" )
    ext_tex = (".tex" if (target_game == "THUG1" and not self.pack_pre) else ".tex.xbx" )
    ext_qb = ".qb"
    if target_game == "THPS4":
        ext_col = "col.dat"
        ext_scn = "scn.dat"
        ext_tex = "tex.dat"

    self.report({'OPERATOR'}, "")
    self.report({'INFO'}, "-" * 20)
    self.report({'INFO'}, "Starting export of {} at {}".format(filename, start_time.time()))
    orig_objects, temporary_objects = [], []

    import sys
    logging_fh = logging.FileHandler(j(directory, filename + "_export.log"), mode='w')
    logging_fh.setFormatter(logging.Formatter("{asctime} [{levelname}]  {message}", style='{', datefmt="%H:%M:%S"))
    logging_ch = logging.StreamHandler(sys.stdout)
    logging_ch.setFormatter(logging.Formatter("{asctime} [{levelname}]  {message}", style='{', datefmt="%H:%M:%S"))
    
    set_export_scale(operator.export_scale)

    threads = list()
    compilation_successful = True
    
    try:
        LOG.addHandler(logging_fh)
        LOG.addHandler(logging_ch)
        LOG.setLevel(logging.DEBUG)

        if self.generate_col_file or self.generate_scn_file or self.generate_scripts_files:
            orig_objects, temporary_objects = autosplit._prepare_autosplit_objects(operator, context,target_game)

        path = j(directory, "Levels", filename)
        md(path)

        if self.generate_col_file:
            t = ExportThread(target=export_col, args=(filename + ext_col, path, target_game, self))
            t.setDaemon(True)
            t.setName("export_col")
            threads.append(t)
            t.start()
            
        if self.generate_scn_file:
            self.report({'OPERATOR'}, "Generating scene file... ")
            
            t = ExportThread(target=export_scn, args=(filename + ext_scn, path, target_game, self, is_model))
            t.setDaemon(True)
            t.setName("export_scn")
            threads.append(t)
            t.start()
    
        if self.generate_scripts_files:
            self.report({'OPERATOR'}, "Generating QB files... ")
            t = ExportThread(target=export_qb, args=(filename, path, target_game, self))
            t.setDaemon(True)
            t.setName("export_qb")
            threads.append(t)
            t.start()

        # Tex export must be run on the main thread, not sure why
        if self.generate_tex_file:
            self.report({'OPERATOR'}, "Generating tex file... ")
            export_tex(filename + ext_tex, path, target_game, self)
            
            # ********************************************************
            # Export cubemap DDS textures
            if True:
                _lightmap_folder = bpy.path.basename(bpy.context.blend_data.filepath)[:-6] # = Name of blend file
                _folder = bpy.path.abspath("//Tx_Cubemap/{}".format(_lightmap_folder))
                for ob in bpy.data.objects:
                    if ob.type == 'EMPTY' and ob.thug_empty_props and ob.thug_empty_props.empty_type == 'CubemapProbe' \
                        and ob.thug_cubemap_props and ob.thug_cubemap_props.exported == True:
                        shutil.copy("{}/{}.dds".format(_folder, ob.name),
                            j(path, "{}.dds".format(ob.name)))
            # ********************************************************
            
        # If any threads haven't finished yet, wait before continuing
        for index, thread in enumerate(threads):
            thread.join()
            
        if self.generate_scn_file and self.generate_sky:
            skypath = j(directory, "Levels", filename + "_sky")
            md(skypath)
            shutil.copy(
                get_asset_path("sky", DEFAULT_SKY_SCN),
                j(skypath, filename + "_sky" + ext_scn))
            shutil.copy(
                get_asset_path("sky", DEFAULT_SKY_TEX),
                j(skypath, filename + "_sky" + ext_tex))

        if self.generate_scripts_files:
            old_cwd = os.getcwd()
            os.chdir(path)

            import platform
            wine = [] if platform.system() == "Windows" else ["wine"]

            # #########################
            # Build NODEARRAY qb file
            try:
                LOG.debug("Compiling {}.txt to QB...".format(filename))
                roq_output = subprocess.run(wine + [
                    get_asset_path("roq.exe"),
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
            # /Build NODEARRAY qb file
            # #########################
            
            # #########################
            # Build _SCRIPTS qb file
            if os.path.exists(j(path, filename + "_scripts.txt")):
                LOG.debug("Compiling {}_scripts.txt to QB...".format(filename))
                os.chdir(path)
                try:
                    roq_output = subprocess.run(wine + [
                        get_asset_path("roq.exe"),
                        "-c",
                        filename + "_scripts.txt"
                        ], stdout=subprocess.PIPE)
                    if os.path.exists(filename + "_scripts.qb"):
                        os.remove(filename + "_scripts.qb")
                    if os.path.exists(filename + "_scripts.txt.qb"):
                        os.rename(filename + "_scripts.txt.qb", filename + "_scripts.qb")
                    else:
                        self.report({"ERROR"}, "{}\n\nCompiler output:\nFailed to compile the QB file.".format(
                            '\n'.join(reversed(roq_output.stdout.decode().split("\r\n")))))
                        compilation_successful = False

                finally:
                    os.chdir(old_cwd)
            # /Build _SCRIPTS qb file
            # #########################


        # #########################
        # Build PRE files
        if self.pack_pre and target_game != 'THPS4':
            md(j(directory, "pre"))
            
            # Export all level files to a single PRE container
            if False:
                pack_files = []
                pack_files.append(j(path, filename + ext_scn))
                pack_files.append(j(path, filename + ext_tex))
                pack_files.append(j(path, filename + ext_col))
                pack_files.append(j(path, filename + ext_qb))
                pack_files.append(j(path, filename + "_scripts" + ext_qb))
                if self.generate_sky:
                    pack_files.append(j(skypath, filename + "_sky" + ext_scn))
                    pack_files.append(j(skypath, filename + "_sky" + ext_tex))
                pack_pre( directory, pack_files, j(directory, "pre", filename + ext_pre) )
                self.report({'OPERATOR'}, "Exported " + j(directory, "pre", filename + ext_pre))
                
            # Export all level files using the classic multi-PRE container setup
            else:
                if self.generate_scripts_files:
                    pack_files = []
                    pack_files.append(j(path, filename + ext_qb))
                    pack_files.append(j(path, filename + "_scripts" + ext_qb))
                    pack_assets = append_referenced_assets(directory, target_game, addon_prefs)
                    for addl_asset in pack_assets:
                        pack_files.append(addl_asset)
                    print('{}'.format(pack_files))
                    
                    if target_game == "THUG2":
                        pack_files.append(j(path, filename + "_thugpro" + ext_qb))
                        pack_pre( directory, pack_files, j(directory, "pre", filename + "_scripts" + ext_pre) )
                    else:
                        pack_pre( directory, pack_files, j(directory, "pre", filename + ext_pre) )
                    self.report({'OPERATOR'}, "Exported " + j(directory, "pre", filename + ext_pre))
                    
                if self.generate_col_file:
                    pack_files = []
                    pack_files.append(j(path, filename + ext_col))
                    pack_pre( directory, pack_files, j(directory, "pre", filename + "col" + ext_pre) )
                    self.report({'OPERATOR'}, "Exported " + j(directory, "pre", filename + "col" + ext_pre))
                if self.generate_scn_file:
                    pack_files = []
                    pack_files.append(j(path, filename + ext_scn))
                    pack_files.append(j(path, filename + ext_tex))
                    if self.generate_sky:
                        pack_files.append(j(skypath, filename + "_sky" + ext_scn))
                        pack_files.append(j(skypath, filename + "_sky" + ext_tex))
                    pack_pre( directory, pack_files, j(directory, "pre", filename + "scn" + ext_pre) )
                    self.report({'OPERATOR'}, "Exported " + j(directory, "pre", filename + "scn" + ext_pre))
                    
        # /Build PRE files
        # #########################
        
        # Make sure our generated grass materials/textures are removed after export
        cleanup_grass_materials()  
        
        # Final step: generate level manifest .json file!
        export_level_manifest_json(filename, directory, self, context.scene.thug_level_props)
        
    except ExportError as e:
        compilation_successful = False
        LOG.debug(e)
        LOG.debug("".join(traceback.format_tb(e.__traceback__)))
        show_message_box("Export failed.\nError message:\n\n {}".format(str(e)), 'Export Error', 'ERROR')
    except Exception as e:
        compilation_successful = False
        LOG.debug(e)
        LOG.debug("".join(traceback.format_tb(e.__traceback__)))
        show_message_box("Export failed.\nError message:\n\n {}".format(str(e)), 'Export Error', 'ERROR')
    finally:

        end_time = datetime.datetime.now()
        if compilation_successful:
            export_message = "Exported level {} at {} (time taken: {})".format(filename, end_time.time(), end_time - start_time)
            self.report({'INFO'}, export_message)
            show_message_box(export_message, 'Export Complete')
        else:
            self.report({'WARNING'}, "Failed exporting level {} at {} (time taken: {})".format(filename, end_time.time(), end_time - start_time))
            
        LOG.removeHandler(logging_fh)
        LOG.removeHandler(logging_ch)

        autosplit._cleanup_autosplit_objects(operator, context, target_game, orig_objects, temporary_objects)
    return {'FINISHED'}

#----------------------------------------------------------------------------------
def do_export_model(operator, context, target_game):
    is_model = True
    self = operator
    import subprocess, shutil, datetime

    if not target_game in [ "THPS3", "THPS4", "THUG1", "THUG2" ]:
        raise Exception("Unknown target game: {}".format(target_game))

    global PROPNAME_POSITION
    PROPNAME_POSITION = "Position" if target_game in [ "THPS3", "THPS4" ] else "Pos"
    
    start_time = datetime.datetime.now()

    filename = self.filename
    directory = self.directory

    j = os.path.join

    def md(dir):
        if not os.path.exists(dir):
            os.makedirs(dir)

    ext_col = (".col" if target_game == "THUG1" else ".col.xbx" )
    ext_scn = (".mdl" if target_game == "THUG1" else ".mdl.xbx" )
    ext_tex = (".tex" if target_game == "THUG1" else ".tex.xbx" )
    ext_qb = ".qb"
    if self.model_type == "skin":
        ext_scn = (".skin" if target_game == "THUG1" else ".skin.xbx" )
    if target_game == "THPS4":
        ext_col = "col.dat"
        ext_scn = "skin.dat" if self.model_type == "skin" else "mdl.dat"
        ext_tex = "tex.dat"
    
    self.report({'OPERATOR'}, "")
    self.report({'INFO'}, "-" * 20)
    self.report({'INFO'}, "Starting export of {} at {}".format(filename, start_time.time()))
    orig_objects, temporary_objects = [], []

    import sys
    logging_fh = logging.FileHandler(j(directory, filename + "_export.log"), mode='w')
    logging_fh.setFormatter(logging.Formatter("{asctime} [{levelname}]  {message}", style='{', datefmt="%H:%M:%S"))
    logging_ch = logging.StreamHandler(sys.stdout)
    logging_ch.setFormatter(logging.Formatter("{asctime} [{levelname}]  {message}", style='{', datefmt="%H:%M:%S"))
    set_export_scale(operator.export_scale)
    try:
        LOG.addHandler(logging_fh)
        LOG.addHandler(logging_ch)
        LOG.setLevel(logging.DEBUG)
        
        orig_objects, temporary_objects = autosplit._prepare_autosplit_objects(operator, context,target_game)

        path = j(directory, "Models/" + filename)
        md(path)
        
        # Generate COL file
        self.report({'OPERATOR'}, "Generating collision file... ")
        export_col(filename + ext_col, path, target_game, self)
        
        # Generate SCN/MDL file
        self.report({'OPERATOR'}, "Generating scene file... ")
        export_scn(filename + ext_scn, path, target_game, self, is_model)

        # Generate TEX file
        self.report({'OPERATOR'}, "Generating tex file... ")
        export_tex(filename + ext_tex, path, target_game, self)
            
        # Maybe generate QB file
        if self.generate_scripts_files:
            self.report({'OPERATOR'}, "Generating QB files... ")
            export_model_qb(filename, path, target_game, self)

            old_cwd = os.getcwd()
            os.chdir(path)

            import platform
            wine = [] if platform.system() == "Windows" else ["wine"]

            try:
                roq_output = subprocess.run(wine + [
                    get_asset_path("roq.exe"),
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
        if compilation_successful:
            self.report({'INFO'}, "Exported model {} at {} (time taken: {})".format(filename, end_time.time(), end_time - start_time))
        else:
            self.report({'WARNING'}, "Failed exporting model {} at {} (time taken: {})".format(filename, end_time.time(), end_time - start_time))
            
    except ExportError as e:
        self.report({'ERROR'}, "Export failed.\nExport error: {}".format(str(e)))
    except Exception as e:
        LOG.debug(e)
        raise
    finally:
        LOG.removeHandler(logging_fh)
        LOG.removeHandler(logging_ch)
        autosplit._cleanup_autosplit_objects(operator, context, target_game, orig_objects, temporary_objects)

    return {'FINISHED'}

            
#----------------------------------------------------------------------------------
def export_scn(filename, directory, target_game, operator=None, is_model=False):
    def w(fmt, *args):
        outp.write(struct.pack(fmt, *args))

    output_file = os.path.join(directory, filename)
    with open(output_file, "wb") as outp:
        w("3I", 1, 1, 1)

        if target_game == "THPS4":
            export_materials_th4(outp, target_game, operator, is_model)
        else:
            export_materials(outp, target_game, operator, is_model)
        if target_game == "THUG2":
            export_scn_sectors_ug2(outp, operator, is_model)
        elif target_game == "THUG1":
            export_scn_sectors(outp, operator, is_model)
        elif target_game == "THPS4":
            export_scn_sectors_th4(outp, operator, is_model)
        else:
            raise Exception("Unknown target game: {}".format(target_game))

        w("i", 0)  # number of hierarchy objects

#----------------------------------------------------------------------------------
def export_col(filename, directory, target_game, operator=None):
    from io import BytesIO
    p = Printer()
    output_file = os.path.join(directory, filename)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    # Applies modifiers and triangulates mesh - unless the 'speed hack' export option is on
    def triang(o):
        bm.clear()
        bm.from_object(o, depsgraph)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        return

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

        col_version = 10
        if target_game == 'THUG1':
            col_version = 9
        elif target_game == 'THPS4':
            col_version = 8
        
        w("i", col_version) # version
        w("i", len(out_objects)) # num objects
        total_verts_offset = outp.tell()
        w("i", total_verts)
        w("i", total_faces if target_game != 'THPS4' else 0) # large faces
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
        
        face_index = 0 #used for thps4

        DBG = lambda *args: LOG.debug(" ".join(str(arg) for arg in args))

        for o in out_objects:
            def w(fmt, *args):
                outp.write(struct.pack(fmt, *args))

            LOG.debug("Exporting collision object: {}".format(o.name))
            triang(o)
            total_verts += len(bm.verts)
            total_faces += len(bm.faces)

            if "thug_checksum" in o:
                w("i", o["thug_checksum"])
            else:
                clean_name = get_clean_name(o)
                if is_hex_string(clean_name):
                    w("I", int(clean_name, 0))  # checksum
                else:
                    w("I", crc_from_string(bytes(clean_name, 'ascii')))  # checksum
                    
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
            if target_game == 'THPS4':
                obj_face_offset += SIZEOF_LARGE_FACE_THPS4 * len(bm.faces)
            else:
                obj_face_offset += SIZEOF_LARGE_FACE * len(bm.faces)
            obj_matrix = get_scale_matrix(o) if o.thug_object_class == "LevelObject" else o.matrix_world
            #obj_matrix = o.matrix_world
            if operator.is_park_editor: 
                # AFAIK we don't modify the bounding box for dictionary collision, only the scene.
                # But if this changes I'll update it here!
                bbox = get_bbox2(bm.verts, obj_matrix, operator.is_park_editor)
            else:
                bbox = get_bbox2(bm.verts, obj_matrix)
            w("4f", *bbox[0])
            w("4f", *bbox[1])
            w("I", obj_vert_offset)
            if target_game == 'THPS4':
                obj_vert_offset += len(bm.verts)
            else:
                obj_vert_offset += SIZEOF_FLOAT_VERT * len(bm.verts)
            w("I", obj_bsp_offset)
            if target_game != 'THPS4':
                obj_bsp_tree = make_bsp_tree(o, bm.faces[:], obj_matrix)
                obj_bsp_offset += len(list(iter_tree(obj_bsp_tree))) * SIZEOF_BSP_NODE
            else:
                obj_bsp_offset += SIZEOF_BSP_NODE_THPS4
            # THPS4: Intensity list does not exist, intensity is appended to each vert
            if target_game == 'THPS4':
                w("I", 0)
            else:
                w("I", obj_intensity_offset)
            obj_intensity_offset += len(bm.verts)
            w("I", 0) # padding

            def w(fmt, *args):
                verts_out.write(struct.pack(fmt, *args))

            for v in bm.verts:
                w("3f", *to_thug_coords(obj_matrix @ v.co))
                if target_game == 'THPS4':
                    w("B", 0xFF) # Intensity data(?)
                    w("B", 0xFF) # Intensity data(?)
                    w("B", 0xFF) # Intensity data(?)
                    w("B", 0xFF) # Intensity data(?)

            if target_game != 'THPS4':
                def w(fmt, *args):
                    intensities_out.write(struct.pack(fmt, *args))

                intensity_layer = bm.loops.layers.color.get("intensity")
                if not intensity_layer: 
                    intensity_layer = bm.loops.layers.color.get("bake")
                if not intensity_layer: 
                    intensity_layer = bm.loops.layers.color.get("color")
                    
                if intensity_layer:
                    intensities_list = {}
                    for face in bm.faces:
                        for loop in face.loops:
                            tmp_intensity = int((( loop[intensity_layer][0] + loop[intensity_layer][1] + loop[intensity_layer][2] ) / 3.0) * 255)
                            intensities_list[loop.vert] = tmp_intensity
                    
                    for vert in bm.verts:
                        if vert in intensities_list:
                            w('B', intensities_list[vert])
                        else:
                            w('B', 128)
                else:
                    intensities_out.write(b'\xff' * len(bm.verts))

            def w(fmt, *args):
                faces_out.write(struct.pack(fmt, *args))

            cfl = bm.faces.layers.int.get("collision_flags")
            ttl = bm.faces.layers.int.get("terrain_type")
        
            # bm.verts.ensure_lookup_table()
            # Face flags are output here!
            for face in bm.faces:
                if cfl and (face[cfl] & FACE_FLAGS["mFD_TRIGGER"]):
                    if o.thug_triggerscript_props.template_name_txt == "" or o.thug_triggerscript_props.template_name_txt == "None" or \
                    (o.thug_triggerscript_props.template_name_txt == "Custom" and o.thug_triggerscript_props.custom_name == ""):
                        # This object has a Trigger face, but no TriggerScript assigned
                        # Normally this would crash the game, so let's create and assign a blank script!
                        get_triggerscript("io_thps_scene_NullScript")
                        #o.thug_triggerscript_props.template_name = "Custom"
                        o.thug_triggerscript_props.template_name_txt = "Custom"
                        o.thug_triggerscript_props.custom_name = "io_thps_scene_NullScript"
                        LOG.debug("WARNING: Object {} has trigger faces but no TriggerScript. A blank script was assigned.".format(o.name))
                        #raise Exception("Collision object " + o.name + " has a trigger face with no TriggerScript attached to the object! This is for your own safety!")
                        
                w("H", face[cfl] if cfl else 0)
                tt = collision._resolve_face_terrain_type(o, bm, face)
                w("H", tt)
                for vert in face.verts:
                    w("H", vert.index)
                if target_game == 'THPS4':
                    w("H", 0) # Padding?

            if target_game == "THUG2":
                def w(fmt, *args):
                    thug2_thing_out.write(struct.pack(fmt, *args))

                thug2_thing_out.write(b'\x00' * len(bm.faces))

            #p("I am at: {}", outp.tell())

            def w(fmt, *args):
                nodes_out.write(struct.pack(fmt, *args))
            
            if target_game != 'THPS4':
                bsp_nodes_start = bsp_nodes_size
                node_list, node_indices = tree_to_list(obj_bsp_tree)
                for idx, node in enumerate(node_list):
                    # assert idx == node_indices[id(node)]
                    # DBG(node_indices[id(node)])
                    bsp_nodes_size += SIZEOF_BSP_NODE
                    if isinstance(node, BSPLeaf):
                        w("B", 0xFF if target_game == 'THPS4' else 3)  # the axis it is split on (0 = X, 1 = Y, 2 = Z, 3 = Leaf)
                        w("B", 0)  # padding
                        w("H", len(node.faces) * (3 if False and target_game == "THUG2" else 1))
                        w("I", node_face_index_offset)
                        # exported |= set(node.faces)
                        for face in node.faces:
                            # assert bm.faces[face.index] == face
                            node_faces.append(face.index)
                        node_face_index_offset += len(node.faces) * (3 if False and target_game == "THUG2" else 1)
                        #if target_game == 'THPS4':
                        #    # Padding?
                        #    w("I", 0xFFFFFFFF)
                        #    w("I", 0xFFFFFFFF)
                        
                    else:
                        split_axis_and_point = (
                            (node.split_axis & 0x3) |
                            # 1 |
                            (int(node.split_point * 16.0) << 2)
                            )
                        w("i", split_axis_and_point)
                        w("I", (bsp_nodes_start + node_indices[id(node.left)] * SIZEOF_BSP_NODE))
            else:
                num_faces = len(bm.faces)
                w("B", 0xFF) #Leaf?
                w("B", 0x00)
                w("H", num_faces)
                w("I", 0x00000000)
                w("I", 0xFFFFFFFF)
                w("I", 0xFFFFFFFF)
                w("I", face_index)
                face_index += num_faces
                bsp_nodes_size += SIZEOF_BSP_NODE_THPS4
                
        
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

        if target_game != 'THPS4':
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

        if target_game == 'THPS4':
            for o in out_objects:
                index = 0
                triang(o)
                for f in bm.faces:
                    w("H", index)
                    index += 1
        else:
            for face in node_faces:
                w("H", face)

    bm.free()



#----------------------------------------------------------------------------------
def calc_alignment_diff(offset, alignment):
    assert offset >= 0 and alignment >= 0
    if offset % alignment == 0:
        return 0
    return alignment - (offset % alignment)

    
#----------------------------------------------------------------------------------
#- Runs the 'Quick export', validating the settings first
#----------------------------------------------------------------------------------
def maybe_export_scene(operator, scene):
    def scene_settings_are_valid(level_props):
        return (level_props.scene_name != '' and level_props.export_props.target_game != '' and \
            level_props.export_props.directory != '' and level_props.export_props.scene_type != ''  )
            
    if not hasattr(scene, 'thug_level_props') or not hasattr(scene.thug_level_props, 'export_props'):
        operator.report({'ERROR'}, "Unable to run quick export - scene settings were not found!")
        return False
        
    if not scene_settings_are_valid(scene.thug_level_props):
        operator.report({'ERROR'}, "Invalid scene settings. Enter a scene name and select the game/export dir/export type first!")
        return False
        
    scene.thug_level_props.export_props.filename = scene.thug_level_props.scene_name
    scene.thug_level_props.export_props.directory = bpy.path.abspath(scene.thug_level_props.export_props.directory)
    
    if scene.thug_level_props.export_props.scene_type == 'Level':
        do_export(scene.thug_level_props.export_props, bpy.context, scene.thug_level_props.export_props.target_game)
    else:
        do_export_model(scene.thug_level_props.export_props, bpy.context, scene.thug_level_props.export_props.target_game)
    
    return True

#############################################
# OPERATORS
#############################################
class SceneToTHPSLevel(bpy.types.Operator):
    bl_idname = "export.scene_to_thps_level"
    bl_label = "Scene to THPS level"

    def report(self, category, message):
        LOG.debug("OP: {}: {}".format(category, message))
        super().report(category, message)

    engine: EnumProperty(items = (
        ("THPS4", "THPS4", ""),
        ("THUG1", "THUG1", ""),
        ("THUG2", "THUG2", ""),
    ), name="Game Engine", default="THUG2")

    filename: StringProperty(name="File Name")
    directory: StringProperty(name="Directory")

    always_export_normals: BoolProperty(name="Export normals", default=False)
    use_vc_hack: BoolProperty(name="Vertex color hack",
        description = "Doubles intensity of vertex colours. Enable if working with an imported scene that appears too dark in game."
        , default=False)
    # AUTOSPLIT SETTINGS
    autosplit_everything: BoolProperty(name="Autosplit All",
        description = "Applies the autosplit setting to all objects in the scene, with default settings.", default=False)
    autosplit_faces_per_subobject: IntProperty(name="Faces Per Subobject",
        description="The max amount of faces for every created subobject.",
        default=800, min=50, max=6000)
    autosplit_max_radius: FloatProperty(name="Max Radius",
        description="The max radius of for every created subobject.",
        default=2000, min=100, max=5000)
    # /AUTOSPLIT SETTINGS
    pack_pre: BoolProperty(name="Pack files into .prx", default=True)
    is_park_editor: BoolProperty(name="Is Park Editor",
        description="Use this option when exporting a park editor dictionary.", default=False)
    generate_tex_file: BoolProperty(name="Generate a .tex file", default=True)
    generate_scn_file: BoolProperty(name="Generate a .scn file", default=True)
    generate_sky: BoolProperty(name="Generate skybox", default=True,description="Check to export a skybox with this scene")
    generate_col_file: BoolProperty(name="Generate a .col file", default=True)
    generate_scripts_files: BoolProperty(name="Generate scripts", default=True)

    skybox_name: StringProperty(name="Skybox name", default="THUG_sky")
    export_scale: FloatProperty(name="Export scale", default=1)
    
    max_texture_size: IntProperty(name="Max Texture Size"
        , min=0,max=8192,default=0
        , description="Clamp texture dimensions to no larger than the specified size - should be a power of 2"
    )
    max_texture_base_tex: BoolProperty(name="Base Textures", default=False, description="Max texture size applies to base material textures")
    max_texture_lightmap_tex: BoolProperty(name="Lightmaps", default=False, description="Max texture size applies to lightmap textures")
    
    mipmap_offset: IntProperty(
        name="Mipmap offset",
        description="Offsets generation of mipmaps (default is 0). For example, setting this to 1 will make the base texture 1/4 the size. Use when working with very large textures.",
        min=0, max=4, default=0)
    only_offset_lightmap: BoolProperty(name="Only Lightmaps", default=False, description="Mipmap offset only applies to lightmap textures")

    def execute(self, context):
        return do_export(self, context, self.engine)

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        wm.fileselect_add(self)

        return {'RUNNING_MODAL'}
        
    def draw(self, context):
        self.layout.row().prop(self, "engine", icon='FF')
        self.layout.row().prop(self, "generate_sky", toggle=True, icon='MAT_SPHERE_SKY')
        if self.generate_sky:
            box = self.layout.box().column(align=True)
            box.row().prop(self, "skybox_name")
        self.layout.row().prop(self, "always_export_normals", toggle=True, icon='SNAP_NORMAL')
        self.layout.row().prop(self, "use_vc_hack", toggle=True, icon='COLOR')
        self.layout.row().prop(self, "autosplit_everything", toggle=True, icon='MOD_EDGESPLIT')
        if self.autosplit_everything:
            box = self.layout.box().column(align=True)
            box.row().prop(self, "autosplit_faces_per_subobject")
            box.row().prop(self, "autosplit_max_radius")
        self.layout.row().prop(self, "pack_pre", toggle=True, icon='PACKAGE')
        self.layout.row().prop(self, "is_park_editor", toggle=True, icon='PACKAGE')
        self.layout.row().prop(self, "generate_tex_file", toggle=True, icon='TEXTURE_DATA')
        self.layout.row().prop(self, "generate_scn_file", toggle=True, icon='SCENE_DATA')
        self.layout.row().prop(self, "generate_col_file", toggle=True, icon='OBJECT_DATA')
        self.layout.row().prop(self, "generate_scripts_files", toggle=True, icon='FILE_SCRIPT')
        self.layout.row().prop(self, "export_scale")
        box = self.layout.box().column(align=True)
        box.row().prop(self, "max_texture_size")
        row2 = box.row()
        row2.column().prop(self, "max_texture_base_tex", toggle=True)
        row2.column().prop(self, "max_texture_lightmap_tex", toggle=True)
        
#----------------------------------------------------------------------------------
class SceneToTHPSModel(bpy.types.Operator):
    bl_idname = "export.scene_to_thps_model"
    bl_label = "Scene to THPS model"

    def report(self, category, message):
        LOG.debug("OP: {}: {}".format(category, message))
        super().report(category, message)

    engine: EnumProperty(items = (
        ("THPS4", "THPS4", ""),
        ("THUG1", "THUG1", ""),
        ("THUG2", "THUG2", ""),
    ), name="Game Engine", default="THUG2")

    filename: StringProperty(name="File Name")
    directory: StringProperty(name="Directory")

    always_export_normals: BoolProperty(name="Export normals", default=False)
    is_park_editor: BoolProperty(name="Is Park Editor", default=False, options={'HIDDEN'})
    use_vc_hack: BoolProperty(name="Vertex color hack",
        description = "Doubles intensity of vertex colours. Enable if working with an imported scene that appears too dark in game."
        , default=False)
    
    # AUTOSPLIT SETTINGS
    autosplit_everything: BoolProperty(name="Autosplit All"
        , description = "Applies the autosplit setting to all objects in the scene, with default settings."
        , default=False)
    autosplit_faces_per_subobject: IntProperty(name="Faces Per Subobject",
        description="The max amount of faces for every created subobject.",
        default=800, min=50, max=6000)
    autosplit_max_radius: FloatProperty(name="Max Radius",
        description="The max radius of for every created subobject.",
        default=2000, min=100, max=5000)
    # /AUTOSPLIT SETTINGS
    model_type: EnumProperty(items = (
        ("skin", ".skin", "Character skin, used for playable characters and pedestrians"),
        ("mdl", ".mdl", "Model used for vehicles and other static mesh"),
    ), name="Model Type", default="skin")
    generate_scripts_files: BoolProperty(
        name="Generate scripts",
        default=True)
    export_scale: FloatProperty(name="Export scale", default=1)
    
    max_texture_size: IntProperty(name="Max Texture Size"
        , min=0,max=8192,default=0
        , description="Clamp texture dimensions to no larger than the specified size - should be a power of 2"
    )
    max_texture_base_tex: BoolProperty(name="Base Textures", default=False, description="Max texture size applies to base material textures")
    max_texture_lightmap_tex: BoolProperty(name="Lightmaps", default=False, description="Max texture size applies to lightmap textures")
    
    mipmap_offset: IntProperty(
        name="Mipmap offset",
        description="Offsets generation of mipmaps (default is 0). For example, setting this to 1 will make the base texture 1/4 the size. Use when working with very large textures",
        min=0, max=4, default=0)
    only_offset_lightmap: BoolProperty(name="Only Lightmaps", default=False, description="Mipmap offset only applies to lightmap textures")
        
    def execute(self, context):
        return do_export_model(self, context, self.engine)

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        wm.fileselect_add(self)

        return {'RUNNING_MODAL'}
        
    def draw(self, context):
        self.layout.row().prop(self, "engine", icon='FF')
        self.layout.row().prop(self, "always_export_normals", toggle=True, icon='SNAP_NORMAL')
        self.layout.row().prop(self, "use_vc_hack", toggle=True, icon='COLOR')
        self.layout.row().prop(self, "autosplit_everything", toggle=True, icon='MOD_EDGESPLIT')
        if self.autosplit_everything:
            box = self.layout.box().column(align=True)
            box.row().prop(self, "autosplit_faces_per_subobject")
            box.row().prop(self, "autosplit_max_radius")
        self.layout.row().prop(self, "model_type", expand=True)
        self.layout.row().prop(self, "generate_scripts_files", toggle=True, icon='FILE_SCRIPT')
        self.layout.row().prop(self, "export_scale")
        box = self.layout.box().column(align=True)
        box.row().prop(self, "max_texture_size")
        row2 = box.row()
        row2.column().prop(self, "max_texture_base_tex", toggle=True)
        row2.column().prop(self, "max_texture_lightmap_tex", toggle=True)
        #box.row().prop(self, "only_offset_lightmap")


class THUGQuickExport(bpy.types.Operator):
    bl_idname = "export.thug_quick_export"
    bl_label = "Quick Export"

    def execute(self, context):
        maybe_export_scene(self, context.scene)
        return {'FINISHED'}
    
#############################################
# PANELS
#############################################
class THUG_PT_ExportTools(bpy.types.Panel):
    bl_label = "TH Export Tools"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"
    bl_category = "THUG Tools"

    @classmethod
    def poll(cls, context):
        return context.preferences.addons[ADDON_NAME].preferences.object_settings_tools

    def draw(self, context):
        if not context.scene: return
        scene = context.scene
        box = self.layout.box().column(align=True)
        box.row().operator(THUGQuickExport.bl_idname, text=THUGQuickExport.bl_label, icon='PACKAGE')
            
            
