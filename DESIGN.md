---
name: Trilolabs
description: Tripundra Clarity — Shiva blue · vibhuti ash · white on void, for every Trilolabs product and surface.
colors:
  void: "#060606"
  void-elevated: "#0e1116"
  void-soft: "#161b24"
  ash: "#c8c4ba"
  ash-bright: "#f2f0e8"
  ink: "#ffffff"
  ink-muted: "rgba(242, 240, 232, 0.72)"
  ink-faint: "rgba(200, 196, 186, 0.64)"
  line: "rgba(242, 240, 232, 0.12)"
  shiva-blue: "#0047ab"
  shiva-bright: "#3b7ddd"
  shiva-soft: "#132a52"
  cta: "#f2f0e8"
  cta-ink: "#060606"
typography:
  display:
    fontFamily: "Manrope, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(4.5rem, 14vw, 8.125rem)"
    fontWeight: 800
    lineHeight: 0.95
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Manrope, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2.25rem, 5vw, 2.875rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Manrope, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Manrope, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Manrope, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "0.01em"
rounded:
  md: "12px"
  panel: "1.5rem"
  pill: "999px"
spacing:
  gutter: "clamp(1.25rem, 4vw, 3rem)"
  page-max: "72rem"
  xs: "0.5rem"
  sm: "0.75rem"
  md: "1.25rem"
  lg: "2rem"
  xl: "4rem"
components:
  button-primary:
    backgroundColor: "{colors.cta}"
    textColor: "{colors.cta-ink}"
    rounded: "{rounded.pill}"
    padding: "0.75rem 1.15rem"
    height: "2.625rem"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "#e8e8e8"
    textColor: "{colors.cta-ink}"
  button-ghost:
    backgroundColor: "rgba(255, 255, 255, 0.08)"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0.75rem 1.15rem"
    height: "2.75rem"
  button-ghost-hover:
    backgroundColor: "rgba(255, 255, 255, 0.14)"
    textColor: "{colors.ink}"
  chip:
    backgroundColor: "transparent"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.pill}"
    padding: "0.35rem 0.75rem"
  badge:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0.35rem 0.7rem"
    typography: "{typography.label}"
  card-panel:
    backgroundColor: "{colors.void-elevated}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "{spacing.md}"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
---

# Design System: Trilolabs

## Overview

**Creative North Star: "Tripundra Clarity"**

Trilolabs products share one visual doctrine: the tripundra — three horizontal bands of white, vibhuti ash, and Shiva blue — on a near-black void. The mark is not decoration; it is the hierarchy of the system. White for clarity, ash for restraint, blue for decisive focus. Everything else recedes into void so the work (and the founder’s next action) stays obvious.

This language applies to the marketing site **and** to internal products, client builds we own, and subproducts (Outroom, Neurasix shells, future tools). Density and chrome may tighten for Operate surfaces, but palette, type family, mark geometry, pill CTAs, and flat tonal depth do not fork into a second brand.

Reject agency purple glow, cream-serif terracotta, newspaper grids, neon gradients, and glossy “AI startup” chrome. No fake social proof aesthetics. Speak visually the way we speak in copy: plain, result-led, no theater.

**Key Characteristics:**
- Void ground (`#060606`) with ash-white ink and a single blue accent
- One geometric sans (Manrope) for display and body
- Soft pill CTAs; rounded media panels; hairline borders instead of shadows
- Tripundra mark as the only sacred emblem
- Flat-by-default depth; motion is purposeful and short

## Colors

A three-band sacred palette on void — never a rainbow, never a second accent family.

### Primary
- **Shiva Blue** (`#0047ab`): Decisive focus — links in emphasis, brand mark bottom band, sparse interactive accents. Rarity is the point.
- **Shiva Bright** (`#3b7ddd`): Hover / active lift of the blue when the base needs more contrast on void.
- **Shiva Soft** (`#132a52`): Quiet blue-tinted wells (panel underlays, soft selection).

### Neutral
- **Void** (`#060606`): Default canvas for every Trilolabs product chrome.
- **Void Elevated** (`#0e1116`) / **Void Soft** (`#161b24`): One and two steps up for panels, sheets, and nested surfaces.
- **Ash Bright** (`#f2f0e8`): Primary CTA fill and high-signal white-ash.
- **Ash** (`#c8c4ba`): Secondary ash — mark middle band, softer labels.
- **Ink** (`#ffffff`): Primary text on void.
- **Ink Muted** / **Ink Faint**: Supporting and tertiary text (keep faint ≥ ~0.64 alpha for contrast).
- **Line** (`rgba(242, 240, 232, 0.12)`): Hairline borders and dividers.

### Named Rules
**The Tripundra Rule.** Only white · ash · Shiva blue as chromatic identity. Do not introduce purple, teal-neon, gold, or warm-cream systems alongside this brand.

**The Blue Rarity Rule.** Shiva blue occupies a small fraction of any screen. Large fields stay void or ash-bright CTAs; blue marks focus, not wallpaper.

## Typography

