
### Dashboard Sections (Top → Bottom)

#### 1. KPI Strip
- Total Stocks Analyzed | Bullish Count | Bearish Count | Neutral Count | Avg Combined Confidence Score
- Animate all values with a **count-up effect** on page load

#### 2. Confusion Matrix Panel
- Visual 3×3 color-coded grid (Bullish / Neutral / Bearish axes)
  - True Positive → `green` | False Positive → `red` | False Negative → `orange` | True Negative → `neutral`
- Toggle tabs: **Before Correction** vs **After Correction**
- Delta improvement badge (e.g., "+12% F1-Score after correction")

#### 3. Sector Heatmap
- Grid of sector tiles colored by dominant sentiment (Green = Bullish | Red = Bearish | Yellow = Neutral)
- Tile size proportional to stock count per sector
- Hover tooltip: sector name, stock count, avg confidence score

#### 4. Top 10 Priority Setups
- Card carousel or ranked table
- Each card: Ticker · Sector · Pattern · Target Price · Confidence Badge · Sentiment Pill
- Click → opens Technical Chart Drawer

#### 5. Full Stock Table
- Columns: Ticker | Sector | Pattern | Timeframe | Bullish Target | Bearish Target | Confidence | Sentiment | Divergence Flag
- [ ] Search by ticker or sector
- [ ] Sort by any column
- [ ] Filter by: Sector / Sentiment / Confidence Range / Divergence Flag / Misclassification Flag
- [ ] Inline sparkline chart per row (12-month price trend)
- [ ] Expandable row → full pattern breakdown + fundamental data

#### 6. Technical Chart Drawer (Side Panel on Row Click)
- Candlestick chart with Weekly / Daily toggle
- Pattern overlay annotations
- RSI sub-chart (overbought/oversold lines marked)
- MACD sub-chart (signal crossovers marked)
- Entry zone, Target price, Stop-loss as horizontal lines on chart

#### 7. Misclassification Report Panel
- All misclassified stocks listed
- Per stock: Root Cause Tag | Before Classification | After Classification | Correction Applied
- Color-coded rows by root cause type

---

## PART 8 — Engineering & Design Standards

### Tech Stack
- **Charts**: Recharts or Nivo (React-native, not Chart.js)
- **Styling**: Tailwind CSS — match existing app design tokens
- **Data fetching**: `fetch()` with in-memory cache, stale-while-revalidate pattern
- **State**: React context or vanilla useState — no extra library unless already in app

### Design Requirements
- [ ] **Dark mode first-class** — trading dashboards live in dark environments
- [ ] **Fully responsive** — mobile: full-width stacked | desktop: grid layout
- [ ] **Skeleton loaders** on every loading state (mirror real component layout)
- [ ] **KPI count-up animation** on load via CSS `@property` counter or NumberFlow
- [ ] **Export buttons** on all tables (CSV) and all charts (PNG)
- [ ] **Designed empty states** — never just "No data available"
- [ ] Card depth via **box-shadow and surface elevation** — never colored side borders
- [ ] All touch targets **minimum 44×44px**
- [ ] All charts use `ResponsiveContainer` — no hardcoded pixel dimensions
- [ ] Axis labels use `font-variant-numeric: tabular-nums`
- [ ] Cross-chart highlighting: hover on sector highlights across all charts
- [ ] Respect `prefers-reduced-motion` — disable animations for sensitive users

### Reference Aesthetic
> **Bloomberg Terminal · Linear · Vercel Dashboard**
> Keywords: precision-focused · data-dense · clean · zero decorative noise
> Avoid: gradient buttons · glowing orbs · icon-in-colored-circle · centered-everything layouts

---

## ✅ Definition of Done

- [ ] 50 stocks selected with 12-month Polygon data
- [ ] Technical patterns detected on both Weekly + Daily timeframes
- [ ] Bullish/bearish targets + stop losses computed per stock
- [ ] Sentiment and confidence scores generated per stock
- [ ] Confusion Matrix #1 built with Precision / Recall / F1 / Accuracy
- [ ] Root cause documented for every misclassification
- [ ] Course correction applied — Matrix #2 shows measurable improvement
- [ ] Orchestrator collates Technical Agent + Fundamental Agent outputs
- [ ] Divergent signals flagged, Final Combined Score computed per stock
- [ ] Full 14-field report generated for all 50 stocks
- [ ] Top 10 Priority Setups highlighted in a dedicated section
- [ ] Next.js `/dashboard/stock-analysis` page live with all 7 sections
- [ ] Dashboard is dark-mode ready, responsive, and fully interactive
- [ ] All charts and tables are export-ready (CSV + PNG)
- [ ] Zero placeholder data — every value sourced from Polygon API

---

*End of Prompt Blueprint v1.0*