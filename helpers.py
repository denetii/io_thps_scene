import bpy
import struct
import mathutils
import math
import logging
from . constants import *

__reload_order_index__ = -42

# PROPERTIES
#############################################
global_export_scale = 1
LOG = logging.getLogger(ADDON_NAME)


# METHODS
#############################################
def get_index(seq, value, key=lambda x: x, default=-1):
    i = 0
    for item in seq:
        if key(item) == value:
            return i
        i += 1
    return default

def swizzle_axis(val, mask):
    bit = 1
    result = 0
    while bit <= mask:
        test = mask & bit
        if test != 0: result |= val & bit
        else: val <<= 1
        bit <<= 1
    return result
#----------------------------------------------------------------------------------
def swizzle(data, width, height, bitCount, depth, unswizzle):
    def aux(x, y, z, masks):
        return (swizzle_axis(x, masks.x) |
                swizzle_axis(y, masks.y) |
                (0 if z == -1 else swizzle_axis(z, masks.z)))

    bitCount //= 8
    a = 0
    b = 0
    outdata = [0] * len(data)
    offset = 0
    masks = MaskSet(width, height, depth)
    for y in range(height):
        for x in range(width):
            a = (y * width + x) * bitCount
            b = aux(x, y, -1, masks) * bitCount
            if not unswizzle:
                a, b = b, a
            for i in range(offset, bitCount + offset):
                outdata[a + i] = data[b + i]
    return outdata


def _need_to_flip_normals(ob):
    negatives = 0
    while ob:
        for val in ob.scale:
            if val < 0:
                negatives += 1
        ob = ob.parent
    return negatives % 2 == 1

def _flip_normals(ob):
    bpy.context.scene.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")

def _make_temp_obj(data):
    return bpy.data.objects.new("~THUG TEMPORARY OBJECT~", data)

#----------------------------------------------------------------------------------
def get_sphere_from_bbox(bbox):
    bbox_min, bbox_max = bbox

    sphere_x = (bbox_min[0] + bbox_max[0]) / 2.0
    sphere_y = (bbox_min[1] + bbox_max[1]) / 2.0
    sphere_z = (bbox_min[2] + bbox_max[2]) / 2.0
    sphere_radius = (
        (sphere_x - bbox_min[0]) ** 2 +
        (sphere_y - bbox_min[1]) ** 2 +
        (sphere_z - bbox_min[2]) ** 2) ** 0.5

    return (sphere_x, sphere_y, sphere_z, sphere_radius)


#----------------------------------------------------------------------------------
def get_bbox2(vertices, matrix=mathutils.Matrix.Identity(4), is_park_editor=False):
    min_x = float("inf")
    min_y = float("inf")
    min_z = float("inf")
    max_x = -float("inf")
    max_y = -float("inf")
    max_z = -float("inf")
    for v in vertices:
        v = to_thug_coords(matrix * v.co)
        # v = v.co
        min_x = min(v[0], min_x)
        min_y = min(v[1], min_y)
        min_z = min(v[2], min_z)
        max_x = max(v[0], max_x)
        max_y = max(v[1], max_y)
        max_z = max(v[2], max_z)
        
    # bounding box is calculated differently for park dictionaries!
    if is_park_editor: 
        print("bounding box was: " + str(min_x) + "x" + str(min_z) + ", " + str(max_x) + "x" + str(max_z))
        new_min_x = (min_x / 60.0)
        new_min_z = (min_z / 60.0)
        new_max_x = (max_x / 60.0)
        new_max_z = (max_z / 60.0)
        
        if new_min_x < 0: min_x = float(round(new_min_x) * 60);
        else: min_x = float(round(new_min_x) * 60);
        if new_min_z < 0: min_z = float(round(new_min_z) * 60);
        else: min_z = float(round(new_min_z) * 60);
        
        if new_max_x < 0: max_x = float(round(new_max_x) * 60);
        else: max_x = float(round(new_max_x) * 60);
        if new_max_z < 0: max_z = float(round(new_max_z) * 60);
        else: max_z = float(round(new_max_z) * 60);
        
        # Fix bounding boxes that aren't aligned at center
        if (max_x + min_x) > 0: min_x = (max_x * -1.0)
        elif (max_x + min_x) < 0: max_x = (min_x * -1.0)
        if (max_z + min_z) > 0: min_z = (max_z * -1.0)
        elif (max_z + min_z) < 0: max_z = (min_z * -1.0)
        
        # This handles half-size dimensions
        #if (min_x + min_z) % 120 != 0:
        #    if(min_x != min_z and min_x > min_z): min_x -= 60
        #    else: min_z -= 60
        #if (max_x + max_z) % 120 != 0:
        #    if(max_x != max_z and max_x > max_z): max_z += 60
        #    else: max_x += 60
            
        min_y = 0.0
        print("NEW bounding box is: " + str(min_x) + "x" + str(min_z) + ", " + str(max_x) + "x" + str(max_z))
    return ((min_x, min_y, min_z, 1.0), (max_x, max_y, max_z, 1.0))

