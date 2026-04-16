# Requirements Document

## Introduction

This feature redesigns the Trading-Agent dashboard from its current dark financial aesthetic (dark slate/navy backgrounds, light text) to Apple's minimalist, premium, light-mode design language. The redesign covers the global color system, typography, spacing, border radii, glassmorphism effects, and all major UI components across the Next.js 14 / React 18 / Tailwind CSS 3 frontend. The goal is a cohesive, polished interface that feels modern and trustworthy while preserving all existing functionality.

## Glossary

- **Dashboard**: The Trading-Agent web application rendered by the Next.js frontend.
- **Design_System**: The set of Tailwind CSS tokens (colors, radii, shadows, typography) defined in `tailwind.config.ts` and `globals.css` that govern the visual appearance of the Dashboard.
- **Header**: The sticky top navigation bar rendered by `frontend/components/layout/Header.tsx`.
- **Sidebar**: The collapsible left navigation panel rendered by `frontend/components/layout/Sidebar.tsx`.
- **QueryInput**: The stock-query input component rendered by `frontend/components/analysis/QueryInput.tsx`.
- **PriceChart**: The candlestick/line price chart component rendered by `frontend/components/charts/PriceChart.tsx`.
- **AgentCards**: The agent-selection card grid rendered by `frontend/components/analysis/AgentCards.tsx`.
- **ResultTabs**: The tabbed agent-result viewer rendered by `frontend/components/results/ResultTabs.tsx`.
- **DebatePanel**: The debate-configuration and live-debate panel rendered by `frontend/components/analysis/DebatePanel.tsx`.
- **StockDataPanel**: The stock-info / money-flow / news panel rendered by `frontend/components/charts/StockDataPanel.tsx`.
- **Apple_Color_Palette**: The specific color values: background `#f5f5f7`, card `#ffffff`, secondary background `#fafafa`, primary text `#1d1d1f`, muted text `#6e6e73`, border `#e5e5e7`, accent blue `#0071E3`, success green `#34C759`, warning/danger red `#FF3B30`.
- **Apple_Typography**: The font stack `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif` with title weight 700 at 32–48 px and body weight 500 at 14–16 px.
- **Glassmorphism**: A visual effect combining `backdrop-blur` with a semi-transparent white background (`bg-white/80`) and a subtle border.
- **Apple_Radius**: Border-radius values of 12 px (`apple`) and 16 px (`apple-lg`) as custom Tailwind tokens.
- **Apple_Shadow**: Custom Tailwind shadow tokens `apple-sm` (`0 1px 3px rgba(0,0,0,0.08)`) and `apple-md` (`0 4px 16px rgba(0,0,0,0.12)`).

---

## Requirements

### Requirement 1: Design System Tokens

**User Story:** As a frontend developer, I want a centralized set of Apple-style design tokens in Tailwind config and global CSS, so that all components can reference consistent colors, radii, and shadows without hardcoding values.

#### Acceptance Criteria

1. THE Design_System SHALL define custom Tailwind color tokens: `apple-bg` (`#f5f5f7`), `apple-card` (`#ffffff`), `apple-secondary` (`#fafafa`), `apple-text` (`#1d1d1f`), `apple-muted` (`#6e6e73`), `apple-border` (`#e5e5e7`), `apple-blue` (`#0071E3`), `apple-green` (`#34C759`), and `apple-red` (`#FF3B30`) in `tailwind.config.ts`.
2. THE Design_System SHALL define custom border-radius tokens `apple` (12 px) and `apple-lg` (16 px) in `tailwind.config.ts`.
3. THE Design_System SHALL define custom shadow tokens `apple-sm` and `apple-md` in `tailwind.config.ts`.
4. THE Design_System SHALL set the global `body` background to `apple-bg` (`#f5f5f7`) and the default text color to `apple-text` (`#1d1d1f`) in `globals.css`.
5. THE Design_System SHALL apply Apple_Typography (font stack, weights, and sizes) as the default `font-family` on the `body` element in `globals.css`.
6. THE Design_System SHALL update the `.card` utility class in `globals.css` to use `apple-card` background, `apple-border` border color, `apple-sm` shadow, and `apple` border-radius.

---

### Requirement 2: Header Redesign

**User Story:** As a user, I want a clean, sticky header with glassmorphism so that the navigation always remains visible and feels premium.

#### Acceptance Criteria

