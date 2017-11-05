#############################################
# AUTO SCENE BAKING TOOLS
#############################################
import bpy
import bmesh
import struct
import mathutils
import math
import os
import numpy
from bpy.props import *
from . helpers import *
from . material import *


# METHODS
#############################################

#----------------------------------------------------------------------------------
#- Returns an inverted/clamped version of the given image - for lightmap bakes
#----------------------------------------------------------------------------------
def invert_image(img, clamp_factor):
    pixels = list(img.pixels) # create an editable copy (list)
    shadow_clamp = 0.48 * clamp_factor
    for i in range(0, len(pixels), 4):
        pixels[i] = numpy.clip((1.0 - pixels[i]), 0.0, shadow_clamp)
    for i in range(1, len(pixels), 4):
        pixels[i] = numpy.clip((1.0 - pixels[i]), 0.0, shadow_clamp)
    for i in range(2, len(pixels), 4):
        pixels[i] = numpy.clip((1.0 - pixels[i]), 0.0, shadow_clamp)
    img.pixels[:] = pixels
    img.update()
    #return img

#----------------------------------------------------------------------------------
#- Returns an existing material given a name, or creates one with that name
#----------------------------------------------------------------------------------
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
    
#----------------------------------------------------------------------------------
#- Checks for the temp baking material
#----------------------------------------------------------------------------------
def get_filler_mat():
    if bpy.data.materials.get("_tmp_bakemat"):
        return bpy.data.materials.get("_tmp_bakemat")
        
def get_empty_tex():
    if bpy.data.textures.get("_tmp_fillertex"):
        return bpy.data.textures.get("_tmp_fillertex")
    
    blender_tex = bpy.data.textures.new("_tmp_fillertex", "IMAGE")
    blender_tex.image = get_empty_image()
    blender_tex.thug_material_pass_props.blend_mode = 'vBLEND_MODE_BLEND'
    return blender_tex
    
#----------------------------------------------------------------------------------
#- Creates or returns the transparent texture used for 'filler' texture slots
#----------------------------------------------------------------------------------
def get_empty_image():
    if bpy.data.images.get("_tmp_empty"):
        return bpy.data.images.get("_tmp_empty")
    size = 32, 32
    img = bpy.data.images.new(name="_tmp_empty", width=size[0], height=size[1])
    pixels = [None] * size[0] * size[1]
    for x in range(size[0]):
        for y in range(size[1]):
            r = 1.0
            g = 1.0
            b = 1.0
            a = 0.0
            pixels[(y * size[0]) + x] = [r, g, b, a]
    pixels = [chan for px in pixels for chan in px]
    img.pixels = pixels
    return img
    
#----------------------------------------------------------------------------------
#- Checks for the temp off-white image used for baking onto a surface
#----------------------------------------------------------------------------------
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
    
#----------------------------------------------------------------------------------
#- Collects the materials assigned to an object and returns them
#----------------------------------------------------------------------------------
def store_materials(obj):
    stored_mats = []
    # We also want to store the names of the materials on the object itself
    # This way we can 'un-bake' and restore the original mats later on
    if not "is_baked" in obj or obj["is_baked"] == False:
        original_mats = []
    
    for mat_slot in obj.material_slots:
        if not mat_slot.material.name.startswith('Lightmap_'):
            stored_mats.append(mat_slot.material)
            if not "is_baked" in obj or obj["is_baked"] == False:
                # Make sure it won't be deleted upon close!
                mat_slot.material.use_fake_user = True 
                original_mats.append(mat_slot.material.name)
            
    for i in range(len(obj.material_slots)):
        obj.active_material_index = i
        bpy.ops.object.material_slot_remove({'object': obj})
        
    if not "is_baked" in obj or obj["is_baked"] == False:
        obj["original_mats"] = original_mats
    
    return stored_mats
    
#----------------------------------------------------------------------------------
#- Restores materials previously assigned to an object
#----------------------------------------------------------------------------------
def restore_mats(obj, stored_mats):
    new_mats = []
    for mat_slot in obj.material_slots:
        new_mats.append(mat_slot.material)

    for i in range(len(obj.material_slots)):
        obj.active_material_index = i
        bpy.ops.object.material_slot_remove({'object': obj})
        
    for mat in stored_mats:
        #mat.use_nodes = False
        obj.data.materials.append(mat.copy())
    #for mat in new_mats:
    #    obj.data.materials.append(mat)
        