def to_thug_coords(v):
    return (v[0] * global_export_scale, v[2] * global_export_scale, -v[1] * global_export_scale)
#----------------------------------------------------------------------------------
def to_thug_coords_ns(v):
    return (v[0], v[2], -v[1])
#----------------------------------------------------------------------------------
def from_thug_coords(v):
    return (v[0], -v[2], v[1])
#----------------------------------------------------------------------------------
def to_thug_coords_rot(v):
    return (v[0], v[2] + math.radians(180), -v[1])
#----------------------------------------------------------------------------------
def crc_from_string(string):
    string = string.lower()
    string = string.replace(b"/", b"\\")
    rc = 0xffffffff

    for ch in string:
        rc = CRCTable[(rc ^ ch) & 0xff] ^ ((rc >> 8) & 0x00ffffff)

    return rc
#----------------------------------------------------------------------------------
def safe_mode_set(mode):
    if bpy.context.mode != mode:
        bpy.ops.object.mode_set(mode=mode)
#----------------------------------------------------------------------------------
def is_string_clean(string):
    import re
    return re.search(r"[^A-Za-z0-9_]", string) is None
#----------------------------------------------------------------------------------
def get_clean_string(string):
    import re
    return re.sub(r"[^A-Za-z0-9_]", "_", string)
#----------------------------------------------------------------------------------
def get_clean_name(ob):
    return get_clean_string(ob.name)
#----------------------------------------------------------------------------------
def get_scale_matrix(ob):
    matrix = mathutils.Matrix.Identity(4)
    matrix[0][0] = ob.scale[0]
    matrix[1][1] = ob.scale[1]
    matrix[2][2] = ob.scale[2]
    return matrix

# CLASSES
#############################################
class Reader(object):
    def __init__(self, buf):
        self.offset = 0
        self.buf = buf

    def read(self, fmt):
        result = struct.unpack_from(fmt, self.buf, self.offset)
        self.offset += struct.calcsize(fmt)
        return result

    def u8(self):
        return self.read("B")[0]

    def u16(self):
        return self.read("H")[0]

    def u32(self):
        return self.read("I")[0]

    def u64(self):
        return self.read("Q")[0]

    def i32(self):
        return self.read("i")[0]

    def i64(self):
        return self.read("q")[0]

    def f32(self):
        return self.read("f")[0]

    def bool(self):
        return self.read("?")[0]

    def vec3f(self):
        return self.read("3f")
#----------------------------------------------------------------------------------
class Printer(object):
    def __init__(self):
        self.on = True

    def __call__(self, message, *stuff):
        if self.on:
            # LOG.debug(message, stuff)
            print(message.format(*stuff))
        return stuff[0]
#----------------------------------------------------------------------------------
class MaskSet:
    def __init__(self, width, height, depth):
        self.x = 0
        self.y = 0
        self.z = 0
        bit = 1
        index = 1
        while bit < width or bit < height or bit < depth:
            if bit < width:
                self.x |= index
                index <<= 1
            if bit < height:
                self.y |= index
                index <<= 1
            if bit < depth:
                self.z |= index
                index <<= 1
            bit <<= 1