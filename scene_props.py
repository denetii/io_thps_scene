import bpy
import bgl
from bpy.props import *
from . constants import *
from . helpers import *
from . autorail import *
from . collision import *
from . material import *
from . ui_draw import *
from . import_nodes import THUGImportNodeArray
from . presets import *

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

# Applies a context-specific mesh as a child of the empty when applicable
# This just makes it easier to see presets like restarts, CTF flags etc
def thug_empty_update(self, context):
    if context.object.type == "EMPTY":
        ob = context.object
        
        for mdl_ob in ob.children:
            if mdl_ob.name.endswith('_MDL'):
                context.scene.objects.unlink(mdl_ob)
                bpy.data.objects.remove(mdl_ob)
            
        if ob.thug_empty_props.empty_type == 'Restart':
            mdl_mesh = 'Sk3Ed_RS_1p'
            if ob.thug_restart_props.restart_type == 'Player2':
                mdl_mesh = 'Sk3Ed_RS_Mp'
            elif ob.thug_restart_props.restart_type == 'Multiplayer':
                mdl_mesh = 'Sk3Ed_RS_Ho'
            elif ob.thug_restart_props.restart_type == 'Horse':
                mdl_mesh = 'Sk3Ed_RS_Ho'
            elif ob.thug_restart_props.restart_type == 'CTF':
                mdl_mesh = 'Sk3Ed_RS_Ho'
            mdl_ob = append_from_dictionary('presets', mdl_mesh, context.scene)
            mdl_ob.name = ob.name + '_MDL'
            mdl_ob.location = [ 0, 0, 0 ]
            mdl_ob.rotation_euler = [ 0, 0, 0 ]
            mdl_ob.parent = ob
            mdl_ob.hide_select = True
            mdl_ob.hide_render = True
            mdl_ob.thug_export_scene = False
            mdl_ob.thug_export_collision = False
            ob.empty_draw_type = 'CUBE'
            ob.empty_draw_size = 36
            
        if ob.thug_empty_props.empty_type == 'GameObject':
            mdl_mesh = ''
            if ob.thug_go_props.go_type == 'Flag_Blue' or ob.thug_go_props.go_type == 'Team_Blue' :
                mdl_mesh = 'CTF_Flag_Blue'
            elif ob.thug_go_props.go_type == 'Flag_Red' or ob.thug_go_props.go_type == 'Team_Red':
                mdl_mesh = 'CTF_Flag_Red'
            elif ob.thug_go_props.go_type == 'Flag_Green' or ob.thug_go_props.go_type == 'Team_Green':
                mdl_mesh = 'CTF_Flag_Green'
            elif ob.thug_go_props.go_type == 'Flag_Yellow' or ob.thug_go_props.go_type == 'Team_Yellow':
                mdl_mesh = 'CTF_Flag_Yellow'
                
            if ob.thug_go_props.go_type == 'Flag_Blue_Base':
                mdl_mesh = 'CTF_Base_Blue'
            elif ob.thug_go_props.go_type == 'Flag_Red_Base':
                mdl_mesh = 'CTF_Base_Red'
            elif ob.thug_go_props.go_type == 'Flag_Green_Base':
                mdl_mesh = 'CTF_Base_Green'
            elif ob.thug_go_props.go_type == 'Flag_Yellow_Base':
                mdl_mesh = 'CTF_Base_Yellow'
            elif ob.thug_go_props.go_type == 'Secret_Tape':
                mdl_mesh = 'SecretTape'
                
            elif ob.thug_go_props.go_type.startswith('Combo_'):
                mdl_mesh = ob.thug_go_props.go_type
                
            if mdl_mesh != '':
                mdl_ob = append_from_dictionary('presets', mdl_mesh, context.scene)
                mdl_ob.name = ob.name + '_MDL'
                mdl_ob.location = [ 0, 0, 0 ]
                mdl_ob.rotation_euler = [ 0, 0, 0 ]
                mdl_ob.parent = ob
                mdl_ob.hide_select = True
                mdl_ob.hide_render = True
                mdl_ob.thug_export_scene = False
                mdl_ob.thug_export_collision = False
            ob.empty_draw_type = 'CUBE'
            ob.empty_draw_size = 36
            
        elif ob.thug_empty_props.empty_type == 'GenericNode' and \
        ob.thug_generic_props.generic_type == 'Crown':
            mdl_ob = append_from_dictionary('presets', 'Sk3Ed_RS_KOTH', context.scene)
            mdl_ob.name = ob.name + '_MDL'
            mdl_ob.location = [ 0, 0, 0 ]
            mdl_ob.rotation_euler = [ 0, 0, 0 ]
            mdl_ob.parent = ob
            mdl_ob.hide_select = True
            mdl_ob.hide_render = True
            mdl_ob.thug_export_scene = False
            mdl_ob.thug_export_collision = False
            ob.empty_draw_type = 'CUBE'
            ob.empty_draw_size = 42
            
        elif ob.thug_empty_props.empty_type == 'Pedestrian':
            mdl_ob = append_from_dictionary('presets', 'Ped01', context.scene)
            mdl_ob.name = ob.name + '_MDL'
            mdl_ob.location = [ 0, 0, 0 ]
            mdl_ob.rotation_euler = [ 0, 0, 0 ]
            mdl_ob.parent = ob
            mdl_ob.hide_select = True
            mdl_ob.hide_render = True
            mdl_ob.thug_export_scene = False
            mdl_ob.thug_export_collision = False
            ob.empty_draw_type = 'CUBE'
            ob.empty_draw_size = 42
            
        elif ob.thug_empty_props.empty_type == 'Vehicle':
            mdl_ob = append_from_dictionary('presets', 'Veh_Taxi', context.scene)
            mdl_ob.name = ob.name + '_MDL'
            mdl_ob.location = [ 0, 0, 0 ]
            mdl_ob.rotation_euler = [ 0, 0, 0 ]
            mdl_ob.parent = ob
            mdl_ob.hide_select = True
            mdl_ob.hide_render = True
            mdl_ob.thug_export_scene = False
            mdl_ob.thug_export_collision = False
            ob.empty_draw_type = 'CUBE'
            ob.empty_draw_size = 42
            
            
        