#----------------------------------------------------------------------------------
#- Restores face material assignments
#----------------------------------------------------------------------------------
def restore_mat_assignments(obj, orig_polys):
    #polys = obj.data.polygons
    face_list = [face for face in obj.data.polygons]
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data) 
    
    for face in bm.faces: 
        face.select = False
    for face in bm.faces: 
        face.select = True
        face.material_index = orig_polys[face.index]
        #print("assigning mat {} to face {}".format(face.material_index, face.index))
        
    obj.data.update()
        
    # toggle to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
            
def mat_get_pass(blender_mat, type):
    for p in blender_mat.texture_slots:
        if p is None:
            continue
        if type == 'Diffuse' and p.use_map_color_diffuse:
            return p.texture.image
        elif type == 'Normal' and p.use_map_normal:
            return p.texture.image
            
    return None
    
def get_cycles_node(nodes, name, type):
    if nodes.get(name):
        return nodes.get(name)
    new_node = nodes.new(type)
    new_node.name = name
    return new_node
    
#----------------------------------------------------------------------------------
#- Ensures the Cycles scene is using Cycles materials before baking
#----------------------------------------------------------------------------------
def setup_cycles_scene(use_uglymode = False):
    if use_uglymode:
        print("USING UGLY MODE!")
        for mat in bpy.data.materials:
            mat.use_nodes = False
    else:
        print("TURNING ON CYCLES MAT NODES!")
        for mat in bpy.data.materials:
            mat.use_nodes = True
    

def setup_cycles_nodes(node_tree, diffuse_tex = None, normal_tex = None, uv_map = ""):
    nodes = node_tree.nodes
    # First, add textures...
    # Add dummy diffuse texture node (off white)
    node_d = get_cycles_node(nodes, 'Filler Tex', 'ShaderNodeTexImage')
    node_d.image = get_filler_image()
    node_d.location = (-680,40)
    
    node_t = get_cycles_node(nodes, 'Diffuse Texture', 'ShaderNodeTexImage')
    if diffuse_tex:
        node_t.image = diffuse_tex
    node_t.location = (-660,320)
        
    node_n = get_cycles_node(nodes, 'Normal Texture', 'ShaderNodeTexImage')
    if normal_tex:
        node_n.image = normal_tex
    node_n.color_space = 'NONE'
    node_n.location = (-680,-220)
        
    # Now, add shaders!
    # Add diffuse shader (if it doesn't exist, which it should!)
    node_sd = get_cycles_node(nodes, 'Diffuse BSDF', 'ShaderNodeBsdfDiffuse')
    node_sd.location = (-160,280)
    
    # Add the transparent BDSF
    node_st = get_cycles_node(nodes, 'Transparent BDSF', 'ShaderNodeBsdfTransparent')
    node_st.location = (-160,400)
    
    # Add a shader mix node (for transparent and diffuse shaders)
    node_sm = get_cycles_node(nodes, 'Mix Shader', 'ShaderNodeMixShader')
    node_sm.location = (80,340)
    
    # Add a normal map node 
    node_sn = get_cycles_node(nodes, 'Normal Map', 'ShaderNodeNormalMap')
    node_sn.location = (-420,0)
    node_sn.uv_map = uv_map
    
    # Add a UV map node 
    node_uv = get_cycles_node(nodes, 'UV Map', 'ShaderNodeUVMap')
    node_uv.location = (-1060,60)
    node_uv.uv_map = uv_map
    
    # Material output (if that somehow doesn't exist already)
    node_mo = get_cycles_node(nodes, 'Material Output', 'ShaderNodeOutputMaterial')
    node_mo.location = (300, 340)
    
    # Now, add links!
    node_tree.links.new(node_t.inputs[0], node_uv.outputs[0]) # Diffuse Texture UV
    node_tree.links.new(node_n.inputs[0], node_uv.outputs[0]) # Normal Texture UV
    
    if normal_tex:
        node_tree.links.new(node_sn.inputs[1], node_n.outputs[0]) # Normal Map color
    node_tree.links.new(node_sd.inputs[0], node_d.outputs[0]) # Diff Shader color
    node_tree.links.new(node_sd.inputs[2], node_sn.outputs[0]) # Diff Shader Normal
    node_tree.links.new(node_sm.inputs[0], node_t.outputs[1]) # Mix Shader fac
    node_tree.links.new(node_sm.inputs[1], node_st.outputs[0]) # Mix Shader Shader1
    node_tree.links.new(node_sm.inputs[2], node_sd.outputs[0]) # Mix Shader Shader2
    
    node_tree.links.new(node_mo.inputs[0], node_sm.outputs[0]) # Material Output Surface
    
    

