#############################################
# AUTO SCENE BAKING TOOLS
#############################################
import bpy
import bmesh
import struct
import mathutils
import math
from bpy.props import *
from . helpers import *
from . material import *


# METHODS
#############################################

def format_image(img):
    pixels = list(img.pixels) # create an editable copy (list)
    for i in range(0, len(pixels), 4):
        pixels[i] = pixels[i] * 0.5
    for i in range(1, len(pixels), 4):
        pixels[i] = pixels[i] * 0.5
    for i in range(2, len(pixels), 4):
        pixels[i] = pixels[i] * 0.5
    # Write back to image.
    img.pixels[:] = pixels
    # Should probably update image
    img.update()

def invert_image(img):
    pixels = list(img.pixels) # create an editable copy (list)
    # Use the tuple object, which is way faster than direct access to Image.pixels
    for i in range(0, len(pixels), 4):
        pixels[i] = (1.0 - pixels[i]) * 0.5
    for i in range(1, len(pixels), 4):
        pixels[i] = (1.0 - pixels[i]) * 0.5
    for i in range(2, len(pixels), 4):
        pixels[i] = (1.0 - pixels[i]) * 0.5

    # Write back to image.
    # Slice notation here means to replace in-place, not sure if it's faster...
    img.pixels[:] = pixels

    # Should probably update image
    img.update()
    #return img

def get_material(name):
    if not bpy.data.materials.get(str(name)):
        blender_mat = bpy.data.materials.new(str(name)) 
        blender_mat.use_transparency = True
        blender_mat.diffuse_color = (1, 1, 1)
        blender_mat.diffuse_intensity = 1
        blender_mat.specular_intensity = 0.25
        blender_mat.alpha = 1
    else:
        blender_mat = bpy.data.materials.get(str(name)) 
    return blender_mat
    
def get_filler_mat():
    if bpy.data.materials.get("_tmp_bakemat"):
        return bpy.data.materials.get("_tmp_bakemat")
        
def get_filler_image():
    if bpy.data.images.get("_tmp_flat"):
        return bpy.data.images.get("_tmp_flat")
        
    size = 512, 512
    img = bpy.data.images.new(name="_tmp_flat", width=size[0], height=size[1])
    ## For white image
    # pixels = [1.0] * (4 * size[0] * size[1])

    pixels = [None] * size[0] * size[1]
    for x in range(size[0]):
        for y in range(size[1]):
            # assign RGBA to something useful
            r = 1.0
            g = 1.0
            b = 1.0
            a = 1.0
            pixels[(y * size[0]) + x] = [r, g, b, a]

    # flatten list
    pixels = [chan for px in pixels for chan in px]

    # assign pixels
    img.pixels = pixels
    return img
    
def store_materials(obj):
    stored_mats = []
    
    for mat_slot in obj.material_slots:
        if not mat_slot.material.name.startswith('Lightmap_'):
            stored_mats.append(mat_slot.material)
        
    for i in range(len(obj.material_slots)):
        obj.active_material_index = i
        bpy.ops.object.material_slot_remove({'object': obj})
    return stored_mats
    
def restore_mats(obj, stored_mats):
    new_mats = []
    for mat_slot in obj.material_slots:
        new_mats.append(mat_slot.material)

    for i in range(len(obj.material_slots)):
        obj.active_material_index = i
        bpy.ops.object.material_slot_remove({'object': obj})
        
    for mat in stored_mats:
        obj.data.materials.append(mat.copy())
    #for mat in new_mats:
    #    obj.data.materials.append(mat)
        


