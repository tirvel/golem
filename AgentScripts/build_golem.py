# Rebuilds Assets/Golem (golem.fbx + baked textures) from golem.glb.
# Replays the Blender steps the agent ran during the original session, in order,
# without the exploration, camera and screenshot calls.
# The agent first tried a "planar region" retopology (session calls 15-37) and dropped it;
# only the steps that shaped the published asset are kept here.
#
# Usage, from the repository root (Blender 5.2):
#   blender --background --factory-startup --python AgentScripts/build_golem.py
#   blender --background --factory-startup --python AgentScripts/build_golem.py -- <output dir>
# Default output dir: Assets/Golem.

import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_point_line

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB = os.path.join(ROOT, "golem.glb")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(args[0]) if args else os.path.join(ROOT, "Assets", "Golem")
TARGET_TRIS = 18000

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def select_only(active, *others):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in (active, *others):
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


# 1. Import the Meshy model (139k triangles).
bpy.ops.import_scene.gltf(filepath=GLB)
src = next(o for o in sc.objects if o.type == 'MESH')

# 2. Low poly copy: merge duplicate vertices, then collapse to 18k triangles.
g = src.copy()
g.data = src.data.copy()
g.name = g.data.name = "Golem"
sc.collection.objects.link(g)
me = g.data
if "custom_normal" in me.attributes:
    me.attributes.remove(me.attributes["custom_normal"])
for a in list(me.color_attributes):
    me.color_attributes.remove(a)
bm = bmesh.new()
bm.from_mesh(me)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(me)
bm.free()
dec = g.modifiers.new("Dec", "DECIMATE")
dec.decimate_type = 'COLLAPSE'
dec.ratio = TARGET_TRIS / len(src.data.polygons)
dec.use_collapse_triangulate = True
select_only(g)
bpy.ops.object.modifier_apply(modifier="Dec")
me.shade_smooth()

# 3. New UVs.
while me.uv_layers:
    me.uv_layers.remove(me.uv_layers[0])
me.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
bpy.ops.object.mode_set(mode='OBJECT')

# 4. Material, then bake colour and tangent normal map from the original.
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 4
mat = bpy.data.materials.new("Golem_MAT")
mat.use_nodes = True
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
col = bpy.data.images.new("Golem_BaseColor", 2048, 2048, alpha=False)
col.colorspace_settings.name = 'sRGB'
nrm = bpy.data.images.new("Golem_Normal", 2048, 2048, alpha=False, float_buffer=False)
nrm.colorspace_settings.name = 'Non-Color'
tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = col; tc.name = "TexColor"
tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = nrm; tn.name = "TexNormal"
nmap = nt.nodes.new("ShaderNodeNormalMap")
bsdf.inputs["Roughness"].default_value = 0.64
bsdf.inputs["Metallic"].default_value = 0.0
me.materials.clear()
me.materials.append(mat)

select_only(g, src)
bake = dict(use_selected_to_active=True, cage_extrusion=0.02, max_ray_distance=0.08, margin=16)
sc.render.bake.use_clear = True
nt.nodes.active = tc
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, **bake)
nt.nodes.active = tn
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', **bake)
nt.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(tn.outputs["Color"], nmap.inputs["Color"])
nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

# 5. Scale to 2 m, pivot between the feet soles, on the ground.
V = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3)
zmin = V[:, 2].min()
feet = V[V[:, 2] < zmin + 0.03]
cx = (feet[:, 0].min() + feet[:, 0].max()) / 2
cy = (feet[:, 1].min() + feet[:, 1].max()) / 2
me.transform(Matrix.Scale(2.0 / (V[:, 2].max() - zmin), 4) @ Matrix.Translation(Vector((-cx, -cy, -zmin))))
me.update()
g.matrix_world = Matrix.Identity(4)

# 6. Humanoid skeleton (19 bones, final positions after the agent's arm adjustments).
arm = bpy.data.armatures.new("GolemRig")
rig = bpy.data.objects.new("GolemRig", arm)
sc.collection.objects.link(rig)
select_only(rig)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.edit_bones


