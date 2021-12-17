import bpy

scene = bpy.context.scene
print(scene.frame_end - scene.frame_start + 1)
