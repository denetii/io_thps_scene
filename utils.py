#############################################
# SCENE/OBJECT UTILITIES & QUICK FUNCTIONS
#############################################
import bpy
import bmesh
import struct
import mathutils
import math
import os
import numpy
from bpy.props import *
from . constants import *
from . scene_props import *


# METHODS
#############################################

#----------------------------------------------------------------------------------
#- Fills a selection of pedestrian objects with the given props
#----------------------------------------------------------------------------------
#def fill_pedestrians(selection, ped_data):
#    print("omg")


# OPERATORS
#############################################
#----------------------------------------------------------------------------------
class THUGUtilShowFirstPoint(bpy.types.Operator):
    bl_idname = "io.import_thug_util_showfirstpt"
    bl_label = "Show 1st Pt"
    # bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Selects the first point on the path you're currently working with."

    @classmethod
    def poll(cls, context):
        return (context.active_object and context.active_object.type == 'CURVE' and context.active_object.mode == 'EDIT')
        
    def execute(self, context):
        ob = context.active_object
        if len(ob.data.splines) > 0:
            if len(ob.data.splines[0].points) > 0:
                bpy.ops.curve.select_all(action='DESELECT')
                ob.data.splines[0].points[0].select = True
        return {'FINISHED'}

    
        
#----------------------------------------------------------------------------------
class THUGUtilFillPedestrians(bpy.types.Operator):
    bl_idname = "io.import_thug_util_fillpedestrians"
    bl_label = "Auto-Fill Pedestrians"
    # bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Fills a selection (or all) pedestrian objects with default settings for THUG1/2/PRO."
    game_mode = EnumProperty(items=(
        ("THUG1", "THUG1", ""),
        ("THUG2", "THUG2/PRO", ""),
        ), name="Target Game", default="THUG1")

    def execute(self, context):
        peds = [o for o in bpy.data.objects if o.type == 'EMPTY' and o.thug_empty_props.empty_type == 'Pedestrian' ]
        for ped in peds:
            ped.thug_ped_props.ped_type = 'Ped_From_Profile'
            ped.thug_ped_props.ped_source = 'Profile'
            ped.thug_ped_props.ped_profile = 'random_male_profile'
            ped.thug_ped_props.ped_skeleton = 'THPS5_human'
            ped.thug_ped_props.ped_animset = 'animload_THPS5_human'
            if self.game_mode == 'THUG2':
                ped.thug_ped_props.ped_skeleton = 'THPS6_human'
                ped.thug_ped_props.ped_animset = 'animload_THPS6_human'
            ped.thug_ped_props.ped_extra_anims = ''
            ped.thug_ped_props.ped_suspend = 0
            ped.thug_ped_props.ped_model = ''
            ped.thug_ped_props.ped_nologic = False
            
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        peds = [o for o in bpy.data.objects if o.type == 'EMPTY' and o.thug_empty_props.empty_type == 'Pedestrian' ]
        return len(peds) > 0
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=600, height=350)
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Node Array Import")
        row = col.row()
        row.prop(self, "game_mode")
        
#----------------------------------------------------------------------------------
class THUGUtilFillVehicles(bpy.types.Operator):
    bl_idname = "io.import_thug_util_fillvehicles"
    bl_label = "Auto-Fill Vehicles"
    # bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Fills a selection (or all) vehicle objects with default settings for THUG1/2/PRO."
    game_mode = EnumProperty(items=(
        ("THUG1", "THUG1", ""),
        ("THUG2", "THUG2/PRO", ""),
        ), name="Target Game", default="THUG1")

    def execute(self, context):
        vehs = [o for o in bpy.data.objects if o.type == 'EMPTY' and o.thug_empty_props.empty_type == 'Vehicle' ]
        for veh in vehs:
            veh.thug_veh_props.veh_type = 'Generic'
            veh.thug_veh_props.veh_model = 'veh\\Veh_DCShoeTruck\\Veh_DCShoeTruck.mdl'
            veh.thug_veh_props.veh_skeleton = 'car'
            veh.thug_veh_props.veh_suspend = 108000
            veh.thug_veh_props.veh_norail = False
            veh.thug_veh_props.veh_noskitch = False
            veh.thug_veh_props.veh_usemodellights = False
            veh.thug_veh_props.veh_allowreplacetex = False
            
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        vehs = [o for o in bpy.data.objects if o.type == 'EMPTY' and o.thug_empty_props.empty_type == 'Vehicle' ]
        return len(vehs) > 0
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=600, height=350)
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Node Array Import")
        row = col.row()
        row.prop(self, "game_mode")


