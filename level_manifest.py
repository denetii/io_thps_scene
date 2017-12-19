#############################################
# LEVEL MANIFEST FILE HANDLER
#############################################
import bpy
import bmesh
import struct
import mathutils
import math
import os
import numpy
from bpy.props import *
from . scene_props import *


# METHODS
#############################################

#----------------------------------------------------------------------------------
#- Writes the level manifest JSON file
#----------------------------------------------------------------------------------
def export_level_manifest_json(filename, directory, operator, level_info):
    with open(os.path.join(directory, filename + ".json"), "w") as outp:
        outp.write("{\n")
        outp.write("\t\"level_name\": \"{}\",\n".format(level_info.level_name))
        outp.write("\t\"scene_name\": \"{}\",\n".format(level_info.scene_name))

        if level_info.creator_name:
            outp.write("\t\"creator_name\": \"{}\",\n".format(level_info.creator_name))
        else:
            outp.write("\t\"creator_name\": \"Unknown\",\n")

        outp.write("\t\"level_qb\": \"levels\\\\{}\\\\{}.qb\",\n".format(level_info.scene_name, level_info.scene_name))
        outp.write("\t\"level_scripts_qb\": \"levels\\\\{}\\\\{}_scripts.qb\",\n".format(level_info.scene_name, level_info.scene_name))
        outp.write("\t\"level_sfx_qb\": \"levels\\\\{}\\\\{}_sfx.qb\",\n".format(level_info.scene_name, level_info.scene_name))
        outp.write("\t\"level_thugpro_qb\": \"levels\\\\{}\\\\{}_thugpro.qb\",\n".format(level_info.scene_name, level_info.scene_name))

        if not level_info.FLAG_NO_PRX:
            outp.write("\t\"level_pre\": \"{}_scripts.pre\",\n".format(level_info.scene_name))
            outp.write("\t\"level_scnpre\": \"{}scn.pre\",\n".format(level_info.scene_name))
            outp.write("\t\"level_colpre\": \"{}col.pre\",\n".format(level_info.scene_name))

        # outp.write("\t\"FLAG_NOSUN\": true,\n")
        # outp.write("\t\"FLAG_DEFAULT_SKY\": true,\n")
        # outp.write("\t\"FLAG_DISABLE_BACKFACE_HACK\": true,\n")
        # outp.write("\t\"FLAG_DISABLE_GOALEDITOR\": true,\n")
        # outp.write("\t\"FLAG_DISABLE_GOALATTACK\": true,\n")

        # 
        if level_info.FLAG_INDOOR:
            outp.write("\t\"FLAG_INDOOR\": true,\n")
        else:
            outp.write("\t\"FLAG_INDOOR\": false,\n")

        # 
        if level_info.FLAG_NOSUN:
            outp.write("\t\"FLAG_NOSUN\": true,\n")
        else:
            outp.write("\t\"FLAG_NOSUN\": false,\n")

        # 
        if level_info.FLAG_DEFAULT_SKY:
            outp.write("\t\"FLAG_DEFAULT_SKY\": true,\n")
        else:
            outp.write("\t\"FLAG_DEFAULT_SKY\": false,\n")

        # 
        if level_info.FLAG_ENABLE_WALLRIDE_HACK:
            outp.write("\t\"FLAG_ENABLE_WALLRIDE_HACK\": true,\n")
        else:
            outp.write("\t\"FLAG_ENABLE_WALLRIDE_HACK\": false,\n")

        # 
        if level_info.FLAG_DISABLE_BACKFACE_HACK:
            outp.write("\t\"FLAG_DISABLE_BACKFACE_HACK\": true,\n")
        else:
            outp.write("\t\"FLAG_DISABLE_BACKFACE_HACK\": false,\n")

        # 
        if level_info.FLAG_MODELS_IN_SCRIPT_PRX:
            outp.write("\t\"FLAG_MODELS_IN_SCRIPT_PRX\": true,\n")
        else:
            outp.write("\t\"FLAG_MODELS_IN_SCRIPT_PRX\": false,\n")

        # 
        if level_info.FLAG_DISABLE_GOALEDITOR:
            outp.write("\t\"FLAG_DISABLE_GOALEDITOR\": true,\n")
        else:
            outp.write("\t\"FLAG_DISABLE_GOALEDITOR\": false,\n")

        # 
        if level_info.FLAG_DISABLE_GOALATTACK:
            outp.write("\t\"FLAG_DISABLE_GOALATTACK\": true,\n")
        else:
            outp.write("\t\"FLAG_DISABLE_GOALATTACK\": false,\n")

        # 
        if level_info.FLAG_NO_PRX:
            outp.write("\t\"FLAG_NO_PRX\": true\n")
        else:
            outp.write("\t\"FLAG_NO_PRX\": false\n")

        outp.write("}\n")



# PANELS
#############################################
#----------------------------------------------------------------------------------
class THUGSceneSettings(bpy.types.Panel):
    bl_label = "TH Level Settings"
    bl_region_type = "WINDOW"
    bl_space_type = "PROPERTIES"
    bl_context = "world"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        if not context.scene: return
        scene = context.scene
        self.layout.row().prop(scene.thug_level_props, "level_name")
        self.layout.row().prop(scene.thug_level_props, "level_creator")
        self.layout.row().prop(scene.thug_level_props, "level_skybox")
        
        self.layout.row().label(text="Level Lights", icon='LAMP_DATA')
        box = self.layout.box().column(True)
        box.row().prop(scene.thug_level_props, "level_ambient_rgba")
        
        tmp_row = box.row().split()
        col = tmp_row.column()
        col.prop(scene.thug_level_props, "level_light0_rgba")
        col = tmp_row.column()
        col.prop(scene.thug_level_props, "level_light0_headpitch")
        
        tmp_row = box.row().split()
        col = tmp_row.column()
        col.prop(scene.thug_level_props, "level_light1_rgba")
        col = tmp_row.column()
        col.prop(scene.thug_level_props, "level_light1_headpitch")
        
        self.layout.row().label(text="Level Flags", icon='INFO')
        box = self.layout.box().column(True)
        box.row().prop(scene.thug_level_props, "level_flag_offline")
        box.row().prop(scene.thug_level_props, "level_flag_noprx")
        box.row().prop(scene.thug_level_props, "level_flag_indoor")
        box.row().prop(scene.thug_level_props, "level_flag_nosun")
        box.row().prop(scene.thug_level_props, "level_flag_defaultsky")
        box.row().prop(scene.thug_level_props, "level_flag_wallridehack")
        box.row().prop(scene.thug_level_props, "level_flag_nobackfacehack")
        box.row().prop(scene.thug_level_props, "level_flag_modelsinprx")
        box.row().prop(scene.thug_level_props, "level_flag_nogoaleditor")
        box.row().prop(scene.thug_level_props, "level_flag_nogoalattack")