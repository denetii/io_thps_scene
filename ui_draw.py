import bpy
from . import_thps4 import THPS4ScnToScene
from . import_thug1 import THUG1ScnToScene

def import_menu_func(self, context):
    #self.layout.operator(THUGColToScene.bl_idname, text=THUGColToScene.bl_label, icon='PLUGIN')
    #self.layout.operator(THUG2ScnToScene.bl_idname, text=THUG2ScnToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THUG1ScnToScene.bl_idname, text=THUG1ScnToScene.bl_label, icon='PLUGIN')
    self.layout.operator(THPS4ScnToScene.bl_idname, text=THPS4ScnToScene.bl_label, icon='PLUGIN')
    #self.layout.operator(THUGImportSkeleton.bl_idname, text=THUGImportSkeleton.bl_label, icon='PLUGIN')
    
def register_menus():
    bpy.types.INFO_MT_file_import.append(import_menu_func)
    
def unregister_menus():
    bpy.types.INFO_MT_file_import.remove(import_menu_func)