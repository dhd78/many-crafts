# Implementation notes

## 1. Why this design

VESTA is a desktop GUI with no scripting API. Driving it by screenshot, OCR and
synthetic clicks is expensive and fragile. Two facts make a cheaper route work:

1. **VESTA ships a command line**: `VESTA.exe -open <input> -export_img scale=N <output>`
   writes a PNG without any UI interaction.
2. **`.vesta` scene files are plain text**, so view angle, display range, background
   and zoom can be generated programmatically.

The plugin therefore does file-level control + command-line rendering + window
management. It never reads pixels to decide anything and never injects code.

Note: DSH's shell tool runs in a low-integrity sandbox, where GUI programs exit
immediately; plugins run in the host process, where `child_process.spawn` works.
That is why the same command fails in a shell tool and succeeds from the plugin.

## 2. Tools

| Tool | Implementation |
| --- | --- |
| `vesta_status` | resolves `vestaPath` (config > `VESTA_EXE`), reads `VESTA.ini` header for version, enumerates windows |
| `vesta_open` | `spawn VESTA.exe -open <file>`, then detect the window/title (single-instance forwarding) |
| `vesta_export_image` | `spawn VESTA.exe -open <in> -export_img scale=N <out>`, poll the output file until its size is stable twice, then clean up |
| `vesta_screenshot` | screenshots the window via `BitBlt`, falling back to `PrintWindow(PW_RENDERFULLCONTENT)` |
| `vesta_close` | `WM_CLOSE`, then a forced kill if it does not exit |

Window enumeration is done in PowerShell (`EnumWindows` + `GetWindowThreadProcessId`),
returning JSON.

## 3. Rendering

- `-export_img scale=N` — `N` is a viewport multiplier, not a pixel size.
- Because VESTA is single-instance, a second launch forwards the file into the
  running window and exits; tool success must be judged by the window/title, not
  by the launcher's exit code.
- After rendering, the helper process is killed with `taskkill /T /F`.

## 4. Scene files

`.vesta` is plain text. Relevant sections:

- `SCENE` — the first three lines are a 3×3 camera basis (right, up, view direction)
  in Cartesian crystal coordinates. Identity means "look along c" (a → right, b → up).
- `BOUND` — fractional display range, e.g. `0 1 0 1 0 1` for one cell.
- `BKGRC` — background RGB.
- The trailing `0.458` in `SCENE` is the model zoom.

`lib/scene.js` converts a direction `[h,k,l]` plus cell parameters into an
orthonormal basis and rewrites those lines. All overrides are written to a
temporary copy; the original scene is never modified.

**Pitfall**: VESTA does not accept a BOM at the start of the scene file. Write
UTF-8 without BOM, or the render comes out blank.

## 5. Windows and screenshots

- Must call `SetProcessDPIAware()` before `BitBlt`, otherwise captures are
  offset at display scaling above 100%.
- `PrintWindow(PW_RENDERFULLCONTENT)` is the fallback for OpenGL windows.
- The window is brought to front before capture; a window fully covered or
  moved off-screen may still come out incomplete.

## 6. Facts that cost time

| Symptom | Cause |
| --- | --- |
| `vesta_open` "fails" instantly | VESTA is single-instance; the launcher exits after forwarding |
| Blank rendered PNG | scene file saved with a UTF-8 BOM |
| Screenshot region offset | missing `SetProcessDPIAware()` |
| Tool schema rejected | output schema is strict; extra fields are refused, provide defaults in `render` |
| New code not loaded after edit | toggle the plugin row off/on in Plugin Manager |

## 7. Examples

`examples/fe-figure` and `examples/liang-figure` build cells from lattice
constants, write `.vesta` scenes from `templates/template.vesta`, and render
them with `view` / `zoom` / `boundary`. `examples/compose.py` puts a reference
image next to a render; the referenced thesis figures are copyrighted and are
not included.

## 8. Later stages

- Stage 2: thin injected DLL (named-pipe command channel, framebuffer access,
  save/export event mirroring).
- Stage 3 (optional): in-memory state reading.