def bone(name, h, t, parent=None, conn=False):
    e = eb.new(name); e.head = Vector(h); e.tail = Vector(t)
    if parent:
        e.parent = eb[parent]; e.use_connect = conn


bone("Hips", (0, 0.06, 0.62), (0, 0.06, 0.80))
bone("Spine", (0, 0.06, 0.80), (0, 0.07, 1.05), "Hips", True)
bone("Chest", (0, 0.07, 1.05), (0, 0.08, 1.45), "Spine", True)
bone("Neck", (0, 0.08, 1.45), (0, 0.06, 1.58), "Chest", True)
bone("Head", (0, 0.06, 1.58), (0, 0.04, 1.98), "Neck", True)
for s, side in ((1, "Left"), (-1, "Right")):
    bone(side + "Shoulder", (s * 0.14, 0.09, 1.40), (s * 0.58, 0.12, 1.38), "Chest")
    bone(side + "UpperArm", (s * 0.64, 0.14, 1.22), (s * 0.72, 0.13, 1.05), side + "Shoulder")
    bone(side + "LowerArm", (s * 0.72, 0.13, 1.05), (s * 0.84, 0.06, 0.64), side + "UpperArm", True)
    bone(side + "Hand", (s * 0.84, 0.06, 0.64), (s * 0.86, 0.02, 0.26), side + "LowerArm", True)
    bone(side + "UpperLeg", (s * 0.24, 0.05, 0.60), (s * 0.30, 0.05, 0.36), "Hips")
    bone(side + "LowerLeg", (s * 0.30, 0.05, 0.36), (s * 0.31, 0.04, 0.13), side + "UpperLeg", True)
    bone(side + "Foot", (s * 0.31, 0.04, 0.13), (s * 0.31, -0.22, 0.04), side + "LowerLeg", True)
bpy.ops.armature.select_all(action='SELECT')
bpy.ops.armature.calculate_roll(type='GLOBAL_NEG_Y')
bpy.ops.object.mode_set(mode='OBJECT')

# Parent with automatic weights: sets the armature modifier; weights are replaced below.
select_only(rig, g)
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# 7. Skin weights.
names = [b.name for b in arm.bones]
idx = {nm: i for i, nm in enumerate(names)}
H = np.array([b.head_local[:] for b in arm.bones]); T = np.array([b.tail_local[:] for b in arm.bones])
V = np.array([v.co[:] for v in me.vertices]); n = len(V)
E = np.array([e.vertices[:] for e in me.edges])

# Moss and sprout patches (green or brown in the baked colour) follow one bone rigidly.
S = col.size[0]
px = np.array(col.pixels[:]).reshape(S, S, 4)
uv = np.empty(len(me.loops) * 2); me.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
lv = np.empty(len(me.loops), int); me.loops.foreach_get("vertex_index", lv)
c = px[np.clip((uv[:, 1] * S).astype(int), 0, S - 1), np.clip((uv[:, 0] * S).astype(int), 0, S - 1), :3]
vc = np.zeros((n, 3)); cnt = np.zeros(n); np.add.at(vc, lv, c); np.add.at(cnt, lv, 1); vc /= cnt[:, None]
r, gg, b = vc.T
mask = ((gg > r + 0.08) & (gg > b + 0.08)) | ((r > b + 0.08) & (r >= gg) & (gg > b)) | ((V[:, 0] > 0.42) & (V[:, 2] > 1.70))
nbr = [[] for _ in range(n)]
for a, bb in E:
    nbr[a].append(bb); nbr[bb].append(a)
lab = -np.ones(n, int); patches = []
for s0 in np.nonzero(mask)[0]:
    if lab[s0] >= 0:
        continue
    st = [s0]; lab[s0] = len(patches); mem = [s0]
    while st:
        x = st.pop()
        for o in nbr[x]:
            if mask[o] and lab[o] < 0:
                lab[o] = len(patches); st.append(o); mem.append(o)
    patches.append(mem)


