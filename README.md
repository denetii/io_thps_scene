# io_thps_scene
An extension of the last public release of the THPS/THUG scene import/export tools for Blender. 
This version fixes tons of bugs and adds a whole host of new features to make level creation easier for THUG1, THUG2 and THUG PRO.

## Working with previous scenes
Your .blend scenes that were built for the previous plugin, `io_thug_tools`, will need a little converting before they'll export correctly here. 
1. Player restarts, CTF Flags, and KOTH nodes need to be reconfigured, as the interface has been revamped a little bit and the options lists changed.
2. If you wrote any custom scripts in the `THUG_SCRIPTS` text block, you'll need to head to the Import Tools panel, press the 'Import TriggerScripts' 
button, and use the 'Scripts and objects' option. Custom scripts are now stored in individual text blocks per script, rather than one giant text file.
3. Restarts and other nodes may need to be rotated, as the exporter no longer auto-rotates these elements. This was changed so that THUG1/2/PRO 
scenes would export the same way, as well as imported levels.

## Change list
Here's the full list of changes and bug fixes since the previous public release of `io_thug_tools`:

 - Added support for the following object/node types:
    * Level light
    * Pedestrian
    * Vehicle
    * ProximNode
    * Waypoint
    * GameObject
 - Added Network Options to objects, which lets you control how they appear in online play.
 - Added LightGroup setting for scene meshes
 - Name, terrain type, trigger scripts and skater AI properties can now be configured on individual points along a path
 - Occluders can now be configured directly in the editor    
 - Added THUG1 and THPS4 scene/model importing!
 - Added 'auto-split everything' export option, applies the autosplit modifier to each object in the scene. Works great for preventing crashes in high-poly scenes 
 - Added support for using separate scene/collision mesh with the same object name
 - Added support for environment mapped texture passes
 - Added import support for node arrays from existing levels!
    * Rails, waypoints, object settings and more are parsed and placed into the scene
 - Trigger scripts from existing levels can now be imported!
 - Importing without a .tex file can now load TGAs/PNGs from a /tex folder relative to the blend file (same naming convention as files exported from TexTool)
 - Restarts have been revamped and allow you to set multiple restart types per node as well as naming them
 - Trigger scripts are now stored in separate blocks in Blender's text editor
    * This prevents you from misspelling a custom script name, as the field is now a dropdown list
 - Revamped material pass settings to checkbox flags that better represent how they're stored/used in game
    * Flag-specific settings appear when the option is checked off
 - Added separate export option for models, which generates them in the correct file formats, uncompressed, in a Models directory
 - Added skybox option when exporting scenes
 - Added mipmap offset export option to quickly size down textures when working with highly detailed scenes that need to be toned down for the THUG engine
 - Added 'vertex color hack' for THPS3 imported levels that are too dark
 - Fixed bug with collision importing that would cause some collision meshes to have the wrong name and flags settings
 - Fixed export issue with vertex colours in THUG1 levels where the scene would appear extremely bright
 - Fixed huge THUG1 export bug that would not save all UV maps referenced by materials, thus resulting in very warped/stretched textures
