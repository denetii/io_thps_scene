#############################################
# THUG1/2 OBJECT CONFIGURE
#############################################
import bpy
import struct
import mathutils
import math
import os, sys
from bpy.props import *
from . constants import *
from . helpers import *
from . autorail import *
from . collision import *
from . import scene_props
from . import qb 
from . qb import *

# METHODS
#############################################
def _thug_object_settings_draw(self, context):
    if not context.object: return
    ob = context.object
    if ob.type == "EMPTY":
        self.layout.row().prop(ob.thug_empty_props, "empty_type")
        if ob.thug_empty_props.empty_type == "Restart":
            self.layout.row().prop(ob.thug_restart_props, "restart_type")
            self.layout.row().prop(ob.thug_restart_props, "restart_name")
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_restart_props, "restart_p1")
            box.row().prop(ob.thug_restart_props, "restart_p2")
            box.row().prop(ob.thug_restart_props, "restart_team")
            box.row().prop(ob.thug_restart_props, "restart_gen")
            box.row().prop(ob.thug_restart_props, "restart_multi")
            box.row().prop(ob.thug_restart_props, "restart_horse")
            box.row().prop(ob.thug_restart_props, "restart_ctf")
        elif ob.thug_empty_props.empty_type == "ProximNode":
            self.layout.row().prop(ob.thug_proxim_props, "proxim_type")
            self.layout.row().prop(ob.thug_proxim_props, "radius")
        elif ob.thug_empty_props.empty_type == "GenericNode":
            self.layout.row().prop(ob.thug_generic_props, "generic_type")
        elif ob.thug_empty_props.empty_type == "GameObject":
            self.layout.row().prop(ob.thug_go_props, "go_type")
            self.layout.row().prop(ob.thug_go_props, "go_model")
            self.layout.row().prop(ob.thug_go_props, "go_suspend")
        elif ob.thug_empty_props.empty_type == "Pedestrian":
            self.layout.row().prop(ob.thug_ped_props, "ped_type")
            self.layout.row().prop(ob.thug_ped_props, "ped_skeleton")
            self.layout.row().prop(ob.thug_ped_props, "ped_animset")
            self.layout.row().prop(ob.thug_ped_props, "ped_extra_anims")
        
    if ob.type == "EMPTY" and ob.thug_empty_props.empty_type in ( "Pedestrian", "Vehicle" ):
        self.layout.row().prop_search(
            ob, "thug_rail_connects_to",
            context.window_manager,
            "thug_all_rails")
        if (ob.thug_rail_connects_to and
                ob.thug_rail_connects_to in bpy.data.objects and
                bpy.data.objects[ob.thug_rail_connects_to].type != "CURVE"):
            self.layout.label(text=ob.thug_rail_connects_to + " is not a curve!", icon="ERROR")

    if ob.type == "MESH":
        self.layout.row().prop(ob, "thug_object_class")
        self.layout.row().prop(ob, "thug_export_collision")
        self.layout.row().prop(ob, "thug_export_scene")
        self.layout.row().prop(ob, "thug_occluder")
        self.layout.row().prop(ob, "thug_always_export_to_nodearray")
        self.layout.row().prop(ob, "thug_do_autosplit")
        if ob.thug_do_autosplit:
            box = self.layout.column(True)
            box.prop(ob, "thug_do_autosplit_faces_per_subobject")
            box.prop(ob, "thug_do_autosplit_max_radius")
        
    if ob.type == "CURVE":
        self.layout.row().prop(ob, "thug_path_type")
        
    if ob.type == "MESH" or (ob.type == "CURVE" and ob.thug_path_type != "") or ob.type == "EMPTY":
        self.layout.row().prop(ob, "thug_created_at_start")
        self.layout.row().prop(ob, "thug_network_option")
        self.layout.row().prop(ob.thug_triggerscript_props, "triggerscript_type")
        if ob.thug_triggerscript_props.triggerscript_type in ("Killskater", "Killskater_Water", "Teleport"):
            _update_restart_collection(self, context)
            self.layout.row().prop_search(
                ob.thug_triggerscript_props,
                "target_node",
                context.window_manager,
                "thug_all_restarts")
        elif ob.thug_triggerscript_props.triggerscript_type in ("Gap"):
            ob.thug_triggerscript_props.gap_props.draw(self, context)
        elif ob.thug_triggerscript_props.triggerscript_type in ("Custom"):
            
            box = self.layout.box().column(True)
            box.row().prop_search(
                ob.thug_triggerscript_props, "custom_name",
                bpy.data,
                "texts")
            box.row().operator(THUGCreateTriggerScript.bl_idname, THUGCreateTriggerScript.bl_label)
            if ob.thug_triggerscript_props.custom_name != '' and not ob.thug_triggerscript_props.custom_name.startswith("script_"):
                box = self.layout.box().column(True)
                box.label("Bad TriggerScript name!", icon="ERROR")
                box.label("Name must start with '_script' to be exported.")
                
        if ob.type == "MESH" or (ob.type == "CURVE" and ob.thug_path_type == "Rail"):
            self.layout.row().prop(ob, "thug_is_trickobject")
            self.layout.row().prop(ob, "thug_cluster_name")
            if not is_string_clean(ob.thug_cluster_name):
                box = self.layout.box().column(True)
                box.label("Bad cluster name!", icon="ERROR")
                box.label("Only valid characters are small and large letters")
                box.label("digits, and underscores.")
    if (ob.type == "CURVE" and ob.thug_path_type in ("Rail", "Ladder", "Waypoint", "Custom")):
        # context.window_manager.thug_rail_objects = [obj for obj in context.scene.objects if obj.type == "CURVE"]
        if ob.thug_path_type == "Rail":
            self.layout.row().prop(ob, "thug_rail_terrain_type")
        _update_rails_collection(self, context)
        #_update_pathnodes_collections()
        self.layout.row().prop_search(
            ob, "thug_rail_connects_to",
            context.window_manager,
            "thug_all_rails")
        if (ob.thug_rail_connects_to and
                ob.thug_rail_connects_to in bpy.data.objects and
                bpy.data.objects[ob.thug_rail_connects_to].type != "CURVE"):
            self.layout.label(text=ob.thug_rail_connects_to + " is not a curve!", icon="ERROR")

    self.layout.row().prop(ob, "thug_node_expansion")

