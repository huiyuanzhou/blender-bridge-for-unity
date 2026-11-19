"""Lossless Unity packed-map nodes shared with Brick Atlas (Blender 5.x)."""
import math
import bpy

ENCODINGS = {'chicken-rgb-v1', 'unity-r-a-v1'}


def _build_group(encoding):
    tree = bpy.data.node_groups.new('Unity Metallicmap ' + encoding, 'ShaderNodeTree')
    for name, kind in (('Color', 'NodeSocketColor'), ('Alpha', 'NodeSocketFloat'),
                       ('Metallic Scale', 'NodeSocketFloat'), ('Smoothness', 'NodeSocketFloat')):
        tree.interface.new_socket(name=name, in_out='INPUT', socket_type=kind)
    for name in ('Metallic', 'Roughness'):
        tree.interface.new_socket(name=name, in_out='OUTPUT', socket_type='NodeSocketFloat')
    nodes, links = tree.nodes, tree.links
    incoming = nodes.new('NodeGroupInput'); incoming.name = 'Input'
    outgoing = nodes.new('NodeGroupOutput'); outgoing.name = 'Output'
    separate = nodes.new('ShaderNodeSeparateColor'); separate.name = 'Channels'; separate.mode = 'RGB'
    links.new(incoming.outputs['Color'], separate.inputs['Color'])
    def math_node(name, operation, first, second=None):
        node = nodes.new('ShaderNodeMath'); node.name = name; node.operation = operation
        if isinstance(first, (float, int)): node.inputs[0].default_value = first
        else: links.new(first, node.inputs[0])
        if second is not None:
            if isinstance(second, (float, int)): node.inputs[1].default_value = second
            else: links.new(second, node.inputs[1])
        return node
    metal = math_node('Metallic', 'MULTIPLY', separate.outputs['Red'], incoming.outputs['Metallic Scale'])
    metal.use_clamp = True
    links.new(metal.outputs[0], outgoing.inputs['Metallic'])
    if encoding == 'chicken-rgb-v1':
        inverse = math_node('Inverse B', 'SUBTRACT', 1.0, separate.outputs['Blue'])
        source = inverse.outputs[0]
    else:
        source = incoming.outputs['Alpha']
    smooth = math_node('Smoothness', 'MULTIPLY', source, incoming.outputs['Smoothness'])
    smooth.use_clamp = True
    rough = math_node('Roughness', 'SUBTRACT', 1.0, smooth.outputs[0])
    links.new(rough.outputs[0], outgoing.inputs['Roughness'])
    return tree


def _signature(tree):
    nodes = []
    for node in tree.nodes:
        defaults = tuple((i, round(float(socket.default_value), 7)) for i, socket in enumerate(node.inputs)
                         if not socket.is_linked and hasattr(socket, 'default_value')
                         and isinstance(socket.default_value, (float, int)))
        nodes.append((node.name, node.bl_idname, getattr(node, 'operation', None),
                      getattr(node, 'mode', None), getattr(node, 'use_clamp', None), node.mute, defaults))
    links = [(l.from_node.name, list(l.from_node.outputs).index(l.from_socket),
              l.to_node.name, list(l.to_node.inputs).index(l.to_socket)) for l in tree.links]
    interface = [(s.name, s.in_out, s.socket_type) for s in tree.interface.items_tree if s.item_type == 'SOCKET']
    return sorted(nodes), sorted(links), interface


