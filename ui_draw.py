import bpy
from bpy.props import *
from . import_thps4 import THPS4ScnToScene
from . import_thug1 import THUG1ScnToScene
from . import_thug2 import THUG2ScnToScene, THUG2ColToScene
from . skeleton import THUGImportSkeleton
from . object import __init_wm_props
import bgl
from . constants import *
from . scene_props import *
from . material import *
from . collision import *
from . export_thug1 import *
from . export_thug2 import *

# PROPERTIES
#############################################
draw_stuff_display_list_id = bgl.glGenLists(1)
draw_stuff_dirty = True
draw_stuff_objects = set()
draw_handle = None

# METHODS
#############################################
@bpy.app.handlers.persistent
def draw_stuff_post_update(scene):
    # print("draw_stuff_post_update")
    global draw_stuff_dirty, draw_stuff_objects
    if draw_stuff_dirty: return

    if not draw_stuff_objects:
        draw_stuff_dirty = True
        return

    # import time
    # print(time.clock())
    scn_objs = { ob.name: ob for ob in scene.objects }
    for ob in draw_stuff_objects:
        ob = scn_objs.get(ob) # scene.objects.get(ob)
        if (not ob) or ob.is_updated or ob.is_updated_data:
            draw_stuff_dirty = True
            return
    # print(time.clock())

#----------------------------------------------------------------------------------
@bpy.app.handlers.persistent
def draw_stuff_pre_load_cleanup(*args):
    # print("draw_stuff_post_update")
    global draw_stuff_dirty, draw_stuff_objects
    draw_stuff_dirty = True
    draw_stuff_objects = set()