#----------------------------------------------------------------------------------
#- Defines the Class of an empty
#----------------------------------------------------------------------------------
class THUGEmptyProps(bpy.types.PropertyGroup):
    empty_type = EnumProperty(items=(
        ("None", "None", ""),
        ("Restart", "Restart", "Player restarts."),
        ("GenericNode", "Generic Node", "KOTH crown and other objects."),
        ("Pedestrian", "Pedestrian", "Not currently implemented."),
        ("Vehicle", "Vehicle", "Not currently implemented."),
        ("ProximNode", "Proximity Node", "Node that can fire events when objects are inside its radius."),
        ("EmitterObject", "Emitter Object", "Node used to play audio streams (typically, ambient sounds in a level)."),
        ("GameObject", "Game Object", "CTF Flags, COMBO letters, etc."),
        ("BouncyObject", "Bouncy Object", "Legacy node type, not used, only for identification in imported levels."),
        ("ParticleObject", "Particle Object", "Used to preserve particle systems in imported levels."),
        ("Custom", "Custom", ""),
        ), name="Node Type", default="None", update=thug_empty_update)


#----------------------------------------------------------------------------------
#- Currently unused
#----------------------------------------------------------------------------------
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

#----------------------------------------------------------------------------------
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


#----------------------------------------------------------------------------------
#- Proximity node properties
#----------------------------------------------------------------------------------
class THUGProximNodeProps(bpy.types.PropertyGroup):
    proxim_type = EnumProperty(items=(
        ("Camera", "Camera", ""), 
        ("Other", "Other", "")), 
    name="Type", default="Camera")
    proxim_shape = EnumProperty(items=(
        ("BoundingBox", "Bounding Box", ""), 
        ("Sphere", "Sphere", "")), 
    name="Shape", default="BoundingBox")
    proxim_object = BoolProperty(name="Object", default=True)
    proxim_rendertoviewport = BoolProperty(name="RenderToViewport", default=True)
    proxim_selectrenderonly = BoolProperty(name="SelectRenderOnly", default=True)
    proxim_radius = IntProperty(name="Radius", min=0, max=1000000, default=150)
    

#----------------------------------------------------------------------------------
#- Emitter properties
#----------------------------------------------------------------------------------
class THUGEmitterProps(bpy.types.PropertyGroup):
    emit_type = StringProperty(name="Type", default="BoundingBox")
    emit_radius = FloatProperty(name="Radius", min=0, max=1000000, default=0)
    
