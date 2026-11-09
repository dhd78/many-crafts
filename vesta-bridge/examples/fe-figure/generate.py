"""生成论文图 3-3 所需的 FCC-Fe 模型（VESTA 场景 + CIF）。

模型依据（孙浩硕士论文 3.2.3 节，PDF 第 29 页）：
- 以 fcc Fe 的 (111) 密排面为基面；
- 沿 [1-10] 与 [11-2] 方向切面，得到 2×1 的截面；
- 沿 [111] 取 4 个周期 = 12 层 ABCABC 堆垛；
- 在 c 轴上方留 15 Å 真空层。

坐标约定（与图 3-3(b) 的观感一致：横向是 [1-10]，深度方向是 [11-2]）：
    a 轴 = [1-10] * a/2      （1 个周期，视线方向）
    b 轴 = [11-2] * a        （2 个周期，水平方向）
    c 轴 = [111] * 4a        （4 个 a[111] 周期，24.94 Å）
晶格常数取 a = 3.60 Å（论文正文未给出，属合理近似）。
"""

import argparse
import os
import re

import numpy as np

A = 3.60
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, '..', '..', 'templates', 'template.vesta')
OUT_DIR = HERE

# 图 3-3(b)(c) 用 A/B/C 三种层颜色（近似原图的青/橙/蓝）
LAYER_COLORS = [
    (0, 200, 200),    # A
    (255, 140, 0),    # B
    (60, 90, 220),    # C
]
FE_RADIUS = 1.90
# 底层贴住 c 轴边界：VESTA 会自动在顶部画出周期镜像，与原图 (b) 一致
Z_OFFSET = 0.0


def fcc_atoms_in_slab():
    """枚举落在超胞内的 fcc 原子，返回 (u, v, w, layer_index)。"""
    av = A / 2.0 * np.array([1.0, -1.0, 0.0])
    bv = A * np.array([1.0, 1.0, -2.0])
    cv = A * 4.0 * np.array([1.0, 1.0, 1.0])
    matrix = np.column_stack([av, bv, cv])
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
                        atoms.append((u, v, w))
    # 12 层：沿 c 每 1/12 一层，A/B/C 循环
    layer = lambda w: int(round(w * 12)) % 3
    atoms = [(u, v, w, layer(w)) for (u, v, w) in atoms]
    atoms.sort(key=lambda t: (round(t[2], 4), round(t[0], 4), round(t[1], 4)))
    return atoms, av, bv, cv


def scene_atoms_for_fcc_cell():
    basis = [(0, 0, 0), (0, 0.5, 0.5), (0.5, 0, 0.5), (0.5, 0.5, 0)]
    return [(x, y, z, 0) for (x, y, z) in basis], [A, A, A, 90.0, 90.0, 90.0]


def scene_atoms_for_slab(vacuum=15.0):
    atoms, av, bv, cv = fcc_atoms_in_slab()
    thickness = float(np.linalg.norm(cv))
    c_total = Z_OFFSET + thickness + vacuum
    cell = [float(np.linalg.norm(av)), float(np.linalg.norm(bv)), c_total, 90.0, 90.0, 90.0]
    out = []
    for (u, v, w, layer) in atoms:
        z = (Z_OFFSET + w * thickness) / c_total
        out.append((u, v, z, layer))
    return out, cell


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


def build_scene(title, atoms, cell, radius=FE_RADIUS):
    with open(TEMPLATE, 'r', encoding='utf-8') as handle:
        text = handle.read()
    newline = '\r\n' if '\r\n' in text else '\n'
    lines = re.split(r'\r?\n', text)

    struct = []
    theri = []
    sited = []
    for index, (x, y, z, layer) in enumerate(atoms, start=1):
        label = f'Fe{index}'
        r, g, b = LAYER_COLORS[layer % 3]
        struct.append(f'  {index} {"Fe":<9}{label:<6}  1.0000   {x:.6f}   {y:.6f}   {z:.6f}    1a       1')
        struct.append('                             0.000000   0.000000   0.000000  0.00')
        theri.append(f'  {index}        {label} -0.000000')
        sited.append(f'  {index}        {label}  {radius:.4f} {r:3d} {g:3d} {b:3d} {r:3d} {g:3d} {b:3d} 204  0')
    struct.append('  0 0 0 0 0 0 0')
    theri.append('  0 0 0')
    sited.append('  0 0 0 0 0 0')
    atomt = [
        f'  1         Fe  {radius:.4f}   0 200 200   0 200 200 204',
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


def write_cif(path, atoms, cell, title):
    a, b, c, alpha, beta, gamma = cell
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(f'data_{title}\n')
        handle.write("_chemical_formula_sum 'Fe'\n")
        handle.write(f'_cell_length_a {a:.6f}\n_cell_length_b {b:.6f}\n_cell_length_c {c:.6f}\n')
        handle.write(f'_cell_angle_alpha {alpha}\n_cell_angle_beta {beta}\n_cell_angle_gamma {gamma}\n')
        handle.write("_symmetry_space_group_name_H-M 'P 1'\n_symmetry_Int_Tables_number 1\n")
        handle.write("loop_\n_symmetry_equiv_pos_as_xyz\n'x, y, z'\n")
        handle.write('loop_\n_atom_site_label\n_atom_site_type_symbol\n')
        handle.write('_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n')
        for index, (x, y, z, _layer) in enumerate(atoms, start=1):
            handle.write(f'Fe{index} Fe {x:.6f} {y:.6f} {z:.6f} 1\n')


def main():
    global TEMPLATE, OUT_DIR
    parser = argparse.ArgumentParser(description='Build VESTA scenes for the FCC-Fe (111) slab figure')
    parser.add_argument('--template', default=TEMPLATE, help='template .vesta scene')
    parser.add_argument('--out', default=OUT_DIR, help='output directory')
    args = parser.parse_args()
    TEMPLATE = os.path.abspath(args.template)
    OUT_DIR = os.path.abspath(args.out)
    os.makedirs(OUT_DIR, exist_ok=True)

    cell_atoms, cell = scene_atoms_for_fcc_cell()
    slab_atoms, slab_cell = scene_atoms_for_slab()

    jobs = [
        ('fe_fcc_cell', 'Fe FCC', cell_atoms, cell, 1.9),
        ('fe_slab', 'Fe slab 12 layers', slab_atoms, slab_cell, 1.9),
        ('fe_slab_top', 'Fe slab top view', slab_atoms, slab_cell, 1.0),
    ]
    for name, title, atoms, cell_params, radius in jobs:
        scene = build_scene(title, atoms, cell_params, radius)
        scene_path = os.path.join(OUT_DIR, f'{name}.vesta')
        with open(scene_path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(scene)
        cif_path = os.path.join(OUT_DIR, f'{name}.cif')
        write_cif(cif_path, atoms, cell_params, name)
        print(f'{name}: {len(atoms)} atoms, cell={cell_params}, radius={radius}')


if __name__ == '__main__':
    main()
