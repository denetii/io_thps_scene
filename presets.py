#############################################
# OBJECT PRESETS
# Handles the generation of TH engine presets
# - nodes, objects, CAP pieces, etc
#############################################
import bpy
import bmesh
import struct
import mathutils
import math
from bpy.props import *
from . helpers import *
from . material import *
from . pieces import *
from . autorail import *
import fnmatch

# Park piece rotation constants
ROTATE_0 = 0
ROTATE_90 = 1
ROTATE_180 = 2
ROTATE_270 = 3

# METHODS
#############################################
def preset_place_node(node_type, position):
    scene = bpy.context.scene
    bpy.ops.object.select_all(action='DESELECT')
    print("Placing a {}".format(node_type))
    # Create a new Empty, which we will fill in with TH specific data
    ob = bpy.data.objects.new( "empty", None ) 
    ob.location = position
    if node_type == 'RESTART':
        ob.name = 'TRG_Restart'
        ob.thug_empty_props.empty_type = 'Restart'
        ob.thug_restart_props.restart_type = "Player1"
        ob.thug_restart_props.restart_p1 = True
        scene.objects.link( ob )
        scene.objects.active = ob 
        ob.select = True
        to_group(ob, "Restarts")
        
    elif node_type == 'KOTH_CROWN':
        ob.name = 'TRG_KOTH'
        ob.thug_empty_props.empty_type = "GenericNode"
        ob.thug_generic_props.generic_type = "Crown"
        scene.objects.link( ob )
        scene.objects.active = ob 
        ob.select = True
        to_group(ob, "GenericNodes")
        
    elif node_type == 'PEDESTRIAN':
        ob.name = 'TRG_Pedestrian'
        ob.thug_empty_props.empty_type = 'Pedestrian'
        ob.thug_ped_props.ped_type = "Ped_From_Profile"
        ob.thug_ped_props.ped_source = "Profile"
        ob.thug_ped_props.ped_profile = "random_male_profile"
        ob.thug_ped_props.ped_skeleton = "THPS5_human"
        ob.thug_ped_props.ped_animset = "animload_THPS5_human"
        scene.objects.link( ob )
        scene.objects.active = ob 
        ob.select = True
        to_group(ob, "Pedestrians")
        
    elif node_type == 'VEHICLE':
        ob.name = 'TRG_Vehicle'
        ob.thug_empty_props.empty_type = 'Vehicle'
        ob.thug_veh_props.veh_type = "Generic"
        scene.objects.link( ob )
        scene.objects.active = ob 
        ob.select = True
        to_group(ob, "Vehicles")
        
    elif node_type == 'GAMEOBJECT':
        ob.name = 'TRG_GO'
        ob.thug_empty_props.empty_type = 'GameObject'
        ob.thug_go_props.go_type = "Ghost"
        scene.objects.link( ob )
        scene.objects.active = ob 
        ob.select = True
        to_group(ob, "GameObjects")
        
    elif node_type == 'RAIL_NODE' or node_type == 'RAIL_PREMADE':
        rail_path_name = "TRG_RailPath0"
        rail_name_idx = 0
        # Create new rail path
        while rail_path_name in bpy.data.objects:
            rail_name_idx += 1
            rail_path_name = "TRG_RailPath" + str(rail_name_idx)
        curveData = bpy.data.curves.new(rail_path_name, type='CURVE')
        curveData.dimensions = '3D'
        curveData.resolution_u = 12
        curveData.bevel_depth = 2
        # map coords to spline
        polyline = curveData.splines.new('POLY')
        polyline.points.add(1)
        rail_pos = mathutils.Vector([position[0], position[1], position[2], 0])
        polyline.points[0].co = rail_pos + mathutils.Vector([ 0, 0, 0, 0])
        polyline.points[1].co = rail_pos + mathutils.Vector([ 0, 500, 0, 0])
        
        curveOB = bpy.data.objects.new(rail_path_name, curveData)
        curveOB.thug_path_type = "Rail"
        curveOB.thug_rail_terrain_type = "GRINDMETAL"
        curveOB.data.thug_pathnode_triggers.add()
        curveOB.data.thug_pathnode_triggers.add()
        # attach to scene and validate context
        scene.objects.link(curveOB)
        scene.objects.active = curveOB
        curveOB.select = True
        to_group(curveOB, "RailNodes")
        if node_type == 'RAIL_PREMADE':
            build_rail_mesh(curveOB)
    
    elif node_type == 'WAYPOINT':
        path_name = "TRG_Waypoint"
        curveData = bpy.data.curves.new(path_name, type='CURVE')
        curveData.dimensions = '3D'
        curveData.resolution_u = 12
        curveData.bevel_depth = 2
        # map coords to spline
        polyline = curveData.splines.new('POLY')
        polyline.points.add(1)
        rail_pos = mathutils.Vector([position[0], position[1], position[2], 0])
        polyline.points[0].co = rail_pos + mathutils.Vector([ 0, 0, 0, 0])
        polyline.points[1].co = rail_pos + mathutils.Vector([ 0, 500, 0, 0])
        
        curveOB = bpy.data.objects.new(path_name, curveData)
        curveOB.thug_path_type = "Waypoint"
        curveOB.data.thug_pathnode_triggers.add()
        curveOB.data.thug_pathnode_triggers.add()
        # attach to scene and validate context
        scene.objects.link(curveOB)
        scene.objects.active = curveOB
        curveOB.select = True
        to_group(curveOB, "Waypoints")
        

