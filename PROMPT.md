# Le prompt donné à l'agent

Premier message de la session, tel quel. L'agent était Claude Code, avec le MCP Blender et la CLI Unity.

Blender est ouvert via le MCP Blender. Unity est ouvert sur ce projet et se pilote avec la CLI Unity (commande `unity` ; `unity command` liste ce que l'éditeur expose).
golem.glb, à la racine du projet, est un personnage généré par IA. Rends-le jouable dans ce projet Unity, sans toucher à son style low-poly à facettes.

Dans Blender :
1. Importe golem.glb et mesure-le : triangles, dimensions, matériaux.
2. Réduis-le sous 20 000 triangles en gardant la silhouette : tête, mains, pousse, V sur la poitrine. Maillage manifold.
3. Échelle 1 unité = 1 m, hauteur d'environ 2 m, pivot entre les pieds au sol, face à +Z une fois dans Unity.
4. Un seul matériau, texture 2K maximum.
5. Squelette compatible Humanoid Unity (hanches, colonne, poitrine, cou, tête, épaules, bras, avant-bras, mains, cuisses, jambes, pieds), placé d'après les mesures du maillage. Poids automatiques ; mousse et pousse suivent l'os le plus proche.
6. Mets-le en pose de course et vérifie qu'aucune partie ne se déchire. Reviens en pose de repos.
7. Exporte Assets/Golem/golem.fbx.

Dans Unity :
8. Importe golem.fbx en Rig Humanoid et vérifie que l'avatar est valide.
9. Ouvre la scène Playground des Starter Assets (Third Person) et remplace le modèle du personnage jouable par le golem, en gardant son contrôleur et ses animations.
10. Lance le Play Mode et vérifie la console : aucune erreur. Laisse le jeu tourner, je teste la course moi-même au clavier.

Après chaque étape : ce que tu as mesuré, et si le critère passe ou non.