#----------------------------------------------------------------------------------
#- 'Un-bakes' the object (restores the original materials)
#----------------------------------------------------------------------------------
def unbake(obj):
    if not "is_baked" in obj or obj["is_baked"] == False:
        # Don't try to unbake something that isn't baked to begin with!
        return
        
    if not "original_mats" in obj:
        raise Exception("Cannot unbake object - unable to find original materials.")
        
    # First, remove the existing mats on the object (these should be lightmapped)
    for i in range(len(obj.material_slots)):
        obj.active_material_index = i
        bpy.ops.object.material_slot_remove({'object': obj})
        
    for mat_name in obj["original_mats"]:
        if not bpy.data.materials.get(mat_name):
            raise Exception("Material {} no longer exists. Uh oh!".format(mat_name))
        _mat = bpy.data.materials.get(mat_name)
        obj.data.materials.append(_mat)
        
    obj["is_baked"] = False
    obj["thug_last_bake_res"] = 0

def save_baked_texture(img, folder):
    img.filepath_raw = "{}/{}.png".format(folder, img.name)
    img.file_format = "PNG"
    img.save()
    print("Saved texture {}.png to {}".format(img.name, folder))
    #bpy.path.abspath("//my/file.txt")
    
    
#----------------------------------------------------------------------------------
#- Bakes a set of objects
#----------------------------------------------------------------------------------
def bake_thug_lightmaps(meshes, context):
    scene = context.scene
    # De-select any objects currently selected
    if context.selected_objects:
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
        
    # Create destination folder for the baked textures
    _lightmap_folder = bpy.path.basename(bpy.context.blend_data.filepath)[:-6] # = Name of blend file
    _folder = bpy.path.abspath("//Tx_Lightmap/{}".format(_lightmap_folder))
    os.makedirs(_folder, 0o777, True)
    
    # Setup nodes for Cycles materials
    setup_cycles_scene(scene.thug_lightmap_uglymode)
    
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
        
        if "is_baked" in ob and ob["is_baked"] == True:
            print("Object has been previously baked, clearing the bake...")
            #unbake(ob)
            
        if ob.thug_export_scene == False:
            print("Object {} not marked for export to scene, skipping bake!".format(ob.name))
        
        if not ob.data.uv_layers:
            print("Object {} has no UV maps. Cannot bake lighting!".format(ob.name))
            continue
            
        # Set it to active and go into edit mode
        scene.objects.active = ob
        ob.select = True
        
        # Set the desired resolution, both for the UV map and the lightmap texture
        img_res = 128
        bake_margin = 1.0
        if ob.thug_lightmap_resolution:
            img_res = int(ob.thug_lightmap_resolution)
            print("Object lightmap resolution is: {}x{}".format(img_res, img_res))
        if scene.thug_lightmap_scale:
            img_res = int(img_res * float(scene.thug_lightmap_scale))
            print("Resolution after scene scale is: {}x{}".format(img_res, img_res))
            
        # Grab original UV map, so any diffuse/normal textures are mapped correctly
        orig_uv = ob.data.uv_layers[0].name
        
        # Also grab the original mesh data so we can remap the material assignments 
        orig_polys = [0] * len(ob.data.polygons)
        for f in ob.data.polygons:
            orig_polys[f.index] = f.material_index
        
        bpy.ops.object.mode_set(mode='OBJECT')
        # Recreate the UV map if it's a different resolution than we want now
        if ("thug_last_bake_res" in ob and ob["thug_last_bake_res"] != img_res) \
        or ("thug_last_bake_type" in ob and ob["thug_last_bake_type"] != ob.thug_lightmap_type) \
        or ("thug_last_bake_res" not in ob or "thug_last_bake_type" not in ob):
            print("Resolution and/or UV type has changed, removing existing images/UV maps.")
            if ob.data.uv_layers.get('Lightmap'):
                ob.data.uv_textures.remove(ob.data.uv_textures['Lightmap'])
            if bpy.data.images.get("LM_{}".format(ob.name)):
                _img = bpy.data.images.get("LM_{}".format(ob.name))
                _img.user_clear()
                bpy.data.images.remove(_img)
                
        if not ob.data.uv_layers.get('Lightmap'):
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            # Create a new UV layer for the ambient occlusion map
            bpy.ops.mesh.uv_texture_add({"object": ob})
            ob.data.uv_layers[len(ob.data.uv_layers)-1].name = 'Lightmap'
            ob.data.uv_textures['Lightmap'].active = True
            ob.data.uv_textures['Lightmap'].active_render = True
            
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            # Unwrap the mesh based on the type specified on the object properties!
            if ob.thug_lightmap_type == 'Lightmap':
                bpy.ops.uv.lightmap_pack(
                    PREF_CONTEXT='ALL_FACES', PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False,
                    PREF_APPLY_IMAGE=False, PREF_IMG_PX_SIZE=img_res, 
                    PREF_BOX_DIV=48, PREF_MARGIN_DIV=bake_margin)
            elif ob.thug_lightmap_type == 'Smart':
                bpy.ops.uv.smart_project()
            else:
                raise Exception("Unknown lightmap type specified on object {}".format(ob.name))
        else:
            ob.data.uv_textures['Lightmap'].active = True
            ob.data.uv_textures['Lightmap'].active_render = True
            
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        # First, we need to store the materials assigned to the object
        # As baking will fail if there are any materials without textures
        orig_mats = store_materials(ob)
        orig_index = ob.active_material_index
        if orig_index == None or orig_index < 0:
            orig_index = 0
            
        # Create a new image to bake the lighting in to, if it doesn't exist
        if not bpy.data.images.get('LM_' + ob.name):
            bpy.ops.image.new(name="LM_" + ob.name, width=img_res, height=img_res)
            image = bpy.data.images['LM_' + ob.name]
        else:
            image = bpy.data.images.get('LM_' + ob.name)
        # Always set width and height, in case the user changed the lightmap res
        image.generated_width = img_res
        image.generated_height = img_res
        
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
        # Look for diffuse and normal textures in the original active material
        test_mat = orig_mats[orig_index]
        tx_d = mat_get_pass(test_mat, 'Diffuse')
        tx_n = mat_get_pass(test_mat, 'Normal')
        setup_cycles_nodes(blender_mat.node_tree, tx_d, tx_n, orig_uv)
        
        # Finally, add the result texture, this is what will actually store the bake
        node_bake = get_cycles_node(blender_mat.node_tree.nodes, 'Bake Result', 'ShaderNodeTexImage')
        node_bake.image = blender_tex.image
        node_bake.location = (-160,100)
        node_bake.select = True
        blender_mat.node_tree.nodes.active = node_bake
        
        #return {"FINISHED"}
        
        # Bake the lightmap!
        scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_pass_color = False
        scene.render.bake_margin = bake_margin
        if ob.thug_lightmap_quality != 'Custom':
            if ob.thug_lightmap_quality == 'Draft':
                scene.cycles.samples = 16
                scene.cycles.max_bounces = 2
            if ob.thug_lightmap_quality == 'Preview':
                scene.cycles.samples = 32
                scene.cycles.max_bounces = 4
            if ob.thug_lightmap_quality == 'Good':
                scene.cycles.samples = 108
                scene.cycles.max_bounces = 5
            if ob.thug_lightmap_quality == 'High':
                scene.cycles.samples = 225
                scene.cycles.max_bounces = 6
            if ob.thug_lightmap_quality == 'Ultra':
                scene.cycles.samples = 450
                scene.cycles.max_bounces = 8
        print("Using {} bake quality. Samples: {}, bounces: {}".format(ob.thug_lightmap_quality, scene.cycles.samples, scene.cycles.max_bounces))
        #return { 'FINISHED' }
        bpy.ops.object.bake(type='DIFFUSE')
        print("Object " + ob.name + " baked to texture " + blender_tex.name)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        # Now, for the cleanup! Let's get everything back to BI and restore the missing mats
        blender_mat.use_nodes = False
        restore_mats(ob, orig_mats)
        # Assign the texture pass from the bake material to the base material(s)
        ob.active_material_index = orig_index
        invert_image(blender_tex.image, scene.thug_lightmap_clamp)
        save_baked_texture(blender_tex.image, _folder)
        for mat in ob.data.materials:
            mat.use_nodes = False
            if not mat.texture_slots.get(blender_tex.name):
                slot = mat.texture_slots.add()
            else:
                slot = mat.texture_slots.get(blender_tex.name)
            slot.texture = blender_tex
            slot.uv_layer = str('Lightmap')
            slot.blend_type = 'SUBTRACT'
            
        ob.data.uv_textures[orig_uv].active = True
        ob.data.uv_textures[orig_uv].active_render = True
        # If there is more than one material, restore the per-face material assignment
        if len(ob.data.materials) > 1:
            restore_mat_assignments(ob, orig_polys)
        ob.select = False
        ob["is_baked"] = True
        ob["thug_last_bake_res"] = img_res
        ob["thug_last_bake_type"] = ob.thug_lightmap_type
        # Done!!
    
    # Switch back to the original engine, if it wasn't Cycles
    if previous_engine != 'CYCLES':
        scene.render.engine = previous_engine
        
        
