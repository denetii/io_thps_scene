#############################################
# THUG1/2 COLLISION SETTINGS
#############################################
import bpy
import struct
import mathutils
import math
import os, sys
from bpy.props import *
from . constants import *
from . helpers import *

# PROPERTIES
#############################################
update_triggered_by_ui_updater = False

# METHODS
#############################################
def update_collision_flag_mesh(wm, context, flag):
    global update_triggered_by_ui_updater
    if update_triggered_by_ui_updater:
        return
    if not context.edit_object:
        return
    bm = bmesh.from_edit_mesh(context.edit_object.data)

    cfl = bm.faces.layers.int.get("collision_flags")
    if not cfl:
        cfl = bm.faces.layers.int.new("collision_flags")

    flag_set = getattr(wm, "thug_face_" + flag)
    for face in bm.faces:
        if not face.select:
            continue
        flags = face[cfl]
        #for ff in SETTABLE_FACE_FLAGS:
        if flag_set:
            flags |= FACE_FLAGS[flag]
        else:
            flags &= ~FACE_FLAGS[flag]
        face[cfl] = flags
    bmesh.update_edit_mesh(context.edit_object.data)

#----------------------------------------------------------------------------------
def update_terrain_type_mesh(wm, context):
    global update_triggered_by_ui_updater
    if update_triggered_by_ui_updater:
        return
    if not context.edit_object:
        return
    bm = bmesh.from_edit_mesh(context.edit_object.data)

    ttl = bm.faces.layers.int.get("terrain_type")
    if not ttl:
        ttl = bm.faces.layers.int.new("terrain_type")

    for face in bm.faces:
        if not face.select:
            continue

        if wm.thug_face_terrain_type == "Auto":
            face[ttl] = AUTORAIL_AUTO
        else:
            face[ttl] = TERRAIN_TYPES.index(wm.thug_face_terrain_type)


    bmesh.update_edit_mesh(context.edit_object.data)

#----------------------------------------------------------------------------------
@bpy.app.handlers.persistent
def update_collision_flag_ui_properties(scene):
    global update_triggered_by_ui_updater
    update_triggered_by_ui_updater = True
    try:
        ob = scene.objects.active
        if not ob or ob.mode != "EDIT" or ob.type != "MESH":
            return
        bm = bmesh.from_edit_mesh(ob.data)
        wm = bpy.context.window_manager

        arl = bm.edges.layers.int.get("thug_autorail")
        edge = bm.select_history.active
        if arl and edge and isinstance(edge, bmesh.types.BMEdge):
            new_value = "Auto" if edge[arl] == AUTORAIL_AUTO else \
                        "None" if edge[arl] == AUTORAIL_NONE else \
                        TERRAIN_TYPES[edge[arl]]
            if wm.thug_autorail_terrain_type != new_value:
                try:
                    wm.thug_autorail_terrain_type = new_value
                except TypeError:
                    wm.thug_autorail_terrain_type = "Auto"

        face = None
        if (("FACE" in bm.select_mode)
            and bm.select_history
            and isinstance(bm.select_history[-1], bmesh.types.BMFace)):
            face = bm.select_history[-1]
        if not face:
            face = next((face for face in bm.faces if face.select), None)
        if not face:
            return

        cfl = bm.faces.layers.int.get("collision_flags")
        for ff in SETTABLE_FACE_FLAGS:
            new_value = bool(cfl and (face[cfl] & FACE_FLAGS[ff]))
            if getattr(wm, "thug_face_" + ff) != new_value:
                setattr(wm, "thug_face_" + ff, new_value)

        ttl = bm.faces.layers.int.get("terrain_type")
        if ttl:
            if face[ttl] == AUTORAIL_AUTO:
                new_value = "Auto"
            else:
                new_value = TERRAIN_TYPES[face[ttl]]
        else:
            new_value = "Auto"
        if wm.thug_face_terrain_type != new_value:
            wm.thug_face_terrain_type = new_value
    finally:
        update_triggered_by_ui_updater = False


# PROPERTIES
#############################################
class THUGCollisionMeshTools(bpy.types.Panel):
    bl_label = "TH Collision Mesh Tools"
    bl_region_type = "TOOLS"
    bl_space_type = "VIEW_3D"
    bl_category = "THUG Tools"

    """
    @classmethod
    def poll(cls, context):
        # Only allow in edit mode for a selected mesh.
        return context.mode == "EDIT_MESH" and context.object is not None and context.object.type == "MESH"
    """

    def draw(self, context):
        self.layout.prop(context.window_manager, "thug_show_face_collision_colors")
        if not context.object: return
        #print(context.mode + " " + context.object.type)
        if context.mode == "EDIT_MESH" and context.object.type == "MESH":
            obj = context.object
            bm = bmesh.from_edit_mesh(obj.data)
            any_face_selected = any(face for face in bm.faces if face.select)
            collision_flag_layer = bm.faces.layers.int.get("collision_flags")
            terrain_type_layer = bm.faces.layers.int.get("terrain_type")
            if any_face_selected:
                cf_box = self.layout.box()
                for idx, ff in enumerate(SETTABLE_FACE_FLAGS):
                    cf_box.prop(context.window_manager, "thug_face_" + ff)
                self.layout.prop(context.window_manager, "thug_face_terrain_type")
            else:
                self.layout.label("No faces selected.")

            if any_face_selected or any(edge for edge in bm.edges if edge.select):
                col = self.layout.column(True)
                col.operator(MarkAutorail.bl_idname)
                col.operator(ClearAutorail.bl_idname)
                self.layout.prop(context.window_manager, "thug_autorail_terrain_type")
                self.layout.operator(ExtractRail.bl_idname)
            else:
                self.layout.label("No edges selected.")
        elif False and context.mode == "OBJECT":
            self.layout.row().label("Object: {}".format(context.object.type))
            self.layout.row().label("Object flags: {}".format(context.object.thug_col_obj_flags))

        elif context.mode == "EDIT_CURVE" and context.object.type == "CURVE":
            if (context.object.type == "CURVE" and
                        context.object.data.splines and
                        context.object.data.splines[0].points):
                #_update_pathnodes_collections(self, context)
                #context.object.data.thug_pathnode_triggers.clear()
                tmp_idx = -1
                for p in context.object.data.splines[0].points:
                    tmp_idx += 1
                    if p.select:
                        self.layout.prop(context.object.data.thug_pathnode_triggers[tmp_idx], "script_name")
                        break
                        
                