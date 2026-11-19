"""Import the Unity tint fixture and bake its actual material graphs into an atlas."""
import json
from pathlib import Path
import runpy
import sys
import tempfile

import bpy

ROOT = Path(__file__).resolve().parents[2]
injector = runpy.run_path(str(ROOT / 'Editor/blender-bridge-injector.py'))
request_path = Path(sys.argv[sys.argv.index('--') + 1])
request = json.loads(request_path.read_text(encoding='utf-8-sig'))
bpy.ops.preferences.addon_enable(module='better_fbx')
injector['UnityModelExporter'](str(request_path)).load_model()
helper = injector['_material_helpers']('blender_bridge_tints')
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
assert len(meshes) == 3
assert bpy.context.scene['unity_model_path'] == request['model_path']
seen = []
for obj in meshes:
    mat = obj.material_slots[0].material
    entry = json.loads(mat['unity_bridge_material'])
    tint = helper.inspect_base_color_tint(mat)
    expected = entry['base_color']
    assert tint['color_space'] == entry['color_space']
    assert all(abs(tint['tint'][i] - expected[k]) < 1e-6 for i,k in enumerate(('r','g','b','a')))
    assert Path(tint['image'].filepath) == Path(entry['base_texture']['path'])
    assert not any(n.get('unity_bridge_packed_map') for n in mat.node_tree.nodes)
    seen.append((obj.name, entry['id'], tint['tint']))
assert len({row[1] for row in seen}) == 3
assert all(row[2][:3] != (1,1,1) for row in seen)
if '--atlas-root' in sys.argv:
    sys.path.insert(0, sys.argv[sys.argv.index('--atlas-root') + 1])
    from brick_atlas_tool import core, model_export
    analysis = core.analyze_objects(meshes)
    groups = core.auto_pack(analysis['groups'], 128, 128, 4)
    generated = core.generate_atlas(meshes, groups, 128, 128, 4, 'UnityTintIntegration', False)
    generated_mat = bpy.data.materials[generated['material']]
    assert helper.inspect_base_color_tint(generated_mat) is None
    assert all(g['color_tint'][:3] != [1,1,1] for g in analysis['groups'])
    with tempfile.TemporaryDirectory(prefix='unity_tint_integration_') as folder:
        output = model_export.export_collection(generated['collection'], folder)
        assert len(output['fbx_paths']) == 3
        assert Path(output['color_path']).is_file()
print('TINT_IMPORT_CHECK: ALL_CHECKS_PASSED', seen)
