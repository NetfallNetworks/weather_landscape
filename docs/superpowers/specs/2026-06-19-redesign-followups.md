# Redesign Follow-ups (captured 2026-06-19)

Future tasks split out of the
[pixel-zine redesign](./2026-06-19-weather-landscape-redesign-design.md) so the
redesign itself stays shippable. Each is a standalone unit of work; sequence
matters where noted. (GitHub Issues are disabled on this fork, so these live in
the repo until/unless Issues are enabled.)

---

## 1. Geo-aware `/example` — "a landscape near you"

**Problem.** Today `/example` serves one static landscape for everyone. We'd like
the homepage hero (and the format-preview cards that read from it) to show a
landscape that's *relevant to the visitor* — without (a) proactively generating
every ZIP on the globe, or (b) doxxing the visitor's exact location.

**Approach.**
- Pre-generate a curated set of **major US DMAs** (Designated Market Areas) through
  the normal pipeline, so a spread of representative landscapes is always warm in
  R2/KV.
- At request time, use **Cloudflare edge geo detection** (`request.cf` —
  `country` / `region` / lat-long, available in Workers) to pick the **nearest
  pre-generated DMA** and serve that landscape.
- Fall back to the current static example when geo is unavailable or out of the
  covered set.

**Why it's nice.** Relevant-feeling without being creepy — a *near-you
approximation*, not your address. Still openly an open-source fork of the real
`weather_landscape`, so the "show-off" framing is intact; this just makes the demo
land better.

**Generate all formats per DMA.** Each seeded DMA should render the full set of
configured formats (rgb_light / rgb_dark / bw), not just the default. This makes
the geo-picked `/example?{format}` previews real per-format renders at every
warm location — and obviates a separate per-format *static* fallback: once the
DMA swath exists, the landing's format cards are format-true even on a cold visit
(no dark-card-shows-color edge case). Folds in the deferred per-format-fallback
concern from the redesign.

**Depends on:** Task 2 (confirm the added DMA generation fits the pricing tier
before widening the pipeline). Note the format multiplier: N DMAs x 3 formats.

**Touches:** `workers/web/src/web.py` (`/example` route + geo read), the
scheduler/dispatcher pipeline (DMA seed list), template hero caption (generic, not
a literal location).

---

## 2. Usage & spend audit before DMA expansion (research)

**Problem.** Adding a set of always-on DMAs increases scheduled generations,
OpenWeatherMap calls, R2 writes/reads, and Worker invocations. We need to confirm
this stays inside the pricing tier we already pay for **before** turning it on.

**Deliverable.** A short written audit:
- Current cadence and volume: how many ZIPs × formats × the 15-min cron =
  generations/day today; resulting OpenWeatherMap call volume; R2 + Workers usage.
- Headroom against current plan limits (Cloudflare Workers/R2/Queues plan +
  OpenWeatherMap tier).
- Marginal cost of N additional DMAs, and the max N that stays within tier.
- Recommendation: the DMA count to seed in Task 1.

**Note.** This is a research/investigation task — pairs well with a deep-research
pass plus reading the actual wrangler configs and any usage dashboards. Run it
*before* Task 1's pipeline change.

---

## 3. Frontend observability — Cloudflare Web Analytics / RUM beacon

**Goal.** Bonus client-side observability for the public site with minimal effort
and privacy-first defaults.

**Approach.** Add Cloudflare's frontend analytics beacon (their privacy-first
**Web Analytics** / Real User Monitoring JS snippet) to the served pages — a small
`<script>` with the site token in the shared page `<head>`/footer. Confirm the
current product name/snippet at implementation time (Cloudflare has iterated on
Web Analytics vs. newer RUM offerings), and keep it off the internal styleguide/
admin pages if we only want public-traffic signal.

**Touches:** the shared page chrome (head or footer) across templates; Cloudflare
dashboard (enable Web Analytics, get site token).
