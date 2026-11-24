---
name: Technical Precision
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3d4a42'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6d7a72'
  outline-variant: '#bccac0'
  surface-tint: '#006c4a'
  primary: '#006948'
  on-primary: '#ffffff'
  primary-container: '#00855d'
  on-primary-container: '#f5fff7'
  inverse-primary: '#68dba9'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#825100'
  on-tertiary: '#ffffff'
  tertiary-container: '#a36700'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#85f8c4'
  primary-fixed-dim: '#68dba9'
  on-primary-fixed: '#002114'
  on-primary-fixed-variant: '#005137'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12.5px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.03em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system embodies the utilitarian clarity and precision of modern developer tools, heavily inspired by modern component libraries (such as shadcn/ui and Tailwind CSS). It projects authoritative engineering rigor, effortless legibility, and architectural safety for developer-first data plumbing and Model Context Protocol (MCP) integrations.

### Design Movement & Aesthetic
- **Modern Minimalist & Utilitarian**: Built on neutral slate surfaces, ultra-crisp 1px borders, high-contrast typography, and purposeful semantic accents.
- **Atmosphere**: Focused, technical, transparent, and noise-free. Whitespace acts as structural pacing rather than mere decoration.
- **Target Audience**: Infrastructure engineers, full-stack builders, and AI engineers needing instant comprehension of data schemas, permission boundaries, and protocol mechanics.
- **Sensory Balance**: Cool slate neutrals ground the interface, while precise semantic colors (emerald for secure reads/success, amber for state mutations, crimson for blocked/destructive operations) communicate protocol statuses with absolute immediacy.

## Colors

The palette employs a calibrated slate scale paired with high-intent semantic accents. Pure white serves as the default canvas, with stratified slate tones providing subtle structural separation.

### Palette Architecture
- **Primary Canvas & Surfaces**:
  - Base Background: `#ffffff`
  - Subsurface / Sidebar Canvas: `#f8fafc` (slate-50)
  - Card & Code Light Background: `#f1f5f9` (slate-100)
  - Code Dark Surface: `#0f172a` (slate-900)
  - Code Highlighted Row / Sub-container: `#1e293b` (slate-800)
- **Borders & Dividers**:
  - Default Border: `#e2e8f0` (slate-200)
  - Subtle Inset / Code Border: `#cbd5e1` (slate-300)
  - Dark Mode / Code Block Border: `#334155` (slate-700)
- **Text & Content**:
  - Display / Primary Text: `#0f172a` (slate-900)
  - Secondary / Body Text: `#334155` (slate-700)
  - Muted / Placeholder Text: `#64748b` (slate-500)
  - Inverted / Code Text: `#f8fafc` (slate-50)
- **Semantic Accents**:
  - **Read / Success / Secure**: Primary `#059669` (emerald-600), Vibrant `#10b981` (emerald-500), Surface Tint `#ecfdf5` (emerald-50), Border Tint `#a7f3d0` (emerald-200).
  - **Write / Warning / Mutation**: Primary `#f59e0b` (amber-500), Surface Tint `#fffbeb` (amber-50), Border Tint `#fde68a` (amber-200).
  - **Blocked / Destructive / Critical**: Primary `#ef4444` (red-500), Surface Tint `#fef2f2` (red-50), Border Tint `#fecaca` (red-200).
  - **Informational / Schema**: Primary `#0284c7` (sky-600), Surface Tint `#f0f9ff` (sky-50), Border Tint `#bae6fd` (sky-200).

## Typography

The type scale combines the neutral structural neutrality of `Inter` for documentation reading with the exact geometric spacing of `JetBrains Mono` for code, syntax, and protocol schema structures.

### Application Rules
- **Headings**: Dense tracking (`-0.02em` to `-0.025em`) ensures an assertive, modern editorial presence. Headings must avoid decorative treatments and rely solely on scale and weight.
- **Body Text**: Body prose is standardized at 15px with relaxed line height (24px) for long-form documentation reading comfort.
- **Monospace Elements**: Inline code, parameters, schemas, HTTP verbs, and SQL tokens use `JetBrains Mono`. When placed inline inside body text, code snippets render with a faint `#f1f5f9` slate background and a 1px `#e2e8f0` border at 0.875em scale.
- **Labels & Badges**: Small badges, tool names, and parameters use `JetBrains Mono` uppercase or lowercase identifier tokens with light letter spacing for sharp visual anchoring.

## Layout & Spacing

The layout is grounded in a classic, high-density documentation layout system with fluid vertical flow and structural horizontal constraints.

### Layout Model
- **Shell Structure**: A fixed 3-column architecture on desktop:
  1. **Primary Navigation (Left)**: Fixed 260px width, sticky positioning, independent scroll, background `#f8fafc` with a right border in `#e2e8f0`.
  2. **Documentation Canvas (Center)**: Fluid main content area constrained to a maximum width of `832px` (`52rem`) to prevent lines of prose and code from becoming too long to read comfortably.
  3. **Table of Contents (Right)**: Fixed 220px to 260px width, sticky positioning, displaying "On this page" hierarchy.
- **Top Navigation Bar**: Fixed at 56px height, spans 100% viewport width, featuring a hairline bottom border `#e2e8f0` with translucent backdrop blur (`rgba(255, 255, 255, 0.85)`).

