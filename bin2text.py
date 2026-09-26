#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bin2text.py - Désassembleur MOS 6502 & Générateur de Reverse Engineering Interactif
Outil transverse pour Apple II & systèmes 6502.
Supporte le mode CLI et l'interface graphique Tkinter.
"""

import sys
import os
import re
import json
import argparse

# =============================================================================
# DICTIONNAIRE DES OPCODES MOS 6502
# (Mnémonique, Mode d'adressage, Longueur en octets)
# =============================================================================
OPCODES_6502 = {
    0x00: ("BRK", "impl", 1), 0x01: ("ORA", "indx", 2), 0x05: ("ORA", "zp",   2), 0x06: ("ASL", "zp",   2),
    0x08: ("PHP", "impl", 1), 0x09: ("ORA", "imm",  2), 0x0A: ("ASL", "acc",  1), 0x0D: ("ORA", "abs",  3),
    0x0E: ("ASL", "abs",  3), 0x10: ("BPL", "rel",  2), 0x11: ("ORA", "indy", 2), 0x15: ("ORA", "zpx",  2),
    0x16: ("ASL", "zpx",  2), 0x18: ("CLC", "impl", 1), 0x19: ("ORA", "absy", 3), 0x1D: ("ORA", "absx", 3),
    0x1E: ("ASL", "absx", 3), 0x20: ("JSR", "abs",  3), 0x21: ("AND", "indx", 2), 0x24: ("BIT", "zp",   2),
    0x25: ("AND", "zp",   2), 0x26: ("ROL", "zp",   2), 0x28: ("PLP", "impl", 1), 0x29: ("AND", "imm",  2),
    0x2A: ("ROL", "acc",  1), 0x2C: ("BIT", "abs",  3), 0x2D: ("AND", "abs",  3), 0x2E: ("ROL", "abs",  3),
    0x30: ("BMI", "rel",  2), 0x31: ("AND", "indy", 2), 0x35: ("AND", "zpx",  2), 0x36: ("ROL", "zpx",  2),
    0x38: ("SEC", "impl", 1), 0x39: ("AND", "absy", 3), 0x3D: ("AND", "absx", 3), 0x3E: ("ROL", "absx", 3),
    0x40: ("RTI", "impl", 1), 0x41: ("EOR", "indx", 2), 0x45: ("EOR", "zp",   2), 0x46: ("LSR", "zp",   2),
    0x48: ("PHA", "impl", 1), 0x49: ("EOR", "imm",  2), 0x4A: ("LSR", "acc",  1), 0x4C: ("JMP", "abs",  3),
    0x4D: ("EOR", "abs",  3), 0x4E: ("LSR", "abs",  3), 0x50: ("BVC", "rel",  2), 0x51: ("EOR", "indy", 2),
    0x55: ("EOR", "zpx",  2), 0x56: ("LSR", "zpx",  2), 0x58: ("CLI", "impl", 1), 0x59: ("EOR", "absy", 3),
    0x5D: ("EOR", "absx", 3), 0x5E: ("LSR", "absx", 3), 0x60: ("RTS", "impl", 1), 0x61: ("ADC", "indx", 2),
    0x65: ("ADC", "zp",   2), 0x66: ("ROR", "zp",   2), 0x68: ("PLA", "impl", 1), 0x69: ("ADC", "imm",  2),
    0x6A: ("ROR", "acc",  1), 0x6C: ("JMP", "ind",  3), 0x6D: ("ADC", "abs",  3), 0x6E: ("ROR", "abs",  3),
    0x70: ("BVS", "rel",  2), 0x71: ("ADC", "indy", 2), 0x75: ("ADC", "zpx",  2), 0x76: ("ROR", "zpx",  2),
    0x78: ("SEI", "impl", 1), 0x79: ("ADC", "absy", 3), 0x7D: ("ADC", "absx", 3), 0x7E: ("ROR", "absx", 3),
    0x81: ("STA", "indx", 2), 0x84: ("STY", "zp",   2), 0x85: ("STA", "zp",   2), 0x86: ("STX", "zp",   2),
    0x88: ("DEY", "impl", 1), 0x8A: ("TXA", "impl", 1), 0x8C: ("STY", "abs",  3), 0x8D: ("STA", "abs",  3),
    0x8E: ("STX", "abs",  3), 0x90: ("BCC", "rel",  2), 0x91: ("STA", "indy", 2), 0x94: ("STY", "zpx",  2),
    0x95: ("STA", "zpx",  2), 0x96: ("STX", "zpy",  2), 0x98: ("TYA", "impl", 1), 0x99: ("STA", "absy", 3),
    0x9A: ("TXS", "impl", 1), 0x9D: ("STA", "absx", 3), 0xA0: ("LDY", "imm",  2), 0xA1: ("LDA", "indx", 2),
    0xA2: ("LDX", "imm",  2), 0xA4: ("LDY", "zp",   2), 0xA5: ("LDA", "zp",   2), 0xA6: ("LDX", "zp",   2),
    0xA8: ("TAY", "impl", 1), 0xA9: ("LDA", "imm",  2), 0xAA: ("TAX", "impl", 1), 0xAC: ("LDY", "abs",  3),
    0xAD: ("LDA", "abs",  3), 0xAE: ("LDX", "abs",  3), 0xB0: ("BCS", "rel",  2), 0xB1: ("LDA", "indy", 2),
    0xB4: ("LDY", "zpx",  2), 0xB5: ("LDA", "zpx",  2), 0xB6: ("LDX", "zpy",  2), 0xB8: ("CLV", "impl", 1),
    0xB9: ("LDA", "absy", 3), 0xBA: ("TSX", "impl", 1), 0xBC: ("LDY", "absx", 3), 0xBD: ("LDA", "absx", 3),
    0xBE: ("LDX", "absy", 3), 0xC0: ("CPY", "imm",  2), 0xC1: ("CMP", "indx", 2), 0xC4: ("CPY", "zp",   2),
    0xC5: ("CMP", "zp",   2), 0xC6: ("DEC", "zp",   2), 0xC8: ("INY", "impl", 1), 0xC9: ("CMP", "imm",  2),
    0xCA: ("DEX", "impl", 1), 0xCC: ("CPY", "abs",  3), 0xCD: ("CMP", "abs",  3), 0xCE: ("DEC", "abs",  3),
    0xD0: ("BNE", "rel",  2), 0xD1: ("CMP", "indy", 2), 0xD5: ("CMP", "zpx",  2), 0xD6: ("DEC", "zpx",  2),
    0xD8: ("CLD", "impl", 1), 0xD9: ("CMP", "absy", 3), 0xDD: ("CMP", "absx", 3), 0xDE: ("DEC", "absx", 3),
    0xE0: ("CPX", "imm",  2), 0xE1: ("SBC", "indx", 2), 0xE4: ("CPX", "zp",   2), 0xE5: ("SBC", "zp",   2),
    0xE6: ("INC", "zp",   2), 0xE8: ("INX", "impl", 1), 0xE9: ("SBC", "imm",  2), 0xEA: ("NOP", "impl", 1),
    0xEC: ("CPX", "abs",  3), 0xED: ("SBC", "abs",  3), 0xEE: ("INC", "abs",  3), 0xF0: ("BEQ", "rel",  2),
    0xF1: ("SBC", "indy", 2), 0xF5: ("SBC", "zpx",  2), 0xF6: ("INC", "zpx",  2), 0xF8: ("SED", "impl", 1),
    0xF9: ("SBC", "absy", 3), 0xFD: ("SBC", "absx", 3), 0xFE: ("INC", "absx", 3)
}

# =============================================================================
# REGISTRES MATÉRIELS APPLE II & SYMBOLES ROM
# =============================================================================
APPLE2_HARDWARE = {
    0xC000: ("KBD", "Clavier : Lecture du caractère (Bit 7 = 1 si touche enfoncée)"),
    0xC010: ("KBDSTRB", "Clavier : Acquittement du strobe de touche"),
    0xC020: ("TAPETOG", "Cassette : Bascule de sortie cassette"),
    0xC030: ("SPKR", "Speaker : Clic haut-parleur (génération sonore 1-bit)"),
    0xC050: ("TXTCLR", "Affichage : Active le mode Graphique"),
    0xC051: ("TXTSET", "Affichage : Active le mode Texte"),
    0xC052: ("MIXCLR", "Affichage : Mode Graphique Plein Écran (Full Screen)"),
    0xC053: ("MIXSET", "Affichage : Mode Graphique Mixte (avec 4 lignes de texte)"),
    0xC054: ("TXTPAGE1", "Affichage : Sélectionne la Page 1 ($2000-$3FFF / $0400-$07FF)"),
    0xC055: ("TXTPAGE2", "Affichage : Sélectionne la Page 2 ($4000-$5FFF / $0800-$0BFF)"),
    0xC056: ("LORES", "Affichage : Active le mode Basse Résolution (Lo-Res 40x48)"),
    0xC057: ("HIRES", "Affichage : Active le mode Haute Résolution (Hi-Res 280x192)"),
    0xC061: ("PB0", "Entrée : Bouton poussoir 0 / Touche Open Apple"),
    0xC062: ("PB1", "Entrée : Bouton poussoir 1 / Touche Solid Apple"),
    0xC064: ("PADDL0", "Entrée : Potentiomètre Paddle 0 (Axe horizontal)"),
    0xC065: ("PADDL1", "Entrée : Potentiomètre Paddle 1 (Axe vertical)"),
    0xC070: ("PTRIG", "Entrée : Déclenchement des timers des paddles"),
    0xFB6F: ("SETPWRC", "ROM : Initialise le vecteur Power-Up ($03F2/$03F3)"),
    0xFC58: ("HOME", "ROM : Efface l'écran texte et place le curseur en haut à gauche"),
    0xFD1B: ("KEYIN", "ROM : Attend et lit un caractère clavier"),
    0xFDED: ("COUT", "ROM : Affiche le caractère dans l'accumulateur à l'écran"),
    0xFAA6: ("PWRUP", "ROM : Routine de démarrage / Reset froid"),
}

# =============================================================================
# CLASSE DE DÉSASSEMBLAGE & ANALYSE
# =============================================================================
class Disassembler6502:
    def __init__(self, binary_data, start_address=0x0800):
        self.data = binary_data
        self.start = start_address
        self.end = start_address + len(binary_data)
        self.instructions = []       # Liste d'objets instruction
        self.labels = {}             # addr -> label string
        self.xrefs = {}              # target_addr -> set(source_addr)
        self.annotations = {}        # addr -> comment string
        self.sections = []           # (start_addr, end_addr, title, desc)

    def load_annotations(self, file_path):
        """Charge des annotations depuis un fichier texte ou JSON."""
        if not os.path.exists(file_path):
            print(f"[-] Fichier d'annotations introuvable : {file_path}")
            return
        
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
                for k, v in data.items():
                    try:
                        if isinstance(k, str) and "_" in k:
                            _, hex_part = k.split("_", 1)
                            addr = int(hex_part, 16)
                        else:
                            addr = int(k, 16) if isinstance(k, str) else int(k)
                        if addr not in self.annotations or len(v) > len(self.annotations[addr]):
                            self.annotations[addr] = v
                    except ValueError:
                        pass
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if ';' in line:
                        m = re.search(r'([0-9A-Fa-f]{4}):', line)
                        comment = line.split(';', 1)[1].strip()
                        comment = re.sub(r'<[^>]+>', '', comment).strip()
                        if m and comment:
                            addr = int(m.group(1), 16)
                            if addr not in self.annotations or len(comment) > len(self.annotations[addr]):
                                self.annotations[addr] = comment

    def pass1_decode(self):
        """Passe 1 : Décode les instructions et collecte les cibles de saut/appel."""
        i = 0
        data_len = len(self.data)

        while i < data_len:
            addr = self.start + i
            op = self.data[i]
            
            if op in OPCODES_6502:
                mnemonic, mode, length = OPCODES_6502[op]
                if i + length <= data_len:
                    bytes_chunk = self.data[i : i + length]
                    target_addr = None
                    operand_str = ""
                    indirect_resolved = None

                    # Analyse selon le mode d'adressage
                    if mode == "impl":
                        operand_str = ""
                    elif mode == "acc":
                        operand_str = "A"
                    elif mode == "imm":
                        operand_str = f"#${bytes_chunk[1]:02X}"
                    elif mode == "zp":
                        target_addr = bytes_chunk[1]
                        operand_str = f"${bytes_chunk[1]:02X}"
                    elif mode == "zpx":
                        target_addr = bytes_chunk[1]
                        operand_str = f"${bytes_chunk[1]:02X},X"
                    elif mode == "zpy":
                        target_addr = bytes_chunk[1]
                        operand_str = f"${bytes_chunk[1]:02X},Y"
                    elif mode == "abs":
                        target_addr = bytes_chunk[1] | (bytes_chunk[2] << 8)
                        operand_str = f"${target_addr:04X}"
                    elif mode == "absx":
                        target_addr = bytes_chunk[1] | (bytes_chunk[2] << 8)
                        operand_str = f"${target_addr:04X},X"
                    elif mode == "absy":
                        target_addr = bytes_chunk[1] | (bytes_chunk[2] << 8)
                        operand_str = f"${target_addr:04X},Y"
                    elif mode == "ind":
                        vec_addr = bytes_chunk[1] | (bytes_chunk[2] << 8)
                        operand_str = f"(${vec_addr:04X})"
                        # Tente de résoudre le saut indirect si le vecteur est dans notre binaire
                        if self.start <= vec_addr < self.end - 1:
                            off = vec_addr - self.start
                            indirect_resolved = self.data[off] | (self.data[off + 1] << 8)
                            target_addr = indirect_resolved
                        else:
                            target_addr = vec_addr
                    elif mode == "indx":
                        operand_str = f"(${bytes_chunk[1]:02X},X)"
                    elif mode == "indy":
                        operand_str = f"(${bytes_chunk[1]:02X}),Y"
                    elif mode == "rel":
                        offset = bytes_chunk[1]
                        if offset >= 0x80:
                            offset -= 256
                        target_addr = addr + 2 + offset
                        operand_str = f"${target_addr:04X}"

                    # Enregistre la cible dans la table de références croisées
                    if target_addr is not None:
                        self.xrefs.setdefault(target_addr, set()).add(addr)

                    # Catégorie de l'instruction pour la coloration syntaxique
                    category = "data"
                    if mnemonic in ("JMP", "JSR"):
                        category = "flow-jump"
                    elif mnemonic.startswith("B") and mnemonic not in ("BIT", "BRK"):
                        category = "flow-branch"
                    elif mnemonic in ("RTS", "RTI"):
                        category = "flow-ret"
                    elif mnemonic in ("LDA", "LDX", "LDY"):
                        category = "load"
                    elif mnemonic in ("STA", "STX", "STY"):
                        category = "store"
                    elif mnemonic in ("CMP", "CPX", "CPY", "BIT"):
                        category = "compare"
                    elif mnemonic in ("ADC", "SBC", "INC", "DEC", "INX", "DEX", "INY", "DEY", "ASL", "LSR", "ROL", "ROR", "AND", "ORA", "EOR"):
                        category = "math"
                    elif mnemonic in ("PHA", "PLA", "PHP", "PLP", "TXS", "TSX"):
                        category = "stack"
                    elif mnemonic in ("CLC", "SEC", "CLI", "SEI", "CLD", "SED", "CLV"):
                        category = "flag"

                    self.instructions.append({
                        "addr": addr,
                        "bytes": bytes_chunk,
                        "op": op,
                        "mnemonic": mnemonic,
                        "mode": mode,
                        "length": length,
                        "operand": operand_str,
                        "target": target_addr,
                        "indirect_vec": (bytes_chunk[1] | (bytes_chunk[2] << 8)) if mode == "ind" else None,
                        "indirect_resolved": indirect_resolved,
                        "category": category
                    })
                    i += length
                    continue

            # Octet inconnu ou non-opcode
            self.instructions.append({
                "addr": addr,
                "bytes": bytes([op]),
                "op": op,
                "mnemonic": "???",
                "mode": "raw",
                "length": 1,
                "operand": f"${op:02X}",
                "target": None,
                "indirect_vec": None,
                "indirect_resolved": None,
                "category": "unknown"
            })
            i += 1

    def pass2_labels(self, custom_labels=None):
        """Passe 2 : Génère des étiquettes sémantiques explicites (pas de simple LOC_ ou SUB_)."""
        if custom_labels:
            for k, v in custom_labels.items():
                self.labels[k] = v

        for instr in self.instructions:
            addr = instr["addr"]
            if addr in self.labels:
                continue
            if addr in self.xrefs:
                callers = self.xrefs[addr]
                has_jsr = any(
                    any(i["addr"] == c and i["mnemonic"] == "JSR" for i in self.instructions)
                    for c in callers
                )
                has_jmp = any(
                    any(i["addr"] == c and i["mnemonic"] == "JMP" for i in self.instructions)
                    for c in callers
                )
                is_loop = any(c > addr for c in callers)

                if has_jsr:
                    self.labels[addr] = f"ROUTINE_{addr:04X}"
                elif is_loop:
                    self.labels[addr] = f"LOOP_{addr:04X}"
                elif has_jmp:
                    self.labels[addr] = f"JUMP_TARGET_{addr:04X}"
                else:
                    self.labels[addr] = f"BRANCH_TARGET_{addr:04X}"

    def define_sections(self, sections):
        """Définit les grandes sections du binaire pour la table des matières."""
        self.sections = sections

    def generate_html(self, output_path, title="Désassemblage 6502"):
        """Génère le document HTML interactif complet."""
        print(f"[*] Génération du rapport HTML interactif : {output_path}...")

        total_instr = len(self.instructions)
        total_sub = sum(1 for l in self.labels.values() if l.startswith("SUB_"))
        total_ann = len(self.annotations)
        total_xrefs = len(self.xrefs)

        html_lines = []
        html_lines.append(f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    :root {{
      --bg-main: #0d1117;
      --bg-sidebar: #161b22;
      --bg-card: #1c2128;
      --border-color: #30363d;
      --text-main: #c9d1d9;
      --text-muted: #8b949e;
      --text-dim: #484f58;
      
      --c-addr: #58a6ff;
      --c-bytes: #6e7681;
      --c-jump: #f0883e;
      --c-branch: #79c0ff;
      --c-load: #7ee787;
      --c-store: #aff5b4;
      --c-compare: #d2a8ff;
      --c-math: #ff7b72;
      --c-stack: #e3b341;
      --c-comment: #3fb950;
      --c-cheat: #ffa657;
      --c-hw: #f778ba;
      --highlight: #21262d;
      --active-line: #388bfd33;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg-main);
      color: var(--text-main);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }}

    /* SIDEBAR */
    #sidebar {{
      width: 360px;
      min-width: 320px;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      height: 100vh;
    }}

    .sidebar-header {{
      padding: 18px 20px;
      border-bottom: 1px solid var(--border-color);
      background: #111418;
    }}

    .sidebar-header h1 {{
      font-size: 1.15rem;
      font-weight: 700;
      color: #58a6ff;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .badge-sub {{
      font-size: 0.75rem;
      color: var(--text-muted);
    }}

    .search-box {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: var(--bg-sidebar);
    }}

    .search-row {{
      display: flex;
      gap: 6px;
    }}

    .search-input {{
      flex: 1;
      background: #0d1117;
      border: 1px solid var(--border-color);
      color: #fff;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-family: monospace;
    }}

    .search-input:focus {{
      outline: none;
      border-color: #58a6ff;
    }}

    .btn {{
      background: #21262d;
      color: #c9d1d9;
      border: 1px solid var(--border-color);
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 500;
      transition: all 0.15s;
    }}

    .btn:hover {{
      background: #30363d;
      color: #fff;
    }}

    .btn-primary {{
      background: #238636;
      border-color: #2ea043;
      color: #fff;
    }}

    .btn-primary:hover {{
      background: #2ea043;
    }}

    .stats-bar {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      padding: 12px 16px;
      background: #13171d;
      border-bottom: 1px solid var(--border-color);
      font-size: 0.8rem;
    }}

    .stat-item {{
      background: #1c2128;
      padding: 6px 8px;
      border-radius: 4px;
      border: 1px solid #30363d;
    }}

    .stat-val {{
      font-weight: 700;
      color: #58a6ff;
    }}

    .sidebar-scroll {{
      flex: 1;
      overflow-y: auto;
      padding: 12px 16px;
    }}

    .section-title {{
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin: 16px 0 8px 0;
    }}

    .toc-link {{
      display: block;
      padding: 6px 10px;
      color: #c9d1d9;
      text-decoration: none;
      font-size: 0.85rem;
      border-radius: 4px;
      margin-bottom: 2px;
      transition: background 0.1s;
    }}

    .toc-link:hover {{
      background: #21262d;
      color: #58a6ff;
    }}

    .toc-link span.range {{
      font-family: monospace;
      color: var(--c-addr);
      font-size: 0.8rem;
      margin-right: 6px;
    }}

    /* MAIN CODE VIEW */
    #main {{
      flex: 1;
      height: 100vh;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      position: relative;
    }}

    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: #111418ee;
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border-color);
      padding: 10px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .code-container {{
      padding: 16px 24px 80px 24px;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 13px;
      line-height: 1.6;
    }}

    .code-line {{
      display: flex;
      align-items: baseline;
      padding: 1px 6px;
      border-radius: 4px;
      margin-bottom: 1px;
      scroll-margin-top: 60px;
    }}

    .code-line:hover {{
      background: #1c2128;
    }}

    .code-line.active {{
      background: #388bfd33 !important;
      border-left: 3px solid #58a6ff;
    }}

    .label-header {{
      margin-top: 14px;
      margin-bottom: 4px;
      padding: 6px 8px;
      background: #161b22;
      border-left: 3px solid #f0883e;
      border-radius: 0 4px 4px 0;
      color: #f0883e;
      font-weight: 700;
      font-size: 0.95rem;
    }}

    .label-header.sub {{
      border-color: #58a6ff;
      color: #79c0ff;
      background: #131d2a;
    }}

    .line-addr {{
      width: 65px;
      color: var(--c-addr);
      font-weight: 600;
      user-select: none;
    }}

    .line-bytes {{
      width: 90px;
      color: var(--c-bytes);
      user-select: none;
    }}

    .line-mnemonic {{
      width: 50px;
      font-weight: 700;
    }}

    .line-operand {{
      width: 140px;
      color: #e6edf3;
    }}

    .target-link {{
      color: #79c0ff;
      text-decoration: none;
      border-bottom: 1px dotted #58a6ff;
    }}

    .target-link:hover {{
      color: #fff;
      border-bottom: 1px solid #fff;
    }}

    .vec-resolved {{
      color: #aff5b4;
      font-weight: 600;
      margin-left: 4px;
    }}

    .xrefs-tag {{
      margin-left: 8px;
      font-size: 0.78rem;
      color: var(--text-muted);
    }}

    .xref-link {{
      color: #d2a8ff;
      text-decoration: none;
    }}

    .xref-link:hover {{
      text-decoration: underline;
    }}

    .line-comment {{
      color: var(--c-comment);
      margin-left: 16px;
      white-space: pre-wrap;
    }}

    .line-comment.hw {{
      color: var(--c-hw);
      font-weight: 500;
    }}

    .line-comment.cheat {{
      color: var(--c-cheat);
      font-weight: 600;
      background: #341804;
      padding: 1px 6px;
      border-radius: 3px;
      border: 1px solid #844200;
    }}

    /* Coloration des catégories */
    .flow-jump {{ color: var(--c-jump); }}
    .flow-branch {{ color: var(--c-branch); }}
    .flow-ret {{ color: #f85149; }}
    .load {{ color: var(--c-load); }}
    .store {{ color: var(--c-store); }}
    .compare {{ color: var(--c-compare); }}
    .math {{ color: var(--c-math); }}
    .stack {{ color: var(--c-stack); }}
    .flag {{ color: #e3b341; }}
    .unknown {{ color: #8b949e; }}

    /* CONTRÔLES DE NAVIGATION & HISTORIQUE */
    .nav-controls {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .nav-btn {{
      background: #21262d;
      color: #c9d1d9;
      border: 1px solid var(--border-color);
      padding: 5px 11px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
      display: flex;
      align-items: center;
      gap: 4px;
    }}

    .nav-btn:hover:not(:disabled) {{
      background: #30363d;
      color: #58a6ff;
      border-color: #58a6ff;
    }}

    .nav-btn:disabled {{
      opacity: 0.35;
      cursor: not-allowed;
    }}

    .nav-history-trail {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.78rem;
      font-family: monospace;
      overflow-x: auto;
      max-width: 380px;
    }}

    .trail-item {{
      color: #58a6ff;
      background: #1c2128;
      border: 1px solid var(--border-color);
      padding: 2px 7px;
      border-radius: 4px;
      cursor: pointer;
      text-decoration: none;
    }}

    .trail-item:hover {{
      background: #58a6ff;
      color: #0d1117;
    }}

    .trail-item.current {{
      color: #f0883e;
      border-color: #f0883e;
      font-weight: bold;
    }}

    /* FLOATING RETURN TOAST */
    #return-toast {{
      position: fixed;
      bottom: 24px;
      right: 32px;
      z-index: 1000;
      background: #1c2128;
      border: 1px solid #58a6ff;
      box-shadow: 0 8px 24px rgba(0,0,0,0.6);
      border-radius: 8px;
      padding: 10px 16px;
      display: none;
      align-items: center;
      gap: 12px;
      color: #f0f6fc;
      font-size: 0.85rem;
      font-weight: 600;
      animation: slideUp 0.2s ease-out;
    }}

    #return-toast button#return-toast-btn {{
      background: #1f6feb;
      border: none;
      color: #fff;
      padding: 6px 14px;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 700;
      font-size: 0.82rem;
    }}

    #return-toast button#return-toast-btn:hover {{
      background: #388bfd;
    }}

    @keyframes slideUp {{
      from {{ transform: translateY(20px); opacity: 0; }}
      to {{ transform: translateY(0); opacity: 1; }}
    }}
  </style>
</head>
<body>

  <!-- SIDEBAR -->
  <aside id="sidebar">
    <div class="sidebar-header">
      <h1>🕹️ 6502 RE Explorer</h1>
      <div class="badge-sub">{title}</div>
    </div>

    <!-- Quick Jump & Search -->
    <div class="search-box">
      <div class="search-row">
        <input type="text" id="jump-input" class="search-input" placeholder="Adresse Hex (ex: 0A76, 1300)..." maxlength="6">
        <button class="btn btn-primary" onclick="jumpToAddress()">Aller</button>
      </div>
      <div class="search-row">
        <input type="text" id="filter-input" class="search-input" placeholder="Filtrer texte/opcode/cheat..." oninput="filterCode()">
        <button class="btn" onclick="clearFilter()">Reset</button>
      </div>
    </div>

    <!-- Statistiques -->
    <div class="stats-bar">
      <div class="stat-item">Plage : <span class="stat-val">${self.start:04X} - ${self.end-1:04X}</span></div>
      <div class="stat-item">Taille : <span class="stat-val">{len(self.data):,} o</span></div>
      <div class="stat-item">Instructions : <span class="stat-val">{total_instr:,}</span></div>
      <div class="stat-item">Routines (SUB) : <span class="stat-val">{total_sub:,}</span></div>
      <div class="stat-item">Annotations : <span class="stat-val">{total_ann:,}</span></div>
      <div class="stat-item">XREFs : <span class="stat-val">{total_xrefs:,}</span></div>
    </div>

    <!-- Table des matières & Navigation -->
    <div class="sidebar-scroll">
      <div class="section-title">Grandes Sections Mémoire</div>
""")

        # Sections prédéfinies
        for s_start, s_end, s_name, s_desc in self.sections:
            html_lines.append(f"""      <a class="toc-link" href="#{s_start:04X}" onclick="handleLinkClick(event, null, '{s_start:04X}')">
        <span class="range">${s_start:04X}</span> {s_name}
      </a>""")

        # Liste des sous-routines clés
        html_lines.append("""      <div class="section-title">Points d'Entrée & Routines Clés</div>""")
        for addr, lbl in sorted(self.labels.items()):
            if lbl.startswith("SUB_") or addr in self.annotations:
                ann_preview = f" - {self.annotations[addr][:28]}..." if addr in self.annotations else ""
                html_lines.append(f"""      <a class="toc-link" href="#{addr:04X}" onclick="handleLinkClick(event, null, '{addr:04X}')">
        <span class="range">${addr:04X}</span> {lbl}{ann_preview}
      </a>""")

        html_lines.append("""    </div>
  </aside>

  <!-- MAIN CODE VIEW -->
  <main id="main">
    <div class="toolbar">
      <div style="display:flex; align-items:center; gap:16px;">
        <div style="font-weight: 700; color: #58a6ff; font-size: 0.95rem;">Explorateur 6502</div>
        <div class="nav-controls">
          <button id="btn-nav-back" class="nav-btn" onclick="navBack()" title="Précédent (Alt + Gauche)" disabled>⬅️ Retour</button>
          <button id="btn-nav-fwd" class="nav-btn" onclick="navForward()" title="Suivant (Alt + Droite)" disabled>Suivant ➡️</button>
        </div>
      </div>
      <div id="nav-trail" class="nav-history-trail" title="Historique de navigation récent"></div>
      <div style="font-size: 0.8rem; color: var(--text-muted);">
        Cliquez sur une adresse pour naviguer • Flèche retour du navigateur supportée
      </div>
    </div>

    <div class="code-container" id="code-container">
""")

        # Génération des lignes de code
        for instr in self.instructions:
            addr = instr["addr"]
            addr_hex = f"{addr:04X}"
            hex_bytes = " ".join(f"{b:02X}" for b in instr["bytes"])

            # Entête de label si cible de saut ou sous-routine
            if addr in self.labels:
                lbl = self.labels[addr]
                is_sub = lbl.startswith("SUB_")
                sub_class = " sub" if is_sub else ""
                callers = self.xrefs.get(addr, set())
                caller_links = ", ".join(f'<a class="xref-link" href="#{c:04X}" onclick="handleLinkClick(event, \'{addr_hex}\', \'{c:04X}\')">${c:04X}</a>' for c in sorted(callers)[:8])
                caller_tag = f" <span style='font-size:0.8rem; font-weight:normal; color:#8b949e;'>(Appelé par: {caller_links})</span>" if caller_links else ""
                html_lines.append(f"""      <div class="label-header{sub_class}">{lbl}:{caller_tag}</div>""")

            # Traitement de l'opérande avec liens HTML
            op_html = instr["operand"]
            target = instr["target"]

            if target is not None:
                if self.start <= target < self.end:
                    target_hex = f"{target:04X}"
                    # Remplacement de l'adresse par un lien hypertexte
                    if f"${target:04X}" in op_html:
                        op_html = op_html.replace(f"${target:04X}", f'<a class="target-link" href="#{target_hex}" onclick="handleLinkClick(event, \'{addr_hex}\', \'{target_hex}\')">${target_hex}</a>')
                    elif f"${target:02X}" in op_html:
                        op_html = op_html.replace(f"${target:02X}", f'<a class="target-link" href="#{target_hex}" onclick="handleLinkClick(event, \'{addr_hex}\', \'{target_hex}\')">${target:02X}</a>')
                elif target in APPLE2_HARDWARE:
                    hw_sym, _ = APPLE2_HARDWARE[target]
                    op_html += f' <span style="color:var(--c-hw); font-weight:bold;">({hw_sym})</span>'

            # Résolution indirecte JMP ($13xx) => $6000
            if instr["indirect_resolved"] is not None:
                res = instr["indirect_resolved"]
                res_hex = f"{res:04X}"
                if self.start <= res < self.end:
                    op_html += f' <span class="vec-resolved">=&gt;<a class="target-link" href="#{res_hex}" onclick="handleLinkClick(event, \'{addr_hex}\', \'{res_hex}\')">${res_hex}</a></span>'
                else:
                    op_html += f' <span class="vec-resolved">=&gt;${res_hex}</span>'

            # XREFs tag sur l'instruction si elle est appelée
            xrefs_html = ""
            if addr in self.xrefs and addr not in self.labels:
                callers = self.xrefs[addr]
                c_links = ", ".join(f'<a class="xref-link" href="#{c:04X}" onclick="handleLinkClick(event, \'{addr_hex}\', \'{c:04X}\')">${c:04X}</a>' for c in sorted(callers)[:4])
                xrefs_html = f'<span class="xrefs-tag">[de: {c_links}]</span>'

            # Commentaire / Annotation
            comment_html = ""
            comment_class = "line-comment"
            comment_text = self.annotations.get(addr, "")

            # Détection d'accès matériel Apple II si pas de commentaire utilisateur
            if not comment_text and target in APPLE2_HARDWARE:
                _, hw_desc = APPLE2_HARDWARE[target]
                comment_text = hw_desc
                comment_class += " hw"
            elif "CHEAT" in comment_text.upper():
                comment_class += " cheat"

            if comment_text:
                comment_html = f'<span class="{comment_class}">; {comment_text}</span>'

            cat_class = instr["category"]

            html_lines.append(f"""      <div class="code-line" id="{addr_hex}">
        <span class="line-addr"><a href="#{addr_hex}" style="color:inherit; text-decoration:none;" onclick="handleLinkClick(event, null, '{addr_hex}')">{addr_hex}:</a></span>
        <span class="line-bytes">{hex_bytes:<10}</span>
        <span class="line-mnemonic {cat_class}">{instr["mnemonic"]}</span>
        <span class="line-operand">{op_html}</span>
        {xrefs_html}
        {comment_html}
      </div>""")

        html_lines.append("""    </div>

    <!-- Floating Return Toast -->
    <div id="return-toast">
      <span>📍 Téléporté depuis <strong id="return-toast-addr">$0000</strong></span>
      <button id="return-toast-btn" onclick="returnToCaller()">↩ Revenir à l'appelant</button>
      <span onclick="closeReturnToast()" style="cursor:pointer; opacity:0.6; padding:0 4px;" title="Fermer">✕</span>
    </div>
  </main>

  <script>
    // --- Système de Navigation & Historique ---
    let navHistory = [];
    let navHistoryIndex = -1;
    let lastCallerAddr = null;

    function recordJump(fromAddr, targetAddr) {
      if (fromAddr) {
        lastCallerAddr = fromAddr;
        showReturnToast(fromAddr);
      }
      if (navHistoryIndex >= 0 && navHistory[navHistoryIndex] === targetAddr) {
        return;
      }
      if (navHistoryIndex < navHistory.length - 1) {
        navHistory = navHistory.slice(0, navHistoryIndex + 1);
      }
      navHistory.push(targetAddr);
      navHistoryIndex = navHistory.length - 1;
      updateNavUI();
    }

    function showReturnToast(callerAddr) {
      const toast = document.getElementById('return-toast');
      const addrSpan = document.getElementById('return-toast-addr');
      if (toast && addrSpan) {
        addrSpan.textContent = '$' + callerAddr;
        toast.style.display = 'flex';
      }
    }

    function closeReturnToast() {
      const toast = document.getElementById('return-toast');
      if (toast) toast.style.display = 'none';
    }

    function returnToCaller() {
      if (lastCallerAddr) {
        closeReturnToast();
        jumpTo(lastCallerAddr, true, null);
      }
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
          return `<span class="trail-item ${isCurrent ? 'current' : ''}" onclick="jumpToHistoryIndex(${actualIdx})">$${addr}</span>`;
        }).join(' <span style="color:#6e7681;">➜</span> ');
      }
    }

    function navBack() {
      if (navHistoryIndex > 0) {
        navHistoryIndex--;
        let addr = navHistory[navHistoryIndex];
        jumpTo(addr, false);
        updateNavUI();
      } else {
        window.history.back();
      }
    }

    function navForward() {
      if (navHistoryIndex < navHistory.length - 1) {
        navHistoryIndex++;
        let addr = navHistory[navHistoryIndex];
        jumpTo(addr, false);
        updateNavUI();
      } else {
        window.history.forward();
      }
    }

    function jumpToHistoryIndex(idx) {
      if (idx >= 0 && idx < navHistory.length) {
        navHistoryIndex = idx;
        let addr = navHistory[idx];
        jumpTo(addr, false);
        updateNavUI();
      }
    }

    function highlightLine(addr) {
      document.querySelectorAll('.code-line.active').forEach(el => el.classList.remove('active'));
      const el = document.getElementById(addr);
      if (el) {
        el.classList.add('active');
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    function jumpTo(addr, addToHistory = true, fromAddr = null) {
      if (!addr) return;
      addr = addr.replace('#', '').replace('$', '').toUpperCase();
      if (addr.length < 4) addr = addr.padStart(4, '0');

      const el = document.getElementById(addr);
      if (el) {
        highlightLine(addr);
        if (addToHistory) {
          recordJump(fromAddr, addr);
          if (window.location.hash.substring(1).toUpperCase() !== addr) {
            history.pushState({ addr: addr }, '', '#' + addr);
          }
        }
      } else {
        alert('Adresse introuvable dans le binaire : $' + addr);
      }
    }

    function handleLinkClick(e, fromAddr, targetAddr) {
      if (e) e.preventDefault();
      jumpTo(targetAddr, true, fromAddr);
    }

    function jumpToAddress() {
      const input = document.getElementById('jump-input').value.trim().toUpperCase();
      if (!input) return;
      let addr = input.replace('$', '');
      if (addr.length < 4) addr = addr.padStart(4, '0');
      jumpTo(addr, true, null);
    }

    document.getElementById('jump-input').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') jumpToAddress();
    });

    function filterCode() {
      const q = document.getElementById('filter-input').value.toLowerCase().trim();
      const lines = document.querySelectorAll('.code-line');
      if (!q) {
        lines.forEach(l => l.style.display = 'flex');
        return;
      }
      lines.forEach(l => {
        const text = l.textContent.toLowerCase();
        l.style.display = text.includes(q) ? 'flex' : 'none';
      });
    }

    function clearFilter() {
      document.getElementById('filter-input').value = '';
      filterCode();
    }

    // Support natif des flèches Retour / Avance du navigateur web
    window.addEventListener('hashchange', function() {
      const h = window.location.hash.substring(1).toUpperCase();
      if (h) {
        jumpTo(h, false);
      }
    });

    window.addEventListener('popstate', function(e) {
      const h = window.location.hash.substring(1).toUpperCase();
      if (h) {
        jumpTo(h, false);
      }
    });

    // Raccourcis clavier : Alt + Flèche Gauche (Retour) / Alt + Flèche Droite (Avance)
    window.addEventListener('keydown', function(e) {
      if (e.altKey && e.key === 'ArrowLeft') {
        e.preventDefault();
        navBack();
      } else if (e.altKey && e.key === 'ArrowRight') {
        e.preventDefault();
        navForward();
      }
    });

    // Gestion du hash initial au chargement
    window.addEventListener('load', function() {
      let h = window.location.hash.substring(1).toUpperCase();
      if (h) {
        jumpTo(h, true, null);
      }
    });
  </script>
</body>
</html>
""")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html_lines))
        print(f"[+] Rapport interactif HTML créé avec succès ({len(html_lines):,} lignes) : {output_path}")