# OPERATORS
#############################################
class BakeLightmaps(bpy.types.Operator):
    bl_idname = "object.thug_bake_scene"
    bl_label = "Bake Lighting"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        return len(meshes) > 0

    def execute(self, context):
        scene = context.scene
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        for ob in context.selected_objects:
            ob.select = False
            
        # We need to be in Cycles to run the lightmap bake
        previous_engine = 'CYCLES'
        if scene.render.engine != 'CYCLES':
            previous_engine = scene.render.engine
            scene.render.engine = 'CYCLES'
            
        # If the user saved but didn't pack images, the filler image will be black
        # so we should get rid of it to ensure the bake result is always correct
        if bpy.data.images.get("_tmp_flat"):
            bpy.data.images["_tmp_flat"].user_clear()
            bpy.data.images.remove(bpy.data.images.get("_tmp_flat"))
            
        total_meshes = len(meshes)
        mesh_num = 0
        for ob in meshes:
            mesh_num += 1
            print("****************************************")
            print("****************************************")
            print("****************************************")
            print("BAKING LIGHTING FOR OBJECT #" + str(mesh_num) + " OF " + str(total_meshes) + ": " + ob.name)
            print("****************************************")
            print("****************************************")
            print("****************************************")
            
            # Set it to active and go into edit mode
            scene.objects.active = ob
            ob.select = True
            
            bpy.ops.object.mode_set(mode='OBJECT')
            if not ob.data.uv_layers.get('Lightmap'):
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                # Create a second UV layer for the ambient occlusion map
                bpy.ops.mesh.uv_texture_add({"object": ob})
                ob.data.uv_layers[1].name = 'Lightmap'
                bpy.context.object.data.uv_textures['Lightmap'].active = True
                bpy.context.object.data.uv_textures['Lightmap'].active_render = True
                
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.lightmap_pack(
                    PREF_CONTEXT='ALL_FACES', PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False,
                    PREF_APPLY_IMAGE=False, PREF_IMG_PX_SIZE=512, PREF_BOX_DIV=48, PREF_MARGIN_DIV=0.1)
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            else:
                bpy.context.object.data.uv_textures['Lightmap'].active = True
                bpy.context.object.data.uv_textures['Lightmap'].active_render = True
            
            
            # First, we need to store the materials assigned to the object
            # As baking will fail if there are any materials without textures
            orig_mats = store_materials(ob)
            orig_index = ob.active_material_index
            
            img_res = 512
            if ob.thug_lightmap_resolution:
                img_res = int(ob.thug_lightmap_resolution)
            
            # Create a new image to bake the lighting in to, if it doesn't exist
            if not bpy.data.images.get('LM_' + ob.name):
                bpy.ops.image.new(name="LM_" + ob.name, width=img_res, height=img_res)
                image = bpy.data.images['LM_' + ob.name]
            else:
                image = bpy.data.images.get('LM_' + ob.name)
            
            # Create or retrieve the lightmap material
            if not bpy.data.textures.get("Baked_{}".format(ob.name)):
                blender_tex = bpy.data.textures.new("Baked_{}".format(ob.name), "IMAGE")
            else:
                blender_tex = bpy.data.textures.get("Baked_{}".format(ob.name))
            blender_tex.image = image
            blender_tex.thug_material_pass_props.blend_mode = 'vBLEND_MODE_SUBTRACT'
            blender_mat = get_material("Lightmap_" + ob.name)
            if not blender_mat.texture_slots.get(blender_tex.name):
                tex_slot = blender_mat.texture_slots.add()
            else:
                tex_slot = blender_mat.texture_slots.get(blender_tex.name)
            tex_slot.texture = blender_tex
            tex_slot.uv_layer = str('Lightmap')
            tex_slot.blend_type = 'SUBTRACT'
            blender_mat.use_textures[0] = True
            if not ob.data.materials.get(blender_mat.name):
                ob.data.materials.append(blender_mat)
            
            # Create a material tree node in Cycles
            blender_mat.use_nodes = True
            nodes = blender_mat.node_tree.nodes
            
            # Add a dummy image texture so Cycles will actually bake without yelling 
            if nodes.get('Filler Tex'):
                node0 = nodes.get('Filler Tex')
            else:
                node0 = nodes.new('ShaderNodeTexImage')
                node0.name = "Filler Tex"
            node0.image = get_filler_image()
            node0.location = (-20,0)
            material_output = nodes.get('Diffuse BSDF')
            blender_mat.node_tree.links.new(material_output.inputs[0], node0.outputs[0])
            
            # Now add the result texture, this is what will store the bake
            if nodes.get('Bake Result'):
                node = nodes.get('Bake Result')
            else:
                node = nodes.new('ShaderNodeTexImage')
                node.name = "Bake Result"
            node.image = blender_tex.image
            node.location = (0,-40)
            node.select = True
            nodes.active = node
            # Bake the lightmap
            scene.cycles.bake_type = 'DIFFUSE'
            bpy.context.scene.render.bake.use_pass_color = False
            scene.render.bake_margin = 2
            scene.cycles.samples = 32
            scene.cycles.max_bounces = 4
            bpy.ops.object.bake(type='DIFFUSE')
            
            print("Object " + ob.name + " baked to texture " + blender_tex.name)

            bpy.ops.object.mode_set(mode='OBJECT')
            # Now, for the cleanup! Let's get everything back to BI and restore the missing mats
            blender_mat.use_nodes = False
            restore_mats(ob, orig_mats)
            # Assign the texture pass from the bake material to the base material(s)
            ob.active_material_index = orig_index
            for mat in ob.data.materials:
                invert_image(blender_tex.image)
                #format_image(blender_tex.image)
                if not mat.texture_slots.get(blender_tex.name):
                    slot = mat.texture_slots.add()
                else:
                    slot = mat.texture_slots.get(blender_tex.name)
                slot.texture = blender_tex
                slot.uv_layer = str('Lightmap')
                slot.blend_type = 'SUBTRACT'
                
            orig_uv = ob.data.uv_layers[0].name
            bpy.context.object.data.uv_textures[orig_uv].active = True
            bpy.context.object.data.uv_textures[orig_uv].active_render = True
            ob.select = False
            # Done!!
        
        # Switch back to the original engine, if it wasn't Cycles
        if previous_engine != 'CYCLES':
            scene.render.engine = previous_engine
        return {"FINISHED"}

# PANELS
#############################################
#----------------------------------------------------------------------------------
class THUGLightingTools(bpy.types.Panel):
    bl_label = "TH Lighting Tools"
    bl_region_type = "TOOLS"
    bl_space_type = "VIEW_3D"
    bl_category = "THUG Tools"

    @classmethod
    def poll(cls, context):
        return context.user_preferences.addons[ADDON_NAME].preferences.object_settings_tools

    def draw(self, context):
        if not context.object: return
        ob = context.object
        if ob.type == "MESH" and ob.thug_export_scene:
            self.layout.row().prop(ob, "thug_lightmap_resolution")
            self.layout.row().operator(BakeLightmaps.bl_idname, text=BakeLightmaps.bl_label, icon='PLUGIN')

