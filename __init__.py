bl_info = {
    "name": "THPS Scene Export/Import",
    "description": "Enables the importing and exporting of scene files for the Tony Hawk Xbox engine (THPS4, THUG1, THUG2, THAW)",
    "author": "denetii",
    "version": (0, 2, 3),
    "blender": (2, 79, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Object" }


import bpy


# Load and reload submodules
##################################

import importlib
from . import developer_utils
importlib.reload(developer_utils)
modules = developer_utils.setup_addon_modules(__path__, __name__, "bpy" in locals())

from . ui_draw import register_menus, unregister_menus

# Register
##################################

import traceback

def register():
    try: bpy.utils.register_module(__name__)
    except: traceback.print_exc()
    register_menus()
    print("Registered {} with {} modules".format(bl_info["name"], len(modules)))

def unregister():
    try: bpy.utils.unregister_module(__name__)
    except: traceback.print_exc()
    unregister_menus()
    print("Unregistered {}".format(bl_info["name"]))
