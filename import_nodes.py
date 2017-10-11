#############################################
# NODEARRAY IMPORTER
#############################################
import bpy
from bpy.props import *
import bmesh
import struct
import mathutils
import math
from . helpers import *


# PROPERTIES
#############################################
linked_nodes = []
NodeArray = []
KeyTable = []
ncomp = []

# METHODS
#############################################
#----------------------------------------------------------------------------------
#- Returns a node, given the node index
#----------------------------------------------------------------------------------
def get_node(index):
    tmp_index = -1
    for node in NodeArray:
        tmp_index += 1
        if tmp_index == index:
            if "Index" not in node:
                node["Index"] = index
            return fill_ncomp_data(node)
        
    raise Exception("Node index " + str(index) + " does not exist.")

#----------------------------------------------------------------------------------
#- Expands ncomp data into the node
#----------------------------------------------------------------------------------
def fill_ncomp_data(node):
    if "ncomp_filled" in node:
        return node
    
    ncomp_names = []
    for name, value in node.items():
        if name.startswith("ncomp_"):
            ncomp_names.append(name)
            
    for ncomp_name in ncomp_names:
        if ncomp_name in ncomp:
            for name, value in ncomp[ncomp_name].items():
                #print("expanding " + str(name) + ": " + str(value))
                if name not in node:
                    node[str(name)] = value
    node["ncomp_filled"] = 1
    return node
    
