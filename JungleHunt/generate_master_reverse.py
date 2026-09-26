#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_master_reverse.py
Générateur Haute Fidélité de Reverse Engineering Complet pour Jungle Hunt (Apple II).
Intègre l'intégralité du jeu :
- Moteur Principal ($0A00 - $1EFF)
- Bibliothèque Hi-Res & Sons ($6000 - $76FF)
- Niveau 1 : La Jungle aux Lianes ($7700 - $96FF)
- Niveau 2 : La Rivière aux Crocodiles ($7700 - $A6FF)
- Niveau 3 : La Pente aux Rochers ($7700 - $96FF)
- Niveau 4 : Le Village Cannibale & La Marmite ($7700 - $96FF)

Fonctionnalités :
- Sélecteur d'onglets de niveaux interactif (filtrage ou vue d'ensemble)
- Synchronisation parfaite des points d'entrée (aucun lien mort)
- Système de navigation complet (Historique, Retour/Suivant, Toast flottant, Hashchange)
- Étiquettes sémantiques explicites (aucun LOC / SUB) et Doc-Cards détaillées
"""

import os
import sys
import json
import re

# Import du module transverse bin2text
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bin2text import OPCODES_6502, APPLE2_HARDWARE

# =============================================================================
# DONNÉES GRAPHIQUES & BITMAPS DES SPRITES (CHARGÉES DEPUIS EXTRACTED_SPRITES.JSON)
# =============================================================================
json_spr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extracted_sprites.json")
if os.path.exists(json_spr_path):
    with open(json_spr_path, "r", encoding="utf-8") as f:
        ALL_SPRITES = json.load(f)
else:
    ALL_SPRITES = {}

SPRITE_TRIGGERS = {
    "l1": 0x8000,
    "l2": 0x7EB0,
    "l3": 0x8000,
    "l4": 0x8000
}

MODULE_DATA_RANGES = {
    "main": [
        (0x12E9, 0x13FF, "Tables de constantes du moteur, vecteurs et scoring", 16),
        (0x151B, 0x15C6, "Données d'étalonnage et tables paddle/clavier", 16),
        (0x1715, 0x17D2, "Tables de texte et chaîne du High Score", 16),
        (0x1814, 0x1CFF, "Tampon de transit mémoire & zones de travail", 16),
        (0x1D74, 0x20FF, "Tampon de swap Page Zéro ($1F00-$1FFF) & padding", 16),
    ],
    "hires": [
        (0x600E, 0x618D, "Table des adresses des 192 lignes Hi-Res", 16),
        (0x6199, 0x63C8, "Table des décalages de lignes Hi-Res entrelacées", 16),
        (0x63D4, 0x64EB, "Table de conversion Y et masquage d'écran", 16),
        (0x6963, 0x6B0A, "Tables de fréquences audio, notes et timbres sonores", 16),
        (0x6C9E, 0x7000, "Polices de caractères et tables de caractères graphiques", 16),
        (0x74DE, 0x78FF, "Tampons de transit audio et coordonnées", 16),
    ],
    "l1": [
        (0x7BFD, 0x7C0F, "Table des offsets de trajectoire de chute", 16),
        (0x7DF8, 0x96FF, "Tables de trajectoire des lianes et sprites Hi-Res de Dudley et singes", 16),
    ],
    "l2": [
        (0x7CC8, 0xA6FF, "Tables d'animation aquatique, masques et sprites des crocodiles", 16),
    ],
    "l3": [
        (0x7D02, 0x96FF, "Tables de physique des rochers, trajectoires et sprites Hi-Res", 16),
    ],
    "l4": [
        (0x7CCE, 0x96FF, "Tables d'animation des flammes et sprites des cannibales / marmite", 16),
    ],
}

# =============================================================================
# ÉTIQUETTES SÉMANTIQUES PAR MODULE (AUCUN LOC_ / SUB_)
# =============================================================================
SEMANTIC_LABELS = {
    # --- MOTEUR RÉSIDANT : TABLE DE SAUTS API ($0A00 - $0A6F) ---
    0x0A00: "JMP_BOOT_ENTRY",
    0x0A03: "API_CALC_HIRES_SCANLINE",
    0x0A06: "API_DRAW_SPRITE_SHAPE",
    0x0A09: "API_DETECT_COLLISION",
    0x0A0C: "API_LOAD_NEXT_LEVEL",
    0x0A0F: "API_HANDLE_PAUSE_ESC",
    0x0A12: "API_SAVE_ZP_TO_1C00",
    0x0A15: "API_RESTORE_ZP_TO_1F00",
    0x0A18: "API_CLEAR_HIRES_PAGE",
    0x0A1B: "API_INIT_GRAPHICS",
    0x0A1E: "API_RESET_GRAPHICS",
    0x0A21: "API_TRIGGER_SOUND_FX",
    0x0A24: "API_READ_KEYBOARD",
    0x0A27: "API_TOGGLE_HIRES_PAGE",
    0x0A2A: "API_WAIT_VBLANK_DELAY",
    0x0A2D: "API_RENDER_HIRES_TEXT",
    0x0A30: "API_PLAY_SPEAKER_TONE",
    0x0A33: "API_FAST_MEM_COPY",
    0x0A36: "API_PRNG_RANDOM_GEN",
    0x0A39: "API_MAIN_DISPATCHER",
    0x0A3C: "API_READ_CONTROLLERS",
    0x0A3F: "API_CALIBRATE_PADDLE",
    0x0A42: "API_ADD_POINTS_SCORE",
    0x0A45: "API_DRAW_SCORES_P1_P2",
    0x0A48: "API_UPDATE_LIVES_COUNT",
    0x0A4B: "API_DRAW_LIVES_ICONS",
    0x0A4E: "API_CHECK_HIGH_SCORE",
    0x0A51: "API_TEST_GAME_OVER",
    0x0A54: "API_PLAYER_DEATH_ANIM",
    0x0A57: "API_RESPAWN_CHECKPOINT",
    0x0A5A: "API_HIGH_SCORE_SCREEN",
    0x0A5D: "API_GAME_OVER_SCREEN",
    0x0A60: "API_TITLE_SCREEN_LOOP",
    0x0A63: "API_ATTRACT_MODE_DEMO",
    0x0A66: "JMP_SETUP_SYSTEM",

    # --- MOTEUR RÉSIDANT : INITIALISATION & BOUCLE ($0A70 - $1EFF) ---
    0x0A70: "RESET_POWERUP_VECTOR",
    0x0A73: "BOOT_INITIALIZE_ENGINE",
    0x0A76: "MAIN_GAME_LOOP",
    0x0A8E: "MAIN_LOOP_RESTART",
    0x0A91: "RESET_GAME_MEMORY",
    0x0A94: "LOOP_CLEAR_ZERO_PAGE",
    0x0AA4: "CLEAR_HIRES_FRAME_BUFFER",
    0x0AB0: "ACTIVATE_HIRES_GRAPHICS_MODE",
    0x0ABF: "INIT_GAME_ENGINE_REGISTERS",
    0x0B0D: "PROCESS_KEYBOARD_INPUT",
    0x0B2B: "VERIFY_GAME_RUNNING_FLAG",
    0x0B30: "START_NEW_GAME_SESSION",
    0x0B50: "UPDATE_AND_DISPLAY_SCORE",
    0x0B74: "CHECK_BONUS_LIFE_THRESHOLD",
    0x0B8B: "HANDLE_STAGE_COMPLETION",
    0x0BC3: "HANDLE_PLAYER_INPUT_MOTION",
    0x0C83: "CHECK_PAUSE_ESC_STATUS",
    0x0CA1: "SWITCH_ACTIVE_PLAYER_TURN",
    0x0D50: "MAIN_TIMER_OXYGEN_CONTROLLER",
    0x0D79: "TIMER_OXYGEN_DECREMENT_TICK",
    0x0E09: "CONVERT_SCORE_TO_BCD",
    0x0E50: "DRAW_DIGITS_ON_HIRES",
    0x1300: "TABLE_VECTORS_DATA_START",
    0x1400: "ENGINE_EVENT_DISPATCHER",
    0x1464: "CALIBRATE_PADDLE_CONTROLS",
    0x1494: "READ_JOYSTICK_AXIS_INPUT",
    0x15CD: "ENTER_HIGH_SCORE_INITIALS",
    0x17D3: "GAME_OVER_DISPLAY_SCREEN",

    # --- BIBLIOTHÈQUE PARTAGÉE HI-RES & SONS ($6000 - $76FF) ---
    0x6000: "CALC_HIRES_SCANLINE_ADDR",
    0x618E: "DRAW_SPRITE_SHAPE_BLITTER",
    0x63C9: "CHECK_BOUNDING_BOX_COLLISION",
    0x64EC: "LOAD_LEVEL_OVERLAY_FROM_DISK",
    0x654E: "PAUSE_GAME_FREEZE_EXECUTION",
    0x65C6: "SAVE_ZP_TO_1C00_RESTORE_1F00",
    0x65D8: "SAVE_ZP_TO_1F00_RESTORE_1C00",
    0x65EA: "RESET_GRAPHICS_CONTROLLERS",
    0x65F8: "CLEAR_SCREEN_DISPLAY_BUFFER",
    0x6606: "TOGGLE_HIRES_PAGE_DISPLAY",
    0x661F: "WAIT_VBLANK_AND_SYNC_DELAY",
    0x6646: "CLEAR_ACTIVE_HIRES_PAGE",
    0x6664: "RENDER_HIRES_CHAR_STRING",
    0x66BE: "FAST_MEMORY_BLOCK_COPY",
    0x672E: "GENERATE_1BIT_SPEAKER_TONE",
    0x6766: "READ_KEYBOARD_NON_BLOCKING",
    0x67DA: "TRIGGER_SOUND_EFFECT_ENTRY",
    0x6B64: "PSEUDO_RANDOM_NUMBER_GEN",
    0x706F: "DRAW_PLAYER_LIVES_ICONS",
    0x7152: "CHECK_HIGH_SCORE_UPDATE",
    0x716B: "DRAW_SCORES_P1_P2_BAR",
    0x722F: "ANIMATE_PLAYER_DEATH_FALL",
    0x7277: "RESPAWN_PLAYER_AT_CHECKPOINT",
    0x7287: "REFRESH_LIVES_COUNTER_STATE",
    0x72A5: "ADD_POINTS_TO_PLAYER_SCORE",
    0x72C3: "TEST_GAME_OVER_CONDITIONS",
}

# Étiquettes spécifiques pour chaque niveau ($7700+)
LEVEL_LABELS = {
    "l1": {
        0x7700: "L1_INIT_VINES_STAGE",
        0x772D: "L1_MAIN_VINES_LOOP",
        0x7800: "L1_SWING_VINES_PHYSICS",
        0x7900: "L1_UPDATE_DUDLEY_POSITION",
        0x7B00: "L1_UPDATE_MONKEYS_ROUTINE",
        0x7B1D: "L1_START_MONKEY_COLLISION_CHECK",
        0x7B25: "L1_CHECK_MONKEY_COLLISION_BOX",
        0x7B3D: "L1_TRIGGER_MONKEY_COLLISION_DEATH",
        0x7B44: "L1_TRIGGER_MONKEY_COLLISION_DEATH_ALT",
        0x7B47: "L1_RESUME_AFTER_MONKEY_PASS",
        0x7B8C: "L1_HANDLE_MONKEY_HIT_DEATH",
        0x7B97: "L1_START_PIT_FALL_CHECK",
        0x7B9F: "L1_TEST_PIT_FALL_BRANCH",
        0x7BBD: "L1_EXIT_PIT_CHECK",
        0x7BD1: "L1_START_LIFE_SUBTRACTION",
        0x7BD3: "L1_DEC_LIFE_ACTIVE_PLAYER",
        0x7BE6: "L1_TEST_STAGE_COMPLETION",
        0x7BF5: "L1_STAGE_CLEAR_NEXT_LEVEL",
    },
    "l2": {
        0x7700: "L2_INIT_RIVER_STAGE",
        0x7730: "L2_MAIN_UNDERWATER_LOOP",
        0x77B8: "L2_UPDATE_WATER_SURFACE_CURRENT",
        0x78E5: "L2_SWIM_CONTROLS_AND_PHYSICS",
        0x792D: "L2_UPDATE_OXYGEN_GAUGE_TICK",
        0x7956: "L2_SURFACE_BREATH_REPLENISH_OXYGEN",
        0x79B1: "L2_SPAWN_AND_UPDATE_CROCODILES",
        0x7AFF: "L2_ANIMATE_CROCODILE_JAWS",
        0x7B2A: "L2_KNIFE_ATTACK_CROCODILE",
        0x7B8C: "L2_CHECK_CROCODILE_BITE_COLLISION",
        0x7BE6: "L2_HANDLE_DUDLEY_UNDERWATER_DEATH",
        0x7C03: "L2_STAGE_CLEAR_RIVER_EXIT",
        0x7CA6: "L2_RENDER_OXYGEN_BAR",
    },
    "l3": {
        0x7700: "L3_INIT_BOULDER_HILL_STAGE",
        0x7740: "L3_MAIN_HILL_ASCENT_LOOP",
        0x7762: "L3_UPDATE_HILL_SLOPE_SCROLLING",
        0x77AE: "L3_SPAWN_BOULDERS_ROUTINE",
        0x78FB: "L3_BOULDER_BOUNCE_PHYSICS_BIG",
        0x795D: "L3_BOULDER_ROLL_PHYSICS_SMALL",
        0x7AE5: "L3_DUDLEY_JUMP_AND_DUCK_CONTROLS",
        0x7B1C: "L3_UPDATE_BOULDER_SHAPES_ANIM",
        0x7B8F: "L3_CHECK_BOULDER_CRUSH_COLLISION",
        0x7C2E: "L3_HANDLE_BOULDER_DEATH",
        0x7CE2: "L3_STAGE_CLEAR_REACH_SUMMIT",
    },
    "l4": {
        0x7700: "L4_INIT_CANNIBAL_VILLAGE_STAGE",
        0x7733: "L4_MAIN_VILLAGE_LOOP",
        0x78EC: "L4_UPDATE_VILLAGE_PATROLS",
        0x7A2A: "L4_ANIMATE_MAIDEN_IN_POT",
        0x7A8E: "L4_CANNIBAL_SPEAR_THRUST_AI",
        0x7AF8: "L4_DUDLEY_JUMP_OVER_SPEARS",
        0x7B53: "L4_CHECK_SPEAR_THRUST_COLLISION",
        0x7B9A: "L4_HANDLE_SPEAR_DEATH",
        0x7C2D: "L4_RESCUE_MAIDEN_VICTORY_ROUTINE",
        0x7CA1: "L4_CYCLE_COMPLETION_SPEED_INCREASE",
    }
}

# =============================================================================
# CARTES DOCUMENTAIRES DES ROUTINES (DOC-CARDS)
# =============================================================================
ROUTINE_DOCS = {
    # --- MOTEUR ($0A00 - $1EFF) ---
    0x0A00: {
        "title": "Table de Sauts d'API Interne (API Jump Vector Table)",
        "role": "Point d'entrée du moteur résident. 32 instructions JMP qui redirigent les appels vers les sous-routines de JUNGLE.DATA ($6000) et des overlays ($7700).",
        "inputs": "Variable selon la fonction appelée.",
        "outputs": "Variable.",
        "gameplay": "Assure l'indépendance modulaire entre le moteur et les niveaux rechargés dynamiquement en RAM.",
        "cheat": None
    },
    0x0A70: {
        "title": "Configuration Démarrage & Sécurisation Reset (BOOT_SETUP)",
        "role": "Initialise les registres de base et détourne le vecteur Reset ($03F2/$03F3) vers la ROM ($FAA6) via SETPWRC ($FB6F).",
        "inputs": "Aucune.",
        "outputs": "Vecteur Reset protégé, Page Zéro prête.",
        "gameplay": "Empêche l'interruption intempestive du jeu par appui sur la touche Reset.",
        "cheat": None
    },
    0x0A76: {
        "title": "Boucle Principale de Trame (MAIN_GAME_LOOP)",
        "role": "Cœur temps réel exécuté à chaque trame (60 Hz). Ordonnance lecture clavier, machine d'états, joueur actif, scoring, physique et pause ESC.",
        "inputs": "Registres en Page Zéro ($31, $40, $41, $42).",
        "outputs": "Actualisation globale de l'état du jeu.",
        "gameplay": "Cadence toute l'action et assure la synchronisation fluide des animations.",
        "cheat": None
    },
    0x0A91: {
        "title": "Réinitialisation Système & Effacement (RESET_GAME_MEMORY)",
        "role": "Vide la Page Zéro ($00..$FF), efface la mémoire Hi-Res ($2000-$3FFF) et active les soft switches vidéo Apple II.",
        "inputs": "Aucune.",
        "outputs": "Page Zéro = 0, Hi-Res effacée, affichage configuré.",
        "gameplay": "Prépare la mémoire pour une nouvelle partie ou un redémarrage propre.",
        "cheat": None
    },
    0x0B0D: {
        "title": "Traitement des Commandes Clavier (PROCESS_KEYBOARD_INPUT)",
        "role": "Analyse le code ASCII ($C000) pour démarrer la partie (SPACE/RETURN), choisir 1 ou 2 joueurs ou réinitialiser.",
        "inputs": "A = code ASCII lu.",
        "outputs": "Mise à jour des indicateurs de démarrage.",
        "gameplay": "Gestion des entrées utilisateur au clavier.",
        "cheat": None
    },
    0x0B2B: {
        "title": "Validation Partie Active (VERIFY_GAME_RUNNING_FLAG)",
        "role": "Vérifie $31. Si $31 == 0, renvoie immédiatement vers l'attract mode de démonstration.",
        "inputs": "$31 = Flag partie en cours.",
        "outputs": "Poursuite du jeu ou boucle de démo.",
        "gameplay": "Bascule automatique entre attract mode et partie réelle.",
        "cheat": None
    },
    0x0B30: {
        "title": "Initialisation Nouvelle Session (START_NEW_GAME_SESSION)",
        "role": "Affecte 3 ou 9 vies aux joueurs dans $42/$43, remet à zéro les scores et charge le timer de départ dans $A3..$AA.",
        "inputs": "Nombre de joueurs.",
        "outputs": "$42 = Vies P1, $43 = Vies P2, $A3..$AA = Timer initial.",
        "gameplay": "Configure les paramètres de départ d'une partie.",
        "cheat": "Cible de triche : forcer 9 dans $42/$43 pour 9 vies de départ."
    },
    0x0B50: {
        "title": "Mise à Jour du Score Joueur (UPDATE_AND_DISPLAY_SCORE)",
        "role": "Compare le score, convertit en BCD via $0E09 et rafraîchit les chiffres sur l'écran Hi-Res.",
        "inputs": "Score binaire, index joueur $41.",
        "outputs": "Chiffres dessinés sur l'écran graphique.",
        "gameplay": "Actualisation instantanée des points gagnés.",
        "cheat": None
    },
    0x0B74: {
        "title": "Attribution Vie Bonus (CHECK_BONUS_LIFE_THRESHOLD)",
        "role": "Vérifie le franchissement du palier d'extra life (10 000 pts). Incrémente $42/$43 et joue le jingle.",
        "inputs": "Score du joueur.",
        "outputs": "Incrémentation de $42/$43.",
        "gameplay": "Récompense les paliers de points élevés.",
        "cheat": None
    },
    0x0BC3: {
        "title": "Physique & Déplacements Héros (HANDLE_PLAYER_INPUT_MOTION)",
        "role": "Convertit les axes joystick ($C064) ou touches de direction en vélocité X/Y pour Dudley.",
        "inputs": "Signaux manettes / clavier.",
        "outputs": "Coordonnées de Dudley mises à jour.",
        "gameplay": "Contrôle direct des sauts et mouvements du héros.",
        "cheat": None
    },
    0x0C83: {
        "title": "Gestionnaire de Pause ESC (CHECK_PAUSE_ESC_STATUS)",
        "role": "Détecte la touche Escape ($1B). Coupe le son, fige l'affichage et attend une touche pour reprendre.",
        "inputs": "Touche clavier.",
        "outputs": "Suspension ou reprise de la boucle.",
        "gameplay": "Mise en pause propre à tout instant.",
        "cheat": None
    },
    0x0CA1: {
        "title": "Alternance Joueurs Multijoueur (SWITCH_ACTIVE_PLAYER_TURN)",
        "role": "Lors d'une mort ou d'un niveau réussi en mode 2P, permute $40 et swap la Page Zéro via $1C00 / $1F00.",
        "inputs": "$40 = Joueur actif (0 ou 1).",
        "outputs": "Inversion de $40 et restauration des variables du joueur.",
        "gameplay": "Gestion fluide de la partie à deux joueurs.",
        "cheat": None
    },
    0x0D79: {
        "title": "Décompte Timer & Oxygène (TIMER_OXYGEN_DECREMENT_TICK)",
        "role": "Exécute DEC $A6,X pour décrémenter le tick d'horloge. Au Niveau 2, ce registre gère l'oxygène sous l'eau.",
        "inputs": "X = joueur, $A6,X = tick actuel.",
        "outputs": "Décrémentation. Si zéro -> déclenche la mort.",
        "gameplay": "Chronomètre général et réserve d'oxygène en plongée.",
        "cheat": "POINT DE TRICHE CRITIQUE : Patch NOP NOP ($EA $EA) pour temps & oxygène infini !"
    },
    0x0E09: {
        "title": "Convertisseur Score BCD (CONVERT_SCORE_TO_BCD)",
        "role": "Convertit la valeur binaire 16 bits du score en digits décimaux BCD pour affichage sur l'écran Hi-Res.",
        "inputs": "Score binaire en mémoire.",
        "outputs": "Table des chiffres BCD prête pour le blitter.",
        "gameplay": "Rendu textuel et score.",
        "cheat": None
    },
    0x1400: {
        "title": "Dispatcher d'Événements Moteur (ENGINE_EVENT_DISPATCHER)",
        "role": "Aiguille les transitions d'écrans : fin de niveau, perte de vie, écran titre ou saisie du High Score.",
        "inputs": "Code d'événement dans l'accumulateur.",
        "outputs": "Branchement vers la routine associée.",
        "gameplay": "Ordonnancement global du cycle de jeu.",
        "cheat": None
    },
    0x1464: {
        "title": "Calibration Manettes Paddles (CALIBRATE_PADDLE_CONTROLS)",
        "role": "Étalonne les temporisations analogiques des paddles Apple II ($C064/$C070) pour compenser les variations matérielles.",
        "inputs": "Lecture des décharges de condensateurs.",
        "outputs": "Seuils normalisés dans les registres.",
        "gameplay": "Précision des contrôles à la manette.",
        "cheat": None
    },

    # --- BIBLIOTHÈQUE COMMUNE ($6000 - $76FF) ---
    0x6000: {
        "title": "Calculateur d'Adresse Ligne Hi-Res (CALC_HIRES_SCANLINE_ADDR)",
        "role": "Résout l'adressage entrelacé non-linéaire de l'Apple II. Dépose l'adresse 16 bits de la ligne Y dans ($4C/$4D).",
        "inputs": "Y = ligne (0..191), $E6 = page ($20/$40).",
        "outputs": "$4C (poids faible) et $4D (poids fort).",
        "gameplay": "Pilier du moteur graphique Hi-Res.",
        "cheat": None
    },
    0x618E: {
        "title": "Traceur de Sprites & Masques (DRAW_SPRITE_SHAPE_BLITTER)",
        "role": "Blitter logiciel appliquant les masques de transparence pour dessiner Dudley, les animaux et les décors sans clignotement.",
        "inputs": "Pointeur de forme, X, Y.",
        "outputs": "Pixels écrits dans la RAM écran.",
        "gameplay": "Affichage de tous les éléments graphiques mobiles.",
        "cheat": None
    },
    0x63C9: {
        "title": "Détecteur de Collision Boîte Englobante (CHECK_BOUNDING_BOX_COLLISION)",
        "role": "Compare les boîtes rectangulaires (X1, Y1, X2, Y2) de Dudley avec celles des ennemis (singes, crocodiles, lances).",
        "inputs": "Coordonnées des entités.",
        "outputs": "Carry flag = 1 si collision, 0 si pas d'impact.",
        "gameplay": "Détermine si le joueur est touché.",
        "cheat": "Cible de triche pour immunité complète aux collisions."
    },
    0x64EC: {
        "title": "Chargeur d'Overlay de Niveau (LOAD_LEVEL_OVERLAY_FROM_DISK)",
        "role": "Lit les secteurs de la disquette pour charger le code du niveau suivant directement à l'adresse $7700.",
        "inputs": "Numéro du niveau (1, 2, 3 ou 4).",
        "outputs": "Binaire injecté à $7700 en mémoire vive.",
        "gameplay": "Transition transparente entre les 4 mondes du jeu.",
        "cheat": None
    },
    0x672E: {
        "title": "Générateur Audio 1-Bit Speaker (GENERATE_1BIT_SPEAKER_TONE)",
        "role": "Bascule la membrane du haut-parleur Apple II en accédant à $C030 dans une boucle calibrée.",
        "inputs": "A = note/fréquence, Y = durée.",
        "outputs": "Accès cyclique à $C030.",
        "gameplay": "Production des tonalités et mélodies du jeu.",
        "cheat": None
    },
    0x67DA: {
        "title": "Gestionnaire des Effets Sonores (TRIGGER_SOUND_EFFECT_ENTRY)",
        "role": "Table de dispatching des sons : saut, morsure, coup de couteau, rocher qui roule, jingle de fin de niveau.",
        "inputs": "Numéro d'effet sonore dans A.",
        "outputs": "Déclenchement du motif sonore correspondant.",
        "gameplay": "Feedback sonore complet.",
        "cheat": None
    },

    # --- NIVEAU 1 : LIANES ($7700) ---
    "L1_7700": {
        "title": "Niveau 1 : Initialisation des Lianes (L1_INIT_VINES_STAGE)",
        "role": "Positionne les arbres, les cordes végétales de départ et les singes grimpants pour le premier stage.",
        "inputs": "Index joueur.",
        "outputs": "Tables d'angles de lianes initialisées.",
        "gameplay": "Lancement du Niveau 1.",
        "cheat": None
    },
    "L1_7B1D": {
        "title": "Niveau 1 : Test Collision Singes (L1_CHECK_MONKEY_COLLISION)",
        "role": "Vérifie si Dudley entre en collision avec un singe grimpant sur la corde en cours d'accrochage.",
        "inputs": "Coordonnées de Dudley et des singes.",
        "outputs": "Saut vers chute mortelle en cas de contact.",
        "gameplay": "Danger principal du Niveau 1.",
        "cheat": "POINT DE TRICHE : Forcer le saut vers $7B47 pour traverser les singes sans dommage !"
    },
    "L1_7B9F": {
        "title": "Niveau 1 : Test Chute Ravin (L1_CHECK_FALLING_INTO_PIT)",
        "role": "Vérifie si la coordonnée Y de Dudley dépasse le bas de l'écran lors d'un saut manqué entre deux lianes.",
        "inputs": "Position Y de Dudley.",
        "outputs": "Déclenche l'animation de chute et la perte d'une vie si Y trop bas.",
        "gameplay": "Pénalise les sauts dans le vide.",
        "cheat": "POINT DE TRICHE : Remplacer BCC par BCS ($B0) pour flotter au-dessus du ravin !"
    },
    "L1_7BD3": {
        "title": "Niveau 1 : Décrémentation Vies sur Décès (L1_SUBTRACT_LIFE_ON_DEATH)",
        "role": "Exécute DEC $41,X pour soustraire une vie au joueur lorsqu'il heurte un singe ou tombe dans un trou.",
        "inputs": "X = joueur, $41 = pointeur vies.",
        "outputs": "Réduction du stock de vies.",
        "gameplay": "Perte de vie.",
        "cheat": "POINT DE TRICHE : Remplacer par NOP NOP ($EA $EA) pour vies infinies !"
    },

    # --- NIVEAU 2 : CROCODILES ($7700) ---
    "L2_7700": {
        "title": "Niveau 2 : Amorce de la Rivière (L2_INIT_RIVER_STAGE)",
        "role": "Initialise le décor aquatique, la profondeur de la rivière et les bancs de crocodiles.",
        "inputs": "Index joueur.",
        "outputs": "Variables de nage et d'oxygène prêtes.",
        "gameplay": "Lancement du Niveau 2 sous l'eau.",
        "cheat": None
    },
    "L2_7B2A": {
        "title": "Niveau 2 : Coup de Poignard (L2_KNIFE_ATTACK_CROCODILE)",
        "role": "Vérifie l'appui sur le bouton tir pour donner un coup de poignard vers l'avant. Tue les crocodiles à gueule fermée.",
        "inputs": "Bouton manette ou barre espace.",
        "outputs": "Élimination du crocodile et attribution des points.",
        "gameplay": "Défense active contre les reptiles.",
        "cheat": None
    },
    "L2_7B8C": {
        "title": "Niveau 2 : Collision Crocodile (L2_CHECK_CROCODILE_BITE_COLLISION)",
        "role": "Vérifie si Dudley touche un crocodile à gueule ouverte ou par l'arrière, provoquant une morsure mortelle.",
        "inputs": "Positions relatives Dudley et crocodiles.",
        "outputs": "Déclenche la mort par morsure si gueule ouverte.",
        "gameplay": "Danger principal du niveau sous-marin.",
        "cheat": "POINT DE TRICHE : Bypass du saut pour immunité totale aux morsures de crocodiles !"
    },
    "L2_792D": {
        "title": "Niveau 2 : Épuisement Oxygène (L2_UPDATE_OXYGEN_GAUGE_TICK)",
        "role": "Décompte la jauge d'air respirable quand Dudley est immergé. Déclenche la noyade si la jauge atteint zéro.",
        "inputs": "Chronomètre d'immersion.",
        "outputs": "Réduction de l'oxygène, noyade à zéro.",
        "gameplay": "Contrainte de remontée régulière en surface.",
        "cheat": "POINT DE TRICHE : Désactivation de la perte d'air pour plongée illimitée !"
    },

    # --- NIVEAU 3 : ROCHERS ($7700) ---
    "L3_7700": {
        "title": "Niveau 3 : Amorce Pente aux Rochers (L3_INIT_BOULDER_HILL_STAGE)",
        "role": "Génère le profil de la colline et initialise les générateurs de rochers dévalant la pente.",
        "inputs": "Index joueur.",
        "outputs": "Pente et tables de rochers configurées.",
        "gameplay": "Lancement du Niveau 3.",
        "cheat": None
    },
    "L3_78FB": {
        "title": "Niveau 3 : Physique Grands Rochers (L3_BOULDER_BOUNCE_PHYSICS_BIG)",
        "role": "Calcule la trajectoire parabolique des gros rochers rebondissant au-dessus de Dudley.",
        "inputs": "Vecteurs gravitationnels et sol.",
        "outputs": "Hauteur et vitesse des rochers géants.",
        "gameplay": "Nécessite de se baisser (DUCK) pour les laisser passer.",
        "cheat": None
    },
    "L3_7B8F": {
        "title": "Niveau 3 : Écrasement Rocher (L3_CHECK_BOULDER_CRUSH_COLLISION)",
        "role": "Détecte si un rocher (petit ou grand) percute Dudley de plein fouet pendant sa course.",
        "inputs": "Coordonnées de collision.",
        "outputs": "Animation d'écrasement et perte de vie.",
        "gameplay": "Danger du niveau de montagne.",
        "cheat": "POINT DE TRICHE : Ignorer la collision pour gravir la colline sans crainte !"
    },

    # --- NIVEAU 4 : CANNIBALES ($7700) ---
    "L4_7700": {
        "title": "Niveau 4 : Amorce Village Cannibale (L4_INIT_CANNIBAL_VILLAGE_STAGE)",
        "role": "Positionne les deux cannibales avec lances, la marmite bouillante et la jeune femme suspendue.",
        "inputs": "Index joueur.",
        "outputs": "Scène finale configurée.",
        "gameplay": "Lancement du Niveau 4 final.",
        "cheat": None
    },
    "L4_7A2A": {
        "title": "Niveau 4 : Animation Fille dans la Marmite (L4_ANIMATE_MAIDEN_IN_POT)",
        "role": "Gère le mouvement vertical de descente et montée de la corde suspendant la demoiselle au-dessus du chaudron.",
        "inputs": "Cycle de frame.",
        "outputs": "Position Y de la jeune femme.",
        "gameplay": "Fenêtre d'opportunité pour le saut de sauvetage.",
        "cheat": None
    },
    "L4_7B53": {
        "title": "Niveau 4 : Collision Lances Cannibales (L4_CHECK_SPEAR_THRUST_COLLISION)",
        "role": "Teste l'impact entre Dudley et les pointes des lances dressées par les indigènes en ronde.",
        "inputs": "Position de Dudley et des pointes de lance.",
        "outputs": "Mort par transpercement si contact.",
        "gameplay": "Obstacle à sauter pour atteindre la marmite.",
        "cheat": "POINT DE TRICHE : Bypass de la blessure de lance pour traverser le village !"
    },
    "L4_7C2D": {
        "title": "Niveau 4 : Sauvetage de la Demoiselle & Victoire (L4_RESCUE_MAIDEN_VICTORY_ROUTINE)",
        "role": "Déclenché quand Dudley attrape la jeune femme en plein vol. Joue le jingle de félicitations, attribue le bonus et boucle le jeu avec vitesse accrue.",
        "inputs": "Saut réussi sur la fille.",
        "outputs": "Animation de bisou / cœur, boucle vers Niveau 1 plus difficile.",
        "gameplay": "Victoire suprême du jeu Jungle Hunt !",
        "cheat": None
    }
}

# =============================================================================
# ANNOTATIONS LIGNE PAR LIGNE DÉTAILLÉES
# =============================================================================

# Charge automatiquement toutes les annotations de consolidated_annotations.json
DETAILED_LINE_COMMENTS = {
    0x0A70: "Initialisation Power-Up : JSR $FB6F reconfigure le vecteur Reset $03F2 pour interdire le redémarrage intempestif",
    0x0A73: "Appel de la routine de remise à zéro du moteur et de l'affichage ($0A91)",
    0x0A76: "--- POINT D'ENTRÉE TRAME (MAIN GAME LOOP) ---",
    0x0A79: "Vérifie les touches frappées et déclenche les actions associées ($0B0D)",
    0x0A7C: "Teste le flag partie active dans $31 (si nul, retourne en mode démo attract)",
    0x0A7F: "Bascule vers le joueur actif P1/P2 selon la configuration de partie ($0CA1)",
    0x0A82: "Met à jour et réaffiche le score du joueur en cours ($0B50)",
    0x0A85: "Actualise la machine d'états (physique, inertie, chronomètre, animations) ($0BB7)",
    0x0A88: "Lit les entrées contrôleurs (manette / clavier) et applique les mouvements du héros ($0BC3)",
    0x0A8B: "Vérifie si la touche ESC a été pressée pour suspendre le jeu ($0C83 -> $654E)",
    0x0A8E: "Fin de trame : boucle infinie vers le début de la trame suivante ($0A76)",

    0x0A91: "Sauvegarde la Page Zéro dans $1C00 et restaure le bloc d'état depuis $1F00",
    0x0A94: "Prépare l'indice Y = $00 pour la boucle de mise à zéro de la Page Zéro",
    0x0A96: "Charge zéro dans l'accumulateur",
    0x0A98: "Efface l'octet Page Zéro à l'adresse ($00,Y)",
    0x0A9B: "Incrémente le pointeur de boucle Y",
    0x0A9C: "Tant que Y ne repasse pas à zéro, continue d'effacer la Page Zéro ($00..$FF)",
    0x0A9E: "Définit la page graphique Hi-Res par défaut ($20 = Page 1)",
    0x0AA0: "Stocke la page active dans le registre d'état $E6",
    0x0AA4: "Efface l'intégralité de la mémoire Haute Résolution de la page sélectionnée ($6646)",
    0x0AB0: "BIT $C010 : Réinitialise le strobe du clavier Apple II (acquitte les touches en attente)",
    0x0AB3: "BIT $C050 : Bascule l'affichage en mode Graphique plein écran",
    0x0AB6: "BIT $C054 : Sélectionne la Page 1 graphique ($2000-$3FFF)",
    0x0AB9: "BIT $C057 : Active le mode Haute Résolution (Hi-Res 280x192 pixels)",
    0x0ABC: "BIT $C052 : Active le mode Full Screen (sans les 4 lignes de texte en bas)",

    0x0B0D: "Lecture du clavier : charge le code de touche dans A et teste le bit 7",
    0x0B2B: "Charge l'état du drapeau de jeu $31 pour vérifier si une partie est active",
    0x0B30: "Démarrage d'une nouvelle session : initialise les scores et compteurs des deux joueurs",
    0x0B3B: "Définit 3 vies par défaut pour le joueur dans le registre X",
    0x0B3D: "Enregistre le nombre de vies initiales du Joueur 1 dans $42",
    0x0B3F: "Enregistre le nombre de vies initiales du Joueur 2 dans $43",
    0x0B4D: "Définit le Joueur 1 comme joueur actif au départ ($40 = 0)",

    0x0B50: "Début de la routine de score : vérifie si le score a changé et lance la conversion BCD",
    0x0B74: "Test d'obtention de vie supplémentaire : compare le score actuel au seuil d'extra life",
    0x0BC3: "Lecture des contrôles : interroge les manettes analogiques ($C064) ou le clavier",
    0x0C83: "Test de la touche ESC : si pressée, saute vers $654E pour figer l'affichage",
    0x0CA1: "Gestion du changement de joueur : inverse l'index $40 et swap la mémoire vive",
    0x0D79: "DEC $A6,X : DÉCOMPTE DU TICK DU TIMER / OXYGÈNE -> Patch NOP NOP pour temps infini !",
    0x0E09: "Début de la conversion binaire vers BCD pour le rendu des scores sur l'écran Hi-Res",
    0x1400: "Point d'entrée du gestionnaire d'événements et de transitions de niveaux du moteur",
    0x1464: "Routine de calibration matérielle des potentiomètres de manettes Apple II",

    0x6000: "Calcul de l'adresse de ligne Hi-Res : prend Y (0..191) et $E6, dépose le pointeur dans $4C/$4D",
    0x618E: "Traceur de formes : dessine un sprite Hi-Res avec gestion de transparence par masque",
    0x63C9: "Détecteur de collisions par boîte englobante rectangulaire (X1, Y1, X2, Y2)",
    0x64EC: "Chargeur d'overlay de niveau : charge le fichier binaire correspondant depuis la disquette vers $7700",
    0x654E: "Routine de pause : fige l'exécution et coupe le haut-parleur jusqu'à nouvel appui de touche",
    0x672E: "Générateur sonore : commute $C030 en boucle pour produire une tonalité sur le haut-parleur",
    0x67DA: "Point d'entrée du synthétiseur d'effets sonores du jeu (bruits d'impact, sauts, alarmes)",

    # Niveau 1
    0x7700: "Niveau 1 : Initialisation des arbres, cordes de lianes et singes",
    0x7800: "Physique des lianes : calcule l'oscillation angulaire des cordes selon le chronomètre",
    0x7900: "Physique de Dudley : gère le balancement accroché à la corde et le décrochage",
    0x7B1D: "LDY #$00 : Début du test de collision singe -> initialise l'offset 0",
    0x7B21: "CMP #$02 : Vérifie si le singe est en état d'attaque menaçant (#$02)",
    0x7B25: "LDA $13BE : Charge la coordonnée verticale Y de Dudley",
    0x7B30: "LDA $13A1 : Charge la coordonnée horizontale X du singe",
    0x7B37: "BMI $7B40 : Si Dudley est à droite du singe, teste la borne négative",
    0x7B3D: "JMP $7B8C : 💥 [COLLISION SINGE 1] Déclenche la mort de Dudley ($7B8C) ! [TRICHE MAME : patcher opérande $7B3E..$7B3F vers $7B47]",
    0x7B40: "CMP #$EC : Test borne négative de collision (-20 pixels)",
    0x7B44: "JMP $7B8C : 💥 [COLLISION SINGE 2] Déclenche la mort de Dudley ($7B8C) ! [TRICHE MAME : patcher opérande $7B45..$7B46 vers $7B47]",
    0x7B47: "JSR $7D34 : --- PAS DE COLLISION --- Poursuit le cycle d'affichage normal du Niveau 1",
    0x7B8C: "LDA #$05 : Déclenchement de l'animation de chute mortelle de Dudley",
    0x7B9F: "BCC $7BBD : [TEST CHUTE FOSSE] Si encore au-dessus du fond ($AF), saute vers RTS [TRICHE MAME : inverser BCC en BCS]",
    0x7BD3: "DEC $41,X : [PERTE DE VIE NIVEAU 1] Décrémente les vies du joueur ! [TRICHE MAME : patcher en NOP NOP]",
    0x7BF5: "INC $36 : 🎉 [STAGE CLEAR NIVEAU 1] Déclenche le passage au Niveau 2 !",
}

# Charge automatiquement toutes les annotations de consolidated_annotations.json
ann_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "consolidated_annotations.json")
if os.path.exists(ann_json_path):
    with open(ann_json_path, "r", encoding="utf-8") as _f_ann:
        _loaded_ann = json.load(_f_ann)
    for _k, _v in _loaded_ann.items():
        DETAILED_LINE_COMMENTS[_k] = _v
        try:
            _addr_int = int(_k, 16)
            if _addr_int not in DETAILED_LINE_COMMENTS:
                DETAILED_LINE_COMMENTS[_addr_int] = _v
        except ValueError:
            pass

# =============================================================================
# DÉSASSEMBLAGE INTELLIGENT AVEC SYNCHRONISATION DES POINTS D'ENTRÉE
# =============================================================================
def smart_disasm(data, start_addr, known_entry_points, prefix="", data_ranges=None):
    """
    Désassemble un binaire 6502 en garantissant qu'aucun point d'entrée connu
    ne soit 'avalé' et que les plages de données brutes (tables, sprites, buffers)
    soient émises en paquets d'octets sans interprétation d'opcodes erronée.
    """
    if data_ranges is None:
        data_ranges = []

    instructions = []
    i = 0
    data_len = len(data)

    while i < data_len:
        addr = start_addr + i

        # Vérification si l'adresse courante appartient à une plage de DONNÉES / TABLES / SPRITES
        in_data_range = False
        for r_start, r_end, r_label, chunk_size in data_ranges:
            if r_start <= addr <= r_end:
                in_data_range = True
                rem_range = r_end - addr + 1
                rem_data = data_len - i
                l = min(chunk_size, rem_range, rem_data)
                chunk = data[i : i + l]
                dom_id = f"{prefix}_{addr:04X}" if prefix else f"{addr:04X}"
                op_str = ", ".join(f"${b:02X}" for b in chunk)

                instructions.append({
                    "addr": addr,
                    "dom_id": dom_id,
                    "prefix": prefix,
                    "bytes": chunk,
                    "op": None,
                    "mnemonic": ".byte",
                    "mode": "data",
                    "length": l,
                    "operand": op_str,
                    "target": None,
                    "delta": None,
                    "indirect_resolved": None,
                    "category": "data-packet",
                    "is_code": False,
                    "data_banner": r_label if addr == r_start else None
                })
                i += l
                break

        if in_data_range:
            continue

        op = data[i]

        if op in OPCODES_6502:
            mnem, mode, l = OPCODES_6502[op]
            # Vérifie si un point d'entrée connu se trouve DANS cette instruction (overshoot)
            overshoot = False
            for step in range(1, l):
                if (addr + step) in known_entry_points:
                    overshoot = True
                    break

            if not overshoot and i + l <= data_len:
                chunk = data[i : i + l]
                target_addr = None
                delta = None
                operand_str = ""
                indirect_resolved = None

                if mode == "impl": operand_str = ""
                elif mode == "acc": operand_str = "A"
                elif mode == "imm": operand_str = f"#${chunk[1]:02X}"
                elif mode == "zp":
                    target_addr = chunk[1]
                    operand_str = f"${chunk[1]:02X}"
                elif mode == "zpx":
                    target_addr = chunk[1]
                    operand_str = f"${chunk[1]:02X},X"
                elif mode == "zpy":
                    target_addr = chunk[1]
                    operand_str = f"${chunk[1]:02X},Y"
                elif mode == "abs":
                    target_addr = chunk[1] | (chunk[2] << 8)
                    operand_str = f"${target_addr:04X}"
                elif mode == "absx":
                    target_addr = chunk[1] | (chunk[2] << 8)
                    operand_str = f"${target_addr:04X},X"
                elif mode == "absy":
                    target_addr = chunk[1] | (chunk[2] << 8)
                    operand_str = f"${target_addr:04X},Y"
                elif mode == "ind":
                    vec_addr = chunk[1] | (chunk[2] << 8)
                    operand_str = f"(${vec_addr:04X})"
                    target_addr = vec_addr
                elif mode == "indx": operand_str = f"(${chunk[1]:02X},X)"
                elif mode == "indy": operand_str = f"(${chunk[1]:02X}),Y"
                elif mode == "rel":
                    offset = chunk[1]
                    if offset >= 0x80: offset -= 256
                    target_addr = addr + 2 + offset
                    delta = offset
                    operand_str = f"${target_addr:04X}"

                # Catégorie syntaxique
                cat = "data"
                if mnem in ("JMP", "JSR"): cat = "flow-jump"
                elif mnem.startswith("B") and mnem not in ("BIT", "BRK"): cat = "flow-branch"
                elif mnem in ("RTS", "RTI"): cat = "flow-ret"
                elif mnem in ("LDA", "LDX", "LDY"): cat = "load"
                elif mnem in ("STA", "STX", "STY"): cat = "store"
                elif mnem in ("CMP", "CPX", "CPY", "BIT"): cat = "compare"
                elif mnem in ("ADC", "SBC", "INC", "DEC", "INX", "DEX", "INY", "DEY", "ASL", "LSR", "ROL", "ROR", "AND", "ORA", "EOR"): cat = "math"
                elif mnem in ("PHA", "PLA", "PHP", "PLP", "TXS", "TSX"): cat = "stack"
                elif mnem in ("CLC", "SEC", "CLI", "SEI", "CLD", "SED", "CLV"): cat = "flag"

                dom_id = f"{prefix}_{addr:04X}" if prefix else f"{addr:04X}"

                instructions.append({
                    "addr": addr,
                    "dom_id": dom_id,
                    "prefix": prefix,
                    "bytes": chunk,
                    "op": op,
                    "mnemonic": mnem,
                    "mode": mode,
                    "length": l,
                    "operand": operand_str,
                    "target": target_addr,
                    "delta": delta,
                    "indirect_resolved": indirect_resolved,
                    "category": cat,
                    "is_code": True
                })
                i += l
                continue

        # Octet de données / padding
        dom_id = f"{prefix}_{addr:04X}" if prefix else f"{addr:04X}"
        instructions.append({
            "addr": addr,
            "dom_id": dom_id,
            "prefix": prefix,
            "bytes": bytes([op]),
            "op": op,
            "mnemonic": ".byte",
            "mode": "raw",
            "length": 1,
            "operand": f"${op:02X}",
            "target": None,
            "indirect_resolved": None,
            "category": "unknown",
            "is_code": False
        })
        i += 1

    return instructions


# =============================================================================
# GÉNÉRATEUR DU DOCUMENT MAÎTRE MULTI-NIVEAUX
# =============================================================================
def build_master_html():
    out_html = "JungleHunt/junglehunt_complete_reverse.html"
    bin_dir = "JungleHunt/binaries"

    print("[*] Initialisation du désassemblage multi-niveaux pour Jungle Hunt...")

    modules_config = [
        {
            "id": "main",
            "title": "Moteur Principal ($0A00 - $1EFF)",
            "short": "Moteur",
            "icon": "🕹️",
            "file": "jungle_main_0A00.bin",
            "start": 0x0A00,
            "end": 0x1F00,
            "prefix": "",
            "desc": "Cœur du système résident : table de sauts d'API universelle ($0A00), boucle principale 60 Hz ($0A76), gestion du clavier, scoring BCD, machine d'états et écrans de fin.",
            "badge": "Moteur Résident",
            "color": "#38bdf8"
        },
        {
            "id": "gfx",
            "title": "Bibliothèque Hi-Res & Audio ($6000 - $76FF)",
            "short": "GFX & Sons",
            "icon": "🎨",
            "file": "jungle_data_6000.bin",
            "start": 0x6000,
            "end": 0x7700,
            "prefix": "",
            "desc": "Bibliothèque commune résidente : calculateur de balayage entrelacé Hi-Res ($6000), shape blitter de sprites ($618E), détection de collision ($63C9), chargeur de niveaux ($64EC) et synthétiseur audio 1-bit ($672E/$67DA).",
            "badge": "Bibliothèque Partagée",
            "color": "#a855f7"
        },
        {
            "id": "l1",
            "title": "Niveau 1 : La Jungle aux Lianes ($7700 - $96FF)",
            "short": "Niv 1: Lianes",
            "icon": "🌴",
            "file": "level1_7700.bin",
            "start": 0x7700,
            "end": 0x9700,
            "prefix": "L1",
            "desc": "Premier stage : physique d'oscillation angulaire des lianes ($7800), accrochage et balancement de Dudley ($7900), esquive des singes ($7B3E) et détection de chute dans le ravin ($7B9F).",
            "badge": "Overlay Niveau 1",
            "color": "#22c55e"
        },
        {
            "id": "l2",
            "title": "Niveau 2 : La Rivière aux Crocodiles ($7700 - $A6FF)",
            "short": "Niv 2: Crocos",
            "icon": "🐊",
            "file": "level2_7700.bin",
            "start": 0x7700,
            "end": 0xA700,
            "prefix": "L2",
            "desc": "Deuxième stage : physique de plongée sous-marine ($7730), décompte de la jauge d'oxygène ($7E10), bancs de crocodiles ($7900), coups de couteau ($7B20) et morsures mortelles ($7C50).",
            "badge": "Overlay Niveau 2",
            "color": "#06b6d4"
        },
        {
            "id": "l3",
            "title": "Niveau 3 : La Pente aux Rochers ($7700 - $96FF)",
            "short": "Niv 3: Rochers",
            "icon": "🪨",
            "file": "level3_7700.bin",
            "start": 0x7700,
            "end": 0x9700,
            "prefix": "L3",
            "desc": "Troisième stage : ascension de la colline ($7740), physique parabolique des gros rochers rebondissants ($78A0), roulement des petits rochers ($7960), contrôles saut/accroupissement ($7A50) et collision ($7C80).",
            "badge": "Overlay Niveau 3",
            "color": "#eab308"
        },
        {
            "id": "l4",
            "title": "Niveau 4 : Le Village Cannibale & La Marmite ($7700 - $96FF)",
            "short": "Niv 4: Cannibales",
            "icon": "🏺",
            "file": "level4_7700.bin",
            "start": 0x7700,
            "end": 0x9700,
            "prefix": "L4",
            "desc": "Quatrième stage final : rondes des cannibales armés de lances ($7820), animation de la demoiselle suspendue au-dessus de la marmite ($7920), coup de lance ($7B60) et grand saut de victoire ($7DF0).",
            "badge": "Overlay Niveau 4",
            "color": "#ef4444"
        }
    ]

    # Collecte des points d'entrée connus
    known_eps_global = set(SEMANTIC_LABELS.keys())
    for lvl_dict in LEVEL_LABELS.values():
        known_eps_global.update(lvl_dict.keys())
    for doc_k in ROUTINE_DOCS.keys():
        if isinstance(doc_k, int):
            known_eps_global.add(doc_k)
        elif isinstance(doc_k, str) and "_" in doc_k:
            try:
                known_eps_global.add(int(doc_k.split("_")[1], 16))
            except ValueError:
                pass
    known_eps_global.update(SPRITE_TRIGGERS.values())
    known_eps_global.add(0x8C00)

    all_modules_data = []

    for mod in modules_config:
        fpath = os.path.join(bin_dir, mod["file"])
        with open(fpath, "rb") as f:
            raw_data = f.read()

        if mod["end"]:
            raw_data = raw_data[:mod["end"] - mod["start"]]

        print(f"[*] Traitement de {mod['title']} ({len(raw_data):,} octets)...")

        # Collecte des points d'entrée spécifiques à ce module uniquement (évite les collisions d'adresses entre niveaux)
        mod_eps = set()
        if mod["id"] == "main":
            mod_eps.update(k for k in SEMANTIC_LABELS.keys() if 0x0A00 <= k < 0x2000)
        elif mod["id"] == "gfx":
            mod_eps.update(k for k in SEMANTIC_LABELS.keys() if 0x6000 <= k < 0x7700)
        elif mod["id"] in LEVEL_LABELS:
            mod_eps.update(LEVEL_LABELS[mod["id"]].keys())
        if mod["id"] in SPRITE_TRIGGERS:
            mod_eps.add(SPRITE_TRIGGERS[mod["id"]])

        # Désassemblage intelligent avec points d'entrée locaux
        ranges = MODULE_DATA_RANGES.get(mod["id"], [])
        instrs = smart_disasm(raw_data, mod["start"], mod_eps, mod["prefix"], ranges)

        # Collecte des XREFs locales
        mod_xrefs = {}
        for inst in instrs:
            t = inst["target"]
            if t is not None and mod["start"] <= t < mod["start"] + len(raw_data):
                mod_xrefs.setdefault(t, set()).add(inst["addr"])

        all_modules_data.append({
            "config": mod,
            "instructions": instrs,
            "xrefs": mod_xrefs
        })

    # =========================================================================
    # PRODUCTION DU DOCUMENT HTML
    # =========================================================================
    print("[*] Assemblage du document HTML interactif unifié...")

    h = []
    h.append("""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Jungle Hunt (Apple II) - Reverse Engineering Intégral Multi-Niveaux</title>
  <style>
    :root {
      --bg-main: #0a0e14;
      --bg-sidebar: #12171f;
      --bg-card: #181f2a;
      --border-color: #273344;
      --border-accent: #38bdf8;
      --text-main: #e2e8f0;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      
      --c-addr: #38bdf8;
      --c-bytes: #64748b;
      --c-label: #f59e0b;
      --c-jump: #f97316;
      --c-branch: #60a5fa;
      --c-load: #4ade80;
      --c-store: #86efac;
      --c-compare: #c084fc;
      --c-math: #f87171;
      --c-stack: #fbbf24;
      --c-comment: #34d399;
      --c-cheat: #fb923c;
      --c-hw: #ec4899;
      --active-line: #1e3a8a55;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg-main);
      color: var(--text-main);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }

    /* SIDEBAR */
    #sidebar {
      width: 380px;
      min-width: 340px;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      height: 100vh;
    }

    .sidebar-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-color);
      background: #0d1219;
    }

    .sidebar-header h1 {
      font-size: 1.15rem;
      font-weight: 800;
      color: #38bdf8;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .sidebar-header .subtitle {
      font-size: 0.78rem;
      color: var(--text-muted);
    }

    .search-box {
      padding: 10px 16px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      gap: 6px;
      background: #10151d;
    }

    .search-row { display: flex; gap: 6px; }

    .search-input {
      flex: 1;
      background: #0a0e14;
      border: 1px solid var(--border-color);
      color: #fff;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-family: monospace;
    }

    .search-input:focus { outline: none; border-color: #38bdf8; }

    .btn {
      background: #1e293b;
      color: #e2e8f0;
      border: 1px solid var(--border-color);
      padding: 6px 10px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.82rem;
      font-weight: 600;
      transition: all 0.15s;
    }

    .btn:hover { background: #334155; color: #fff; }
    .btn-primary { background: #0284c7; border-color: #0369a1; color: #fff; }
    .btn-primary:hover { background: #0369a1; }

    .quick-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      padding: 8px 16px;
      border-bottom: 1px solid var(--border-color);
      background: #0f141c;
    }

    .chip {
      font-size: 0.72rem;
      background: #1e293b;
      color: #94a3b8;
      padding: 2px 7px;
      border-radius: 10px;
      text-decoration: none;
      border: 1px solid #334155;
      font-weight: 600;
      cursor: pointer;
    }

    .chip:hover { background: #38bdf822; color: #38bdf8; border-color: #38bdf8; }
    .chip.cheat { color: #fb923c; border-color: #c2410c; background: #431407; }

    .sidebar-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 10px 14px;
    }

    .section-title {
      font-size: 0.72rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #38bdf8;
      margin: 14px 0 6px 0;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .toc-item {
      display: flex;
      align-items: center;
      padding: 4px 8px;
      color: #cbd5e1;
      text-decoration: none;
      font-size: 0.8rem;
      border-radius: 4px;
      margin-bottom: 1px;
      transition: background 0.1s;
    }

    .toc-item:hover { background: #1e293b; color: #38bdf8; }
    .toc-item span.addr {
      font-family: monospace;
      color: #38bdf8;
      font-weight: 700;
      width: 54px;
      flex-shrink: 0;
    }

    /* MAIN VIEW */
    #main {
      flex: 1;
      height: 100vh;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      position: relative;
    }

    .main-header {
      position: sticky;
      top: 0;
      z-index: 100;
      background: #0d1219f2;
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--border-color);
      padding: 8px 20px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .main-header-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .main-header-title {
      font-size: 0.95rem;
      font-weight: 800;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* LEVEL SELECTOR TABS */
    .level-tabs {
      display: flex;
      align-items: center;
      gap: 6px;
      overflow-x: auto;
      padding-bottom: 2px;
    }

    .level-tab {
      background: #1e293b;
      color: #94a3b8;
      border: 1px solid #334155;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
    }

    .level-tab:hover { background: #334155; color: #fff; }
    .level-tab.active {
      background: #0284c7;
      color: #fff;
      border-color: #38bdf8;
      box-shadow: 0 0 10px #0284c755;
    }

    /* NAV CONTROLS & BREADCRUMBS */
    .nav-controls {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .nav-btn {
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid #334155;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
    }

    .nav-btn:hover:not(:disabled) {
      background: #38bdf822;
      color: #38bdf8;
      border-color: #38bdf8;
    }

    .nav-btn:disabled { opacity: 0.35; cursor: not-allowed; }

    .nav-history-trail {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.76rem;
      font-family: monospace;
      overflow-x: auto;
      max-width: 320px;
    }

    .trail-item {
      color: #38bdf8;
      background: #1e293b;
      border: 1px solid #334155;
      padding: 2px 6px;
      border-radius: 4px;
      cursor: pointer;
      text-decoration: none;
    }

    .trail-item:hover { background: #38bdf8; color: #0f172a; }
    .trail-item.current { color: #fbbf24; border-color: #f59e0b; font-weight: bold; }

    /* FLOATING RETURN TOAST */
    #return-toast {
      position: fixed;
      bottom: 24px;
      right: 32px;
      z-index: 1000;
      background: #1e293b;
      border: 1px solid #38bdf8;
      box-shadow: 0 8px 24px rgba(0,0,0,0.6);
      border-radius: 8px;
      padding: 9px 15px;
      display: none;
      align-items: center;
      gap: 10px;
      color: #f1f5f9;
      font-size: 0.85rem;
      font-weight: 600;
      animation: slideUp 0.2s ease-out;
    }

    #return-toast button#return-toast-btn {
      background: #0284c7;
      border: none;
      color: #fff;
      padding: 5px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 700;
      font-size: 0.82rem;
    }

    #return-toast button#return-toast-btn:hover { background: #0369a1; }

    @keyframes slideUp {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    .code-container {
      padding: 16px 24px 100px 24px;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 13px;
      line-height: 1.6;
    }

    /* MODULE HERO BANNER */
    .module-banner {
      margin: 36px 0 16px 0;
      background: linear-gradient(135deg, #111827 0%, #1e293b 100%);
      border: 1px solid var(--border-color);
      border-left: 6px solid var(--border-accent);
      border-radius: 8px;
      padding: 16px 20px;
      box-shadow: 0 6px 20px rgba(0,0,0,0.4);
      scroll-margin-top: 110px;
    }

    .module-banner-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .module-banner-title {
      font-size: 1.15rem;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .module-banner-badge {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      padding: 3px 10px;
      border-radius: 12px;
      background: #0284c722;
      color: #38bdf8;
      border: 1px solid #0284c7;
    }

    .module-banner-desc {
      color: #cbd5e1;
      font-size: 0.86rem;
      line-height: 1.5;
    }

    /* ROUTINE DOC-CARD */
    .routine-card {
      margin: 22px 0 10px 0;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-left: 4px solid #38bdf8;
      border-radius: 8px;
      padding: 14px 18px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      scroll-margin-top: 100px;
    }

    .routine-card.cheat { border-left-color: #f97316; }

    .routine-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .routine-card-name {
      font-size: 0.95rem;
      font-weight: 800;
      color: #f8fafc;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .routine-card-badge {
      font-size: 0.7rem;
      font-weight: 700;
      background: #0369a1;
      color: #fff;
      padding: 2px 8px;
      border-radius: 12px;
      font-family: monospace;
    }

    .routine-card.cheat .routine-card-badge { background: #c2410c; }

    .routine-desc {
      color: #cbd5e1;
      font-size: 0.85rem;
      line-height: 1.5;
      margin-bottom: 8px;
    }

    .routine-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      font-size: 0.78rem;
      background: #0f141d;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid #243042;
    }

    .routine-grid-item span.label { color: #94a3b8; font-weight: 600; margin-right: 4px; }
    .routine-grid-item span.val { color: #e2e8f0; }

    .cheat-box {
      margin-top: 8px;
      background: #431407;
      border: 1px solid #9a3412;
      color: #fdba74;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
    }

    /* LIGNES DE CODE */
    .code-line {
      display: flex;
      align-items: baseline;
      padding: 1px 8px;
      border-radius: 4px;
      margin-bottom: 1px;
      scroll-margin-top: 100px;
      transition: background 0.1s;
    }

    .code-line:hover { background: #16202e; }
    .code-line.active {
      background: var(--active-line) !important;
      border-left: 3px solid #38bdf8 !important;
      animation: linePulse 1.2s ease-out;
    }

    @keyframes linePulse {
      0% { background: rgba(56, 189, 248, 0.5) !important; box-shadow: 0 0 15px rgba(56, 189, 248, 0.4); }
      100% { background: var(--active-line) !important; box-shadow: none; }
    }

    .label-line {
      margin-top: 12px;
      margin-bottom: 3px;
      padding: 3px 8px;
      background: #16202f;
      border-left: 3px solid #f59e0b;
      border-radius: 0 4px 4px 0;
      color: #fbbf24;
      font-weight: 700;
      font-size: 0.9rem;
    }

    .line-addr {
      width: 70px;
      color: var(--c-addr);
      font-weight: 700;
      user-select: none;
    }

    .line-bytes {
      width: 95px;
      color: var(--c-bytes);
      user-select: none;
    }

    .line-mnemonic {
      width: 55px;
      font-weight: 700;
    }

    .line-operand {
      width: 160px;
      color: #f1f5f9;
    }

    .target-link {
      color: #38bdf8;
      text-decoration: none;
      border-bottom: 1px dotted #0284c7;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.15s ease;
    }

    .target-link:hover {
      color: #ffffff;
      border-bottom: 1px solid #38bdf8;
      text-shadow: 0 0 8px rgba(56, 189, 248, 0.7);
    }

    .vec-resolved {
      color: #4ade80;
      font-weight: 700;
      margin-left: 4px;
    }

    .xrefs-tag {
      margin-left: 10px;
      font-size: 0.74rem;
      color: var(--text-dim);
    }

    .xref-link {
      color: #c084fc;
      text-decoration: none;
      cursor: pointer;
    }

    .xref-link:hover { text-decoration: underline; }

    .line-comment {
      color: var(--c-comment);
      margin-left: 16px;
      white-space: pre-wrap;
    }

    .line-comment.hw { color: var(--c-hw); font-weight: 600; }
    .line-comment.cheat {
      color: #fdba74;
      background: #431407;
      padding: 1px 6px;
      border-radius: 4px;
      border: 1px solid #9a3412;
      font-weight: 700;
    }

    
    /* DATA LINE & DATA BLOCK BANNER */
    .data-block-banner {
      margin: 22px 0 8px 0;
      padding: 8px 16px;
      background: linear-gradient(90deg, rgba(30, 41, 59, 0.85) 0%, rgba(15, 23, 42, 0.6) 100%);
      border-left: 4px solid #38bdf8;
      border-radius: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }

    .data-block-title {
      font-size: 0.88rem;
      font-weight: 700;
      color: #f1f5f9;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .data-block-badge {
      font-size: 0.72rem;
      color: #94a3b8;
      background: #0f172a;
      border: 1px solid #334155;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      font-weight: 600;
    }

    .code-line.data-line {
      background: rgba(15, 23, 42, 0.25);
      border-left: 2px solid #334155;
    }

    .code-line.data-line:hover {
      background: rgba(30, 41, 59, 0.45);
    }

    .line-bytes.data-bytes {
      color: #64748b;
      font-weight: normal;
    }

    .line-mnemonic.data-mnem {
      color: #c084fc;
      font-weight: 700;
    }

    .line-operand.data-op {
      color: #94a3b8;
      font-family: monospace;
    }

    .line-comment.data-comment {
      color: #64748b;
      font-style: italic;
    }

    /* SPRITE VIS-À-VIS DUAL-PANEL GRID */
    .sprite-visavis-grid {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 20px;
      align-items: start;
      margin-top: 14px;
    }

    @media (max-width: 900px) {
      .sprite-visavis-grid { grid-template-columns: 1fr; }
    }

    .sprite-visavis-col-left {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }

    .sprite-screen-frame {
      background: #020605;
      padding: 14px;
      border-radius: 8px;
      border: 2px solid #064e3b;
      box-shadow: 0 0 20px rgba(16, 185, 129, 0.15), inset 0 0 15px rgba(0, 0, 0, 0.9);
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 180px;
      width: 100%;
      box-sizing: border-box;
    }

    .sprite-canvas {
      image-rendering: pixelated;
      border-radius: 4px;
      display: block;
    }

    .sprite-screen-legend {
      font-size: 0.74rem;
      color: #6ee7b7;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .crt-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #34d399;
      box-shadow: 0 0 6px #34d399;
      display: inline-block;
    }

    .sprite-visavis-col-right {
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-width: 0;
    }

    .sprite-meta-box {
      background: #09131a;
      border: 1px solid #1e293b;
      border-radius: 6px;
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .sprite-meta-row {
      display: flex;
      align-items: baseline;
      gap: 8px;
      font-size: 0.85rem;
    }

    .meta-label {
      color: #94a3b8;
      font-weight: 600;
      min-width: 110px;
    }

    .meta-val {
      color: #f1f5f9;
    }

    .meta-badge-addr {
      background: #1e1b4b;
      color: #a5b4fc;
      border: 1px solid #4338ca;
      padding: 2px 8px;
      border-radius: 4px;
      font-family: monospace;
      font-weight: 700;
      font-size: 0.82rem;
    }

    .sprite-hex-section {
      background: #020617;
      border: 1px solid #1e293b;
      border-radius: 6px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .sprite-hex-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.82rem;
      font-weight: 700;
      color: #38bdf8;
    }

    .btn-jump-disasm {
      background: #0369a1;
      color: #fff;
      border: none;
      border-radius: 4px;
      padding: 4px 12px;
      font-size: 0.75rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .btn-jump-disasm:hover {
      background: #0284c7;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
    }

    .sprite-hex-box {
      background: #030712;
      border: 1px solid #0f172a;
      border-radius: 4px;
      padding: 8px 12px;
      font-family: "SFMono-Regular", Consolas, Menlo, monospace;
      font-size: 0.76rem;
      max-height: 220px;
      overflow-y: auto;
      line-height: 1.5;
    }

    .hex-row {
      display: flex;
      gap: 12px;
      white-space: nowrap;
    }

    .hr-num { color: #64748b; min-width: 28px; }
    .hr-addr { color: #818cf8; min-width: 54px; font-weight: 600; }
    .hr-hex { color: #f8fafc; min-width: 140px; }
    .hr-ascii { color: #34d399; font-weight: 700; letter-spacing: 1px; }

    /* BRANCH PILLS & VISUAL FLOW */
    .branch-pill {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-family: monospace;
      font-weight: 700;
      margin-left: 8px;
      cursor: pointer;
      transition: all 0.15s ease;
      user-select: none;
    }

    .branch-pill.loop {
      background: #450a0a;
      border: 1px solid #dc2626;
      color: #fca5a5;
    }

    .branch-pill.loop:hover {
      background: #dc2626;
      color: #fff;
      box-shadow: 0 0 8px #dc2626aa;
    }

    .branch-pill.fwd {
      background: #172554;
      border: 1px solid #2563eb;
      color: #93c5fd;
    }

    .branch-pill.fwd:hover {
      background: #2563eb;
      color: #fff;
      box-shadow: 0 0 8px #2563ebaa;
    }

    .branch-target-highlight {
      outline: 2px solid #f59e0b !important;
      box-shadow: 0 0 16px #f59e0b99 !important;
      background: #78350f44 !important;
    }

    /* SPRITE SHAPE GALLERY CARD */
    .sprite-gallery-card {
      margin: 24px 0 16px 0;
      background: #0f172a;
      border: 1px solid #38bdf8;
      border-left: 6px solid #38bdf8;
      border-radius: 8px;
      padding: 16px 20px;
      box-shadow: 0 6px 24px rgba(0,0,0,0.5);
      scroll-margin-top: 110px;
    }

    .sprite-gallery-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .sprite-gallery-title {
      font-size: 1.05rem;
      font-weight: 800;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .sprite-gallery-badge {
      font-size: 0.72rem;
      font-weight: 700;
      background: #0369a1;
      color: #fff;
      padding: 2px 8px;
      border-radius: 12px;
      font-family: monospace;
    }

    .sprite-gallery-desc {
      color: #94a3b8;
      font-size: 0.82rem;
      margin-bottom: 12px;
      line-height: 1.4;
    }

    .sprite-gallery-tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 12px;
    }

    .sprite-tab-btn {
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid #334155;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.76rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
    }

    .sprite-tab-btn:hover { background: #334155; color: #fff; }
    .sprite-tab-btn.active {
      background: #0284c7;
      color: #fff;
      border-color: #38bdf8;
      box-shadow: 0 0 8px #0284c766;
    }

    .sprite-canvas-container {
      display: flex;
      align-items: center;
      gap: 20px;
      background: #090d14;
      padding: 12px 16px;
      border-radius: 6px;
      border: 1px solid #1e293b;
    }

    .sprite-screen-frame {
      background: #000;
      border: 2px solid #334155;
      border-radius: 4px;
      padding: 6px;
      box-shadow: inset 0 0 10px #000;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .sprite-canvas {
      image-rendering: pixelated;
      background: #000;
    }

    .sprite-details {
      font-size: 0.8rem;
      color: #cbd5e1;
      line-height: 1.6;
    }

    .sprite-details strong { color: #38bdf8; }

    /* SYNTAX HIGHLIGHTING */
    .flow-jump { color: var(--c-jump); }
    .flow-branch { color: var(--c-branch); }
    .flow-ret { color: #f43f5e; font-weight: 800; }
    .load { color: var(--c-load); }
    .store { color: var(--c-store); }
    .compare { color: var(--c-compare); }
    .math { color: var(--c-math); }
    .stack { color: var(--c-stack); }
    .flag { color: #eab308; }
    .unknown { color: #64748b; }
  </style>
</head>
<body>

  <!-- SIDEBAR NAVIGATION -->
  <aside id="sidebar">
    <div class="sidebar-header">
      <h1>🎮 Jungle Hunt Reverse</h1>
      <div class="subtitle">Architecture 6502, Moteur & 4 Overlays de Niveaux</div>
    </div>

    <!-- Quick Jump & Search -->
    <div class="search-box">
      <div class="search-row">
        <input type="text" id="jump-input" class="search-input" placeholder="Adresse hex (ex: 0A76, 6000, 7B3E)..." maxlength="8">
        <button class="btn btn-primary" onclick="jumpToAddress()">Aller</button>
      </div>
      <div class="search-row">
        <input type="text" id="filter-input" class="search-input" placeholder="Filtrer code, opcodes, étiquettes..." oninput="filterCode()">
        <button class="btn" onclick="clearFilter()">Reset</button>
      </div>
    </div>

    <!-- Quick Chips -->
    <div class="quick-chips">
      <a class="chip" href="#0A76" onclick="handleLinkClick(event, null, '0A76')">Boucle ($0A76)</a>
      <a class="chip" href="#6000" onclick="handleLinkClick(event, null, '6000')">Hi-Res ($6000)</a>
      <a class="chip" href="#L1_7700" onclick="handleLinkClick(event, null, 'L1_7700')">Niv 1 Lianes</a>
      <a class="chip" href="#L2_7700" onclick="handleLinkClick(event, null, 'L2_7700')">Niv 2 Crocos</a>
      <a class="chip" href="#L3_7700" onclick="handleLinkClick(event, null, 'L3_7700')">Niv 3 Rochers</a>
      <a class="chip" href="#L4_7700" onclick="handleLinkClick(event, null, 'L4_7700')">Niv 4 Cannibales</a>
      <a class="chip cheat" href="#0D79" onclick="handleLinkClick(event, null, '0D79')">Cheat Timer</a>
      <a class="chip cheat" href="#L1_7BD3" onclick="handleLinkClick(event, null, 'L1_7BD3')">Cheat Vies</a>
    </div>

    <!-- Table of Contents -->
    <div class="sidebar-scroll">
""")

    # Sommaire dans la sidebar
    for mod_data in all_modules_data:
        cfg = mod_data["config"]
        pfx = cfg["prefix"]
        hero_id = f"HERO_{cfg['id']}"
        h.append(f"""      <div class="section-title">{cfg['icon']} {cfg['title']}</div>""")
        h.append(f"""      <a class="toc-item" href="#{hero_id}" onclick="handleLinkClick(event, null, '{hero_id}')">
        <span class="addr">${cfg['start']:04X}</span> <strong>Présentation du Module</strong>
      </a>""")

        # Liste des routines de ce module
        for r_addr, r_info in sorted(ROUTINE_DOCS.items(), key=lambda x: str(x[0])):
            # Vérifie si la routine appartient à ce module
            match_mod = False
            target_id = ""
            lbl_name = ""

            if cfg["id"] == "main" and isinstance(r_addr, int) and 0x0A00 <= r_addr < 0x2000:
                match_mod = True
                target_id = f"{r_addr:04X}"
                lbl_name = SEMANTIC_LABELS.get(r_addr, f"{r_addr:04X}")
            elif cfg["id"] == "gfx" and isinstance(r_addr, int) and 0x6000 <= r_addr < 0x7700:
                match_mod = True
                target_id = f"{r_addr:04X}"
                lbl_name = SEMANTIC_LABELS.get(r_addr, f"{r_addr:04X}")
            elif cfg["prefix"] and isinstance(r_addr, str) and r_addr.startswith(cfg["prefix"] + "_"):
                match_mod = True
                target_id = r_addr
                raw_hex = int(r_addr.split("_")[1], 16)
                lbl_name = LEVEL_LABELS.get(cfg["id"], {}).get(raw_hex, r_addr)

            if match_mod:
                h.append(f"""      <a class="toc-item" href="#{target_id}" onclick="handleLinkClick(event, null, '{target_id}')">
        <span class="addr">${target_id.replace(pfx + '_', '') if pfx else target_id}</span> {lbl_name}
      </a>""")

    h.append("""    </div>
  </aside>

  <!-- MAIN VIEW -->
  <main id="main">
    <div class="main-header">
      <div class="main-header-top">
        <div class="main-header-title">
          <span>🎮 Jungle Hunt (Apple II) - Reverse Engineering Intégral</span>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
          <div class="nav-controls">
            <button id="btn-nav-back" class="nav-btn" onclick="navBack()" title="Revenir en arrière (Alt + ←)" disabled>⬅️ Retour</button>
            <button id="btn-nav-fwd" class="nav-btn" onclick="navForward()" title="Aller vers l'avant (Alt + →)" disabled>Suivant ➡️</button>
          </div>
          <button id="btn-toggle-branches" class="nav-btn" onclick="toggleBranchHighlight()" title="Mettre en surbrillance toutes les boucles et sauts">🔀 Sauts & Boucles</button>
          <div id="nav-trail" class="nav-history-trail" title="Historique de vos déplacements"></div>
        </div>
      </div>

      <!-- SÉLECTEUR DE NIVEAUX INTERACTIF -->
      <div class="level-tabs">
        <button class="level-tab active" id="tab-all" onclick="switchLevelView('all')">🌐 Tous les Modules</button>
        <button class="level-tab" id="tab-main" onclick="switchLevelView('main')">🕹️ Moteur ($0A00-$1EFF)</button>
        <button class="level-tab" id="tab-gfx" onclick="switchLevelView('gfx')">🎨 Graphismes & Sons ($6000)</button>
        <button class="level-tab" id="tab-l1" onclick="switchLevelView('l1')">🌴 Niveau 1 : Lianes ($7700)</button>
        <button class="level-tab" id="tab-l2" onclick="switchLevelView('l2')">🐊 Niveau 2 : Crocodiles ($7700)</button>
        <button class="level-tab" id="tab-l3" onclick="switchLevelView('l3')">🪨 Niveau 3 : Rochers ($7700)</button>
        <button class="level-tab" id="tab-l4" onclick="switchLevelView('l4')">🏺 Niveau 4 : Cannibales ($7700)</button>
      </div>
    </div>

    <!-- FLOATING RETURN TOAST -->
    <div id="return-toast">
      <span id="return-toast-text"></span>
      <button id="return-toast-btn">↩ Revenir</button>
      <button style="background:transparent; border:none; color:#94a3b8; cursor:pointer; font-size:1.1rem; padding-left:4px;" onclick="closeReturnToast()">✕</button>
    </div>

    <div class="code-container" id="code-container">
""")

    # Génération du code pour chaque module
    for mod_data in all_modules_data:
        cfg = mod_data["config"]
        instrs = mod_data["instructions"]
        xrefs = mod_data["xrefs"]
        pfx = cfg["prefix"]
        mod_id = cfg["id"]

        # Hero Banner du module
        hero_id = f"HERO_{mod_id}"
        h.append(f"""
      <!-- MODULE CONTAINER : {cfg['title']} -->
      <div class="module-block" id="MOD_BLOCK_{mod_id}" data-module="{mod_id}">
        <div class="module-banner" id="{hero_id}" style="border-left-color: {cfg['color']};">
          <div class="module-banner-header">
            <div class="module-banner-title">{cfg['icon']} {cfg['title']}</div>
            <span class="module-banner-badge" style="border-color: {cfg['color']}; color: {cfg['color']};">{cfg['badge']}</span>
          </div>
          <div class="module-banner-desc">{cfg['desc']}</div>
        </div>
""")

        # Instructions du module
        for instr in instrs:
            addr = instr["addr"]
            dom_id = instr["dom_id"]
            addr_hex = f"{addr:04X}"
            hex_bytes = " ".join(f"{b:02X}" for b in instr["bytes"])

            # 0. Insertion de la bannière de bloc de données si début de table
            if instr.get("data_banner"):
                h.append(f"""
        <div class="data-block-banner" id="BANNER_{dom_id}">
          <div class="data-block-title">📦 {instr['data_banner']} (${addr:04X})</div>
          <span class="data-block-badge">Table de Données &amp; Octets Bruts (Non-Exécutable)</span>
        </div>""")

            # Insertion de la galerie de sprites au point d'ancrage graphique
            if mod_id in ALL_SPRITES and addr == SPRITE_TRIGGERS.get(mod_id):
                spr_dict = ALL_SPRITES[mod_id]
                first_spr_key = list(spr_dict.keys())[0]
                first_spr = spr_dict[first_spr_key]
                btn_parts = []
                for s_key, s_data in spr_dict.items():
                    active_cls = " active" if s_key == first_spr_key else ""
                    btn_parts.append(f'<button class="sprite-tab-btn{active_cls}" data-sprite-id="{s_key}" onclick="selectSprite(\'{mod_id}\', \'{s_key}\')">{s_data["name"]}</button>')
                tab_btns = "".join(btn_parts)
                first_end_addr = first_spr['addr_num'] + first_spr['size_bytes'] - 1

                h.append(f"""
        <div class="sprite-gallery-card" id="SPRITES_{mod_id}">
          <div class="sprite-gallery-header">
            <div class="sprite-gallery-title">🖼️ Galerie Interactive des Sprites Hi-Res &amp; Correspondance Hexadécimale</div>
            <span class="sprite-gallery-badge">{cfg['short']} • Rendu Authentique Apple II</span>
          </div>
          <div class="sprite-gallery-desc">
            Sprites décodés fidèlement depuis la mémoire ROM du niveau : chaque forme est affichée en <strong>vis-à-vis direct avec sa plage mémoire et son listing d'octets hexadécimaux</strong>.
          </div>
          <div class="sprite-gallery-tabs" id="tabs-{mod_id}">{tab_btns}</div>
          
          <div class="sprite-visavis-grid">
            <!-- COLONNE GAUCHE : ÉCRAN CRT PHOSPHORE VERT -->
            <div class="sprite-visavis-col-left">
              <div class="sprite-screen-frame">
                <canvas id="canvas-{mod_id}" class="sprite-canvas"></canvas>
              </div>
              <div class="sprite-screen-legend">
                <span class="crt-dot"></span> Affichage CRT Phosphore Vert Hi-Res (280×192)
              </div>
            </div>
            
            <!-- COLONNE DROITE : VIS-À-VIS DES OCTETS BRUTS & MÉTADONNÉES -->
            <div class="sprite-visavis-col-right">
              <div class="sprite-meta-box">
                <div class="sprite-meta-row">
                  <span class="meta-label">Entité :</span>
                  <strong class="meta-val" id="lbl-name-{mod_id}">{first_spr['name']}</strong>
                </div>
                <div class="sprite-meta-row">
                  <span class="meta-label">Plage Mémoire :</span>
                  <span class="meta-badge-addr" id="lbl-range-{mod_id}">{first_spr['addr']} - ${first_end_addr:04X} ({first_spr['size_bytes']} octets)</span>
                </div>
                <div class="sprite-meta-row">
                  <span class="meta-label">Dimensions :</span>
                  <span class="meta-val" id="lbl-dims-{mod_id}">{first_spr['width_px']} × {first_spr['height']} pixels ({first_spr['width_bytes']} octets/ligne)</span>
                </div>
                <div class="sprite-meta-row">
                  <span class="meta-label">Rôle :</span>
                  <span class="meta-val" id="lbl-desc-{mod_id}" style="color:#cbd5e1;">{first_spr['desc']}</span>
                </div>
              </div>
              
              <!-- TABLEAU DES OCTETS EN VIS-À-VIS -->
              <div class="sprite-hex-section">
                <div class="sprite-hex-title">
                  <span>📄 Octets Hexadécimaux Source (Ligne par Ligne)</span>
                  <button class="btn-jump-disasm" id="btn-jump-{mod_id}" onclick="jumpTo(currentSprAddr['{mod_id}'], true)">
                    🔍 Aller à {first_spr['addr']} dans le listing
                  </button>
                </div>
                <div class="sprite-hex-box" id="hex-box-{mod_id}">
                  <!-- Rempli dynamiquement en JS par selectSprite -->
                </div>
              </div>
            </div>
          </div>
        </div>""")

            # Si c'est un paquet de DONNÉES PURES (non exécutable)
            if not instr["is_code"]:
                comment_text = DETAILED_LINE_COMMENTS.get(dom_id, "") or DETAILED_LINE_COMMENTS.get(addr, "")
                comment_html = f'<span class="line-comment data-comment">; {comment_text}</span>' if comment_text else ""
                h.append(f"""        <div class="code-line data-line" id="{dom_id}" data-addr="{addr_hex}" data-module="{mod_id}">
          <span class="line-addr"><a href="#{dom_id}" style="color:inherit; text-decoration:none;" onclick="handleLinkClick(event, null, '{dom_id}')">{addr_hex}:</a></span>
          <span class="line-bytes data-bytes">{hex_bytes}</span>
          <span class="line-mnemonic data-mnem">.byte</span>
          <span class="line-operand data-op">{instr["operand"]}</span>
          {comment_html}
        </div>""")
                continue

            # 1. Insertion Doc-Card si début de routine majeure
            doc_key_int = addr
            doc_key_str = dom_id
            doc = ROUTINE_DOCS.get(doc_key_str) or (ROUTINE_DOCS.get(doc_key_int) if not pfx else None)

            if doc:
                lbl = LEVEL_LABELS.get(mod_id, {}).get(addr) or SEMANTIC_LABELS.get(addr, f"ROUTINE_{addr_hex}")
                cheat_badge = '<span class="routine-card-badge">POINT DE TRICHE</span>' if doc["cheat"] else '<span class="routine-card-badge">ROUTINE / API</span>'
                cheat_html = f'<div class="cheat-box">🔥 {doc["cheat"]}</div>' if doc["cheat"] else ''
                card_class = "routine-card cheat" if doc["cheat"] else "routine-card"

                h.append(f"""
        <div class="{card_class}" id="DOC_{dom_id}">
          <div class="routine-card-header">
            <div class="routine-card-name">📌 {lbl} (${addr_hex})</div>
            {cheat_badge}
          </div>
          <div class="routine-desc">{doc["role"]}</div>
          <div class="routine-grid">
            <div class="routine-grid-item"><span class="label">Entrées :</span><span class="val">{doc["inputs"]}</span></div>
            <div class="routine-grid-item"><span class="label">Sorties :</span><span class="val">{doc["outputs"]}</span></div>
            <div class="routine-grid-item"><span class="label">Gameplay :</span><span class="val">{doc["gameplay"]}</span></div>
            <div class="routine-grid-item"><span class="label">Adresse :</span><span class="val">${addr_hex} ({cfg['short']})</span></div>
          </div>
          {cheat_html}
        </div>""")

            # 2. Entête d'étiquette sémantique
            lbl_name = LEVEL_LABELS.get(mod_id, {}).get(addr) or (SEMANTIC_LABELS.get(addr) if not pfx else None)
            if not lbl_name and addr in xrefs:
                lbl_name = f"{pfx + '_' if pfx else ''}STEP_{addr_hex}"

            if lbl_name and not doc:
                callers = xrefs.get(addr, set())
                c_links = ", ".join(f'<a class="xref-link" href="#{pfx + "_" if pfx else ""}{c:04X}" onclick="handleLinkClick(event, \'{dom_id}\', \'{pfx + "_" if pfx else ""}{c:04X}\')">${c:04X}</a>' for c in sorted(callers)[:6])
                caller_str = f" <span style='font-size:0.75rem; font-weight:normal; color:#94a3b8;'>(Appelé par: {c_links})</span>" if c_links else ""
                h.append(f"""        <div class="label-line">{lbl_name}:{caller_str}</div>""")

            # 3. Traitement de l'opérande et liens hypertextes
            op_html = instr["operand"]
            target = instr["target"]

            if target is not None:
                target_hex = f"{target:04X}"
                target_id = None

                # A. Cible dans le module courant
                if cfg["start"] <= target < cfg["end"]:
                    target_id = f"{pfx}_{target_hex}" if pfx else target_hex
                # B. Cible dans le Moteur Résident ($0A00 - $1EFF)
                elif 0x0A00 <= target < 0x1F00:
                    target_id = target_hex
                # C. Cible dans la Bibliothèque GFX & Audio ($6000 - $76FF)
                elif 0x6000 <= target < 0x7700:
                    target_id = target_hex
                # D. Registres matériels Apple II ($C000 - $CFFF)
                elif target in APPLE2_HARDWARE:
                    hw_sym, _ = APPLE2_HARDWARE[target]
                    op_html += f' <span style="color:var(--c-hw); font-weight:700;">({hw_sym})</span>'

                # Si target_id est déterminé, transformer l'opérande en lien hypertexte cliquable
                if target_id and f"${target_hex}" in op_html:
                    op_html = op_html.replace(f"${target_hex}", f'<a class="target-link" href="#{target_id}" onclick="handleLinkClick(event, \'{dom_id}\', \'{target_id}\')">${target_hex}</a>')

            # 4. Commentaires et annotations
            # Badge visuel pour les branches courts (BEQ, BNE, BCC, BCS, BMI, BPL...)
            branch_badge = ""
            if instr["mode"] == "rel" and target is not None:
                delta = instr.get("delta")
                if delta is not None:
                    target_id = f"{pfx}_{target:04X}" if pfx else f"{target:04X}"
                    if delta < 0:
                        branch_badge = f' <span class="branch-pill loop" data-target="{target_id}" onclick="handleLinkClick(event, \'{dom_id}\', \'{target_id}\')" title="Boucle vers l\'arrière : ${target:04X} ({delta} octets)">⤶ Boucle {delta}o</span>'
                    elif delta > 0:
                        branch_badge = f' <span class="branch-pill fwd" data-target="{target_id}" onclick="handleLinkClick(event, \'{dom_id}\', \'{target_id}\')" title="Saut conditionnel avant : ${target:04X} (+{delta} octets)">⤷ Saut +{delta}o</span>'
                    else:
                        branch_badge = f' <span class="branch-pill loop" data-target="{target_id}" onclick="handleLinkClick(event, \'{dom_id}\', \'{target_id}\')" title="Boucle infinie sur place">🔄 Sur place</span>'

            comment_text = DETAILED_LINE_COMMENTS.get(dom_id, "") or DETAILED_LINE_COMMENTS.get(addr, "")
            comment_class = "line-comment"

            if not comment_text and target in APPLE2_HARDWARE:
                _, hw_desc = APPLE2_HARDWARE[target]
                comment_text = hw_desc
                comment_class += " hw"
            elif "CHEAT" in comment_text.upper() or "TRICHE" in comment_text.upper():
                comment_class += " cheat"

            comment_html = f'<span class="{comment_class}">; {comment_text}</span>' if comment_text else ""
            cat_class = instr["category"]

            h.append(f"""        <div class="code-line" id="{dom_id}" data-addr="{addr_hex}" data-module="{mod_id}">
          <span class="line-addr"><a href="#{dom_id}" style="color:inherit; text-decoration:none;" onclick="handleLinkClick(event, null, '{dom_id}')">{addr_hex}:</a></span>
          <span class="line-bytes">{hex_bytes:<9}</span>
          <span class="line-mnemonic {cat_class}">{instr["mnemonic"]}</span>
          <span class="line-operand">{op_html}{branch_badge}</span>
          {comment_html}
        </div>""")

        h.append("""      </div><!-- /MODULE CONTAINER -->\n""")

    h.append("""    </div><!-- /code-container -->
  </main>

  <script>
    // --- GESTION DE L'HISTORIQUE DE NAVIGATION ---
    let navHistory = [];
    let navHistoryIndex = -1;
    let lastCallerAddr = null;
    let currentModuleFilter = 'all';

    function switchLevelView(modId, autoScroll = true) {
      currentModuleFilter = modId;
      document.querySelectorAll('.level-tab').forEach(t => t.classList.remove('active'));
      const activeTab = document.getElementById('tab-' + modId);
      if (activeTab) activeTab.classList.add('active');

      const blocks = document.querySelectorAll('.module-block');
      if (modId === 'all') {
        blocks.forEach(b => b.style.display = '');
      } else {
        blocks.forEach(b => {
          b.style.display = (b.dataset.module === modId) ? '' : 'none';
        });
        if (autoScroll) {
          const hero = document.getElementById('HERO_' + modId);
          if (hero) hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    }

    function recordJump(fromAddr, targetAddr) {
      if (fromAddr) {
        lastCallerAddr = fromAddr;
        showReturnToast(fromAddr);
      }
      if (navHistoryIndex >= 0 && navHistory[navHistoryIndex] === targetAddr) return;
      if (navHistoryIndex < navHistory.length - 1) {
        navHistory = navHistory.slice(0, navHistoryIndex + 1);
      }
      navHistory.push(targetAddr);
      navHistoryIndex = navHistory.length - 1;
      updateNavUI();
    }

    function showReturnToast(callerAddr) {
      const toast = document.getElementById('return-toast');
      const textSpan = document.getElementById('return-toast-text');
      const btn = document.getElementById('return-toast-btn');
      if (toast && textSpan) {
        textSpan.innerHTML = `📍 Téléporté depuis <strong>$${callerAddr.replace(/^[A-Z0-9]+_/, '')}</strong>`;
        btn.onclick = () => {
          closeReturnToast();
          jumpTo(callerAddr, true, null);
        };
        toast.style.display = 'flex';
      }
    }

    function closeReturnToast() {
      const toast = document.getElementById('return-toast');
      if (toast) toast.style.display = 'none';
    }

    function updateNavUI() {
      const btnBack = document.getElementById('btn-nav-back');
      const btnFwd = document.getElementById('btn-nav-fwd');
      const trail = document.getElementById('nav-trail');

      if (btnBack) btnBack.disabled = (navHistoryIndex <= 0);
      if (btnFwd) btnFwd.disabled = (navHistoryIndex >= navHistory.length - 1);

      if (trail) {
        let startIdx = Math.max(0, navHistory.length - 4);
        let items = navHistory.slice(startIdx);
        trail.innerHTML = items.map((addr, idx) => {
          let actualIdx = startIdx + idx;
          let isCurrent = (actualIdx === navHistoryIndex);
          let cleanAddr = addr.replace(/^DOC_/, '').replace(/^HERO_/, '');
          return `<span class="trail-item ${isCurrent ? 'current' : ''}" onclick="jumpToHistoryIndex(${actualIdx})">$${cleanAddr}</span>`;
        }).join(' <span style="color:#64748b;">➜</span> ');
      }
    }

    function navBack() {
      if (navHistoryIndex > 0) {
        navHistoryIndex--;
        jumpTo(navHistory[navHistoryIndex], false);
        updateNavUI();
      } else {
        window.history.back();
      }
    }

    function navForward() {
      if (navHistoryIndex < navHistory.length - 1) {
        navHistoryIndex++;
        jumpTo(navHistory[navHistoryIndex], false);
        updateNavUI();
      } else {
        window.history.forward();
      }
    }

    function jumpToHistoryIndex(idx) {
      if (idx >= 0 && idx < navHistory.length) {
        navHistoryIndex = idx;
        jumpTo(navHistory[idx], false);
        updateNavUI();
      }
    }

    function highlightLine(el) {
      document.querySelectorAll('.code-line.active').forEach(e => e.classList.remove('active'));
      if (el) {
        el.classList.add('active');
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    // Recherche robuste d'élément avec support multi-niveaux et fallback
    function resolveElement(target) {
      if (!target) return null;
      let clean = target.replace('#', '').trim();

      // 1. Recherche directe par ID
      let el = document.getElementById(clean) || document.getElementById('DOC_' + clean) || document.getElementById('HERO_' + clean);
      if (el) return el;

      // 2. Recherche avec préfixe de niveau si adresse hex pure (ex: 7700, 7B3E)
      let rawHex = clean.split('_').pop().replace('$', '').toUpperCase();
      if (rawHex.length < 4) rawHex = rawHex.padStart(4, '0');

      // Si un niveau particulier est actif, chercher dans ce niveau en priorité
      if (currentModuleFilter !== 'all') {
        let pfx = currentModuleFilter.toUpperCase();
        let elLvl = document.getElementById(pfx + '_' + rawHex) || document.getElementById('DOC_' + pfx + '_' + rawHex);
        if (elLvl) return elLvl;
      }

      // Parcourir les préfixes possibles
      for (let pfx of ['L1', 'L2', 'L3', 'L4', '']) {
        let testId = pfx ? `${pfx}_${rawHex}` : rawHex;
        let found = document.getElementById(testId) || document.getElementById('DOC_' + testId);
        if (found) return found;
      }

      // 3. Recherche par data-addr exacte
      let exactAddr = document.querySelector(`[data-addr="${rawHex}"]`);
      if (exactAddr) return exactAddr;

      // 4. Fallback vers l'instruction la plus proche précédente (pour les octets de tables/opérandes)
      let targetVal = parseInt(rawHex, 16);
      if (!isNaN(targetVal)) {
        let pfxMatch = clean.includes('_') ? clean.split('_')[0] : (currentModuleFilter !== 'all' ? currentModuleFilter.toUpperCase() : '');
        let selector = pfxMatch ? `.code-line[id^="${pfxMatch}_"]` : '.code-line';
        let lines = document.querySelectorAll(selector);
        let best = null;
        for (let i = 0; i < lines.length; i++) {
          let a = parseInt(lines[i].dataset.addr, 16);
          if (a <= targetVal) {
            best = lines[i];
          } else {
            break;
          }
        }
        if (best) return best;
      }

      return null;
    }

    function jumpTo(target, addToHistory = true, fromAddr = null) {
      if (!target) return;
      const el = resolveElement(target);

      if (el) {
        // Détecter le module parent
        const parentMod = el.closest('.module-block');
        if (parentMod) {
          const modId = parentMod.dataset.module;
          // Si le module cible est masqué par le filtre d'onglets, basculer sur ce module sans écraser le scroll
          if (currentModuleFilter !== 'all' && currentModuleFilter !== modId) {
            switchLevelView(modId, false);
          } else if (parentMod.style.display === 'none') {
            switchLevelView('all', false);
          }
        }

        highlightLine(el);

        if (addToHistory) {
          recordJump(fromAddr, el.id);
          let targetHash = el.id.replace(/^DOC_/, '');
          if (window.location.hash.substring(1) !== targetHash) {
            history.pushState({ addr: targetHash }, '', '#' + targetHash);
          }
        }
      } else {
        alert('Adresse ou routine introuvable dans le code : ' + target);
      }
    }

    function handleLinkClick(e, fromAddr, targetAddr) {
      if (e) e.preventDefault();
      jumpTo(targetAddr, true, fromAddr);
    }

    function jumpToAddress() {
      const input = document.getElementById('jump-input').value.trim().toUpperCase();
      if (!input) return;
      jumpTo(input, true, null);
    }

    document.getElementById('jump-input').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') jumpToAddress();
    });

    function filterCode() {
      const q = document.getElementById('filter-input').value.toLowerCase().trim();
      const lines = document.querySelectorAll('.code-line, .label-line, .routine-card');
      if (!q) {
        lines.forEach(l => l.style.display = '');
        return;
      }
      lines.forEach(l => {
        const text = l.textContent.toLowerCase();
        l.style.display = text.includes(q) ? '' : 'none';
      });
    }

    function clearFilter() {
      document.getElementById('filter-input').value = '';
      filterCode();
    }

    // Support natif des flèches Retour / Avance du navigateur
    window.addEventListener('hashchange', function() {
      const h = window.location.hash.substring(1);
      if (h) jumpTo(h, false);
    });

    window.addEventListener('popstate', function() {
      const h = window.location.hash.substring(1);
      if (h) jumpTo(h, false);
    });

    // Raccourcis clavier Alt + ← et Alt + →
    window.addEventListener('keydown', function(e) {
      if (e.altKey && e.key === 'ArrowLeft') {
        e.preventDefault();
        navBack();
      } else if (e.altKey && e.key === 'ArrowRight') {
        e.preventDefault();
        navForward();
      }
    });

    // Chargement initial
    
    // --- GESTION DES SPRITES ET APERÇU GRAPHIQUE ---
    const SPRITES_DATA = {"l1": {"dudley_hang": {"name": "Dudley Accroch\u00e9 Liane", "addr": "$84CF", "addr_num": 33999, "width_bytes": 3, "width_px": 21, "height": 25, "size_bytes": 75, "desc": "Dudley suspendu \u00e0 la corde en attente de saut", "rows_bits": [[0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["80 BF 80", "80 BF 80", "BF BC 80", "BF 90 80", "BC 90 80", "A0 90 80", "A0 BC 80", "A0 BC 80", "B8 BC 80", "F8 BF 80", "F0 BF 80", "E0 BF 80", "C0 BF 80", "C0 8F 80", "80 B0 80", "80 BF 80", "C0 BF 80", "F8 BF 80", "FE 9F 80", "83 94 80", "83 95 80", "83 95 80", "FB FF 81", "E0 B6 80", "C0 9F 80"]}, "dudley_jump": {"name": "Dudley Saut en Vol", "addr": "$86DC", "addr_num": 34524, "width_bytes": 3, "width_px": 21, "height": 25, "size_bytes": 75, "desc": "Dudley projet\u00e9 dans les airs entre deux lianes", "rows_bits": [[1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["BF 80 80", "BF 80 80", "BC 80 80", "E0 83 80", "E0 87 80", "A0 87 80", "A0 8F 80", "CA 80 80", "FA 9F 80", "FE 9F 80", "FE BF 80", "E0 BF 80", "C0 BF 80", "C0 8F 80", "80 B0 80", "80 BF 80", "C0 BF 80", "F8 BF 80", "FE 9F 80", "83 94 80", "83 95 80", "83 95 80", "FB FF 81", "E0 B6 80", "C0 9F 80"]}, "dudley_swing": {"name": "Dudley Balancement Grand Angle", "addr": "$88E9", "addr_num": 35049, "width_bytes": 6, "width_px": 42, "height": 16, "size_bytes": 96, "desc": "Animation de balancement amplitude maximale", "rows_bits": [[1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0]], "rows_hex": ["8F 80 80 80 80 80", "FC 80 80 80 80 80", "F0 F7 83 80 80 80", "80 FF 9F 80 80 80", "80 FC FF 80 80 80", "A0 F5 FF 83 80 80", "A0 B5 FE 9F 80 80", "FC FF F8 BF 80 80", "B0 9B F0 BF 80 80", "E0 8F 80 FC 80 80", "80 80 80 F0 83 80", "80 80 80 C0 82 80", "80 80 80 80 8A 80", "80 80 80 80 A8 80", "80 80 80 80 F0 81", "80 80 80 80 F0 81"]}, "dudley_arms_up": {"name": "Dudley Prise \u00e0 Deux Mains", "addr": "$8FBE", "addr_num": 36798, "width_bytes": 4, "width_px": 28, "height": 23, "size_bytes": 92, "desc": "Posture bras lev\u00e9s accroch\u00e9 \u00e0 la liane", "rows_bits": [[1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["BF C0 81 80", "BF E0 81 80", "B8 F4 81 80", "A0 E4 81 80", "A0 84 80 80", "A0 9F 80 80", "BC BE 80 80", "FC BF 83 80", "F8 FF 83 80", "F0 BF 83 80", "80 80 83 80", "E0 BF 83 80", "FE BF 83 80", "FE FF 83 80", "E6 FF 81 80", "E0 FF 81 80", "C0 FF 80 80", "80 94 80 80", "80 95 80 80", "80 95 80 80", "F8 FF 81 80", "E0 B6 80 80", "C0 9F 80 80"]}, "monkey_climb": {"name": "Singe Grimpeur", "addr": "$9242", "addr_num": 37442, "width_bytes": 5, "width_px": 35, "height": 13, "size_bytes": 65, "desc": "Singe montant le long de la corde", "rows_bits": [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["80 80 E0 80 80", "80 80 E0 81 80", "C0 FB EB 83 80", "F0 FB EB 86 80", "F8 FB EB 87 80", "FC FB E9 86 80", "FC FB E8 83 80", "FC BD E0 81 80", "A8 B8 E0 80 80", "F7 90 80 80 80", "F7 D3 80 80 80", "FF 83 80 80 80", "8F 80 80 80 80"]}}, "l2": {"dudley_swim": {"name": "Dudley \u00e0 la Nage", "addr": "$7EB0", "addr_num": 32432, "width_bytes": 3, "width_px": 21, "height": 12, "size_bytes": 36, "desc": "Dudley nageant dans la rivi\u00e8re", "rows_bits": [[0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["E0 B8 80", "F0 B1 80", "E0 BF 80", "E0 8F 80", "80 86 80", "80 80 80", "B8 E0 81", "FE F0 81", "BC B0 80", "FC F1 81", "FE E0 80", "9C 80 80"]}, "croco_swim": {"name": "Grand Crocodile Nageant", "addr": "$80A8", "addr_num": 32936, "width_bytes": 7, "width_px": 49, "height": 14, "size_bytes": 98, "desc": "Crocodile adulte en patrouille horizontale", "rows_bits": [[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["D5 AA D5 AA D5 AA D5", "80 80 80 80 80 80 80", "A5 FF D4 EA D3 AA D5", "A0 FF 81 FC 83 87 80", "D5 CA D5 FF 8B A7 D5", "80 F4 BF 9F A0 87 80", "95 D5 BF AF 95 A7 D5", "80 95 BF 9F 80 80 80", "E5 FF BB FF 93 A7 D5", "80 DB C1 FF 8B 87 80", "D5 FE D4 FA A3 A7 D5", "80 80 80 80 80 87 80", "D5 AA D5 AA D5 AA D5", "80 80 80 80 80 80 80"]}, "croco_jaws_open": {"name": "Crocodile M\u00e2choire Ouverte", "addr": "$8356", "addr_num": 33622, "width_bytes": 7, "width_px": 49, "height": 14, "size_bytes": 98, "desc": "Gueule b\u00e9ante dangereuse", "rows_bits": [[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["D5 AA D5 AA D5 AA D5", "80 80 80 80 80 80 80", "95 FD D5 F2 93 A7 D5", "80 FD 83 FE 83 87 80", "D5 AA D3 FF AB A7 D5", "80 C0 BF 9F 80 80 80", "D5 F4 BF FF 93 A7 D5", "80 D5 BF FF 83 87 80", "95 95 BF FF AB A7 D5", "E0 FF C7 87 80 80 80", "9D DB D5 AA D5 AA D5", "F0 FE 80 80 80 80 80", "D5 AA D5 AA D5 AA D5", "80 80 80 80 80 80 80"]}, "croco_fast": {"name": "Crocodile Rapide / Plongeant", "addr": "$8604", "addr_num": 34308, "width_bytes": 7, "width_px": 49, "height": 14, "size_bytes": 98, "desc": "Crocodile en descente d'attaque", "rows_bits": [[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["D5 AA D5 AA D5 AA D5", "80 80 80 80 80 80 80", "D5 F4 CF BA D5 AA D5", "80 F4 8F FC 81 80 80", "D9 AA D6 FF D7 AA D5", "F0 81 BF FF 8B 80 80", "D5 F4 BF FF E9 A9 D5", "80 D5 BF FF FA 81 80", "95 95 BF F7 D2 AA D5", "E0 FF C7 81 82 80 80", "95 DB D5 AA BE AA D5", "80 FE 80 80 BE 80 80", "D5 AA D5 AA D5 AA D5", "80 80 80 80 80 80 80"]}}, "l3": {"small_boulder": {"name": "Petit Rocher Roulant", "addr": "$8898", "addr_num": 34968, "width_bytes": 3, "width_px": 21, "height": 8, "size_bytes": 24, "desc": "Rocher bas \u00e0 enjamber avec un saut", "rows_bits": [[0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["E0 87 80", "F8 9E 80", "FC BF 80", "F8 BF 80", "FC 9D 80", "FC BF 80", "F8 9F 80", "C0 87 80"]}, "big_boulder": {"name": "Gros Rocher Rebondissant", "addr": "$85F8", "addr_num": 34296, "width_bytes": 4, "width_px": 28, "height": 24, "size_bytes": 96, "desc": "Gros bloc rocheux \u00e0 esquiver accroupi", "rows_bits": [[0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["F8 83 80 80", "F8 83 80 80", "C0 BF 80 80", "C0 BF 80 80", "80 B9 80 80", "80 91 80 80", "E0 9F 80 80", "F0 BF 80 80", "F0 BF 80 80", "F0 BF 80 80", "E0 BF 80 80", "80 FC 83 80", "F0 FF 83 80", "F0 BF 83 80", "E0 BF 83 80", "E0 FF 83 80", "E0 FF 81 80", "C0 FF 80 80", "80 94 80 80", "80 95 80 80", "80 95 80 80", "F8 FF 81 80", "E0 B6 80 80", "C0 9F 80 80"]}, "dudley_dodge": {"name": "Dudley Saut / Esquive", "addr": "$8400", "addr_num": 33792, "width_bytes": 3, "width_px": 21, "height": 24, "size_bytes": 72, "desc": "Animation de saut au-dessus des rochers", "rows_bits": [[0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["80 BF 80", "80 BF 80", "80 B8 80", "FE 90 80", "FE 90 80", "B8 90 80", "A0 9F 80", "BC BE 80", "FE BF 80", "FC BF 80", "F8 BF 80", "80 98 80", "F0 BF 80", "FC FF 80", "FC FF 80", "E0 FF 80", "E0 FF 80", "C0 BF 80", "80 94 80", "80 95 80", "80 95 80", "F8 FF 81", "E0 B6 80", "C0 9F 80"]}}, "l4": {"cannibal_spear": {"name": "Guerrier Cannibale & Lance", "addr": "$8156", "addr_num": 33110, "width_bytes": 5, "width_px": 35, "height": 32, "size_bytes": 160, "desc": "Cannibale tenant sa lance d'estoc", "rows_bits": [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["80 F0 81 80 80", "80 F0 83 80 80", "80 80 C3 87 80", "80 80 E3 87 80", "80 86 D3 80 80", "80 BE F7 8E 80", "80 E6 DD 83 80", "80 BE F7 8E 80", "80 E6 DD 83 80", "80 E6 DD 83 80", "80 DE EB 81 80", "80 9E FF 81 80", "80 B6 FE 80 80", "80 E6 FE 9F 80", "80 C6 FF BF 80", "80 86 FF B3 80", "80 86 F0 B1 80", "80 86 FC 87 80", "80 C6 9F BF 80", "80 C6 FF BF 80", "80 C6 F1 B1 80", "80 DE F7 BD 80", "80 8E FE 8F 80", "80 86 F8 83 80", "80 80 80 80 80", "80 80 80 80 80", "80 80 80 80 80", "80 80 80 80 80", "80 80 80 80 80", "80 80 80 80 80", "80 80 80 80 80", "80 80 80 80 80"]}, "maiden_pot": {"name": "Jeune Femme Suspendue", "addr": "$865E", "addr_num": 34398, "width_bytes": 3, "width_px": 21, "height": 24, "size_bytes": 72, "desc": "Prisonni\u00e8re attach\u00e9e au-dessus de la marmite", "rows_bits": [[0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["80 BF 80", "80 BF 80", "80 B8 80", "FE 90 80", "FE 90 80", "B8 90 80", "A0 9F 80", "BC BE 80", "FE BF 80", "FC BF 80", "F8 BF 80", "80 98 80", "F0 BF 80", "FC FF 80", "FC FF 80", "E0 FF 80", "E0 FF 80", "C0 BF 80", "80 94 80", "80 95 80", "80 95 80", "F8 FF 81", "E0 B6 80", "C0 9F 80"]}, "boiling_pot": {"name": "Marmite Bouillonnante", "addr": "$8856", "addr_num": 34902, "width_bytes": 4, "width_px": 28, "height": 24, "size_bytes": 96, "desc": "Chaudron chauff\u00e9 par le feu du village", "rows_bits": [[0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "rows_hex": ["F8 83 80 80", "F8 83 80 80", "C0 BF 80 80", "C0 BF 80 80", "80 B9 80 80", "80 91 80 80", "E0 9F 80 80", "F0 BF 80 80", "F0 BF 80 80", "F0 BF 80 80", "E0 BF 80 80", "80 FC 83 80", "F0 FF 83 80", "F0 BF 83 80", "E0 BF 83 80", "E0 FF 83 80", "E0 FF 81 80", "C0 FF 80 80", "80 94 80 80", "80 95 80 80", "80 95 80 80", "F8 FF 81 80", "E0 B6 80 80", "C0 9F 80 80"]}}};
    const currentSprAddr = {};

    function drawSpriteOnCanvas(canvasId, spr) {
      const canvas = document.getElementById(canvasId);
      if (!canvas || !spr) return;
      const ctx = canvas.getContext('2d');

      // Facteur d'échelle dynamique
      let pixelScale = 7;
      if (spr.width_px > 40 || spr.height > 25) pixelScale = 5;
      if (spr.width_px > 45) pixelScale = 4.5;

      canvas.width = Math.max(Math.round(spr.width_px * pixelScale), 240);
      canvas.height = Math.max(Math.round(spr.height * pixelScale), 160);

      // Fond CRT
      ctx.fillStyle = '#030706';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Lignes de balayage CRT
      ctx.fillStyle = 'rgba(0, 25, 12, 0.4)';
      for (let y = 0; y < canvas.height; y += 3) {
        ctx.fillRect(0, y, canvas.width, 1);
      }

      // Centrage
      const offsetX = Math.floor((canvas.width - spr.width_px * pixelScale) / 2);
      const offsetY = Math.floor((canvas.height - spr.height * pixelScale) / 2);

      const rows = spr.rows_bits;
      for (let y = 0; y < rows.length; y++) {
        for (let x = 0; x < rows[y].length; x++) {
          if (rows[y][x]) {
            ctx.fillStyle = '#34d399';
            ctx.shadowColor = '#10b981';
            ctx.shadowBlur = 4;
            ctx.fillRect(
              Math.floor(offsetX + x * pixelScale),
              Math.floor(offsetY + y * pixelScale),
              Math.ceil(pixelScale - 1),
              Math.ceil(pixelScale - 1)
            );
          }
        }
      }
    }

    function selectSprite(modId, spriteId) {
      const sprMod = SPRITES_DATA[modId];
      if (!sprMod || !sprMod[spriteId]) return;
      const spr = sprMod[spriteId];

      currentSprAddr[modId] = (modId === 'main' ? '' : modId + '_') + spr.addr.substring(1);

      // Mise à jour des onglets
      const container = document.getElementById('tabs-' + modId);
      if (container) {
        container.querySelectorAll('.sprite-tab-btn').forEach(btn => {
          btn.classList.toggle('active', btn.dataset.spriteId === spriteId);
        });
      }

      // Métadonnées
      const lblName = document.getElementById('lbl-name-' + modId);
      const lblRange = document.getElementById('lbl-range-' + modId);
      const lblDims = document.getElementById('lbl-dims-' + modId);
      const lblDesc = document.getElementById('lbl-desc-' + modId);
      const btnJump = document.getElementById('btn-jump-' + modId);

      if (lblName) lblName.textContent = spr.name;
      if (lblRange) {
        const endAddr = spr.addr_num + spr.size_bytes - 1;
        lblRange.textContent = spr.addr + ' - $' + endAddr.toString(16).toUpperCase() + ' (' + spr.size_bytes + ' octets)';
      }
      if (lblDims) {
        lblDims.textContent = spr.width_px + ' × ' + spr.height + ' pixels (' + spr.width_bytes + ' octets/ligne)';
      }
      if (lblDesc) lblDesc.textContent = spr.desc;
      if (btnJump) btnJump.textContent = '🔍 Aller à ' + spr.addr + ' dans le listing';

      // Listing Hexadécimal en vis-à-vis
      const hexBox = document.getElementById('hex-box-' + modId);
      if (hexBox) {
        let rowsHtml = '';
        const baseAddr = spr.addr_num;
        for (let i = 0; i < spr.height; i++) {
          const lineAddr = '$' + (baseAddr + i * spr.width_bytes).toString(16).toUpperCase();
          const hexLine = spr.rows_hex[i];
          const asciiDots = spr.rows_bits[i].map(b => b ? '█' : '·').join('');
          rowsHtml += '<div class="hex-row"><span class="hr-num">L' + (i < 10 ? '0' + i : i) + '</span> ' +
                      '<span class="hr-addr">[' + lineAddr + ']</span> ' +
                      '<span class="hr-hex">' + hexLine + '</span> ' +
                      '<span class="hr-ascii">' + asciiDots + '</span></div>';
        }
        hexBox.innerHTML = rowsHtml;
      }

      // Rendu Canvas
      drawSpriteOnCanvas('canvas-' + modId, spr);
    }

    function initAllSprites() {
      for (let modId in SPRITES_DATA) {
        let keys = Object.keys(SPRITES_DATA[modId]);
        if (keys.length > 0) {
          selectSprite(modId, keys[0]);
        }
      }
    }

    // --- MISE EN VALEUR DES BRANCHES COURTS (HOVER & TOGGLE) ---
    let branchesHighlighted = false;

    function toggleBranchHighlight() {
      branchesHighlighted = !branchesHighlighted;
      const btn = document.getElementById('btn-toggle-branches');
      if (btn) {
        btn.classList.toggle('active', branchesHighlighted);
        btn.style.background = branchesHighlighted ? '#78350f' : '';
        btn.style.borderColor = branchesHighlighted ? '#f59e0b' : '';
      }
      document.querySelectorAll('.branch-pill').forEach(pill => {
        pill.style.boxShadow = branchesHighlighted ? '0 0 6px currentColor' : '';
      });
    }

    function initBranchHover() {
      document.querySelectorAll('.branch-pill').forEach(pill => {
        pill.addEventListener('mouseenter', function() {
          const targetId = this.dataset.target;
          if (targetId) {
            const targetEl = document.getElementById(targetId);
            if (targetEl) targetEl.classList.add('branch-target-highlight');
          }
        });
        pill.addEventListener('mouseleave', function() {
          const targetId = this.dataset.target;
          if (targetId) {
            const targetEl = document.getElementById(targetId);
            if (targetEl) targetEl.classList.remove('branch-target-highlight');
          }
        });
      });
    }

    window.addEventListener('load', function() {
      initAllSprites();
      initBranchHover();

      let h = window.location.hash.substring(1);
      if (h) {
        jumpTo(h, true, null);
      }
    });
  </script>
</body>
</html>
""")

    with open(out_html, "w", encoding="utf-8") as f:
        f.write("".join(h))

    print(f"[+] Document Maître Multi-Niveaux généré avec succès : {out_html}")


if __name__ == "__main__":
    build_master_html()