1. THE Header SHALL use a white base background (`#ffffff`) with `backdrop-blur-md` and `bg-white/80` to produce a Glassmorphism effect.
2. THE Header SHALL be sticky (fixed to the top of the viewport) and render above all page content via an appropriate z-index.
3. THE Header SHALL display the application logo or title on the left and navigation links on the right, separated by a bottom border using `apple-border` color.
4. THE Header SHALL apply Apple_Typography to all text elements within it.
5. WHEN the user scrolls the page, THE Header SHALL remain visible at the top of the viewport.

---

### Requirement 3: Sidebar Redesign

**User Story:** As a user, I want a collapsible sidebar with Apple-style hover and active states so that navigation is intuitive and space-efficient.

#### Acceptance Criteria

1. THE Sidebar SHALL use `apple-secondary` (`#fafafa`) as its background color.
2. THE Sidebar SHALL display a right-side border using `apple-border` color.
3. WHEN a navigation item is in the active state, THE Sidebar SHALL render it with `apple-blue` (`#0071E3`) background and white text.
4. WHEN the user hovers over a non-active navigation item, THE Sidebar SHALL apply a subtle background highlight using `apple-border` color.
5. THE Sidebar SHALL support a collapsed state that hides navigation labels and reduces its width to an icon-only strip.
6. WHEN the viewport width is below the `sm` breakpoint (640 px), THE Sidebar SHALL be hidden by default.
7. THE Sidebar SHALL apply `transition-all duration-300` to all interactive state changes.

---

### Requirement 4: QueryInput Redesign

**User Story:** As a trader, I want a clean, light-themed query input so that entering stock codes feels modern and accessible.

#### Acceptance Criteria

1. THE QueryInput SHALL use `apple-card` (`#ffffff`) as its container background with an `apple-border` border and `apple` border-radius.
2. THE QueryInput SHALL render the text input field with a white background, `apple-border` border, and `apple` border-radius.
3. WHEN the text input receives focus, THE QueryInput SHALL display a focus ring using `apple-blue` (`#0071E3`) color.
4. THE QueryInput SHALL render the primary action button (start/stop analysis) with `apple-blue` (`#0071E3`) background and white text.
5. WHEN the primary action button is pressed, THE QueryInput SHALL apply an `active:scale-95` transform.
6. WHEN the analysis is running, THE QueryInput SHALL render the stop button with `apple-red` (`#FF3B30`) background.
7. IF the input field is empty and the analysis is not running, THEN THE QueryInput SHALL render the action button in a disabled visual state using `apple-border` background and `apple-muted` text.

---

### Requirement 5: PriceChart Redesign

**User Story:** As a trader, I want the price chart to use a light background with subtle grid lines so that price data is easy to read in the Apple aesthetic.

#### Acceptance Criteria

1. THE PriceChart SHALL render its card container with `apple-card` background, `apple-border` border, `apple` border-radius, and `apple-sm` shadow.
2. THE PriceChart SHALL render chart grid lines using `#f0f0f0` stroke color.
3. THE PriceChart SHALL render axis labels and tick text using `apple-muted` (`#6e6e73`) color.
4. THE PriceChart SHALL render the Recharts `Tooltip` with a white background, `apple-border` border, and `apple` border-radius.
5. WHEN the price change is positive, THE PriceChart SHALL display the change value in `apple-green` (`#34C759`).
6. WHEN the price change is negative, THE PriceChart SHALL display the change value in `apple-red` (`#FF3B30`).
7. THE PriceChart SHALL apply Apple_Typography to all text elements within the chart header.

---

### Requirement 6: AgentCards Redesign

**User Story:** As a user, I want agent selection cards with a light, elevated appearance so that selecting agents feels tactile and clear.

#### Acceptance Criteria

1. THE AgentCards SHALL render its container with `apple-card` background, `apple-border` border, `apple` border-radius, and `apple-sm` shadow.
2. THE AgentCards SHALL render each individual agent card with `apple-card` background, `apple-border` border, and `apple` border-radius.
3. WHEN the user hovers over an agent card, THE AgentCards SHALL apply `apple-md` shadow and a `-translate-y-1` transform.
4. WHEN an agent card is selected, THE AgentCards SHALL highlight its border with `apple-blue` (`#0071E3`) color.
5. THE AgentCards SHALL apply `transition-all duration-300` to all card hover and selection state changes.
6. THE AgentCards SHALL render agent name text using `apple-text` (`#1d1d1f`) for selected cards and `apple-muted` (`#6e6e73`) for unselected cards.

---

### Requirement 7: ResultTabs Redesign

**User Story:** As a user, I want result tabs with a light background and a blue underline for the active tab so that switching between agent results is visually clear.

