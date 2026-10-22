---
name: Marché auto
description: Daily-scraped car market dashboards for Tunisia and Europe, in one calm analytics app.
colors:
  canvas: "#ffffff"
  canvas-subtle: "#f8fafc"
  canvas-hover: "#f1f5f9"
  ink: "#0f172a"
  ink-2: "#334155"
  muted: "#64748b"
  muted-2: "#94a3b8"
  hairline: "#e2e8f0"
  hairline-2: "#f1f5f9"
  indigo: "#4f46e5"
  indigo-deep: "#4338ca"
  indigo-wash: "#eef2ff"
  indigo-soft: "#a5b4fc"
  indigo-pale: "#c7d2fe"
  sky-series: "#0ea5e9"
  slate-series: "#1e293b"
  rise-red: "#dc2626"
  rise-wash: "#fef2f2"
  drop-green: "#047857"
  drop-wash: "#ecfdf5"
  stale-amber: "#b45309"
  stale-wash: "#fffbeb"
  stale-line: "#fde68a"
typography:
  headline:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.015em"
    fontFeature: "'cv11', 'ss01', 'tnum'"
  metric:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.45
    letterSpacing: "-0.02em"
    fontFeature: "'cv11', 'ss01', 'tnum'"
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.45
    letterSpacing: "-0.005em"
    fontFeature: "'cv11', 'ss01', 'tnum'"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
    fontFeature: "'cv11', 'ss01', 'tnum'"
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.45
    letterSpacing: "normal"
    fontFeature: "'cv11', 'ss01', 'tnum'"
  axis:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "normal"
rounded:
  inner: "5px"
  sm: "7px"
  tooltip: "8px"
  md: "10px"
  pill: "999px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "14px"
  lg: "16px"
  page-x: "32px"
  sidebar: "232px"
components:
  button-default:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "0 12px"
    height: "32px"
  button-default-hover:
    backgroundColor: "{colors.canvas-subtle}"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.sm}"
    padding: "0 12px"
    height: "32px"
  button-primary-hover:
    backgroundColor: "{colors.slate-series}"
  input-search:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0 10px 0 30px"
    height: "32px"
    width: "240px"
  nav-item:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "7px 8px"
  nav-item-active:
    backgroundColor: "{colors.indigo-wash}"
    textColor: "{colors.indigo}"
  card:
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.md}"
    padding: "14px 16px"
  kpi-tile:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.metric}"
    rounded: "{rounded.md}"
    padding: "14px 16px"
  segmented-track:
    backgroundColor: "{colors.hairline-2}"
    textColor: "{colors.muted}"
    rounded: "{rounded.sm}"
    padding: "2px"
    height: "32px"
  segmented-active:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.inner}"
  tag:
    backgroundColor: "{colors.hairline-2}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "2px 7px"
  tag-rise:
    backgroundColor: "{colors.rise-wash}"
    textColor: "{colors.rise-red}"
  tag-drop:
    backgroundColor: "{colors.drop-wash}"
    textColor: "{colors.drop-green}"
  notice-stale:
    backgroundColor: "{colors.stale-wash}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
---

# Design System: Marché auto

## Overview

**Creative North Star: "The Ledger in Daylight"**

A light, dense analytics app in the category's own register: white ground, slate ink, hairline borders, one indigo accent. Every surface is a working instrument (KPI tile, chart card, bar list, sortable table), and every number carries its source and date. No themed metaphor, no decorative imagery; the only pictures are listing thumbnails inside table rows.

Density is high and even: 13px body, 32px controls, 14px gaps between cards. Hierarchy comes from weight and size inside one family, not from color. Color is a data channel with fixed meanings, so it is spent sparingly and never for decoration.

The interface is bilingual FR/EN through a toggle in the sidebar foot, with French number formatting (thin-space thousands, `%` after a space). Motion is minimal: a 260ms rise on page sections, 120ms hover fades, a 1.2s skeleton shimmer, all off under reduced motion.

**Key Characteristics:**
- White canvas, slate-tinted neutrals, 1px hairlines carry all structure.
- One indigo accent for data marks and selected state only.
- Green/red reserved for price direction; amber reserved for stale data.
- Inter with tabular figures everywhere; numbers align in columns.
- Persistent 232px sidebar on desktop, sticky blurred top bar with underline tabs on mobile.

## Colors

A cool slate neutral ramp with a single indigo voice and three strictly semantic signal hues.

### Primary
- **Ledger Indigo** (indigo): line and area series, column highlights, bar fills, sparklines, range-bar median tick, active nav item, focus ring, links. Means "data" or "selected".
- **Indigo Deep** (indigo-deep): hover of indigo-filled elements.
- **Indigo Wash** (indigo-wash): background of the active sidebar item.
- **Indigo Soft** (indigo-soft): secondary bar lists and the interquartile band of the range bar.
- **Indigo Pale** (indigo-pale): non-highlighted histogram columns.