#----------------------------------------------------------------------------------
#- Fills baked materials with empty material passes to ensure that the 
#- UV indices line up with the material pass indices
#----------------------------------------------------------------------------------
def fill_bake_materials():
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and "is_baked" in o and o["is_baked"] == True]
    processed_mats = []
    for ob in meshes:
        for mat in ob.data.materials:
            #if mat.name in processed_mats: continue
            if not hasattr(mat, 'texture_slots'): continue
            passes = [tex_slot for tex_slot in mat.texture_slots if tex_slot and tex_slot.use and tex_slot.use_map_color_diffuse][:4]
            pass_number = -1
            passes_to_add = 0
            baked_slot = None
            for slot in passes:
                pass_number += 1
                if slot.name.startswith("Baked_"):
                    uv_pass = get_uv_index(ob, slot.uv_layer)
                    if uv_pass < 0:
                        raise Exception("Unable to find UV index for map {}".format(slot.uv_layer))
                    if pass_number != uv_pass:
                        print("Lightmap tex {} (pass #{}) doesn't match lightmap UV index {}!".format(slot.name, pass_number, uv_pass))
                        passes_to_add = uv_pass - pass_number
                        baked_slot = slot.texture
                        mat.texture_slots.clear(pass_number)
                        break
            if passes_to_add != 0:
                filler_slot = get_empty_tex()
                for i in range(0, passes_to_add):
                    _slot = mat.texture_slots.add()
                    _slot.texture = filler_slot
            if baked_slot:
                _slot = mat.texture_slots.add()
                _slot.texture = baked_slot
                _slot.uv_layer = "Lightmap"
                _slot.blend_type = "SUBTRACT"
            processed_mats.append(mat.name)
            
