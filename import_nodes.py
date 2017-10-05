#############################################
# NODEARRAY IMPORTER
#############################################
import bpy
from bpy.props import *
import bmesh
import struct
import mathutils
import math

# PROPERTIES
#############################################
linked_nodes = []
NodeArray = []
KeyTable = []
ncomp = []

# METHODS
#############################################
# duh!
def get_node(index):
    tmp_index = -1
    for node in NodeArray:
        tmp_index += 1
        if tmp_index == index:
            if "Index" not in node:
                node["Index"] = index
            return node
        
    raise Exception("Node index " + str(index) + " does not exist.")

def fill_ncomp_data(node):
    if "ncomp_filled" in node:
        return node
    ncomp_name = node["ncomp"]
    if ncomp_name in ncomp:
        for name, value in ncomp[ncomp_name].items():
            print("expanding " + str(name) + ": " + str(value))
            if name not in node:
                node[str(name)] = value
        node["ncomp_filled"] = 1
    return node
    
# Returns a set of all coordinates for a single rail
def get_linked_path(node, node_type):
    
    node_index = -1
    my_links = []
    point_coords = []
    point_names = []
    point_triggers = []
    is_circular = False
    
    # If the first RailNode has no links, then it might be a point rail
    if "Links" not in node:
        my_links.append(node["Index"])
        linked_nodes.append(node["Index"])
    else:
        next_node = node
        while True:
            #print("It cannot be this!")
            if "Class" in next_node and next_node["Class"] == node_type:
                my_links.append(next_node["Index"])
                linked_nodes.append(next_node["Index"])   
            else:
                # Invalid link?
                print("Invalid " + node_type + " link to node " + next_node["Name"] + " (idx: " + str(next_node["Index"]) + ")")
                break
                
            if "Links" in next_node:
                node_links = next_node["Links"]
                if node_links[0] in linked_nodes:
                    # Circular link, time to blast!
                    print("Circular link to " + node_type + " " + str(node_links[0]) + ", ending line!")
                    is_circular = True
                    break
                next_node = get_node(node_links[0])
            else:
                break
            
    # At this point, we should have all the forward links from the rail node we started from. 
    # But now let's look in reverse and see what links to the start of this path!
    line_continues = True
    while line_continues == True:
        node_index = -1
        link_found = False
        for no in NodeArray:
            if "ncomp" in no:
                no = fill_ncomp_data(no)
            node_index += 1
            if "Class" in no and no["Class"] == node_type and "Links" in no and my_links[0] in no["Links"] and node_index not in my_links:
                # Back link to the start of the path
                my_links.insert(0, node_index)
                linked_nodes.append(node_index)
                print("found rail backlink: " + no["Name"])
                link_found = True
        if link_found == False:
            # this should be the end of the line
            line_continues = False
            break
                
    if len(my_links) == 1:
        print("Point rail?")
        # If there are no links to this rail, it's a point rail!
    
    for idx in my_links:
        tmp_node = get_node(idx)
        if "Position" not in tmp_node:
            if "Pos" in tmp_node:
                tmp_node["Position"] = tmp_node["Pos"]
            else:
                raise Exception("linked node " + tmp_node["Name"] + " has no position!")
        point_coords.append(tmp_node["Position"])
        point_names.append(tmp_node["Name"])
        if "TriggerScript" in tmp_node:
            point_triggers.append(tmp_node["TriggerScript"])
        else:
            point_triggers.append("")
        
    node_path = [ point_coords, point_names, point_triggers, is_circular ]
    return node_path
        