#----------------------------------------------------------------------------------
def _update_pathnodes_collections():
    for ob in bpy.data.objects:
        if ob.type == "CURVE" and ob.thug_path_type in ("Rail", "Ladder", "Waypoint", "Custom"):
            tmp_idx = -1
            if len(ob.data.splines):
                for p in ob.data.splines[0].points:
                    tmp_idx += 1
                    if len(ob.data.thug_pathnode_triggers) < (tmp_idx + 1):
                            ob.data.thug_pathnode_triggers.add()
                            
#----------------------------------------------------------------------------------
def _update_rails_collection(self, context):
    context.window_manager.thug_all_rails.clear()
    for ob in bpy.data.objects:
        if ob.type == "CURVE" and ob.thug_path_type in ("Rail", "Ladder", "Waypoint", "Custom"):
            entry = context.window_manager.thug_all_rails.add()
            entry.name = ob.name

#----------------------------------------------------------------------------------
def _update_restart_collection(self, context):
    context.window_manager.thug_all_restarts.clear()
    for ob in bpy.data.objects:
        if ob.type == "EMPTY" and ob.thug_empty_props.empty_type in ("Restart"):
            entry = context.window_manager.thug_all_restarts.add()
            entry.name = ob.name



# PROPERTIES
#############################################
class THUGObjectSettingsTools(bpy.types.Panel):
    bl_label = "TH Object Settings"
    bl_region_type = "TOOLS"
    bl_space_type = "VIEW_3D"
    bl_category = "THUG Tools"

    @classmethod
    def poll(cls, context):
        return context.object and context.user_preferences.addons[ADDON_NAME].preferences.object_settings_tools

    def draw(self, context):
        _thug_object_settings_draw(self, context)

#----------------------------------------------------------------------------------
class THUGObjectSettings(bpy.types.Panel):
    bl_label = "TH Object Settings"
    bl_region_type = "WINDOW"
    bl_space_type = "PROPERTIES"
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object

    def draw(self, context):
        _thug_object_settings_draw(self, context)


                