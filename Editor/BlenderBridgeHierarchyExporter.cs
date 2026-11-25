using System;
using System.IO;
using UnityEditor;
using UnityEditor.Formats.Fbx.Exporter;
using UnityEditor.SceneManagement;
using UnityEditor.ShortcutManagement;
using UnityEngine;

/// <summary>
/// Exports the selected scene hierarchy through Unity's FBX Exporter package
/// and opens the resulting temporary FBX with the existing Blender Bridge pipeline.
/// </summary>
internal static class BlenderBridgeHierarchyExporter
{
    private const string GameObjectMenuPath = "GameObject/Blender Bridge/Open Hierarchy in Blender";
    private const string TempDirectory = "Library/BlenderBridge/Hierarchy";

    [Shortcut("Blender Bridge/Open Selected Hierarchy in Blender", KeyCode.F9, ShortcutModifiers.Shift)]
    private static void OpenSelectedHierarchy()
    {
        GameObject root = Selection.activeGameObject;
        if (!IsValidSceneGameObject(root))
        {
            Debug.LogError(
                "[BlenderBridge] Select a GameObject from a loaded scene or Prefab Mode before exporting its hierarchy.");
            return;
        }

        if (!TryExportHierarchy(root, out string exportPath, out string error))
        {
            Debug.LogError($"[BlenderBridge] Could not export hierarchy '{root.name}': {error}");
            return;
        }

        Debug.Log($"[BlenderBridge] Exported hierarchy '{root.name}' to '{exportPath}'.");
        BlenderBridgeProcessor.OpenInBlender($"Hierarchy: {root.name}", exportPath, root, true);
    }

    [MenuItem(GameObjectMenuPath, false, 49)]
    private static void OpenSelectedHierarchyFromGameObjectMenu()
    {
        OpenSelectedHierarchy();
    }

    [MenuItem(GameObjectMenuPath, true)]
    private static bool ValidateOpenSelectedHierarchyFromGameObjectMenu()
    {
        return IsValidSceneGameObject(Selection.activeGameObject);
    }

    private static bool IsValidSceneGameObject(GameObject gameObject)
    {
        if (gameObject == null
            || !gameObject.scene.IsValid()
            || EditorUtility.IsPersistent(gameObject))
        {
            return false;
        }

        if (!EditorSceneManager.IsPreviewScene(gameObject.scene))
        {
            return true;
        }

        // Prefab Mode uses a preview scene too. Allow its editable contents,
        // while keeping Inspector previews and other temporary objects excluded.
        PrefabStage prefabStage = PrefabStageUtility.GetPrefabStage(gameObject);
        return prefabStage != null && prefabStage.IsPartOfPrefabContents(gameObject);
    }

    private static bool TryExportHierarchy(GameObject root, out string exportPath, out string error)
    {
        exportPath = null;
        error = null;

        try
        {
            string projectRoot = Path.GetDirectoryName(Application.dataPath);
            string directory = Path.Combine(projectRoot, TempDirectory);
            Directory.CreateDirectory(directory);

            string safeName = MakeSafeFileName(root.name);
            exportPath = Path.Combine(
                directory,
                $"{safeName}_{DateTime.UtcNow:yyyyMMdd_HHmmssfff}_{Guid.NewGuid():N}.fbx");
            exportPath = Path.GetFullPath(exportPath);

            ModelExporter.ExportObject(exportPath, root);
            if (!File.Exists(exportPath))
            {
                error = $"The FBX exporter completed without creating '{exportPath}'.";
                exportPath = null;
                return false;
            }

            return true;
        }
        catch (Exception ex)
        {
            error = $"FBX export failed: {ex.Message}";
            exportPath = null;
            return false;
        }
    }

    private static string MakeSafeFileName(string name)
    {
        string value = string.IsNullOrWhiteSpace(name) ? "SelectedHierarchy" : name.Trim();
        foreach (char invalidCharacter in Path.GetInvalidFileNameChars())
        {
            value = value.Replace(invalidCharacter, '_');
        }

        return value;
    }
}
