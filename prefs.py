import bpy
from bpy.props import *
import bgl
from . constants import *

# PROPERTIES
#############################################
class THUGAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_NAME

    base_files_dir = StringProperty(
        name="Base files directory",
        subtype='DIR_PATH',
        default="D:\\thug_tools\\",
        )

    line_width = FloatProperty(name="Line Width", min=0, max=15, default=10)

    autorail_edge_color = FloatVectorProperty(
        name="Mesh Rail Edge Color",
        size=4,
        min=0.0,
        max=1.0,
        subtype="COLOR",
        default=(1.0, 0.0, 0.0, 1.0))

    rail_end_connection_color = FloatVectorProperty(
        name="Rail End Connection Color",
        size=4,
        min=0.0,
        max=1.0,
        subtype="COLOR",
        default=(1.0, 1.0, 0.0, 1.0))

    bad_face_color = FloatVectorProperty(
        name="Bad Face Color",
        size=4,
        min=0.0,
        max=1.0,
        subtype="COLOR",
        default=(1.0, 0.0, 1.0, 0.5))

    vert_face_color = FloatVectorProperty(
        name="Vert Face Color",
        size=4,
        min=0.0,
        max=1.0,
        subtype="COLOR",
        default=(0.0, 0.0, 1.0, 0.5))

    wallridable_face_color = FloatVectorProperty(
        name="Wallridable Face Color",
        size=4,
        min=0.0,
        max=1.0,
        subtype="COLOR",
        default=(0.0, 1.0, 1.0, 0.5))

    trigger_face_color = FloatVectorProperty(
        name="Trigger Face Color",
        size=4,
        min=0.0,
        max=1.0,
        subtype="COLOR",
        default=(0.0, 1.0, 0.0, 0.5))

    non_collidable_face_color = FloatVectorProperty(
        name="Non Collidable Face Color",
        size=4,
        min=0.0,
        max=1.0,
        subtype="COLOR",
        default=(1.0, 1.0, 0.0, 0.5))

    mix_face_colors = BoolProperty(name="Mix Face Colors", default=False)
    show_bad_face_colors = BoolProperty(name="Hightlight Bad Faces", default=True,
        description="Colorize faces with bad collision flag combinations using Bad Face Color.")

    object_settings_tools = BoolProperty(name="Show Object Settings in the Tools Tab", default=True)
    material_settings_tools = BoolProperty(name="Show Material Settings in the Tools Tab", default=True)
    material_pass_settings_tools = BoolProperty(name="Show Material Pass Settings in the Tools Tab", default=True)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "base_files_dir")
        base_files_dir_error = _get_base_files_dir_error(self)
        if base_files_dir_error:
            layout.label(
                text="Incorrect path: {}".format(base_files_dir_error),
                icon="ERROR")

        for prop in ["autorail_edge_color",
                     "rail_end_connection_color",
                     "bad_face_color",
                     "vert_face_color",
                     "wallridable_face_color",
                     "trigger_face_color",
                     "non_collidable_face_color",]:
            layout.row().prop(self, prop)
        row = layout.row()
        row.prop(self, "mix_face_colors")
        row.prop(self, "show_bad_face_colors")
        row.prop(self, "line_width")
        layout.prop(self, "object_settings_tools")
        layout.prop(self, "material_settings_tools")
        layout.prop(self, "material_pass_settings_tools")


# METHODS
#############################################
def _get_base_files_dir_error(prefs):
    self = prefs
    base_files_dir_error = None
    if not os.path.exists(self.base_files_dir):
        base_files_dir_error = "The path doesn't exist."
    elif not os.path.exists(os.path.join(self.base_files_dir, "roq.exe")):
        base_files_dir_error = "The folder doesn't contain the roq compiler."
    elif not all(os.path.exists(os.path.join(self.base_files_dir, "default_sky", sky_file))
                 for sky_file in
                 ["THUG_sky.scn.xbx", "THUG_sky.tex.xbx", "THUG2_sky.scn.xbx", "THUG2_sky.tex.xbx"]):
        base_files_dir_error = "The folder doesn't contain the default sky files."
    return base_files_dir_error