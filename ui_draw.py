import bpy
import bgl
from bpy.props import *
from mathutils import Vector

from . import_thps4 import THPS4ScnToScene, THPS4ColToScene
from . import_thug1 import THUG1ScnToScene
from . import_thug2 import THUG2ScnToScene, THUG2ColToScene
from . import_park import ImportTHUGPrk
from . import_thps2 import THPS2PsxToScene
from . tex import THUGImgToImages
from . qb import THUGImportLevelQB
from . skeleton import THUGImportSkeleton

from . scene_props import *
from . constants import *
from . material import *
from . constants import *
from . collision import *
from . export_thug1 import *
from . export_thug2 import *
from . export_shared import *
from . import_nodes import *
from . presets import *
from . script_template import *

# PROPERTIES
#############################################
draw_stuff_objects = set()
draw_handle = None
draw_stuff_dirty = True
draw_batches = []

# METHODS
#############################################
@bpy.app.handlers.persistent
def draw_stuff_post_update(scene):
    global draw_stuff_dirty, draw_stuff_objects
    if draw_stuff_dirty: return

    if not draw_stuff_objects:
        draw_stuff_dirty = True
        return

    dep = bpy.context.evaluated_depsgraph_get()
    for update in dep.updates:
        if update.id.original not in draw_stuff_objects:
            draw_stuff_dirty = True
            return
    
    
#----------------------------------------------------------------------------------
@bpy.app.handlers.persistent
def draw_stuff_pre_load_cleanup(*args):
    global draw_stuff_dirty, draw_stuff_objects, draw_batches
    draw_stuff_dirty = True
    draw_stuff_objects = set()
    draw_batches = []
    
#----------------------------------------------------------------------------------
@bpy.app.handlers.persistent
def draw_stuff():
    from . bglx import glColor4f, glVertex3f, glBegin, glEnd, GL_LINES, GL_TRIANGLES, GL_LINE_STRIP #, GL_POLYGON
    global draw_stuff_dirty, draw_stuff_objects, draw_batches
    ctx = bpy.context
    if not len(ctx.selected_objects) and not ctx.object:
        return
    if not bpy.context.window_manager.thug_show_face_collision_colors:
        return

    VERT_FLAG = FACE_FLAGS["mFD_VERT"]
    WALLRIDABLE_FLAG = FACE_FLAGS["mFD_WALL_RIDABLE"]
    TRIGGER_FLAG = FACE_FLAGS["mFD_TRIGGER"]
    NON_COLLIDABLE_FLAG = FACE_FLAGS["mFD_NON_COLLIDABLE"]

    _tmp_buf = bgl.Buffer(bgl.GL_FLOAT, 1)
    bgl.glGetFloatv(bgl.GL_POLYGON_OFFSET_FACTOR, _tmp_buf)
    old_offset_factor = _tmp_buf[0]
    bgl.glGetFloatv(bgl.GL_POLYGON_OFFSET_UNITS, _tmp_buf)
    old_offset_units = _tmp_buf[0]
    del _tmp_buf

    objects = set([ob.name for ob in ctx.selected_objects] if ctx.mode == "OBJECT" else [ctx.object.name])
    if draw_stuff_objects != objects:
        draw_stuff_dirty = True
        
    if not draw_stuff_dirty:
        bgl.glCullFace(bgl.GL_BACK)
        bgl.glEnable(bgl.GL_CULL_FACE)
        bgl.glEnable(bgl.GL_POLYGON_OFFSET_FILL)
        bgl.glPolygonOffset(-2, -2)

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA);

        prefs = ctx.preferences.addons[ADDON_NAME].preferences
        bgl.glLineWidth(prefs.line_width)
        
        for bi in draw_batches:
            if bi == None: continue
            bi[1].bind()
            bi[1].uniform_float("color", bi[2])
            bi[0].draw(bi[1])
            
        bgl.glPolygonOffset(old_offset_factor, old_offset_units)
        bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)
        bgl.glDisable(bgl.GL_CULL_FACE)
        return
        
    draw_batches = []
    bm = None
    try:
        bgl.glCullFace(bgl.GL_BACK)
        bgl.glEnable(bgl.GL_CULL_FACE)
        bgl.glEnable(bgl.GL_POLYGON_OFFSET_FILL)
        bgl.glPolygonOffset(-2, -2)

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA);

        prefs = ctx.preferences.addons[ADDON_NAME].preferences
        depsgraph = bpy.context.evaluated_depsgraph_get()

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
                    glColor4f(*prefs.rail_end_connection_color)
                    v = ob.matrix_world @ ob.data.splines[-1].points[-1].co.to_3d()
                    glVertex3f(v[0], v[1], v[2])
                    v = connects_to.matrix_world @ connects_to.data.splines[0].points[0].co.to_3d()
                    glVertex3f(v[0], v[1], v[2])
                    draw_batches.append(glEnd())

            # Draw previews for area lights - tube/sphere lights and area lights
            if (ob and ob.type == 'LAMP'):
                if ob.data.thug_light_props.light_type == 'TUBE':
                    if ob.data.thug_light_props.light_end_pos != (0, 0, 0):
                        glBegin(GL_LINES)
                        glColor4f(1.0, 0.75, 0.25, 1.0)
                        glVertex3f(ob.location[0], ob.location[1], ob.location[2])
                        glVertex3f(ob.location[0] + ob.data.thug_light_props.light_end_pos[0], ob.location[1] + ob.data.thug_light_props.light_end_pos[1], ob.location[2] + ob.data.thug_light_props.light_end_pos[2])
                        draw_batches.append(glEnd())
                    continue
                elif ob.data.thug_light_props.light_type == 'SPHERE':
                    continue
                elif ob.data.thug_light_props.light_type == 'AREA':
                    continue
                else:
                    continue
            elif (ob and ob.type == 'EMPTY'):
                if ob.thug_empty_props.empty_type == 'LightVolume' or ob.thug_empty_props.empty_type == 'CubemapProbe':
                    # Draw light volume bbox!
                    bbox, bbox_min, bbox_max, bbox_mid = get_bbox_from_node(ob)
                    
                    # 50% alpha, 2 pixel width line
                    bgl.glEnable(bgl.GL_BLEND)
                    glColor4f(1.0, 0.0, 0.0, 0.5)
                    bgl.glLineWidth(4)
                    
                    glBegin(GL_LINE_STRIP)
                    glVertex3f(*bbox[0])
                    glVertex3f(*bbox[1])
                    glVertex3f(*bbox[2])
                    glVertex3f(*bbox[3])
                    glVertex3f(*bbox[0])
                    glVertex3f(*bbox[4])
                    glVertex3f(*bbox[5])
                    glVertex3f(*bbox[6])
                    glVertex3f(*bbox[7])
                    glVertex3f(*bbox[4])
                    draw_batches.append(glEnd())

                    glBegin(bgl.GL_LINES)
                    glVertex3f(*bbox[1])
                    glVertex3f(*bbox[5])
                    glVertex3f(*bbox[2])
                    glVertex3f(*bbox[6])
                    glVertex3f(*bbox[3])
                    glVertex3f(*bbox[7])
                    draw_batches.append(glEnd())
                    
            if not ob or ob.type != "MESH":
                continue

            if ob.mode == "EDIT":
                bm.free()
                bm = bmesh.from_edit_mesh(ob.data).copy()
            else:
                bm.clear()
                bm.from_object(ob, depsgraph)

            arl = bm.edges.layers.int.get("thug_autorail")
            if arl:
                glColor4f(*prefs.autorail_edge_color)
                glBegin(GL_LINES)
                for edge in bm.edges:
                    if edge[arl] == AUTORAIL_NONE:
                        continue

                    for vert in edge.verts:
                        v = ob.matrix_world @ vert.co
                        glVertex3f(v[0], v[1], v[2])
                draw_batches.append(glEnd())

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
                            glColor4f(*prefs.bad_face_color)
                            glBegin(GL_TRIANGLES)
                            for vert in face.verts:
                                v = ob.matrix_world @ vert.co
                                glVertex3f(v[0], v[1], v[2])
                            draw_batches.append(glEnd())
                            continue

                    for face_flag, face_color in flag_stuff:
                        if face[cfl] & face_flag and (not drawn_face or prefs.mix_face_colors):
                            glColor4f(*face_color)
                            drawn_face = True

                            glBegin(GL_TRIANGLES)
                            for vert in face.verts:
                                v = ob.matrix_world @ vert.co
                                glVertex3f(v[0], v[1], v[2])
                            draw_batches.append(glEnd())
    finally:
        draw_stuff_dirty = False
        if bm: bm.free()
        bgl.glPolygonOffset(old_offset_factor, old_offset_units)
        bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)




