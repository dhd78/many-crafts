"""生成梁文艳论文图 4-1(d)：Fe47X1 的 (1-11)[1-12] 滑移体系表面模型。

依据（第 4 章 4.2 节，PDF 第 34 页）：
- Fe48 体材料超胞：x = [11-2]、y = [1-10]、z = [111]，
  尺寸 √6/2 a × √2 a × 4√3 a，共 48 个原子（12 层 (111) 面）；
- 第 7 层中的一个 Fe 被 X 原子替换，形成 Fe47X1；
- 表面模型在 z 方向加 15 Å 真空层，保持 12 层。
晶格常数取 a = 3.60 Å（论文未在本页给出，属合理近似）。
"""

import argparse
import os
import re

import numpy as np

A = 3.60
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, '..', '..', 'templates', 'template.vesta')
OUT_DIR = HERE

FE_COLOR = (230, 160, 40)
X_COLOR = (150, 80, 190)
FE_RADIUS = 1.50
X_RADIUS = 1.38
X_SYMBOL = 'Mo'          # 论文里 X = Cr, Mo, Ni, Pb, Bi；这里取 Mo 作为示例
X_LAYER = 7              # 第 7 层（从 1 开始）
VACUUM = 15.0
Z_OFFSET = 0.4           # 让底层离开 c 轴边界，避免顶部出现周期镜像


def slab_atoms():
    """枚举超胞内的 fcc 原子；返回 [(u, v, w, layer)] 和晶胞参数。"""
    xv = A / 2.0 * np.array([1.0, 1.0, -2.0])   # [11-2] 方向，长度 √6/2 a
    yv = A * np.array([1.0, -1.0, 0.0])          # [1-10] 方向，长度 √2 a
    zv = A * 4.0 * np.array([1.0, 1.0, 1.0])     # [111] 方向，4√3 a
    matrix = np.column_stack([xv, yv, zv])
    inv = np.linalg.inv(matrix)

    basis = [(0, 0, 0), (0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5)]
    atoms = []
    for i in range(-4, 9):
        for j in range(-4, 9):
            for k in range(-4, 9):
                for bx, by, bz in basis:
                    p = A * np.array([i + bx, j + by, k + bz])
                    u, v, w = inv @ p
                    if -1e-6 <= u < 1 - 1e-6 and -1e-6 <= v < 1 - 1e-6 and -1e-6 <= w < 1 - 1e-6:
                        atoms.append((u, v, w, int(round(w * 12)) + 1))

    thickness = float(np.linalg.norm(zv))
    c_total = Z_OFFSET + thickness + VACUUM
    cell = [float(np.linalg.norm(xv)), float(np.linalg.norm(yv)), c_total, 90.0, 90.0, 90.0]
    out = [(u, v, (Z_OFFSET + w * thickness) / c_total, layer) for (u, v, w, layer) in atoms]
    out.sort(key=lambda t: (t[3], round(t[0], 4), round(t[1], 4)))
    return out, cell


def choose_x_site(atoms):
    """在目标层里挑一个面内中心、且朝向观察者一侧的原子。

    第 7 层的四个位点是 (0,0)、(0,0.5)、(0.5,0.25)、(0.5,0.75)；
    其中 (0.5,0.25) 与 (0.5,0.75) 相差 a/2[1-10] 的平移，是等价位点，
    取 v=0.75 的位点可以避免被同列的 Fe 挡住。
    """
    candidates = [atom for atom in atoms if atom[3] == X_LAYER]
    if not candidates:
        raise RuntimeError(f'第 {X_LAYER} 层没有原子')
    centered = [atom for atom in candidates if abs(atom[0] - 0.5) < 0.01]
    pool = centered if centered else candidates
    return max(pool, key=lambda t: t[1])


HEADERS = {
    'CRYSTAL', 'TITLE', 'GROUP', 'SYMOP', 'TRANM', 'LTRANSL', 'LORIENT', 'LMATRIX',
    'PHASON', 'CELLP', 'STRUC', 'THERI', 'SHAPE', 'BOUND', 'QCORIG', 'SBOND', 'SITET',
    'VECTR', 'VECTT', 'SPLAN', 'LBLAT', 'LBLSP', 'DLATM', 'DLBND', 'DLPLY', 'PLN2D',
    'ATOMT', 'SCENE', 'STYLE', 'DISPF', 'MODEL', 'SURFS', 'SECTS', 'FORMS', 'ATOMS',
    'BONDS', 'POLYS', 'VECTS', 'FORMP', 'ATOMP', 'BONDP', 'POLYP', 'ISURF', 'TEX3P',
    'SECTP', 'CONTR', 'HKLPP', 'UCOLP', 'COMPS', 'LABEL', 'PROJT', 'BKGRC', 'DPTHQ',
    'LIGHT0', 'LIGHT1', 'LIGHT2', 'LIGHT3', 'SECCL', 'TEXCL', 'ATOMM', 'BONDM',
    'POLYM', 'SURFM', 'FORMM', 'HKLPM', 'HBOND',
}


def find_header(lines, name):
    for i, line in enumerate(lines):
        token = line.strip().split()
        if token and token[0] == name:
            return i
    raise ValueError(f'场景缺少 {name} 段')


