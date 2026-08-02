#!/usr/bin/env python3
"""Compare config/corne.keymap against the Vial .vil export.

Both boards are meant to carry the same layout, so this reports any cell
where they have drifted apart. Run it after editing either side.

  ./tools/check-vil-parity.py [path/to/export.vil]

Exits non-zero if the two disagree outside the known-divergence list.
"""
import json, re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
VIL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, '..', 'vial', 'promethium.vil')
KEYMAP = os.path.join(HERE, '..', 'config', 'corne.keymap')

# LAYOUT_split_3x6_3 matrix order, from the unicorne keyboard.json.
ORDER = ([(0, c) for c in range(6)] + [(4, c) for c in [5, 4, 3, 2, 1, 0]] +
         [(1, c) for c in range(6)] + [(5, c) for c in [5, 4, 3, 2, 1, 0]] +
         [(2, c) for c in range(6)] + [(6, c) for c in [5, 4, 3, 2, 1, 0]] +
         [(3, 3), (3, 4), (3, 5), (7, 5), (7, 4), (7, 3)])

# Cells that differ on purpose. position -> why.
ALLOWED = {
    (3, p): 'wireless system row, dead (KC_NO) on the wired board'
    for p in range(12)
}

SIMPLE = {
    'TRNS': '&trans', 'NO': '&none',
    'TAB': '&kp TAB', 'ESCAPE': '&kp ESC', 'BSPACE': '&kp BSPC',
    'ENTER': '&kp RET', 'SPACE': '&kp SPACE', 'DELETE': '&kp DEL',
    'MINUS': '&kp MINUS', 'EQUAL': '&kp EQUAL', 'QUOTE': '&kp SQT',
    'SLASH': '&kp FSLH', 'SCOLON': '&kp SEMI', 'COMMA': '&kp COMMA',
    'DOT': '&kp DOT', 'GRAVE': '&kp GRAVE', 'BSLASH': '&kp BSLH',
    'LBRACKET': '&kp LBKT', 'RBRACKET': '&kp RBKT',
    'CAPSLOCK': '&kp CAPS', 'INSERT': '&kp INS', 'HOME': '&kp HOME',
    'END': '&kp END', 'PGUP': '&kp PG_UP', 'PGDOWN': '&kp PG_DN',
    'LEFT': '&kp LEFT', 'RIGHT': '&kp RIGHT', 'UP': '&kp UP', 'DOWN': '&kp DOWN',
    'NUMLOCK': '&kp KP_NUM', 'PSCREEN': '&kp PSCRN',
    'KP_SLASH': '&kp KP_DIVIDE', 'KP_ASTERISK': '&kp KP_MULTIPLY',
    'KP_PLUS': '&kp KP_PLUS', 'KP_MINUS': '&kp KP_MINUS',
    'KP_EQUAL': '&kp KP_EQUAL',
    'LSHIFT': '&kp LSHFT', 'LCTRL': '&kp LCTRL', 'LALT': '&kp LALT',
    'LGUI': '&kp LGUI', 'RSHIFT': '&kp RSHFT', 'RCTRL': '&kp RCTRL',
    'RALT': '&kp RALT', 'RGUI': '&kp RGUI',
    'MUTE': '&kp C_MUTE', 'MPLY': '&kp C_PP', 'MPRV': '&kp C_PREV',
    'MNXT': '&kp C_NEXT', 'VOLD': '&kp C_VOL_DN', 'VOLU': '&kp C_VOL_UP',
    'CUT': '&kp K_CUT', 'COPY': '&kp K_COPY', 'PSTE': '&kp K_PASTE',
    'UNDO': '&kp K_UNDO', 'AGIN': '&kp K_AGAIN',
    'BTN1': '&mkp LCLK', 'BTN2': '&mkp RCLK', 'BTN3': '&mkp MCLK',
    'MS_L': '&mmv MOVE_LEFT', 'MS_R': '&mmv MOVE_RIGHT',
    'MS_U': '&mmv MOVE_UP', 'MS_D': '&mmv MOVE_DOWN',
    'M0': '&qu', 'M1': '&alt_tab', 'TD(0)': '&td0',
}
SIMPLE.update({'F%d' % n: '&kp F%d' % n for n in range(1, 25)})
SIMPLE.update({str(n): '&kp N%d' % n for n in range(10)})
SIMPLE.update({c: '&kp ' + c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'})

SHIFTED = {
    'COMMA': 'LT', 'QUOTE': 'DQT', 'DOT': 'GT', '4': 'DLLR', 'MINUS': 'UNDER',
    '1': 'EXCL', '9': 'LPAR', '0': 'RPAR', '3': 'HASH', '5': 'PRCNT',
    'LBRACKET': 'LBRC', 'RBRACKET': 'RBRC', 'SCOLON': 'COLON', 'SLASH': 'QMARK',
    'BSLASH': 'PIPE', '8': 'ASTRK', 'EQUAL': 'PLUS', '2': 'AT', '7': 'AMPS',
    '6': 'CARET', 'GRAVE': 'TILDE',
}
# Home-row mods: which behavior each hand uses.
HRM = {p: '&hml' for p in (13, 14, 15, 16)}
HRM.update({p: '&hmr' for p in (19, 20, 21, 22)})

# Same modifier, different spelling between the two firmwares.
MOD_ALIAS = {'LCTL': 'LCTRL', 'RCTL': 'RCTRL', 'LSFT': 'LSHFT', 'RSFT': 'RSHFT'}


def vil_to_zmk(kc, pos):
    """Translate one QMK keycode to the ZMK binding we expect. None = unknown."""
    k = kc.replace('KC_', '')
    if k in SIMPLE:
        return SIMPLE[k]
    m = re.fullmatch(r'LSFT\((?:KC_)?(\w+)\)', kc)
    if m and m.group(1) in SHIFTED:
        return '&kp ' + SHIFTED[m.group(1)]
    m = re.fullmatch(r'LT(\d+)\(KC_(\w+)\)', kc)
    if m:
        tap = SIMPLE.get(m.group(2), '')
        return '&ltb %s %s' % (m.group(1), tap.replace('&kp ', ''))
    m = re.fullmatch(r'MO\((\d+)\)', kc)
    if m:
        return '&mo ' + m.group(1)
    m = re.fullmatch(r'TG\((\d+)\)', kc)
    if m:
        return '&tog ' + m.group(1)
    m = re.fullmatch(r'OSL\((\d+)\)', kc)
    if m:
        return '&sl ' + m.group(1)
    m = re.fullmatch(r'(\w+)_T\(KC_(\w+)\)', kc)
    if m and pos in HRM:
        mod = MOD_ALIAS.get(m.group(1), m.group(1))
        return '%s %s %s' % (HRM[pos], mod, m.group(2))
    return None


def load_zmk():
    src = re.sub(r'//[^\n]*', '', open(KEYMAP).read())
    kmap = src[src.index('keymap {'):]
    out = []
    for _, body in re.findall(r'(\w+_layer)\s*\{.*?bindings\s*=\s*<(.*?)>;',
                              kmap, re.S):
        toks = [' '.join(t.split()) for t in
                re.findall(r'&\w+(?:\s+(?!&)[A-Za-z0-9_()]+)*', body)]
        out.append(toks)
    return out


def main():
    vil = json.load(open(VIL))
    zmk = load_zmk()
    mismatches, unknown = [], []
    for L, layer in enumerate(zmk):
        if L >= len(vil['layout']):
            break
        for pos, (r, c) in enumerate(ORDER):
            want = vil_to_zmk(vil['layout'][L][r][c], pos)
            got = layer[pos]
            if want is None:
                unknown.append((L, pos, vil['layout'][L][r][c], got))
            elif want != got and (L, pos) not in ALLOWED:
                mismatches.append((L, pos, vil['layout'][L][r][c], want, got))

    for L, pos, kc, want, got in mismatches:
        print('DRIFT  layer %d pos %-2d  vil=%-18s expected %-18s zmk=%s'
              % (L, pos, kc, want, got))
    for L, pos, kc, got in unknown:
        print('?      layer %d pos %-2d  vil=%-18s zmk=%s  (no mapping)'
              % (L, pos, kc, got))
    if ALLOWED:
        print('\n%d cells skipped as intentional:' % len(ALLOWED))
        for why in sorted(set(ALLOWED.values())):
            print('  -', why)
    print('\n%d drifted, %d unmapped' % (len(mismatches), len(unknown)))
    return 1 if mismatches else 0


if __name__ == '__main__':
    sys.exit(main())
