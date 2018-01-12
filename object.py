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
from . import script_template

# METHODS
#############################################
def _thug_object_settings_draw(self, context):
    if not context.object: return
    ob = context.object
    # ********************************************************
    # * LEVEL LIGHT
    # ********************************************************
    if ob.type == "LAMP" and ob.data.type == "POINT":
        self.layout.row().prop(ob, "thug_created_at_start")
        self.layout.row().prop(ob, "thug_network_option")
        box = self.layout.box().column(True)
        box.row().prop(ob.data, "color")
        box.row().prop(ob.data, "energy")
        box.row().prop(ob.data.thug_light_props, "light_radius")
        box.row().prop(ob.data.thug_light_props, "light_excludeskater")
        box.row().prop(ob.data.thug_light_props, "light_excludelevel")
        
    elif ob.type == "EMPTY":
        self.layout.row().prop(ob.thug_empty_props, "empty_type")
        # ********************************************************
        # * RESTART
        # ********************************************************
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
        # ********************************************************
        # * PROXIMNODE 
        # ********************************************************
        elif ob.thug_empty_props.empty_type == "ProximNode":
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_proxim_props, "proxim_type")
            box.row().prop(ob.thug_proxim_props, "proxim_shape")
            box.row().prop(ob.thug_proxim_props, "proxim_radius")
        # ********************************************************
        # * EMITTER OBJECT
        # ********************************************************
        elif ob.thug_empty_props.empty_type == "EmitterObject":
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_emitter_props, "emit_type")
            box.row().prop(ob.thug_emitter_props, "emit_radius")
        # ********************************************************
        # * GENERIC
        # ********************************************************
        elif ob.thug_empty_props.empty_type == "GenericNode":
            self.layout.row().prop(ob.thug_generic_props, "generic_type")
        # ********************************************************
        # * GAME OBJECT
        # ********************************************************
        elif ob.thug_empty_props.empty_type == "GameObject":
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_go_props, "go_type")
            if ob.thug_go_props.go_type == "Custom":
                box.row().prop(ob.thug_go_props, "go_type_other")
                box.row().prop(ob.thug_go_props, "go_model")
            box.row().prop(ob.thug_go_props, "go_suspend")
        # ********************************************************
        # * PEDESTRIAN
        # ********************************************************
        elif ob.thug_empty_props.empty_type == "Pedestrian":
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_ped_props, "ped_type")
            box.row().prop(ob.thug_ped_props, "ped_source", expand=True)
            if ob.thug_ped_props.ped_source == "Profile":
                box.row().prop(ob.thug_ped_props, "ped_profile")
            else:
                box.row().prop(ob.thug_ped_props, "ped_model")
            box.row().prop(ob.thug_ped_props, "ped_skeleton")
            box.row().prop(ob.thug_ped_props, "ped_animset")
            box.row().prop(ob.thug_ped_props, "ped_extra_anims")
            box.row().prop(ob.thug_ped_props, "ped_suspend")
        # ********************************************************
        # * VEHICLE
        # ********************************************************
        elif ob.thug_empty_props.empty_type == "Vehicle":
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_veh_props, "veh_type")
            box.row().prop(ob.thug_veh_props, "veh_model")
            if ob.thug_veh_props.veh_model != "" and ob.thug_veh_props.veh_model != "none":
                box.row().prop(ob.thug_veh_props, "veh_usemodellights")
                box.row().prop(ob.thug_veh_props, "veh_allowreplacetex")
                box.row().prop(ob.thug_veh_props, "veh_skeleton")
            box.row().prop(ob.thug_veh_props, "veh_suspend")
            box.row().prop(ob.thug_veh_props, "veh_norail")
            box.row().prop(ob.thug_veh_props, "veh_noskitch")
            
        # ********************************************************
        # * PARTICLE OBJECT
        # ********************************************************
        elif ob.thug_empty_props.empty_type == "ParticleObject":
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_particle_props, "particle_boxdimsstart")
            box.row().prop(ob.thug_particle_props, "particle_boxdimsmid")
            box.row().prop(ob.thug_particle_props, "particle_boxdimsend")
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_particle_props, "particle_usestartpos")
            if ob.thug_particle_props.particle_usestartpos == True:
                box.row().prop(ob.thug_particle_props, "particle_startposition")
            box.row().prop(ob.thug_particle_props, "particle_midposition")
            box.row().prop(ob.thug_particle_props, "particle_endposition")
            box.row().prop(ob.thug_particle_props, "particle_suspend")
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_particle_props, "particle_texture")
            box.row().prop(ob.thug_particle_props, "particle_type")
            box.row().prop(ob.thug_particle_props, "particle_blendmode")
            box.row().prop(ob.thug_particle_props, "particle_fixedalpha")
            box.row().prop(ob.thug_particle_props, "particle_alphacutoff")
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_particle_props, "particle_maxstreams")
            box.row().prop(ob.thug_particle_props, "particle_emitrate")
            box.row().prop(ob.thug_particle_props, "particle_lifetime")
            box.row().prop(ob.thug_particle_props, "particle_usemidpoint")
            box.row().prop(ob.thug_particle_props, "particle_midpointpct")
            box.row().prop(ob.thug_particle_props, "EmitScript")
            box.row().prop(ob.thug_particle_props, "Force")
            box.row().prop(ob.thug_particle_props, "Speed")
            box.row().prop(ob.thug_particle_props, "EmitTarget")
            box.row().prop(ob.thug_particle_props, "UsePulseEmit")
            box.row().prop(ob.thug_particle_props, "RandomEmitRate")
            box.row().prop(ob.thug_particle_props, "RandomEmitDelay")
            box.row().prop(ob.thug_particle_props, "EmitRate1")
            box.row().prop(ob.thug_particle_props, "EmitRate1Delay")
            box.row().prop(ob.thug_particle_props, "EmitRate2")
            box.row().prop(ob.thug_particle_props, "EmitRate2Delay")
            
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_particle_props, "particle_radius")
            box.row().prop(ob.thug_particle_props, "particle_radiusspread")
            box.row().prop(ob.thug_particle_props, "Size")
            box.row().prop(ob.thug_particle_props, "Width")
            box.row().prop(ob.thug_particle_props, "AngleSpread")
            box.row().prop(ob.thug_particle_props, "UseMidTime")
            if ob.thug_particle_props.UseMidTime:
                box.row().prop(ob.thug_particle_props, "MidTime")
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_particle_props, "particle_startcolor")
            box.row().prop(ob.thug_particle_props, "particle_usecolormidtime")
            if ob.thug_particle_props.particle_usecolormidtime == True:
                box.row().prop(ob.thug_particle_props, "particle_colormidtime")
            box.row().prop(ob.thug_particle_props, "particle_midcolor")
            box.row().prop(ob.thug_particle_props, "particle_endcolor")
        
    if ob.type == "EMPTY" and ob.thug_empty_props.empty_type in ( "Pedestrian", "Vehicle" ):
        self.layout.row().prop_search(
            ob, "thug_rail_connects_to",
            context.window_manager.thug_all_nodes, "paths")
        if (ob.thug_rail_connects_to and
                ob.thug_rail_connects_to in bpy.data.objects and
                bpy.data.objects[ob.thug_rail_connects_to].type != "CURVE"):
            self.layout.label(text=ob.thug_rail_connects_to + " is not a curve!", icon="ERROR")

    if ob.type == "MESH":
        self.layout.row().prop(ob, "thug_object_class")
        if ob.thug_object_class == "LevelObject":
            box = self.layout.box().column(True)
            box.row().prop(ob.thug_levelobj_props, "obj_type")
            box.row().prop(ob.thug_levelobj_props, "obj_bouncy")
            if ob.thug_levelobj_props.obj_bouncy:
                box.row().prop(ob.thug_levelobj_props, "center_of_mass")
                box.row().prop(ob.thug_levelobj_props, "contacts")
                box.row().prop(ob.thug_levelobj_props, "coeff_restitution")
                box.row().prop(ob.thug_levelobj_props, "coeff_friction")
                box.row().prop(ob.thug_levelobj_props, "skater_collision_impulse_factor")
                box.row().prop(ob.thug_levelobj_props, "skater_collision_rotation_factor")
                box.row().prop(ob.thug_levelobj_props, "skater_collision_assent")
                box.row().prop(ob.thug_levelobj_props, "skater_collision_radius")
                box.row().prop(ob.thug_levelobj_props, "mass_over_moment")
                box.row().prop(ob.thug_levelobj_props, "SoundType")
                box.row().prop_search(
                    ob.thug_levelobj_props, "stuckscript",
                    bpy.data,
                    "texts")
                    
        self.layout.row().prop(ob, "thug_export_collision")
        self.layout.row().prop(ob, "thug_export_scene")
        if ob.thug_export_scene:
            self.layout.row().prop(ob, "thug_lightgroup")
        
        self.layout.row().prop(ob, "thug_occluder")
        self.layout.row().prop(ob, "thug_always_export_to_nodearray")
        self.layout.row().prop(ob, "thug_do_autosplit")
        if ob.thug_do_autosplit:
            box = self.layout.column(True)
            box.prop(ob, "thug_do_autosplit_faces_per_subobject")
            box.prop(ob, "thug_do_autosplit_max_radius")
        
    if ob.type == "CURVE":
        self.layout.row().prop(ob, "thug_path_type")
        if ob.thug_path_type == 'Waypoint':
            box = self.layout.box().column(True)
            box.row().label(text="Waypoint type")
            box.row().prop(ob.thug_waypoint_props, "waypt_type", expand=True)
            if ob.thug_waypoint_props.waypt_type == 'PedAI':
                box.row().prop(ob.thug_waypoint_props, "PedType", expand=True)
        
    if ob.type == "MESH" or (ob.type == "CURVE" and ob.thug_path_type != "") or ob.type == "EMPTY":
        self.layout.row().prop(ob, "thug_created_at_start")
        self.layout.row().prop(ob, "thug_network_option")
                
        # New template system below!
        box = self.layout.box().column(True)
        box.row().prop(ob.thug_triggerscript_props, "template_name")
        if ob.thug_triggerscript_props.template_name not in [ "None", "Custom" ]:
            #print("attempting to show template params")
            tmpl = script_template.get_template(ob.thug_triggerscript_props.template_name)
            #print(tmpl)
            paramindex = 0
            for prm in tmpl['Parameters']:
                paramindex += 1
                if prm['Name'] and prm['Type']:
                    if prm['Type'] == 'String':
                        box.row().prop(ob.thug_triggerscript_props, "param" + str(paramindex) + "_string", text=prm['Name'])
                    elif prm['Type'] == 'Integer':
                        box.row().prop(ob.thug_triggerscript_props, "param" + str(paramindex) + "_int", text=prm['Name'])
                    elif prm['Type'] == 'Float':
                        box.row().prop(ob.thug_triggerscript_props, "param" + str(paramindex) + "_float", text=prm['Name'])
                    elif prm['Type'] == 'Enum':
                        box.row().prop(ob.thug_triggerscript_props, "param" + str(paramindex) + "_enum", text=prm['Name'])
                    elif prm['Type'] == 'Flags':
                        box.row().prop_menu_enum(ob.thug_triggerscript_props, "param" + str(paramindex) + "_flags", text=prm['Name'], icon='SETTINGS')
                    elif prm['Type'] == 'Restart':
                        box.row().prop_search(ob.thug_triggerscript_props, "param" + str(paramindex) + "_string", 
                        context.window_manager.thug_all_nodes, "restarts", text=prm['Name'])
                    elif prm['Type'] == 'Rail' or prm['Type'] == 'Path':
                        box.row().prop_search(ob.thug_triggerscript_props, "param" + str(paramindex) + "_string", 
                        context.window_manager.thug_all_nodes, "paths", text=prm['Name'])
                    elif prm['Type'] == 'Script':
                        box.row().prop_search(ob.thug_triggerscript_props, "param" + str(paramindex) + "_string", 
                        context.window_manager.thug_all_nodes, "scripts", text=prm['Name'])
                        
        elif ob.thug_triggerscript_props.template_name == "Custom":
            box.row().prop_search(ob.thug_triggerscript_props, "custom_name", bpy.data, "texts")
            box.row().operator(THUGCreateTriggerScript.bl_idname, THUGCreateTriggerScript.bl_label)
            if ob.thug_triggerscript_props.custom_name != '' and not ob.thug_triggerscript_props.custom_name.startswith("script_"):
                box = self.layout.box().column(True)
                box.label("Bad TriggerScript name!", icon="ERROR")
                box.label("Name must start with '_script' to be exported.")
        # End new template system
        
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
            self.layout.row().operator(AutoRailMesh.bl_idname, AutoRailMesh.bl_label)
            
        self.layout.row().operator(UpdateRails.bl_idname, UpdateRails.bl_label)
        self.layout.row().prop_search(
            ob, "thug_rail_connects_to",
            context.window_manager.thug_all_nodes, "paths")
        if (ob.thug_rail_connects_to and
                ob.thug_rail_connects_to in bpy.data.objects and
                bpy.data.objects[ob.thug_rail_connects_to].type != "CURVE"):
            self.layout.label(text=ob.thug_rail_connects_to + " is not a curve!", icon="ERROR")

    self.layout.row().prop(ob, "thug_node_expansion")
    scene_props.update_node_collection(self, context)

                            
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


                