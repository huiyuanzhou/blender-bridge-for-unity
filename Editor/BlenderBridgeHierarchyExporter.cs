using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// Exports the selected scene hierarchy through Unity's optional FBX Exporter package
/// and opens the resulting temporary FBX with the existing Blender Bridge pipeline.
/// </summary>
internal static class BlenderBridgeHierarchyExporter
{
    private const string MenuPath = "Blender Bridge/Open Selected Hierarchy in Blender";
    private const string GameObjectMenuPath = "GameObject/Blender Bridge/Open Hierarchy in Blender";
    private const string TempDirectory = "Library/BlenderBridge/Hierarchy";

    [MenuItem(MenuPath, false, 2000)]
    private static void OpenSelectedHierarchy()
    {
        GameObject root = Selection.activeGameObject;
        if (!IsValidSceneGameObject(root))
        {
            Debug.LogError(
                "[BlenderBridge] Select a GameObject from a loaded scene before exporting its hierarchy.");
            return;
        }

        if (!TryExportHierarchy(root, out string exportPath, out string error))
        {
            Debug.LogError($"[BlenderBridge] Could not export hierarchy '{root.name}': {error}");
            return;
        }

        Debug.Log($"[BlenderBridge] Exported hierarchy '{root.name}' to '{exportPath}'.");
        BlenderBridgeProcessor.OpenInBlender($"Hierarchy: {root.name}", exportPath);
    }

    [MenuItem(MenuPath, true)]
    private static bool ValidateOpenSelectedHierarchy()
    {
        return IsValidSceneGameObject(Selection.activeGameObject);
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
        return gameObject != null
            && gameObject.scene.IsValid()
            && !EditorSceneManager.IsPreviewScene(gameObject.scene)
            && !EditorUtility.IsPersistent(gameObject);
    }

    private static bool TryExportHierarchy(GameObject root, out string exportPath, out string error)
    {
        exportPath = null;
        error = null;

        MethodInfo exportMethod = FindExportObjectMethod();
        if (exportMethod == null)
        {
            error =
                "Unity FBX Exporter was not found. Install the com.unity.formats.fbx package " +
                "and ensure UnityEditor.Formats.Fbx.Exporter.ModelExporter is available.";
            return false;
        }

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

            exportMethod.Invoke(null, new object[] { exportPath, root });
            if (!File.Exists(exportPath))
            {
                error = $"The FBX exporter completed without creating '{exportPath}'.";
                exportPath = null;
                return false;
            }

            return true;
        }
        catch (TargetInvocationException ex)
        {
            Exception cause = ex.InnerException ?? ex;
            error = $"FBX ExportObject failed: {cause.Message}";
            exportPath = null;
            return false;
        }
        catch (Exception ex)
        {
            error = $"FBX export failed: {ex.Message}";
            exportPath = null;
            return false;
        }
    }

    private static MethodInfo FindExportObjectMethod()
    {
        const string typeName = "UnityEditor.Formats.Fbx.Exporter.ModelExporter";
        const string assemblyQualifiedTypeName = typeName + ", Unity.Formats.Fbx.Editor";
        Type exporterType = Type.GetType(assemblyQualifiedTypeName, false);

        if (exporterType == null)
        {
            foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                try
                {
                    exporterType = assembly.GetType(typeName, false);
                }
                catch (ReflectionTypeLoadException)
                {
                    // A partially loadable editor assembly cannot provide the exporter type.
                }

                if (exporterType != null)
                {
                    break;
                }
            }
        }

        if (exporterType == null)
        {
            return null;
        }

        foreach (MethodInfo method in exporterType.GetMethods(BindingFlags.Public | BindingFlags.Static))
        {
            if (!string.Equals(method.Name, "ExportObject", StringComparison.Ordinal))
            {
                continue;
            }

            ParameterInfo[] parameters = method.GetParameters();
            if (parameters.Length == 2
                && parameters[0].ParameterType == typeof(string)
                && typeof(UnityEngine.Object).IsAssignableFrom(parameters[1].ParameterType))
            {
                return method;
            }
        }

        return null;
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
