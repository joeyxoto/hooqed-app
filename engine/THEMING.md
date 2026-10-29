# Re-skinning a hooq (THEMING)

A hooq is an interactive quote that turns website visitors into booked calls. The engine decides **content** (hooq.json); the template decides **look**. Re-skin without touching the engine.

## 1. Design tokens — `:root` in `pipeline/template.html`
All colour, type, radius and spacing live in CSS variables. Change these only.

| Group | Variables |
|---|---|
| Brand colours (filled per business by `brand.py`, WCAG ≥ 4.5:1 checked) | `--brand --on-brand --brand-deep --on-deep --button --on-button --accent-text --header-bg --on-header` |
| Neutrals | `--ink --muted --paper --surface --line --ribbon --on-ribbon` |
| Type | `--font-display --font-body --display-case --display-weight --fs-hero --fs-h2 --fs-body` |
| Shape | `--radius-card --radius-button --radius-option --radius-chip --shadow-card` |
| Space | `--space-page --space-block --gap --header-h` |

Brand colours come from the business's real logo/site; `brand.py` darkens or lightens them automatically until text passes 4.5:1 (see `contrast_fixes` in brand.json). If you override a pair, keep it ≥ 4.5:1.

## 2. Named blocks — `data-slot`
Every block renders into an element with a `data-slot` name, so a designer can restyle or reorder by slot:

header, logo, progress (“Step 2 of 5”), intro, intro.photo, hook.eyebrow, hook.headline, hook.sub, hook.cta, steps, duration (“Takes about 30 seconds”), chips, review, question, contact, result, result.photo, result.title, price, summary, drivers (“What moves the price” / “What shapes the job”), next-step, timeline, includes, trust, booking, text-me, about, done, owner-brief, footer.

## 3. Content — `hooq.json`
All words and figures come from hooq.json (`hook`/`hook_q`, `jobs[]` with questions, price, timeline, result; `booking`; `chips`; `review`; `rating`). Never hard-code copy in the template.

## 4. Rules a skin must keep
- Visitors only ever see owner-confirmed or site-published figures; keep the “Example owner confirmation (simulated)” ribbon slot in demos.
- No urgency wording, no phone numbers, never “landing page” / “lead page”.
- Logo is the business's real mark at its true aspect ratio, or the text wordmark (`.wm`). No favicons.
- Mobile first: check at 390px wide, no horizontal scroll.
