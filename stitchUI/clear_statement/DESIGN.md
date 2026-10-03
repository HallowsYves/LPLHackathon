---
name: Clear Statement
colors:
  surface: '#f8f9ff'
  surface-dim: '#cddbf0'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eef4ff'
  surface-container: '#e4efff'
  surface-container-high: '#dbe9fe'
  surface-container-highest: '#d5e4f8'
  on-surface: '#0e1d2b'
  on-surface-variant: '#434751'
  inverse-surface: '#243141'
  inverse-on-surface: '#e9f1ff'
  outline: '#737782'
  outline-variant: '#c3c6d3'
  surface-tint: '#315cab'
  primary: '#00377d'
  on-primary: '#ffffff'
  primary-container: '#1f4e9c'
  on-primary-container: '#aac3ff'
  inverse-primary: '#aec6ff'
  secondary: '#665f3d'
  on-secondary: '#ffffff'
  secondary-container: '#eae0b5'
  on-secondary-container: '#6a6341'
  tertiary: '#004420'
  on-tertiary: '#ffffff'
  tertiary-container: '#1f5c35'
  on-tertiary-container: '#93d2a1'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#aec6ff'
  on-primary-fixed: '#001a43'
  on-primary-fixed-variant: '#0e4491'
  secondary-fixed: '#ede3b8'
  secondary-fixed-dim: '#d1c79d'
  on-secondary-fixed: '#201c02'
  on-secondary-fixed-variant: '#4d4727'
  tertiary-fixed: '#b1f2be'
  tertiary-fixed-dim: '#96d5a3'
  on-tertiary-fixed: '#00210d'
  on-tertiary-fixed-variant: '#12512c'
  background: '#f8f9ff'
  on-background: '#0e1d2b'
  surface-variant: '#d5e4f8'
typography:
  display-xl:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 60px
    letterSpacing: -0.01em
  display-xl-mobile:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 48px
  headline-lg:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 52px
  headline-lg-mobile:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 42px
  headline-md:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 44px
  headline-md-mobile:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 36px
  headline-sm:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 38px
  body-xl:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 24px
    fontWeight: '400'
    lineHeight: 38px
  body-lg:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 22px
    fontWeight: '400'
    lineHeight: 36px
  body-bold:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 36px
  numeric-lg:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: 0.02em
  numeric-md:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: 0.02em
  label-lg:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 30px
  label-md:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 2rem
  gutter-mobile: 1.5rem
  margin: 3rem
  margin-mobile: 1.5rem
  space-xs: 0.75rem
  space-sm: 1rem
  space-md: 1.5rem
  space-lg: 2rem
  space-xl: 3rem
---

## Brand & Style

The design system is crafted specifically for older adults (ages 70+) reviewing retirement savings, monthly pensions, and estate distribution, as well as the financial advisors and family members who support them. The core brand tenets are clarity, calmness, radical legibility, and dignity.

The aesthetic blends **Corporate/Modern clarity with high-contrast accessibility**. Rather than looking clinical or infantile, the design conveys the quiet authority of classic print passbooks and high-end editorial paper goods:
- **Dignified & Reassuring:** Eliminates panic-inducing alert patterns. Financial statements use plain, conversational language alongside explicit numbers.
- **Uncompromising Contrast:** Adheres to WCAG AAA standards (7:1 contrast minimum across all structural text and actions).
- **Physical Affordance & Generous Scale:** Controls, inputs, and tap targets are deliberately enlarged to comfortably accommodate mild tremors, declining motor control, and presbyopia without feeling patronizing.

## Colors

The palette uses warm paper tones and deep mineral hues to relieve eye strain and eliminate blinding pure-white glares:

- **Canvas & Card Base:** The canvas sits at `#FAFAF7` (warm alabaster). Card containers use `#FFFFFF` (pure white) to construct discrete, readable foreground surfaces.
- **Primary Accent (`#1F4E9C`):** A deep, reassuring maritime blue used for primary actions, selected indicators, and major progress bars. Its contrast against `#FFFFFF` is 7.4:1, exceeding WCAG AAA standards.
- **Secondary Accent (`#FEF3C7` / `#D97706`):** Soft warm amber used strictly for explanatory highlight callouts, note boxes, and advisory tips. Pair the fill `#FEF3C7` with text `#78350F` and a defined contour border `#F59E0B`. Never rely on amber as a primary action color.
- **Tertiary Accent (`#14532D`):** A forest green applied for positive confirmations, completed items, and account balance gains. Contrast against white is 9.2:1. Alarming, high-saturation reds are prohibited; necessary notices or reductions rely on a grounded burgundy (`#7F1D1D`) with accompanying explicit textual descriptions.
- **Primary Text (`#12202F`):** Deep charcoal navy, providing a softer reading experience than pure black (`#000000`) while yielding an AAA-compliant contrast ratio of over 14:1 on white and 13.5:1 on `#FAFAF7`.
- **Structural Outlines:** Controlled by `#D1D5DB` (dividers) and `#94A3B8` (interactive borders), guaranteeing that component boundaries remain perceivable across varying display qualities and vision levels.

## Typography

The design system prioritizes character disambiguation (e.g., distinguishing between zero `0` and capital `O`, or lowercase `l` and digit `1`). **Atkinson Hyperlegible Next** provides distinct letterforms created specifically for low-vision readers, falling back gracefully to `Verdana, Inter, system-ui, sans-serif`.