### Breakpoints & Adaptations
- **Desktop (>= 1280px)**: Full 3-column layout visible.
- **Tablet / Small Laptop (768px – 1279px)**: Table of Contents collapses into an in-page dropdown or top summary. Left sidebar remains collapsible via drawer or persistent icon rail.
- **Mobile (< 768px)**: Single column with fluid stretch. Navigation shifts entirely to a slide-over sheet triggered from the top navbar. Inner content gutters compress from 24px (`1.5rem`) to 16px (`1rem`).

## Elevation & Depth

Visual depth is achieved through structural layering and crisp borders rather than deep or dramatic drop shadows.

### Depth Mechanics
- **Hairline Borders over Shadows**: Containers, cards, tables, and dropdowns use explicit 1px `#e2e8f0` borders to structure the layout.
- **Elevation Hierarchy**:
  - **Level 0 (Base)**: `#ffffff` canvas and `#f8fafc` structural sidebars.
  - **Level 1 (Cards, Code Boxes, Tables)**: `#ffffff` or `#0f172a` surfaces with a 1px border. Shadow: `0 1px 2px 0 rgba(0, 0, 0, 0.05)`.
  - **Level 2 (Popovers, Tooltips, Command Palette)**: Floating cards with `0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05)` and a `#cbd5e1` boundary border.
  - **Level 3 (Modal Dialogs & Backdrops)**: Modal dialogs use `0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05)` over a diffused slate backdrop (`rgba(15, 23, 42, 0.4)` with 4px backdrop blur).
- **Dark Mode Code Blocks**: Code blocks reject outer shadows in favor of crisp boundary borders (`1px solid #334155`), ensuring technical definition on both light and dark document contexts.

## Shapes

The interface adopts a disciplined, compact shape system (`roundedness: 1`).

### Geometry System
- **Base Element Corner Radius**: `0.25rem` (4px) for input fields, buttons, table containers, alerts, and inline code tags.
- **Mid-Tier Elements (`rounded-lg`)**: `0.5rem` (8px) for cards, preview panes, code blocks, and dialog boxes.
- **Badges & Pills**: Distinct semantic badges (e.g., protocol tags, HTTP status pills, tool permission chips) utilize fully rounded ends (`9999px`) to visually differentiate metadata from actionable rectangular controls.

## Components

### Top Navigation Bar
- **Height**: 56px.
- **Structure**: Brand logomark paired with semibold wordmark, followed by a monospace version pill (`v1.0.0`, slate background, slate border).
- **Center / Action Area**: Command palette trigger showing `Search documentation...` with a trailing `⌘K` keyboard shortcut badge (`0.25rem` border radius, `#f1f5f9` fill).
- **Right Area**: Direct links to Protocol Specification, Documentation, Theme toggle icon button, and an outlined GitHub repository button displaying live star count.

### Documentation Navigation Sidebar
- **Sections**: Grouped under small uppercase monospace section headers (`#64748b`, 11px, tracking +0.05em).
- **Navigation Links**: 14px `Inter`, 32px height, left padding aligned with subtle border guides. Active link is emphasized with `#0f172a` text, `#f1f5f9` soft background fill, and a left 2px emerald indicator bar.

### Code Blocks
- **Theme**: Slate/midnight dark mode (`#0f172a` surface, `#1e293b` header bar, `#334155` border).
- **Header**: File path or tool name rendered in 12px `JetBrains Mono` with file type icon on the left; top-right hosts a copy button transitioning to a green checkmark upon click.
- **Syntax Tokens**: Green for strings, sky blue for keys/methods, amber for numbers/booleans, and slate-400 for comments.

### Badges & Tool Schema Pills
- **Geometry**: Pill-shaped (`rounded-full`), 20px height, 8px horizontal padding, 11px `JetBrains Mono` medium.
- **Variants**:
  - `Read`: Background `#ecfdf5`, border `#a7f3d0`, text `#059669`.
  - `Write`: Background `#fffbeb`, border `#fde68a`, text `#b45309`.
  - `Blocked / Danger`: Background `#fef2f2`, border `#fecaca`, text `#dc2626`.
  - `Version / Info`: Background `#f1f5f9`, border `#e2e8f0`, text `#475569`.

### Alerts & Callout Banners
- **Geometry**: 8px border radius, 1px perimeter border, with an emphasized 3.5px solid left border.
- **Variants**:
  - **Info**: Soft blue background `#f0f9ff`, left border `#0284c7`, icon: info-circle.
  - **Warning (Write Tools)**: Soft amber `#fffbeb`, left border `#f59e0b`, icon: alert-triangle.
  - **Security (Blocked Queries)**: Soft red `#fef2f2`, left border `#ef4444`, icon: shield-alert.

### Data Tables
- **Container**: Bordered table with `#e2e8f0` outer frame and divider lines.
- **Headers**: Surface `#f8fafc`, uppercase 11px `JetBrains Mono`, text `#64748b`, bottom border `#cbd5e1`.
- **Rows**: 40px minimum height. Parameter names rendered in bold `JetBrains Mono` with subtle inline code styling; type signatures in slate-500 monospace; descriptions in 13px `Inter`.

### AI Chat & MCP Tool Invocation Panel
- **Container**: Card with 8px radius, `#ffffff` surface, and `#e2e8f0` border.
- **User Prompt**: Clean right-aligned bubble or left-accented row with `#f1f5f9` surface and 14px prose.
- **Tool Invocation Pill**: Collapsible row displaying MCP tool identity (e.g., `pg_sheets.execute_query`), a pill badge indicating `READ` or `WRITE`, execution duration (e.g., `42ms`), and chevron toggle.
- **Tool Output Block**: Nested dark or light monospace container showing structured JSON return payload or spreadsheet cell range.