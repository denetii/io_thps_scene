#############################################
# TEST MODULE
#############################################
import bpy
import struct
import mathutils
import math
from bpy.props import *
from . helpers import *
from . import prefs
import configparser
import glob

# PROPERTIES
#############################################
SCRIPT_TEMPLATES = []

# METHODS
#############################################
def init_templates():
    global SCRIPT_TEMPLATES
    
    addon_prefs = bpy.context.user_preferences.addons[ADDON_NAME].preferences
    base_files_dir_error = prefs._get_base_files_dir_error(addon_prefs)
    if base_files_dir_error:
        self.report({"ERROR"}, "Base files directory error: {} - Unable to read script templates.".format(base_files_dir_error))
        return
    base_files_dir = addon_prefs.base_files_dir
    
    template_files = glob.glob(base_files_dir + "scripts\*.ini")
    for temp_path in template_files:
        new_template = parse_template(temp_path)
        if not template_exists(new_template['Name'], SCRIPT_TEMPLATES):
            SCRIPT_TEMPLATES.append(parse_template(temp_path))
    
    return
    
def get_templates(self, context):
    if not context.object:
        return []
    ob = context.object
    global SCRIPT_TEMPLATES
    items = []
    items.append( ('None', 'None', '') )
    items.append( ('Custom', 'Custom', 'Write your own Trigger Script.') )
    for tmp in SCRIPT_TEMPLATES:
        # Based on the type of object selected, determine which script templates should be selectable
        should_append = True if ('All' in tmp['Types']) else False
        if ob.type == 'MESH' and ob.thug_object_class in tmp['Types'] or 'Mesh' in tmp['Types']:
                should_append = True
        elif ob.type == 'EMPTY' and (ob.thug_empty_props.empty_type in tmp['Types'] or 'Empty' in tmp['Types']):
                should_append = True
        elif ob.type == 'CURVE' and (ob.thug_path_type in tmp['Types'] or 'Path' in tmp['Types']):
                should_append = True
                
        if should_append:
            items.append((tmp['Name'], tmp['Name'], tmp['Description']))
    return items
    
def get_template(name):
    global SCRIPT_TEMPLATES
    for template in SCRIPT_TEMPLATES:
        if template['Name'] == name:
            return template
    return None
    
def template_exists(name, templates):
    for template in templates:
        if template['Name'] == name:
            return True
    return False

def get_param_values(param_num, context):
    if not context.object:
        return []
    ob = context.object
    if ob.thug_triggerscript_props.template_name in [ "None", "Custom", "" ]:
        return []
    tmpl = get_template(ob.thug_triggerscript_props.template_name)
    paramindex = 0
    for param in tmpl['Parameters']:
        paramindex += 1
        if paramindex == param_num:
            return param['Values']
    return []
def get_param1_values(self, context):
    return get_param_values(1, context)
def get_param2_values(self, context):
    return get_param_values(2, context)
def get_param3_values(self, context):
    return get_param_values(3, context)
def get_param4_values(self, context):
    return get_param_values(4, context)
    
def parse_template(config_path):
    print("Attempting to read script file: {}".format(config_path))
    scr_cfg = configparser.ConfigParser()
    scr_cfg.read(config_path)
    obj_template = {}
    if not 'Script' in scr_cfg:
        raise Exception("Unable to find required {} section in script template: {}".format('Script', config_path))
    if not 'Content' in scr_cfg:
        raise Exception("Unable to find required {} section in script template: {}".format('Content', config_path))
    if not 'Name' in scr_cfg['Script']:
        raise Exception("Unable to find required value {} in {} section in script template: {}".format('Name', 'Script', config_path))
    obj_template['Name'] = scr_cfg['Script']['Name']
    obj_template['Description'] = scr_cfg['Script'].get('Description', 'No description available.')
    obj_template['Parameters'] = []
    # Read compatible games/object types, if not specified then assume everything
    game_list = scr_cfg['Script'].get('Games', 'THUG1,THUG2,THUGPRO')
    obj_template['Games'] = game_list.split(',')
    type_list = scr_cfg['Script'].get('Types', 'LevelGeometry,LevelObject,Empty,Path')
    obj_template['Types'] = type_list.split(',')
    
    for i in range(1,5):
        if 'Parameter' + str(i) in scr_cfg:
            param = {}
            param['Name'] = scr_cfg['Parameter' + str(i)]['Name']
            param['Description'] = scr_cfg['Parameter' + str(i)].get('Description', 'No description available.')
            param['Type'] = scr_cfg['Parameter' + str(i)].get('Type', 'String')
            if 'Values' in scr_cfg['Parameter' + str(i)]:
                param['Values'] = []
                for val in str(scr_cfg['Parameter' + str(i)]['Values']).split('\n'):
                    val_clean = val.strip().split(';')
                    if len(val_clean) < 2:
                        val_clean.append('Parameter value.')
                    param['Values'].append( (val_clean[0], val_clean[0], val_clean[1]) )
                    
            obj_template['Parameters'].append(param)
    
    if not 'Blub' in scr_cfg['Content'] and not 'QConsole' in scr_cfg['Content']:
        raise Exception("Cannot find script content for template: {}".format(config_path))
    obj_template['Script_Blub'] = scr_cfg['Content'].get('Blub', '')
    obj_template['Script_QConsole'] = scr_cfg['Content'].get('QConsole', '')
    
    #print("Template: {}".format(obj_template))
    return obj_template
        
def generate_template_script(ob, template, compiler):
    script_text = template['Script_Blub']
    script_name = get_clean_name(ob) + "_Script"
    script_header = ":i function ${}$".format(script_name)
    script_footer = ":i endfunction"
    
    if compiler == 'QConsole':
        script_text = template['Script_QConsole']
        script_header = "script {}".format(script_name)
        script_footer = "endscript"
        
    base_replace = [
        [ '~this.object~', get_clean_name(ob) ]
        ,[ '~this.level~', "Test" ]
        ,[ '~this.scene~', "Test2" ]
    ]
    
    paramindex = 0
    for param in template['Parameters']:
        paramindex += 1
        if not param['Name'] or not param['Type']:
            continue
        paramname = "param" + str(paramindex) + "_"
        if param['Type'] in [ 'String', 'Restart', 'Rail', 'Path', 'Waypoint', 'Script', 'Mesh' ]:
            paramname += "string"
        elif param['Type'] == 'Float':
            paramname += "float"
        elif param['Type'] == 'Int':
            paramname += "int"
        elif param['Type'] == 'Enum':
            paramname += "enum"
        if getattr(ob.thug_triggerscript_props, paramname, ""):
            base_replace.append( [ '~' + param['Name'] + '~', getattr(ob.thug_triggerscript_props, paramname, "")] )
            
    print(base_replace)
    final_text = script_text
    for token in base_replace:
        final_text = final_text.replace(token[0], token[1])
        
    final_text = script_header + "\n" + final_text + "\n" + script_footer + "\n"
    print(final_text)
    return script_name, final_text
        