# OPERATORS
#############################################
class ToggleLightmapPreview(bpy.types.Operator):
    bl_idname = "object.thug_toggle_lightmap_preview"
    bl_label = "Toggle Lightmap Preview"
    bl_options = {'REGISTER', 'UNDO'}
    
    preview_on = bpy.props.BoolProperty()
    
    @classmethod
    def poll(cls, context):
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and "is_baked" in o and o["is_baked"] == True]
        return len(meshes) > 0

    def execute(self, context):
        if self.preview_on:
            for mat in bpy.data.materials:
                mat.use_nodes = True
            self.preview_on = False
        else:
            for mat in bpy.data.materials:
                mat.use_nodes = False
            self.preview_on = True
        
        return {"FINISHED"}
        
        
#----------------------------------------------------------------------------------
class UnBakeLightmaps(bpy.types.Operator):
    bl_idname = "object.thug_unbake_scene"
    bl_label = "Un-Bake Objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH' and "is_baked" in o and o["is_baked"] == True]
        return len(meshes) > 0

    def execute(self, context):
        scene = context.scene
        meshes = [o for o in context.selected_objects if o.type == 'MESH' and "is_baked" in o and o["is_baked"] == True]

        bpy.ops.object.select_all(action='DESELECT')
        for ob in meshes:
            #ob.select = False
            
            print("----------------------------------------")
            print("Attempting to un-bake object {}...".format(ob.name))
            print("----------------------------------------")
            
            # Grab the original mesh data so we can remap the material assignments 
            orig_polys = [0] * len(ob.data.polygons)
            for f in ob.data.polygons:
                orig_polys[f.index] = f.material_index
                
            unbake(ob)
            
            bpy.context.scene.objects.active = ob
            ob.select = True
            restore_mat_assignments(ob, orig_polys)
            ob.select = False
            print("... Un-bake successful!")
        
        print("Unbake completed on all objects!")
        return {"FINISHED"}
        
#----------------------------------------------------------------------------------
class BakeLightmaps(bpy.types.Operator):
    bl_idname = "object.thug_bake_scene"
    bl_label = "Bake Lighting"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        return len(meshes) > 0

    def execute(self, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        bake_thug_lightmaps(meshes, context)
        return {"FINISHED"}
        
#----------------------------------------------------------------------------------
class FixLightmapMaterials(bpy.types.Operator):
    bl_idname = "object.thug_bake_fix_mats"
    bl_label = "Fix Materials"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and "is_baked" in o and o["is_baked"] == True ]
        return len(meshes) > 0

    def execute(self, context):
        fill_bake_materials()
        return {"FINISHED"}
        