def preset_place_mesh(piece_name, position):
    scene = bpy.context.scene
    bpy.ops.object.select_all(action='DESELECT')
    piece_search = [obj for obj in scene.objects if fnmatch.fnmatch(obj.name, piece_name)]
    if not piece_search:
        print("Piece {} not found in scene.".format(piece_name))
        return
    source_piece = piece_search[0]
    new_piece = source_piece.copy()
    new_piece.data = source_piece.data.copy()
    new_piece.location = position
    new_piece.hide = False
    new_piece.hide_render = False
    new_piece.thug_export_scene = True
    new_piece.thug_export_collision = True
    scene.objects.link(new_piece)
    scene.objects.active = new_piece
    new_piece.select = True
    return new_piece
    
def preset_place_compositeobject(piece_name):
    piece_data = {}
    found = False
    pieces = []
    for ob in Ed_Pieces_UG1:
        # Single object definitions don't use "single" for the mesh name
        if "single" in ob and ob["single"] == piece_name:
            found = True
            piece = {}
            piece["name"] = ob["single"]
            if "pos" in ob:
                piece["pos"] = ob["pos"]
            else:
                piece["pos"] = [0,0,0]
            if "is_riser" in ob:
                piece["riser"] = 1
            pieces.append(piece)
            break
            
        # Multi-object composites have a "name" property we can look up
        elif "name" in ob and ob["name"] == piece_name:
            found = True
            piece_data["name"] = piece_name
        
            for cob in ob["multiple"]:
                piece = {}
                piece["name"] = cob["name"]
                if "pos" in cob:
                    piece["pos"] = cob["pos"]
                else:
                    piece["pos"] = [0,0,0]
                pieces.append(piece)
                        
    if not found:
        raise Exception("Unable to find object {} in piece list.".format(piece_name))
    
    piece_data["pieces"] = pieces
    return piece_data

    
#----------------------------------------------------------------------------------
preset_node_list = [
    { 'name': 'RESTART', 'title': 'Restart', 'desc': 'Add a restart point.' },
    { 'name': 'KOTH_CROWN', 'title': 'KOTH Crown', 'desc': 'Add a crown for KOTH games.' },
    { 'name': 'PEDESTRIAN', 'title': 'Pedestrian', 'desc': 'Add a new pedestrian.' },
    { 'name': 'VEHICLE', 'title': 'Vehicle', 'desc': 'Add a new vehicle.' },
    { 'name': 'RAIL_NODE', 'title': 'Rail Node', 'desc': 'Add a new rail with 2 points (no mesh).' },
    { 'name': 'RAIL_PREMADE', 'title': 'Premade Rail', 'desc': 'Add a new rail with 2 points and mesh.' },
    { 'name': 'WAYPOINT', 'title': 'Waypoint', 'desc': 'Add a waypoint path with 2 points.' },
    { 'name': 'GAMEOBJECT', 'title': 'GameObject', 'desc': 'Add a new GameObject.' },
]