#----------------------------------------------------------------------------------
#- If you know of another thing GenericNode is used for, let me know!
#----------------------------------------------------------------------------------
class THUGGenericNodeProps(bpy.types.PropertyGroup):
    generic_type = EnumProperty(items=(
        ("Crown", "KOTH Crown", ""), 
        ("Other", "Other", "")) 
    ,name="Node Type",default="Crown")
    

#----------------------------------------------------------------------------------
#- Game objects - models with collision that affect gameplay
#----------------------------------------------------------------------------------
class THUGGameObjectProps(bpy.types.PropertyGroup):
    go_type = EnumProperty(items=(
        ("Ghost", "Ghost", "No model, used for game logic."), 
        ("Flag_Red", "CTF Flag - Red", "Red team flag for CTF."), 
        ("Flag_Blue", "CTF Flag - Blue", "Blue team flag for CTF."), 
        ("Flag_Green", "CTF Flag - Green", "Green team flag for CTF."), 
        ("Flag_Yellow", "CTF Flag - Yellow", "Yellow team flag for CTF."), 
        ("Flag_Red_Base", "CTF Base - Red", "Red team base for CTF."), 
        ("Flag_Blue_Base", "CTF Base - Blue", "Blue team base for CTF."), 
        ("Flag_Green_Base", "CTF Base - Green", "Green team base for CTF."), 
        ("Flag_Yellow_Base", "CTF Base - Yellow", "Yellow team base for CTF."), 
        ("Team_Red", "Team Flag - Red", "Red team selection flag."), 
        ("Team_Blue", "Team Flag - Blue", "Blue team selection flag."), 
        ("Team_Green", "Team Flag - Green", "Green team selection flag."), 
        ("Team_Yellow", "Team Flag - Yellow", "Yellow team selection flag."), 
        ("Secret_Tape", "Secret Tape", ""), 
        ("Combo_C", "Combo Letter C", ""), 
        ("Combo_O", "Combo Letter O", ""), 
        ("Combo_M", "Combo Letter M", ""), 
        ("Combo_B", "Combo Letter B", ""), 
        ("Custom", "Custom", "Specify a custom type and model.")), 
    name="Type", default="Ghost", update=thug_empty_update)
    go_type_other = StringProperty(name="Type", description="Custom type.")
    go_model = StringProperty(name="Model path", default="none", description="Path to the model, relative to Data/Models/.")
    go_suspend = IntProperty(name="Suspend Distance", description="Distance at which the logic/motion of the object pauses.", min=0, max=1000000, default=0)
    
    
class THUGBouncyProps(bpy.types.PropertyGroup):
    contact = FloatVectorProperty(name="Contact", description="A point used for collision detection.")
    
#----------------------------------------------------------------------------------
#- Level obj properties! There's a lot of them!
#----------------------------------------------------------------------------------
class THUGLevelObjectProps(bpy.types.PropertyGroup):
    obj_type = StringProperty(name="Type", description="Type of level object.")
    obj_bouncy = BoolProperty(name="Bouncy", description="Enable collision physics on this object.")
    center_of_mass = FloatVectorProperty(name="Center Of Mass")
    contacts = CollectionProperty(type=THUGBouncyProps, name="Contacts")
    coeff_restitution = FloatProperty(name="coeff_restitution", min=0, max=1024, default=0.25)
    coeff_friction = FloatProperty(name="coeff_friction", min=0, max=1024, default=0.25)
    skater_collision_impulse_factor = FloatProperty(name="skater_collision_impulse_factor", min=0, max=1024, default=1.5)
    skater_collision_rotation_factor = FloatProperty(name="skater_collision_rotation_factor", min=0, max=1024, default=1)
    skater_collision_assent = IntProperty(name="skater_collision_assent", min=0, max=1024, default=0)
    skater_collision_radius = IntProperty(name="skater_collision_radius", min=0, max=1024, default=0)
    mass_over_moment = FloatProperty(name="mass_over_moment", min=-1, max=1024, default=-1, description="Use value of -1 to not export this property to the QB.")
    stuckscript = StringProperty(name="stuckscript")
    SoundType = StringProperty(name="Sound", description="Sound used when colliding with the object.")
    
