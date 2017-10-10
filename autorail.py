import bpy
import bgl
import bmesh
from bpy.props import *
from pprint import pprint
from . import collision, helpers
from . collision import update_triggered_by_ui_updater 
from . constants import *
from . helpers import *

# PROPERTIES
#############################################
AUTORAIL_NONE = 0 # -2
AUTORAIL_AUTO = -1

# METHODS
#############################################
def update_autorail_terrain_type(wm, context):
    global update_triggered_by_ui_updater
    if update_triggered_by_ui_updater:
        return
    if not context.edit_object:
        return
    bm = bmesh.from_edit_mesh(context.edit_object.data)

    arl = bm.edges.layers.int.get("thug_autorail")
    if not arl:
        if wm.thug_autorail_terrain_type == "None":
            return
        arl = bm.edges.layers.int.new("thug_autorail")
        for edge in bm.edges:
            edge[arl] = AUTORAIL_NONE

    for edge in bm.edges:
        if not edge.select:
            continue
        type_ = wm.thug_autorail_terrain_type
        edge[arl] = AUTORAIL_AUTO if type_ == "Auto" else \
                    AUTORAIL_NONE if type_ == "None" else \
                    TERRAIN_TYPES.index(wm.thug_autorail_terrain_type)

    bmesh.update_edit_mesh(context.edit_object.data)

def _resolve_autorail_terrain_type(ob, bm, edge, arl):
    if edge[arl] != AUTORAIL_AUTO:
        return edge[arl]

    lfs = list(edge.link_faces)
    if not lfs:
        return 0

    face_tt = collision._resolve_face_terrain_type(ob, bm, lfs[0])
    return TERRAIN_TYPES.index(TERRAIN_TYPE_TO_GRIND.get(TERRAIN_TYPES[face_tt], "DEFAULT"))


def _get_autorails(mesh_object, operator=None):
    from contextlib import ExitStack
    assert mesh_object.type == "MESH"
    ob = mesh_object

    all_autorails = []

    with ExitStack() as exit_stack:
        if mesh_object.modifiers:
            final_mesh = mesh_object.to_mesh(bpy.context.scene, True, 'PREVIEW')
            exit_stack.callback(bpy.data.meshes.remove, final_mesh)
        else:
            final_mesh = mesh_object.data

        bm = bmesh.new()
        exit_stack.callback(bm.free)

        bm.from_mesh(final_mesh)
        arl = bm.edges.layers.int.get("thug_autorail")
        if not arl: return []

        eligible_edges = set(bm.edges)

        # start_co = start.co.copy().freeze()

        while eligible_edges:
            root_edge = eligible_edges.pop()
            if root_edge[arl] == AUTORAIL_NONE:
                continue

            edge_beginning = root_edge.verts[0]
            edge_end = root_edge.verts[1]
            autorail_points = [AutorailPoint(
                ob.matrix_world * edge_beginning.co.copy(),
                _resolve_autorail_terrain_type(mesh_object, bm, root_edge, arl)
                )]

            # going forwards
            while True:
                forward_edge = None
                for edge in edge_end.link_edges:
                    if edge[arl] != AUTORAIL_NONE and edge in eligible_edges:
                        forward_edge = edge
                        eligible_edges.remove(forward_edge)

                if forward_edge:
                    if forward_edge.verts[0] == edge_end:
                        edge_beginning = forward_edge.verts[0]
                        edge_end = forward_edge.verts[1]
                    else:
                        edge_beginning = forward_edge.verts[1]
                        edge_end = forward_edge.verts[0]

                    autorail_points.append(AutorailPoint(
                        ob.matrix_world * edge_beginning.co.copy(),
                        _resolve_autorail_terrain_type(mesh_object, bm, forward_edge, arl)))
                else:
                    autorail_points.append(AutorailPoint(
                        ob.matrix_world * edge_end.co.copy(),
                        AUTORAIL_AUTO))
                    break
            forward_edge = None

            edge_beginning = root_edge.verts[0]
            edge_end = root_edge.verts[1]

            # going backwards
            while True:
                backward_edge = None
                for edge in edge_beginning.link_edges:
                    if edge[arl] != AUTORAIL_NONE and edge in eligible_edges:
                        backward_edge = edge
                        eligible_edges.remove(backward_edge)

                if backward_edge:
                    if backward_edge.verts[1] == edge_beginning:
                        edge_beginning = backward_edge.verts[0]
                        edge_end = backward_edge.verts[1]
                    else:
                        edge_beginning = backward_edge.verts[1]
                        edge_end = backward_edge.verts[0]

                    autorail_points = [(AutorailPoint(
                        ob.matrix_world * edge_beginning.co.copy(),
                        _resolve_autorail_terrain_type(mesh_object, bm, backward_edge, arl))),
                        *autorail_points]
                else:
                    break

            all_autorails.append(Autorail(autorail_points, ob))

    return all_autorails


