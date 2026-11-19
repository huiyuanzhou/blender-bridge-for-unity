using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

// Material properties that FBX cannot represent travel in a Library-only import request.
internal static class BlenderBridgeMaterials
{
    [Serializable] internal class TextureData
    {
        public string path;
        public Vector2 scale;
        public Vector2 offset;
    }

    [Serializable] internal class MaterialData
    {
        public string id;
        public string name;
        public string shader;
        public TextureData base_texture;
        public string color_property;
        public Color base_color = Color.white;
        public string color_space;
        public TextureData metallic;
        public string encoding;
        public float metallic_scale;
        public float smoothness;
        public bool texture_active;
    }

    [Serializable] internal class Binding
    {
        public string[] object_path;
        public string[] exported_object_path;
        public string[] materials;
    }

    [Serializable] internal class Request
    {
        public int version = 1;
        public string model_path;
        public MaterialData[] materials;
        public Binding[] bindings;
    }

    internal static string CreateImportRequest(GameObject root, string modelPath, bool exportedHierarchy = false)
    {
        if (root == null) return modelPath;
        var materials = new List<MaterialData>();
        var bindings = new List<Binding>();
        var ids = new Dictionary<string, string>();
        var exportedPaths = exportedHierarchy ? ExportedPaths(root) : null;
        foreach (Renderer renderer in root.GetComponentsInChildren<Renderer>(true))
        {
            if (!(renderer is MeshRenderer) && !(renderer is SkinnedMeshRenderer)) continue;
            var slotIds = new List<string>();
            var rendererBlock = new MaterialPropertyBlock();
            renderer.GetPropertyBlock(rendererBlock);
            Material[] sharedMaterials = renderer.sharedMaterials;
            for (int slot = 0; slot < sharedMaterials.Length; slot++)
            {
                Material material = sharedMaterials[slot];
                if (material == null) { slotIds.Add(""); continue; }
                string colorProperty = material.HasColor("_BaseColor") ? "_BaseColor"
                    : material.HasColor("_Color") ? "_Color" : "";
                Color color = string.IsNullOrEmpty(colorProperty) ? Color.white : material.GetColor(colorProperty);
                var slotBlock = new MaterialPropertyBlock();
                renderer.GetPropertyBlock(slotBlock, slot);
                // A per-material block takes precedence over the whole renderer block.
                var block = !slotBlock.isEmpty ? slotBlock : rendererBlock;
                if (!string.IsNullOrEmpty(colorProperty) && block.HasColor(colorProperty))
                    color = block.GetColor(colorProperty);
                bool linear = QualitySettings.activeColorSpace == ColorSpace.Linear;
                if (linear) color = color.linear;
                string key = material.GetInstanceID() + ":" + JsonUtility.ToJson(color);
                if (!ids.TryGetValue(key, out string id))
                {
                    id = materials.Count.ToString();
                    ids.Add(key, id);
                    string shader = material.shader != null ? material.shader.name : "";
                    bool chicken = IsChickenRgbShader(shader);
                    // Unknown shader packing is preserved as data, without guessing its preview.
                    bool standard = IsStandardMetallic(shader)
                        && ReadFloat(material, "_SmoothnessTextureChannel", 0) == 0
                        && ReadFloat(material, "_WorkflowMode", 1) == 1;
                    string encoding = chicken ? "chicken-rgb-v1" : standard ? "unity-r-a-v1" : "raw-v1";
                    TextureData metallic = ReadTexture(material, "_MetallicGlossMap");
                    // These shader families sample the mask using the base map UV transform.
                    string uvProperty = material.HasProperty("_BaseMap") ? "_BaseMap" : "_MainTex";
                    if (metallic != null && (chicken || standard) && material.HasProperty(uvProperty))
                    {
                        metallic.scale = material.GetTextureScale(uvProperty);
                        metallic.offset = material.GetTextureOffset(uvProperty);
                    }
                    materials.Add(new MaterialData {
                        id = id, name = material.name, shader = shader,
                        base_texture = ReadTexture(material, material.HasProperty("_BaseMap") ? "_BaseMap" : "_MainTex"),
                        color_property = colorProperty, base_color = color, color_space = linear ? "linear" : "gamma",
                        metallic = metallic, encoding = encoding,
                        metallic_scale = chicken ? ReadFloat(material, "_Metallic", 1) : 1,
                        smoothness = ReadFloat(material, "_Smoothness", ReadFloat(material, "_GlossMapScale", 1)),
                        texture_active = chicken || (standard && material.IsKeywordEnabled(
                            shader == "Standard" ? "_METALLICGLOSSMAP" : "_METALLICSPECGLOSSMAP"))
                    });
                }
                slotIds.Add(id);
            }
            var names = new List<string>();
            for (Transform current = renderer.transform; current != null; current = current.parent)
            {
                names.Add(current.name);
                if (current == root.transform) break;
            }
            names.Reverse();
            bindings.Add(new Binding { object_path = names.ToArray(), materials = slotIds.ToArray(),
                exported_object_path = exportedPaths != null ? exportedPaths[renderer.transform] : names.ToArray() });
        }
        if (!materials.Exists(m => m.metallic != null || !string.IsNullOrEmpty(m.color_property))) return modelPath;
        string directory = Path.Combine(Path.GetDirectoryName(Application.dataPath), "Library/BlenderBridge/Materials");
        Directory.CreateDirectory(directory);
        string path = Path.Combine(directory, Guid.NewGuid().ToString("N") + ".bridge-import");
        File.WriteAllText(path, JsonUtility.ToJson(new Request {
            model_path = Path.GetFullPath(modelPath), materials = materials.ToArray(), bindings = bindings.ToArray()
        }, true));
        return path;
    }

