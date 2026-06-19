# Weather Landscape — "Pixel-Zine" Site Redesign

**Date:** 2026-06-19
**Status:** Approved design, pending spec review → implementation plan
**Scope:** Full site — all four pages (landing, forecasts, guide, admin)

## Summary

Replace the current "modern SaaS" visual language (blue gradients, white rounded
cards, blurred drop-shadows, `system-ui`, emoji headings) with the **"calm tech /
pixel-zine"** system from the landed mockup at `code/landing.html`.

The core idea: the site *chrome* now speaks the same visual language as the
*product*. The weather images are 296×128 pixel landscapes; the site that frames
them becomes pixel-native too — cream paper, ink borders, hand-drawn pixel-art
SVG glyphs, and pixel typography.

This is a CSS + template-markup job. The `web.py` routing layer is **not** changed.

## Design language

Sourced verbatim from the mockup's `:root` tokens:

| Token | Value | Role |
|-------|-------|------|
| `--paper` | `#f3e8c8` | cream background (with faint scanline texture on `html`) |
| `--ink` | `#1e1a14` | near-black text, borders |
| `--ink-dim` | `#6d5d44` | secondary text |
| `--ink-faint` | `#b39c75` | tertiary / labels |
| `--rule` | `#d4bd8f` | section dividers |
| `--accent` | `#c44d3a` | terracotta — primary accent, CTAs |
| `--accent-2` | `#2d6e3d` | green — grass, "active"/on states |
| (sky) | `#88c5e8` | glyph windows |
| (sun) | `#f5b342` | sun/noon |
| `--tile` | `#e0c98f` | framed-art / table-header fill |

**Type:** `Press Start 2P` (display, tags, buttons, section titles) + `VT323`
(body, mono, data), via Google Fonts `<link>` in each page `<head>`. Body base
~21px so VT323 stays comfortable.

**Primitives (brutalist):** 3–4px solid `--ink` borders, hard offset box-shadows
(no blur), zero border-radius, "press into shadow" hover (`translate` + reduced
shadow). Extracted as reusable classes: `.box`, `.btn` (`.primary`/`.ghost`),
`.tag`, `.section`, `.section-tag`, `.section-title`, `.section-lede`, nav, footer.

**Decision — pixel everywhere, literally.** Pixel fonts apply on *every* page,
including admin. This is acceptable because **content-heavy blocks are rewritten
to be sparse** — nothing stays dense enough for VT323 to hurt.

## Architecture (integration approach "B")

- **`workers/web/src/assets/styles.css`** is **replaced wholesale**. The current
  blue-card CSS is removed; the new file holds all tokens, primitives, and
  page-specific sections. Single source of truth — honors the existing shared-CSS
  pattern (`<link rel="stylesheet" href="/assets/styles.css">`).
- **Pixel-SVG glyphs** (house, hill, tree, cloud, sun, flower) are extracted from
  the landing markup so the heavy `<rect>` data is defined **once per page**, not
  pasted per use. **Default: an inline SVG-symbol sprite** (`<svg><symbol
  id="glyph-house">…</symbol>…</svg>` once, referenced everywhere via
  `<use href="#glyph-house">`). `<use>` markup contains no `$`, so it is safe on
  the `string.Template` pages. Fallback if a sprite proves awkward across pages: the
  server-side `glyphs.html` partial (option "C" injection). The glyph fill classes
  (`.roof/.wall/.window/.grass/.ink/.smoke/.chimney/.door`) live in the shared CSS
  so glyphs recolor from tokens.
- **Per-page templates** in `assets/templates/` keep only their own markup +
  the shared `<head>` (fonts + stylesheet link).
- Shared **nav** (sticky, ink-bordered, "Get yours →" CTA) and **footer** are
  duplicated per page for now. *Fallback option "C"* — a tiny sentinel-based
  partial system (`<!--PARTIAL:nav-->` replaced server-side **before**
  `string.Template` substitution) — is held in reserve if the duplication
  becomes painful. Not built up front (no gold-plating).

### `string.Template` landmine

`forecasts.html` and `admin.html` are rendered through Python `string.Template`
(`$zip_links`, `$zip_count`, `$zip_table_rows`). **Any literal `$` in their markup,
CSS, or JS must be doubled to `$$`** or rendering throws (this is the bug from #27).
`landing.html` and `guide.html` are loaded static (`load_template`) and are not
subject to this. The redesign must preserve every existing substitution variable
and JS hook/ID on the templated pages.

## Page-by-page treatment

### 🏠 Landing (`landing.html`)
The mockup, wired to live data. Sections: hero (framed `/example` art + live
caption), "dashboard numbers vs. landscape" before/after, 6-cell decoder ring,
three format cards, fat footer. The hardcoded "Austin · 78729" caption becomes a
real default ZIP or neutral copy.
**The design-system showcase section is removed from the public landing** — it is
a portfolio flourish, not visitor-facing value. The design system is still owned
and documented, but as an internal styleguide (below), never on the public site.

### 🎨 Internal styleguide (new, non-public)
We own and dogfood the design system, but it never appears on the public website.
The showcase markup (type ramp, swatches, component gallery) becomes its own page
rendered from the **real shared `styles.css`**, so it is a *living* reference that
cannot drift from production. It is **kept out of the public nav and gated like
admin** (internal-only). This replaces the landing's showcase section.

### 📍 Forecasts (`forecasts.html`)
Live ZIP list restyled as brutalist `.box` cards: pixel `--font-display` ZIP code,
`.tag` status pill (active/inactive, green for active), format links styled like
the landing's `.format-link` (`→` arrows). Preserves `$zip_links` / `$zip_count`.
Empty state = glyph + one line.

### 📖 Guide (`guide.html`) — the deep dive
**Reframed, not just restyled.** The landing's decoder is the *hook* (6 glyphs,
one line each, ~80% of a reading). The guide is the *complete reference* — it goes
**past** the landing. Same glyph components and calm layout, but each entry carries
the full encoding the landing withholds:

