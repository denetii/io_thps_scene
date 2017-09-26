
import struct
import mathutils
import math
from . constants import CRCTable

# PROPERTIES
#############################################
global_export_scale = 1


# METHODS
#############################################
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