---
name: Old Pages Books Help Desk (SupportPilot)
description: A policy help desk bound like a library shelf; every cited passage is a cloth-bound volume you can pull and open.
colors:
  buckram: "#17352b"
  buckram-deep: "#10261f"
  buckram-ink: "#d9e4dc"
  gold: "#d4b04c"
  gold-soft: "#e8cf86"
  linen: "#dfe3dc"
  linen-deep: "#cfd5cc"
  paper: "#f6f7f4"
  ink: "#1b2420"
  ink-soft: "#46524c"
  rule: "#b9c2b9"
  cloth-returns: "#7a1f2b"
  cloth-shipping: "#1d2f5a"
  cloth-promotions: "#c8962b"
  cloth-catalog: "#553366"
typography:
  display:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 800
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 112"
  headline:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "clamp(1.5rem, 2.2vw, 1.9rem)"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 90"
  title:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 800
    fontVariation: "'wdth' 90"
  body-large:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 400
    lineHeight: 1.6
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 700
    letterSpacing: "0.12em"
    fontVariation: "'wdth' 75"
  call-number:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 800
    fontFeature: "'tnum' 1"
    fontVariation: "'wdth' 75"
  spine-title:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 700
    letterSpacing: "0.04em"
    fontVariation: "'wdth' 62"
rounded:
  stamp: "1px"
  label: "2px"
  control: "3px"
  panel: "4px"
spacing:
  xs: "0.35rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2.5rem"
  gutter: "clamp(1.5rem, 4vw, 3rem)"
components:
  button-primary:
    backgroundColor: "{colors.buckram}"
    textColor: "{colors.gold-soft}"
    rounded: "{rounded.control}"
    padding: "0.6rem 1.15rem"
  button-primary-hover:
    backgroundColor: "{colors.buckram-deep}"
    textColor: "{colors.gold-soft}"
  library-card:
    backgroundColor: "{colors.buckram}"
    textColor: "{colors.buckram-ink}"
    rounded: "{rounded.control}"
    padding: "0.4rem 0.8rem"
  question-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "1rem"
  answer-panel:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "clamp(1.25rem, 3vw, 2.25rem)"
  call-number:
    textColor: "{colors.paper}"
    typography: "{typography.call-number}"
    rounded: "{rounded.label}"
    height: "1.45em"
  spine:
    textColor: "{colors.paper}"
    typography: "{typography.spine-title}"
    width: "clamp(3rem, 7vw, 4rem)"
  spine-call:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.stamp}"
    padding: "0.1rem 0.25rem"
---

# Design System: Old Pages Books Help Desk (SupportPilot)

## Overview

**Creative North Star: "The Library Buckram"**

Every policy document is a bound library volume, and every citation is that volume's spine pulled from the shelf. The world is a reading room rendered in cloth and board: a black-green buckram rail across the top with gold-blocked lettering, a cool linen-grey ground, and near-white paper panels where the work happens. Colour is not decoration here; it is the legend. Each policy document owns exactly one cloth, and that cloth follows the document everywhere it appears: the inline call number in the answer, the spine on the shelf, the legend swatch, the rule above the opened passage.

Density is moderate and calm. One typeface, Archivo, carries the whole system by bending its width axis: wide and heavy for the store name, condensed for stamped labels and call numbers, narrowest for the vertical spine titles. Depth is physical but quiet: the shelf board casts a soft shadow, spines carry cloth bevels, cited volumes are seated forward over the board's lip. Nothing floats, nothing glows.

The world rejects the chat-bubble widget with grey source chips. Sources are objects with a place on a shelf, not tags trailing a message.

**Key Characteristics:**
- Buckram rail, linen ground, paper panels: three surfaces, one hue family (green-grey).
- One cloth per document; the colour is the legend and the catalog number is the only label.
- Archivo's width axis is the type hierarchy's second dimension.
- Spines stand on one shared baseline, height ramped by retrieval rank.
- Gold marks what matters on buckram: brand, active customer card, cited headband, opened ribbon, focus ring.

## Colors

A green-grey library palette (buckram, linen, paper, ink) with gold as the stamped accent and four saturated bookcloths reserved for policy documents.

### Primary
- **Library Buckram** (buckram): the rail, the primary Ask button, the shelf board, the selection highlight, the scrollbar thumb. The world's structural colour.
- **Deep Buckram** (buckram-deep): the rail's bottom edge and the primary button's hover state.
- **Buckram Ink** (buckram-ink): pale green-grey text set on buckram.

### Secondary
- **Blocking Gold** (gold): gold-blocked lettering and marks on buckram: the store name, the active customer card's border and number, the cited spine's headband, the opened spine's ribbon marker, and the global focus outline.
- **Soft Gold** (gold-soft): the Ask button's label and selected-text colour; gold that must read as text on dark cloth.

