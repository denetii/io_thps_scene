# io_thps_scene
An extension of the last public release of the THPS/THUG scene import/export tools for Blender. 
This version fixes tons of bugs and adds a whole host of new features to make level creation easier for THUG1, THUG2 and THUG PRO.

## Working with previous scenes
Your .blend scenes that were built for the previous plugin, `io_thug_tools`, will need a little converting before they'll export correctly here. The plugin can detect old scenes, and automatically converts what it can, but there will be a few things that need to be done manually.
1. Player restarts, CTF Flags, and KOTH nodes need to be reconfigured, as the interface has been revamped a little bit and the options lists changed.
2. Restarts and other nodes may need to be rotated, as the exporter no longer auto-rotates these elements. This was changed so that THUG1/2/PRO scenes would export the same way, as well as imported levels.

## Change list
Here's the full list of changes and bug fixes since the previous public release of `io_thug_tools`:

 - Added tons of missing object properties and node types - the vast majority of object/nodes are fully handled directly in the plugin, without the need for 'node expansion' blocks. Some examples include:
     * Network Options, which lets you control whether appear in online play
     * LightGroup setting for scene meshes
     * Pedestrian/AI skater paths can now be fully set up directly in the plugin
     * Occluders can now be configured directly in the editor    
     * Added the missing 'no skater shadow' option
     * Restarts have been revamped and allow you to set multiple restart types per node as well as naming them
 - Added presets! Most nodes can be inserted through the new presets menu
     - Park editor pieces from THPS3, THPS4, THUG1, and THUG2/PRO are also part of the presets menu
 - Fully automated lightmap baking! Easily bake lighting or ambient occlusion to your level/model/skin 
 - Even more import options:
     - Added THUG1 and THPS4 scene/model importing!
     - QB importing has been added, allowing you to set original object names on imported scenes
     - Added import support for node arrays from existing levels!
        * Rails, waypoints, object settings and more are parsed and placed into the scene
     - Trigger scripts from existing levels can now be imported!
     - Import your custom parks (.PRK) from THUG1/2/PRO and the plugin will generate the scene for you! (Experimental feature)
 - Totally revamped object/node scripting, using an all-new template system that gives you more built-in TriggerScripts
     - Custom scripting is now easier and more foolproof, using separate text blocks rather than `THUG_SCRIPTS`
 - Greatly expanded/improved export options:
     - Revamped export file structure to match what the game engines expect - it is now possible to export models/skins/levels directly into the game
     - Added separate export option for models, which generates them in the correct file formats, uncompressed, in a Models directory
     - New 'auto-split everything' option, applies the autosplit modifier to each object in the scene
     - New skybox option when exporting scenes
     - New mipmap offset export option, to quickly size down textures
     - 'No modifiers' speed hack greatly speeds up COL/SCN exporting, especially on large levels
     - Park editor dictionaries can now be exported with full compatibility
     - All-new 'Quick Export' option lets you save your export settings and re-export with one click!
     - Levels can now be exported in the new custom level format (used on THUG PRO)
 - New settings when working with materials/textures:
     - Added support for environment mapped texture passes
     - Support for the new material/shader system used in Underground+ 1.5+ (more details coming soon!)
     - Revamped material pass settings to checkbox flags that better represent how they're stored/used in game
        * Flag-specific settings appear when the option is checked off
 - Added support for using separate scene/collision mesh
 - Rail, waypoint and ladder paths now render larger and are assigned materials - allowing you to customize how they're displayed in the editor
 - Added new utility functions, allowing you to:
     - Auto-merge scene/collision mesh
     - Automatically assign the wallride flag to objects in your scene, based on the face normal
     - Auto-fill vehicle/pedestrian properties
     - Batch apply object properties on a selection
     - Set terrain type on a selection of objects
     - Select the first point on a rail/waypoint path
 - Tons of bug fixes!
     - Imported levels/models/skins now retain their object name checksums on export, fixing a long-standing issue that prevented you from making custom CAS/board models
     - Fixed bug with collision importing that would cause some collision meshes to have the wrong name and flags settings
     - Fixed export issue with vertex colours in THUG1 levels where the scene would appear extremely bright
     - Fixed huge THUG1 export bug that would not save all UV maps referenced by materials, thus resulting in very warped/stretched textures
     - Fixed incorrect collision generation for LevelObjects 
