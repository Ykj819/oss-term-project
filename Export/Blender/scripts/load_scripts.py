# Loads the generator scripts in this folder into the open .blend as text blocks (replacing ones with the same name).
# The generators exec each other through bpy.data.texts['<name>.py'], so they must live in the .blend to run.
#
# Usage (Blender Python console or MCP):
#   exec(open(r"<project>/Export/Blender/scripts/load_scripts.py", encoding="utf-8").read(), {"SUBDIR": "mannequin"})
# SUBDIR = "mannequin" (open Club.blend) or "wolf" (open Wolf_Rig.blend).
import bpy, os

HERE = os.path.join(os.path.dirname(bpy.data.filepath), "scripts") if bpy.data.filepath else ""
sub = globals().get("SUBDIR", "mannequin")
folder = os.path.join(HERE, sub)
for name in sorted(os.listdir(folder)):
    if not name.endswith(".py"):
        continue
    with open(os.path.join(folder, name), encoding="utf-8") as f:
        src = f.read()
    t = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    t.clear(); t.write(src)
    print("loaded", name)