### Secondary
- **Sky Series** (sky-series) and **Slate Series** (slate-series): the second and third Europe country series alongside indigo; muted-2 is the fourth. Slate Series also serves as the ink-button hover.

### Tertiary (signal)
- **Rise Red** (rise-red) on **Rise Wash** (rise-wash): price went up. Deltas, tags, diverging-bar positives.
- **Drop Green** (drop-green) on **Drop Wash** (drop-wash): price went down. Deltas, tags, diverging-bar negatives. Also fills the "fresh" source dot.
- **Stale Amber** (stale-amber) on **Stale Wash** (stale-wash) with **Stale Line** (stale-line): frozen-source notice and stale source dot.

### Neutral
- **Canvas** (canvas): page and card ground.
- **Canvas Subtle** (canvas-subtle): sidebar ground, row hover, default-button hover.
- **Canvas Hover** (canvas-hover): nav-item hover.
- **Ink** (ink): primary text, primary button fill, active language toggle.
- **Ink 2** (ink-2): secondary text, nav labels, bar labels.
- **Muted** (muted): captions, axis text, column headers, KPI labels.
- **Muted 2** (muted-2): placeholders, disabled legend items.
- **Hairline** (hairline): every border and chart axis.
- **Hairline 2** (hairline-2): table row dividers, chart gridlines, bar and range tracks, segmented-control track, neutral tag.

### Named Rules
**The One Indigo Rule.** Indigo means data or selection. Buttons that perform actions are ink or white, never indigo.

**The Direction Only Rule.** Green and red encode price direction (drop green, rise red) and nothing else; the single exception is the green fresh-source dot beside its amber stale counterpart.

**The Amber Is Stale Rule.** Amber appears only where a source is frozen or out of date.

**The Cool Series Rule.** Multi-series charts (Europe countries) draw from indigo, sky, slate and muted-2 only; no signal hues as series colors.

## Typography

**Display Font:** none; the system has no display tier.
**Body Font:** Inter 400/500/600 (with -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif)

**Character:** One neutral grotesque at small sizes, `cv11` and `ss01` alternates on, tabular figures globally so every number column aligns.

### Hierarchy
- **Headline** (600, 20px, 1.3, -0.015em): page title in the header, one per route.
- **Metric** (600, 24px, -0.02em): KPI values; unit set inline at 13px/500 in muted. Drops to 20px under 520px.
- **Title** (600, 14px): card titles. Sub-sections inside a card use 600 at 13px.
- **Body** (400, 13px, 1.45): base text, table cells, bar labels.
- **Label** (500, 12px): KPI subs, hints, column headers, legend chips, pager, segmented controls.
- **Axis** (400, 11px, muted): chart tick labels. Tags use 600 at 11px.

### Named Rules
**The Tabular Rule.** `font-variant-numeric: tabular-nums` is set on body and never turned off; numbers use French spacing in FR mode.

**The Weight Not Color Rule.** Hierarchy is built from 400/500/600 weight and size; text color only steps ink, ink-2, muted, muted-2.

## Layout

Desktop is a two-column grid: a sticky full-height 232px sidebar and a main column capped at 1440px with 22px/32px padding and a 16px vertical stack gap. Each route follows the same order: header (title, source line, segmented date range, export), a four-up KPI row (14px gap), a row of a flexible chart card beside a 380px breakdown card (or two equal cards), then a full-width table card.

Breakpoints: at 1180px the chart row stacks and KPIs go two-up; at 900px the sidebar is replaced by a sticky top bar (white at 92% with saturate/blur backdrop) holding brand, source freshness and horizontally scrolling tabs, main padding drops to 16px, search fields go full width; at 520px KPI sparklines hide and the export label collapses to its icon.

Internal rhythm: card padding 14px/16px, control height 32px, bar rows 28px, table cells 8px/10px with 16px outer gutters (the table bleeds to the card edge).

## Elevation & Depth

Flat. Depth is carried by 1px hairline borders and the subtle-canvas sidebar, not shadows. Two shadows exist, both functional.

### Shadow Vocabulary
- **Pressed chip** (`box-shadow: 0 1px 2px rgba(15,23,42,0.08), 0 0 0 1px rgba(15,23,42,0.04)`): the selected option inside a segmented control or tab set.
- **Floating tip** (`box-shadow: 0 8px 24px rgba(15,23,42,0.12), 0 2px 6px rgba(15,23,42,0.06)`): chart tooltips only.