#----------------------------------------------------------------------------------
#- Properties for individual nodes along a path (rail, ladder, waypoints)
#----------------------------------------------------------------------------------
class THUGPathNodeProps(bpy.types.PropertyGroup):
    name = StringProperty(name="Node Name")
    waypt_type = StringProperty(name="Type")
    script_name = StringProperty(name="TriggerScript Name")
    terrain = EnumProperty(
        name="Terrain Type",
        items=[(t, t, t) for t in ["None", "Auto"] + [tt for tt in TERRAIN_TYPES if tt.lower().startswith("grind")]])
    #terrain = StringProperty(name="Terrain Type")
    spawnobjscript = StringProperty(name="SpawnObj Script")
    PedType = StringProperty(name="PedType")
    do_continue = BoolProperty(name="Continue")
    JumpToNextNode = BoolProperty(name="JumpToNextNode")
    Priority = StringProperty(name="Priority")
    ContinueWeight = FloatProperty(name="Continue Weight")
    SkateAction = StringProperty(name="Skate Action")
    JumpHeight = FloatProperty(name="Jump Height")
    skaterai_terrain = StringProperty(name="TerrainType")
    ManualType = StringProperty(name="ManualType")
    Deceleration = FloatProperty(name="Deceleration")
    StopTime = FloatProperty(name="StopTime")
    SpinAngle = FloatProperty(name="SpinAngle")
    SpinDirection = StringProperty(name="SpinDirection")
    #def register():
        #print("adding new path node struct")
        
#----------------------------------------------------------------------------------
#- Restart properties
#----------------------------------------------------------------------------------
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
    name="Primary Type", default="Player1", update=thug_empty_update)
    restart_name = StringProperty(name="Restart Name", description="Name that appears in restart menu.")
    

#----------------------------------------------------------------------------------
#- Pedestrian properties
#----------------------------------------------------------------------------------
class THUGPedestrianProps(bpy.types.PropertyGroup):
    ped_type = StringProperty(name="Type", default="Ped_From_Profile")
    ped_source = EnumProperty(name="Source", items=(
        ( 'Profile', 'Profile', 'Pedestrian model is defined in a profile.'),
        ( 'Model', 'Model', 'Use an explicit path to the mdl file.')
    ), default="Profile")
    ped_profile = StringProperty(name="Profile", default="random_male_profile", description="Pedestrian profile name.")
    ped_skeleton = StringProperty(name="Skeleton", default="THPS5_human")
    ped_animset = StringProperty(name="Anim Set", default="animload_THPS5_human", description="Anim set to load for this pedestrian.")
    ped_extra_anims = StringProperty(name="Extra Anims", description="Additional anim sets to load.")
    ped_suspend = IntProperty(name="Suspend Distance", description="Distance at which the logic/motion pauses.", min=0, max=1000000, default=0)
    ped_model = StringProperty(name="Model", default="", description="Relative path to mdl file.")
    ped_nologic = BoolProperty(name="No Logic", default=False, description="Pedestrian will not have any logic, only animations.")
    
#----------------------------------------------------------------------------------
#- Vehicle properties
#----------------------------------------------------------------------------------
class THUGVehicleProps(bpy.types.PropertyGroup):
    veh_type = StringProperty(name="Type", default="Generic", description="Type of vehicle.")
    veh_model = StringProperty(name="Model", default="", description="Relative path to mdl file.")
    veh_skeleton = StringProperty(name="Skeleton", default="car", description="Name of skeleton.")
    veh_suspend = IntProperty(name="Suspend Distance", description="Distance at which the logic/motion pauses.", min=0, max=1000000, default=0)
    veh_norail = BoolProperty(name="No Rails", default=False, description="Vehicle will not have any rails (even if the model does).")
    veh_noskitch = BoolProperty(name="No Skitch", default=False, description="Vehicle cannot be skitched.")
    veh_usemodellights = BoolProperty(name="Use Model Lights", default=False)
    veh_allowreplacetex = BoolProperty(name="Texture Replacement", default=False, description="Allow model textures to be changed by scripts.")
    
def thug_light_update(self, context):
    if context.object.type == "LAMP" and context.object.data.type == "POINT":
        context.object.data.distance = self.light_radius[0]
    