- **Trees** — every species (pine / palm / round / thin) and the wind *direction*
  each encodes; height = wind strength.
- **House** — chimney smoke = atmospheric pressure.
- **Flowers** — blue = midnight, yellow = noon, as time anchors along the timeline.
- **Terrain** — vertical position = temperature; the lower line = the temp curve
  drawn across 24h.
- **Sun & moon** — rise/set positions → hours of daylight at a glance.
- **Clouds** — coverage, positioned over the part of the day they occur.

No symbol table, no walls of text — sparse, glyph-forward rows. The two pages now
justify each other (hook vs. reference) instead of competing.

### ⚙️ Admin (`admin.html`)
Every function preserved (ZIP table, format toggles, generate buttons, add-ZIP
form, toasts) but reskinned: brutalist table with ink rules and `--tile` header,
toggle switch recolored to `--accent-2`, buttons as `.btn` press-blocks. Trimmed so
nothing is visually dense. **All existing JS hooks/IDs and `$zip_table_rows`
preserved; `$` literals in JS doubled** so behavior and tests don't move.

## Format previews (landing + forecasts)

**Use the real renders, not CSS fakery.** The mockup faked B&W and Dark format
cards with CSS filters (`grayscale/contrast`, `invert/hue-rotate`) over the single
color `/example` image. Those filters *lie* in the ways that matter — real e-ink
B&W dithering ≠ `grayscale()`, and a real dark render ≠ a hue-rotated color image.
The app genuinely generates each format (`GET /{zip}?{format}`), so the three cards
point at **real per-format example renders** (e.g. `/example`, `/example?format=bw`,
`/example?format=dark`, each produced the same way today's `/example` is). No CSS
filters. Forecasts page links to the real format endpoints as today.

**Now vs. future on the example *location*:** the example stays a **single static
location today** (whatever `/example` serves now), rendered honestly in all three
formats. Making `/example` a *near-the-user* approximation (edge-geo → nearest
pre-generated DMA) is a deliberate **follow-up**, not part of this redesign — see
Future Work.

## Out of scope (this redesign) — captured as Future Work

- No change to `web.py` routing, the queue/worker pipeline, or image generation,
  **except** staging the real per-format example renders the format cards point at.
- Geo-aware `/example` (edge-geo → nearest DMA) and adding DMAs to the pipeline.
- The Cloudflare/OpenWeather usage + spend audit that gates the DMA expansion.
- Client-side observability (Cloudflare Web Analytics / RUM beacon).
- No partials system unless the nav/footer duplication proves painful (option C).

These follow-ups are captured in
[`2026-06-19-redesign-followups.md`](./2026-06-19-redesign-followups.md).

## Future Work

See the companion follow-ups doc for fully-specced next steps:
1. **Geo-aware example** — pre-generate major DMAs, pick the nearest via Cloudflare
   edge geo; less-doxxable than the user's literal location.
2. **Usage & spend research** — confirm DMA expansion stays within the current
   Cloudflare + OpenWeatherMap pricing tier *before* widening the pipeline.
3. **Frontend observability** — add the Cloudflare Web Analytics / RUM beacon.

## Testing

Per repo `CLAUDE.md` testing policy (tests pass before *and* after; no gamed tests):

1. Run the existing web-worker tests first; confirm green before touching anything.
2. The redesign is markup/CSS, so the highest-value guards are the render paths:
   - `render_template('forecasts.html', …)` and `render_template('admin.html', …)`
     must still substitute without `string.Template` errors (the `$$` discipline) —
     add/extend a test that renders each with representative context and asserts no
     exception + presence of substituted values.
   - `load_template('landing.html')` and `load_template('guide.html')` load and
     contain expected anchors/sections.
   - Static asset route still serves `styles.css`.
3. Preserve all admin JS hook IDs; if tests assert on specific element IDs/classes,
   keep them or update tests deliberately (never weaken assertions to pass).
4. Run the full web-worker suite again; then the project-level test
   (`python run_test.py`) to confirm nothing in the shared path regressed.
5. Run the repo's 4-agent QA review (Code Quality, Security, Test Quality,
   Maintainability) before marking the phase done, per `CLAUDE.md`.

## Rollout

Single branch `claude/weather-landscape-pixel-redesign` off `main`; PR for human
squash-merge (no direct-to-main). Deployable via the standard `web` worker deploy;
no migrations, no new bindings.
