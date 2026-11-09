# many-crafts · 千方百技

Bridges that let AI use professional software. Each plugin lets a DSH session drive a program that has no scripting API — by file-level control, command-line rendering and window management, instead of screenshot-and-click.

## Plugins

| Directory | Software | What it does |
| --- | --- | --- |
| [`vesta-bridge`](vesta-bridge/) | [VESTA](https://jp-minerals.org/vesta/en/) (crystal structure visualization) | Opens structure files, renders PNGs via `-export_img`, captures the window, manages the process; `.vesta` scenes support view/zoom/boundary/background overrides |

## Layout

```text
many-crafts/
  vesta-bridge/
    index.js            plugin entry (tools + system prompt section)
    lib/                vesta (process/render), scene (.vesta rewrite), pwsh (window enumeration)
    cordis.patch.yml    bundle patch (vestaPath must be set)
    locale/             display names
    docs/IMPLEMENTATION.md
    examples/           two reproduction cases + compose helper
    templates/          minimal .vesta template
    README.md
    LICENSE             MIT (dhd)
    AI-DISCLOSURE.md
    THIRD_PARTY_NOTICES.md
```

## Design notes

- **No screen scraping**: renders are files, checked with `read_image`.
- **No injection**: stage 1 only uses the program's own command line and window messages.
- **No bundled software**: VESTA, and any other commercial or registration-gated tool, must be installed by the user and used under its own license.

## License

MIT per plugin directory. Third-party software keeps its own license; see each plugin's `THIRD_PARTY_NOTICES.md`.
