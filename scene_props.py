import bpy
import bgl
from bpy.props import *


# METHODS
#############################################
def _gap_props_end_object_changed(gap_props, context):
    eo = bpy.data.objects.get(gap_props.end_object)
    if not eo:
        return
    eo.thug_triggerscript_props.triggerscript_type = "None"
    eo.thug_triggerscript_props.gap_props.reserved_by = gap_props.id_data.name

# PROPERTIES
#############################################
class THUGGapProps(bpy.types.PropertyGroup):
    flags = {
        "CANCEL_GROUND": 0x00000001,
        "CANCEL_AIR": 0x00000002,
        "CANCEL_RAIL": 0x00000004,
        "CANCEL_WALL": 0x00000008,
        "CANCEL_LIP": 0x00000010,
        "CANCEL_WALLPLANT": 0x00000020,
        "CANCEL_MANUAL": 0x00000040,
        "CANCEL_HANG": 0x00000080,
        "CANCEL_LADDER": 0x00000100,
        "CANCEL_SKATE": 0x00000200,
        "CANCEL_WALK": 0x00000400,
        "CANCEL_DRIVE": 0x00000800,
        "REQUIRE_GROUND": 0x00010000,
        "REQUIRE_AIR": 0x00020000,
        "REQUIRE_RAIL": 0x00040000,
        "REQUIRE_WALL": 0x00080000,
        "REQUIRE_LIP": 0x00100000,
        "REQUIRE_WALLPLANT": 0x00200000,
        "REQUIRE_MANUAL": 0x00400000,
        "REQUIRE_HANG": 0x00800000,
        "REQUIRE_LADDER": 0x01000000,
        "REQUIRE_SKATE": 0x02000000,
        "REQUIRE_WALK": 0x04000000,
        "REQUIRE_DRIVE": 0x08000000,
    }

    CANCEL_MASK = 0x0000FFFF
    REQUIRE_MASK = 0xFFFF0000

    CANCEL_GROUND = BoolProperty(name="CANCEL_GROUND", default=True)
    CANCEL_AIR = BoolProperty(name="CANCEL_AIR", default=False)
    CANCEL_RAIL = BoolProperty(name="CANCEL_RAIL", default=False)
    CANCEL_WALL = BoolProperty(name="CANCEL_WALL", default=False)
    CANCEL_LIP = BoolProperty(name="CANCEL_LIP", default=False)
    CANCEL_WALLPLANT = BoolProperty(name="CANCEL_WALLPLANT", default=False)
    CANCEL_MANUAL = BoolProperty(name="CANCEL_MANUAL", default=False)
    CANCEL_HANG = BoolProperty(name="CANCEL_HANG", default=False)
    CANCEL_LADDER = BoolProperty(name="CANCEL_LADDER", default=False)
    CANCEL_SKATE = BoolProperty(name="CANCEL_SKATE", default=False)
    CANCEL_WALK = BoolProperty(name="CANCEL_WALK", default=False)
    CANCEL_DRIVE = BoolProperty(name="CANCEL_DRIVE", default=False)
    REQUIRE_GROUND = BoolProperty(name="REQUIRE_GROUND", default=False)
    REQUIRE_AIR = BoolProperty(name="REQUIRE_AIR", default=False)
    REQUIRE_RAIL = BoolProperty(name="REQUIRE_RAIL", default=False)
    REQUIRE_WALL = BoolProperty(name="REQUIRE_WALL", default=False)
    REQUIRE_LIP = BoolProperty(name="REQUIRE_LIP", default=False)
    REQUIRE_WALLPLANT = BoolProperty(name="REQUIRE_WALLPLANT", default=False)
    REQUIRE_MANUAL = BoolProperty(name="REQUIRE_MANUAL", default=False)
    REQUIRE_HANG = BoolProperty(name="REQUIRE_HANG", default=False)
    REQUIRE_LADDER = BoolProperty(name="REQUIRE_LADDER", default=False)
    REQUIRE_SKATE = BoolProperty(name="REQUIRE_SKATE", default=False)
    REQUIRE_WALK = BoolProperty(name="REQUIRE_WALK", default=False)
    REQUIRE_DRIVE = BoolProperty(name="REQUIRE_DRIVE", default=False)

    name = StringProperty(name="Gap Name", default="Gap")
    score = IntProperty(name="Score", min=0, max=2**30, default=100)
    """
    trickstring = StringProperty(name="Trick", default="")
    spin = IntProperty(name="Required Spin", min=0, max=2**31, default=0, description="Should be a multiple of 180.")
    """
    end_object = StringProperty(
        name="End",
        description="The trigger object that that will end the gap.",
        default="",
        update=_gap_props_end_object_changed)
    two_way = BoolProperty(name="Two way", default=False)

    reserved_by = StringProperty() # the start gap object this object's reserved by

    def draw(self, panel, context):
        col = panel.layout.box().column()
        col.prop(self, "name")
        col.prop(self, "score")
        col.prop_search(self, "end_object", context.scene, "objects")
        col.prop(self, "two_way")

        for flag in sorted(self.flags):
            col.prop(self, flag)