#----------------------------------------------------------------------------------
@bpy.app.handlers.persistent
def draw_stuff():
    # print("draw_stuff")
    # FIXME this should use glPushAttrib
    from bgl import glColor3f, glVertex3f, glBegin, glEnd, GL_POLYGON, GL_LINES
    global draw_stuff_dirty, draw_stuff_objects
    ctx = bpy.context
    if not len(ctx.selected_objects) and not ctx.object:
        return
    if not bpy.context.window_manager.thug_show_face_collision_colors:
        return

    VERT_FLAG = FACE_FLAGS["mFD_VERT"]
    WALLRIDABLE_FLAG = FACE_FLAGS["mFD_WALL_RIDABLE"]
    TRIGGER_FLAG = FACE_FLAGS["mFD_TRIGGER"]
    NON_COLLIDABLE_FLAG = FACE_FLAGS["mFD_NON_COLLIDABLE"]

    bgl.glPushAttrib(bgl.GL_ALL_ATTRIB_BITS)
    try:
        _tmp_buf = bgl.Buffer(bgl.GL_FLOAT, 1)
        bgl.glGetFloatv(bgl.GL_POLYGON_OFFSET_FACTOR, _tmp_buf)
        old_offset_factor = _tmp_buf[0]
        bgl.glGetFloatv(bgl.GL_POLYGON_OFFSET_UNITS, _tmp_buf)
        old_offset_units = _tmp_buf[0]
        del _tmp_buf

        objects = set([ob.name for ob in ctx.selected_objects] if ctx.mode == "OBJECT" else [ctx.object.name])
        if draw_stuff_objects != objects:
            draw_stuff_dirty = True
        # print("draw_stuff2")

        if not draw_stuff_dirty:
            bgl.glCallList(draw_stuff_display_list_id)
            bgl.glPolygonOffset(old_offset_factor, old_offset_units)
            bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)
            bgl.glDisable(bgl.GL_CULL_FACE)
            return

        bm = None
        bgl.glNewList(draw_stuff_display_list_id, bgl.GL_COMPILE_AND_EXECUTE)
        try:
            bgl.glCullFace(bgl.GL_BACK)
            bgl.glEnable(bgl.GL_CULL_FACE)
            bgl.glEnable(bgl.GL_POLYGON_OFFSET_FILL)
            #bgl.glEnable(bgl.GL_POLYGON_OFFSET_LINE)
            bgl.glPolygonOffset(-2, -2)

            bgl.glEnable(bgl.GL_BLEND)
            bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA);

            prefs = ctx.user_preferences.addons[ADDON_NAME].preferences

            bgl.glLineWidth(prefs.line_width)

            draw_stuff_objects = objects
            bdobs = {ob.name: ob for ob in bpy.data.objects}
            for ob in objects:
                ob = bdobs[ob]
                if not bm: bm = bmesh.new()
                if (ob and
                        ob.type == "CURVE" and
                        ob.data.splines and
                        ob.data.splines[-1].points and
                        ob.thug_path_type == "Rail" and
                        ob.thug_rail_connects_to):
                    connects_to = bdobs[ob.thug_rail_connects_to]
                    if (connects_to and
                            connects_to.type == "CURVE" and
                            connects_to.data.splines and
                            connects_to.data.splines[0].points):
                        glBegin(GL_LINES)
                        bgl.glColor4f(*prefs.rail_end_connection_color)
                        v = ob.matrix_world * ob.data.splines[-1].points[-1].co.to_3d()
                        glVertex3f(v[0], v[1], v[2])
                        v = connects_to.matrix_world * connects_to.data.splines[0].points[0].co.to_3d()
                        glVertex3f(v[0], v[1], v[2])
                        glEnd()


                if not ob or ob.type != "MESH":
                    continue

                if ob.mode == "EDIT":
                    bm.free()
                    bm = bmesh.from_edit_mesh(ob.data).copy()
                else:
                    bm.clear()
                    if ob.modifiers:
                        final_mesh = ob.to_mesh(bpy.context.scene, True, "PREVIEW")
                        try:
                            bm.from_mesh(final_mesh)
                        finally:
                            bpy.data.meshes.remove(final_mesh)
                    else:
                        bm.from_mesh(ob.data)

                arl = bm.edges.layers.int.get("thug_autorail")
                if arl:
                    bgl.glColor4f(*prefs.autorail_edge_color)
                    glBegin(GL_LINES)
                    for edge in bm.edges:
                        if edge[arl] == AUTORAIL_NONE:
                            continue

                        for vert in edge.verts:
                            v = ob.matrix_world * vert.co
                            glVertex3f(v[0], v[1], v[2])
                    glEnd()

                cfl = bm.faces.layers.int.get("collision_flags")
                flag_stuff = ((VERT_FLAG, prefs.vert_face_color),
                              (WALLRIDABLE_FLAG, prefs.wallridable_face_color),
                              (TRIGGER_FLAG, prefs.trigger_face_color),
                              (NON_COLLIDABLE_FLAG, prefs.non_collidable_face_color))
                if cfl:
                    bmesh.ops.triangulate(bm, faces=bm.faces)

                    for face in bm.faces:
                        drawn_face = False
                        if prefs.show_bad_face_colors:
                            if (face[cfl] & (VERT_FLAG | WALLRIDABLE_FLAG | NON_COLLIDABLE_FLAG) not in
                                (VERT_FLAG, WALLRIDABLE_FLAG, NON_COLLIDABLE_FLAG, 0)):
                                bgl.glColor4f(*prefs.bad_face_color)
                                glBegin(GL_POLYGON)
                                for vert in face.verts:
                                    v = ob.matrix_world * vert.co
                                    glVertex3f(v[0], v[1], v[2])
                                glEnd()
                                continue

                        for face_flag, face_color in flag_stuff:
                            if face[cfl] & face_flag and (not drawn_face or prefs.mix_face_colors):
                                bgl.glColor4f(*face_color)
                                drawn_face = True

                                glBegin(GL_POLYGON)
                                for vert in face.verts:
                                    v = ob.matrix_world * vert.co
                                    glVertex3f(v[0], v[1], v[2])
                                glEnd()
        finally:
            draw_stuff_dirty = False
            bgl.glEndList()
            if bm: bm.free()
            bgl.glPolygonOffset(old_offset_factor, old_offset_units)
            bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)
    finally:
        bgl.glPopAttrib()



