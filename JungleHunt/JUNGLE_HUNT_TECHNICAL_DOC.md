# Dossier Technique Complet : Jungle Hunt (Apple II)
**Atari Corp. / Taito America Corp. (1982)**  
*Reverse Engineering, Architecture Système, Protection Disquette & Routines de Jeu*

---

## Sommaire
1. [Introduction & Contexte Historique](#1-introduction--contexte-historique)
2. [Spécifications Matérielles Cibles (Apple II)](#2-spécifications-matérielles-cibles-apple-ii)
3. [La Disquette d'Origine "Plombée" & Protection](#3-la-disquette-dorigine-plombée--protection)
   - Structure physique et absence de VTOC DOS 3.3
   - Mécanisme de bootloader personnalisé et RWTS propriétaire
   - Le crack historique d'Elite Soft
   - Reconstruction propre en DOS 3.3 standard (`make_clean_dsk.py`)
4. [Cartographie Mémoire Globale (Memory Map)](#4-cartographie-mémoire-globale-memory-map)
   - Page Zéro ($0000 - $00FF) et variables clés
   - Pile et vecteurs système ($0100 - $03FF)
   - Moteur principal ($0A00 - $1EFF)
   - Buffers graphiques Hi-Res ($2000 - $5FFF)
   - Routines et données partagées ($6000 - $76FF)
   - Zone d'overlay dynamique des Niveaux ($7700 - $A6FF)
   - Soft Switches d'entrées/sorties Apple II ($C000 - $C0FF)
5. [Analyse Détaillée de l'Architecture Logicielle](#5-analyse-détaillée-de-larchitecture-logicielle)
   - La table de sauts principale ($0A00 - $0A6F)
   - La table des vecteurs indirects ($1300 - $135F)
   - La boucle principale de frame (`Main Game Loop`, $0A76 - $0A8E)
   - Le moteur graphique Hi-Res et calcul de balayage ($6000)
   - Gestion du son et des effets sonores ($672E / $67DA)
   - Détection des collisions ($63C9)
6. [Étude des 4 Niveaux de Jeu](#6-étude-des-4-niveaux-de-jeu)
   - Niveau 1 : La Jungle aux Lianes (Vines & Monkeys)
   - Niveau 2 : La Rivière aux Crocodiles & Plongée (Underwater & Oxygen)
   - Niveau 3 : La Pente aux Rochers (Rolling & Bouncing Boulders)
   - Niveau 4 : Le Village Cannibale & La Marmite (Rescue the Maiden)
7. [Reverse Engineering des Cheats & Points de Patch](#7-reverse-engineering-des-cheats--points-de-patch)
   - Registres de vies ($42 / $43)
   - Registres de temps / oxygène ($A3..$AA) et patch décrément ($0D79)
   - Invulnérabilités et bypass collisions
   - Équivalences MAME XML (Apple II vs Arcade `junglek`)

---

## 1. Introduction & Contexte Historique

Sorti en arcade en 1982 par Taito sous le titre initial **Jungle King**, le jeu mettait en scène un personnage rappelant fortement Tarzan. Suite aux réclamations des ayants droit d'Edgar Rice Burroughs, Taito modifia les graphismes : le héros devint Sir Dudley (un explorateur en tenue safari avec casque colonial) et les lianes furent remplacées par des cordes végétales, donnant naissance à **Jungle Hunt**.

La conversion sur micro-ordinateur Apple II a été publiée fin 1982 sous licence Atari / Taito. Il s'agit d'une prouesse technique remarquable pour l'Apple II :
- Animation fluide en graphismes Haute Résolution (Hi-Res 280x192).
- Quatre niveaux aux mécaniques de gameplay totalement différentes.
- Utilisation intensive de la mémoire (plus de 46 Ko occupés) grâce à un système d'**overlays dynamiques** rechargeant chaque niveau depuis la disquette en cours de partie.

---

## 2. Spécifications Matérielles Cibles (Apple II)

| Composant | Caractéristique sur Apple II / II+ / IIe |
| :--- | :--- |
| **Processeur** | MOS 6502 (8 bits), cadencé à **1.023 MHz** |
| **Mémoire Vive (RAM)** | 48 Ko minimum (64 Ko avec Language Card / Apple IIe) |
| **Affichage** | Mode Hi-Res plein écran : **280 × 192 pixels**, 6 couleurs (Noir, Blanc, Vert, Violet, Orange, Bleu) |
| **Double Buffering** | Page 1 Hi-Res ($2000 - $3FFF) et Page 2 Hi-Res ($4000 - $5FFF) |
| **Son** | 1-bit toggle speaker via soft switch `$C030` |
| **Contrôles** | Joystick analogique (Paddles `$C064` / boutons `$C061-$C062`) ou Clavier (`$C000`) |
| **Lecteur de disquette** | Apple Disk II (disquette 5.25 pouces 140 Ko, 35 pistes de 16 secteurs de 256 octets) |

---

## 3. La Disquette d'Origine "Plombée" & Protection

### Structure Physique et Absence de VTOC DOS 3.3
Sur un disque Apple II standard DOS 3.3 :
- La **Piste 17** contient le **VTOC** (Volume Table of Contents) au secteur 0 et le **Catalogue** aux secteurs 1 à 15, listant les fichiers, leur type et leur liste Piste/Secteur (T/S List).
- Les pistes 0, 1 et 2 hébergent le système d'exploitation DOS 3.3 et son sous-système **RWTS** (*Read/Write Track/Sector*).

La disquette commerciale de Jungle Hunt est dite **"plombée"** :
1. **Pas de VTOC standard** : La piste 17 est vierge ou détournée de son format catalogue. L'insertion de la disquette sous DOS 3.3 avec la commande `CATALOG` génère une erreur `DISK FULL` ou `FILE NOT FOUND`.
2. **Streaming direct des secteurs** : Le jeu n'utilise pas le DOS conventionnel pour charger ses données. Il implémente son propre micro-driver de disquette (situé en mémoire vers `$1D00`).
3. **Implantation géographique des pistes** :
   - **Pistes 0 à 2** : Code de boot personnalisé.
   - **Pistes 3 & 4** : Données et code du **Niveau 1** (Lianes).
   - **Pistes 5, 6 & 7** : Données et code du **Niveau 2** (Rivière aux crocodiles, 12 Ko).
   - **Pistes 8 & 9** : Données et code du **Niveau 3** (Rochers).
   - **Pistes 10 & 11** : Données et code du **Niveau 4** (Village cannibale).
   - **Pistes 12 & 13** : Image de l'écran titre Hi-Res ($2000 - $3FFF).
   - **Piste 19, Secteur 14** : Routine d'amorce initiale (139 octets exécutés à `$4000`).
   - **Pistes 25 & 26** : Moteur de jeu principal (`JUNGLE.MAIN`, 23 secteurs, chargé à `$0A00`).
   - **Pistes 27 & 28** : Données et sous-routines communes (`JUNGLE.DATA`, 25 secteurs, chargé à `$6000`).

### Le Crack Historique d'Elite Soft
Dans l'image disquette `Jungle Hunt (1982)(Atari)[cr Crack Elite Soft].dsk` :
- Les protections physiques d'origine (bits de synchronisation modifiés, altération du prologue d'adresse/données `D5 AA 96` / `D5 AA AD`) ont été normalisées pour être écrites sur n'importe quel lecteur Disk II.
- En revanche, **la structure brute des pistes a été conservée telle quelle** : pas de catalogue DOS 3.3, les pistes sont lues séquentiellement en lecture brute.

### Reconstruction DOS 3.3 Standard (`make_clean_dsk.py`)
Pour analyser, désassembler et modifier proprement le jeu, le script [`make_clean_dsk.py`](file:///c:/Users/baco/Documents/Dev/MameCheatFile/JungleHunt/make_clean_dsk.py) réalise une extraction et reconstruction complète :
1. **Création d'une image vierge 140 Ko** (143 360 octets).
2. **Copie d'un DOS 3.3 officiel** (pistes 0, 1 et 2 extraites du System Master Apple).
3. **Génération d'un catalogue DOS 3.3 valide** sur la piste 17 avec allocation de secteurs non conflictuels.
4. **Extraction et modularisation des fichiers** :
   - `HELLO` (Type `$02` Applesoft BASIC) : Script d'accueil qui affiche le titre et enchaîne :
     ```basic
     10 TEXT : HOME
     20 PRINT "========================================"
     30 PRINT "          JUNGLE HUNT (1982)            "
     40 PRINT "   ATARI CORP. / TAITO AMERICA CORP.    "
     50 PRINT "========================================"
     70 PRINT "CHARGEMENT DU MOTEUR ($0A00)..."
     80 PRINT CHR$(4);"BLOAD JUNGLE.MAIN"
     90 PRINT "CHARGEMENT DES DONNEES ($6000)..."
     100 PRINT CHR$(4);"BLOAD JUNGLE.DATA"
     110 PRINT "LANCEMENT DE JUNGLE HUNT..."
     120 PRINT CHR$(4);"BRUN JUNGLE HUNT"
     ```
   - `JUNGLE HUNT` (Type `$04` Binaire, adresse `$4000`, 139 octets) : Lanceur principal.
   - `JUNGLE.MAIN` (Type `$04` Binaire, adresse `$0A00`, 5 888 octets) : Moteur complet.
   - `JUNGLE.DATA` (Type `$04` Binaire, adresse `$6000`, 6 400 octets) : Sous-routines et tables.
   - `JUNGLE.PIC` (Type `$04` Binaire, adresse `$2000`, 8 192 octets) : Écran titre Hi-Res.
   - `LEVEL1.BIN` à `LEVEL4.BIN` (Type `$04` Binaire, adresse `$7700`) : Données de niveaux.
5. Résultat : une disquette standard DOS 3.3 bootable et modifiable avec n'importe quel éditeur de disquette ou émulateur AppleWin/MAME.

---

## 4. Cartographie Mémoire Globale (Memory Map)

```
+-------------------------------------------------------------------------+
| ADRESSE     | TAILLE   | CONTENU / FONCTION PRINCIPALE                  |
+-------------------------------------------------------------------------+
| $0000-$00FF | 256 o    | Page Zéro (Pointeurs indirects, variables jeu) |
| $0100-$01FF | 256 o    | Pile Système 6502 (Hardware Stack)             |
| $0200-$02FF | 256 o    | Buffer de saisie texte Apple II                |
| $0300-$03FF | 256 o    | Vecteurs Système & Reset ($03F2-$03F4)         |
| $0400-$07FF | 1 024 o  | Mémoire Texte / Lo-Res Page 1                  |
| $0800-$09FF | 512 o    | Tampon transitoire / Amorce de boot            |
| $0A00-$0A6F | 112 o    | TABLE DE SAUTS D'API (Jump Table 32 entrées)   |
| $0A70-$0A8E | 31 o     | BOUCLE PRINCIPALE DE JEU (Main Game Loop)      |
| $0A91-$12FF | 2 159 o  | Initialisation, scoring, machine d'états       |
| $1300-$135F | 96 o     | TABLE DE VECTEURS D'ADRESSES ($6000, $7000...) |
| $1400-$1EFF | 2 816 o  | Routines contrôleurs, écrans score & fin       |
| $1F00-$1FFF | 256 o    | Zone de sauvegarde/swap de la Page Zéro        |
| $2000-$3FFF | 8 192 o  | Graphismes Haute Résolution (Hi-Res Page 1)    |
| $4000-$5FFF | 8 192 o  | Graphismes Haute Résolution (Hi-Res Page 2)    |
| $7700-$96FF | 8 Ko     | OVERLAYS NIVEAUX 1, 3 & 4 (Lianes, Rochers, Cannibales) |
| $7700-$A6FF | 12 Ko    | OVERLAY NIVEAU 2 (Rivière aux Crocodiles, code étendu)  |
| $A000-$A6FF | 1.7 Ko   | Extension mémoire du Niveau 2 (Tables crocos & sprites) |
| $A700-$B7FF | 4 Ko     | Buffers de transit, décompression & tables d'état       |
| $B800-$BFFF | 2 Ko     | Pilote disquette bas niveau (RWTS résident pour $64EC)  |
| $C000-$C0FF | 256 o    | Soft Switches Matériels Apple II (I/O, Sons)   |
| $C100-$CFFF | 3 840 o  | ROMs des slots d'extension (Slot 6 Disk II)    |
| $D000-$FFFF | 12 Ko    | ROM AppleSoft BASIC & Moniteur Apple II        |
+-------------------------------------------------------------------------+
```

### Registres Clés en Page Zéro ($0000 - $00FF)

| Adresse | Rôle technique et utilisation dans le code |
| :--- | :--- |
| `$20 - $2F` | Registres de travail temporaires pour les calculs mathématiques et boucles |
| `$30 - $31` | **Flag d'état de partie** : `$31` non nul indique une partie en cours ; si nul, retour à l'attract mode |
| `$3E - $3F` | Pointeur d'adresse mémoire indirecte (destination pour copies et décompression) |
| `$40` | Index du joueur actif (0 = Joueur 1, 1 = Joueur 2) ou base d'adressage relatif |
| `$41` | Pointeur de base vers les données d'état du joueur courant |
| **`$42`** | **Nombre de vies restantes - Joueur 1** (valeur 0 à 9). Décrémenté lors de la mort |
| **`$43`** | **Nombre de vies restantes - Joueur 2** (valeur 0 à 9) |
| `$4C - $4D` | **Pointeur d'adresse écran Hi-Res** calculé par la routine `$6000` pour la ligne Y |
| `$A3 - $A6` | **Timer / Jauge d'Oxygène - Joueur 1** : Décompté à chaque tick par `$0D79: DEC $A6,X` |
| `$A7 - $AA` | **Timer / Jauge d'Oxygène - Joueur 2** |
| `$E6` | **Poids fort de la page graphique active** : `$20` pour Page 1 ($2000), `$40` pour Page 2 ($4000) |

---

## 5. Analyse Détaillée de l'Architecture Logicielle

### La Table de Sauts Principale ($0A00 - $0A6F)
Au début du moteur à `$0A00`, les développeurs ont implémenté une table de dispatching universelle : chaque instruction est un `JMP ($13xx)` qui pointe vers une case de la table de vecteurs à `$1300`. Cette architecture découple le moteur des routines graphiques et sonores :

| Entrée | Mnémonique | Vecteur | Cible | Fonctionnalité |
| :---: | :--- | :---: | :---: | :--- |
| `0A00` | `JMP $0A66` | - | `$0A66` | Démarrage du moteur et configuration |
| `0A03` | `JMP ($1300)` | `$1300` | **`$6000`** | Calcul de l'adresse Hi-Res de la ligne Y dans `$4C/$4D` |
| `0A06` | `JMP ($1302)` | `$1302` | **`$618E`** | Rendu de sprite / shape blitter |
| `0A09` | `JMP ($1304)` | `$1304` | **`$63C9`** | Détection de collision (boîtes englobantes) |
| `0A0C` | `JMP ($1306)` | `$1306` | **`$64EC`** | Transition et initialisation de niveau |
| `0A0F` | `JMP ($1308)` | `$1308` | **`$654E`** | Gestion de la touche Pause (`ESC`) |
| `0A12` | `JMP ($130A)` | `$130A` | **`$65C6`** | Sauvegarde Page Zéro vers `$1C00` et restauration depuis `$1F00` |
| `0A15` | `JMP ($130C)` | `$130C` | **`$65D8`** | Sauvegarde Page Zéro vers `$1F00` et restauration depuis `$1C00` |
| `0A18` | `JMP ($130E)` | `$130E` | **`$6646`** | Effacement de la page Hi-Res (définie par `$E6`) |
| `0A1B` | `JMP ($1310)` | `$1310` | **`$65F8`** | Réinitialisation et effacement de l'affichage |
| `0A1E` | `JMP ($1312)` | `$1312` | **`$65EA`** | Réinitialisation des contrôleurs graphiques |
| `0A21` | `JMP ($1314)` | `$1314` | **`$67DA`** | Déclenchement d'un effet sonore |
| `0A24` | `JMP ($1316)` | `$1316` | **`$6766`** | Lecture non bloquante du clavier |
| `0A27` | `JMP ($1318)` | `$1318` | **`$6606`** | Bascule de la page Hi-Res affichée (Page 1 ↔ Page 2) |
| `0A2A` | `JMP ($131A)` | `$131A` | **`$661F`** | Temporisation / attente de synchronisation |
| `0A2D` | `JMP ($131C)` | `$131C` | **`$6664`** | Rendu de texte sur l'écran Hi-Res |
| `0A30` | `JMP ($131E)` | `$131E` | **`$672E`** | Génération d'une tonalité audio (`$C030`) |
| `0A33` | `JMP ($1320)` | `$1320` | **`$66BE`** | Copie rapide de bloc mémoire |
| `0A36` | `JMP ($1322)` | `$1322` | **`$6B64`** | Générateur pseudo-aléatoire (PRNG) |
| `0A39` | `JMP ($1340)` | `$1340` | **`$1400`** | Dispatcher d'événements du moteur |
| `0A3C` | `JMP ($1342)` | `$1342` | **`$1494`** | Lecture des contrôles (Joystick / Clavier) |
| `0A3F` | `JMP ($1344)` | `$1344` | **`$1464`** | Calibration des entrées analogiques |
| `0A42` | `JMP ($1330)` | `$1330` | **`$72A5`** | Incrémentation du score |
| `0A45` | `JMP ($1332)` | `$1332` | **`$716B`** | Affichage du score Joueur 1 / Joueur 2 |
| `0A48` | `JMP ($1334)` | `$1334` | **`$7287`** | Mise à jour du compteur de vies |
| `0A4B` | `JMP ($1336)` | `$1336` | **`$706F`** | Rendu graphique des icônes de vies |
| `0A4E` | `JMP ($1338)` | `$1338` | **`$7152`** | Gestion du High Score & vie bonus |
| `0A51` | `JMP ($133A)` | `$133A` | **`$72C3`** | Test condition Game Over |
| `0A54` | `JMP ($133C)` | `$133C` | **`$722F`** | Animation de mort du joueur |
| `0A57` | `JMP ($133E)` | `$133E` | **`$7277`** | Réapparition du joueur au point de passage |
| `0A5A` | `JMP ($1352)` | `$1352` | **`$15CD`** | Écran de saisie des initiales High Score |
| `0A5D` | `JMP ($1354)` | `$1354` | **`$17D3`** | Écran de fin de partie (Game Over) |

---

### La Boucle Principale de Frame (`$0A76 - $0A8E`)
Chaque trame du jeu s'exécute selon une séquence déterministe au sein de cette boucle infinie :

```assembly
; === INITIALISATION (AVANT BOUCLE) ===
0A70: 20 6F FB    JSR $FB6F      ; SETPWRC : Reconfigure le vecteur Reset $03F2 vers $FAA6
0A73: 20 91 0A    JSR $0A91      ; Reset Page 0, configuration écran Hi-Res

; === BOUCLE PRINCIPALE INFINIE ===
0A76: 20 24 0A    JSR $0A24      ; -> $6766 : Teste l'état du clavier (lecture $C000)
0A79: 20 0D 0B    JSR $0B0D      ; Traitement des commandes clavier spécifiques
0A7C: 20 2B 0B    JSR $0B2B      ; Vérifie le flag $31 (si 0, redémarre l'attract mode)
0A7F: 20 A1 0C    JSR $0CA1      ; Sélectionne et bascule le joueur actif (P1 ou P2)
0A82: 20 50 0B    JSR $0B50      ; Rafraîchit l'affichage du score du joueur courant
0A85: 20 B7 0B    JSR $0BB7      ; Met à jour la machine d'état (physique, animations)
0A88: 20 C3 0B    JSR $0BC3      ; Lit les contrôles (joystick/touches) et applique l'action
0A8B: 20 83 0C    JSR $0C83      ; Teste la touche ESC ($654E) pour suspendre l'exécution
0A8E: 4C 76 0A    JMP $0A76      ; Bouclage infini vers la trame suivante
```

---

### Le Moteur Graphique Hi-Res & Routine `$6000`
L'Apple II possède une mémoire graphique Hi-Res notoirement non-linéaire : les 192 lignes de l'écran ne sont pas contiguës en mémoire mais entrelacées en 3 groupes de 8 blocs de 8 lignes.
La routine située à **`$6000`** résout ce calcul en temps record :
- **Entrées** : Registre `Y` = numéro de la ligne (0 à 191), Registre `$E6` = page graphique ($20 ou $40).
- **Sortie** : `$4C/$4D` = adresse de base 16 bits de la ligne dans la mémoire écran.
- Les sous-routines de dessin de sprites (`$618E`) et d'effacement (`$6646`) exploitent directement ce pointeur indirect `($4C),Y`.

---

### Rôle et Découpage de la Zone Haute ($A000 - $BFFF, 8 Ko)

La plage mémoire **`$A000 - $BFFF`** (située juste avant les adresses d'E/S matérielles en `$C000`) est au cœur de l'optimisation mémoire de Jungle Hunt.

#### Est-ce du code rechargé à chaque niveau ?
**Non, pas dans son ensemble.** Contrairement aux niveaux 1, 3 et 4 qui occupent strictement la plage `$7700 - $96FF` (8 Ko), l'espace `$A000 - $BFFF` a une structure mixte et asymétrique :

| Plage | Taille | Statut | Rôle technique et contenu |
| :--- | :---: | :---: | :--- |
| **`$A000 - $A6FF`** | 1.7 Ko | **Overlay Niveau 2** | **Extension de code et tables du Niveau 2** (Rivière aux Crocodiles). Le module du Niveau 2 fait 12 Ko au total (`$7700 - $A6FF`). Il déborde donc sur `$A000` pour loger la physique sous-marine de Dudley, le calcul de flottaison, la gestion de l'oxygène et les tables de spawn aléatoire des 4 types de crocodiles. |
| **`$A700 - $B7FF`** | 4 Ko | **Résident / Travail** | **Buffers de transit dynamique & décompression**. Zone tampon utilisée par le moteur pour préparer les coordonnées des sprites, les tampons de calcul de masquage Hi-Res et stocker l'état volatil des entités. |
| **`$B800 - $BFFF`** | 2 Ko | **Résident Permanent** | **Micro-pilote Disquette (RWTS allégé Apple II)**. Routines bas niveau de commande du Disk II (Slot 6) appelées directement par `$64EC` (`API_LOAD_NEXT_LEVEL`). Ce micro-pilote permet de streamer les pistes des niveaux (Pistes 3 à 11) secteur par secteur directement vers `$7700` sans dépendre d'un DOS 3.3 complet en mémoire (qui consommerait 10 Ko supplémentaires). |

---

## 6. Étude des 4 Niveaux de Jeu

Chaque niveau est un module binaire indépendant compilé pour résider à l'adresse **`$7700`** :

```
          [ Moteur $0A00 + Routines $6000 ]
                         │
        ┌────────────────┼────────────────┬────────────────┐
        ▼                ▼                ▼                ▼
   NIVEAU 1         NIVEAU 2         NIVEAU 3         NIVEAU 4
 (Lianes/Singes)  (Crocodiles)      (Rochers)        (Cannibales)
   Track 3..4       Track 5..7       Track 8..9      Track 10..11
   Taille: 8 Ko    Taille: 12 Ko    Taille: 8 Ko     Taille: 8 Ko
```

### Niveau 1 : La Jungle aux Lianes
- **Objectif** : Sauter de corde en corde d'arbre en arbre.
- **Dangers** : Singes montant le long des cordes et chutes dans le vide.
- **Routines clés** :
  - `$7B3E` / `$7B45` : Détection de collision avec les singes.
  - `$7B9F` : Test de chute dans un trou/ravin (`BCC $7BBD`).
  - `$7BD3` : Décrémentation de vie (`DEC $41,X`).

### Niveau 2 : La Rivière aux Crocodiles
- **Objectif** : Traverser la rivière à la nage en poignardant les crocodiles.
- **Mécanique d'oxygène** : La jauge de temps `$A3..$AA` fait office de jauge d'oxygène. Si le joueur reste trop longtemps sous l'eau sans remonter respirer à la surface, le compteur s'épuise et provoque la noyade.
- **Combat** : Le joueur peut attaquer les crocodiles uniquement quand leur gueule est fermée. Si la gueule est ouverte, le contact est mortel.

### Niveau 3 : La Pente aux Rochers
- **Objectif** : Gravir une colline pendant que des rochers de différentes tailles dévalent la pente.
- **Mécanique** : Les petits rochers doivent être sautés ; les gros rochers rebondissant en hauteur doivent être esquivés en se baissant (`DUCK`).

### Niveau 4 : Le Village Cannibale & La Marmite
- **Objectif** : Secourir la femme suspendue au-dessus d'une marmite bouillante.
- **Dangers** : Deux indigènes armés de lances effectuent des rondes et piquent le joueur.
- **Condition de victoire** : Sauter au bon moment pour attraper la jeune femme quand la corde la descend vers le chaudron, déclenchant l'animation de fin de boucle et le passage au cycle suivant avec une vitesse accrue.

---

## 7. Reverse Engineering des Cheats & Points de Patch

### Vies Infinies
- En Page Zéro, l'adresse **`$0042`** contient le nombre de vies du Joueur 1 (format BCD/binaire affichable de 1 à 9). L'adresse **`$0043`** concerne le Joueur 2.
- **Cheat MAME RAM** :
  ```xml
  <action>maincpu.pb@0042=09</action>
  <action>maincpu.pb@0043=09</action>
  ```
- **Patch ROM / Code** :
  À l'adresse `$7BD3` (dans le module de niveau), remplacer l'instruction :
  ```assembly
  7BD3: D6 41    DEC $41,X
  ```
  par deux NOPs :
  ```assembly
  7BD3: EA EA    NOP NOP
  ```
  Le joueur ne perd alors plus aucune vie lors d'une collision ou d'une chute.

### Temps & Oxygène Infini
- Le décompte du timer (qui sert également de réserve d'oxygène au Niveau 2) est orchestré par la routine `$0D79` :
  ```assembly
  0D79: D6 A6    DEC $A6,X      ; Décrémente le tick de timer du joueur actif
  ```
- **Patch d'arrêt du décompte** :
  Remplacer les octets à `$0D79` par `$EA $EA` (`NOP NOP`).
  Le chronomètre et la réserve d'oxygène restent ainsi indéfiniment gelés.

### Invulnérabilité Niveau 1 (Singes & Chute)
1. **Immunité aux Singes (Analyse détaillée du désassemblage)** :
   La routine de test de collision avec le singe débute à **`$7B1D`** :
   ```assembly
   7B1D: A0 00       LDY #$00       ; Pointeur d'offset 0 dans Y
   7B1F: B1 84       LDA ($84),Y    ; Lit l'état du singe via le vecteur ($84)
   7B21: C9 02       CMP #$02       ; Le singe est-il menaçant / actif (#$02) ?
   7B23: D0 22       BNE $7B47      ; Si non menaçant, saute vers la suite ($7B47) -> Pas de collision
   7B25: AD BE 13    LDA $13BE      ; Coordonnée verticale Y de Dudley
   7B28: 18          CLC 
   7B29: 69 14       ADC #$14       ; Demi-hauteur de boîte de collision (+20 px)
   7B2B: CD A3 13    CMP $13A3      ; Compare avec la coordonnée Y du singe
   7B2E: 90 17       BCC $7B47      ; Dudley au-dessus du singe : saute vers $7B47 (pas de contact)
   7B30: AD A1 13    LDA $13A1      ; Coordonnée horizontale X du singe
   7B33: 38          SEC 
   7B34: ED BC 13    SBC $13BC      ; Delta X = Singe X - Dudley X
   7B37: 30 07       BMI $7B40      ; Si Dudley est à droite, teste borne négative
   7B39: C9 14       CMP #$14       ; Compare l'écart à la largeur (+20 px)
   7B3B: B0 0A       BCS $7B47      ; Dudley trop loin à gauche : saute vers $7B47
   7B3D: 4C 8C 7B    JMP $7B8C      ; <--- COLLISION CONFIRMÉE ! Saute vers la mort de Dudley ($7B8C)
   7B40: C9 EC       CMP #$EC       ; Test borne négative (-20 px en signé = $EC)
   7B42: 90 03       BCC $7B47      ; Dudley trop loin à droite : saute vers $7B47
   7B44: 4C 8C 7B    JMP $7B8C      ; <--- COLLISION CONFIRMÉE ! Saute vers la mort de Dudley ($7B8C)
   7B47: 20 34 7D    JSR $7D34      ; --- SUITE NORMALE --- Rendu graphique si pas d'impact
   ```
   > [!NOTE]
   > **Note sur le désalignement à `$7B3E`** :  
   > L'instruction à `$7B3D` est `4C 8C 7B` (`JMP $7B8C`). Ses octets d'opérande sont situés à `$7B3E` (`$8C`) et `$7B3F` (`$7B`).  
   > Le cheat MAME patche ces deux octets en `$47 $7B` (et de même pour le saut alternatif à `$7B44` via `$7B45..$7B46`), ce qui transforme l'instruction en `4C 47 7B` (`JMP $7B47`), neutralisant instantanément la collision !  
   > Si un désassembleur commence naïvement son analyse à l'adresse du patch `$7B3E` au lieu du début de l'instruction (`$7B3D`), il découpe `8C 7B C9` en `STY $C97B`. Il s'agissait d'un pur artefact de désalignement d'un octet, et en aucun cas d'une écriture en ROM.
2. **Protection contre les chutes** : À l'adresse `$7B9F`, l'instruction `90 1C` (`BCC $7BBD`) teste si la chute libre de Dudley atteint le fond du ravin (`$AF`). Remplacer le code opcode `90` (BCC) par `B0` (BCS) fait flotter le personnage au-dessus de la fosse sans mourir.
3. **Vies infinies en collision** : À l'adresse `$7BD3`, l'instruction `D6 41` (`DEC $41,X`) décrémente les vies du joueur actif. Remplacer ces deux octets par `EA EA` (`NOP NOP`) préserve intégralement le stock de vies.

### Équivalences des Fichiers Cheats MAME

| Cheat | Apple II (`junghunt.xml`) | Arcade Hardware (`junglek.xml`) |
| :--- | :--- | :--- |
| **Vies Infinies P1** | `maincpu.pb@0042=09` | `maincpu.pb@8425=1F` |
| **Vies Infinies P2** | `maincpu.pb@0043=09` | `maincpu.pb@8426=1F` |
| **Temps Infini** | `maincpu.mb@0D79=EA EA` | `maincpu.pb@842F=99` |
| **Oxygène Infini** | Inclus dans le timer ($A6,X) | `maincpu.pb@8457=30` |
| **Invulnérabilité** | Patchs `$7B3E`, `$7B9F`, `$7BD3` | Multi-patchs `$1A6F`, `$287A`, `$3886` |