#----------------------------------------------------------------------------------
#- Processes the node array found in the 'NodeArray' text block
#- 'gamemode' must be one of: 'THPS', 'THUG', 'THAW'
#----------------------------------------------------------------------------------
def import_nodearray(gamemode):
    if not 'NodeArray' in globals():
        raise Exception("Node array was not found!")
        
    node_index = -1
    linked_nodes.clear()
    
    # STEP 1 - RENAME OBJECTS TO THEIR PROPER NAMES FROM LEVEL .QB
    level_mesh = [o for o in bpy.data.objects if (o.type == "MESH")]
    for ob in level_mesh:
        if ob.name.startswith("scn_"):
            if ob.name[4:] in KeyTable:
                print("Renaming " + ob.name + " to scn_" + KeyTable[ob.name[4:]])
                ob.name = KeyTable[ob.name[4:]] + "_SCN"
            ob.thug_export_collision = False
            ob.thug_export_scene = True
                
        if ob.name.startswith("col_"):
            if ob.name[4:] in KeyTable:
                print("Renaming " + ob.name + " to scn_" + KeyTable[ob.name[4:]])
                # We want the collision mesh to have the exact name, no suffix
                ob.name = KeyTable[ob.name[4:]]
                ob.thug_always_export_to_nodearray = True # always export named collision!
            ob.thug_export_collision = True
            ob.thug_export_scene = False
            

    for node in NodeArray:
        node_index += 1
        node["Index"] = node_index
        if "Position" not in node:
            if "Pos" in node: # Newer games use Pos instead of Position
                node["Position"] = node["Pos"]
            else:
                raise Exception("Node " + node["Name"] + " has no position!")
        if "ncomp" in node:
            node = fill_ncomp_data(node)
            
        # STEP 2 - GENERATE RAIL NODES
        if "Class" in node and ( node["Class"] == "RailNode" or node["Class"] == "Waypoint" or node["Class"] == "ClimbingNode" ):
            if node["Index"] in linked_nodes:
                print(node["Class"] + " " + node["Name"] + "already used previously")
                continue
                
            rail_nodes = get_linked_path(node, node["Class"])
            if len(rail_nodes) < 1 or len(rail_nodes[0]) < 1: 
                print("Point rail")
                #continue
                
            rail_path_name = "TRG_" + node["Class"] + "Path0"
            rail_name_idx = 0
            # Create new rail path
            while rail_path_name in bpy.data.objects:
                rail_name_idx += 1
                rail_path_name = "TRG_" + node["Class"] + "Path" + str(rail_name_idx)
                #print("TRG_RailPath" + str(rail_name_idx))
            
            print("Creating rail " + node["Name"])
            curveData = bpy.data.curves.new(rail_path_name, type='CURVE')
            curveData.dimensions = '3D'
            curveData.resolution_u = 12
            curveData.bevel_depth = 1.0
            
            # map coords to spline
            polyline = curveData.splines.new('POLY')
            polyline.points.add(len(rail_nodes[0]) - 1)
            for i, coord in enumerate(rail_nodes[0]):
                print("Adding point " + str(i))
                x,y,z = coord
                if gamemode == 'THAW':
                    polyline.points[i].co = (x, -z, y, 1)
                else:
                    polyline.points[i].co = (x, z, y, 1)
                    

            if rail_nodes[3] == True: # is_circular = True  
                polyline.use_endpoint_u = True
                polyline.use_cyclic_u = True  
            # create Object
            curveOB = bpy.data.objects.new(node["Name"], curveData)
            for i, coord in enumerate(rail_nodes[0]):
                curveOB.data.thug_pathnode_triggers.add()
            
            for i, nm in enumerate(rail_nodes[1]):
                curveOB.data.thug_pathnode_triggers[i].name = nm
                
            for i, ts in enumerate(rail_nodes[2]):
                curveOB.data.thug_pathnode_triggers[i].script_name = ts
                if ts != "":
                    script_text = bpy.data.texts.get("THUG_SCRIPTS", None)
                    if not script_text:
                        script_text = bpy.data.texts.new(name="THUG_SCRIPTS")
                    script_text.write(":i function $" + ts + "$\n")
                    script_text.write(":i endfunction\n")
                
            #curveData.bevel_depth = 0.01
            if node["Class"] == "RailNode":
                curveOB.thug_path_type = "Rail"
                if "TerrainType" in node:
                    try:
                        curveOB.thug_rail_terrain_type = str(node["TerrainType"]).replace("TERRAIN_", "")
                    except TypeError:
                        curveOB.thug_rail_terrain_type = "Auto"
            elif node["Class"] == "Waypoint":
                curveOB.thug_path_type = "Waypoint"
                
            elif node["Class"] == "ClimbingNode":
                curveOB.thug_path_type = "Ladder"
            
            else:
                # The importer is meant for THPS3/4 levels, so ClimbingNodes are not currently implemented
                # but the paths should still be created for you
                curveOB.thug_path_type = "Custom"
                
            if "TrickObject" in node:
                curveOB.thug_is_trickobject = True
                if "Cluster" in node:
                    curveOB.thug_cluster_name = node["Cluster"]

            # attach to scene and validate context
            scn = bpy.context.scene
            scn.objects.link(curveOB)
            scn.objects.active = curveOB
            
        # STEP 3 - ATTACH TRIGGERSCRIPTS/FLAGS TO MESH, CREATE EMPTY NODES
        if "Name" in node and "Class" in node:
            node_name = node["Name"]
            
            # Create object if it doesn't exist (should be vehicles, pedestrians, restarts etc)
            if not bpy.data.objects.get(node_name):
                ob = bpy.data.objects.new( "empty", None )
                bpy.context.scene.objects.link( ob )
                if node["Class"] == "GameObject":
                    ob.empty_draw_type = 'CUBE'
                    ob.empty_draw_size = 64
                elif node["Class"] == "Pedestrian" or node["Class"] == "Vehicle":
                    ob.empty_draw_type = 'PLAIN_AXES'
                    ob.empty_draw_size = 108
                elif node["Class"] == "EnvironmentObject" or node["Class"] == "LevelGeometry" or node["Class"] == "LevelObject":
                    ob.empty_draw_type = 'CONE'
                    ob.empty_draw_size = 32
                elif node["Class"] == "BouncyObject":
                    ob.empty_draw_type = 'CUBE'
                    ob.empty_draw_size = 32
                elif node["Class"] == "ProximNode":
                    ob.empty_draw_type = 'SPHERE'
                    if "radius" in node:
                        ob.empty_draw_size = node["radius"]
                    else:
                        ob.empty_draw_size = 150
                    
                elif node["Class"] == "GenericNode":
                    ob.empty_draw_type = 'CIRCLE'
                    ob.empty_draw_size = 32
                else:
                    ob.empty_draw_type = 'ARROWS'
                    ob.empty_draw_size = 108
                ob.location[0] = node["Position"][0]
                if gamemode == 'THAW':
                    ob.location[1] = -node["Position"][2]
                else:
                    ob.location[1] = node["Position"][2]
                ob.location[2] = node["Position"][1]
                
                ob.rotation_euler[0] = node["Angles"][0]
                if gamemode == 'THAW':
                    ob.rotation_euler[1] = -node["Angles"][2]
                else:
                    ob.rotation_euler[1] = node["Angles"][2]
                ob.rotation_euler[2] = node["Angles"][1]
                ob.name = node["Name"]
            
            print("Updating node: " + node_name)
            if bpy.data.objects.get(node["Name"]):
                ob = bpy.data.objects.get(node["Name"])
                
                if node["Class"] == "RailNode" or node["Class"] == "Waypoint":
                    # Rail nodes and waypoints were already created earlier
                    continue
                if "Occluder" in node:
                    ob.thug_occluder = True
                if "CreatedAtStart" in node:
                    print("CreatedAtStart")
                    ob.thug_created_at_start = True
                else:
                    ob.thug_created_at_start = False
                    
                if "AbsentInNetGames" in node:
                    print("AbsentInNetGames")
                    ob.thug_network_option = "AbsentInNetGames"
                elif "NetEnabled" in node:
                    ob.thug_network_option = "NetEnabled"
                else:
                    ob.thug_network_option = "Default"
                    
                if node["Class"] == "LevelGeometry" or node["Class"] == "EnvironmentObject":
                    ob.thug_object_class = "LevelGeometry"
                elif node["Class"] == "LevelObject":
                    ob.thug_object_class = "LevelObject"
                elif node["Class"] == "Restart":
                    ob.thug_empty_props.empty_type = "Restart"
                    if "Type" in node:
                        if node["Type"] == "Player1":
                            ob.thug_restart_props.restart_type = "Player1"
                            ob.thug_restart_props.restart_p1 = True
                        elif node["Type"] == "Player2":
                            ob.thug_restart_props.restart_type = "Player2"
                            ob.thug_restart_props.restart_p2 = True
                        elif node["Type"] == "Multiplayer":
                            ob.thug_restart_props.restart_type = "Multiplayer"
                            ob.thug_restart_props.restart_multi = True
                        elif node["Type"] == "Team":
                            ob.thug_restart_props.restart_type = "Team"
                            ob.thug_restart_props.restart_team = True
                        elif node["Type"] == "Generic":
                            ob.thug_restart_props.restart_type = "Generic"
                            ob.thug_restart_props.restart_gen = True
                        elif node["Type"] == "Horse":
                            ob.thug_restart_props.restart_type = "Horse"
                            ob.thug_restart_props.restart_horse = True
                        elif node["Type"] == "CTF":
                            ob.thug_restart_props.restart_type = "CTF"
                            ob.thug_restart_props.restart_ctf = True
                        else:
                            ob.thug_restart_props.restart_type = "Generic"
                            ob.thug_restart_props.restart_generic = True
                    else:
                        ob.thug_restart_props.restart_type = "Generic"
                        ob.thug_restart_props.restart_generic = True
                        
                        
                    if "restart_types" in node:
                        for _type in node["restart_types"]:
                            if _type == "Player1":
                                ob.thug_restart_props.restart_p1 = True
                            elif _type == "Player2":
                                ob.thug_restart_props.restart_p2 = True
                            elif _type == "Multiplayer":
                                ob.thug_restart_props.restart_multi = True
                            elif _type == "Team":
                                ob.thug_restart_props.restart_team = True
                            elif _type == "Generic":
                                ob.thug_restart_props.restart_gen = True
                            elif _type == "Horse":
                                ob.thug_restart_props.restart_horse = True
                            elif _type == "CTF":
                                ob.thug_restart_props.restart_ctf = True

                    if "RestartName" in node:
                        ob.thug_restart_props.restart_name = node["RestartName"]
                            
                elif node["Class"] == "ProximNode":
                    ob.thug_empty_props.empty_type = "ProximNode"
                    if "Type" in node:
                        if node["Type"] in ("Camera", "Other"):
                            ob.thug_proxim_props.proxim_type = node["Type"]
                        else:
                            ob.thug_proxim_props.proxim_type = "Camera"
                            
                    if "radius" in node:
                        ob.thug_proxim_props.radius = node["radius"]
                    
                elif node["Class"] == "Pedestrian":
                    ob.thug_empty_props.empty_type = "Pedestrian"
                    # more stuff goes here later!
                    
                elif node["Class"] == "Vehicle":
                    ob.thug_empty_props.empty_type = "Vehicle"
                    # more stuff goes here later!
                    
                elif node["Class"] == "GameObject":
                    try:
                        ob.thug_empty_props.empty_type = "GameObject"
                        if "Type" in node:
                            ob.thug_go_props.go_type = node["Type"]
                        if "Model" in node:
                            ob.thug_go_props.go_model = node["Model"]
                        if "SuspendDistance" in node:
                            ob.thug_go_props.go_suspend = node["SuspendDistance"]
                        # more stuff goes here later!
                    except TypeError:
                        print("Game object " + node["Name"] + " was invalid.")
                    
                elif node["Class"] == "GenericNode":
                    ob.thug_empty_props.empty_type = "GenericNode"
                    if "Type" in node:
                        try:
                            ob.thug_generic_props.generic_type = node["Type"]
                        except TypeError:
                            print("Node " + node["Name"] + " had an invalid generic node type!")
                    # more stuff goes here later!
                    
                elif node["Class"] == "BouncyObject":
                    ob.thug_empty_props.empty_type = "BouncyObject"
                    
                if "TriggerScript" in node:
                    ob.thug_triggerscript_props.triggerscript_type = "Custom"
                    ob.thug_triggerscript_props.custom_name = node["TriggerScript"]
                    script_text = bpy.data.texts.get("THUG_SCRIPTS", None)
                    if not script_text:
                        script_text = bpy.data.texts.new(name="THUG_SCRIPTS")
                        
                    script_text.write(":i function $" + node["TriggerScript"] + "$\n")
                    script_text.write(":i endfunction\n")
                    
                if "TrickObject" in node:
                    ob.thug_is_trickobject = True
                if "Cluster" in node:
                    ob.thug_cluster_name = node["Cluster"]
                
            

# OPERATORS
#############################################
class THUGImportNodeArray(bpy.types.Operator):
    bl_idname = "io.import_thug_nodearray"
    bl_label = "Import NodeArray"
    # bl_options = {'REGISTER', 'UNDO'}
    game_mode = EnumProperty(items=(
        ("THPS", "THPS", "THPS3/4 games."),
        ("THUG", "THUG", "THUG1/2 games."),
        ("THAW", "THAW", "THAW and later games."),
        ), name="Game Mode", default="THUG")

    def execute(self, context):
        import_nodearray(self.game_mode)
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return "NodeArray" in bpy.data.texts
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Node Array Import")
        row = col.row()
        row.prop(self, "game_mode")