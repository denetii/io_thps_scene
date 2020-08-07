bl_info = {
    "name": "THPS Scene Export/Import",
    "description": "Enables the importing and exporting of scene files for the Tony Hawk game engines (THPS4, THUG1, THUG2, THAW)",
    "author": "denetii",
    "version": (2, 0, 0),
    "blender": (2, 83, 4),
    "location": "View3D",
    "wiki_url": "http://tharchive.net/misc/io_thps_scene.html",
    "category": "Import-Export" }


import bpy

# Load and reload submodules
##################################

from . import auto_load
auto_load.init()

from . ui_draw import *
from . scene_props import *

# Register
##################################

import traceback

def register():
    auto_load.register()
    register_menus()
    register_props()

def unregister():
    auto_load.unregister()
    unregister_menus()
    unregister_props()
    