#----------------------------------------------------------------------------------
#- Light properties
#----------------------------------------------------------------------------------
class THUGLightProps(bpy.types.PropertyGroup):
    light_radius = FloatVectorProperty(name="Radius", size=2, min=0, max=128000, default=[300,300], description="Inner/outer radius.", update=thug_light_update)
    light_excludeskater = BoolProperty(name="Exclude Skater", default=False, description="Light will not influence the skater.")
    light_excludelevel = BoolProperty(name="Exclude Level", default=False, description="Light will not influence the scene.")
    
#----------------------------------------------------------------------------------
#- Particle system properties! There's a lot of them!
#----------------------------------------------------------------------------------
class THUGParticleProps(bpy.types.PropertyGroup):
    particle_boxdimsstart = FloatVectorProperty(name="Box Dims Start")
    particle_boxdimsmid = FloatVectorProperty(name="Box Dims Mid")
    particle_boxdimsend = FloatVectorProperty(name="Box Dims End")
    particle_usestartpos = BoolProperty(name="Use Start Pos", default=False)
    particle_startposition = FloatVectorProperty(name="Start Position")
    particle_midposition = FloatVectorProperty(name="Mid Position")
    particle_endposition = FloatVectorProperty(name="End Position")
    
    particle_texture = StringProperty(name="Texture", description="Texture assigned to the particles.")
    particle_usemidpoint = BoolProperty(name="Use Midpoint", default=False)
    particle_profile = StringProperty(name="Profile", default="Default")
    particle_type = StringProperty(name="Type", default="NEWFLAT")
    particle_blendmode = StringProperty(name="Blend Mode", default="BLEND")
    particle_fixedalpha = IntProperty(name="Fixed Alpha", min=0, max=256, default=128)
    particle_alphacutoff = IntProperty(name="Alpha Cutoff", soft_min=0, max=256, default=-1)
    particle_maxstreams = IntProperty(name="Max Streams", soft_min=0, max=256, default=-1)
    particle_emitrate = FloatProperty(name="Emit Rate", soft_min=0, max=4096, default=-1)
    particle_lifetime = FloatProperty(name="Lifetime", soft_min=0, max=128000, default=-1)
    particle_midpointpct = IntProperty(name="Midpoint Pct", soft_min=0, max=100, default=-1)
    particle_radius = FloatVectorProperty(name="Radius", description="Start, mid and end radius.", default=(-1,-1,-1))
    particle_radiusspread = FloatVectorProperty(name="Radius Spread", default=(-1, -1, -1))
    particle_startcolor = FloatVectorProperty(name="Start Color",
                           subtype='COLOR',
                           default=(1.0, 1.0, 1.0, 1.0),
                           size=4,
                           min=0.0, max=1.0,
                           description="Start Color (with alpha).")
    particle_usecolormidtime = BoolProperty(name="Use Color Mid Time", default=False)
    particle_colormidtime = FloatProperty(name="Color Mid Time", min=0, max=128000, default=50)
    particle_midcolor = FloatVectorProperty(name="Mid Color",
                           subtype='COLOR',
                           default=(1.0, 1.0, 1.0, 1.0),
                           size=4,
                           min=0.0, max=1.0,
                           description="Mid Color (with alpha).")
    particle_endcolor = FloatVectorProperty(name="End Color",
                           subtype='COLOR',
                           default=(1.0, 1.0, 1.0, 1.0),
                           size=4,
                           min=0.0, max=1.0,
                           description="End Color (with alpha).")
    particle_suspend = IntProperty(name="Suspend Distance", description="Distance at which the system pauses.", min=0, max=1000000, default=0)
    
    # Even more particle properties that I missed the first time!
    #EmitSize = FloatVectorProperty(name="Emit Size", size=3, min=0, max=4096, default=16)
    EmitScript = StringProperty(name="Emit Script")
    Force = FloatVectorProperty(name="Emit Force", size=3, soft_min=0, soft_max=4096, default=(-1, -1, -1))
    Speed = FloatVectorProperty(name="Speed", size=2, soft_min=0, soft_max=4096, default=(-1, -1))
    Size = FloatVectorProperty(name="Emit Size", description="Width/height.", size=2, soft_min=0, soft_max=4096, default=(-1, -1))
    Width = FloatVectorProperty(name="Start/End Width", size=2, soft_min=0, soft_max=4096, default=(-1, -1))
    AngleSpread = FloatProperty(name="Angle Spread", soft_min=0, soft_max=4096, default=-1)
    UsePulseEmit = BoolProperty(name="UsePulseEmit", default=False)
    RandomEmitRate = BoolProperty(name="RandomEmitRate", default=False)
    RandomEmitDelay = BoolProperty(name="RandomEmitDelay", default=False)
    UseMidTime = BoolProperty(name="UseMidTime", default=False)
    MidTime = IntProperty(name="MidTime", default=-1)
    EmitTarget = FloatVectorProperty(name="Emit Target", size=3, default=(-1, -1, -1))
    EmitRate1 = FloatVectorProperty(name="Emit Rate 1", size=3, default=(-1, -1, -1))
    EmitRate1Delay = FloatVectorProperty(name="Emit Delay 1", size=3, default=(-1, -1, -1))
    EmitRate2 = FloatVectorProperty(name="Emit Rate 2", size=3, default=(-1, -1, -1))
    EmitRate2Delay = FloatVectorProperty(name="Emit Delay 2", size=3, default=(-1, -1, -1))
    
