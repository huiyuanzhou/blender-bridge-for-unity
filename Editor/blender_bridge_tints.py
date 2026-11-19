"""Unity base-color RGB tint graphs shared with Blender Bridge (Blender 5.x)."""
import math
import bpy

MARKER = 'unity_bridge_base_tint_v1'
COLOR_SPACES = {'linear', 'gamma'}


def _build_group(color_space):
    tree = bpy.data.node_groups.new('Unity Base Color Tint ' + color_space, 'ShaderNodeTree')
    tree.interface.new_socket(name='Color', in_out='INPUT', socket_type='NodeSocketColor')
    tree.interface.new_socket(name='Tint', in_out='INPUT', socket_type='NodeSocketColor')
    tree.interface.new_socket(name='Color', in_out='OUTPUT', socket_type='NodeSocketColor')
    nodes, links = tree.nodes, tree.links
    incoming = nodes.new('NodeGroupInput'); incoming.name = 'Input'
    outgoing = nodes.new('NodeGroupOutput'); outgoing.name = 'Output'
    texture = nodes.new('ShaderNodeSeparateColor'); texture.name = 'Texture RGB'; texture.mode = 'RGB'
    tint = nodes.new('ShaderNodeSeparateColor'); tint.name = 'Tint RGB'; tint.mode = 'RGB'
    combine = nodes.new('ShaderNodeCombineColor'); combine.name = 'Result RGB'; combine.mode = 'RGB'
    links.new(incoming.outputs['Color'], texture.inputs['Color'])
    links.new(incoming.outputs['Tint'], tint.inputs['Color'])

    def op(name, operation, *values):
        node = nodes.new('ShaderNodeMath'); node.name = name; node.operation = operation
        for index, value in enumerate(values):
            if isinstance(value, (float, int)): node.inputs[index].default_value = value
            else: links.new(value, node.inputs[index])
        return node.outputs[0]

    def transfer(value, name, encode):
        if encode:
            low = op(name + ' low', 'MULTIPLY', value, 12.92)
            power = op(name + ' power', 'POWER', value, 1 / 2.4)
            high = op(name + ' high', 'MULTIPLY_ADD', power, 1.055, -0.055)
            choose_low = op(name + ' threshold', 'LESS_THAN', value, 0.0031308)
        else:
            low = op(name + ' low', 'DIVIDE', value, 12.92)
            shifted = op(name + ' shift', 'ADD', value, 0.055)
            scaled = op(name + ' scale', 'DIVIDE', shifted, 1.055)
            high = op(name + ' high', 'POWER', scaled, 2.4)
            choose_low = op(name + ' threshold', 'LESS_THAN', value, 0.04045)
        choose_high = op(name + ' inverse', 'SUBTRACT', 1.0, choose_low)
        a = op(name + ' selected low', 'MULTIPLY', low, choose_low)
        b = op(name + ' selected high', 'MULTIPLY', high, choose_high)
        return op(name + ' result', 'ADD', a, b)

    for channel in ('Red', 'Green', 'Blue'):
        value = texture.outputs[channel]
        if color_space == 'gamma':
            value = transfer(value, channel + ' Encode', True)
        value = op(channel + ' Tint', 'MULTIPLY', value, tint.outputs[channel])
        if color_space == 'gamma':
            value = transfer(value, channel + ' Decode', False)
        links.new(value, combine.inputs[channel])
    # This graph drives RGB Base Color only; image Alpha remains available separately.
    links.new(combine.outputs['Color'], outgoing.inputs['Color'])
    return tree


def _signature(tree):
    nodes = []
    for node in tree.nodes:
        defaults = []
        for index, socket in enumerate(node.inputs):
            if socket.is_linked or not hasattr(socket, 'default_value'):
                continue
            value = socket.default_value
            if isinstance(value, (float, int)): value = round(float(value), 7)
            else:
                try: value = tuple(round(float(v), 7) for v in value)
                except TypeError: value = str(value)
            defaults.append((index, value))
        nodes.append((node.name, node.bl_idname, getattr(node, 'operation', None),
                      getattr(node, 'mode', None), getattr(node, 'use_clamp', None), node.mute, tuple(defaults)))
    links = [(l.from_node.name, list(l.from_node.outputs).index(l.from_socket),
              l.to_node.name, list(l.to_node.inputs).index(l.to_socket)) for l in tree.links]
    interface = [(s.name, s.in_out, s.socket_type) for s in tree.interface.items_tree if s.item_type == 'SOCKET']
    return sorted(nodes), sorted(links), interface