def replace_section(lines, name, body):
    start = find_header(lines, name)
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line and not line[0].isspace():
            token = line.split()
            if token and token[0] in HEADERS:
                break
        end += 1
    return lines[:start + 1] + body + lines[end:]


def build_scene(title, atoms, cell, x_index):
    with open(TEMPLATE, 'r', encoding='utf-8') as handle:
        text = handle.read()
    newline = '\r\n' if '\r\n' in text else '\n'
    lines = re.split(r'\r?\n', text)

    struct, theri, sited = [], [], []
    for index, (x, y, z, layer) in enumerate(atoms, start=1):
        label = f'Fe{index}'
        if index == x_index:
            symbol, radius, color = X_SYMBOL, X_RADIUS, X_COLOR
        else:
            symbol, radius, color = 'Fe', FE_RADIUS, FE_COLOR
        r, g, b = color
        struct.append(f'  {index} {symbol:<9}{label:<6}  1.0000   {x:.6f}   {y:.6f}   {z:.6f}    1a       1')
        struct.append('                             0.000000   0.000000   0.000000  0.00')
        theri.append(f'  {index}        {label} -0.000000')
        sited.append(f'  {index}        {label}  {radius:.4f} {r:3d} {g:3d} {b:3d} {r:3d} {g:3d} {b:3d} 204  0')
    struct.append('  0 0 0 0 0 0 0')
    theri.append('  0 0 0')
    sited.append('  0 0 0 0 0 0')
    atomt = [
        f'  1         Fe  {FE_RADIUS:.4f} {FE_COLOR[0]:3d} {FE_COLOR[1]:3d} {FE_COLOR[2]:3d} '
        f'{FE_COLOR[0]:3d} {FE_COLOR[1]:3d} {FE_COLOR[2]:3d} 204',
        f'  2        {X_SYMBOL}  {X_RADIUS:.4f} {X_COLOR[0]:3d} {X_COLOR[1]:3d} {X_COLOR[2]:3d} '
        f'{X_COLOR[0]:3d} {X_COLOR[1]:3d} {X_COLOR[2]:3d} 204',
        '  0 0 0 0 0 0',
    ]

    lines = replace_section(lines, 'TITLE', [title])
    lines = replace_section(lines, 'CELLP', [
        '  ' + '  '.join(f'{value:.6f}' for value in cell[:3]) + '  ' + '  '.join(f'{value:.6f}' for value in cell[3:]),
        '  0.000000   0.000000   0.000000   0.000000   0.000000   0.000000',
    ])
    lines = replace_section(lines, 'STRUC', struct)
    lines = replace_section(lines, 'THERI', theri)
    lines = replace_section(lines, 'SBOND', ['  0 0 0 0'])
    lines = replace_section(lines, 'SITET', sited)
    lines = replace_section(lines, 'ATOMT', atomt)
    lines = replace_section(lines, 'BOUND', ['0 1 0 1 0 1 ', '  0   0   0   0  0'])
    return newline.join(lines)


def write_cif(path, atoms, cell, x_index, title):
    a, b, c, alpha, beta, gamma = cell
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(f'data_{title}\n')
        handle.write(f"_chemical_formula_sum 'Fe47{X_SYMBOL}'\n")
        handle.write(f'_cell_length_a {a:.6f}\n_cell_length_b {b:.6f}\n_cell_length_c {c:.6f}\n')
        handle.write(f'_cell_angle_alpha {alpha}\n_cell_angle_beta {beta}\n_cell_angle_gamma {gamma}\n')
        handle.write("_symmetry_space_group_name_H-M 'P 1'\n_symmetry_Int_Tables_number 1\n")
        handle.write("loop_\n_symmetry_equiv_pos_as_xyz\n'x, y, z'\n")
        handle.write('loop_\n_atom_site_label\n_atom_site_type_symbol\n')
        handle.write('_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n')
        for index, (x, y, z, _layer) in enumerate(atoms, start=1):
            symbol = X_SYMBOL if index == x_index else 'Fe'
            handle.write(f'{symbol}{index} {symbol} {x:.6f} {y:.6f} {z:.6f} 1\n')


def main():
    global TEMPLATE, OUT_DIR
    parser = argparse.ArgumentParser(description='Build VESTA scenes for the Fe47X1 surface figure')
    parser.add_argument('--template', default=TEMPLATE, help='template .vesta scene')
    parser.add_argument('--out', default=OUT_DIR, help='output directory')
    args = parser.parse_args()
    TEMPLATE = os.path.abspath(args.template)
    OUT_DIR = os.path.abspath(args.out)
    os.makedirs(OUT_DIR, exist_ok=True)
    atoms, cell = slab_atoms()
    target = choose_x_site(atoms)
    x_index = atoms.index(target) + 1

    scene = build_scene(f'Fe47{X_SYMBOL} surface model', atoms, cell, x_index)
    scene_path = os.path.join(OUT_DIR, 'fe47x_surface.vesta')
    with open(scene_path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(scene)
    write_cif(os.path.join(OUT_DIR, 'fe47x_surface.cif'), atoms, cell, x_index, 'fe47x_surface')

    layers = sorted({atom[3] for atom in atoms})
    print(f'atoms={len(atoms)}, layers={layers}, cell={cell}')
    print(f'X at atom #{x_index}, layer={target[3]}, uvw=({target[0]:.3f},{target[1]:.3f},{target[2]:.3f})')


if __name__ == '__main__':
    main()
