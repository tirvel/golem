using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class GolemSetup
{
    const string FbxPath = "Assets/Golem/golem.fbx";

    // Étape 8 : import Humanoid + rapport sur l'avatar.
    public static string ImportHumanoid()
    {
        AssetDatabase.Refresh();
        var imp = (ModelImporter)AssetImporter.GetAtPath(FbxPath);
        if (imp == null) return "FBX introuvable : " + FbxPath;
        imp.globalScale = 1f;
        imp.useFileScale = true;
        imp.bakeAxisConversion = true;
        imp.importNormals = ModelImporterNormals.Import;
        imp.importTangents = ModelImporterTangents.CalculateMikk;
        imp.importAnimation = false;
        imp.materialImportMode = ModelImporterMaterialImportMode.None;
        imp.animationType = ModelImporterAnimationType.Human;
        imp.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
        imp.SaveAndReimport();
        return Report();
    }

    // L'auto-mapping ignore Chest : on l'ajoute à la description humaine.
    public static string MapChest()
    {
        var imp = (ModelImporter)AssetImporter.GetAtPath(FbxPath);
        var hd = imp.humanDescription;
        if (!hd.human.Any(h => h.humanName == "Chest"))
        {
            var chest = new HumanBone { humanName = "Chest", boneName = "Chest" };
            chest.limit.useDefaultValues = true;
            hd.human = hd.human.Concat(new[] { chest }).ToArray();
            imp.humanDescription = hd;
            imp.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            imp.SaveAndReimport();
        }
        return Report();
    }

    public static string Report()
    {
        var sb = new StringBuilder();
        var imp = (ModelImporter)AssetImporter.GetAtPath(FbxPath);
        var assets = AssetDatabase.LoadAllAssetsAtPath(FbxPath);
        var avatar = assets.OfType<Avatar>().FirstOrDefault();
        sb.AppendLine("animationType=" + imp.animationType + " scaleFactor(file)=" + imp.fileScale + " bakeAxis=" + imp.bakeAxisConversion);
        sb.AppendLine("avatar=" + (avatar ? avatar.name : "null") + " isValid=" + (avatar && avatar.isValid) + " isHuman=" + (avatar && avatar.isHuman));
        var hd = imp.humanDescription;
        sb.AppendLine("human bones mapped: " + hd.human.Length);
        foreach (var hb in hd.human) sb.Append(hb.humanName + "->" + hb.boneName + "; ");
        sb.AppendLine();
        var mesh = assets.OfType<Mesh>().FirstOrDefault();
        if (mesh)
            sb.AppendLine("mesh " + mesh.name + " tris=" + mesh.triangles.Length / 3 + " verts=" + mesh.vertexCount + " bounds=" + mesh.bounds + " submeshes=" + mesh.subMeshCount);
        return sb.ToString();
    }

    // Mesures signées dans l'espace monde d'une instance temporaire.
    public static string Orientation()
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(FbxPath);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        try
        {
            var sb = new StringBuilder();
            var anim = go.GetComponent<Animator>();
            Transform B(HumanBodyBones b) => anim.GetBoneTransform(b);
            var hips = B(HumanBodyBones.Hips);
            sb.AppendLine("root rot=" + go.transform.rotation.eulerAngles + " scale=" + go.transform.lossyScale);
            foreach (var b in new[] { HumanBodyBones.Hips, HumanBodyBones.Head, HumanBodyBones.LeftHand, HumanBodyBones.RightHand,
                                      HumanBodyBones.LeftFoot, HumanBodyBones.RightFoot, HumanBodyBones.LeftToes })
            {
                var t = B(b);
                sb.AppendLine(b + " = " + (t ? t.position.ToString("F3") : "absent"));
            }
            // Orteil du pied gauche : enfant-feuille absent, on prend la direction pied -> pointe via le mesh
            var smr = go.GetComponentInChildren<SkinnedMeshRenderer>();
            var m = smr.sharedMesh;
            var baked = new Mesh(); smr.BakeMesh(baked);
            var v = baked.vertices; var tr = smr.transform;
            var w = v.Select(p => tr.TransformPoint(p)).ToArray();
            var min = new Vector3(w.Min(p => p.x), w.Min(p => p.y), w.Min(p => p.z));
            var max = new Vector3(w.Max(p => p.x), w.Max(p => p.y), w.Max(p => p.z));
            sb.AppendLine("world bounds min=" + min.ToString("F3") + " max=" + max.ToString("F3"));
            // Le V de poitrine est la zone la plus en avant à hauteur de torse : moyenne Z des sommets du torse
            var torso = w.Where(p => p.y > 1.0f && p.y < 1.4f && Mathf.Abs(p.x) < 0.3f).ToArray();
            sb.AppendLine("torso verts=" + torso.Length + " zmin=" + torso.Min(p => p.z).ToString("F3") + " zmax=" + torso.Max(p => p.z).ToString("F3"));
            sb.AppendLine("sprout side (verts y>1.9, |x|>0.4) mean x=" + w.Where(p => p.y > 1.9f && Mathf.Abs(p.x) > 0.4f).Select(p => p.x).DefaultIfEmpty(0).Average().ToString("F3"));
            Object.DestroyImmediate(baked);
            return sb.ToString();
        }
        finally { Object.DestroyImmediate(go); }
    }
}