#----------------------------------------------------------------------------------
#- Returns a set of all coordinates for a single rail
#----------------------------------------------------------------------------------
def get_linked_path(node, node_type):
    
    node_index = -1
    my_links = []
    point_coords = []
    point_names = []
    point_triggers = []
    point_indices = []
    point_nodes = []
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
                print("Invalid link to node " + next_node["Name"] + " (idx: " + str(next_node["Index"]) + ", expecting " + node_type + ")")
                break
                
            if "Links" in next_node:
                node_links = next_node["Links"]
                if node_links[0] in my_links:
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
        for node in NodeArray:
            #if "ncomp" in no:
            no = fill_ncomp_data(node)
            node_index += 1
            if "Class" in no and no["Class"] == node_type and "Links" in no and my_links[0] in no["Links"] and node_index not in my_links:
                # Back link to the start of the path
                my_links.insert(0, node_index)
                linked_nodes.append(node_index)
                #print("found rail backlink: " + no["Name"])
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
                
        # Make sure there isn't already a point with the same position, or the game will crash!
        duplicate_pos = False
        for railpoint in point_coords:
            tmp_pos = tmp_node["Position"]
            if railpoint[0] == tmp_pos[0] and railpoint[1] == tmp_pos[1] and railpoint[2] == tmp_pos[2]:
                print("***********************************************")
                print("* Rail point already exists!")
                print("***********************************************")
                duplicate_pos = True
                break
        if duplicate_pos:
            print("Skipping...")
            continue
            
        point_coords.append(tmp_node["Position"])
        point_names.append(tmp_node["Name"])
        point_indices.append(tmp_node["Index"])
        point_nodes.append(tmp_node)
        #if "TriggerScript" in tmp_node:
        #    point_triggers.append(tmp_node["TriggerScript"])
        #else:
        #    point_triggers.append("")
        
    node_path = [ point_coords, point_names, point_nodes, is_circular, point_indices ]
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
    node_indices = []
    
    # STEP 1 - RENAME OBJECTS TO THEIR PROPER NAMES FROM LEVEL .QB
    level_mesh = [o for o in bpy.data.objects if (o.type == "MESH")]
    for ob in level_mesh:
        if ob.name.startswith("scn_"):
            if ob.name[4:] in KeyTable:
                print("Renaming " + ob.name + " to " + KeyTable[ob.name[4:]] + "_SCN")
                ob.name = KeyTable[ob.name[4:]] + "_SCN"
            ob.thug_export_collision = False
            ob.thug_export_scene = True
                
        if ob.name.startswith("col_"):
            if ob.name[4:] in KeyTable:
                print("Renaming " + ob.name + " to " + KeyTable[ob.name[4:]])
                # We want the collision mesh to have the exact name, no suffix
                ob.name = KeyTable[ob.name[4:]]
                ob.thug_always_export_to_nodearray = True # always export named collision!
            ob.thug_export_collision = True
            ob.thug_export_scene = False
            

    # STEP 2: FIRST PASS OF NODEARRAY
    for node in NodeArray:
        #print(str(node))
        node_index += 1
        node["Index"] = node_index
        if "Position" not in node:
            if "Pos" in node: # Newer games use Pos instead of Position
                node["Position"] = node["Pos"]
            else:
                raise Exception("Node " + node["Name"] + " has no position!")
        #if "ncomp" in node:
        node = fill_ncomp_data(node)
            
        # STEP 2A - GENERATE RAIL NODES
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
                #print("Adding point " + str(i))
                x,y,z = coord
                if gamemode == 'THAW':
                    polyline.points[i].co = (x, -z, y, 1)
                else:
                    polyline.points[i].co = (x, z, y, 1)
                    
            test_cyclic = False
            if rail_nodes[3] == True and len(polyline.points) > 2: # is_circular = True  
                polyline.use_endpoint_u = True
                polyline.use_cyclic_u = True  
                test_cyclic = True
                
            # Save the node indices of each point in our newly created Path
            # This lets us resolve links to the specific blender objects later
            node_indices.append({ 'name': node["Name"], 'indices': rail_nodes[4] })
            
            # create Object
            curveOB = bpy.data.objects.new(node["Name"], curveData)
            for i, coord in enumerate(rail_nodes[0]):
                curveOB.data.thug_pathnode_triggers.add()
            
            for i, nm in enumerate(rail_nodes[1]):
                curveOB.data.thug_pathnode_triggers[i].name = nm
                
            for i, _pnode in enumerate(rail_nodes[2]):
                if "TriggerScript" in _pnode and _pnode["TriggerScript"] != "":
                    # If there is a TriggerScript defined, assign to the blender obj and create text block if needed
                    curveOB.data.thug_pathnode_triggers[i].script_name = _pnode["TriggerScript"]
                    script_text = bpy.data.texts.get("script_" + _pnode["TriggerScript"], None)
                    if not script_text:
                        script_text = bpy.data.texts.new(name="script_" + _pnode["TriggerScript"])
                # Assign terrain type
                if "TerrainType" in _pnode and _pnode["TerrainType"] != "":
                    curveOB.data.thug_pathnode_triggers[i].terrain = _pnode["TerrainType"]
                        
                # Assign spawnobj script
                if "spawnobjscript" in _pnode and _pnode["spawnobjscript"] != "":
                    curveOB.data.thug_pathnode_triggers[i].spawnobjscript = _pnode["spawnobjscript"]
                    
                # Assign skater AI properties (if defined!)
                if "PedType" in _pnode and _pnode["PedType"] != "":
                    curveOB.data.thug_pathnode_triggers[i].PedType = _pnode["PedType"]
                if "Continue" in _pnode:
                    curveOB.data.thug_pathnode_triggers[i].do_continue = True
                if "JumpToNextNode" in _pnode:
                    curveOB.data.thug_pathnode_triggers[i].JumpToNextNode = True
                if "Priority" in _pnode and _pnode["Priority"] != "":
                    curveOB.data.thug_pathnode_triggers[i].Priority = _pnode["Priority"]
                if "ContinueWeight" in _pnode and _pnode["ContinueWeight"] != "":
                    curveOB.data.thug_pathnode_triggers[i].ContinueWeight = _pnode["ContinueWeight"]
                if "SkateAction" in _pnode and _pnode["SkateAction"] != "":
                    curveOB.data.thug_pathnode_triggers[i].SkateAction = _pnode["SkateAction"]
                if "JumpHeight" in _pnode and _pnode["JumpHeight"] != "":
                    curveOB.data.thug_pathnode_triggers[i].JumpHeight = _pnode["JumpHeight"]
                if "ManualType" in _pnode and _pnode["ManualType"] != "":
                    curveOB.data.thug_pathnode_triggers[i].ManualType = _pnode["ManualType"]
                if "Deceleration" in _pnode and _pnode["Deceleration"] != "":
                    curveOB.data.thug_pathnode_triggers[i].Deceleration = _pnode["Deceleration"]
                if "StopTime" in _pnode and _pnode["StopTime"] != "":
                    curveOB.data.thug_pathnode_triggers[i].StopTime = _pnode["StopTime"]
                if "SpinAngle" in _pnode and _pnode["SpinAngle"] != "":
                    curveOB.data.thug_pathnode_triggers[i].SpinAngle = _pnode["SpinAngle"]
                if "SpinDirection" in _pnode and _pnode["SpinDirection"] != "":
                    curveOB.data.thug_pathnode_triggers[i].SpinDirection = _pnode["SpinDirection"]
                
                        
            #curveData.bevel_depth = 0.01
            if node["Class"] == "RailNode":
                curveOB.thug_path_type = "Rail"
                if "TerrainType" in node:
                    try:
                        curveOB.thug_rail_terrain_type = str(node["TerrainType"]).replace("TERRAIN_", "")
                    except TypeError:
                        curveOB.thug_rail_terrain_type = "Auto"
                to_group(curveOB, "RailNodes")
                if test_cyclic:
                    to_group(curveOB, "Circular RailNodes")
                    
            elif node["Class"] == "Waypoint":
                curveOB.thug_path_type = "Waypoint"
                to_group(curveOB, "Waypoints")
                if test_cyclic:
                    to_group(curveOB, "Circular Waypoints")
                
            elif node["Class"] == "ClimbingNode":
                curveOB.thug_path_type = "Ladder"
                to_group(curveOB, "ClimbingNodes")
                if test_cyclic:
                    to_group(curveOB, "Circular ClimbingNodes")
            
            else:
                # The importer is meant for THPS3/4 levels, so ClimbingNodes are not currently implemented
                # but the paths should still be created for you
                curveOB.thug_path_type = "Custom"
                to_group(curveOB, "OtherPathNodes")
                
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
            
            # Proximity nodes generate an empty collision mesh for some reason,
            # so we have to remove that first or the actual proxim node won't be created
            if node["Class"] == "ProximNode" and bpy.data.objects.get(node_name):
                #bpy.data.objects.remove(bpy.data.objects[node_name], True)
                bpy.data.objects[node_name].name = bpy.data.objects[node_name].name + "_COL"
                
            # Same story for EmitterObjects
            elif node["Class"] == "EmitterObject" and bpy.data.objects.get(node_name):
                #bpy.data.objects.remove(bpy.data.objects[node_name], True)
                bpy.data.objects[node_name].name = bpy.data.objects[node_name].name + "_COL"
                
            # Create level lights - these are point lamps and not empties
            if node["Class"] == "LevelLight":
                lamp_data = bpy.data.lamps.new(name="Lamp_" + node["Name"], type='POINT')
                if "Brightness" in node:
                    if node["Brightness"] != 0:
                        lamp_data.energy = float(node["Brightness"])
                    else:
                        lamp_data.energy = 100.0
                        
                if "InnerRadius" in node:
                    lamp_data.thug_light_props.light_radius[0] = float(node["InnerRadius"])
                if "OuterRadius" in node:
                    lamp_data.thug_light_props.light_radius[1] = float(node["OuterRadius"])
                if "Color" in node:
                    lamp_data.color[0] = float(int(node["Color"][0]) / 256)
                    lamp_data.color[1] = float(int(node["Color"][1]) / 256)
                    lamp_data.color[2] = float(int(node["Color"][2]) / 256)
                if "ExcludeSkater" in node:
                    lamp_data.thug_light_props.light_excludeskater = True
                if "ExcludeLevel" in node:
                    lamp_data.thug_light_props.light_excludelevel = True
                    
                ob = bpy.data.objects.new(name=node["Name"], object_data=lamp_data )
                ob.location[0] = node["Position"][0]
                if gamemode == 'THAW':
                    ob.location[1] = -node["Position"][2]
                else:
                    ob.location[1] = node["Position"][2]
                ob.location[2] = node["Position"][1]
                bpy.context.scene.objects.link( ob )
                to_group(ob, "LevelLights")
                continue
            
            # Create object if it doesn't exist (should be vehicles, pedestrians, restarts etc)
            if not bpy.data.objects.get(node_name):
                ob = bpy.data.objects.new( "empty", None )
                bpy.context.scene.objects.link( ob )
                if node["Class"] == "GameObject":
                    ob.empty_draw_type = 'CUBE'
                    ob.empty_draw_size = 64
                    to_group(ob, "GameObjects")
                elif node["Class"] == "Pedestrian" or node["Class"] == "Vehicle":
                    ob.empty_draw_type = 'PLAIN_AXES'
                    ob.empty_draw_size = 108
                elif node["Class"] == "EnvironmentObject" or node["Class"] == "LevelGeometry" or node["Class"] == "LevelObject":
                    ob.empty_draw_type = 'CONE'
                    ob.empty_draw_size = 32
                elif node["Class"] == "BouncyObject":
                    ob.empty_draw_type = 'CUBE'
                    ob.empty_draw_size = 32
                    to_group(ob, "BouncyObjects")
                elif node["Class"] == "ParticleObject":
                    ob.empty_draw_type = 'IMAGE'
                    ob.empty_draw_size = 108
                    to_group(ob, "ParticleObjects")
                elif node["Class"] == "ProximNode":
                    ob.empty_draw_type = 'SPHERE'
                    if "radius" in node:
                        ob.empty_draw_size = node["radius"]
                    else:
                        ob.empty_draw_size = 150
                    to_group(ob, "ProximNodes")
                elif node["Class"] == "EmitterObject":
                    ob.empty_draw_type = 'SPHERE'
                    if "radius" in node:
                        ob.empty_draw_size = node["radius"]
                    else:
                        ob.empty_draw_size = 300
                    to_group(ob, "EmitterObjects")
                    
                elif node["Class"] == "GenericNode":
                    ob.empty_draw_type = 'CIRCLE'
                    ob.empty_draw_size = 32
                    to_group(ob, "GenericNodes")
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
                    to_group(ob, "Occluders")
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
                    if "LightGroup" in node and bpy.data.objects.get(node["Name"] + "_SCN"):
                        scn_ob = bpy.data.objects.get(node["Name"] + "_SCN")
                        scn_ob.thug_lightgroup = node["LightGroup"]
                        
                elif node["Class"] == "LevelObject":
                    ob.thug_object_class = "LevelObject"
                    if "LightGroup" in node and bpy.data.objects.get(node["Name"] + "_SCN"):
                        scn_ob = bpy.data.objects.get(node["Name"] + "_SCN")
                        scn_ob.thug_lightgroup = node["LightGroup"]
                    ob.location[0] = node["Position"][0]
                    # Reposition the LevelObject based on what is in the NodeArray
                    # When exported it is always at the origin
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
                    # Pull the _SCN mesh out and give it the same position
                    if bpy.data.objects.get(ob.name + "_SCN"):
                        ob2 = bpy.data.objects.get(ob.name + "_SCN")
                        ob2.location = ob.location
                        ob2.rotation_euler = ob.rotation_euler
                
                    # Process additional LevelObject properties, including bouncy mesh!
                    if "Type" in node:
                        ob.thug_levelobj_props.obj_type = node["Type"]
                    if "Bouncy" in node or "bouncy" in node:
                        ob.thug_levelobj_props.obj_bouncy = True
                    if "contacts" in node:
                        for _pos in node["contacts"]:
                            _contact = ob.thug_levelobj_props.contacts.add()
                            _contact.contact = _pos
                    if "center_of_mass" in node:
                        ob.thug_levelobj_props.center_of_mass = node["center_of_mass"]
                    if "coeff_restitution" in node:
                        ob.thug_levelobj_props.coeff_restitution = node["coeff_restitution"]
                    if "coeff_friction" in node:
                        ob.thug_levelobj_props.coeff_friction = node["coeff_friction"]
                    if "skater_collision_impulse_factor" in node:
                        ob.thug_levelobj_props.skater_collision_impulse_factor = node["skater_collision_impulse_factor"]
                    if "skater_collision_rotation_factor" in node:
                        ob.thug_levelobj_props.skater_collision_rotation_factor = node["skater_collision_rotation_factor"]
                    if "skater_collision_assent" in node:
                        ob.thug_levelobj_props.skater_collision_assent = node["skater_collision_assent"]
                    if "skater_collision_radius" in node:
                        ob.thug_levelobj_props.skater_collision_radius = node["skater_collision_radius"]
                    if "mass_over_moment" in node:
                        ob.thug_levelobj_props.mass_over_moment = node["mass_over_moment"]
                    if "stuckscript" in node:
                        if node["stuckscript"] != "":
                            script_text = bpy.data.texts.get("script_" + node["stuckscript"], None)
                            if not script_text:
                                script_text = bpy.data.texts.new(name="script_" + node["stuckscript"])
                        
                        ob.thug_levelobj_props.stuckscript = node["stuckscript"]
                        
                elif node["Class"] == "Restart":
                    to_group(ob, "Restarts")
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
                            elif _type == "MultiPlayer":
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
                        ob.thug_proxim_props.proxim_radius = node["radius"]
                    if "Shape" in node:
                        ob.thug_proxim_props.proxim_shape = node["Shape"]
                    if "RenderToViewport" in node:
                        ob.thug_proxim_props.proxim_rendertoviewport = True
                    if "SelectRenderOnly" in node:
                        ob.thug_proxim_props.proxim_selectrenderonly = True
                    if "ProximObject" in node:
                        ob.thug_proxim_props.proxim_object = True
                    
                elif node["Class"] == "EmitterObject":
                    ob.thug_empty_props.empty_type = "EmitterObject"
                    if "Type" in node:
                        ob.thug_emitter_props.emit_type = node["Type"]
                    if "radius" in node:
                        ob.thug_emitter_props.emit_radius = node["radius"]
                    
                elif node["Class"] == "ParticleObject":
                    ob.thug_empty_props.empty_type = "ParticleObject"
                    #ob.rotation_euler[0] = math.radians(90.0)
                    if "BoxDimsStart" in node:
                        ob.thug_particle_props.particle_boxdimsstart = from_thug_coords(node["BoxDimsStart"])
                    if "BoxDimsMid" in node:
                        ob.thug_particle_props.particle_boxdimsmid = from_thug_coords(node["BoxDimsMid"])
                    if "BoxDimsEnd" in node:
                        ob.thug_particle_props.particle_boxdimsend = from_thug_coords(node["BoxDimsEnd"])
                    if "UseStartPosition" in node:
                        ob.thug_particle_props.particle_usestartpos = node["UseStartPosition"]
                    if "StartPosition" in node:
                        ob.thug_particle_props.particle_startposition = from_thug_coords(node["StartPosition"])
                    if "MidPosition" in node:
                        ob.thug_particle_props.particle_midposition = from_thug_coords(node["MidPosition"])
                    if "EndPosition" in node:
                        ob.thug_particle_props.particle_endposition = from_thug_coords(node["EndPosition"])
                    if "Texture" in node:
                        tmp_texture_name = node["Texture"] #str(crc_from_string(bytes(node["Texture"], 'ascii')))
                        ob.thug_particle_props.particle_texture = tmp_texture_name
                        if tmp_texture_name in bpy.data.images:
                            ob.image = tmp_texture_name
                    if "Type" in node:
                        ob.thug_particle_props.particle_type = node["Type"]
                    if "BlendMode" in node:
                        ob.thug_particle_props.particle_blendmode = node["BlendMode"]
                    if "FixedAlpha" in node:
                        ob.thug_particle_props.particle_fixedalpha = node["FixedAlpha"]
                    if "AlphaCutoff" in node:
                        ob.thug_particle_props.particle_alphacutoff = node["AlphaCutoff"]
                    if "MaxStreams" in node:
                        ob.thug_particle_props.particle_maxstreams = node["MaxStreams"]
                    if "SuspendDistance" in node:
                        ob.thug_particle_props.particle_suspend = node["SuspendDistance"]
                    if "EmitRate" in node:
                        ob.thug_particle_props.particle_emitrate = node["EmitRate"]
                    if "Lifetime" in node:
                        ob.thug_particle_props.particle_lifetime = node["Lifetime"]
                    if "UseMidPoint"in node:
                        ob.thug_particle_props.particle_usemidpoint = node["UseMidPoint"]
                    if "MidPointPCT" in node:
                        ob.thug_particle_props.particle_midpointpct = node["MidPointPCT"]
                    if "StartRadius" in node:
                        ob.thug_particle_props.particle_radius[0] = node["StartRadius"]
                    if "MidRadius" in node:
                        ob.thug_particle_props.particle_radius[1] = node["MidRadius"]
                    if "EndRadius" in node:
                        ob.thug_particle_props.particle_radius[2] = node["EndRadius"]
                    if "StartRadiusSpread" in node:
                        ob.thug_particle_props.particle_radiusspread[0] = node["StartRadiusSpread"]
                    if "MidRadiusSpread" in node:
                        ob.thug_particle_props.particle_radiusspread[1] = node["MidRadiusSpread"]
                    if "EndRadiusSpread" in node:
                        ob.thug_particle_props.particle_radiusspread[2] = node["EndRadiusSpread"]
                    if "StartRGB" in node:
                        ob.thug_particle_props.particle_startcolor[0] = float(int(node["StartRGB"][0]) / 256)
                        ob.thug_particle_props.particle_startcolor[1] = float(int(node["StartRGB"][1]) / 256)
                        ob.thug_particle_props.particle_startcolor[2] = float(int(node["StartRGB"][2]) / 256)
                    if "StartAlpha" in node:
                        ob.thug_particle_props.particle_startcolor[3] = float(int(node["StartAlpha"]) / 256)
                    if "UseColorMidTime" in node:
                        ob.thug_particle_props.particle_usecolormidtime = node["UseColorMidTime"]
                    if "ColorMidTime" in node:
                        ob.thug_particle_props.particle_colormidtime = node["ColorMidTime"]
                    if "MidRGB" in node:
                        ob.thug_particle_props.particle_midcolor[0] = float(int(node["MidRGB"][0]) / 256)
                        ob.thug_particle_props.particle_midcolor[1] = float(int(node["MidRGB"][1]) / 256)
                        ob.thug_particle_props.particle_midcolor[2] = float(int(node["MidRGB"][2]) / 256)
                    if "MidAlpha" in node:
                        ob.thug_particle_props.particle_midcolor[3] = float(int(node["MidAlpha"]) / 256)
                    if "EndRGB" in node:
                        ob.thug_particle_props.particle_endcolor[0] = float(int(node["EndRGB"][0]) / 256)
                        ob.thug_particle_props.particle_endcolor[1] = float(int(node["EndRGB"][1]) / 256)
                        ob.thug_particle_props.particle_endcolor[2] = float(int(node["EndRGB"][2]) / 256)
                    if "EndAlpha" in node:
                        ob.thug_particle_props.particle_endcolor[3] = float(int(node["EndAlpha"]) / 256)
                    
                elif node["Class"] == "Pedestrian":
                    to_group(ob, "Pedestrians")
                    ob.thug_empty_props.empty_type = "Pedestrian"
                    if "Type" in node:
                        ob.thug_ped_props.ped_type = node["Type"]
                    if "profile" in node:
                        ob.thug_ped_props.ped_profile = node["profile"]
                    if "SuspendDistance" in node:
                        ob.thug_ped_props.ped_suspend = node["SuspendDistance"]
                    if "AnimName" in node:
                        ob.thug_ped_props.ped_animset = node["AnimName"]
                    if "Extra_Anims" in node:
                        ob.thug_ped_props.ped_extra_anims = node["Extra_Anims"]
                    if "SkeletonName" in node:
                        ob.thug_ped_props.ped_skeleton = node["SkeletonName"]
                    if "skeletonName" in node:
                        ob.thug_ped_props.ped_skeleton = node["skeletonName"]
                    
                elif node["Class"] == "Vehicle":
                    to_group(ob, "Vehicles")
                    ob.thug_empty_props.empty_type = "Vehicle"
                    if "Type" in node:
                        ob.thug_veh_props.veh_type = node["Type"]
                    if "model" in node:
                        ob.thug_veh_props.veh_model = node["model"]
                    if "SkeletonName" in node:
                        ob.thug_veh_props.veh_skeleton = node["SkeletonName"]
                    if "SuspendDistance" in node:
                        ob.thug_veh_props.veh_suspend = node["SuspendDistance"]
                    if "NoRail" in node:
                        ob.thug_veh_props.veh_norail = True
                    if "NoSkitch" in node:
                        ob.thug_veh_props.veh_noskitch = True
                    # more stuff goes here later!
                    
                elif node["Class"] == "GameObject":
                    try:
                        ob.thug_empty_props.empty_type = "GameObject"
                        if "Type" in node:
                            ob.thug_go_props.go_type = "Custom"
                            ob.thug_go_props.go_type_other = node["Type"]
                        if "model" in node:
                            ob.thug_go_props.go_model = node["model"]
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
                    ob.thug_triggerscript_props.custom_name = "script_" + node["TriggerScript"]
                    script_text = bpy.data.texts.get("script_" + node["TriggerScript"], None)
                    if not script_text:
                        script_text = bpy.data.texts.new(name="script_" + node["TriggerScript"])
                        
                    #script_text.write(":i function $" + node["TriggerScript"] + "$\n")
                    #script_text.write(":i endfunction\n")
                    
                if "TrickObject" in node:
                    ob.thug_is_trickobject = True
                if "Cluster" in node:
                    ob.thug_cluster_name = node["Cluster"]
     
    # STEP 4 - SECOND PASS OF NODEARRAY TO RESOLVE LINKS
    for node in NodeArray:           
        if "Links" in node and bpy.data.objects.get(node["Name"]):
            if "Class" in node and (node["Class"] == "RailNode" or node["Class"] == "ClimbingNode" or node["Class"] == "Waypoint"):
                continue
            
            ob = bpy.data.objects.get(node["Name"])
            for obj_index in node_indices:
                for _idx in obj_index['indices']:
                    if _idx == node["Links"][0]:
                        ob.thug_rail_connects_to = obj_index['name']
                        print("Object " + node["Name"] + " is linked to: " + obj_index['name'] + "(" + str(_idx) + ")")
        
        