#----------------------------------------------------------------------------------
def import_menu_func(self, context):
    self.layout.operator(THUG2ColToScene.bl_idname, text=THUG2ColToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THUG2ScnToScene.bl_idname, text=THUG2ScnToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THUG1ScnToScene.bl_idname, text=THUG1ScnToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THPS4ScnToScene.bl_idname, text=THPS4ScnToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THUGImportSkeleton.bl_idname, text=THUGImportSkeleton.bl_label, icon='PLUGIN')
#----------------------------------------------------------------------------------    
def export_menu_func(self, context):
    self.layout.operator(SceneToTHUGFiles.bl_idname, text="Scene to THUG1 level files", icon='PLUGIN')
    self.layout.operator(SceneToTHUGModel.bl_idname, text="Scene to THUG1 model", icon='PLUGIN')
    self.layout.operator(SceneToTHUG2Files.bl_idname, text="Scene to THUG2 level files", icon='PLUGIN')
    self.layout.operator(SceneToTHUG2Model.bl_idname, text="Scene to THUG2 model", icon='PLUGIN')
#----------------------------------------------------------------------------------
def register_menus():
    bpy.types.INFO_MT_file_import.append(import_menu_func)
    bpy.types.INFO_MT_file_export.append(export_menu_func)
#----------------------------------------------------------------------------------
def unregister_menus():
    bpy.types.INFO_MT_file_import.remove(import_menu_func)
    bpy.types.INFO_MT_file_export.remove(export_menu_func)
