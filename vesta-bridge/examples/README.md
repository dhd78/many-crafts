# Examples

Two reproductions of published figures, used as end-to-end demos of the bridge.

| Directory | Structure | Renders |
| --- | --- | --- |
| `fe-figure/` | FCC-Fe (111) 2×1×4 slab, 12 ABC layers + 15 Å vacuum (48 atoms) | `out-cell.png`, `out-slab-side*.png`, `out-slab-top*.png` |
| `liang-figure/` | Fe47Mo1 (1-11)[1-12] surface, 12 layers, one Mo substitution | `out-d*.png` |

Both are built from lattice constants in the scripts, not from redistributed
data. The figures they refer to belong to the cited theses; the originals are
**not** included.

## Run

```powershell
pip install numpy pillow

python fe-figure\generate.py --out fe-figure
python liang-figure\generate.py --out liang-figure
```

`--template` defaults to `../templates/template.vesta`; pass another `.vesta`
scene if you want different element styles.

Then render from a DSH session:

```text
vesta_export_image input=<repo>\examples\fe-figure\fe_slab.vesta view=[1,0,0] zoom=0.8 boundary=[0,1,0,1,0,1] scale=2
```

## Compare

```powershell
python compose.py --left your-reference.png --right fe-figure\out-slab-side4.png --out comparison.png
```
