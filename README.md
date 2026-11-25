# Blender Bridge

[English](#english) · [中文](#中文)

---

Open `.FBX`, `.OBJ`, `.DAE`, and Unity Mesh (`.mesh` / `.asset`) assets in Blender from Unity, then export straight back to the original asset. Ctrl+S in Blender is overridden so saving writes to the Unity project file instead of a `.blend`.

**Version:** 0.1.18 · **Unity:** 2022.3+ · **Platform:** Windows

## Installing

1. Open Unity and go to **Window → Package Manager**
2. Click the **+** button in the top-left
3. Choose **Add package from git URL**
4. Enter:
  ```
   https://github.com/huiyuanzhou/blender-bridge-for-unity.git
  ```
5. Done — configure your Blender path (see [Configuration](#configuration)).

## Quick start

1. Set your Blender executable path in **Edit > Project Settings > Blender Bridge** (see [Configuration](#configuration)).
2. For an asset round-trip, double-click an `.fbx`, `.obj`, `.dae`, `.mesh`, or Mesh `.asset` in the Unity Project window, edit it in Blender, then press **Ctrl+S** or use **File → Export → … (back to original Unity asset)**.
3. For a scene hierarchy, install the Unity FBX Exporter package, select its root GameObject in the Unity Hierarchy, and press **Shift+F9**. You can also use **GameObject → Blender Bridge → Open Hierarchy in Blender**. In Prefab Mode, select the prefab root or any child to export that object and its descendants.
4. Edit the exported hierarchy in Blender. This workflow opens a temporary FBX under `Library/BlenderBridge/Hierarchy`; saving it updates that temporary file only and does not modify the Unity scene.

## Features

- **Double-click to edit** — open supported 3D assets directly from the Unity Project window
- **Hierarchy export** — send a selected scene GameObject and its complete child hierarchy to Blender through a temporary FBX (saving that file does not write changes back to the Unity scene)
- **Metallicmap transfer** — carries assigned Unity `_MetallicGlossMap` textures alongside FBX imports, including renderer material overrides and inactive children. Packed RGBA stays in Non-Color / Channel Packed data. Chicken Scene RGB masks and Unity Standard/URP metallic R + smoothness A receive explicit Metallic/Roughness nodes; unrecognized shader packing is retained as an image with a warning.
- **Base color tint** — reconstructs `_BaseColor` (or legacy `_Color`) multiplied with the assigned base texture, including renderer and per-material property block color overrides. Uses the Unity project's Gamma/Linear color space. BrickAtlas 1.6.0 bakes each material's RGB tint into its color atlas and leaves the output material white, so the tint is applied once. Custom shader layers, vertex colors, lighting and transparency are outside this RGB tint transfer.
- **Unity Mesh (.mesh / .asset)** — opens Mesh assets through a JSON interchange under `Library/BlenderBridge/`, including meshes with Read/Write disabled
- **Matching up axis** — Unity Mesh assets are shown Z-up in Blender and converted back to Unity Y-up on save
- **Hot reuse** — if Blender is already running, the next double-click imports into the same window instead of launching another instance
- **Auto focus** — when hot-reusing Blender, the window is brought to the foreground automatically
- **Asset save back to Unity** — Ctrl+S and the File → Export menu export edited project assets to their original paths
- **Format preserved** — round-trip stays in the same format (FBX / OBJ / DAE / Mesh)
- **Unity-aware FBX** — reads Unity `.meta` importer settings (normals, smooth angle, axis) for better round-trip fidelity
- **Better FBX support** — uses the [Better FBX Importer & Exporter](https://blendermarket.com/products/better-fbx-importer-exporter) addon when installed; falls back to Blender's built-in FBX importer/exporter
- **Transform preservation** — restores object transforms before export and bakes static FBX geometric pivots so Unity root rotation/position stay unchanged
- **Viewport framing** — zooms the 3D view to the imported model
- **Face select mode** — mesh edit mode defaults to face selection
- **No splash screen** — Blender opens without the splash
- **Optional texture loading** — can auto-apply textures from a folder (off by default)

[https://github.com/user-attachments/assets/c8879a20-0098-4138-a847-a047c0887f8a](https://github.com/user-attachments/assets/c8879a20-0098-4138-a847-a047c0887f8a)

## Requirements


| Requirement          | Notes                                                                                                     |
| -------------------- | --------------------------------------------------------------------------------------------------------- |
| **Windows**          | Editor integration uses Windows process and window APIs                                                   |
| **Blender 5.x**      | Default path targets Blender 5.1; other versions can be selected in Project Settings                     |
| **Unity FBX Exporter** | Required for the Hierarchy export command; discovered at runtime and optional for asset double-click workflows |
| **Better FBX addon** | Strongly recommended for FBX (especially ASCII FBX and correct normals). Built-in FBX is used as fallback |


## Configuration

Project-level options are available under **Edit > Project Settings > Blender Bridge**. The remaining advanced options are documented below.

### Blender executable path

In Unity, open **Edit > Project Settings > Blender Bridge** and select your Blender executable. The setting is saved per project in `ProjectSettings/BlenderBridgeSettings.asset`.

Common locations:

- Standard install: `C:\Program Files\Blender Foundation\Blender X.X\blender.exe`
- Steam: `C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe`

### Save without closing Blender

Ctrl+S and the File → Export menu write the edited model back to Unity and keep Blender open. Saving never quits Blender automatically. Ctrl+S in a Bridge session exports the original model; use Save As to keep a separate `.blend` working file.

### Texture loading

In `Editor/blender-bridge-injector.py`:

```python
LOAD_TEXTURES = True
TEXTURE_PATH = r"C:\path\to\your\textures"
```

Textures are matched by material name + extension (`.png`, `.jpg`, etc.).

### Unity Mesh (`.mesh` / `.asset`) requirements

- Read/Write can be enabled or disabled. The bridge uses Unity's editor-only MeshData API for non-readable meshes without changing their importer setting.
- For `.asset` files, Blender Bridge activates only when the selected object is a `Mesh`; other `.asset` types keep Unity's normal behavior.
- Double-clicking a Mesh writes a temporary `Library/BlenderBridge/*.bridge-mesh` interchange file, opens it in Blender, and on Ctrl+S writes geometry back into that exact Mesh object.
- Unity Y-up coordinates are rotated into Blender Z-up on import. The inverse conversion is applied on save, so the Unity asset keeps its original orientation.
- Unity CompressedMesh YAML is never parsed by Blender; Unity decompresses via the Mesh API.
- When a face's normal is flipped in Blender, unchanged vertices keep their original Unity normals; only the flipped face's shared vertices are split so adjacent faces keep their previous shading.

### Advanced (environment variables)


| Variable                          | Purpose                                             |
| --------------------------------- | --------------------------------------------------- |
| `BRIDGE_BLENDER_PORT`             | TCP port for hot reuse (default `35971`)            |
| `BRIDGE_BETTER_FBX_MODULE`        | Better FBX addon folder name (default `better_fbx`) |
| `BRIDGE_FORCE_BUILTIN_FBX`        | Force built-in FBX import                           |
| `BRIDGE_FORCE_BUILTIN_FBX_EXPORT` | Force built-in FBX export                           |
| `BRIDGE_EXPORT_FBX_AXIS`          | Better FBX export axis (`MayaZUp`, `Unity`, etc.)   |
| `BLENDER_BRIDGE_PROFILE`          | Enable import timing logs                           |


## How it works

```
Unity double-click
    │
    ├─ Blender already listening on localhost:35971?
    │       └─ Yes → TCP IMPORT → load model + focus window
    │
    └─ No → launch Blender with blender-bridge-injector.py
                └─ script registers Ctrl+S, starts TCP server for reuse
```

## Development tools

`Tools/BlenderBridgeProfile/` contains PowerShell/Python scripts for batch testing, TCP flow checks, and import profiling. These are for development only and are not required for normal use.

## Credits

Based on work by [FleshMobProductions](https://gist.github.com/FleshMobProductions/f598096b705f6a9c96beb58e284303f1). Extended with hot reuse, Unity meta sync, Better FBX integration, transform baseline restore, and profiling tools.

## License

MIT

---

# Blender Bridge（中文）

在 Unity 中双击 `.FBX`、`.OBJ`、`.DAE`、Unity Mesh（`.mesh` / `.asset`）资产即可用 Blender 打开编辑；保存时直接写回 Unity 项目里的原文件，而不是存成 `.blend`。Blender 中的 **Ctrl+S** 已被桥接脚本接管。

**版本：** 0.1.18 · **Unity：** 2022.3+ · **平台：** Windows

## 安装

1. 打开 Unity，进入 **Window → Package Manager**（窗口 → 包管理器）
2. 点击左上角 **+** 按钮
3. 选择 **Add package from git URL**（从 Git URL 添加包）
4. 填入：
  ```
   https://github.com/huiyuanzhou/blender-bridge-for-unity.git
  ```
5. 完成。记得配置 Blender 路径（见下方 [配置说明](#配置说明)）。

## 快速上手

1. 在 Unity 的 **Edit > Project Settings > Blender Bridge** 中设置 Blender 可执行文件路径（见 [配置说明](#配置说明)）。
2. 资产往返流程：在 Unity **Project** 窗口双击 `.fbx`、`.obj`、`.dae`、`.mesh` 或 Mesh 类型的 `.asset`，在 Blender 中编辑后按 **Ctrl+S** 或使用 **File → Export → … (back to original Unity asset)**。
3. 场景层级流程：安装 Unity FBX Exporter，在 Unity **Hierarchy** 中选中根 GameObject，然后按 **Shift+F9**。也可以使用 **GameObject → Blender Bridge → Open Hierarchy in Blender**。在预制体编辑模式下，也可以选中预制体根物体或任意子物体，导出该物体及其后代。
4. 在 Blender 中编辑导出的层级。该流程会在 `Library/BlenderBridge/Hierarchy` 下打开临时 FBX；保存只会更新这个临时文件，不会修改 Unity 场景。

## 功能特性

- **双击编辑** — 从 Unity 工程窗口直接打开支持的 3D 资产
- **Hierarchy 层级导入** — 将选中的场景 GameObject 及其全部子物体通过临时 FBX 打开到 Blender（在 Blender 保存的是临时 FBX，不会回写 Unity 场景）
- **Metallicmap 传递** — 将 Unity 材质实际引用的 `_MetallicGlossMap` 传入 Blender，支持子物体、隐藏物体和材质覆盖。RGBA 数据使用 Non-Color / Channel Packed；项目 Chicken RGB 遮罩和 Unity Standard/URP 的 R 金属度、A 光滑度有对应的节点连接。未知 Shader 保留原贴图并提示，不猜测通道含义。
- **材质染色同步** — 传递 `_BaseColor`（或旧版 `_Color`）和实际底色贴图，包含 Renderer 和材质槽 PropertyBlock 的颜色覆盖，并按 Unity 工程的 Gamma/Linear 色彩空间重建相乘。BrickAtlas 1.6.0 将各材质 RGB 染色烘焙进颜色图集，输出材质保持白色，避免重复染色。自定义 Shader 混层、顶点色、灯光和透明度效果不在本次 RGB 染色同步范围内。
- **Unity Mesh（.mesh / .asset）** — 通过 `Library/BlenderBridge/` 下的 JSON 中转文件往返，也支持未开启 Read/Write 的 Mesh
- **坐标轴一致** — Unity Mesh 在 Blender 中按 Z 轴朝上显示，保存时自动转换回 Unity 的 Y 轴朝上
- **热复用** — Blender 已在运行时，再次双击会导入到同一窗口，不会重复启动新实例
- **自动置前** — 热复用导入时，Blender 窗口会自动弹到最前面
- **资产保存回 Unity** — Ctrl+S 和导出菜单会把编辑后的工程资产写回原路径
- **格式保持不变** — 往返编辑保持原格式（FBX / OBJ / DAE / Mesh）
- **读取 Unity 导入设置** — 从 `.meta` 读取法线、平滑角度、轴向等，提升往返一致性
- **Better FBX 支持** — 已安装 [Better FBX Importer & Exporter](https://blendermarket.com/products/better-fbx-importer-exporter) 时优先使用；否则回退到 Blender 内置 FBX 导入/导出
- **变换保持** — 导出前恢复物体变换，并烘焙静态 FBX 的几何枢轴，避免 Unity 根节点产生旋转和位移
- **视口自动聚焦** — 导入后自动缩放到模型
- **默认面选择模式** — 进入网格编辑时默认为面选择
- **无启动闪屏** — 打开 Blender 时不显示 Splash
- **可选纹理加载** — 可从指定文件夹自动匹配贴图（默认关闭）

## 环境要求


| 要求                | 说明                                        |
| ----------------- | ----------------------------------------- |
| **Windows**       | 编辑器集成依赖 Windows 进程与窗口 API                 |
| **Blender 5.x**   | 默认路径为 Blender 5.1；其他版本可在 Project Settings 中选择 |
| **Unity FBX Exporter** | 使用 Hierarchy 层级导入命令时需要；插件运行时查找该包，资产双击流程不强制要求 |
| **Better FBX 插件** | 强烈建议安装（ASCII FBX 与法线一致性尤其需要）；未安装时使用内置 FBX |


## 配置说明

项目级选项位于 **Edit > Project Settings > Blender Bridge**，其余高级选项见下文。

### Blender 可执行文件路径

在 Unity 中打开 **Edit > Project Settings > Blender Bridge**，选择 Blender 可执行文件。该设置会按项目保存在 `ProjectSettings/BlenderBridgeSettings.asset`。

常见路径：

- 官方安装：`C:\Program Files\Blender Foundation\Blender X.X\blender.exe`
- Steam 版：`C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe`

### 保存后保持 Blender 打开

Ctrl+S 和 File → Export 菜单都会将模型写回 Unity，并保持 Blender 打开，保存不会自动退出。Bridge 会话中的 Ctrl+S 用于导出原模型；需要保留独立的 `.blend` 工作文件时，请使用“另存为”。

### 纹理加载

在 `Editor/blender-bridge-injector.py` 中：

```python
LOAD_TEXTURES = True
TEXTURE_PATH = r"C:\path\to\your\textures"
```

贴图按 **材质名 + 扩展名**（`.png`、`.jpg` 等）匹配。

### Unity Mesh（`.mesh` / `.asset`）要求

- 无论是否开启 **Read/Write Enabled** 均可处理；未开启时使用 Unity 编辑器专用 MeshData API，不会修改原导入设置。
- 对于 `.asset` 文件，仅当所选对象本身是 `Mesh` 时才由 Blender Bridge 接管，其他 `.asset` 类型保持 Unity 原有行为。
- 双击 Mesh 时，会在 `Library/BlenderBridge/` 生成 JSON 中转文件 `*.bridge-mesh` 并在 Blender 中打开；Ctrl+S 后把几何精确写回该 Mesh 对象。
- 导入时会把 Unity Y-up 坐标转换为 Blender Z-up；保存时执行逆转换，因此 Unity 资产朝向保持不变。
- Blender 不直接解析 Unity CompressedMesh YAML，而是由 Unity Mesh API 解压后再中转。
- 在 Blender 中翻转某个面的法线时，未改动的顶点会保留原有 Unity 法线；仅被翻转面共用的顶点会被拆分，从而让相邻面的原有光照保持不变。

### 高级选项（环境变量）

在 Blender 进程上设置，用于调试或覆盖默认行为：


| 变量                                | 用途                                   |
| --------------------------------- | ------------------------------------ |
| `BRIDGE_BLENDER_PORT`             | 热复用 TCP 端口（默认 `35971`）               |
| `BRIDGE_BETTER_FBX_MODULE`        | Better FBX 插件文件夹名（默认 `better_fbx`）   |
| `BRIDGE_FORCE_BUILTIN_FBX`        | 强制使用内置 FBX 导入                        |
| `BRIDGE_FORCE_BUILTIN_FBX_EXPORT` | 强制使用内置 FBX 导出                        |
| `BRIDGE_EXPORT_FBX_AXIS`          | Better FBX 导出轴向（`MayaZUp`、`Unity` 等） |
| `BLENDER_BRIDGE_PROFILE`          | 开启导入耗时日志                             |


## 工作原理

```
Unity 双击资产
    │
    ├─ Blender 是否已在 localhost:35971 监听？
    │       └─ 是 → TCP 发送 IMPORT → 加载模型并置前窗口
    │
    └─ 否 → 启动 Blender 并执行 blender-bridge-injector.py
                └─ 注册 Ctrl+S、启动 TCP 服务供后续热复用
```

## 开发工具

`Tools/BlenderBridgeProfile/` 目录下有 PowerShell / Python 脚本，用于批量测试、TCP 流程检查和导入性能分析。仅供开发调试，日常使用无需关心。

## 致谢

基于 [FleshMobProductions](https://gist.github.com/FleshMobProductions/f598096b705f6a9c96beb58e284303f1) 的原始脚本。本分支扩展了热复用、Unity meta 同步、Better FBX 集成、变换基线恢复与性能分析工具。

## 许可证

MIT