#----------------------------------------------------------------------------------
def register_props():
    __init_wm_props()
    bpy.types.Object.thug_object_class = EnumProperty(
        name="Object Class",
        description="Object Class.",
        items=[
            ("LevelGeometry", "LevelGeometry", "LevelGeometry. Use for static geometry."),
            ("LevelObject", "LevelObject", "LevelObject. Use for dynamic objects.")],
        default="LevelGeometry")
    bpy.types.Object.thug_do_autosplit = BoolProperty(
        name="Autosplit Object on Export",
        description="Split object into multiple smaller objects of sizes suitable for the THUG engine. Note that this will create multiple objects, which might cause issues with scripting. Using this for LevelObjects or objects used in scripts is not advised.",
        default=False)
    bpy.types.Object.thug_node_expansion = StringProperty(
        name="Node Expansion",
        description="The struct with this name will be merged to this node's definition in the NodeArray.",
        default="")
    bpy.types.Object.thug_do_autosplit_faces_per_subobject = IntProperty(
        name="Faces Per Subobject",
        description="The max amount of faces for every created subobject.",
        default=300, min=50, max=6000)
    bpy.types.Object.thug_do_autosplit_max_radius = FloatProperty(
        name="Max Radius",
        description="The max radius of for every created subobject.",
        default=2000, min=100, max=5000)
    """
    bpy.types.Object.thug_do_autosplit_preserve_normals = BoolProperty(
        name="Preserve Normals",
        description="Preserve the normals of the ",
        default=True)
    """
    bpy.types.Object.thug_col_obj_flags = IntProperty()
    bpy.types.Object.thug_created_at_start = BoolProperty(name="Created At Start", default=True)
    bpy.types.Object.thug_network_option = EnumProperty(
        name="Network Options",
        items=[
            ("Default", "Default", "Appears in network games."),
            ("AbsentInNetGames", "Offline Only", "Only appears in single-player."),
            ("NetEnabled", "Online (Broadcast)", "Appears in network games, events/scripts appear on all clients.")],
        default="Default")
    bpy.types.Object.thug_export_collision = BoolProperty(name="Export to Collisions", default=True)
    bpy.types.Object.thug_export_scene = BoolProperty(name="Export to Scene", default=True)
    bpy.types.Object.thug_always_export_to_nodearray = BoolProperty(name="Always Export to Nodearray", default=False)
    bpy.types.Object.thug_occluder = BoolProperty(name="Occluder", description="Occludes (hides) geometry behind this mesh. Used for performance improvements.", default=False)
    bpy.types.Object.thug_is_trickobject = BoolProperty(
        name="Is a TrickObject",
        default=False,
        description="This must be checked if you want this object to be taggable in Graffiti.")
    bpy.types.Object.thug_cluster_name = StringProperty(
        name="TrickObject Cluster",
        description="The name of the graffiti group this object belongs to. If this is empty and this is a rail with a mesh object parent this will be set to the parent's name. Otherwise it will be set to this object's name.")
    bpy.types.Object.thug_path_type = EnumProperty(
        name="Path Type",
        items=[
            ("None", "None", "None"),
            ("Rail", "Rail", "Rail"),
            ("Ladder", "Ladder", "Ladder"),
            ("Waypoint", "Waypoint", "Navigation path for pedestrians/vehicles/AI skaters."),
            ("Custom", "Custom", "Custom")],
        default="None")
    bpy.types.Object.thug_rail_terrain_type = EnumProperty(
        name="Rail Terrain Type",
        items=[(t, t, t) for t in ["Auto"] + TERRAIN_TYPES],
        default="Auto")
    bpy.types.Object.thug_rail_connects_to = StringProperty(name="End Connects To")

    bpy.types.Object.thug_triggerscript_props = PointerProperty(type=THUGObjectTriggerScriptProps)

    bpy.types.Object.thug_empty_props = PointerProperty(type=THUGEmptyProps)
    
    bpy.types.Object.thug_proxim_props = PointerProperty(type=THUGProximNodeProps)
    bpy.types.Object.thug_generic_props = PointerProperty(type=THUGGenericNodeProps)
    bpy.types.Object.thug_restart_props = PointerProperty(type=THUGRestartProps)
    bpy.types.Object.thug_go_props = PointerProperty(type=THUGGameObjectProps)
    
    bpy.types.Curve.thug_pathnode_triggers = CollectionProperty(type=THUGPathNodeProps)
    
    bpy.types.Image.thug_image_props = PointerProperty(type=THUGImageProps)

    bpy.types.Material.thug_material_props = PointerProperty(type=THUGMaterialProps)
    bpy.types.Texture.thug_material_pass_props = PointerProperty(type=THUGMaterialPassProps)

    bpy.types.WindowManager.thug_all_rails = CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.WindowManager.thug_all_restarts = CollectionProperty(type=bpy.types.PropertyGroup)

    # bpy.utils.unregister_class(ExtractRail)
    # bpy.utils.register_class(ExtractRail)
    
    #_update_pathnodes_collections()
    
    global draw_handle
    draw_handle = bpy.types.SpaceView3D.draw_handler_add(draw_stuff, (), 'WINDOW', 'POST_VIEW')
    # bpy.app.handlers.scene_update_pre.append(draw_stuff_pre_update)
    bpy.app.handlers.scene_update_post.append(draw_stuff_post_update)
    bpy.app.handlers.scene_update_post.append(update_collision_flag_ui_properties)

    bpy.app.handlers.load_pre.append(draw_stuff_pre_load_cleanup)
    
    
#----------------------------------------------------------------------------------
def unregister_props():
    bgl.glDeleteLists(draw_stuff_display_list_id, 1)

    # bpy.utils.unregister_class(ExtractRail)

    global draw_handle
    if draw_handle:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handle, 'WINDOW')
        draw_handle = None

    """
    if draw_stuff_pre_update in bpy.app.handlers.scene_update_pre:
        bpy.app.handlers.scene_update_pre.remove(draw_stuff_pre_update)
    """

    if update_collision_flag_ui_properties in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.remove(update_collision_flag_ui_properties)

    if draw_stuff_post_update in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.remove(draw_stuff_post_update)

    if draw_stuff_pre_load_cleanup in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(draw_stuff_pre_load_cleanup)