def apply_packed_map(material, image, encoding='chicken-rgb-v1', metallic_scale=1.0, smoothness=0.5, uv_name=''):
    if encoding not in ENCODINGS:
        raise ValueError('Unsupported Metallicmap encoding: ' + encoding)
    for value in (metallic_scale, smoothness):
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('Metallicmap factors must be finite values in 0..1')
    if encoding == 'unity-r-a-v1' and metallic_scale != 1:
        raise ValueError('Unity metallic texture uses R directly; Metallic Scale must be 1')
    material.use_nodes = True
    shader = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if shader is None:
        raise ValueError('Metallicmap requires a Principled BSDF')
    nodes, links = material.node_tree.nodes, material.node_tree.links
    # Reuse the existing metallic image node when converting a direct legacy connection.
    previous = shader.inputs['Metallic'].links
    texture = previous[0].from_node if previous and previous[0].from_node.type == 'TEX_IMAGE' and previous[0].from_node.image == image else None
    if texture is None:
        texture = nodes.new('ShaderNodeTexImage')
    texture.image = image
    image.colorspace_settings.name = 'Non-Color'
    image.alpha_mode = 'CHANNEL_PACKED'
    texture.label = 'Unity Metallicmap · RGBA'
    if uv_name:
        uv = nodes.new('ShaderNodeUVMap'); uv.uv_map = uv_name
        links.new(uv.outputs['UV'], texture.inputs['Vector'])
    group = nodes.new('ShaderNodeGroup')
    group.node_tree = _build_group(encoding)
    group['unity_bridge_packed_map'] = encoding
    group.label = 'Unity Metallicmap · ' + encoding
    group.inputs['Metallic Scale'].default_value = metallic_scale
    group.inputs['Smoothness'].default_value = smoothness
    links.new(texture.outputs['Color'], group.inputs['Color'])
    links.new(texture.outputs['Alpha'], group.inputs['Alpha'])
    links.new(group.outputs['Metallic'], shader.inputs['Metallic'])
    links.new(group.outputs['Roughness'], shader.inputs['Roughness'])
    return group


def inspect_packed_map(material, shader=None):
    """Validate the actual graph, never trusting a marker as proof of its math."""
    if not material.use_nodes or not material.node_tree:
        return None
    if shader is None:
        shader = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if shader is None:
        return None
    link = shader.inputs['Metallic'].links
    if not link or 'unity_bridge_packed_map' not in link[0].from_node:
        return None
    group = link[0].from_node
    encoding = group.get('unity_bridge_packed_map')
    if group.bl_idname != 'ShaderNodeGroup' or encoding not in ENCODINGS or group.mute:
        raise ValueError('Invalid Unity Metallicmap group')
    expected = _build_group(encoding)
    try:
        if _signature(expected) != _signature(group.node_tree):
            raise ValueError('Unity Metallicmap group was edited; restore the supported graph')
    finally:
        bpy.data.node_groups.remove(expected)
    required = []
    texture = None
    for output, target in (('Metallic', 'Metallic'), ('Roughness', 'Roughness')):
        links = shader.inputs[target].links
        if len(links) != 1 or links[0].from_node != group or links[0].from_socket.name != output:
            raise ValueError('Unity Metallicmap must drive both Metallic and Roughness')
        required.append(links[0])
    for name in ('Color', 'Alpha'):
        links = group.inputs[name].links
        if len(links) != 1 or links[0].from_node.type != 'TEX_IMAGE' or links[0].from_socket.name != name:
            raise ValueError('Unity Metallicmap requires Color and Alpha from one image')
        if texture is not None and texture != links[0].from_node:
            raise ValueError('Unity Metallicmap Color and Alpha images disagree')
        texture = links[0].from_node
        required.append(links[0])
    values = {}
    for socket, key in (('Metallic Scale', 'metallic_scale'), ('Smoothness', 'smoothness')):
        inp = group.inputs[socket]
        value = inp.default_value
        if inp.is_linked or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('Unity Metallicmap factors must be constant values in 0..1')
        values[key] = value
    if encoding == 'unity-r-a-v1' and abs(values['metallic_scale'] - 1) > 1e-6:
        raise ValueError('Unity metallic texture uses R directly')
    if texture.image is None or texture.image.colorspace_settings.name != 'Non-Color' or texture.image.alpha_mode != 'CHANNEL_PACKED':
        raise ValueError('Unity Metallicmap requires Non-Color and Channel Packed image data')
    return dict(image=texture.image, image_node=texture, group=group, encoding=encoding,
                links=required, **values)
