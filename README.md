# Le golem, de Meshy à Unity

Le projet de la vidéo 1 de [Tirvel](https://www.youtube.com/@tirvel).

Un golem généré par IA avec [Meshy](https://www.meshy.ai), puis rendu jouable dans Unity par un agent (Claude Code), à partir d'un seul prompt.

## Contenu

- `PROMPT.md` : le prompt donné à l'agent.
- `golem.glb` : le modèle sorti de Meshy (139 000 triangles).
- `AgentScripts/build_golem.py` : les étapes Blender de l'agent, en un script rejouable. Réduction à 18 000 triangles, UV, bake couleur et normal map, squelette Humanoid, poids, export FBX.
- `AgentScripts/GolemSetup.cs`, `AgentScripts/GolemScene.cs` : les étapes Unity de l'agent.
- `Assets/Golem/` : le golem prêt pour Unity (FBX, textures, matériau) et sa scène jouable, `Scenes/GolemPlayground.unity`.

## Prérequis

- Unity 6000.2.6f2 (URP).
- Le paquet gratuit [Starter Assets : First Person + Third Person](https://assetstore.unity.com/packages/essentials/starter-assets-thirdperson-updates-in-new-charactercontroller-pa-196526), ajouté à ton compte Asset Store. Il n'est pas dans ce dépôt : il se télécharge depuis l'Asset Store.
- Pour rejouer l'étape Blender : Blender 5.2.

## Jouer

1. Ouvre le projet dans Unity.
2. Importe Starter Assets (Window > Package Manager > My Assets). La scène en a besoin pour le contrôleur, la caméra et les animations.
3. Ouvre `Assets/Golem/Scenes/GolemPlayground.unity` et lance le Play Mode.

## Refaire le golem

Depuis la racine du dépôt :

    blender --background --factory-startup --python AgentScripts/build_golem.py

Le script lit `golem.glb` et réécrit `Assets/Golem/golem.fbx` et `Assets/Golem/Textures/`. Ajoute `-- <dossier>` pour écrire ailleurs.

L'agent a d'abord tenté une autre réduction, par plans de facettes, puis l'a abandonnée. Le script ne garde que les étapes qui ont produit le modèle publié.

Côté Unity, l'agent a appelé les méthodes de `AgentScripts/` avec la CLI `unity` (paquet `com.unity.pipeline`), Unity ouvert :

    unity command run_script --file AgentScripts/GolemSetup.cs --entry GolemSetup.ImportHumanoid
    unity command run_script --file AgentScripts/GolemSetup.cs --entry GolemSetup.MapChest
    unity command run_script --file AgentScripts/GolemScene.cs --entry GolemScene.ReplaceInScene

`ReplaceInScene` attend la scène Playground des Starter Assets ouverte.

## Licences

- Code et prompt : MIT, voir `LICENSE`.
- Le golem (`golem.glb` et `Assets/Golem/`) : [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Model created with Meshy, modifié : réduit, retexturé par bake, riggé.