# =============================================================================
# INTERFACE GRAPHIQUE TKINTER (GUI)
# =============================================================================
def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title("bin2text - 6502 Disassembler & Reverse Engineering")
    root.geometry("640x480")
    root.configure(bg="#1e1e1e")

    bin_path_var = tk.StringVar()
    ann_path_var = tk.StringVar()
    start_addr_var = tk.StringVar(value="0800")
    title_var = tk.StringVar(value="6502 Reverse Engineering")
    out_path_var = tk.StringVar()

    def browse_bin():
        p = filedialog.askopenfilename(title="Choisir le fichier binaire", filetypes=[("Fichiers binaires", "*.bin;*.rom;*.dsk;*.*")])
        if p:
            bin_path_var.set(p)
            if not out_path_var.get():
                out_path_var.set(os.path.splitext(p)[0] + "_reverse.html")

    def browse_ann():
        p = filedialog.askopenfilename(title="Choisir les annotations (JSON ou TXT)", filetypes=[("Annotations", "*.json;*.txt")])
        if p:
            ann_path_var.set(p)

    def browse_out():
        p = filedialog.asksaveasfilename(title="Enregistrer sous", defaultextension=".html", filetypes=[("HTML", "*.html")])
        if p:
            out_path_var.set(p)

    def execute_disasm():
        bp = bin_path_var.get().strip()
        if not bp or not os.path.exists(bp):
            messagebox.showerror("Erreur", "Veuillez sélectionner un fichier binaire valide.")
            return

        try:
            start_addr = int(start_addr_var.get().strip(), 16)
        except ValueError:
            messagebox.showerror("Erreur", "L'adresse de départ doit être en hexadécimal (ex: 0800, 0A00).")
            return

        op = out_path_var.get().strip() or os.path.splitext(bp)[0] + "_reverse.html"

        with open(bp, "rb") as f:
            data = f.read()

        disasm = Disassembler6502(data, start_addr)
        ap = ann_path_var.get().strip()
        if ap and os.path.exists(ap):
            disasm.load_annotations(ap)

        disasm.pass1_decode()
        disasm.pass2_labels()
        disasm.generate_html(op, title=title_var.get().strip())

        res = messagebox.askyesno("Succès", f"Désassemblage HTML terminé !\n{op}\n\nOuvrir dans le navigateur ?")
        if res:
            import webbrowser
            webbrowser.open(op)

    # UI Widgets
    title_lbl = tk.Label(root, text="Désassembleur MOS 6502 & Reverse HTML", font=("Arial", 14, "bold"), fg="#58a6ff", bg="#1e1e1e")
    title_lbl.pack(pady=15)

    frame = tk.Frame(root, bg="#1e1e1e")
    frame.pack(fill="both", expand=True, padx=25)

    # Binary file
    tk.Label(frame, text="Fichier Binaire :", fg="#c9d1d9", bg="#1e1e1e").grid(row=0, column=0, sticky="w", pady=6)
    tk.Entry(frame, textvariable=bin_path_var, width=45, bg="#2d2d2d", fg="#fff").grid(row=0, column=1, padx=6)
    tk.Button(frame, text="Parcourir...", command=browse_bin, bg="#333", fg="#fff").grid(row=0, column=2)

    # Start address
    tk.Label(frame, text="Adresse de départ (Hex) :", fg="#c9d1d9", bg="#1e1e1e").grid(row=1, column=0, sticky="w", pady=6)
    tk.Entry(frame, textvariable=start_addr_var, width=15, bg="#2d2d2d", fg="#fff").grid(row=1, column=1, sticky="w", padx=6)

    # Annotations file
    tk.Label(frame, text="Fichier Annotations (Optionnel) :", fg="#c9d1d9", bg="#1e1e1e").grid(row=2, column=0, sticky="w", pady=6)
    tk.Entry(frame, textvariable=ann_path_var, width=45, bg="#2d2d2d", fg="#fff").grid(row=2, column=1, padx=6)
    tk.Button(frame, text="Parcourir...", command=browse_ann, bg="#333", fg="#fff").grid(row=2, column=2)

    # HTML Title
    tk.Label(frame, text="Titre de la page :", fg="#c9d1d9", bg="#1e1e1e").grid(row=3, column=0, sticky="w", pady=6)
    tk.Entry(frame, textvariable=title_var, width=45, bg="#2d2d2d", fg="#fff").grid(row=3, column=1, padx=6)

    # Output file
    tk.Label(frame, text="Fichier HTML de sortie :", fg="#c9d1d9", bg="#1e1e1e").grid(row=4, column=0, sticky="w", pady=6)
    tk.Entry(frame, textvariable=out_path_var, width=45, bg="#2d2d2d", fg="#fff").grid(row=4, column=1, padx=6)
    tk.Button(frame, text="Parcourir...", command=browse_out, bg="#333", fg="#fff").grid(row=4, column=2)

    btn_exec = tk.Button(root, text="🚀 Générer le Reverse HTML Interactif", font=("Arial", 11, "bold"), bg="#238636", fg="#fff", padx=15, pady=8, command=execute_disasm)
    btn_exec.pack(pady=20)

    root.mainloop()


