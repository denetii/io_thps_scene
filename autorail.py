import bpy
import bgl
import bmesh
from bpy.props import *
from . collision import update_triggered_by_ui_updater
from . constants import *

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

# OPERATORS
#############################################
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

