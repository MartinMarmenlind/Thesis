import bpy
import os
import math
import random
import bmesh
from mathutils.bvhtree import BVHTree

# ---------------- SETTINGS ----------------
input_folder = r"C:\Users\martin.marmenlind\Desktop\Thesis\3D_Models\Testing\Input"
output_folder = r"C:\Users\martin.marmenlind\Desktop\Thesis\3D_Models\Testing\Output"
log_file_folder = r"C:\Users\martin.marmenlind\Desktop\Thesis\3D_Models\Testing\Log"
samples_per_face = 3
decimate_ratio = 0.5

random.seed(42) # random seed for sampling points

# make output and log dir if missing
os.makedirs(output_folder, exist_ok=True)
os.makedirs(log_file_folder, exist_ok=True)

# Get vertex-, edge- and face count of mesh
def get_mesh_stats(objects):
    v = e = f = 0
    for obj in objects:
        if obj.type == 'MESH':
            m = obj.data
            v += len(m.vertices)
            e += len(m.edges)
            f += len(m.polygons)
    return v, e, f


# join multiple meshes
def join_objects(objs):
    mesh_objs = [o for o in objs if o.type == 'MESH']
    if not mesh_objs:
        return None

    if len(mesh_objs) == 1:
        return mesh_objs[0]

    bpy.ops.object.select_all(action='DESELECT')
    for o in mesh_objs:
        o.select_set(True)

    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()

    return bpy.context.active_object


# sample points on faces and find distances between scr and tgt
def sample_and_measure(src_obj, tgt_obj, samples_per_face, depsgraph):
    tgt_eval = tgt_obj.evaluated_get(depsgraph)
    tgt_mesh = tgt_eval.to_mesh()

    bm_tgt = bmesh.new()
    bm_tgt.from_mesh(tgt_mesh)
    bm_tgt.transform(tgt_obj.matrix_world)

    bvh = BVHTree.FromBMesh(bm_tgt)

    mesh = src_obj.data
    mesh.calc_loop_triangles()

    samples = []
    distances = []
    face_indices = []

    for tri in mesh.loop_triangles:
        poly_index = tri.polygon_index

        v0 = mesh.vertices[tri.vertices[0]].co
        v1 = mesh.vertices[tri.vertices[1]].co
        v2 = mesh.vertices[tri.vertices[2]].co

        for _ in range(samples_per_face):
            r1 = random.random()
            r2 = random.random()

            sqrt_r1 = r1 ** 0.5
            u = 1 - sqrt_r1
            v = r2 * sqrt_r1
            w = 1 - u - v

            local_p = u*v0 + v*v1 + w*v2
            world_p = src_obj.matrix_world @ local_p

            _, _, _, dist = bvh.find_nearest(world_p)
            if dist is None:
                dist = 0.0

            samples.append(world_p)
            distances.append(dist)
            face_indices.append(poly_index)

    bm_tgt.free()
    tgt_eval.to_mesh_clear()

    return samples, distances, face_indices


# Compute hausdorff distance and RMS distance
def compute_metrics(distances):
    hausdorff = max(distances)
    rmsd = math.sqrt(sum(d*d for d in distances) / len(distances))
    return hausdorff, rmsd


# Sampled points on faces to face heatmap 
def sample_to_face_heatmap(obj, face_indices, distances):
    num_faces = len(obj.data.polygons)

    sums = [0.0] * num_faces
    counts = [0] * num_faces

    for f_idx, d in zip(face_indices, distances):
        sums[f_idx] += d
        counts[f_idx] += 1

    return [
        (sums[i] / counts[i]) if counts[i] > 0 else 0.0
        for i in range(num_faces)
    ]


# Apple face heatmap to color layer data
def apply_face_heatmap(obj, face_distances):
    mesh = obj.data

    min_d = min(face_distances)
    max_d = max(face_distances)
    if max_d == min_d:
        max_d += 1e-8

    color_layer = mesh.color_attributes.new(
        name="FaceErrorHeatmap",
        type='FLOAT_COLOR',
        domain='FACE'
    )

    for i, d in enumerate(face_distances):
        t = (d - min_d) / (max_d - min_d)
        color_layer.data[i].color = (t, 0.0, 1.0 - t, 1.0)


