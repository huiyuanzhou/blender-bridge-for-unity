"""Blender background regression checks; pass the Unity-generated .bridge-import after --."""
import json
from pathlib import Path
import runpy
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
module = runpy.run_path(str(ROOT / 'Editor/blender-bridge-injector.py'))
request_path = Path(sys.argv[sys.argv.index('--') + 1])
request = json.loads(request_path.read_text(encoding='utf-8-sig'))
bpy.ops.preferences.addon_enable(module='better_fbx')
module['UnityModelExporter'](str(request_path)).load_model()
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
assert len(meshes) == 4, [obj.name for obj in meshes]
assert bpy.context.scene['unity_model_path'] == request['model_path']
helper = module['_material_helpers']()
results = []
dormant = 0
for obj in meshes:
    mat = obj.material_slots[0].material
    entry = json.loads(mat['unity_bridge_material'])
    if not entry['texture_active']:
        assert not any(n.get('unity_bridge_packed_map') for n in mat.node_tree.nodes)
        assert any(n.get('unity_bridge_raw_metallic') for n in mat.node_tree.nodes)
        dormant += 1
        continue
    group, = [n for n in mat.node_tree.nodes if n.get('unity_bridge_packed_map')]
    assert group.inputs['Metallic Scale'].default_value == entry['metallic_scale']
    assert abs(group.inputs['Smoothness'].default_value - entry['smoothness']) < 1e-6
    image = group.inputs['Color'].links[0].from_node.image
    assert Path(image.filepath) == Path(entry['metallic']['path'])
    assert image.colorspace_settings.name == 'Non-Color'
    assert image.alpha_mode == 'CHANNEL_PACKED'
    results.append((obj.name, entry['id'], image.name, entry['encoding']))
assert len({entry[1] for entry in results}) == 2, results
assert dormant == 1
assert {row[0] for row in results} == {'Cube', 'Cube_1', 'Cube_2'}
# Two Unity materials with identical names must remain distinct by object path/slot.
assert len({Path(obj.material_slots[0].material.node_tree.nodes[
    next(n.name for n in obj.material_slots[0].material.node_tree.nodes if n.get('unity_bridge_packed_map'))
].inputs['Color'].links[0].from_node.image.filepath) for obj in meshes if obj.name != 'Dormant'}) == 2
print('MATERIAL_IMPORT_CHECK: ALL_CHECKS_PASSED', results)
