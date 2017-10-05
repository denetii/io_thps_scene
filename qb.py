import bpy
import os
import struct
from bpy.props import *
import bgl
from pprint import pprint
from . import autorail, helpers
from . constants import *
from . autorail import *
from . helpers import *

# PROPERTIES
#############################################


# METHODS
#############################################
def blub_int(integer):
    return "%i({},{:08})".format(integer, integer)
#----------------------------------------------------------------------------------
def blub_str(string):
    return "%s({},\"{}\")".format(len(string), string)
#----------------------------------------------------------------------------------

def obj_get_reserved_by(obj):
    return None

    rb = obj.thug_triggerscript_props.gap_props.reserved_by
    rbo = bpy.data.objects.get(rb)
    if rbo:
        if (rbo.thug_triggerscript_props.triggerscript_type != "Gap" or
            rbo.thug_triggerscript_props.gap_props.end_object != obj.name):
            obj.thug_triggerscript_props.gap_props.reserved_by = ""
            return None

    return rbo

def _generate_script(_ob):
    script_props = _ob.thug_triggerscript_props
    t = script_props.triggerscript_type
    if t in ("Killskater_Water", "Killskater", "Teleport"):
        target = script_props.target_node
        if not target:
            for ob in bpy.data.objects:
                if ob.type == "EMPTY" and \
                    ob.thug_empty_props.empty_type in ("SingleRestart", "MultiRestart", "TeamRestart"):
                    target = get_clean_name(ob)
        else:
            target = get_clean_string(target)

    reserved_by = None # obj_get_reserved_by(_ob)
    if reserved_by or t == "Gap":
        if reserved_by:
            gap_props = reserved_by.thug_triggerscript_props.gap_props
        else:
            gap_props = script_props.gap_props
        first_name, second_name = \
            ("GapStart", "GapEnd") if not reserved_by else ("GapEnd", "GapStart")
        script_name = "GENERATED_{}_{}".format(first_name, get_clean_name(_ob))
        flags = ' '.join("${}$".format(flag)
            for flag in THUGGapProps.flags
            if getattr(gap_props, flag, False))
        start_call = ""
        if not reserved_by or gap_props.two_way:
            start_call = ":i call $StartGap$ arguments $flags$ = :a{{ {flags} :a}} $gapid$ = ${name}$".format(flags=flags, name=script_name)
        end_call = ""
        if not gap_props.end_object and not reserved_by:
            end_call = ":i call $EndGap$ arguments $gapid$ = ${name}$ $score$ = {score} $text$ = {text}".format(
                name="GENERATED_{}_{}".format(first_name, get_clean_name(_ob)),
                score=blub_int(gap_props.score),
                text=blub_str(gap_props.name))
        elif gap_props.two_way or reserved_by:
            other_obj = bpy.data.objects.get(gap_props.end_object) or reserved_by
            end_call = ":i call $EndGap$ arguments $gapid$ = ${name}$ $score$ = {score} $text$ = {text}".format(
                name="GENERATED_{}_{}".format(second_name, get_clean_name(other_obj)),
                score=blub_int(gap_props.score),
                text=blub_str(gap_props.name))
        script_code = """
:i function ${name}$
    {start_call}
    {end_call}
:i endfunction
""".format(name=script_name, start_call=start_call, end_call=end_call)
    elif t == "Killskater_Water":
        script_name = "GENERATED_Killskater_Water_to_{}".format(target)
        script_code = """
:i function ${}$
    :i call $Sk3_Killskater_Water$ arguments
        $nodename$ = ${}$
:i endfunction
""".format(script_name, target)
    elif t == "Killskater":
        script_name = "GENERATED_Killskater_to_{}".format(target)
        script_code = """
:i function ${}$
    :i call $Sk3_Killskater$ arguments
        $nodename$ = ${}$
:i endfunction
""".format(script_name, target)
    elif t == "Teleport":
        script_name = "GENERATED_Teleport_to_{}".format(target)
        script_code = """
:i function ${}$
    :i call $TeleportSkaterToNode$ arguments
        $nodename$ = ${}$
    #/ :i call $create_panel_message$
    #/    $text$ = %s(11,"Teleported!")
:i endfunction
""".format(script_name, target)
    else:
        raise Exception("Unknown script type: {}".format(t))
    return script_name, script_code