# =============================================================================
# CLI ENTRY POINT
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Désassembleur MOS 6502 & Générateur de Reverse Engineering Interactif HTML")
    parser.add_argument("binary", nargs="?", help="Chemin vers le fichier binaire à désassembler")
    parser.add_argument("start_address", nargs="?", help="Adresse de départ en hexadécimal (ex: 0800, 0A00, 6000)")
    parser.add_argument("output", nargs="?", help="Chemin du fichier HTML de sortie")
    parser.add_argument("--annotations", "-a", help="Chemin vers le fichier d'annotations (JSON ou texte)")
    parser.add_argument("--title", "-t", default="6502 Reverse Engineering", help="Titre du rapport HTML")
    parser.add_argument("--gui", "-g", action="store_true", help="Lancer l'interface graphique Tkinter")

    args = parser.parse_args()

    # Si aucun argument ou flag --gui, lance la GUI
    if args.gui or (not args.binary and not args.start_address):
        launch_gui()
        return

    bin_path = args.binary
    if not os.path.exists(bin_path):
        print(f"[-] Erreur : Fichier binaire introuvable : {bin_path}")
        sys.exit(1)

    try:
        start_addr = int(args.start_address, 16)
    except (ValueError, TypeError):
        print(f"[-] Erreur : Adresse de départ invalide '{args.start_address}'. Spécifiez un hexadécimal (ex: 0800, 0A00).")
        sys.exit(1)

    out_path = args.output or (os.path.splitext(bin_path)[0] + "_reverse.html")

    with open(bin_path, "rb") as f:
        data = f.read()

    print(f"[*] Chargement du binaire : {bin_path} ({len(data):,} octets, ${start_addr:04X} à ${start_addr + len(data) - 1:04X})")

    disasm = Disassembler6502(data, start_addr)
    if args.annotations and os.path.exists(args.annotations):
        disasm.load_annotations(args.annotations)
        print(f"[*] Annotations chargées depuis : {args.annotations} ({len(disasm.annotations)} entrées)")

    disasm.pass1_decode()
    disasm.pass2_labels()
    disasm.generate_html(out_path, title=args.title)


if __name__ == "__main__":
    main()