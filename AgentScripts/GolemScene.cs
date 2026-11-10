using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class GolemScene
{
    const string FbxPath = "Assets/Golem/golem.fbx";
    const string AnimDir = "Assets/Starter Assets/Runtime/ThirdPersonController/Character/Animations";

    static AnimationClip Clip(string contains)
    {
        foreach (var guid in AssetDatabase.FindAssets("t:AnimationClip", new[] { AnimDir }))
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            foreach (var c in AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>())
                if (c.name.Contains(contains) && !c.name.StartsWith("__preview")) return c;
        }
        return null;
    }

    // Échantillonne une course sur le golem : les mains restent-elles hors du torse ?
    public static string CheckPose(string clipName)
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(FbxPath);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        var sb = new StringBuilder();
        try
        {
            var anim = go.GetComponent<Animator>();
            var clip = Clip(clipName);
            sb.AppendLine("clip=" + (clip ? clip.name + " len=" + clip.length : "null"));
            AnimationMode.StartAnimationMode();
            try
            {
                for (int i = 0; i <= 4; i++)
                {
                    float t = clip.length * i / 4f;
                    AnimationMode.BeginSampling();
                    AnimationMode.SampleAnimationClip(go, clip, t);
                    AnimationMode.EndSampling();
                    var lh = anim.GetBoneTransform(HumanBodyBones.LeftHand).position;
                    var rh = anim.GetBoneTransform(HumanBodyBones.RightHand).position;
                    var lua = anim.GetBoneTransform(HumanBodyBones.LeftUpperArm);
                    var dirL = (anim.GetBoneTransform(HumanBodyBones.LeftLowerArm).position - lua.position).normalized;
                    var lf = anim.GetBoneTransform(HumanBodyBones.LeftFoot).position;
                    var rf = anim.GetBoneTransform(HumanBodyBones.RightFoot).position;
                    sb.AppendLine($"t={t:F2} LHand={lh:F2} RHand={rh:F2} LUpperArmDir={dirL:F2} LFoot={lf:F2} RFoot={rf:F2}");
                }
            }
            finally { AnimationMode.StopAnimationMode(); }
        }
        finally { Object.DestroyImmediate(go); }
        return sb.ToString();
    }

    const string MatPath = "Assets/Golem/Golem_MAT.mat";

    static Material BuildMaterial()
    {
        const string colPath = "Assets/Golem/Textures/Golem_BaseColor.png";
        const string nrmPath = "Assets/Golem/Textures/Golem_Normal.png";
        var ti = (TextureImporter)AssetImporter.GetAtPath(nrmPath);
        if (ti.textureType != TextureImporterType.NormalMap) { ti.textureType = TextureImporterType.NormalMap; ti.SaveAndReimport(); }
        var ci = (TextureImporter)AssetImporter.GetAtPath(colPath);
        if (!ci.sRGBTexture) { ci.sRGBTexture = true; ci.SaveAndReimport(); }
        var mat = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
        if (!mat)
        {
            mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            AssetDatabase.CreateAsset(mat, MatPath);
        }
        mat.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(colPath));
        mat.SetColor("_BaseColor", Color.white);
        mat.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(nrmPath));
        mat.SetFloat("_BumpScale", 1f);
        mat.EnableKeyword("_NORMALMAP");
        mat.SetFloat("_Metallic", 0f);
        mat.SetFloat("_Smoothness", 0.36f);
        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssets();
        return mat;
    }

    // Étape 9 : remplace le modèle du joueur dans la scène ouverte, garde contrôleur et animations.
    public static string ReplaceInScene()
    {
        var sb = new StringBuilder();
        var player = GameObject.Find("PlayerArmature");
        if (!player) return "PlayerArmature absent";
        var mat = BuildMaterial();
        var avatar = AssetDatabase.LoadAllAssetsAtPath(FbxPath).OfType<Avatar>().First();
        var existing = player.transform.Find("Golem");
        if (existing) Undo.DestroyObjectImmediate(existing.gameObject);

        var golem = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(FbxPath));
        Undo.RegisterCreatedObjectUndo(golem, "Golem");
        golem.name = "Golem";
        Undo.SetTransformParent(golem.transform, player.transform, "Golem parent");
        golem.transform.localPosition = Vector3.zero;
        golem.transform.localRotation = Quaternion.identity;
        golem.transform.localScale = Vector3.one;
        var nestedAnimator = golem.GetComponent<Animator>();
        if (nestedAnimator) Undo.DestroyObjectImmediate(nestedAnimator);
        var smr = golem.GetComponentInChildren<SkinnedMeshRenderer>();
        Undo.RecordObject(smr, "Golem material");
        smr.sharedMaterial = mat;

        var an = player.GetComponent<Animator>();
        Undo.RecordObject(an, "Golem avatar");
        an.avatar = avatar;

        foreach (var oldName in new[] { "Geometry", "Skeleton" })
        {
            var old = player.transform.Find(oldName);
            if (!old) continue;
            try { Undo.DestroyObjectImmediate(old.gameObject); sb.AppendLine("supprimé " + oldName); }
            catch (System.Exception e) { Undo.RecordObject(old.gameObject, "hide"); old.gameObject.SetActive(false); sb.AppendLine("désactivé " + oldName + " (" + e.Message + ")"); }
        }

        // Capsule à la taille du golem : 2 m de haut, torse ±0,44 m.
        var cc = player.GetComponent<CharacterController>();
        Undo.RecordObject(cc, "Golem capsule");
        cc.height = 2.0f; cc.radius = 0.45f; cc.center = new Vector3(0f, 1.02f, 0f);
        var camRoot = player.transform.Find("PlayerCameraRoot");
        Undo.RecordObject(camRoot, "Golem camera root");
        camRoot.localPosition = new Vector3(0f, 1.55f, 0f);

        an.Rebind();
        EditorSceneManager.MarkSceneDirty(player.scene);
        EditorSceneManager.SaveScene(player.scene);
        sb.Append(DescribePlayer());
        sb.AppendLine("golem renderer material=" + smr.sharedMaterial.name + " shader=" + smr.sharedMaterial.shader.name + " bones=" + smr.bones.Length + " rootBone=" + smr.rootBone.name);
        return sb.ToString();
    }

    public static string DescribePlayer()
    {
        var sb = new StringBuilder();
        var scene = EditorSceneManager.GetActiveScene();
        sb.AppendLine("scene=" + scene.path);
        var player = GameObject.Find("PlayerArmature");
        if (!player) return sb.Append("PlayerArmature absent").ToString();
        sb.AppendLine("isPrefabInstance=" + PrefabUtility.IsPartOfPrefabInstance(player) + " pos=" + player.transform.position);
        foreach (var c in player.GetComponents<Component>()) sb.Append(c.GetType().Name + ", ");
        sb.AppendLine();
        foreach (Transform ch in player.transform) sb.AppendLine(" child " + ch.name + " active=" + ch.gameObject.activeSelf + " localPos=" + ch.localPosition);
        var an = player.GetComponent<Animator>();
        sb.AppendLine("animator avatar=" + (an.avatar ? an.avatar.name : "null") + " controller=" + (an.runtimeAnimatorController ? an.runtimeAnimatorController.name : "null") + " applyRootMotion=" + an.applyRootMotion);
        var cc = player.GetComponent<CharacterController>();
        sb.AppendLine($"cc height={cc.height} radius={cc.radius} center={cc.center} skin={cc.skinWidth} step={cc.stepOffset}");
        return sb.ToString();
    }
}