#----------------------------------------------------------------------------------
def get_custom_node_props():
    node_props_text = bpy.data.texts.get("THUG_NODES", None)
    if not node_props_text: return {}
    node_props = {}

    current_node_name = None
    for line in node_props_text.as_string().split('\n'):
        if line.startswith("#="):
            current_node_name = line[2:]
        else:
            node_props[current_node_name] = node_props.get(current_node_name, "") + line + '\n'
    return node_props
#----------------------------------------------------------------------------------
def get_custom_func_code():
    funcs_text = bpy.data.texts.get("THUG_FUNCS", None)
    if not funcs_text: return {}
    funcs_code = {}

    current_node_name = None
    for line in funcs_text.as_string().split('\n'):
        if line.startswith("#="):
            current_node_name = line[2:].lower()
        else:
            funcs_code[current_node_name] = funcs_code.get(current_node_name, "") + line + '\n'
    return funcs_code

#----------------------------------------------------------------------------------
def export_qb(filename, directory, target_game, operator=None):
    checksums = {}

    def v3(v):
        return "%vec3({:6f},{:6f},{:6f})".format(*v)
    def c(s):
        if s not in checksums:
            checksums[s] = crc_from_string(bytes(s, 'ascii'))
        return "$" + s + "$"
    i = blub_int
    _string = blub_str

    generated_scripts = {}
    custom_triggerscript_names = []
    custom_node_props = get_custom_node_props()
    custom_func_code = get_custom_func_code()

    with open(os.path.join(directory, filename + ".txt"), "w") as outp:
        from io import StringIO
        string_output = StringIO()
        p = lambda *args, **kwargs: print(*args, **kwargs, file=string_output)
        p("%include \"qb_table.qbi\"")

        custom_script_text = bpy.data.texts.get("THUG_SCRIPTS", None)
        if custom_script_text:
            p(custom_script_text.as_string())
            p("")
            p("#/ custom script code end")
            p("")

        if target_game == "THUG2":
            p("$" + filename + "_NodeArray$ =")
        else:
            p("$NodeArray$ =")
        p(":i :a{")

        rail_custom_triggerscript_names, rail_generated_scripts = autorail._export_rails(p, c, operator)
        custom_triggerscript_names += rail_custom_triggerscript_names
        generated_scripts.update(rail_generated_scripts)

        # Used further down to determine if we need to auto-generate restarts of certain types
        has_restart_p1 = False
        has_restart_p2 = False
        has_restart_multi = False
        has_restart_gen = False
        has_restart_ctf = False
        has_restart_team = False
        has_restart_horse = False
        has_koth = False
        has_ctf_base_red = False
        has_ctf_base_yellow = False
        has_ctf_base_green = False
        has_ctf_base_blue = False
        has_ctf_red = False
        has_ctf_yellow = False
        has_ctf_green = False
        has_ctf_blue = False
        
        for ob in bpy.data.objects:
            # -----------------------------------------------------------------------------------------------------------
            # -----------------------------------------------------------------------------------------------------------
            # -----------------------------------------------------------------------------------------------------------
            if ob.type == "MESH" and not ob.get("thug_autosplit_object_no_export_hack"):
                is_levelobject = ob.thug_object_class == "LevelObject"
                clean_name = get_clean_name(ob)
                if not ob.thug_always_export_to_nodearray and \
                    not is_levelobject and \
                    ob.thug_created_at_start and \
                    not custom_node_props.get(clean_name) and \
                    not ob.name.lower().startswith("NightOn") and \
                    not ob.name.lower().startswith("NightOff") :
                    if (not getattr(ob, "thug_is_trickobject", False) and
                            ob.thug_triggerscript_props.triggerscript_type == "None") \
                        or not \
                        (getattr(ob, "thug_export_collision", True) or
                         getattr(ob, "thug_export_scene", True)):
                        continue
                    
                p("\t:i :s{")
                p("\t\t:i {} = {}".format(c("Pos"), v3(to_thug_coords(ob.location)))) # v3(get_sphere(ob))))
                if is_levelobject:
                    p("\t\t:i {} = {}".format(c("Angles"), v3(to_thug_coords_ns(ob.rotation_euler))))
                else:
                    p("\t\t:i {} = {}".format(c("Angles"), v3((0, 0, 0))))
                p("\t\t:i {} = {}".format(c("Name"), c(clean_name)))
                p("\t\t:i {} = {}".format(c("Class"), c("LevelGeometry") if not is_levelobject else c("LevelObject")))

                if ob.thug_occluder:
                    p("\t\t:i {}".format(c("Occluder")))
                elif ob.thug_created_at_start:
                    p("\t\t:i {}".format(c("CreatedAtStart")))

                if getattr(ob, "thug_is_trickobject", False):
                    p("\t\t:i call {} arguments".format(c("TrickObject")))
                    p("\t\t\t{} = {}".format(c("Cluster"),
                                             c(ob.thug_cluster_name if ob.thug_cluster_name else clean_name)))
                p("\t\t:i {} = {}".format(c("CollisionMode"), c("Geometry")))

                if ob.thug_triggerscript_props.triggerscript_type != "None" or obj_get_reserved_by(ob):
                    if (ob.thug_triggerscript_props.triggerscript_type == "Custom" and not obj_get_reserved_by(ob)):
                        script_name = ob.thug_triggerscript_props.custom_name
                        custom_triggerscript_names.append(script_name)
                    else:
                        script_name, script_code = _generate_script(ob)
                        generated_scripts.setdefault(script_name, script_code)
                    p("\t\t:i {} = {}".format(c("TriggerScript"), c(script_name)))

                if ob.thug_node_expansion:
                    p("\t\t:i {}".format(c(ob.thug_node_expansion)))

            # -----------------------------------------------------------------------------------------------------------
            # -----------------------------------------------------------------------------------------------------------
            # -----------------------------------------------------------------------------------------------------------
            elif ob.type == "EMPTY" and ob.thug_empty_props.empty_type != "" and ob.thug_empty_props.empty_type != "None":
                if ob.thug_empty_props.empty_type == "Pedestrian" or ob.thug_empty_props.empty_type == "Vehicle" or \
                    ob.thug_empty_props.empty_type == "BouncyObject" or ob.thug_empty_props.empty_type == "GenericNode" or \
                    ob.thug_empty_props.empty_type == "ProximNode":
                    continue
                    
                clean_name = get_clean_name(ob)
                
                p("\t:i :s{")
                p("\t\t:i {} = {}".format(c("Pos"), v3(to_thug_coords(ob.location))))
                p("\t\t:i {} = {}".format(c("Angles"), v3(to_thug_coords_ns(ob.rotation_euler))))
                p("\t\t:i {} = {}".format(c("Name"), c(clean_name)))
                if ob.thug_empty_props.empty_type == "Restart":
                    p("\t\t:i {} = {}".format(c("Class"), c("Restart")))
                    p("\t\t:i {} = {}".format(c("Type"), c(ob.thug_restart_props.restart_type)))
                    auto_restart_name = ""
                    str_all_types = ":a{"
                    if ob.thug_restart_props.restart_p1:
                        has_restart_p1 = True
                        str_all_types += c("Player1")
                        if auto_restart_name == "": auto_restart_name = "P1: Restart"
                    if ob.thug_restart_props.restart_p2:
                        has_restart_p2 = True
                        str_all_types += c("Player2")
                        if auto_restart_name == "": auto_restart_name = "P2: Restart"
                    if ob.thug_restart_props.restart_gen:
                        has_restart_gen = True
                        str_all_types += c("Generic")
                        if auto_restart_name == "": auto_restart_name = "Gen: Restart"
                    if ob.thug_restart_props.restart_multi:
                        has_restart_multi = True
                        str_all_types += c("Multiplayer")
                        if auto_restart_name == "": auto_restart_name = "Multi: Restart"
                    if ob.thug_restart_props.restart_team:
                        has_restart_team = True
                        str_all_types += c("Team")
                        if auto_restart_name == "": auto_restart_name = "Team: Restart"
                    if ob.thug_restart_props.restart_horse:
                        has_restart_horse = True
                        str_all_types += c("Horse")
                        if auto_restart_name == "": auto_restart_name = "Horse: Restart"
                    if ob.thug_restart_props.restart_ctf:
                        has_restart_ctf = True
                        str_all_types += c("CTF")
                        if auto_restart_name == "": auto_restart_name = "CTF: Restart"
                    
                    str_all_types += ":a}"
                    if auto_restart_name == "":
                        raise Exception("Restart node {} has no restart type(s).".format(ob.name))
                        
                    p("\t\t:i {} = {}".format(c("restart_types"), str_all_types))
                    actual_restart_name = ob.thug_restart_props.restart_name
                    if ob.thug_restart_props.restart_name == "":
                        actual_restart_name = auto_restart_name
                    p("\t\t:i {} = {}".format(c("RestartName"), blub_str(actual_restart_name)))
                    
                if ob.thug_empty_props.empty_type == "ProximNode":
                    p("\t\t:i {} = {}".format(c("Class"), c("ProximNode")))
                    p("\t\t:i {} = {}".format(c("Type"), c(ob.thug_proxim_props.proxim_type)))
                    #p("\t\t:i {}".format(c("ProximObject")))
                    p("\t\t:i {}".format(c("RenderToViewport")))
                    p("\t\t:i {}".format(c("SelectRenderOnly")))
                    p("\t\t:i {} = {}".format(c("Shape"), c("Sphere")))
                    p("\t\t:i {} = {}".format(c("Radius"), i(ob.thug_proxim_props.radius)))
                    
                elif ob.thug_empty_props.empty_type == "GameObject":
                    p("\t\t:i {} = {}".format(c("Class"), c("GameObject")))
                    p("\t\t:i {} = {}".format(c("Type"), c(ob.thug_go_props.go_type)))
                    
                    if ob.thug_go_props.go_type.startswith("Flag_"):
                        if ob.thug_triggerscript_props.triggerscript_type == "None" or ob.thug_triggerscript_props.custom_name == "":
                            ob.thug_triggerscript_props.triggerscript_type = "Custom"
                            ob.thug_triggerscript_props.custom_name = "TRG_CTF_" + ob.thug_go_props.go_type + "_Script"
                            
                    # Removing temporarily to make imported levels easier to work with!
                    #if ob.thug_go_props.go_model != "":
                    #    p("\t\t:i {} = {}".format(c("Model"), c(ob.thug_go_props.go_type)))
                    if ob.thug_go_props.go_type in THUG_DefaultGameObjects:
                        p("\t\t:i {} = {}".format(c("Model"), blub_str(THUG_DefaultGameObjects[ob.thug_go_props.go_type])))
                    elif ob.thug_go_props.go_type != "Ghost":
                        raise Exception("Game object " + clean_name + " has no model specified.")
                    p("\t\t:i {} = {}".format(c("SuspendDistance"), i(ob.thug_go_props.go_suspend)))
                    
                elif ob.thug_empty_props.empty_type == "GenericNode":
                    p("\t\t:i {} = {}".format(c("Class"), c("GenericNode")))
                    p("\t\t:i {} = {}".format(c("Type"), c(ob.thug_generic_props.generic_type)))
                    
                if ob.thug_created_at_start:
                    p("\t\t:i {}".format(c("CreatedAtStart")))
                if ob.thug_network_option != "Default":
                    p("\t\t:i {}".format(c(ob.thug_network_option)))
                    if ob.thug_network_option == "NetEnabled":
                        p("\t\t:i {}".format(c("Permanent")))
                        
                if ob.thug_triggerscript_props.triggerscript_type != "None" or obj_get_reserved_by(ob):
                    if (ob.thug_triggerscript_props.triggerscript_type == "Custom" and not obj_get_reserved_by(ob)):
                        script_name = ob.thug_triggerscript_props.custom_name
                        custom_triggerscript_names.append(script_name)
                    else:
                        script_name, script_code = _generate_script(ob)
                        generated_scripts.setdefault(script_name, script_code)
                    p("\t\t:i {} = {}".format(c("TriggerScript"), c(script_name)))

                if ob.thug_node_expansion:
                    p("\t\t:i {}".format(c(ob.thug_node_expansion)))

            else:
                continue

            if custom_node_props.get(clean_name):
                p("#/ custom props")
                p(custom_node_props.get(clean_name).strip('\n'))
                p("#/ end custom props")
            p("\t:i :s}")

        # -----------------------------------------------------------------------------------------------------------
        # -----------------------------------------------------------------------------------------------------------
        # -----------------------------------------------------------------------------------------------------------
        single_restarts = []
        multi_restarts = []
        team_restarts = []
        generic_restarts = []
        koth_nodes = []
        ctf_nodes = []
        team_nodes = []

        if not has_restart_p1:
            single_restarts = [("TRG_Playerone_0", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))]
        if not has_restart_multi:
            single_restarts = [("TRG_Multiplayer_0", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))]
        if not has_restart_team:
            single_restarts = [("TRG_Team_Restart", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))]
        if not has_koth:
            koth_nodes = [("TRG_KOTH", (0.0, 108.0, 0.0), (0.0, 0.0, 0.0))]
        if not has_ctf_blue:
            ctf_nodes.append(("Flag_Blue", (108.0, 108.0, 0.0), (0.0, 0.0, 0.0)))
            ctf_nodes.append(("Flag_Blue_Base", (108.0, 108.0, 0.0), (0.0, 0.0, 0.0)))
        if not has_ctf_red:
            ctf_nodes.append(("Flag_Red", (0.0, 108.0, 0.0), (0.0, 0.0, 0.0)))
            ctf_nodes.append(("Flag_Red_Base", (0.0, 108.0, 0.0), (0.0, 0.0, 0.0)))
        if not has_ctf_yellow:
            ctf_nodes.append(("Flag_Yellow", (-108.0, 108.0, 0.0), (0.0, 0.0, 0.0)))
            ctf_nodes.append(("Flag_Yellow_Base", (-108.0, 108.0, 0.0), (0.0, 0.0, 0.0)))
        if not has_ctf_green:
            ctf_nodes.append(("Flag_Green", (0.0, 108.0, 108.0), (0.0, 0.0, 0.0)))
            ctf_nodes.append(("Flag_Green_Base", (0.0, 108.0, 108.0), (0.0, 0.0, 0.0)))
            
        for (name, loc, rot) in single_restarts:
            p("""\t:i :s{{
\t\t:i $Pos$ = %vec3({:.6f},{:.6f},{:.6f})
\t\t:i $Angles$ = %vec3({:.6f},{:.6f},{:.6f})
\t\t:i $Name$ = {}
\t\t:i $Class$ = $Restart$
\t\t:i $Type$ = $Generic$
\t\t:i $RestartName$ = %s(11,"P1: Restart")
\t\t:i $CreatedAtStart$
\t\t:i $restart_types$ = :a{{$Player1$:a}}
\t:i :s}}""".format(loc[0], loc[1], loc[2], rot[0], rot[1], rot[2], c(name)))

        for (name, loc, rot) in multi_restarts:
            p("""\t:i :s{{
\t\t:i $Pos$ = %vec3({:.6f},{:.6f},{:.6f})
\t\t:i $Angles$ = %vec3({:.6f},{:.6f},{:.6f})
\t\t:i $Name$ = {}
\t\t:i $Class$ = $Restart$
\t\t:i $Type$ = $Multiplayer$
\t\t:i $CreatedAtStart$
\t\t:i $RestartName$ = %s(14,"Multi: Restart")
\t\t:i $restart_types$ = :a{{call $Multiplayer$ arguments
\t\t\t\t$Horse$:a}}
\t:i :s}}""".format(loc[0], loc[1], loc[2], rot[0], rot[1], rot[2], c(name)))

        for (name, loc, rot) in team_restarts:
            p("""\t:i :s{{
\t\t:i $Pos$ = %vec3({:.6f},{:.6f},{:.6f})
\t\t:i $Angles$ = %vec3({:.6f},{:.6f},{:.6f})
\t\t:i $Name$ = {}
\t\t:i $Class$ = $Restart$
\t\t:i $Type$ = $Team$
\t\t:i $CreatedAtStart$
\t\t:i $RestartName$ = %s(13,"Team: Restart")
\t\t:i $restart_types$ = :a{{$Team$:a}}
\t:i :s}}""".format(loc[0], loc[1], loc[2], rot[0], rot[1], rot[2], c(name)))

        for (name, loc, rot) in koth_nodes:
            p("""
\t:i :s{{
\t\t:i $Pos$ = %vec3{}
\t\t:i $Angles$ = %vec3{}
\t\t:i $Name$ = {}
\t\t:i $Class$ = $GenericNode$
\t\t:i $Type$ = $Crown$
\t:i :s}}
""".format(loc, rot, c(name)))

        for (name, loc, rot) in ctf_nodes:
            model_path = THUG_DefaultGameObjects[name]
            p("""\t:i :s{{
\t\t:i $Pos$ = %vec3({:.6f},{:.6f},{:.6f})
\t\t:i $Angles$ = %vec3({:.6f},{:.6f},{:.6f})
\t\t:i $Name$ = $TRG_CTF_{}$
\t\t:i $Class$ = $GameObject$
\t\t:i $Type$ = {}
\t\t:i $NeverSuspend$
\t\t:i $model$ = {}
\t\t:i $lod_dist1$ = %i(800,00000320)
\t\t:i $lod_dist2$ = %i(801,00000321)
\t\t:i $TriggerScript$ = $TRG_CTF_{}_Script$
\t:i :s}}""".format(loc[0], loc[1], loc[2], rot[0], rot[1], rot[2], name, c(name), blub_str(model_path), name))

        p(":i :a}") # end node array =======================

        if target_game == "THUG2":
            p("""
:i function ${}_Goals$
{}
    :i if $InMultiplayerGame$
        :i call $add_multiplayer_mode_goals$
    :i endif
:i endfunction
            """.format(filename, custom_func_code.get("goals", "").strip('\n')))
        else:
            p("""
:i function ${}_Goals$
{}
    :i doIf $InMultiplayerGame$
        :i call $add_multiplayer_mode_goals$
    :i doElse
    :i endif
:i endfunction
            """.format(filename, custom_func_code.get("goals", "").strip('\n')))

        p("""
:i function ${}_Startup$
{}
:i endfunction
        """.format(filename, custom_func_code.get("startup", "").strip('\n')))

        if target_game == "THUG1": # not sure if this is needed?
            p("""\n:i $TriggerScripts$ =
:i :a{
\t:i $LoadTerrain$
            """)

            p(":i $TRG_CTF_Flag_Blue_Script$")
            p(":i $TRG_CTF_Flag_Red_Script$")
            p(":i $TRG_CTF_Flag_Yellow_Script$")
            p(":i $TRG_CTF_Flag_Green_Script$")
            p(":i $TRG_CTF_Flag_Blue_Base_Script$")
            p(":i $TRG_CTF_Flag_Red_Base_Script$")
            p(":i $TRG_CTF_Flag_Yellow_Base_Script$")
            p(":i $TRG_CTF_Flag_Green_Base_Script$")

            for script_name, script_code in generated_scripts.items():
                p("\t:i {}".format(c(script_name)))
            p('\n'.join("\t:i ${}$".format(script_name) for script_name in custom_triggerscript_names))
            p("\n:i :a}\n")

        p("""
:i function $TRG_CTF_Flag_Blue_Script$
    :i call $Team_Flag$ arguments $blue$
:i endfunction
:i function $TRG_CTF_Flag_Red_Script$
    :i call $Team_Flag$ arguments $red$
:i endfunction
:i function $TRG_CTF_Flag_Yellow_Script$
    :i call $Team_Flag$ arguments $yellow$
:i endfunction
:i function $TRG_CTF_Flag_Green_Script$
    :i call $Team_Flag$ arguments $green$
:i endfunction
:i function $TRG_CTF_Flag_Blue_Base_Script$
    :i call $Team_Flag_Base$ arguments $blue$
:i endfunction
:i function $TRG_CTF_Flag_Green_Base_Script$
    :i call $Team_Flag_Base$ arguments $green$
:i endfunction
:i function $TRG_CTF_Flag_Red_Base_Script$
    :i call $Team_Flag_Base$ arguments $red$
:i endfunction
:i function $TRG_CTF_Flag_Yellow_Base_Script$
    :i call $Team_Flag_Base$ arguments $yellow$
:i endfunction
""")

        p(":i function $LoadAllParticleTextures$")
        p(":i endfunction")

        for script_name, script_code in generated_scripts.items():
            p("")
            p(script_code)


        p(":i function $LoadTerrain$\n")

        for terrain_type in TERRAIN_TYPES:
            if terrain_type != "WHEELS":
                if target_game == "THUG2":
                    p("\t:i $LoadTerrainSounds$$terrain$ = $TERRAIN_{}$\n".format(terrain_type))
                else:
                    p("\t:i $SetTerrain{}$\n".format(terrain_type))

        if target_game == "THUG1":
            p(""":i call $LoadSound$ arguments %s(22,"Shared\Water\FallWater") $FLAG_PERM$\n""")


        p("""
#/    :i call $script_change_tod$ arguments $tod_action$ = $set_tod_night$
#/    :i call $start_dynamic_tod$

    :i endfunction""")

        p(""":i function $load_level_anims$
#/    :i $animload_THPS5_human$
:i endfunction""")

        p(""":i function $LoadCameras$
:i endfunction
:i function $LoadObjectAnims$
:i endfunction
""")

        ncomp_text = bpy.data.texts.get("NCOMP", None)
        if ncomp_text:
            p(ncomp_text.as_string())
            p("")
            p("#/ ncomp end")
            p("")

        p(":i :end")

        string_final = string_output.getvalue()
        import re
        for qb_identifier in re.findall(r"\$([A-Za-z_0-9]+)\$", string_final):
            c(qb_identifier)
        outp.write(string_final)

    with open(os.path.join(directory, "qb_table.qbi"), "w") as outp:
        for s, checksum in checksums.items():
            outp.write("#addx 0x{:08x} \"{}\"\n".format(checksum, s))

    if False: # and target_game == "THUG2":
        _scripts_path = os.path.join(directory, filename + "_scripts.txt")
        if not os.path.exists(_scripts_path):
            with open(_scripts_path, "w") as outp:
                outp.write(":end")
    else:
        _scripts_path = os.path.join(directory, filename + "_scripts.qb")
        if not os.path.exists(_scripts_path):
            with open(_scripts_path, "wb") as outp:
                outp.write(b'\x00')

    if target_game == "THUG2":
        with open(os.path.join(directory, filename + "_thugpro.qb"), "wb") as outp:
            outp.write(b'\x00')