# Create face heatmap material
def create_material(obj):
    mat = bpy.data.materials.new(name="Heatmap")
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    vc = nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "FaceErrorHeatmap"

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    out = nodes.new("ShaderNodeOutputMaterial")

    links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)


# Main loop
for file_name in os.listdir(input_folder):

    if not file_name.lower().endswith(".obj"):
        continue

    file_path = os.path.join(input_folder, file_name)
    
    #log_file_path = os.path.join(log_file_folder, (file_name + f"_Log.txt"))
    log_file_path = os.path.join(log_file_folder, (file_name[:-4] + f"_Log_Dec.txt"))
    
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    # Clean scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Import
    bpy.ops.wm.obj_import(filepath=file_path)
    imported = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not imported:
        continue

    original = join_objects(imported)
    if original is None:
        continue

    # Duplicate reference
    bpy.ops.object.select_all(action='DESELECT')
    original.select_set(True)
    bpy.context.view_layer.objects.active = original
    bpy.ops.object.duplicate()
    reference = bpy.context.active_object

    # Stats before
    v1, e1, f1 = get_mesh_stats([reference])

    # Perform simplification through decimate modifier (collapse mode)
    bpy.ops.object.select_all(action='DESELECT')
    original.select_set(True)
    bpy.context.view_layer.objects.active = original

    dec_mod = original.modifiers.new(name="Decimate", type='DECIMATE')
    dec_mod.decimate_type = 'COLLAPSE'
    dec_mod.ratio = decimate_ratio

    bpy.ops.object.modifier_apply(modifier=dec_mod.name)

    # Triangulate dissolved mesh_objs
    tri_mod = original.modifiers.new(name="Triangulate", type='TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=tri_mod.name)

    # Stats after
    v2, e2, f2 = get_mesh_stats([original])

    # Sampling + metrics
    depsgraph = bpy.context.evaluated_depsgraph_get()

    samples, distances, face_indices = sample_and_measure(
        original,
        reference,
        samples_per_face,
        depsgraph
    )

    hd, rmsd_value = compute_metrics(distances)

    # Heatmap
    face_distances = sample_to_face_heatmap(
        original,
        face_indices,
        distances
    )

    apply_face_heatmap(original, face_distances)
    create_material(original)

    # Export
    export_name = os.path.splitext(file_name)[0] + "_Dec.obj"
    export_path = os.path.join(output_folder, export_name)

    bpy.ops.object.select_all(action='DESELECT')
    original.select_set(True)

    bpy.ops.wm.obj_export(
        filepath=export_path,
        export_selected_objects=True
    )

    # write obtained data to log file
    with open(log_file_path, "a") as f:
        f.write(
            f"Model\tVerts\tEdges\tFaces\tFile size (bytes)\n"
            f"{file_name}\t{v1}\t{e1}\t{f1}\t{os.path.getsize(file_path)}\n"
            f"{export_name}\t{v2}\t{e2}\t{f2}\t{os.path.getsize(export_path)}\n\n"
            
            f"Mesh simplification:\n"
            f"Removed {v1-v2} vertices, simplified vertex count is {(100*(v2/v1)):.6f}% of origianl\n"
            f"Removed {e1-e2} edges, simplified edge count is {(100*(e2/e1)):.6f}% of origianl\n"
            f"Removed {f1-f2} faces, simplified face count is {(100*(f2/f1)):.6f}% of origianl\n\n"
            
            f"Hausdorff distance = {hd:.6f}\n"
            f"Root Mean Square Distance = {rmsd_value:.6f}\n\n"
        )
        
        f.write(f"Raw data of sampled points on faces and distances:\n")
        f.write("face index\tsample_x\tsample_y\tsample_z\tdistance\n")
        for i, s, d in zip(face_indices, samples, distances):
            f.write(f"{i}\t{s.x:.6f}\t{s.y:.6f}\t{s.z:.6f}\t{d:.6f}\n")

    print(f"Processed: {file_name}")