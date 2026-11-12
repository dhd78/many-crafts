# many-crafts · 千方百技

Bridges that let AI use professional software. Each one lets an agent drive a program that has no scripting API — by file-level control, command-line rendering and window management, instead of screenshot-and-click.

Two forms are provided per program:

- **plugin** — runs inside a DSH (DeepSeek Harness) session;
- **skill** — a `SKILL.md` package with a CLI, for Claude Code, Cursor, Copilot and other agents that read the open skill format.

## Plugins

| Directory | Software | What it does |
| --- | --- | --- |
| [`vesta-bridge`](vesta-bridge/) | [VESTA](https://jp-minerals.org/vesta/en/) (crystal structure visualization) | Opens structure files, renders PNGs via `-export_img`, captures the window, manages the process; `.vesta` scenes support view/zoom/boundary/background overrides. `skill/` holds the `SKILL.md` wrapper |

## Skills

| Directory | For | What it does |
| --- | --- | --- |
| [`vesta-render`](https://github.com/dhd78/skills/tree/main/vesta-render) | Claude Code, Cursor, Copilot and other `SKILL.md` agents | Same VESTA workflow as a standalone CLI + `SKILL.md`; canonical copy in the [skills repo](https://github.com/dhd78/skills/tree/main/vesta-render), mirror at [`vesta-bridge/skill/`](vesta-bridge/skill/). Verified with VESTA 3.90.6a on Windows 11. Also on [Agensi](https://www.agensi.io/skills/vesta-render) (free) |

## Layout

```text
many-crafts/
  vesta-bridge/        DSH plugin
    index.js           plugin entry (tools + system prompt section)
    lib/               vesta (process/render), scene (.vesta rewrite), pwsh (window enumeration)
    cordis.patch.yml   bundle patch (vestaPath must be set)
    locale/            display names
    docs/IMPLEMENTATION.md
    examples/          two reproduction cases + compose helper
    templates/         minimal .vesta template
    README.md
    LICENSE            MIT (dhd)
    AI-DISCLOSURE.md
    THIRD_PARTY_NOTICES.md

  vesta-bridge/skill/  SKILL.md wrapper (mirror of the skills repo)
    SKILL.md           frontmatter + instructions for the agent
    scripts/vesta.mjs  CLI (status / open / export / render / close)
    scripts/doctor.mjs preflight check
    lib/               shared with the plugin
    references/        implementation notes
    templates/         .vesta template
    examples/          CIF inputs and rendered PNGs
    README.md
    LICENSE            MIT (dhd)
    AI-DISCLOSURE.md
    THIRD_PARTY_NOTICES.md
    SOURCE.md          upstream mapping and verification record
    CANONICAL.md       points to the canonical copy

  vesta-render/        pointer only (old path; see README.md)
```

## Design notes

- **No screen scraping**: renders are files, checked with `read_image`.
- **No injection**: stage 1 only uses the program's own command line and window messages.
- **No bundled software**: VESTA, and any other commercial or registration-gated tool, must be installed by the user and used under its own license.

## License

MIT per directory. Third-party software keeps its own license; see each `THIRD_PARTY_NOTICES.md`.
