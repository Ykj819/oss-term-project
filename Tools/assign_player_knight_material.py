# Put M_PlayerKnight on every slot of SKM_PlayerKnight (after a reimport the slot can fall back to WorldGridMaterial
# when the material is set while Interchange is still building the skinned asset).
import unreal
eal = unreal.EditorAssetLibrary
MESH = "/Game/Characters/PlayerKnight/SKM_PlayerKnight"
mesh = unreal.load_asset(MESH)
mat = unreal.load_asset("/Game/Characters/PlayerKnight/M_PlayerKnight")
mats = mesh.get_editor_property("materials")
new = []
for i in range(len(mats)):
    m = mats[i]                       # unreal.Array indexing returns a COPY: edit it, then put the copies back
    m.set_editor_property("material_interface", mat)
    new.append(m)
mesh.set_editor_property("materials", new)
eal.save_asset(MESH, only_if_is_dirty=False)
mesh = unreal.load_asset(MESH)
unreal.log_warning("KMAT " + str([x.get_editor_property("material_interface").get_name() for x in mesh.get_editor_property("materials")]))