Rules for typographic execution:
- **Baseline Floor:** The absolute minimum text size anywhere in the interface is 20px (for compact labels only). Default running copy is strictly 22px to 24px.
- **Generous Leading:** Line height is fixed at 1.55 to 1.65× the font size to ensure users do not lose their place across lines of financial text.
- **Tabular & Bold Numerics:** All currency figures, interest rates, and balances use tabular figure spacing and bold weights (`700`) to enable effortless vertical scanning across statements.
- **Sentence Case Only:** Never use all-caps for buttons or navigation items; title case or sentence case retains standard word shapes that are significantly easier to decode.

## Layout & Spacing

The layout model is a grounded, readable **fixed-max-width grid** centered on desktop screens (max width `1160px`) to prevent excessively wide text lines that cause visual fatigue:

- **Desktop & Tablet:** An 8-column grid with generous 32px (`2rem`) gutters and 48px (`3rem`) page margins. Paragraphs and financial advice blocks are capped at 65 characters per line (typically 6 columns).
- **Mobile (Phone / Small Tablets):** A 4-column grid with 24px (`1.5rem`) margins. Content reflows vertically into single-column cards.
- **Spacing Rhythm:** Elements maintain a mandatory spacing floor. Adjacent interactive targets require a minimum gap of 24px (`space-md`) to eliminate errant touches. Major section blocks are divided by 48px (`space-xl`).

## Elevation & Depth

To avoid optical haze, this design system does not use heavy multi-stop drop shadows, neomorphic bevels, or frosted glass surfaces. Depth is established through **tonal separation reinforced by distinct structural borders**:

- **Canvas to Card Layer:** The `#FFFFFF` card surface rests directly upon the `#FAFAF7` canvas. Separation is achieved through an explicit 1.5px solid border (`#D1D5DB`) backed by an ultra-subtle, non-directional resting shadow: `0px 2px 6px rgba(18, 32, 47, 0.05)`.
- **Focused / Elevated State:** Modals, persistent summary drawers, and active cards take a 2px solid border (`#1F4E9C`) accompanied by an ambient soft spread: `0px 8px 24px rgba(18, 32, 47, 0.08)`.
- **High-Visibility Focus Rings:** For keyboard and screen magnification accessibility, all focused interactive elements display an unbroken 4px outer ring (`#1F4E9C` with a 2px white gap offset).

## Shapes

The interface employs a balanced **Rounded** geometry (`roundedness: 2`), utilizing 8px to 16px corner radii to establish a warm, approachable feel while maintaining structural stability:

- **Primary Actions & Chips:** Use 12px (`0.75rem`) to 16px (`1rem`) corner radii, avoiding hyper-thin sharp corners and extreme pill forms that can obscure button hit areas.
- **Data Cards & Dialogs:** Grounded with a 16px (`1rem`) border radius, framing information clearly against the background.
- **Form Fields & Inputs:** Feature an 8px (`0.5rem`) radius with a distinct 2px continuous border, clearly defining the editable area.

## Components

### Buttons & Interactive Triggers
- **Dimensions:** Primary and secondary actions must have an absolute minimum height of 64px (desktop) to 72px (touch screens), with horizontal padding of at least 32px.
- **Styling:** Primary buttons use `#1F4E9C` fill, white bold 22px text, and an integrated 2px solid tone-on-tone edge. Secondary buttons feature a white background, `#12202F` bold text, and a crisp 2px border in `#1F4E9C`.
- **Strict Prohibition on Icon-Only Buttons:** Every icon must be accompanied by explicit, bold, human-readable text (e.g., a phone handset icon is always paired with "Call Financial Advisor").

### Form Inputs & Text Fields
- **Height & Size:** Field height is minimum 68px. Entered text renders at 22px (`body-lg`) in `#12202F`.
- **Labels:** Floating or vanishing labels are forbidden. Permanent, high-contrast labels (20px bold) are placed strictly above the input with explicit micro-instructions directly below (e.g., "Format: MM / DD / YYYY").
- **Borders:** Resting inputs carry a 2px `#94A3B8` border. Active focus triggers a 4px primary blue ring.

### Cards & Financial Statement Summaries
- **Structure:** Encased in pure white cards with 32px inner padding, separated by 1.5px `#D1D5DB` borders.
- **Summary Rows:** Financial ledger rows maintain a 60px minimum row height with 1px hairline dividers (`#E5E7EB`). Labels sit on the left (22px regular); sums sit on the right (26px tabular bold).

### Checkboxes & Radio Controls
- **Scale:** Hitbox squares and radio circles are enlarged to 36px × 36px with a 3px outer border. The clickable hit area encompasses the entire label row (minimum 64px tall), with 20px clearance between target centers.
- **Selected States:** Filled with `#1F4E9C` featuring an unmistakable, high-contrast white checkmark (minimum 3.5px stroke weight).

### Advisory Callout Boxes
- **Visuals:** Warm amber surface (`#FEF3C7`) bordered by a 2px `#F59E0B` outline. Contains simple, jargon-free explanations of complex terms (e.g., "Required Minimum Distribution (RMD)"). Text inside is rendered in `#78350F` at 22px with a leading advisory icon.

### Plain Language Glossary Chips
- **Interaction:** Embedded directly into body copy next to financial terms. Rendered as interactive chips with a dotted underline and a clear "Explain This" text indicator, opening an inline, accessible popover drawer with plain-language definitions.