# this holds the custom operators so we can cleanup when turned off
preset_nodes = []
preset_mesh = []

def addPresetNodes():
    for node in preset_node_list:
        op_name = 'object.add_custom_' + node['name'].lower()
        nc = type(  'DynOp_' + node['name'],
                    (AddTHUGNode, ),
                    {'bl_idname': op_name,
                    'bl_label': node['title'],
                    'bl_description': node['desc'],
                    'node_type': node['name']
                })
        preset_nodes.append(nc)
        bpy.utils.register_class(nc)

def addPresetMesh():
    for ob in Ed_Pieces_UG1:
        # Single object definitions don't use "single" for the mesh name
        if "single" in ob:
            piece_name = ob["single"]
            #piece_search = [obj for obj in bpy.context.scene if fnmatch.fnmatch(obj.name, piece_name)]
            #if not piece_search:
            #    continue
                
            op_name = 'object.add_custom_' + ob["single"].lower()
            op_label = ob["single"]
            if "text_name" in ob:
                op_label = ob["text_name"]
            
            nc = type(  'DynOp_' + ob["single"],
                        (AddTHUGMesh, ),
                        {'bl_idname': op_name,
                        'bl_label': op_label,
                        'bl_description': 'Add this piece to the scene.',
                        'piece_name': ob["single"]
                    })
            preset_mesh.append(nc)
            bpy.utils.register_class(nc)

def clearPresetNodes():
    for c in preset_nodes:
        bpy.utils.unregister_class(c)
        
def clearPresetMesh():
    for c in preset_nodes:
        bpy.utils.unregister_class(c)

# OPERATORS
#############################################
class AddTHUGNode(bpy.types.Operator):
    bl_idname = "mesh.thug_preset_addnode"
    bl_label = "Add Node"
    bl_description = "Base operator for adding custom objects"
    bl_options = {'REGISTER', 'UNDO'}

    node_type = bpy.props.StringProperty()

    def execute(self, context):
        preset_place_node(self.node_type, bpy.context.scene.cursor_location)
        return {'FINISHED'}
        
class AddTHUGMesh(bpy.types.Operator):
    bl_idname = "mesh.thug_preset_addmesh"
    bl_label = "Add Mesh"
    bl_description = "Base operator for adding custom mesh (usually CAP pieces)"
    bl_options = {'REGISTER', 'UNDO'}

    piece_name = bpy.props.StringProperty()

    def execute(self, context):
        preset_place_mesh(self.piece_name, bpy.context.scene.cursor_location)
        return {'FINISHED'}


# MENUS
#############################################
class THUGNodesMenu(bpy.types.Menu):
    bl_label = 'Nodes'
    bl_idname = 'mesh.thug_preset_nodes'

    def draw(self, context):
        layout = self.layout
        #layout.row().label("This is a submenu")
        for o in preset_nodes:
            layout.operator(o.bl_idname)
            
class THUGMeshMenu(bpy.types.Menu):
    bl_label = 'Objects'
    bl_idname = 'mesh.thug_preset_pieces'

    def draw(self, context):
        print("drawing mesh menu")
        layout = self.layout
        #layout.row().label("This is a submenu")
        for o in preset_mesh:
            piece_search = [obj for obj in bpy.data.objects if obj.type == 'MESH' and fnmatch.fnmatch(obj.name, o.piece_name)]
            if not piece_search:
                continue
            layout.operator(o.bl_idname, icon='OUTLINER_OB_ARMATURE')


class THUGPresetsMenu(bpy.types.Menu):
    bl_label = 'my materials'
    bl_idname = 'mesh.thug_presets'

    def draw(self, context):
        layout = self.layout

        #layout.label("This is a main menu")
        layout.row().menu(THUGNodesMenu.bl_idname)
        layout.row().menu(THUGMeshMenu.bl_idname)