def _try_merge_autorails(autorail, other_autorail):
    if autorail.is_cyclical():
        return False
    if other_autorail.is_cyclical():
        return False
    if autorail.next_merged:
        return False

    if not other_autorail.prev_merged:
        dist_between = (other_autorail.points[0].position - autorail.points[-1].position).length
        if dist_between < 0.25:
            autorail.next_merged = other_autorail
            other_autorail.prev_merged = autorail
            last_point = autorail.points.pop()
            other_autorail.points[0].position = (other_autorail.points[0].position + last_point.position) / 2
            return True

    if other_autorail.can_reverse():
        dist_between = (other_autorail.points[-1].position - autorail.points[-1].position).length
        if dist_between < 0.25:
            autorail.next_merged = other_autorail
            other_autorail.reverse()
            other_autorail.prev_merged = autorail
            last_point = autorail.points.pop()
            other_autorail.points[0].position = (other_autorail.points[0].position + last_point.position) / 2
            return True

def _export_autorails(p, c, i, v3, operator):
    import mathutils

    rail_node_counter = 0
    all_autorails = []
    for ob in bpy.data.objects:
        if ob.get("thug_autosplit_object_no_export_hack"):
            continue
        if ob.type == "MESH":
            autorails = _get_autorails(ob, operator)
            all_autorails += autorails
    del ob

    autorail_tree = mathutils.kdtree.KDTree(len(all_autorails) * 2)
    autorail_idx = 0
    for autorail in all_autorails:
        autorail_tree.insert(autorail.points[0].position, autorail_idx)
        autorail_tree.insert(autorail.points[-1].position, autorail_idx + 1)
        autorail_idx += 2
    autorail_tree.balance()

    to_merge = list(all_autorails)
    while to_merge:
        autorail = to_merge.pop()
        if autorail.next_merged or autorail.is_cyclical():
            continue

        for other_autorail in (
            autorail_tree.find_range(autorail.points[ 0].position, 0.25) +
            autorail_tree.find_range(autorail.points[-1].position, 0.25)):
            other_autorail = all_autorails[other_autorail[1]//2]
            if autorail is other_autorail or other_autorail.is_cyclical():
                continue
            if _try_merge_autorails(autorail, other_autorail):
                #LOG.debug("Merged autorail {} ({}) with {} ({})".format(autorail, autorail.object, other_autorail, other_autorail.object))
                break

    output_offsets = {}
    while all_autorails:
        autorail = all_autorails.pop()

        while autorail:
            next_autorail = None
            beginning_node_index = rail_node_counter
            output_offsets[autorail] = beginning_node_index

            autorail_point_index = 0
            while autorail_point_index < len(autorail.points):
                autorail_point = autorail.points[autorail_point_index]
                obj_clean_name = get_clean_name(autorail.object)
                p("\t:i :s{")
                p("\t\t:i {} = {}".format(c("Pos"),
                    v3(mathutils.Vector(to_thug_coords(autorail_point.position)) + mathutils.Vector((0, 1, 0)))))
                p("\t\t:i {} = {}".format(c("Angles"), v3((0, 0, 0))))
                # name = "{}_AutoRailNode__{}".format(obj_clean_name, autorail_point_index) # rail_node_counter)
                name = "{}__AutoRailNode_{}".format(obj_clean_name, rail_node_counter)
                p("\t\t:i {} = {}".format(c("Name"), c(name)))
                p("\t\t:i {} = {}".format(c("Class"), c("RailNode")))
                p("\t\t:i {} = {}".format(c("Type"), c("Concrete")))
                p("\t\t:i {} = {}".format(c("CollisionMode"), c("Geometry")))
                autorail_type = autorail_point.terrain_type
                if autorail_type == AUTORAIL_AUTO:
                    autorail_type = "TERRAIN_GRINDCONC"
                else:
                    autorail_type = "TERRAIN_" + TERRAIN_TYPES[autorail_type]
                p("\t\t:i {} = {}".format(c("TerrainType"), c(autorail_type)))

                if getattr(autorail.object, "thug_is_trickobject", False):
                    p("\t\t:i call {} arguments".format(c("TrickObject")))
                    if autorail.object.thug_cluster_name:
                        cluster_name = autorail.object.thug_cluster_name
                    else:
                        cluster_name = get_clean_name(autorail.object)
                    p("\t\t\t{} = {}".format(c("Cluster"), c(cluster_name)))

                if autorail_point_index + 1 == len(autorail.points):
                    if autorail.is_cyclical():
                        links = [i(beginning_node_index)]
                    elif autorail.next_merged:
                        if autorail.next_merged in output_offsets:
                            links = [i(output_offsets[autorail.next_merged])]
                        else:
                            links = [i(rail_node_counter + 1)]

                            next_autorail = autorail.next_merged
                    else:
                        links = []
                else:
                    links = [i(rail_node_counter + 1)]

                p("\t\t:i {} = :a{{ {} :a}}".format(c("Links"), ' '.join(links)))
                if autorail.object.thug_created_at_start:
                    p("\t\t:i {}".format(c("CreatedAtStart")))
                p("\t:i :s}")
                rail_node_counter += 1
                autorail_point_index += 1

            if next_autorail:
                all_autorails.remove(next_autorail)
            autorail = next_autorail
    return rail_node_counter


def _export_rails(p, c, operator=None):
    def v3(v):
        return "%vec3({:6f},{:6f},{:6f})".format(*v)

    def i(integer):
        return "%i({},{:08})".format(integer, integer)
    def f(value):
        return "%f({})".format(value)

    rail_node_counter = _export_autorails(p, c, i, v3, operator)

    generated_scripts = {}
    custom_triggerscript_names = []

    obj_rail_node_start_offset_counter = rail_node_counter
    obj_rail_node_start_offsets = {}
    for ob in bpy.data.objects:
        if ob.type != "CURVE" or ob.thug_path_type not in ("Rail", "Ladder", "Waypoint"): continue
        obj_rail_node_start_offsets[ob] = obj_rail_node_start_offset_counter
        for spline in ob.data.splines:
            obj_rail_node_start_offset_counter += len(spline.points)

    for ob in bpy.data.objects:
        if ob.type != "CURVE" or ob.thug_path_type not in ("Rail", "Ladder", "Waypoint"): continue
        if ob.thug_path_type == "Custom" and ob.thug_node_expansion == "": continue # Path with no class will break the game!
        
        clean_name = get_clean_name(ob)
        point_idx = 1
        first_node_idx = rail_node_counter
        for spline in ob.data.splines:
            points = spline.points
            point_count = len(points)
            p_num = -1
            for point in points:
                p_num += 1
                p("\t:i :s{")
                p("\t\t:i {} = {}".format(c("Pos"), v3(to_thug_coords(ob.matrix_world * point.co.to_3d()))))

                if ob.thug_path_type == "Rail":
                    p("\t\t:i {} = {}".format(c("Class"), c("RailNode")))
                    p("\t\t:i {} = {}".format(c("Type"), c("Concrete")))
                    p("\t\t:i {} = {}".format(c("Angles"), v3((0, 0, 0))))
                    name = "RailNode_" + str(rail_node_counter)
                elif ob.thug_path_type == "Ladder":
                    p("\t\t:i {} = {}".format(c("Class"), c("ClimbingNode")))
                    p("\t\t:i {} = {}".format(c("Type"), c("Ladder")))
                    p("\t\t:i {} = {}".format(c("Angles"), v3((0, ob.rotation_euler[2], 0))))
                    name = "LadderNode_" + str(rail_node_counter)
                elif ob.thug_path_type == "Waypoint":
                    p("\t\t:i {} = {}".format(c("Class"), c("Waypoint")))
                    #p("\t\t:i {} = {}".format(c("Type"), c("Default")))
                    p("\t\t:i {} = {}".format(c("Angles"), v3((0, ob.rotation_euler[2], 0))))
                    name = "Waypoint_" + str(rail_node_counter)
                elif ob.thug_path_type == "Custom":
                    p("\t\t:i {} = {}".format(c("Angles"), v3((0, 0, 0))))
                    name = "CustomPathNode_" + str(rail_node_counter)
                else:
                    assert False
                    
                # Insert individual node properties here, if they exist!
                if len(ob.data.thug_pathnode_triggers) > p_num and ob.data.thug_pathnode_triggers[p_num].name != "":
                    # individual rail/path node names
                    name = ob.data.thug_pathnode_triggers[p_num].name
                    p("\t\t:i {} = {}".format(c("Name"), c(name)))
                    if ob.data.thug_pathnode_triggers[p_num].terrain != "":
                        # Terrain is also used for AI skaters, so don't output twice!
                        if ob.data.thug_pathnode_triggers[p_num].PedType != "Skate":
                            p("\t\t:i {} = {}".format(c("TerrainType"), c(ob.data.thug_pathnode_triggers[p_num].terrain)))
                        
                    if ob.data.thug_pathnode_triggers[p_num].PedType != "":
                        p("\t\t:i {} = {}".format(c("PedType"), c(ob.data.thug_pathnode_triggers[p_num].PedType)))
                        # Output skater AI node properties here!
                        if ob.data.thug_pathnode_triggers[p_num].PedType == "Skate":
                            if ob.data.thug_pathnode_triggers[p_num].do_continue:
                                p("\t\t:i {}".format(c("Continue")))
                                p("\t\t:i {} = {}".format(c("ContinueWeight"), f(ob.data.thug_pathnode_triggers[p_num].ContinueWeight)))
                            if ob.data.thug_pathnode_triggers[p_num].JumpToNextNode:
                                p("\t\t:i {}".format(c("JumpToNextNode")))
                            p("\t\t:i {} = {}".format(c("Priority"), c(ob.data.thug_pathnode_triggers[p_num].Priority)))
                            # Skate action types defined here!
                            _skateaction = ob.data.thug_pathnode_triggers[p_num].SkateAction
                            p("\t\t:i {} = {}".format(c("SkateAction"), c(_skateaction)))
                            if _skateaction == "Flip_Trick" or _skateaction == "Jump" or _skateaction == "Vert_Jump" or \
                                _skateaction == "Vert_Flip":
                                p("\t\t:i {} = {}".format(c("JumpHeight"), f(ob.data.thug_pathnode_triggers[p_num].JumpHeight)))
                            elif _skateaction == "Grind":
                                p("\t\t:i {} = {}".format(c("TerrainType"), c(ob.data.thug_pathnode_triggers[p_num].terrain)))
                            elif _skateaction == "Manual":
                                p("\t\t:i {} = {}".format(c("ManualType"), c(ob.data.thug_pathnode_triggers[p_num].ManualType)))
                            elif _skateaction == "Stop":
                                p("\t\t:i {} = {}".format(c("Deceleration"), f(ob.data.thug_pathnode_triggers[p_num].Deceleration)))
                                p("\t\t:i {} = {}".format(c("StopTime"), f(ob.data.thug_pathnode_triggers[p_num].StopTime)))
                            elif _skateaction == "Vert_Grab":
                                p("\t\t:i {} = {}".format(c("SpinAngle"), f(ob.data.thug_pathnode_triggers[p_num].SpinAngle)))
                                p("\t\t:i {} = {}".format(c("SpinDirection"), c(ob.data.thug_pathnode_triggers[p_num].SpinDirection)))
                        
                # No individual node properties are defined, so use the object-level settings    
                else:
                    name = clean_name + "__" + str(point_idx - 1)
                    p("\t\t:i {} = {}".format(c("Name"), c(name)))
                    # Generate terrain type using the object terrain settings
                    if ob.thug_path_type != "Custom" and ob.thug_path_type != "Waypoint" :
                        p("\t\t:i {} = {}".format(c("CollisionMode"), c("Geometry")))
                        rail_type = ob.thug_rail_terrain_type
                        if rail_type == "Auto":
                            rail_type = "TERRAIN_GRINDCONC"
                        else:
                            rail_type = "TERRAIN_" + rail_type
                        p("\t\t:i {} = {}".format(c("TerrainType"), c(rail_type)))

                # Other object-level properties defined here!
                if ob.thug_path_type != "Custom" and ob.thug_path_type != "Waypoint" :
                    if getattr(ob, "thug_is_trickobject", False):
                        p("\t\t:i call {} arguments".format(c("TrickObject")))
                        if ob.thug_cluster_name:
                            cluster_name = ob.thug_cluster_name
                        elif ob.parent and ob.parent.type == "MESH":
                            cluster_name = get_clean_name(ob.parent)
                        else:
                            cluster_name = name
                        p("\t\t\t{} = {}".format(c("Cluster"), c(cluster_name)))

                if ob.thug_node_expansion:
                    p("\t\t:i {}".format(c(ob.thug_node_expansion)))

                if ob.thug_created_at_start:
                    p("\t\t:i {}".format(c("CreatedAtStart")))

                if len(ob.data.thug_pathnode_triggers) > p_num and ob.data.thug_pathnode_triggers[p_num].script_name != "":
                    # Export trigger script assigned to individual rail nodes (not entire rail)
                    p("\t\t:i {} = {}".format(c("TriggerScript"), c(ob.data.thug_pathnode_triggers[p_num].script_name)))

                if point_idx != point_count:
                    p("\t\t:i {} = :a{{{}:a}}".format(c("Links"), i(rail_node_counter + 1)))
                elif spline.use_cyclic_u:
                    p("\t\t:i {} = :a{{{}:a}}".format(c("Links"), i(first_node_idx)))
                elif ob.thug_rail_connects_to:
                    if ob.thug_rail_connects_to not in bpy.data.objects:
                        operator.report({"ERROR"}, "Rail {} connects to nonexistent rail {}".format(ob.name, ob.thug_rail_connects_to))
                    else:
                        connected_to = bpy.data.objects[ob.thug_rail_connects_to]
                        if connected_to in obj_rail_node_start_offsets:
                            p("\t\t:i {} = :a{{{}:a}}".format(
                                c("Links"),
                                i(obj_rail_node_start_offsets[connected_to])))

                p("\t:i :s}")
                point_idx += 1
                rail_node_counter += 1

    return custom_triggerscript_names, generated_scripts, obj_rail_node_start_offsets




# OPERATORS
#############################################
class AutorailPoint:
    def __init__(self, position, terrain_type, trickobject_cluster=""):
        self.position = position
        self.terrain_type = terrain_type
        self.trickobject_cluster = trickobject_cluster
        # self.max_distance_for_merging = 0.25


class Autorail:
    def __init__(self, points, object=None):
        self.points = points
        self.object = object
        self.prev_merged = None
        self.next_merged = None

    def is_cyclical(self):
        return len(self.points) >= 2 and self.points[0].position == self.points[-1].position

    def can_reverse(self):
        return not self.prev_merged and not self.next_merged

    def reverse(self):
        assert self.can_reverse()
        reversed_points = []
        if len(self.points) == 1:
            return

        i = len(self.points) - 1
        while i >= 0:
            point = self.points[i]
            prev_point = None if i - 1 < 0 else self.points[i]
            if prev_point:
                point.terrain_type = prev_point.terrain_type
            else:
                point.terrain_type = AUTORAIL_AUTO
            reversed_points.append(point)
            i -= 1

        self.points = reversed_points

class MarkAutorail(bpy.types.Operator):
    bl_idname = "mesh.thug_mark_autorail"
    bl_label = "Mark Rail"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH" and context.object.type == "MESH"

    def execute(self, context):
        bm = bmesh.from_edit_mesh(context.object.data)
        arl = bm.edges.layers.int.get("thug_autorail")

        if not arl:
            arl = bm.edges.layers.int.new("thug_autorail")
            for edge in bm.edges:
                edge[arl] = AUTORAIL_NONE

        for edge in bm.edges:
            if edge.select:
                edge[arl] = AUTORAIL_AUTO

        bmesh.update_edit_mesh(context.object.data)

        return {'FINISHED'}


class ClearAutorail(bpy.types.Operator):
    bl_idname = "mesh.thug_clear_autorail"
    bl_label = "Clear Rail"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH" and context.object.type == "MESH"

    def execute(self, context):
        bm = bmesh.from_edit_mesh(context.object.data)
        arl = bm.edges.layers.int.get("thug_autorail")
        if not arl:
            return {'FINISHED'}

        for edge in bm.edges:
            if edge.select:
                edge[arl] = AUTORAIL_NONE
        bmesh.update_edit_mesh(context.object.data)

        return {'FINISHED'}


class ExtractRail(bpy.types.Operator):
    bl_idname = "object.thug_extract_rail"
    bl_label = "Extract Rail"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH" and context.object.type == "MESH"

    def execute(self, context):
        old_object = context.object
        bpy.ops.mesh.duplicate()
        before = set(bpy.data.objects)
        bpy.ops.mesh.separate()
        after = set(bpy.data.objects)
        new_object = list(after - before)[0]
        new_name_idx = 0
        new_name = "RailPath0"
        while new_name in bpy.data.objects:
            new_name_idx += 1
            new_name = "RailPath" + str(new_name_idx)
        new_object.name = new_name
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all()
        new_object.select = True
        context.scene.objects.active = new_object
        bpy.ops.object.convert(target='CURVE')
        new_object.parent = old_object
        new_object.matrix_parent_inverse = old_object.matrix_basis.inverted()
        new_object.thug_path_type = "Rail"

        return {"FINISHED"}