def _validate_tint(tint):
    tint = tuple(tint)
    if len(tint) != 4 or any(not math.isfinite(v) or not 0 <= v <= 1 for v in tint):
        raise ValueError('Base color tint must contain four finite values in 0..1')
    return tint


def apply_base_color_tint(material, image, tint=(1, 1, 1, 1), color_space='linear', uv_name=''):
    """Tint an sRGB image; linear mode expects a tint already converted to linear."""
    tint = _validate_tint(tint)
    if color_space not in COLOR_SPACES:
        raise ValueError('Unsupported base color tint space: ' + color_space)
    if image.colorspace_settings.name != 'sRGB':
        raise ValueError('Base color tint requires an sRGB image')
    material.use_nodes = True
    shader = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if shader is None:
        raise ValueError('Base color tint requires a Principled BSDF')
    nodes, links = material.node_tree.nodes, material.node_tree.links
    previous = inspect_base_color_tint(material, shader)
    old_tree = None
    if previous:
        texture = previous['image_node']
        old_tree = previous['group'].node_tree
        nodes.remove(previous['group'])
    else:
        base_links = shader.inputs['Base Color'].links
        texture = base_links[0].from_node if base_links and base_links[0].from_node.type == 'TEX_IMAGE' else None
    if texture is None:
        texture = nodes.new('ShaderNodeTexImage')
    texture.image = image
    if uv_name:
        uv = nodes.new('ShaderNodeUVMap'); uv.uv_map = uv_name
        links.new(uv.outputs['UV'], texture.inputs['Vector'])
    group = nodes.new('ShaderNodeGroup')
    group.node_tree = _build_group(color_space)
    group[MARKER] = color_space
    group.label = 'Unity Base Color Tint · ' + color_space
    group.inputs['Tint'].default_value = tint
    links.new(texture.outputs['Color'], group.inputs['Color'])
    links.new(group.outputs['Color'], shader.inputs['Base Color'])
    if old_tree and old_tree.users == 0:
        bpy.data.node_groups.remove(old_tree)
    return group


def inspect_base_color_tint(material, shader=None):
    if not material.use_nodes or not material.node_tree:
        return None
    if shader is None:
        shader = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if shader is None:
        return None
    links = shader.inputs['Base Color'].links
    if not links or MARKER not in links[0].from_node:
        return None
    group = links[0].from_node
    color_space = group.get(MARKER)
    if group.bl_idname != 'ShaderNodeGroup' or color_space not in COLOR_SPACES or group.mute:
        raise ValueError('Invalid Unity base color tint group')
    expected = _build_group(color_space)
    try:
        if _signature(group.node_tree) != _signature(expected):
            raise ValueError('Unity base color tint group was edited; restore the supported graph')
    finally:
        bpy.data.node_groups.remove(expected)
    if len(links) != 1 or links[0].from_socket.name != 'Color':
        raise ValueError('Unity base color tint must drive Base Color')
    source = group.inputs['Color'].links
    if len(source) != 1 or source[0].from_node.type != 'TEX_IMAGE' or source[0].from_socket.name != 'Color':
        raise ValueError('Unity base color tint requires a direct image Color input')
    if group.inputs['Tint'].is_linked:
        raise ValueError('Unity base color tint must be a constant color')
    texture = source[0].from_node
    if texture.image is None or texture.image.colorspace_settings.name != 'sRGB':
        raise ValueError('Unity base color tint requires an sRGB image')
    return dict(image=texture.image, image_node=texture, group=group, links=[links[0], source[0]],
                tint=_validate_tint(group.inputs['Tint'].default_value), color_space=color_space)
