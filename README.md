# MameCheatFile

[![MAME](https://img.shields.io/badge/MAME-Cheat%20Files-red.svg)](https://www.mamedev.org/)
[![Platform](https://img.shields.io/badge/Platform-Apple%20II%20%7C%20Arcade-blue.svg)]()
[![Processor](https://img.shields.io/badge/CPU-MOS%206502-orange.svg)]()
[![Python](https://img.shields.io/badge/Python-3.8%2B-green.svg)]()

**MameCheatFile** est un projet dédié au **reverse-engineering** approfondi de jeux vidéo rétro (Apple II, Arcade, etc.), au désassemblage de leurs binaires machine (MOS 6502), à la cartographie de leurs variables mémoire, et à la création de **fichiers de triche (cheat files XML)** prêts à l'emploi pour l'émulateur **MAME**.

---

## 🎯 Objectifs du Projet

1. **Décortiquer les jeux rétro** : Extraire les binaires des disquettes/ROMs d'époque (y compris les disquettes protégées/bootloaders personnalisés).
2. **Désassembler et Annoter** : Analyser le code assembleur (boucle principale, sous-routines graphiques Hi-Res, son, tables d'adresses indirectes, gestion des collisions).
3. **Identifier les adresses clés** : Localiser en mémoire vive (Page Zéro et RAM) les variables de vies, compteurs de temps, barres d'oxygène, états d'invulnérabilité et routines de détection de mort.
4. **Créer des fichiers de cheat MAME (`.xml`)** : Développer des cheats complets (gel de mémoire `pb@` / `pw@` ou modifications de code au vol `mb@` avec restauration d'opcodes d'origine).
5. **Partager des outils réutilisables** : Fournir des outils de désassemblage et d'analyse interactifs pour la communauté.

---

## 📁 Structure du Répertoire

```text
MameCheatFile/
├── bin2text.py                     # Désassembleur interactif MOS 6502 (GUI Tkinter + CLI + Export HTML)
├── JungleHunt/                     # Projet complet Jungle Hunt (Apple II & Arcade)
│   ├── JUNGLE_HUNT_TECHNICAL_DOC.md# Dossier technique complet (Memory map, protection, architecture)
│   ├── junghunt.xml                # Fichier Cheat MAME pour la version Apple II (driver 'apple2p' / 'apple2ee')
│   ├── junglek.xml                 # Fichier Cheat MAME pour la version Arcade (driver 'junglek')
│   ├── junglehunt_complete_reverse.html # Désassemblage interactif HTML complet du jeu (Multi-niveaux)
│   ├── level1_vines_reverse.html        # Reverse interactif Niveau 1 (Jungle aux lianes)
│   ├── level2_crocodiles_reverse.html   # Reverse interactif Niveau 2 (Rivière aux crocodiles)
│   ├── level3_boulders_reverse.html     # Reverse interactif Niveau 3 (Rochers)
│   ├── level4_cannibals_reverse.html    # Reverse interactif Niveau 4 (Marmite & cannibales)
│   ├── binaries/                   # Dumps binaires extraits par plage mémoire ($0A00, $6000, $7700)
│   ├── make_clean_dsk.py           # Script Python de reconstruction de disquette DOS 3.3 propre
│   ├── find_cheats.py              # Script utilitaire de recherche de signatures de cheats
│   ├── generate_master_reverse.py  # Générateur de la documentation reverse HTML
│   ├── consolidated_annotations.json # Base de données d'annotations et symboles 6502
│   └── extracted_sprites.json      # Extraction des coordonnées et formats de sprites
├── AE/                             # Projet en cours : A.E. (Broderbund / Apple II & Arcade)
│   └── README.md                   # Suivi du reverse engineering du jeu A.E.
└── README.md                       # Présentation générale du projet
```

---

## 🛠️ Outil inclus : `bin2text.py`

`bin2text.py` est un désassembleur MOS 6502 avancé capable de générer un rapport HTML interactif avec :
- Navigation par hyperliens sur toutes les instructions de saut (`JMP`, `JSR`, `BNE`, `BEQ`, `BCC`, `BCS`...).
- Résolution des adresses directes et indirectes (`($xx,X)`, `($xx),Y`).
- Détection des chaînes de texte ASCII Apple II (inversé, clignotant, normal).
- Injection d'annotations et labels de fonctions (depuis un fichier JSON ou texte).
- Interface graphique moderne sombre (Tkinter) ou ligne de commande (CLI).

### Utilisation de l'Interface Graphique (GUI)
```bash
python bin2text.py --gui
# Ou simplement sans arguments :
python bin2text.py
```

### Utilisation en Ligne de Commande (CLI)
```bash
python bin2text.py <fichier_binaire> <adresse_depart_hex> [fichier_sortie.html] -a annotations.json -t "Titre du rapport"

# Exemple pour Jungle Hunt (bloc principal $0A00) :
python bin2text.py JungleHunt/binaries/jungle_main_0A00.bin 0A00 reverse_0A00.html -a JungleHunt/consolidated_annotations.json
```

---

## 🎮 Jeux Décortiqués

### 1. Jungle Hunt (Apple II / Arcade)
- **Fichiers MAME XML** :
  - `JungleHunt/junghunt.xml` (pour Apple II)
  - `JungleHunt/junglek.xml` (pour Arcade)
- **Cheats disponibles** :
  - Vies infinies (Joueur 1 & Joueur 2)
  - Temps infini / Oxygène illimité
  - Désactivation du compte à rebours (patch NOP sur routine `DEC $A6,X`)
  - Invulnérabilité complète Niveau 1 (Singes & lianes)
  - Protection contre les chutes dans les fosses
  - Pas de perte de vie en cas de collision
- **Dossier technique** : Consulter [`JungleHunt/JUNGLE_HUNT_TECHNICAL_DOC.md`](file:///c:/Users/baco/Documents/Dev/MameCheatFile/JungleHunt/JUNGLE_HUNT_TECHNICAL_DOC.md) pour l'analyse exhaustive (déprotection disquette, détection de collisions, moteur Hi-Res 280x192).

### 2. A.E. (Broderbund)
- En cours d'analyse dans [`AE/`](file:///c:/Users/baco/Documents/Dev/MameCheatFile/AE/README.md).

---

## 🕹️ Comment Installer les Cheat Files dans MAME

1. Assurez-vous que l'option cheat est activée dans votre configuration MAME (`mame.ini`) :
   ```ini
   cheat 1
   ```
2. Placez le fichier `.xml` correspondant au jeu dans le sous-dossier `cheat` de MAME :
   - Pour les jeux d'arcade : placez `junglek.xml` dans `mame/cheat/junglek.xml` ou dans l'archive `cheat.7z`.
   - Pour les logiciels Apple II (Software List) : placez `junghunt.xml` dans `mame/cheat/apple2p/junghunt.xml` ou `mame/cheat/apple2_flop_orig/junghunt.xml`.
3. Lancez le jeu sous MAME, puis appuyez sur la touche <kbd>Tab</kbd> pour ouvrir le menu interne et accédez à **Cheat** pour activer les codes souhaités.

---

## 📜 Licence & Contributions

Projet open-source dédié à la préservation du patrimoine vidéoludique, à l'analyse pédagogique du code assembleur 6502 et à la communauté d'émulation rétro. Les contributions pour de nouveaux jeux sont les bienvenues !
