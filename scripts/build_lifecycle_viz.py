#!/usr/bin/env python3
"""
Build an interactive HTML visualization of benchmark lifecycle data.

Reads CSV outputs from analyze_safety_benchmarks.py and produces a standalone
HTML file with an interactive swimlane Gantt chart (D3.js).

Usage:
    python scripts/build_lifecycle_viz.py [--mode all_evals|safety]

Output:
    output/analysis/{mode}/benchmark_lifecycle_interactive.html
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Reuse constants from the analysis script
# ---------------------------------------------------------------------------
GEN_CHRONO_ORDER = {
    "claude-2": 1, "claude-3": 2, "claude-3.5": 3, "claude-3.5-haiku": 4,
    "claude-3.7": 5, "claude-4": 6, "claude-sonnet-4.5": 7, "claude-opus-4.5": 8,
    "claude-haiku-4.5": 9, "claude-opus-4.1": 10, "claude-sonnet-4.6": 11,
    "claude-opus-4.6": 12, "claude-mythos": 13,
    "gpt-4": 1, "gpt-4o": 2, "gpt-4.5": 3, "o1": 4, "o3-mini": 5,
    "o3": 6, "gpt-5": 7, "operator": 8, "gpt-5.1": 9, "gpt-5.2": 10,
    "gpt-5.3": 11,
    "gemini-1.0": 1, "gemini-1.5": 2, "gemini-2.0": 3, "gemini-2.5": 4,
    "gemini-2.5-pro": 5, "gemini-2.5-dt": 6, "gemini-3.0": 7,
    "gemini-3.0-pro": 8, "gemini-3.1-pro": 9,
    "llama-2": 1, "llama-3": 2, "llama-3.1": 3, "llama-3.1-card": 4,
    "llama-3.2": 5, "llama-3.3": 6, "llama-4": 7,
    "grok-4": 1, "grok-4-fast": 2, "grok-4.1": 3,
    "mistral-7b": 1, "mixtral-8x7b": 2, "codestral": 3,
    "mistral-large-2": 4, "mistral-small-3": 5,
    "command-r": 1, "command-a": 2,
    "jamba-1.5": 1,
    "nova": 1, "nova-premier": 2,
}

LAB_COLORS = {
    "claude":  "#D4791A",
    "gpt":     "#10A37F",
    "gemini":  "#4285F4",
    "llama":   "#0866FF",
    "grok":    "#1DA1F2",
    "mistral": "#FF7000",
    "command": "#39594D",
    "jamba":   "#6C3CE1",
    "nova":    "#FF9900",
}

LAB_NAMES = {
    "claude": "Anthropic (Claude)",
    "gpt": "OpenAI (GPT)",
    "gemini": "Google (Gemini)",
    "llama": "Meta (Llama)",
    "grok": "xAI (Grok)",
    "mistral": "Mistral",
    "command": "Cohere (Command)",
    "jamba": "AI21 (Jamba)",
    "nova": "Amazon (Nova)",
}

LIFECYCLE_COLORS = {
    "ACTIVE": "#2ecc71",
    "EMERGING": "#3498db",
    "SATURATED": "#95a5a6",
    "SUPERSEDED": "#f39c12",
    "CONTAMINATED": "#9b59b6",
    "FLAWED": "#e67e22",
    "FORMAT_AGED": "#1abc9c",
    "INTERNAL": "#7f8c8d",
    "CAP_SHIFT": "#2c3e50",
    "METRIC_CHANGE": "#d35400",
    "COST_PROHIBITIVE": "#8e44ad",
    "SUSPICIOUS": "#e74c3c",
    "ONE-TIME": "#bdc3c7",
}

LIFECYCLE_LABELS = {
    "ACTIVE": "Active",
    "EMERGING": "Emerging",
    "SATURATED": "Saturated",
    "SUPERSEDED": "Superseded",
    "CONTAMINATED": "Contaminated",
    "FLAWED": "Flawed",
    "FORMAT_AGED": "Format Aged",
    "INTERNAL": "Internal/Proprietary",
    "CAP_SHIFT": "Capability Shift",
    "METRIC_CHANGE": "Metric Change",
    "COST_PROHIBITIVE": "Cost Prohibitive",
    "SUSPICIOUS": "Suspicious Drop",
    "ONE-TIME": "One-Time",
}


def build_data(mode: str) -> dict:
    """Read CSVs and build the JSON data structure."""
    base = Path(__file__).parent.parent / "output" / "analysis" / mode

    lifecycle_path = base / "benchmark_lifecycle.csv"
    matrix_path = base / "coverage_matrix.csv"

    if not lifecycle_path.exists():
        print(f"ERROR: {lifecycle_path} not found. Run analyze_safety_benchmarks.py first.")
        sys.exit(1)

    lc_df = pd.read_csv(lifecycle_path)
    mat_df = pd.read_csv(matrix_path) if matrix_path.exists() else pd.DataFrame()

    # Build score lookup from coverage matrix
    score_lookup: dict[tuple[str, str, str], float] = {}
    if not mat_df.empty:
        scored = mat_df[mat_df["cell_value"].notna() & (mat_df["cell_value"] != ".")]
        for _, row in scored.iterrows():
            try:
                score = float(row["cell_value"])
                score_lookup[(row["family_slug"], row["gen_slug"], row["benchmark_slug"])] = score
            except (ValueError, TypeError):
                pass

    # Build per-lab data
    labs_data = []
    for lab in sorted(lc_df["family_slug"].unique()):
        lab_lc = lc_df[lc_df["family_slug"] == lab]

        # Get ordered generations for this lab
        lab_gens_set = set()
        if not mat_df.empty:
            lab_gens_set = set(mat_df[mat_df["family_slug"] == lab]["gen_slug"].unique())
        # Also include gens from lifecycle
        lab_gens_set.update(lab_lc["last_gen_reported"].dropna().unique())

        lab_gens = sorted(lab_gens_set, key=lambda g: GEN_CHRONO_ORDER.get(g, 999))

        # Build benchmark entries
        benchmarks = []
        for _, row in lab_lc.iterrows():
            slug = row["benchmark_slug"]

            # Find first and last generation with scores
            scores = {}
            first_gen_idx = len(lab_gens)
            last_gen_idx = -1
            for gi, gen in enumerate(lab_gens):
                s = score_lookup.get((lab, gen, slug))
                if s is not None:
                    scores[gen] = round(s, 2)
                    first_gen_idx = min(first_gen_idx, gi)
                    last_gen_idx = max(last_gen_idx, gi)

            # Fallback if no scores found in matrix
            if last_gen_idx < 0:
                last_gen = row.get("last_gen_reported")
                if pd.notna(last_gen) and last_gen in lab_gens:
                    last_gen_idx = lab_gens.index(last_gen)
                    first_gen_idx = last_gen_idx
                else:
                    continue

            benchmarks.append({
                "slug": slug,
                "name": str(row.get("benchmark_name", slug)),
                "lifecycle": row["lifecycle"],
                "dropReasons": str(row.get("drop_reasons", "")) if pd.notna(row.get("drop_reasons")) else "",
                "firstGenIdx": first_gen_idx,
                "lastGenIdx": last_gen_idx,
                "bestScore": round(row["best_score"], 2) if pd.notna(row.get("best_score")) else None,
                "dropScore": round(row["drop_score"], 2) if pd.notna(row.get("drop_score")) else None,
                "successor": str(row["successor"]) if pd.notna(row.get("successor")) else None,
                "isInternal": bool(row.get("is_internal", False)),
                "capabilityTags": str(row.get("capability_tags", "")) if pd.notna(row.get("capability_tags")) else "",
                "nGens": int(row.get("n_gens_reported", 1)),
                "scores": scores,
            })

        # Sort: by lifecycle priority, then first appearance, then name
        lifecycle_sort = {
            "ACTIVE": 0, "EMERGING": 1, "SATURATED": 2, "SUPERSEDED": 3,
            "CONTAMINATED": 4, "FLAWED": 5, "FORMAT_AGED": 6,
            "INTERNAL": 7, "CAP_SHIFT": 8, "METRIC_CHANGE": 9,
            "COST_PROHIBITIVE": 10, "SUSPICIOUS": 11, "ONE-TIME": 12,
        }
        benchmarks.sort(key=lambda b: (lifecycle_sort.get(b["lifecycle"], 99),
                                        b["firstGenIdx"], b["slug"]))

        labs_data.append({
            "slug": lab,
            "name": LAB_NAMES.get(lab, lab.title()),
            "color": LAB_COLORS.get(lab, "#888888"),
            "generations": lab_gens,
            "benchmarks": benchmarks,
        })

    return {
        "labs": labs_data,
        "lifecycleColors": LIFECYCLE_COLORS,
        "lifecycleLabels": LIFECYCLE_LABELS,
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Benchmark Lifecycle Explorer</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fafafa; color: #333; }

.layout { display: flex; height: 100vh; }
.sidebar { width: 260px; min-width: 260px; background: #fff; border-right: 1px solid #e0e0e0; padding: 16px; overflow-y: auto; }
.main { flex: 1; overflow-y: auto; padding: 20px 24px; }

h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.subtitle { font-size: 13px; color: #888; margin-bottom: 16px; }

/* Stats bar */
.stats-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.stat { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px 14px; font-size: 12px; }
.stat strong { font-size: 18px; display: block; }

/* Sidebar */
.sidebar h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #999; margin: 16px 0 8px; }
.sidebar h3:first-child { margin-top: 0; }
.search-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; margin-bottom: 12px; }
.search-input:focus { outline: none; border-color: #4285F4; }

.filter-group { margin-bottom: 8px; }
.filter-item { display: flex; align-items: center; gap: 6px; padding: 3px 0; cursor: pointer; font-size: 13px; }
.filter-item input { cursor: pointer; }
.color-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; flex-shrink: 0; }
.filter-count { color: #aaa; font-size: 11px; margin-left: auto; }

.quick-filters { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }
.qf-btn { padding: 5px 10px; font-size: 11px; border: 1px solid #ddd; border-radius: 4px; background: #fff; cursor: pointer; color: #555; transition: all 0.15s; }
.qf-btn:hover { background: #f0f0f0; }
.qf-btn.active { background: #333; color: #fff; border-color: #333; }

.sort-group { margin-bottom: 12px; }
.sort-group select { width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; background: #fff; }

/* Lab sections */
.lab-section { margin-bottom: 24px; }
.lab-header { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; user-select: none; margin-bottom: 2px; }
.lab-header:hover { background: #f5f5f5; }
.lab-color-bar { width: 4px; height: 24px; border-radius: 2px; }
.lab-name { font-weight: 600; font-size: 15px; }
.lab-count { color: #888; font-size: 13px; margin-left: auto; }
.lab-toggle { font-size: 12px; color: #aaa; transition: transform 0.2s; }
.lab-toggle.collapsed { transform: rotate(-90deg); }

.lab-body { overflow: hidden; transition: max-height 0.3s ease; }
.lab-body.collapsed { max-height: 0 !important; }

/* Gantt chart */
.gantt-container { position: relative; overflow-x: auto; background: #fff; border: 1px solid #e0e0e0; border-radius: 0 0 8px 8px; }
.gantt-header { display: flex; position: sticky; top: 0; background: #f9f9f9; border-bottom: 1px solid #eee; z-index: 2; }
.gantt-header-label { min-width: 200px; max-width: 200px; padding: 6px 10px; font-size: 11px; font-weight: 600; color: #666; }
.gen-header { flex: 1; text-align: center; font-size: 10px; color: #888; padding: 6px 2px; min-width: 70px; border-left: 1px solid #f0f0f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.gantt-row { display: flex; align-items: center; border-bottom: 1px solid #f5f5f5; min-height: 26px; }
.gantt-row:hover { background: #f8f9ff; }
.gantt-label { min-width: 200px; max-width: 200px; padding: 2px 10px; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #555; }
.gantt-bars { display: flex; flex: 1; position: relative; }
.gantt-cell { flex: 1; min-width: 70px; height: 22px; border-left: 1px solid #f8f8f8; position: relative; display: flex; align-items: center; justify-content: center; }
.bar-segment { height: 14px; border-radius: 3px; position: absolute; top: 4px; cursor: pointer; transition: opacity 0.15s; min-width: 8px; }
.bar-segment:hover { opacity: 0.8; filter: brightness(1.1); }

/* Score dot inside bar */
.score-dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.7); position: absolute; top: 50%; transform: translateY(-50%); }

/* Drop marker */
.drop-marker { position: absolute; right: -4px; top: -2px; font-size: 12px; line-height: 1; }

/* Tooltip */
.tooltip { position: fixed; background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 12px 16px; font-size: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); z-index: 1000; max-width: 380px; pointer-events: none; display: none; }
.tooltip-name { font-weight: 700; font-size: 14px; margin-bottom: 4px; }
.tooltip-lifecycle { display: inline-block; padding: 2px 8px; border-radius: 3px; color: #fff; font-size: 11px; font-weight: 600; margin-bottom: 8px; }
.tooltip-row { display: flex; justify-content: space-between; gap: 16px; padding: 2px 0; }
.tooltip-row .label { color: #888; }
.tooltip-scores { margin-top: 8px; border-top: 1px solid #eee; padding-top: 8px; }
.tooltip-scores h4 { font-size: 11px; color: #888; margin-bottom: 4px; }
.score-list { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 12px; }
.score-entry { font-size: 11px; }
.score-entry .gen { color: #888; }
.score-entry .val { font-weight: 600; }

/* No results */
.no-results { padding: 40px; text-align: center; color: #aaa; font-size: 14px; }
</style>
</head>
<body>

<div class="layout">
  <aside class="sidebar">
    <h1>Benchmark Lifecycle</h1>
    <div class="subtitle">Interactive swimlane explorer</div>

    <input type="text" class="search-input" id="searchInput" placeholder="Search benchmarks...">

    <h3>Sort by</h3>
    <div class="sort-group">
      <select id="sortSelect">
        <option value="lifecycle">Lifecycle status</option>
        <option value="appearance">First appearance</option>
        <option value="name">Name (A-Z)</option>
        <option value="ngens">Longevity (most → least)</option>
      </select>
    </div>

    <h3>Quick Filters</h3>
    <div class="quick-filters">
      <button class="qf-btn active" id="qfSignal">Signal only</button>
      <button class="qf-btn" id="qfAll">Show all</button>
      <button class="qf-btn" id="qfDrops">Drops only</button>
      <button class="qf-btn" id="qfSuspicious">Suspicious only</button>
    </div>

    <h3>Lifecycle Status</h3>
    <div id="lifecycleFilters" class="filter-group"></div>

    <h3>Labs</h3>
    <div id="labFilters" class="filter-group"></div>
  </aside>

  <div class="main">
    <div class="stats-bar" id="statsBar"></div>
    <div id="chartArea"></div>
  </div>
</div>

<div class="tooltip" id="tooltip"></div>

<script>
// === DATA (embedded by Python) ===
const DATA = __DATA_PLACEHOLDER__;

// === STATE ===
// Default: hide ONE-TIME and INTERNAL (the long tail) so you start with signal
const DEFAULT_HIDDEN = new Set(['ONE-TIME', 'INTERNAL']);
const state = {
  lifecycleFilters: new Set(Object.keys(DATA.lifecycleColors).filter(s => !DEFAULT_HIDDEN.has(s))),
  labFilters: new Set(DATA.labs.map(l => l.slug)),
  search: '',
  sort: 'lifecycle',
  collapsed: new Set(),
};

// === LIFECYCLE SORT ORDER ===
const LIFECYCLE_ORDER = [
  'ACTIVE','EMERGING','SATURATED','SUPERSEDED','CONTAMINATED','FLAWED',
  'FORMAT_AGED','INTERNAL','CAP_SHIFT','METRIC_CHANGE','COST_PROHIBITIVE',
  'SUSPICIOUS','ONE-TIME'
];

// === RENDER ===
function getFilteredBenchmarks(lab) {
  let benchmarks = lab.benchmarks.filter(b => {
    if (!state.lifecycleFilters.has(b.lifecycle)) return false;
    if (state.search) {
      const q = state.search.toLowerCase();
      if (!b.slug.includes(q) && !b.name.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  // Sort
  const sortFn = {
    lifecycle: (a, b) => {
      const ai = LIFECYCLE_ORDER.indexOf(a.lifecycle);
      const bi = LIFECYCLE_ORDER.indexOf(b.lifecycle);
      if (ai !== bi) return ai - bi;
      return a.firstGenIdx - b.firstGenIdx || a.slug.localeCompare(b.slug);
    },
    appearance: (a, b) => a.firstGenIdx - b.firstGenIdx || a.slug.localeCompare(b.slug),
    name: (a, b) => a.name.localeCompare(b.name),
    ngens: (a, b) => b.nGens - a.nGens || a.slug.localeCompare(b.slug),
  };
  benchmarks.sort(sortFn[state.sort] || sortFn.lifecycle);
  return benchmarks;
}

function renderStats() {
  const bar = document.getElementById('statsBar');
  let total = 0;
  const counts = {};
  LIFECYCLE_ORDER.forEach(s => counts[s] = 0);

  DATA.labs.forEach(lab => {
    if (!state.labFilters.has(lab.slug)) return;
    lab.benchmarks.forEach(b => {
      if (state.search) {
        const q = state.search.toLowerCase();
        if (!b.slug.includes(q) && !b.name.toLowerCase().includes(q)) return;
      }
      counts[b.lifecycle] = (counts[b.lifecycle] || 0) + 1;
      total++;
    });
  });

  let html = `<div class="stat"><strong>${total}</strong>total benchmarks</div>`;
  LIFECYCLE_ORDER.forEach(s => {
    if (counts[s] > 0) {
      const color = DATA.lifecycleColors[s];
      const label = DATA.lifecycleLabels[s] || s;
      html += `<div class="stat"><strong style="color:${color}">${counts[s]}</strong>${label}</div>`;
    }
  });
  bar.innerHTML = html;
}

function renderSidebar() {
  // Lifecycle filters
  const lcDiv = document.getElementById('lifecycleFilters');
  let lcHtml = '';
  const lcCounts = {};
  DATA.labs.forEach(lab => {
    lab.benchmarks.forEach(b => {
      lcCounts[b.lifecycle] = (lcCounts[b.lifecycle] || 0) + 1;
    });
  });
  LIFECYCLE_ORDER.forEach(s => {
    const color = DATA.lifecycleColors[s];
    const label = DATA.lifecycleLabels[s] || s;
    const count = lcCounts[s] || 0;
    if (count === 0) return;
    const checked = state.lifecycleFilters.has(s) ? 'checked' : '';
    lcHtml += `<label class="filter-item">
      <input type="checkbox" ${checked} data-lifecycle="${s}">
      <span class="color-dot" style="background:${color}"></span>
      ${label}
      <span class="filter-count">${count}</span>
    </label>`;
  });
  lcDiv.innerHTML = lcHtml;
  lcDiv.querySelectorAll('input').forEach(cb => {
    cb.addEventListener('change', () => {
      const s = cb.dataset.lifecycle;
      if (cb.checked) state.lifecycleFilters.add(s);
      else state.lifecycleFilters.delete(s);
      document.querySelectorAll('.qf-btn').forEach(b => b.classList.remove('active'));
      renderChart();
      renderStats();
    });
  });

  // Lab filters
  const labDiv = document.getElementById('labFilters');
  let labHtml = '';
  DATA.labs.forEach(lab => {
    const checked = state.labFilters.has(lab.slug) ? 'checked' : '';
    labHtml += `<label class="filter-item">
      <input type="checkbox" ${checked} data-lab="${lab.slug}">
      <span class="color-dot" style="background:${lab.color}"></span>
      ${lab.name}
      <span class="filter-count">${lab.benchmarks.length}</span>
    </label>`;
  });
  labDiv.innerHTML = labHtml;
  labDiv.querySelectorAll('input').forEach(cb => {
    cb.addEventListener('change', () => {
      const s = cb.dataset.lab;
      if (cb.checked) state.labFilters.add(s);
      else state.labFilters.delete(s);
      renderChart();
      renderStats();
    });
  });
}

function renderChart() {
  const area = document.getElementById('chartArea');
  let html = '';

  const visibleLabs = DATA.labs.filter(l => state.labFilters.has(l.slug));
  if (visibleLabs.length === 0) {
    area.innerHTML = '<div class="no-results">No labs selected</div>';
    return;
  }

  visibleLabs.forEach(lab => {
    const benchmarks = getFilteredBenchmarks(lab);
    const isCollapsed = state.collapsed.has(lab.slug);
    const gens = lab.generations;

    html += `<div class="lab-section" data-lab="${lab.slug}">`;
    html += `<div class="lab-header" data-lab="${lab.slug}">
      <div class="lab-color-bar" style="background:${lab.color}"></div>
      <span class="lab-name">${lab.name}</span>
      <span class="lab-count">${benchmarks.length} benchmarks</span>
      <span class="lab-toggle ${isCollapsed ? 'collapsed' : ''}">▼</span>
    </div>`;

    html += `<div class="lab-body ${isCollapsed ? 'collapsed' : ''}" style="max-height:${isCollapsed ? 0 : (benchmarks.length + 1) * 28 + 40}px">`;
    html += `<div class="gantt-container">`;

    // Header row
    html += `<div class="gantt-header">`;
    html += `<div class="gantt-header-label">Benchmark</div>`;
    gens.forEach(g => {
      html += `<div class="gen-header" title="${g}">${g}</div>`;
    });
    html += `</div>`;

    if (benchmarks.length === 0) {
      html += '<div class="no-results">No matching benchmarks</div>';
    }

    // Benchmark rows
    benchmarks.forEach(b => {
      html += `<div class="gantt-row">`;
      html += `<div class="gantt-label" title="${b.name}">${b.name}</div>`;
      html += `<div class="gantt-bars">`;

      gens.forEach((g, gi) => {
        html += `<div class="gantt-cell">`;
        if (gi >= b.firstGenIdx && gi <= b.lastGenIdx) {
          const color = DATA.lifecycleColors[b.lifecycle] || '#ccc';
          const isFirst = gi === b.firstGenIdx;
          const isLast = gi === b.lastGenIdx;
          const score = b.scores[g];
          const borderRadius = `${isFirst ? '3px' : '0'} ${isLast ? '3px' : '0'} ${isLast ? '3px' : '0'} ${isFirst ? '3px' : '0'}`;

          html += `<div class="bar-segment"
            style="background:${color}; left:0; right:0; border-radius:${borderRadius}"
            data-bench='${JSON.stringify(b).replace(/'/g, "&#39;")}'
            data-gen="${g}"
            data-score="${score != null ? score : ''}">`;

          // Score dot
          if (score != null) {
            html += `<div class="score-dot" style="left:50%"></div>`;
          }

          // Drop marker for terminated benchmarks
          if (isLast && b.lifecycle !== 'ACTIVE' && b.lifecycle !== 'EMERGING') {
            const markers = {
              'SATURATED': '⬆', 'SUPERSEDED': '→', 'CONTAMINATED': '☣',
              'SUSPICIOUS': '?', 'INTERNAL': '🔒', 'CAP_SHIFT': '↗',
              'METRIC_CHANGE': '📐', 'COST_PROHIBITIVE': '💰', 'FLAWED': '⚠',
              'ONE-TIME': '·',
            };
            const marker = markers[b.lifecycle] || '';
            if (marker && b.lifecycle !== 'ONE-TIME') {
              html += `<span class="drop-marker">${marker}</span>`;
            }
          }

          html += `</div>`;
        }
        html += `</div>`;
      });

      html += `</div></div>`;
    });

    html += `</div></div></div>`;
  });

  area.innerHTML = html;

  // Attach event listeners
  area.querySelectorAll('.lab-header').forEach(el => {
    el.addEventListener('click', () => {
      const lab = el.dataset.lab;
      const body = el.nextElementSibling;
      const toggle = el.querySelector('.lab-toggle');
      if (state.collapsed.has(lab)) {
        state.collapsed.delete(lab);
        body.classList.remove('collapsed');
        const benchmarks = getFilteredBenchmarks(DATA.labs.find(l => l.slug === lab));
        body.style.maxHeight = ((benchmarks.length + 1) * 28 + 40) + 'px';
        toggle.classList.remove('collapsed');
      } else {
        state.collapsed.add(lab);
        body.classList.add('collapsed');
        toggle.classList.add('collapsed');
      }
    });
  });

  // Tooltip
  const tooltip = document.getElementById('tooltip');
  area.querySelectorAll('.bar-segment').forEach(el => {
    el.addEventListener('mouseenter', (e) => {
      const b = JSON.parse(el.dataset.bench);
      const gen = el.dataset.gen;
      const color = DATA.lifecycleColors[b.lifecycle] || '#ccc';
      const label = DATA.lifecycleLabels[b.lifecycle] || b.lifecycle;

      let html = `<div class="tooltip-name">${b.name}</div>`;
      html += `<div class="tooltip-lifecycle" style="background:${color}">${label}</div>`;

      if (b.dropReasons) {
        html += `<div class="tooltip-row"><span class="label">Drop reasons:</span><span>${b.dropReasons}</span></div>`;
      }
      if (b.bestScore != null) {
        html += `<div class="tooltip-row"><span class="label">Best score:</span><span>${b.bestScore}</span></div>`;
      }
      if (b.dropScore != null) {
        html += `<div class="tooltip-row"><span class="label">Score at drop:</span><span>${b.dropScore}</span></div>`;
      }
      if (b.successor) {
        html += `<div class="tooltip-row"><span class="label">Successor:</span><span>${b.successor}</span></div>`;
      }
      if (b.capabilityTags) {
        html += `<div class="tooltip-row"><span class="label">Capability:</span><span>${b.capabilityTags}</span></div>`;
      }
      html += `<div class="tooltip-row"><span class="label">Generations:</span><span>${b.nGens}</span></div>`;

      // Score trajectory
      const scoreEntries = Object.entries(b.scores);
      if (scoreEntries.length > 0) {
        html += `<div class="tooltip-scores"><h4>Score trajectory</h4><div class="score-list">`;
        scoreEntries.forEach(([g, s]) => {
          const highlight = g === gen ? 'font-weight:700;color:#333' : '';
          html += `<div class="score-entry" style="${highlight}"><span class="gen">${g}:</span> <span class="val">${s}</span></div>`;
        });
        html += `</div></div>`;
      }

      tooltip.innerHTML = html;
      tooltip.style.display = 'block';

      // Position
      const rect = el.getBoundingClientRect();
      let left = rect.right + 12;
      let top = rect.top - 10;
      if (left + 380 > window.innerWidth) left = rect.left - 392;
      if (top + tooltip.offsetHeight > window.innerHeight) top = window.innerHeight - tooltip.offsetHeight - 10;
      if (top < 10) top = 10;
      tooltip.style.left = left + 'px';
      tooltip.style.top = top + 'px';
    });

    el.addEventListener('mouseleave', () => {
      tooltip.style.display = 'none';
    });
  });
}

// === INIT ===
document.getElementById('searchInput').addEventListener('input', (e) => {
  state.search = e.target.value.trim();
  renderChart();
  renderStats();
});

document.getElementById('sortSelect').addEventListener('change', (e) => {
  state.sort = e.target.value;
  renderChart();
});

// Quick filter presets
const PRESETS = {
  signal: new Set(LIFECYCLE_ORDER.filter(s => !DEFAULT_HIDDEN.has(s))),
  all: new Set(LIFECYCLE_ORDER),
  drops: new Set(['SATURATED','SUPERSEDED','CONTAMINATED','FLAWED','FORMAT_AGED','CAP_SHIFT','METRIC_CHANGE','COST_PROHIBITIVE','SUSPICIOUS']),
  suspicious: new Set(['SUSPICIOUS']),
};

function applyPreset(name) {
  state.lifecycleFilters = new Set(PRESETS[name]);
  document.querySelectorAll('.qf-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('qf' + name.charAt(0).toUpperCase() + name.slice(1)).classList.add('active');
  renderSidebar();
  renderStats();
  renderChart();
}

document.getElementById('qfSignal').addEventListener('click', () => applyPreset('signal'));
document.getElementById('qfAll').addEventListener('click', () => applyPreset('all'));
document.getElementById('qfDrops').addEventListener('click', () => applyPreset('drops'));
document.getElementById('qfSuspicious').addEventListener('click', () => applyPreset('suspicious'));

renderSidebar();
renderStats();
renderChart();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Build interactive benchmark lifecycle visualization")
    parser.add_argument("--mode", choices=["all_evals", "safety"], default="all_evals",
                        help="Which analysis output to visualize")
    args = parser.parse_args()

    print(f"Building interactive visualization for {args.mode}...")
    data = build_data(args.mode)

    total_benchmarks = sum(len(lab["benchmarks"]) for lab in data["labs"])
    print(f"  {len(data['labs'])} labs, {total_benchmarks} benchmark entries")

    # Embed data into HTML
    data_json = json.dumps(data, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", data_json)

    out_dir = Path(__file__).parent.parent / "output" / "analysis" / args.mode
    out_path = out_dir / "benchmark_lifecycle_interactive.html"
    out_path.write_text(html, encoding="utf-8")

    print(f"  Written: {out_path}")
    print(f"  Size: {out_path.stat().st_size / 1024:.0f} KB")
    print(f"\n  Open in browser: file:///{out_path.resolve().as_posix()}")


if __name__ == "__main__":
    main()