#----------------------------------------------------------------------------------
def import_menu_func(self, context):
    self.layout.operator(THUG2ColToScene.bl_idname, text=THUG2ColToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THUG2ScnToScene.bl_idname, text=THUG2ScnToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THUG1ScnToScene.bl_idname, text=THUG1ScnToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THPS4ScnToScene.bl_idname, text=THPS4ScnToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THPS4ColToScene.bl_idname, text=THPS4ColToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THPS2PsxToScene.bl_idname, text=THPS2PsxToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THUGImportLevelQB.bl_idname, text=THUGImportLevelQB.bl_label, icon='PLUGIN')
    self.layout.operator(THUGImportSkeleton.bl_idname, text=THUGImportSkeleton.bl_label, icon='PLUGIN')
    self.layout.operator(ImportTHUGPrk.bl_idname, text=ImportTHUGPrk.bl_label, icon='PLUGIN')
    self.layout.operator(THUGImgToImages.bl_idname, text=THUGImgToImages.bl_label, icon='PLUGIN')
#----------------------------------------------------------------------------------    
def export_menu_func(self, context):
    self.layout.operator(SceneToTHPSLevel.bl_idname, text=SceneToTHPSLevel.bl_label, icon='PLUGIN')
    self.layout.operator(SceneToTHPSModel.bl_idname, text=SceneToTHPSModel.bl_label, icon='PLUGIN')
#----------------------------------------------------------------------------------
def add_menu_func(self, context):
    self.layout.menu(THUG_MT_PresetsMenu.bl_idname, text="THUG", icon='PLUGIN')
#----------------------------------------------------------------------------------
def register_menus():
    bpy.types.TOPBAR_MT_file_import.append(import_menu_func)
    bpy.types.TOPBAR_MT_file_export.append(export_menu_func)
    addPresetNodes()
    addPresetMesh()
    bpy.types.VIEW3D_MT_add.append(add_menu_func)
    script_template.init_templates()
#----------------------------------------------------------------------------------
def unregister_menus():
    bpy.types.TOPBAR_MT_file_import.remove(import_menu_func)
    bpy.types.TOPBAR_MT_file_export.remove(export_menu_func)
    bpy.types.VIEW3D_MT_add.remove(add_menu_func)
    clearPresetNodes()
    clearPresetMesh()