#----------------------------------------------------------------------------------
class THUGUtilBatchTerrain(bpy.types.Operator):
    bl_idname = "io.import_thug_util_batchterrain"
    bl_label = "Batch Terrain"
    # bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Sets the terrain type on all faces for all selected objects."
    terrain_type = EnumProperty(
        name="Terrain Type",
        items=[(t, t, t) for t in ["Auto"] + TERRAIN_TYPES], 
        description="Terrain type to set.")

    def execute(self, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        for ob in meshes:
            bpy.context.scene.objects.active = ob
            bpy.ops.object.select_all(action='DESELECT')
            ob.select = True
            bpy.ops.object.editmode_toggle()
            bpy.ops.mesh.select_all(action='SELECT')
            bm = bmesh.from_edit_mesh(ob.data)
            ttl = bm.faces.layers.int.get("terrain_type")
            if not ttl:
                ttl = bm.faces.layers.int.new("terrain_type")
            for face in bm.faces:
                #if not face.select:
                #    continue
                if self.terrain_type == "Auto":
                    face[ttl] = AUTORAIL_AUTO
                else:
                    face[ttl] = TERRAIN_TYPES.index(self.terrain_type)
            bmesh.update_edit_mesh(context.edit_object.data)
            bpy.ops.object.editmode_toggle()
            ob.select = False
            
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        return len(meshes) > 0
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=600, height=250)
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        #col.label(text="Node Array Import")
        row = col.row()
        row.prop(self, "terrain_type")


#----------------------------------------------------------------------------------
class THUGUtilBatchRailTerrain(bpy.types.Operator):
    bl_idname = "io.import_thug_util_batchrailterrain"
    bl_label = "Set Rail Terrain"
    # bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Sets the terrain type on all points for the selected rails."
    terrain_type = EnumProperty(
        name="Terrain Type",
        items=[(t, t, t) for t in ["None", "Auto"] + [tt for tt in TERRAIN_TYPES if tt.lower().startswith("grind")]],
        description="Terrain type to set.")

    def execute(self, context):
        curves = [o for o in context.selected_objects if o.type == 'CURVE' and o.thug_path_type != ""]
        for ob in curves:
            ob.thug_rail_terrain_type = self.terrain_type
            # Set the terrain on any points with terrain defined
            for spline in ob.data.splines:
                points = spline.points
                point_count = len(points)
                p_num = -1
                for point in points:
                    p_num += 1
                    if len(ob.data.thug_pathnode_triggers) > p_num and ob.data.thug_pathnode_triggers[p_num].terrain != "Auto" and ob.data.thug_pathnode_triggers[p_num].terrain != "None":
                        ob.data.thug_pathnode_triggers[p_num].terrain = self.terrain_type
            
            
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        meshes = [o for o in context.selected_objects if o.type == 'CURVE']
        return len(meshes) > 0
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=600, height=250)
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row()
        row.prop(self, "terrain_type")

