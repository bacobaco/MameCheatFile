import os
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_MASTER_PATH = r"D:\Emulateurs\AppleWin\roms\AppleSauce\DOS 3.3 SYSTEM MASTER (Animals).dsk"
ORIG_DSK_PATH = os.path.join(SCRIPT_DIR, "Jungle Hunt (1982)(Atari)[cr Crack Elite Soft].dsk")
OUTPUT_DSK = os.path.join(SCRIPT_DIR, "Jungle Hunt (DOS 3.3).dsk")

with open(SYSTEM_MASTER_PATH, 'rb') as f:
    master = f.read()

with open(ORIG_DSK_PATH, 'rb') as f:
    orig = f.read()

def get_sec(d, t, s):
    return d[(t * 16 + s) * 256 : (t * 16 + s + 1) * 256]

# Create new 140KB disk image
new_dsk = bytearray(143360)

def put_sec(d, t, s, data):
    assert len(data) == 256
    d[(t * 16 + s) * 256 : (t * 16 + s + 1) * 256] = data

# 1. Copy pristine Apple DOS 3.3 tracks 0, 1, 2 from official System Master
for t in range(3):
    for s in range(16):
        put_sec(new_dsk, t, s, get_sec(master, t, s))

# 2. Copy Track 17 (VTOC and full catalog skeleton) from System Master
for s in range(16):
    put_sec(new_dsk, 17, s, get_sec(master, 17, s))

# Clear all file entries in catalog sectors 15 down to 1
# Keeping the standard link pointers in bytes 1 and 2!
for s in range(1, 16):
    off = (17 * 16 + s) * 256
    next_t = new_dsk[off + 1]
    next_s = new_dsk[off + 2]
    new_dsk[off : off + 256] = b'\x00' * 256
    new_dsk[off + 1] = next_t
    new_dsk[off + 2] = next_s

# 3. Copy game raw streaming tracks from original Jungle Hunt disk:
# Tracks 3..13 (Levels 1..4 + Hi-Res screen for in-game $1D00 / RWTS)
for t in range(3, 14):
    for s in range(16):
        put_sec(new_dsk, t, s, get_sec(orig, t, s))

# Tracks 25..28 (Engine $0A00 and Routines $6000 raw sectors)
for t in range(25, 29):
    for s in range(16):
        put_sec(new_dsk, t, s, get_sec(orig, t, s))

# 4. Set up VTOC track allocation map
# 1 = free, 0 = used.
track_free_masks = [0xFFFF] * 35

# Mark system tracks, in-game raw tracks, and VTOC as used:
for t in list(range(3)) + list(range(3, 14)) + [17] + list(range(25, 29)):
    track_free_masks[t] = 0x0000

def allocate_sector():
    # Standard DOS 3.3 search order
    search_tracks = list(range(18, 25)) + list(range(29, 35)) + list(range(16, 13, -1))
    for t in search_tracks:
        mask = track_free_masks[t]
        if mask == 0:
            continue
        for s in range(15, -1, -1):
            if (mask & (1 << s)) != 0:
                track_free_masks[t] &= ~(1 << s)
                return (t, s)
    raise RuntimeError("Erreur : Disque plein !")

# Extract original components
# 1. Main Engine
jungle_main = bytearray()
for sec in range(15, -1, -1):
    jungle_main.extend(get_sec(orig, 25, sec))
for sec in range(15, 8, -1):
    jungle_main.extend(get_sec(orig, 26, sec))

# 2. Data / Routines
jungle_data = bytearray()
for sec in range(15, -1, -1):
    jungle_data.extend(get_sec(orig, 27, sec))
for sec in range(15, 6, -1):
    jungle_data.extend(get_sec(orig, 28, sec))

# 3. Title Screen
jungle_pic = bytearray()
for trk in [12, 13]:
    for sec in range(15, -1, -1):
        jungle_pic.extend(get_sec(orig, trk, sec))

# 4. Levels 1 to 4
level1 = bytearray()
for trk in [3, 4]:
    for sec in range(15, -1, -1):
        level1.extend(get_sec(orig, trk, sec))

level2 = bytearray()
for trk in [5, 6, 7]:
    for sec in range(15, -1, -1):
        level2.extend(get_sec(orig, trk, sec))

level3 = bytearray()
for trk in [8, 9]:
    for sec in range(15, -1, -1):
        level3.extend(get_sec(orig, trk, sec))

level4 = bytearray()
for trk in [10, 11]:
    for sec in range(15, -1, -1):
        level4.extend(get_sec(orig, trk, sec))