#----------------------------------------------------------------------------------
#- Exports QB in the format used for models (or anything that isn't a level)
#----------------------------------------------------------------------------------
def export_model_qb(filename, directory, target_game, operator=None):
    checksums = {}

    def v3(v):
        return "%vec3({:6f},{:6f},{:6f})".format(*v)
    def c(s):
        if s not in checksums:
            checksums[s] = crc_from_string(bytes(s, 'ascii'))
        return "$" + s + "$"
    i = blub_int
    _string = blub_str

    generated_scripts = {}
    custom_triggerscript_names = []
    custom_node_props = get_custom_node_props()
    custom_func_code = get_custom_func_code()

    with open(os.path.join(directory, filename + ".txt"), "w") as outp:
        from io import StringIO
        string_output = StringIO()
        p = lambda *args, **kwargs: print(*args, **kwargs, file=string_output)
        p("%include \"qb_table.qbi\"")

        custom_script_text = bpy.data.texts.get("THUG_SCRIPTS", None)
        if custom_script_text:
            p(custom_script_text.as_string())
            p("")
            p("#/ custom script code end")
            p("")

        p("$" + filename + "_NodeArray$ =")
        p(":i :a{")

        rail_custom_triggerscript_names, rail_generated_scripts = _export_rails(p, c, operator)
        custom_triggerscript_names += rail_custom_triggerscript_names
        generated_scripts.update(rail_generated_scripts)

        for ob in bpy.data.objects:
            if ob.type == "MESH" and not ob.get("thug_autosplit_object_no_export_hack"):
                is_levelobject = ob.thug_object_class == "LevelObject"
                clean_name = get_clean_name(ob)
                if not ob.thug_always_export_to_nodearray and \
                    not is_levelobject and \
                    ob.thug_created_at_start and \
                    not custom_node_props.get(clean_name) and \
                    not ob.name.lower().startswith("NightOn") and \
                    not ob.name.lower().startswith("NightOff") :
                    if (not getattr(ob, "thug_is_trickobject", False) and
                            ob.thug_triggerscript_props.triggerscript_type == "None") \
                        or not \
                        (getattr(ob, "thug_export_collision", True) or
                         getattr(ob, "thug_export_scene", True)):
                        continue
                p("\t:i :s{")
                p("\t\t:i {} = {}".format(c("Pos"), v3(to_thug_coords(ob.location)))) # v3(get_sphere(ob))))
                if is_levelobject:
                    p("\t\t:i {} = {}".format(c("Angles"), v3(to_thug_coords_ns(ob.rotation_euler))))
                    # p("\t\t:i {} = {}".format(c("Scale"), v3(to_thug_coords(ob.scale))))
                else:
                    p("\t\t:i {} = {}".format(c("Angles"), v3((0, 0, 0))))
                    # p("\t\t:i {} = {}".format(c("Scale"), v3((2, 0.5, 1))))
                p("\t\t:i {} = {}".format(c("Name"), c(clean_name)))
                p("\t\t:i {} = {}".format(c("Class"), c("LevelGeometry") if not is_levelobject else c("LevelObject")))

                if ob.thug_created_at_start:
                    p("\t\t:i {}".format(c("CreatedAtStart")))

                if getattr(ob, "thug_is_trickobject", False):
                    p("\t\t:i call {} arguments".format(c("TrickObject")))
                    p("\t\t\t{} = {}".format(c("Cluster"),
                                             c(ob.thug_cluster_name if ob.thug_cluster_name else clean_name)))
                p("\t\t:i {} = {}".format(c("CollisionMode"), c("Geometry")))

                if ob.thug_triggerscript_props.triggerscript_type != "None" or obj_get_reserved_by(ob):
                    if (ob.thug_triggerscript_props.triggerscript_type == "Custom" and not obj_get_reserved_by(ob)):
                        script_name = ob.thug_triggerscript_props.custom_name
                        custom_triggerscript_names.append(script_name)
                    else:
                        script_name, script_code = _generate_script(ob)
                        generated_scripts.setdefault(script_name, script_code)
                    p("\t\t:i {} = {}".format(c("TriggerScript"), c(script_name)))

                if ob.thug_node_expansion:
                    p("\t\t:i {}".format(c(ob.thug_node_expansion)))

            elif ob.type == "EMPTY" and ob.thug_empty_props.empty_type == "Custom":
                clean_name = get_clean_name(ob)

                p("\t:i :s{")
                p("\t\t:i {} = {}".format(c("Pos"), v3(to_thug_coords(ob.location))))
                p("\t\t:i {} = {}".format(c("Angles"), v3(to_thug_coords_ns(ob.rotation_euler))))
                # p("\t\t:i {} = {}".format(c("Scale"), v3(to_thug_coords_ns(ob.scale))))
                p("\t\t:i {} = {}".format(c("Name"), c(clean_name)))

                if ob.thug_node_expansion:
                    p("\t\t:i {}".format(c(ob.thug_node_expansion)))

            else:
                continue

            if custom_node_props.get(clean_name):
                p("#/ custom props")
                p(custom_node_props.get(clean_name).strip('\n'))
                p("#/ end custom props")
            p("\t:i :s}")

            
        p(":i :a}") # end node array =======================

        if target_game == "THUG1": # not sure if this is needed?
            p("""\n:i $""" + filename + """TriggerScripts$ = 
:i :a{ """)
        elif target_game == "THUG2":
            p("""\n:i $""" + filename + """TriggerScripts$ = 
:i :a{ """)

        for script_name, script_code in generated_scripts.items():
            p("\t:i {}".format(c(script_name)))
        p('\n'.join("\t:i ${}$".format(script_name) for script_name in custom_triggerscript_names))
        p("\n:i :a}\n")

        
        for script_name, script_code in generated_scripts.items():
            p("")
            p(script_code)

        p(":i :end")

        string_final = string_output.getvalue()
        import re
        for qb_identifier in re.findall(r"\$([A-Za-z_0-9]+)\$", string_final):
            c(qb_identifier)
        outp.write(string_final)

    with open(os.path.join(directory, "qb_table.qbi"), "w") as outp:
        for s, checksum in checksums.items():
            outp.write("#addx 0x{:08x} \"{}\"\n".format(checksum, s))

    if False: # and target_game == "THUG2":
        _scripts_path = os.path.join(directory, filename + "_scripts.txt")
        if not os.path.exists(_scripts_path):
            with open(_scripts_path, "w") as outp:
                outp.write(":end")
    else:
        _scripts_path = os.path.join(directory, filename + "_scripts.qb")
        if not os.path.exists(_scripts_path):
            with open(_scripts_path, "wb") as outp:
                outp.write(b'\x00')

    if target_game == "THUG2":
        with open(os.path.join(directory, filename + "_thugpro.qb"), "wb") as outp:
            outp.write(b'\x00')



def maybe_create_triggerscript(self, context):
    if context.object.thug_triggerscript_props.custom_name != '':
        script_name = context.object.thug_triggerscript_props.custom_name
    else:
        script_name = "script_" + context.object.name
        
    if not script_name in bpy.data.texts:
        bpy.data.texts.new(script_name)
    
    if context.object.thug_triggerscript_props.custom_name == '':
        context.object.thug_triggerscript_props.custom_name = script_name
    
    editor_found = False
    for area in context.screen.areas:
        if area.type == "TEXT_EDITOR":
            editor_found = True
            break

    if editor_found:
        area.spaces[0].text = bpy.data.texts[script_name]
        


# OPERATORS
#############################################
class THUGCreateTriggerScript(bpy.types.Operator):
    bl_idname = "io.thug_create_triggerscript"
    bl_label = "Create/View TriggerScript"
    # bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        maybe_create_triggerscript(self, context)
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