    private static Dictionary<Transform, string[]> ExportedPaths(GameObject root)
    {
        // ExportObject's default options use Maya names, globally uniquified in depth-first order.
        // Use the exporter's own converter so accents/namespaces follow its installed version.
        Type exporter = Type.GetType("UnityEditor.Formats.Fbx.Exporter.ModelExporter, Unity.Formats.Fbx.Editor", true);
        MethodInfo convert = exporter.GetMethod("ConvertToMayaCompatibleName", BindingFlags.Static | BindingFlags.NonPublic);
        if (convert == null) throw new NotSupportedException("FBX exporter name conversion API was not found");
        var paths = new Dictionary<Transform, string[]>();
        var counts = new Dictionary<string, int>();
        foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
        {
            string name = (string)convert.Invoke(null, new object[] { transform.name });
            counts.TryGetValue(name, out int count);
            counts[name] = count + 1;
            string unique = count == 0 ? name : name + "_" + count;
            var path = transform == root.transform ? new List<string>() : new List<string>(paths[transform.parent]);
            path.Add(unique);
            paths.Add(transform, path.ToArray());
        }
        return paths;
    }

    private static TextureData ReadTexture(Material material, string property)
    {
        if (!material.HasProperty(property)) return null;
        Texture texture = material.GetTexture(property);
        if (texture == null) return null;
        string assetPath = AssetDatabase.GetAssetPath(texture);
        if (string.IsNullOrEmpty(assetPath)) return null;
        string fullPath = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(Application.dataPath), assetPath));
        var package = UnityEditor.PackageManager.PackageInfo.FindForAssetPath(assetPath);
        if (package != null && assetPath.StartsWith(package.assetPath + "/", StringComparison.Ordinal))
            fullPath = Path.Combine(package.resolvedPath, assetPath.Substring(package.assetPath.Length + 1));
        if (!File.Exists(fullPath)) return null;
        return new TextureData { path = fullPath, scale = material.GetTextureScale(property), offset = material.GetTextureOffset(property) };
    }

    private static float ReadFloat(Material material, string property, float fallback)
    {
        return material.HasProperty(property) ? material.GetFloat(property) : fallback;
    }

    private static bool IsStandardMetallic(string shader)
    {
        return shader == "Standard" || shader == "Universal Render Pipeline/Lit";
    }

    private static bool IsChickenRgbShader(string shader)
    {
        switch (shader)
        {
            case "Chicken/PC/PBR/Lit": case "Chicken/Scene/PBR/Lit":
            case "Chicken/Scene/PBR/LitMagma": case "Chicken/Scene/PBR/SandLit":
            case "Chicken/Scene/PBR/LBP_Lightmap": case "Chicken/Scene/PBR/Lightmap":
                return true;
            default: return false;
        }
    }
}