**Display Font:** Manrope (ui-sans-serif, system-ui)
**Body Font:** Manrope (same family — one voice)

**Character:** Geometric, confident, slightly condensed tracking on big type. No serif pairing. Weight does the hierarchy work.

### Hierarchy
- **Display** (800, `clamp(4.5rem, 14vw, 8.125rem)`, ~0.95 lh, tight tracking): Brand / hero wordmarks only. Overpowering headlines that eclipse the brand fail the brand test.
- **Headline** (700, `clamp(2.25rem, 5vw, 2.875rem)`): Section titles (`display-title`).
- **Title** (700, ~1.5rem): Card and panel titles.
- **Body** (400, 1rem, 1.55 lh): Support copy; prefer ~45–70ch.
- **Label** (500, ~0.8125rem): Buttons, badges, meta.

### Named Rules
**The One Family Rule.** Manrope (or an approved geometric successor applied globally) for all UI. Do not mix Inter/Roboto/system-default stacks as the face of the product.

## Layout

Fluid gutters `clamp(1.25rem, 4vw, 3rem)` inside a `72rem` max measure. Marketing pages breathe with large vertical rhythm (~4rem section gaps); Operate products keep the same gutter language but may compress vertical spacing.

Primary breakpoint for layout shifts: ~`56rem` (also `48rem` / `52rem` / `72rem` for grids). Mobile-first; full-bleed heroes on marketing; product shells use the same void canvas with denser tool chrome.

One job per section on persuasive surfaces. Product UIs: one primary task per view, secondary chrome quieter than the work surface.

## Elevation & Depth

Flat by default. Depth comes from **tonal steps** (void → elevated → soft), **hairline borders**, and light veils/gradients over media — not drop shadows or glow stacks.

### Shadow Vocabulary
None as a system primitive. Do not invent ambient card shadows for “polish.”

### Named Rules
**The Flat-By-Default Rule.** Surfaces rest flat. Motion and border/contrast shifts carry state; shadows are not part of the brand grammar.

## Shapes

- **Pills** (`999px`): Primary CTAs, badges, chips, nav CTA — soft, approachable, founder-friendly.
- **Panels** (`1.5rem` / ~24px): Media wells, case cards, about panels, accordion media.
- **Mark tile** (`7px` on 32px mark): Slightly softer than sharp square; keep the tripundra bars straight and horizontal.
- Circles for icon wells and arrow affordances inside ghost buttons.

Borders are 1px `line` or subtle white alpha — never thick chrome frames.

## Components

### Buttons
Soft, pill-shaped, high-contrast ash on void for primary actions.

- **Shape:** Full pill (`999px`)
- **Primary:** Ash-bright fill (`#f2f0e8`), void ink, ~2.625rem height, label weight 500
- **Hover:** Slightly cooler ash (`#e8e8e8`); short ease-out (~220ms)
- **Ghost:** Translucent white fill + hairline border; brightens on hover
- **Focus:** Visible focus ring required; do not remove outlines without an equal replacement

### Chips / Pills
Outline or soft translucent tags for taxonomy (service tags). Pill radius; muted ink; never a second accent color.

### Cards / Containers
- **Corner:** ~1.5rem panels
- **Background:** Void elevated or media cover with dark veil
- **Border:** `line` hairline
- **Shadow:** None
- Prefer full-bleed media + veil over boxed “card chrome” when the content is visual

### Inputs / Fields (product adaptation)
- Void-elevated field on void canvas; hairline border; pill or 12px radius depending on density
- Focus: Shiva bright border or soft blue ring — not purple glow
- Error: Keep accessible contrast; prefer ash-bright text + clear message over color-only

### Navigation
Fixed, transparent until scroll then frosted void blur. Brand mark centered or leading; primary links quiet; one pill CTA (“Book…” / primary product action). Mobile sheet is inert when closed.

### Signature: Tripundra Mark
Three horizontal bars (ash-bright, ash, Shiva blue) on a void rounded square. Always preserve band order and relative lengths (top widest → bottom shortest). Do not recolor bands arbitrarily; do not replace with generic AI glyphs.

## Do's and Don'ts

### Do:
- **Do** start from void (`#060606`) and the tripundra palette for any new Trilolabs product.
- **Do** keep Manrope (or the global successor) as the single type family.
- **Do** use ash-bright pill buttons for the primary action; keep blue rare.
- **Do** express depth with tonal steps and hairlines.
- **Do** show the legal entity where merchant/compliance surfaces require it.
- **Do** tighten density for Operate UIs without inventing a second palette.

### Don't:
- **Don't** introduce purple-indigo gradients, cream+terracotta, or broadsheet newspaper layouts.
- **Don't** use multi-layer shadows, neon glow, or glassmorphism stacks as identity.
- **Don't** put competing hero headlines above the brand on marketing surfaces.
- **Don't** fabricate metrics, testimonials, or team theater as visual filler.
- **Don't** fork a “product theme” that drops ash/blue/void for a trendy SaaS skin.
- **Don't** resize or recolor tripundra bands independently of the mark system.
