"""Run with Blender --background --factory-startup --python-exit-code 1 --python."""
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import Mock

import bpy

ROOT = Path(__file__).resolve().parents[2]
bridge = runpy.run_path(str(ROOT / "Editor/blender-bridge-injector.py"))
operator = bridge["WM_OT_save_unity_model"]
exporter = bridge["UnityModelExporter"]

with tempfile.TemporaryDirectory(prefix="bridge_save_check_") as directory:
    target = Path(directory) / "Edited.fbx"
    scene = bpy.context.scene
    scene["unity_model_path"] = str(target)
    scene["unity_model_format"] = ".fbx"
    bpy.utils.register_class(operator)
    try:
        # A real export must return and reach the final success marker. The old
        # save-and-quit behavior terminated Blender here before reaching it.
        assert bpy.ops.wm.save_unity_model() == {"FINISHED"}
        assert target.is_file() and target.stat().st_size > 100
        assert target.read_bytes().startswith(b"Kaydara FBX Binary")

        # Failed exports keep the session alive and report failure.
        class Reports:
            def __init__(self): self.messages = []
            def report(self, severity, message): self.messages.append((severity, message))
        reports = Reports()
        quit_op = Mock(side_effect=AssertionError("Save attempted to quit"))
        save_op = Mock(return_value={"RUNNING_MODAL"})
        # bpy.ops resolves each attribute dynamically; inject a controlled ops
        # facade for branches that cannot display a save dialog in background.
        facade = SimpleNamespace(ops=SimpleNamespace(wm=SimpleNamespace(quit_blender=quit_op,save_mainfile=save_op)))
        with patch.object(exporter, "export_to_unity", side_effect=OSError("test export failure")), \
             patch.dict(operator.execute.__globals__, bpy=facade):
            assert operator.execute(reports, bpy.context) == {"CANCELLED"}
            assert reports.messages[-1][0] == {"ERROR"}
            quit_op.assert_not_called()

        del scene["unity_model_path"]
        del scene["unity_model_format"]
        with patch.dict(operator.execute.__globals__, bpy=facade):
            assert operator.execute(reports,bpy.context) == {"FINISHED"}
            save_op.assert_called_once_with("INVOKE_DEFAULT")
            quit_op.assert_not_called()
    finally:
        bpy.utils.unregister_class(operator)

print("BRIDGE_SAVE_TEST successful=true real_fbx_export=true export_failure_keeps_open=true normal_save_keeps_open=true")