#----------------------------------------------------------------------------------
class THUGUtilBatchObjectProps(bpy.types.Operator):
    bl_idname = "io.import_thug_util_batchobjprops"
    bl_label = "Batch Object Properties"
    # bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Apples a selection of properties on all selected objects."
    
    # Basic object properties
    thug_created_at_start = EnumProperty(name="Created At Start", items=[
        ("NULL", " --- ", "This property will not be modified."),
        ("True", "Yes", ""),
        ("False", "No", "")
    ], default="NULL")
    thug_network_option = EnumProperty(name="Network Options", items=[
            ("NULL", " --- ", "This property will not be modified."),
            ("Default", "Default", "Appears in network games."),
            ("AbsentInNetGames", "Offline Only", "Only appears in single-player."),
            ("NetEnabled", "Online (Broadcast)", "Appears in network games, events/scripts appear on all clients.")],
        default="NULL")
    thug_export_collision = EnumProperty(name="Export to Collisions", items=[
        ("NULL", " --- ", "This property will not be modified."),
        ("True", "Yes", ""),
        ("False", "No", "")
    ], default="NULL")
    thug_export_scene = EnumProperty(name="Export to Scene", items=[
        ("NULL", " --- ", "This property will not be modified."),
        ("True", "Yes", ""),
        ("False", "No", "")
    ], default="NULL")
    thug_lightgroup = EnumProperty(name="Light Group", items=[
            ("NULL", " --- ", "This property will not be modified."),
            ("None", "None", ""),
            ("Outdoor", "Outdoor", ""),
            ("NoLevelLights", "NoLevelLights", ""),
            ("Indoor", "Indoor", "")],
        default="NULL")
    thug_is_trickobject = EnumProperty(name="Is a TrickObject", items=[
        ("NULL", " --- ", "This property will not be modified."),
        ("True", "Yes", ""),
        ("False", "No", "")
    ], default="NULL")
    thug_cluster_name = StringProperty(name="TrickObject Cluster")
        
    # TriggerScript properties
    triggerscript_type = EnumProperty(items=(
        ("NULL", " --- ", "This property will not be modified."),
        ("None", "None", ""),
        ("Killskater", "Killskater", "Bail the skater and restart them at the given node."),
        ("Killskater_Water", "Killskater (Water)", "Bail the skater and restart them at the given node."),
        ("Teleport", "Teleport", "Teleport the skater to a given node without breaking their combo."),
        ("Custom", "Custom", "Runs a custom script."),
        ), name="TriggerScript Type", default="NULL")
    target_node = StringProperty(name="Target Node")
    custom_name = StringProperty(name="Custom Script Name")

    def execute(self, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH' or o.type == 'CURVE']
        for ob in meshes:
            if self.thug_created_at_start != "NULL":
                print("Updating thug_created_at_start for object {}...".format(ob.name))
                ob.thug_created_at_start = (self.thug_created_at_start == "True")
            if self.thug_network_option != "NULL":
                print("Updating thug_network_option for object {}...".format(ob.name))
                ob.thug_network_option = self.thug_network_option
                
            # Mesh-only properties start here!
            if ob.type == 'MESH':
                if self.thug_export_collision != "NULL":
                    print("Updating thug_export_collision for object {}...".format(ob.name))
                    ob.thug_export_collision = (self.thug_export_collision == "True")
                if self.thug_export_scene != "NULL":
                    print("Updating thug_export_scene for object {}...".format(ob.name))
                    ob.thug_export_scene = (self.thug_export_scene == "True")
                if self.thug_lightgroup != "NULL":
                    print("Updating thug_lightgroup for object {}...".format(ob.name))
                    ob.thug_lightgroup = self.thug_lightgroup
            # Mesh-only properties end here!
            
            if self.thug_is_trickobject != "NULL":
                print("Updating thug_is_trickobject for object {}...".format(ob.name))
                ob.thug_is_trickobject = (self.thug_is_trickobject == "True")
                if self.thug_is_trickobject == "True":
                    print("Updating thug_cluster_name for object {}...".format(ob.name))
                    ob.thug_cluster_name = self.thug_cluster_name
                    
            # TriggerScript props
            if self.triggerscript_type != "NULL":
                print("Updating triggerscript_type for object {}...".format(ob.name))
                ob.thug_triggerscript_props.triggerscript_type = self.triggerscript_type
                if self.triggerscript_type == "Custom":
                    print("Updating custom_name for object {}...".format(ob.name))
                    ob.thug_triggerscript_props.custom_name = self.custom_name
                elif self.triggerscript_type != "None":
                    print("Updating target_node for object {}...".format(ob.name))
                    ob.thug_triggerscript_props.target_node = self.target_node
                    
            
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH' or o.type == 'CURVE']
        return len(meshes) > 0
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=800, height=350)
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="                                        ")
        col.row().prop(self, "thug_created_at_start")
        col.row().prop(self, "thug_network_option")
        col.row().prop(self, "thug_export_collision")
        col.row().prop(self, "thug_export_scene")
        col.row().prop(self, "thug_lightgroup")
        col.row().prop(self, "thug_is_trickobject")
        col.row().prop(self, "thug_cluster_name")
        col.row().prop(self, "triggerscript_type")
        col.row().prop_search(
                self,
                "target_node",
                context.window_manager,
                "thug_all_restarts")
        col.row().prop_search(
                self, "custom_name",
                bpy.data,
                "texts")


# PANELS
#############################################
#----------------------------------------------------------------------------------
class THUGObjectUtils(bpy.types.Panel):
    bl_label = "TH Object Utilities"
    bl_region_type = "TOOLS"
    bl_space_type = "VIEW_3D"
    bl_category = "THUG Tools"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        if not context.scene: return
        scene = context.scene
        self.layout.row().operator(THUGUtilFillPedestrians.bl_idname, THUGUtilFillPedestrians.bl_label, icon="TEXT")
        self.layout.row().operator(THUGUtilFillVehicles.bl_idname, THUGUtilFillVehicles.bl_label, icon="TEXT")
        self.layout.row().operator(THUGUtilBatchTerrain.bl_idname, THUGUtilBatchTerrain.bl_label, icon="TEXT")
        self.layout.row().operator(THUGUtilBatchRailTerrain.bl_idname, THUGUtilBatchRailTerrain.bl_label, icon="TEXT")
        self.layout.row().operator(THUGUtilBatchObjectProps.bl_idname, THUGUtilBatchObjectProps.bl_label, icon="TEXT")
        self.layout.row().operator(THUGUtilShowFirstPoint.bl_idname, THUGUtilShowFirstPoint.bl_label, icon="TEXT")