# METHODS
#############################################
#----------------------------------------------------------------------------------
def __init_wm_props():
    def make_updater(flag):
        return lambda wm, ctx: update_collision_flag_mesh(wm, ctx, flag)

    FLAG_NAMES = {
        "mFD_VERT": ("Vert", "Vert. This face is a vert (used for ramps)."),
        "mFD_WALL_RIDABLE": ("Wallridable", "Wallridable. This face is wallridable"),
        "mFD_NON_COLLIDABLE": ("Non-Collidable", "Non-Collidable. The skater won't collide with this face. Used for triggers."),
        "mFD_NO_SKATER_SHADOW": ("No Skater Shadow", "No Skater Shadow"),
        "mFD_NO_SKATER_SHADOW_WALL": ("No Skater Shadow Wall", "No Skater Shadow Wall"),
        "mFD_TRIGGER": ("Trigger", "Trigger. The object's TriggerScript will be called when a skater goes through this face. Caution: if the object doesn't have a triggerscript defined the game will crash!"),
    }

    for ff in SETTABLE_FACE_FLAGS:
        fns = FLAG_NAMES.get(ff)
        if fns:
            fn, fd = fns
        else:
            fn = ff
            fd = ff
        setattr(bpy.types.WindowManager,
                "thug_face_" + ff,
                BoolProperty(name=fn,
                             description=fd,
                             update=make_updater(ff)))

    bpy.types.WindowManager.thug_autorail_terrain_type = EnumProperty(
        name="Autorail Terrain Type",
        items=[(t, t, t) for t in ["None", "Auto"] + [tt for tt in TERRAIN_TYPES if tt.lower().startswith("grind")]],
        update=update_autorail_terrain_type)

    bpy.types.WindowManager.thug_face_terrain_type = EnumProperty(
        name="Terrain Type",
        items=[(t, t, t) for t in ["Auto"] + TERRAIN_TYPES],
        update=update_terrain_type_mesh)

    bpy.types.WindowManager.thug_show_face_collision_colors = BoolProperty(
        name="Colorize faces and edges",
        description="Colorize faces and edges in the 3D view according to their collision flags and autorail settings.",
        default=True)
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
        default=800, min=50, max=6000)
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
    bpy.types.Object.thug_rail_connects_to = StringProperty(name="Linked To", description="Path this object links to (must be a rail/ladder/waypoint).")


    bpy.types.Object.thug_lightgroup = EnumProperty(
        name="Light Group",
        items=[
            ("None", "None", ""),
            ("Outdoor", "Outdoor", ""),
            ("NoLevelLights", "NoLevelLights", ""),
            ("Indoor", "Indoor", "")],
        default="None")
        
    bpy.types.Object.thug_lightmap_resolution = EnumProperty(
        name="Lightmap Resolution",
        items=[
            ("16", "16", ""),
            ("32", "32", ""),
            ("64", "64", ""),
            ("128", "128", ""),
            ("256", "256", ""),
            ("512", "512", ""),
            ("1024", "1024", ""),
            ("2048", "2048", ""),
            ("4096", "4096", ""),
            ("8192", "8192", "")],
        default="128", 
        description="Controls the resolution (squared) of baked lightmaps.")
    bpy.types.Object.thug_lightmap_quality = EnumProperty(
        name="Lightmap Quality",
        items=[
            ("Draft", "Draft", ""),
            ("Preview", "Preview", ""),
            ("Good", "Good", ""),
            ("High", "High", ""),
            ("Ultra", "Ultra", ""),
            ("Custom", "Custom", "Uses existing Cycles render settings.")],
        default="Preview", 
        description="Preset controls for the bake quality.")
    bpy.types.Object.thug_lightmap_type = EnumProperty(
        name="UV Type",
        items=[
            ("Lightmap", "Lightmap", "Lightmap pack with preset margins."),
            ("Smart", "Smart", "Smart UV projection with default settings.")],
        default="Lightmap", 
        description="Determines the type of UV unwrapping done on the object for the bake.")
        
    bpy.types.Object.thug_levelobj_props = PointerProperty(type=THUGLevelObjectProps)
    bpy.types.Object.thug_triggerscript_props = PointerProperty(type=THUGObjectTriggerScriptProps)
    bpy.types.Object.thug_empty_props = PointerProperty(type=THUGEmptyProps)
    bpy.types.Object.thug_proxim_props = PointerProperty(type=THUGProximNodeProps)
    bpy.types.Object.thug_emitter_props = PointerProperty(type=THUGEmitterProps)
    bpy.types.Object.thug_generic_props = PointerProperty(type=THUGGenericNodeProps)
    bpy.types.Object.thug_restart_props = PointerProperty(type=THUGRestartProps)
    bpy.types.Object.thug_go_props = PointerProperty(type=THUGGameObjectProps)
    bpy.types.Object.thug_ped_props = PointerProperty(type=THUGPedestrianProps)
    bpy.types.Object.thug_veh_props = PointerProperty(type=THUGVehicleProps)
    bpy.types.Object.thug_particle_props = PointerProperty(type=THUGParticleProps)
    
    bpy.types.Lamp.thug_light_props = PointerProperty(type=THUGLightProps)
    
    bpy.types.Curve.thug_pathnode_triggers = CollectionProperty(type=THUGPathNodeProps)
    
    bpy.types.Image.thug_image_props = PointerProperty(type=THUGImageProps)

    bpy.types.Material.thug_material_props = PointerProperty(type=THUGMaterialProps)
    bpy.types.Texture.thug_material_pass_props = PointerProperty(type=THUGMaterialPassProps)

    bpy.types.WindowManager.thug_all_rails = CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.WindowManager.thug_all_restarts = CollectionProperty(type=bpy.types.PropertyGroup)

    bpy.types.Scene.thug_lightmap_scale = EnumProperty(
        name="Lightmap Scale",
        items=[
            ("0.25", "0.25", ""),
            ("0.5", "0.5", ""),
            ("1", "1", ""),
            ("2", "2", ""),
            ("4", "4", ""),
            ("8", "8", "")],
        default="1", 
        description="Scales the resolution of all lightmaps by the specified factor.")
    bpy.types.Scene.thug_lightmap_uglymode = BoolProperty(
        name="Performance Mode",
        default=False, 
        description="Disable all Cycles materials when baking. Bakes faster, but with much less accuracy.")
    bpy.types.Scene.thug_lightmap_clamp = FloatProperty(
        name="Shadow Intensity",
        description="Controls the maximum intensity of shadowed areas. Reduce in low-light scenes if you need to improve visibility.",
        min=0, max=1.0, default=1.0)
    bpy.types.Scene.thug_lightmap_color = FloatVectorProperty(name="Ambient Color",
                       subtype='COLOR',
                       default=(1.0, 1.0, 1.0, 1.0),
                       size=4,
                       min=0.0, max=1.0,
                       description="Lightmaps are baked onto a surface of this color.")
    bpy.types.Scene.thug_bake_type = EnumProperty(
        name="Bake Type",
        items=[
            ("LIGHT", "Lighting Only", "Bake lighting and mix with original textures. Preserves texture resolution, but less accurate lighting."),
            ("FULL", "Full Diffuse", "Bake lighting onto textures. Accurate lighting, but lowers base texture resolution.")],
        default="LIGHT", 
        description="Type of bakes to use for this scene.")
                           
    # bpy.utils.unregister_class(ExtractRail)
    # bpy.utils.register_class(ExtractRail)
    # bpy.utils.unregister_class(THUGImportNodeArray)
    # bpy.utils.register_class(THUGImportNodeArray)
    
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
    # bpy.utils.unregister_class(THUGImportNodeArray)

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