### Tertiary
- **Returns Oxblood** (cloth-returns): the returns-and-refunds volume. Also the system's alert voice: the error state, the unverified-citation warning, the invalid call number, the textarea caret, and the hover colour of example questions.
- **Shipping Navy** (cloth-shipping): the shipping volume.
- **Promotions Mustard** (cloth-promotions): the promotions volume; the only cloth light enough to take dark text (#1b1406) instead of white.
- **Catalog Plum** (cloth-catalog): the catalog volume.

### Neutral
- **Linen** (linen): the page ground.
- **Deep Linen** (linen-deep): the divider inside the question form and the loading-spine ghost.
- **Paper** (paper): working panels (question form, answer panel) and the stamped label on each spine.
- **Ink** (ink): body text.
- **Soft Ink** (ink-soft): secondary text, section labels, counts, the colophon.
- **Rule** (rule): hairline borders on panels and list dividers.

### Named Rules
**The Cloth Is The Legend Rule.** Each policy document owns one cloth, and that cloth is applied through a single `--cloth` variable to every representation of the document (call number, spine, swatch, passage rule). Never use a cloth colour for anything that is not that document, with one exception: Returns Oxblood doubles as the alert colour.

**The Gold On Buckram Rule.** Gold appears as stamped marks: lettering, borders, headbands, ribbons, the focus ring. It never fills a panel or a large area.

## Typography

**Display Font:** Archivo (variable, width axis loaded via next/font), with system-ui, sans-serif
**Body Font:** Archivo
**Label/Mono Font:** Archivo condensed (wdth 62-75) for labels; passage ids render in the browser's default monospace via `<code>` (not a system rule, see Don'ts)

**Character:** A single grotesque that behaves like a binder's type case: expanded and heavy for the cover title, condensed and tracked for stamped labels, narrowest on the spines.

### Hierarchy
- **Display** (800, 1.35rem, wdth 112): the store name in gold on the rail. Only there.
- **Headline** (800, clamp(1.5rem, 2.2vw, 1.9rem), 1.15, wdth 90, balanced wrap): the single page heading over the question column.
- **Title** (800, 1.15-1.25rem, wdth 90): opened passage heading; empty and error state headings.
- **Body Large** (400, 1.2rem, 1.6, max 68ch): the agent's answer.
- **Body** (400, 1rem, 1.55): everything else; opened passage text at 1.05rem, max 68ch.
- **Label** (700, 0.75-0.85rem, 0.12em tracking, uppercase, wdth 75): section headings for the example list and the shelf, the desk name and customer switch label on the rail.
- **Call number** (800, 0.75rem, wdth 75, tabular numerals): inline citation numbers, customer card numbers, spine stamps.
- **Spine title** (700, 0.8rem, 0.04em, uppercase, wdth 62, vertical): section names running up the spines.

### Named Rules
**The Width Axis Rule.** Hierarchy moves along two axes: weight and width. Expand only for the brand (wdth 112); condense for anything stamped (wdth 62-90). Never introduce a second family to get contrast.

**The Tabular Count Rule.** Every number a reader might compare (order numbers, counts, elapsed seconds, ranks) uses tabular numerals.

## Layout

A two-column desk inside a centred 82rem container: the question column at minmax(18rem, 26rem) on the left, the answer column filling the rest, separated by a clamp(1.5rem, 3vw, 3rem) gap with clamp(1.5rem, 4vw, 3rem) padding. The rail runs full width above, padded clamp(1rem, 4vw, 3rem) horizontally. Below 52rem the desk collapses to one column, the rail stacks, and the customer cards become a two-up grid (one-up below 26rem). The spacing rhythm steps 0.35 / 0.5 / 1 / 1.5 / 2.5rem; section breaks inside the answer panel use 2.25-2.5rem with a hairline rule.

The shelf is a 16rem-tall flex row with every spine bottom-aligned on a single board. Spine heights follow a fixed rank ramp (100, 92, 85, 79, 74, 70, 67, 65 percent), so retrieval rank reads as height.

### Named Rules
**The Shared Baseline Rule.** Every volume stands on the same board. Rank is expressed by height, citation by seating forward; never by moving a spine off the baseline.

## Elevation & Depth

Flat surfaces, physical objects. Panels (question form, answer panel) are flat with a 1px rule border and no shadow. Only the library objects carry depth: the shelf board casts a soft drop shadow, spines carry inner cloth bevels, and cited spines add a soft shadow as they sit forward over the board's lip. Focus is shown with a gold outline or, on the question form, a soft buckram halo.

### Shadow Vocabulary
- **Board shadow** (`box-shadow: 0 6px 10px -6px rgb(16 38 31 / 0.6)`): under the shelf board only.
- **Cloth bevel** (`box-shadow: inset 4px 0 0 rgb(255 255 255 / 0.08), inset -4px 0 0 rgb(0 0 0 / 0.18)`): every spine at rest.
- **Seated forward** (`box-shadow: inset 4px 0 0 rgb(255 255 255 / 0.1), inset -4px 0 0 rgb(0 0 0 / 0.2), 0 10px 14px -8px rgb(16 38 31 / 0.55)`): cited spines.
- **Field halo** (`box-shadow: 0 0 0 3px rgb(23 53 43 / 0.15)`): question form on focus-within.
- **Call ring** (`box-shadow: 0 0 0 2px var(--paper), 0 0 0 3px var(--cloth)`): inline call number on hover or when its passage is open.