class THUGObjectTriggerScriptProps(bpy.types.PropertyGroup):
    triggerscript_type = EnumProperty(items=(
        ("None", "None", ""),
        ("Killskater", "Killskater", "Bail the skater and restart them at the given node."),
        ("Killskater_Water", "Killskater (Water)", "Bail the skater and restart them at the given node."),
        ("Teleport", "Teleport", "Teleport the skater to a given node without breaking their combo."),
        ("Custom", "Custom", "Runs a custom script."),
        # ("Gap", "Gap", "Gap."),
        ), name="TriggerScript Type", default="None")
    target_node = StringProperty(name="Target Node")
    custom_name = StringProperty(name="Custom Script Name")
    # gap_props = PointerProperty(type=THUGGapProps)

class THUGProximNodeProps(bpy.types.PropertyGroup):
    proxim_type = EnumProperty(items=(
        ("Camera", "Camera", ""), 
        ("Other", "Other", "")), 
    name="Proximity Type",
    default="Camera")
    radius = IntProperty(name="Radius", min=0, max=1000000, default=150)
    
class THUGGenericNodeProps(bpy.types.PropertyGroup):
    generic_type = EnumProperty(items=(
        ("Crown", "KOTH Crown", ""), 
        ("Other", "Other", "")) 
    ,name="Node Type",default="Crown")
    
class THUGGameObjectProps(bpy.types.PropertyGroup):
    go_type = EnumProperty(items=(
        ("Ghost", "Ghost", "No model, used for game logic."), 
        ("Flag_Red", "CTF Flag - Red", "Red team flag for CTF."), 
        ("Flag_Red_Base", "CTF Base - Red", "Red team base for CTF."), 
        ("Flag_Yellow", "CTF Flag - Yellow", "Yellow team flag for CTF."), 
        ("Flag_Yellow_Base", "CTF Base - Yellow", "Yellow team base for CTF."), 
        ("Flag_Green", "CTF Flag - Green", "Green team flag for CTF."), 
        ("Flag_Green_Base", "CTF Base - Green", "Green team base for CTF."), 
        ("Flag_Blue", "CTF Flag - Blue", "Blue team flag for CTF."), 
        ("Flag_Blue_Base", "CTF Base - Blue", "Blue team base for CTF."), 
        ("Secret_Tape", "Secret Tape", ""), 
        ("Combo_C", "Combo Letter C", ""), 
        ("Combo_O", "Combo Letter O", ""), 
        ("Combo_M", "Combo Letter M", ""), 
        ("Combo_B", "Combo Letter B", "")), 
    name="Type", default="Ghost")
    go_model = StringProperty(name="Model path", description="Path to the model, relative to Data/Models/.")
    go_suspend = IntProperty(name="Suspend Distance", description="Distance at which the logic/motion of the object pauses.", min=0, max=1000000, default=0)
    
class THUGPathNodeProps(bpy.types.PropertyGroup):
    name = StringProperty(name="Node Name")
    script_name = StringProperty(name="TriggerScript Name")
    
    def register():
        print("adding new path node struct")
    
class THUGRestartProps(bpy.types.PropertyGroup):

    restart_p1 = BoolProperty(name="Player 1", default=False)
    restart_p2 = BoolProperty(name="Player 2", default=False)
    restart_gen = BoolProperty(name="Generic", default=False)
    restart_multi = BoolProperty(name="Multiplayer", default=False)
    restart_team = BoolProperty(name="Team", default=False)
    restart_horse = BoolProperty(name="Horse", default=False)
    restart_ctf = BoolProperty(name="CTF", default=False)
    restart_type = EnumProperty(items=(
        ("Player1", "Player 1", ""),
        ("Player2", "Player 2", ""),
        ("Generic", "Generic", ""),
        ("Team", "Team", ""),
        ("Multiplayer", "Multiplayer", ""),
        ("Horse", "Horse", ""),
        ("CTF", "CTF", "")),
    name="Primary Type", default="Player1")
    restart_name = StringProperty(name="Restart Name", description="Name that appears in restart menu.")

class THUGEmptyProps(bpy.types.PropertyGroup):
    empty_type = EnumProperty(items=(
        ("None", "None", ""),
        ("Restart", "Restart", "Player restarts."),
        ("GenericNode", "Generic Node", "KOTH crown and other objects."),
        ("Pedestrian", "Pedestrian", "Not currently implemented."),
        ("Vehicle", "Vehicle", "Not currently implemented."),
        ("ProximNode", "Proximity Node", "Node that can fire events when objects are inside its radius."),
        ("GameObject", "Game Object", "CTF Flags, COMBO letters, etc."),
        ("BouncyObject", "Bouncy Object", "Legacy node type, not used, only for identification in imported levels."),
        ("Custom", "Custom", ""),
        ), name="Node Type", default="None")

    #empty_restart_name = StringProperty(name="Restart Name", description="Not currently used.")
    """
    restart_singleplayer = BoolProperty(name="Singleplayer Restart", default=True)
    restart_multiplayer = BoolProperty(name="Multiplayer Restart", default=True)
    restart_team = BoolProperty(name="Team Restart", default=True)
    """