### Named Rules
**The Hairline Rule.** Cards, tiles, inputs and buttons are separated by a 1px hairline, never by a shadow. Only overlays float.

## Shapes

Soft rectangles at two radii: 10px for containers (cards, KPI tiles, notices, error blocks) and 7px for controls (buttons, inputs, selects, nav items, segmented tracks, brand mark), with 5px for options nested inside a 7px track. Pills (999px) for tags and legend chips. Data marks are small and squared off: 4px track and bar ends, 2px column corners, 8px rounded-2px legend swatches, 7px round status dots. Listing thumbnails are 48x36 at 5px.

## Components

### Buttons
- **Shape:** gently rounded (7px), fixed 32px height, 14px icon with 6px gap.
- **Default:** white with hairline border and ink-2 text, 500 weight; hover moves to canvas-subtle with a darker #cbd5e1 border.
- **Primary:** ink fill, white text; hover to slate. One per header (export).
- **Disabled:** 50% opacity, not-allowed cursor.

### Segmented Controls and Tabs
- **Style:** hairline-2 track with 2px inset; options are 12px/500 muted text.
- **State:** the selected option becomes a white chip with ink text and the pressed-chip shadow. Used for date range, chart metric and table tabs.

### Chips (tags and legend toggles)
- **Tag:** 11px/600 pill; neutral by default, rise or drop washes for price direction.
- **Legend toggle:** white pill with hairline border and 8px swatch; off state greys text to muted-2 and swatch to hairline.

### Cards / Containers
- **Corner Style:** 10px.
- **Background:** canvas.
- **Shadow Strategy:** none (see Elevation).
- **Border:** 1px hairline.
- **Internal Padding:** 14px 16px; header row min 32px with 14px/600 title and 12px muted hint right-aligned.

### KPI Tiles
Label (muted, 500) on top, metric value with inline unit, 12px sub line colored only when it is a price direction, and an 84x32 indigo sparkline anchored bottom right.

### Inputs / Fields
- **Style:** 32px, white, hairline border, 7px radius; search carries a 14px muted icon at 9px left; selects use a custom chevron.
- **Hover / Focus:** border to #cbd5e1 on hover; focus sets indigo border plus a 3px indigo ring at 15% alpha.

### Navigation
- **Sidebar:** brand row (24px indigo mark, 15px/650 wordmark), 11px uppercase group labels, nav items with 16px icon, label and right-aligned count; hover canvas-hover, active indigo-wash with indigo text and count. A sources list shows each scraper with a fresh (green) or stale (amber) dot and date. Foot holds the FR/EN toggle (active option ink fill) and a GitHub link.
- **Mobile:** sticky blurred top bar; nav items lose icons and counts and mark the active route with a 2px indigo underline.

### Data Table
Sticky 12px muted headers with sortable buttons (sort icon at 35% until active), right-aligned numeric columns, 1px hairline-2 row dividers, canvas-subtle row hover, thumbnail title cells truncated at 420px, muted external-link icons turning indigo on hover. A tools row above holds search, selects and a muted count; a pager below holds prev/next default buttons.

### Bar List and Range Bar
Bar list rows: label, 8px hairline-2 track with indigo (or indigo-soft) fill, tabular value, muted share. Range bar: indigo-soft interquartile band on a hairline-2 track with a 2px indigo median tick.

### Charts
Hand-built SVG: 2px indigo lines with a 16%-to-0 area gradient, hairline-2 gridlines, 11px muted axis labels, a hover guide line and 4px white-stroked dots feeding the floating tip. Histogram columns are indigo-pale with the highlighted band in indigo. Diverging bars put rises (red) above and drops (green) below a midline.

### States
Skeleton blocks shimmer between hairline-2 and canvas-subtle at 6px radius. Errors use a rise-wash block with #fecaca border, dark red text and a default retry button. The stale notice is an amber-wash strip with a stale-amber icon.

## Do's and Don'ts

### Do:
- **Do** keep every number in tabular Inter and show its source and date nearby.
- **Do** use indigo for series, fills and selected state, and indigo-soft/indigo-pale for secondary data.
- **Do** separate surfaces with 1px hairline (#e2e8f0) borders at 10px (containers) or 7px (controls) radius.
- **Do** mark frozen sources with the amber notice and amber dot, never by hiding them.
- **Do** ship every UI string in FR and EN.

### Don't:
- **Don't** use green or red for anything but price direction (beyond the fresh-source dot).
- **Don't** use amber for anything but stale data.
- **Don't** fill action buttons with indigo; primary actions are ink.
- **Don't** add drop shadows to cards, tiles or controls; shadows belong to tooltips and pressed segment chips only.
- **Don't** introduce a second typeface or a display tier above the 20px headline.