### Named Rules
**The Only Objects Cast Shadows Rule.** Shadows belong to things that physically exist on the shelf (board, spines). Panels, buttons, and cards stay flat.

## Shapes

Near-square, bookbinding geometry. Radii are tiny and graded by object size: 1px on spine stamps, 2px on call numbers and swatches, 3px on buttons, customer cards, and spine heads (top corners only), 4px on panels. Spines and legend swatches are rounded only at the top, like a book standing upright. Two clipped details carry the binding: the gold headband strip across a cited spine and a swallow-tailed gold ribbon (clip-path polygon) hanging under the opened spine. An opened passage is not boxed; it is marked by a 3rem by 3px rule in its cloth above the heading.

## Components

### Buttons
Cloth-bound and decisive.
- **Shape:** near-square (3px).
- **Primary (Ask):** buckram fill, soft-gold label, 700 weight, 0.6rem 1.15rem padding, with an inline arrow icon.
- **Hover / Focus:** hover deepens to Deep Buckram; active nudges down 1px; focus is the global 3px gold outline at 2px offset. Transitions are 200ms on the house ease-out curve.
- **Disabled:** grey-green fill (#8c9a91) with pale text; loading replaces the arrow with a spinning loader.
- **Example-question rows:** borderless full-width text rows between hairline rules; on hover they turn Returns Oxblood and slide 0.35rem right.

### Chips (Library cards)
The customer switcher is a radio group of library cards on the rail.
- **Style:** transparent on buckram, 1px pale border, condensed tabular "No. n" followed by the name.
- **State:** hover warms the border toward gold; checked fills a lighter buckram (#24493c), gold border, gold number, white name.

### Cards / Containers
- **Corner Style:** 4px.
- **Background:** Paper on the Linen ground.
- **Shadow Strategy:** none (see Elevation).
- **Border:** 1px Rule.
- **Internal Padding:** clamp(1.25rem, 3vw, 2.25rem) on the answer panel.

### Inputs / Fields
- **Style:** the question form is one paper panel holding a borderless textarea (1rem padding, oxblood caret) above an action bar divided by a Deep Linen hairline.
- **Focus:** the whole form takes a buckram border and a soft buckram halo; the textarea suppresses its own outline.

### Navigation
The rail is the only navigation: buckram, 3px Deep Buckram bottom edge, store name in gold display type, a gold-hairline divider, the desk name as a condensed label, and the library cards on the right. On narrow screens it stacks and the cards form a grid.

### Call Number (signature)
The inline citation. A small stamped rectangle (2px radius, 1.45em tall) in its document's cloth carrying only the passage's rank number, raised slightly off the baseline. Hover or an open passage draws a paper-gapped ring in the same cloth. A citation to a passage that was never retrieved turns into an outlined oxblood "?" with a help cursor.

### Spine and Shelf (signature)
Retrieved passages stand as spines on a buckram board. Each spine wears its document's cloth with inner bevels, a vertical condensed title, and a paper stamp with its rank. Spines slide in from the right (700ms ease-out) on arrival. Retrieved-but-uncited spines are faded (saturate 0.5, brightness 1.06) and recover on hover; cited spines are full cloth, carry a gold headband, and sit forward over the board's lip. The opened spine hangs a gold ribbon below the board. While loading, ghost spines in Deep Linen pulse on the ramp. At rest (empty state) the four volumes stand in full cloth with no headband. A legend of top-rounded swatches names each cloth.

### Opened Passage (signature)
The page inside the volume: no box, a cloth rule above, a title with a cloth-filled rank stamp, the passage text at 1.05rem within 68ch, and a meta line with the chunk id and whether it was cited.

## Do's and Don'ts

### Do:
- **Do** route every document colour through the `--cloth` variable via the `cloth-*` classes so call number, spine, swatch, and passage rule always agree.
- **Do** set dark text (#1b1406) on Promotions Mustard and white on every other cloth.
- **Do** express hierarchy through Archivo's width axis (wdth 62-112) and weight before reaching for size.
- **Do** keep spines on one baseline with height from the rank ramp (100, 92, 85, 79, 74, 70, 67, 65 percent).
- **Do** use the 3px gold focus outline at 2px offset for every focusable element.
- **Do** use tabular numerals for order numbers, ranks, counts, and timers.
- **Do** animate with the house ease-out (cubic-bezier(0.16, 1, 0.3, 1)) at 150-300ms for state, 700ms for the spine arrival, and drop all motion under prefers-reduced-motion.

### Don't:
- **Don't** show sources as grey chips or bubbles attached to a chat message; a source is a volume on the shelf.
- **Don't** use a cloth colour for anything other than its document, except Returns Oxblood as the alert voice.
- **Don't** put a word on a call number or spine stamp; the catalog number is the only label, the cloth is the legend.
- **Don't** fill large areas with gold; it is a stamped mark.
- **Don't** give panels, buttons, or cards drop shadows; only the board and the spines carry depth.
- **Don't** add a second typeface for headings or labels.