# 5. Build HELLO Applesoft BASIC program
lines = [
    (10, bytes([0x89, ord(':'), 0x97])), # TEXT : HOME
    (20, bytes([0xBA, ord('"'), *b"========================================", ord('"')])),
    (30, bytes([0xBA, ord('"'), *b"          JUNGLE HUNT (1982)            ", ord('"')])),
    (40, bytes([0xBA, ord('"'), *b"   ATARI CORP. / TAITO AMERICA CORP.    ", ord('"')])),
    (50, bytes([0xBA, ord('"'), *b"========================================", ord('"')])),
    (60, bytes([0xBA])),
    (70, bytes([0xBA, ord('"'), *b"CHARGEMENT DU MOTEUR ($0A00)...", ord('"')])),
    (80, bytes([0xBA, 0xE7, ord('('), ord('4'), ord(')'), ord(';'), ord('"'), *b"BLOAD JUNGLE.MAIN", ord('"')])),
    (90, bytes([0xBA, ord('"'), *b"CHARGEMENT DES DONNEES ($6000)...", ord('"')])),
    (100, bytes([0xBA, 0xE7, ord('('), ord('4'), ord(')'), ord(';'), ord('"'), *b"BLOAD JUNGLE.DATA", ord('"')])),
    (110, bytes([0xBA, ord('"'), *b"LANCEMENT DE JUNGLE HUNT...", ord('"')])),
    (120, bytes([0xBA, 0xE7, ord('('), ord('4'), ord(')'), ord(';'), ord('"'), *b"BRUN JUNGLE HUNT", ord('"')])),
]
cur_addr = 0x0801
hello_basic = bytearray()
for lnum, ldata in lines:
    line_len = 2 + 2 + len(ldata) + 1
    next_addr = cur_addr + line_len
    hello_basic.extend(struct.pack('<HH', next_addr, lnum))
    hello_basic.extend(ldata)
    hello_basic.append(0x00)
    cur_addr = next_addr
hello_basic.extend(b'\x00\x00')

# 6. Binary for JUNGLE HUNT ($4000)
# Original 139-byte loader from track 19 sec 14:
orig_file_a = get_sec(orig, 19, 14)[4:4+139]
jungle_hunt_bin = bytearray(orig_file_a)

# Files to add:
files_to_add = [
    ("HELLO",        0x02, hello_basic,     None),
    ("JUNGLE HUNT",  0x04, jungle_hunt_bin, 0x4000),
    ("JUNGLE.MAIN",  0x04, jungle_main,     0x0A00),
    ("JUNGLE.DATA",  0x04, jungle_data,     0x6000),
    ("JUNGLE.PIC",   0x04, jungle_pic,      0x2000),
    ("LEVEL1.BIN",   0x04, level1,          0x7700),
    ("LEVEL2.BIN",   0x04, level2,          0x7700),
    ("LEVEL3.BIN",   0x04, level3,          0x7700),
    ("LEVEL4.BIN",   0x04, level4,          0x7700),
]

catalog_entries = []

for name, ftype, raw_data, load_addr in files_to_add:
    if ftype == 0x02: # Applesoft
        payload = struct.pack('<H', len(raw_data)) + raw_data
    elif ftype == 0x04: # Binary
        payload = struct.pack('<HH', load_addr, len(raw_data)) + raw_data
    else:
        payload = raw_data

    # Allocate data sectors
    data_sectors = []
    offset = 0
    while offset < len(payload):
        chunk = payload[offset : offset + 256]
        t, s = allocate_sector()
        data_sectors.append((t, s))
        sec_buf = bytearray(256)
        sec_buf[:len(chunk)] = chunk
        put_sec(new_dsk, t, s, bytes(sec_buf))
        offset += len(chunk)

    # Allocate T/S list sector
    ts_t, ts_s = allocate_sector()
    ts_buf = bytearray(256)
    ts_buf[1] = 0x00
    ts_buf[2] = 0x00
    ts_buf[5] = 0x00
    ts_buf[6] = 0x00
    for idx, (dt, ds) in enumerate(data_sectors):
        ts_buf[0x0C + idx * 2] = dt
        ts_buf[0x0C + idx * 2 + 1] = ds
    put_sec(new_dsk, ts_t, ts_s, bytes(ts_buf))

    total_sectors = len(data_sectors) + 1

    entry = bytearray(0x23)
    entry[0] = ts_t
    entry[1] = ts_s
    entry[2] = ftype | 0x80 # Locked
    padded_name = name.ljust(30)[:30]
    for i, c in enumerate(padded_name):
        entry[3 + i] = ord(c) | 0x80
    entry[33] = total_sectors & 0xFF
    entry[34] = (total_sectors >> 8) & 0xFF

    catalog_entries.append((name, ftype, total_sectors, entry))

# Write entries into catalog sectors 15 down to 1
cat_s = 15
entry_idx = 0
for _, _, _, e_bytes in catalog_entries:
    sec_offset = (17 * 16 + cat_s) * 256
    slot_in_sec = entry_idx % 7
    entry_pos = sec_offset + 0x0B + slot_in_sec * 0x23
    new_dsk[entry_pos : entry_pos + 0x23] = e_bytes
    entry_idx += 1
    if entry_idx % 7 == 0:
        cat_s -= 1

# Update VTOC on Track 17 Sector 0
vtoc_off = 17 * 16 * 256
# Keep original system master VTOC bytes 0..0x37
# Update allocation map at 0x38..0xC3:
for t in range(35):
    off = vtoc_off + 0x38 + t * 4
    mask = track_free_masks[t]
    new_dsk[off] = (mask >> 8) & 0xFF
    new_dsk[off + 1] = mask & 0xFF
    new_dsk[off + 2] = 0x00
    new_dsk[off + 3] = 0x00

with open(OUTPUT_DSK, 'wb') as f:
    f.write(new_dsk)

print(f"Disquette générée avec succès : {OUTPUT_DSK}")
print(f"Secteurs libres restants : {sum(bin(m).count('1') for m in track_free_masks)}")