#----------------------------------------------------------------------------------
class ReBakeLightmaps(bpy.types.Operator):
    bl_idname = "object.thug_rebake_scene"
    bl_label = "Re-Bake All"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context):
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and "is_baked" in o and o["is_baked"] == True ]
        return len(meshes) > 0

    def execute(self, context):
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and "is_baked" in o and o["is_baked"] == True ]
        bake_thug_lightmaps(meshes, context)
        return {"FINISHED"}

#----------------------------------------------------------------------------------
class BakeNewLightmaps(bpy.types.Operator):
    bl_idname = "object.thug_bake_scene_new"
    bl_label = "Bake All New"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context):
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and ("is_baked" not in o or o["is_baked"] == False) ]
        return len(meshes) > 0

    def execute(self, context):
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and ("is_baked" not in o or o["is_baked"] == False) ]
        bake_thug_lightmaps(meshes, context)
        return {"FINISHED"}
        
#----------------------------------------------------------------------------------
class AutoLightmapResolution(bpy.types.Operator):
    bl_idname = "object.thug_auto_lightmap"
    bl_label = "Auto-set Resolution"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context):
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and ("is_baked" not in o or o["is_baked"] == False) ]
        return len(meshes) > 0

    def execute(self, context):
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and ("is_baked" not in o or o["is_baked"] == False) ]
        
        for ob in meshes:
            # We will use the object's area and density (number of faces) to determine
            # The approximate 'best' lightmap resolution, and then set that
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            ob_area = sum(f.calc_area() for f in bm.faces)
            ob_polys = len(ob.data.polygons)
            bm.free()
            print("Area of {}: {}".format(ob.name, ob_area))
            print("Density of {}: {} polys".format(ob.name, ob_polys))
            # Start with the poly count and use that to set a 'base' resolution
            base_res = 32
            res_multi = 1
            if ob_polys >= 256:
                base_res = 512
            elif ob_polys >= 96:
                base_res = 256
            elif ob_polys >= 48:
                base_res = 128
            elif ob_polys >= 16:
                base_res = 64
                
            if ob_area >= 500000000:
                res_multi = 8
            elif ob_area >= 50000000:
                res_multi = 4
            elif ob_area >= 100000:
                res_multi = 2
                
            actual_res = (base_res * res_multi)
            ob.thug_lightmap_resolution = str(actual_res)
            print("Calculated lightmap res: {}".format(actual_res))
            print("**************************************************")
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
            self.layout.row().prop(ob, "thug_lightmap_quality")
            self.layout.row().prop(ob, "thug_lightmap_type")
            self.layout.row().operator(BakeLightmaps.bl_idname, text=BakeLightmaps.bl_label, icon='LIGHTPAINT')
            self.layout.row().operator(UnBakeLightmaps.bl_idname, text=UnBakeLightmaps.bl_label, icon='SMOOTH')

class THUGSceneLightingTools(bpy.types.Panel):
    bl_label = "TH Lighting Settings"
    bl_region_type = "WINDOW"
    bl_space_type = "PROPERTIES"
    bl_context = "world"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        if not context.scene: return
        scene = context.scene
        self.layout.row().prop(scene, "thug_lightmap_scale")
        self.layout.row().prop(scene, "thug_lightmap_uglymode")
        self.layout.row().prop(scene, "thug_lightmap_clamp")
        self.layout.row().operator(ToggleLightmapPreview.bl_idname, text=ToggleLightmapPreview.bl_label, icon='SEQ_PREVIEW')
        
        tmp_row = self.layout.split()
        col = tmp_row.column()
        col.operator(ReBakeLightmaps.bl_idname, text=ReBakeLightmaps.bl_label, icon='LIGHTPAINT')
        col = tmp_row.column()
        col.operator(BakeNewLightmaps.bl_idname, text=BakeNewLightmaps.bl_label, icon='LIGHTPAINT')
        tmp_row = self.layout.split()
        col = tmp_row.column()
        col.operator(AutoLightmapResolution.bl_idname, text=AutoLightmapResolution.bl_label, icon='SCRIPT')
        col = tmp_row.column()
        col.operator(FixLightmapMaterials.bl_idname, text=FixLightmapMaterials.bl_label, icon='MATERIAL')