def read_until(textblock, start_line, trigger):
    lines = []
    line_num = 0
    for line in textblock.lines:
        line_num += 1
        if line_num < start_line:
            continue
        if line.body.startswith(":i function "):
            continue
        if line.body.startswith(trigger):
            return lines
        lines.append(line)
    
def import_triggerscripts():
    old_scripts = bpy.data.texts.get("THUG_SCRIPTS")
    line_number = 0
    for line in old_scripts.lines:
        line_number += 1
        if line.body.startswith(":i function "):
            script_name = line.body.replace(":i function ", "").replace("$", "")
            print("Found script: " + script_name)
            script_text = read_until(old_scripts, line_number, ":i endfunction")
            if not bpy.data.texts.get("script_" + script_name, None):
                print("Writing script: " + script_name)
                script_block = bpy.data.texts.new(name="script_" + script_name)
                
                for script_line in script_text:
                    script_block.write(script_line.body + "\n")

# OPERATORS
#############################################
class THUGImportTriggerScripts(bpy.types.Operator):
    bl_idname = "io.import_thug_triggerscripts"
    bl_label = "Import TriggerScripts"
    import_type = EnumProperty(items=(
        ("ScriptsOnly", "Scripts only", "Copies scripts from THUG_SCRIPTS into individual text blocks (the new format)."),
        ("ScriptsAndObjects", "Scripts and objects", "Also updates object references to script names."),
        ), name="Import type", default="ScriptsOnly")
    # bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import_triggerscripts()
        if self.import_type == "ScriptsAndObjects":
            for ob in bpy.data.objects:
                if ob.thug_triggerscript_props and ob.thug_triggerscript_props.triggerscript_type == "Custom":
                    old_name = ob.thug_triggerscript_props.custom_name
                    if bpy.data.texts.get(old_name, None):
                        # This was already converted, don't modify
                        continue
                    new_name = "script_" + old_name
                    if not bpy.data.texts.get(new_name, None):
                        # Converted name was not found! Make sure they know there's an invalid reference
                        raise Exception("Updated script name " + new_name + " was not found.")
                    ob.thug_triggerscript_props.custom_name = new_name
                        
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return "THUG_SCRIPTS" in bpy.data.texts
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="TriggerScript Import")
        row = col.row()
        row.prop(self, "import_type")
        
        
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