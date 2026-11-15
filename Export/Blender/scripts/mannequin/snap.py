
import bpy
def snap(frames):
    g={}; exec(bpy.data.texts['skel_preview.py'].as_string(), g)
    arm=bpy.data.objects['root']; sc=bpy.context.scene
    for o in [o for o in bpy.data.objects if o.name.startswith('Prev_')]: bpy.data.objects.remove(o)
    names=[]
    for i,f in enumerate(frames):
        arm.hide_viewport=False; sc.frame_set(f); bpy.context.view_layer.update()
        ob=g['build_skel'](); o=bpy.data.objects.new(f'Prev_{f}', ob.data.copy()); sc.collection.objects.link(o); o.location.y=i*1.2; names.append(o.name)
    bpy.data.objects['SkelPreview'].hide_viewport=True
    arm.hide_viewport=False
    return names