#### Acceptance Criteria

1. THE ResultTabs SHALL render the tab bar with `apple-secondary` (`#fafafa`) background and `apple-border` bottom border.
2. WHEN a tab is active, THE ResultTabs SHALL display a bottom underline indicator using `apple-blue` (`#0071E3`) color and render the tab label in `apple-blue`.
3. WHEN a tab is inactive, THE ResultTabs SHALL render the tab label in `apple-muted` (`#6e6e73`) color.
4. WHEN the user hovers over an inactive tab, THE ResultTabs SHALL transition the label color toward `apple-text` (`#1d1d1f`).
5. THE ResultTabs SHALL apply `transition-all duration-300` to all tab state changes.

---

### Requirement 8: DebatePanel Redesign

**User Story:** As a user, I want the debate panel to use a white background with dark bold titles and light inputs so that debate configuration and live debate content are easy to read.

#### Acceptance Criteria

1. THE DebatePanel SHALL render its container with `apple-card` (`#ffffff`) background, `apple-border` border, and `apple` border-radius.
2. THE DebatePanel SHALL render section titles in `apple-text` (`#1d1d1f`) with font-weight 700.
3. THE DebatePanel SHALL render the internal tab switcher with `apple-secondary` (`#fafafa`) background.
4. WHEN an internal tab is active, THE DebatePanel SHALL render it with `apple-card` background and `apple-blue` text.
5. THE DebatePanel SHALL render range inputs with `apple-blue` (`#0071E3`) accent color.
6. THE DebatePanel SHALL render the status badge using `apple-green` (`#34C759`) tones when the debate is running and `apple-border` tones when idle.

---

### Requirement 9: StockDataPanel Redesign

**User Story:** As a user, I want the stock data panel to use a white background with a clean grid layout so that company info, money flow, and news are easy to scan.

#### Acceptance Criteria

1. THE StockDataPanel SHALL render its container with `apple-card` (`#ffffff`) background, `apple-border` border, and `apple` border-radius.
2. THE StockDataPanel SHALL render the tab navigation bar with `apple-secondary` (`#fafafa`) background and `apple-border` bottom border.
3. WHEN a tab is active, THE StockDataPanel SHALL display a bottom underline indicator using `apple-blue` (`#0071E3`) color.
4. THE StockDataPanel SHALL render data items (company info fields, money-flow cells) with `apple-secondary` (`#fafafa`) background, `apple-muted` label text, and `apple-text` bold value text.
5. THE StockDataPanel SHALL arrange company info fields in a 2-column grid on `md` viewports and a 3-column grid on `lg` viewports.
6. WHEN money flow is positive, THE StockDataPanel SHALL display the value in `apple-green` (`#34C759`).
7. WHEN money flow is negative, THE StockDataPanel SHALL display the value in `apple-red` (`#FF3B30`).

---

### Requirement 10: Animations and Micro-interactions

**User Story:** As a user, I want smooth, Apple-style animations on load and interaction so that the interface feels polished and responsive.

#### Acceptance Criteria

1. THE Dashboard SHALL apply a fade-in animation to page-level content on initial load using a CSS keyframe defined in `globals.css`.
2. WHEN the user hovers over any interactive card component (AgentCards, StockDataPanel news items), THE Dashboard SHALL apply `apple-md` shadow and a `-translate-y-1` transform.
3. WHEN the user presses any button, THE Dashboard SHALL apply an `active:scale-95` transform.
4. THE Dashboard SHALL apply `transition-all duration-300` as the default transition on all interactive elements.

---

### Requirement 11: Responsive Layout

**User Story:** As a user on any device, I want the dashboard layout to adapt gracefully so that all features remain accessible on mobile, tablet, and desktop.

#### Acceptance Criteria

1. WHILE the viewport width is below the `sm` breakpoint (640 px), THE Dashboard SHALL render all content panels in a single-column layout.
2. WHILE the viewport width is at or above the `md` breakpoint (768 px), THE Dashboard SHALL render content panels in a 2-column grid.
3. WHILE the viewport width is at or above the `lg` breakpoint (1024 px), THE Dashboard SHALL render content panels in a 3-column grid with the Sidebar visible.
4. WHILE the viewport width is below the `sm` breakpoint (640 px), THE Sidebar SHALL be hidden and replaced by a mobile-accessible navigation control.
5. THE Dashboard SHALL apply `gap-6` between grid columns on `md` viewports and `gap-8` on `lg` viewports.
