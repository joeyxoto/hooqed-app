# Hooq templates

Each folder here is one plug-in hooq design. The engine writes the content (hooq.json); the template only decides the look (see `engine/THEMING.md`).

A template folder holds:
- `template.html`: the page. Keep the design tokens, `data-slot` names and the rules in THEMING.md.
- `manifest.json`: name, label, slots and screens it supports, and the hooks the app needs (`window.leadBrief`, the contact form `#cf`, the `data-confirm` / `data-textme` buttons).

`v7` is the current design, copied unchanged from the proof repo (tag `flowA-blind-v7`). To add a new design, copy `v7/` to a new folder, restyle it, and set the hooq's `template` column to the folder name.