def nearest_bone(p):
    best = None
    for b_ in arm.bones:
        h, t = b_.head_local, b_.tail_local
        _, f = intersect_point_line(p, h, t); f = min(max(f, 0), 1)
        d = (p - (h + (t - h) * f)).length
        if best is None or d < best[0]:
            best = (d, b_.name)
    return best[1]


rigid = {}
for m in patches:
    if len(m) >= 4:
        nm = nearest_bone(Vector(V[m].mean(0)))
        for i in m:
            rigid[int(i)] = nm

# Inverse distance to each bone, with zones that forbid implausible bones, two bones per vertex, smoothed.
d = np.zeros((n, len(names)))
for j in range(len(names)):
    ab = T[j] - H[j]; t = np.clip(((V - H[j]) @ ab) / (ab @ ab), 0, 1)
    d[:, j] = np.linalg.norm(V - (H[j] + t[:, None] * ab), axis=1)
ax = np.abs(V[:, 0]); z = V[:, 2]; BIG = 1e3
torso = (ax < 0.44) & (z > 0.62)
legs = (z < 0.56) & (ax < 0.52)
for nm in names:
    if any(k in nm for k in ("UpperArm", "LowerArm", "Hand", "UpperLeg", "LowerLeg", "Foot")):
        d[torso, idx[nm]] += BIG
    if not any(k in nm for k in ("UpperLeg", "LowerLeg", "Foot", "Hips")):
        d[legs, idx[nm]] += BIG
    if nm.startswith("Left"):
        d[V[:, 0] < -0.05, idx[nm]] += BIG
    if nm.startswith("Right"):
        d[V[:, 0] > 0.05, idx[nm]] += BIG
for s, side in ((1, "Left"), (-1, "Right")):
    rock = (s * V[:, 0] > 0.42) & (z > 1.18)  # shoulder rocks move with the shoulder only
    for nm in names:
        if nm != side + "Shoulder":
            d[rock, idx[nm]] += BIG
w = 1.0 / np.maximum(d, 1e-3) ** 6
order = np.argsort(-w, axis=1); W = np.zeros_like(w); rows = np.arange(n)[:, None]
W[rows, order[:, :2]] = w[rows, order[:, :2]]; W /= W.sum(1, keepdims=True)
for _ in range(3):
    acc = np.zeros_like(W); cnt = np.zeros(n)
    np.add.at(acc, E[:, 0], W[E[:, 1]]); np.add.at(acc, E[:, 1], W[E[:, 0]])
    np.add.at(cnt, E[:, 0], 1); np.add.at(cnt, E[:, 1], 1)
    W = 0.5 * W + 0.5 * acc / cnt[:, None]
W[W < 0.02] = 0; W /= W.sum(1, keepdims=True)

for vg in list(g.vertex_groups):
    g.vertex_groups.remove(vg)
for nm in names:
    g.vertex_groups.new(name=nm)
for j, nm in enumerate(names):
    vg = g.vertex_groups[nm]
    for i in np.nonzero(W[:, j] > 0)[0]:
        if int(i) not in rigid:
            vg.add([int(i)], float(W[i, j]), 'REPLACE')
for i, nm in rigid.items():
    g.vertex_groups[nm].add([i], 1.0, 'REPLACE')

# 8. Face +Y in Blender (Unity forward after export), then export.
select_only(rig, g)
rig.rotation_euler[2] += math.pi
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False, properties=False)

os.makedirs(os.path.join(OUT, "Textures"), exist_ok=True)
for im in (col, nrm):
    im.filepath_raw = os.path.join(OUT, "Textures", im.name + ".png")
    im.file_format = 'PNG'
    im.save()
select_only(rig, g)
bpy.ops.export_scene.fbx(
    filepath=os.path.join(OUT, "golem.fbx"), use_selection=True, object_types={'ARMATURE', 'MESH'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
    bake_space_transform=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
    use_armature_deform_only=True, bake_anim=False, use_tspace=True, mesh_smooth_type='OFF',
    use_mesh_modifiers=False, path_mode='RELATIVE')
print("golem: %d triangles, %d bones, %d rigid vertices -> %s" % (len(me.polygons), len(names), len(rigid), OUT))
