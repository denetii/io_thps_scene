# io_thps_scene
This Blender addon allows you to export a scene as a custom level for some of the classic THPS games. Also includes a variety of import tools to load existing levels/assets, as well as a fully integrated lightmap baking tool.

## Migrating from Blender 2.79
Unfortunately, due to various breaking changes introduced with Blender 2.8x, there is no way to seamlessly convert old .blend files that were developed on Blender 2.79. However, I have written a pair of scripts that will take care of it for you. You'll still need Blender 2.79 installed on your system, and you need to know how to run scripts in the text editor. Grab these two scripts here: https://gist.github.com/denetii/6e66891505b32fc7c64c22031288d7f4

'Step 1' is a script that needs to be run on your .blend file from within Blender **2.79**. Once that's done, save a copy of your scene, then open the new copy in **2.8x** and run the 'Step 2' script in there. Your scene should now be fully migrated and exportable from within 2.8x. The addon has been tested on **2.83.4**, but should be compatible with most of the 2.8x versions.

While support for the 2.79 addon isn't stopping yet, eventually the development will move fully to the 2.8x addon.

## Installation/Documentation
The complete documentation and changelog can be found at: http://tharchive.net/misc/io_thps_scene.html
You can download the addon from there, or grab the newest release on GitHub. It should be a zip file containing two other zip files. Extract the one that corresponds to your Blender version:
 - `io_thps_scene_blender2.79.zip` is for Blender 2.79
 - `io_thps_scene_blender2.8.zip` is for Blender 2.8 and newer. Has been developed on 2.83 LTS, but is also compatible with 2.9x

Ensure the zip file you extract is renamed to `io_thps_scene.zip`, or the installation may not work correctly. Once done, go to Blender's addon manager, click 'Install add-on from file', then choose the zip file you just created. The addon should then appear in the list - click the checkbox to activate it.

There are a few options you can configure, such as viewport colors and menu options. If you wish to use game asset integration, then configure the path to your THPS game installation(s) here. 

## Changes from the 2.79 version
Since the addon was just migrated, most of the functionality will appear virtually the same as in the 2.79 releases. However, there are a few things to note:
 * The removal of Blender Internal from 2.8 means that I had to implement a way to translate the 'legacy' THPS material/material pass settings into shader nodes for Cycles/Eevee. The result is a much more accurate viewport representation of your materials, including proper handling of vertex colors, vertex alpha, and most blending modes. This will be particularly noticeable when working with imported scenes from the base THPS games.
 * To simplify installation/first time setup, there is no secondary `thug_tools` package required for setup. All necessary assets are bundled in with the addon code. 
 * Because Blender 2.8 finally uses `RGBA` instead of RGB for vertex color channels, there is no need for a second 'alpha' channel to represent vertex alpha on your meshes. The conversion script moves the R value from the 'alpha' RGB into the 'color' channel's alpha value. 
 * Exporting scenes is now much faster without using the 'Speed Hack' export option. The difference in performance is now much lower, perhaps negating the need for the speed hack. But it will remain there for now. This ultimately means you don't have to completely triangulate the scene if you want faster exporting. (This update will come to the 2.79 addon as well)
 * Viewport rendering performance is lower than in 2.79 when a large number of objects that use the addon's color codes (collision flags, auto-rails, etc) are selected at once. This is partly due to the updated OpenGL version in 2.8 removing display lists, but the viewport drawing code needs to be rewritten anyway. 

## Examples 
I host a selection of custom levels built with this addon on the Tony Hawk Archive: http://tharchive.net/misc/custom_levels.html
You can also find a larger collection of custom levels at THPSX: http://thpsx.com/community-upload-list/
