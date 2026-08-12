/**
 * Cascadia ECharts theme — implements VIZ-PRINCIPLES.md v2.3 as defaults.
 * v2.3 · August 2026 · Aaron Robbins · Robbins Analytics
 *
 * Usage:
 *   <script src="echarts.min.js"></script>
 *   <script src="cascadia-echarts-theme.js"></script>
 *   const chart = echarts.init(el, 'cascadia');
 *
 * Helpers:
 *   cascadiaTitle(finding, subtitle)                  → Rule 3.1 title block
 *   cascadiaProvenance(el, {source, asOf, flags, view}) → Rule 4.2 / 4.4 strip (idempotent)
 *   cascadiaAnnotation(text, {color, coord, position}) → Rule 3.3 / 3.4 colour-matched annotation
 *   cascadiaBankedHeight(values, width)               → Rule 1.3 banking to 45 degrees
 *   cascadiaAccessible(el, {summary, tableId, label}) → Rule 5.1 / 5.2 access layers
 *   cascadiaNavigator(el, {chart, label, series, onFocus}) → Rule 5.1 layer 3, keyboard
 *   cascadiaResize(el, chart)                         → keep a chart sized to its container
 *   cascadiaMotion()                                  → Rule 5.6 reduced-motion state
 *
 * Reference data:
 *   CASCADIA.colors · .palette · .smallMarkPalette · .seq · .diverging
 *   CASCADIA.textInk · .textInkFor(hex)               → Rule 2.3.7, hues at text contrast
 *   CASCADIA.maxCategories · .minTextPx · .minCanvasPx · .encodingRank
 *
 * WHAT A THEME CANNOT ENFORCE. This file sets rendering defaults only. The
 * selection layer (Rules 1.1-1.4), the explanation layer (3.2 title-data
 * alignment, 3.4 annotation presence, 3.5 arrangement) and the whole access
 * layer live in CHART-REVIEW.md, not here. Passing this theme is necessary
 * and nowhere near sufficient.
 */
(function (root) {
  'use strict';

  var C = {
    evergreen: '#1E7A4C',
    glacier:   '#4C8BC0',
    madrona:   '#C05A2E',
    lupine:    '#7B68AE',
    lichen:    '#9C7A20',
    rain:      '#9AA6A0',
    basalt:    '#232B27',
    slateMoss: '#5B6660',
    mist:      '#E4E7E3',
    paper:     '#FCFCFA'
  };

  // Rule 2.3.7 — text inks. A palette hue used as TEXT meets 4.5:1, not the
  // 3:1 that governs the mark. Three of the five hues do not clear 4.5:1 on
  // Paper, so each is darkened along its own hue by the least amount that
  // does. The mark keeps the full palette value; only the text darkens, so
  // series identity survives. Computed, not picked.
  //
  //   Evergreen 5.18 and Lupine 4.61 already clear and are unchanged.
  //   Madrona 4.31 -> 4.55 · Lichen 3.92 -> 4.52 · Glacier 3.55 -> 4.52
  //
  // These are here so that no module re-derives them. Use them for direct
  // labels, end-of-series labels, data labels and annotation prose. Do NOT
  // use them for the mark.
  var INK = {
    evergreen: C.evergreen,
    glacier:   '#4279A7',
    madrona:   '#BA572D',
    lupine:    C.lupine,
    lichen:    '#90701D'
  };

  /** Rule 2.3.7 — the text ink for a palette hex, or the hex unchanged. */
  function textInkFor(hex) {
    if (!hex) return hex;
    var h = String(hex).toLowerCase();
    for (var name in C) {
      if (Object.prototype.hasOwnProperty.call(C, name) &&
          String(C[name]).toLowerCase() === h &&
          Object.prototype.hasOwnProperty.call(INK, name)) return INK[name];
    }
    return hex;
  }

  var SERIF = '"Source Serif 4", Georgia, "Times New Roman", serif';
  var SANS  = '"Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif';

  // Rule 5.3 / WCAG 1.4.10 — the narrowest canvas the system supports is
  // 320 CSS px. Any helper that sizes a text box sizes it for this width
  // unless the caller supplies a real container to measure.
  var MIN_CANVAS = 320;

  /** Shallow copy plus overrides. The file is ES5 by choice; this is Object.assign. */
  function extend(base, over) {
    var out = {}, k;
    for (k in base) if (Object.prototype.hasOwnProperty.call(base, k)) out[k] = base[k];
    for (k in over) if (Object.prototype.hasOwnProperty.call(over, k)) out[k] = over[k];
    return out;
  }

  /** Resolve a container to a pixel width. Accepts a number, an id, or an element. */
  function canvasWidth(container) {
    if (typeof container === 'number' && isFinite(container) && container > 0) return container;
    var el = (typeof container === 'string') ? document.getElementById(container) : container;
    var w = el && (el.clientWidth || (el.getBoundingClientRect && el.getBoundingClientRect().width));
    return (w && w > 0) ? w : MIN_CANVAS;
  }

  // Rule 5.3 / Chartability: no text anywhere in a chart below 12px (9pt).
  // This is why axis labels and the provenance strip are 12px in v2 where
  // they were 11px and 10.5px in v1.0. The rule is INVARIANT; the slightly
  // heavier strip is the price.
  var MIN_TEXT = 12;

  /** Rule 5.6 — true when the reader has asked for reduced motion. */
  function reducedMotion() {
    return typeof root.matchMedia === 'function' &&
           root.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  var RM = reducedMotion();

  var theme = {
    // Rule 2.3.1: fixed slot order, never cycled, never re-dealt on filter.
    // Rule 2.3.5 caps a single chart at FOUR of these; the fifth exists so a
    // family of charts can carry five entities. See CASCADIA.maxCategories.
    color: [C.evergreen, C.glacier, C.madrona, C.lupine, C.lichen],

    backgroundColor: C.paper,

    textStyle: { fontFamily: SANS, color: C.basalt, fontSize: MIN_TEXT },

    // Rule 6.3: transitions run 250ms-2s and are suppressed under reduced motion.
    animation: !RM,
    animationDuration: RM ? 0 : 400,
    animationDurationUpdate: RM ? 0 : 500,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',

    // Rule 5.1: a floor, not a solution. ECharts' aria is one generated label
    // and no keyboard support (apache/echarts#18585). The real access layer is
    // DOM-side — see cascadiaAccessible().
    //
    // decal is DELIBERATELY OFF. It is a genuine second non-colour channel for
    // Rule 2.3.2, but it renders as visible hatching and checkerboard across
    // every categorical series, which reads as texture decoration under Rule
    // 2.5 and makes de-emphasised Rain series look like loading placeholders.
    // Rule 3.6 already requires a direct label on every series, and a label is
    // the stronger non-colour channel. Turn decal on per chart — via
    // `aria: { decal: { show: true } }` in setOption — for the case it is
    // actually built for: a categorical chart where direct labels genuinely
    // will not fit and a legend is unavoidable.
    aria: { enabled: true, decal: { show: false } },

    // Rule 3.1: serif finding + sans subtitle in secondary ink, positioned top.
    title: {
      textStyle:    { fontFamily: SERIF, fontSize: 17, fontWeight: 600, color: C.basalt },
      subtextStyle: { fontFamily: SANS,  fontSize: MIN_TEXT, color: C.slateMoss },
      left: 0, top: 0, itemGap: 6
    },

    // Right padding reserves room for end-of-line direct labels (Rule 3.6).
    grid: { left: 8, right: 90, top: 64, bottom: 30, containLabel: true },

    // Rule 3.6: legends off by default — direct-label instead.
    legend: { show: false },

    categoryAxis: {
      axisLine:  { show: true, lineStyle: { color: C.mist, width: 1 } },
      axisTick:  { show: false },
      axisLabel: { color: C.slateMoss, fontSize: MIN_TEXT, fontFamily: SANS, rotate: 0 }, // Rule 2.8
      splitLine: { show: false }
    },

    // Rule 2.4: no gridlines unless earned by scanning behaviour. Opt back in
    // per chart. NOTE the v2 trigger change: v1.0 said "no tooltip available",
    // which permanently suppressed gridlines on interactive pages. The trigger
    // is now whether the reader decodes off the axis while scanning.
    valueAxis: {
      axisLine:  { show: false },
      axisTick:  { show: false },
      axisLabel: { color: C.slateMoss, fontSize: MIN_TEXT, fontFamily: SANS },
      splitLine: { show: false },
      splitNumber: 4
    },
    logAxis:  { splitLine: { show: false } },
    timeAxis: {
      axisLine:  { show: true, lineStyle: { color: C.mist } },
      axisTick:  { show: false },
      axisLabel: { color: C.slateMoss, fontSize: MIN_TEXT, fontFamily: SANS },
      splitLine: { show: false }
    },

    // Rule 2.5: flat marks. 2px lines, no shadows, square bar caps.
    line: {
      itemStyle: { borderWidth: 0 },
      lineStyle: { width: 2 },
      symbol: 'circle', symbolSize: 1, showSymbol: false,
      smooth: false,                    // honest geometry — no beziers
      emphasis: { lineStyle: { width: 2.5 } }
    },
    bar: {
      // borderRadius 0 is Rule 2.5. The 1px Paper border is Chartability's
      // adjacent-mark separation (Rule 5.3) and matters most on stacked bars.
      itemStyle: { borderRadius: 0, borderColor: C.paper, borderWidth: 1 },
      barMaxWidth: 42
    },
    scatter: { symbolSize: 9 },

    // Rule 2.6 — REVERSED IN v2. A plain, unexploded, two-dimensional pie or
    // donut is now permitted where the sole task is reading a single share of
    // a whole. Angle is the least important cue in a pie (Skau & Kosara 2016);
    // area is primary (Kosara 2019); no significant difference against stacked
    // bars (Bailey & Gleicher 2025). Sorted bars remain the DEFAULT for ranking
    // and multi-category comparison, which is what most business reporting is.
    // Exploded, elliptical, 3D and square pies remain banned outright.
    pie: {
      itemStyle: { borderColor: C.paper, borderWidth: 1, borderRadius: 0 },
      label: { show: true, fontFamily: SANS, fontSize: MIN_TEXT, color: C.basalt },
      labelLine: { lineStyle: { color: C.mist } },
      avoidLabelOverlap: true,
      startAngle: 90,
      selectedOffset: 0                 // never explode
    },

    // Rule 2.5: gauges and speedometers are banned. Left present and unstyled
    // so accidental use is conspicuous in review.
    gauge: {},

    // Rule 2.9: full precision lives here; visible labels stay rounded.
    tooltip: {
      backgroundColor: '#FFFFFF',
      borderColor: C.mist, borderWidth: 1,
      textStyle: { color: C.basalt, fontFamily: SANS, fontSize: MIN_TEXT },
      axisPointer: {
        lineStyle: { color: C.rain, width: 1 },
        crossStyle: { color: C.rain, width: 1 }
      },
      extraCssText: 'box-shadow: none; border-radius: 2px; padding: 8px 10px;'
    }
  };

  // ---- helpers ---------------------------------------------------------

  /**
   * Rule 3.1 title block: finding sentence + metric subtitle, at the top.
   *
   * WRAPS, NEVER CLIPS. ECharts truncates an over-long title silently and
   * with no warning anywhere — two charts shipped reading "…arithmetically
   * corre" and "…one cause, two sympto". A title is a complete sentence
   * stating the takeaway (Rule 3.1) and half a sentence is not a shorter
   * title, it is a different claim. So the width is always set and overflow
   * is always 'break'.
   *
   * Pass `opts.container` (element, id or px) to wrap to the real plot
   * width. With no container the title wraps to the narrowest supported
   * canvas, which is conservative: it wraps earlier than it needs to on a
   * wide screen and never clips on a narrow one. Wrapping early costs a line
   * of height; clipping costs the sentence.
   */
  function cascadiaTitle(finding, subtitle, opts) {
    opts = opts || {};
    var width = opts.width || canvasWidth(opts.container);
    var titleStyle = extend(theme.title.textStyle,
      { width: width, overflow: 'break', lineHeight: 26 });
    var subStyle = extend(theme.title.subtextStyle,
      { width: width, overflow: 'break' });
    return {
      text: finding,
      subtext: subtitle || '',
      textStyle:    titleStyle,
      subtextStyle: subStyle,
      left: 0, top: 0, itemGap: 6
    };
  }

  // The strip's segment separator. This helper JOINS on it, so a separator
  // arriving inside segment content would silently split one segment into
  // two and the rendered strip would carry more segments than it declares.
  // Rule 4.2 fixes the strip's anatomy, so a strip with the wrong number of
  // parts is an INVARIANT failure that nothing in the config would show you.
  var SEP = ' · ';

  /**
   * Escape the separator out of segment content and say so in the console.
   *
   * Escaped rather than rejected: a source genuinely named with a middle dot
   * is not the author's mistake and dropping the segment would lose the
   * provenance, which is worse than showing it with a different glyph. The
   * warning is there because the substitution is visible in the render and
   * an author who did not intend it should be told once.
   */
  function safeSegment(value, field) {
    var s = String(value == null ? '' : value);
    if (s.indexOf('·') === -1) return s;
    if (root.console && root.console.warn) {
      root.console.warn('[cascadia] Rule 4.2: "' + field + '" contains the strip ' +
        'separator and was escaped. The rendered strip must carry its declared ' +
        'segment count (check K5).');
    }
    return s.replace(/·/g, '∙');
  }

  /**
   * Rule 4.2 provenance strip, plus Rule 4.4's fourth segment.
   *
   * IDEMPOTENT (Rule 6.7). v1.0 appended with insertAdjacentElement on every
   * call, so an interactive chart that re-rendered on filter change grew a
   * second strip, then a third. This version replaces any existing strip for
   * the same host.
   *
   * `source` and `asOf` describe the DATASET and must not change when a
   * control changes. `view` describes the reader's filter state and belongs
   * in the fourth segment — never in place of the source.
   */
  function cascadiaProvenance(el, opts) {
    var host = (typeof el === 'string') ? document.getElementById(el) : el;
    if (!host) return null;
    opts = opts || {};

    // Idempotency by OWNER, not by adjacency. Checking nextElementSibling was
    // wrong the moment anything else could be inserted after the chart — the
    // keyboard navigator (cascadiaNavigator) does exactly that, which pushed
    // the strip out of the sibling slot and made every re-render append a new
    // one. Rule 6.7 is INVARIANT and that failure is invisible until a reader
    // changes a filter, so the guard now finds the strip wherever it sits.
    var owner = host.id || (host.dataset.cascadiaOwner ||
      (host.dataset.cascadiaOwner = 'c' + Math.abs(
        (host.className + host.tagName).split('').reduce(function (a, ch) {
          return ((a << 5) - a + ch.charCodeAt(0)) | 0; }, 0))));
    var scope = host.parentNode || document;
    Array.prototype.forEach.call(
      scope.querySelectorAll('.cascadia-provenance[data-cascadia-prov="' + owner + '"]'),
      function (n) { n.parentNode.removeChild(n); });

    var strip = document.createElement('div');
    strip.className = 'cascadia-provenance';
    strip.setAttribute('data-cascadia-prov', owner);
    strip.setAttribute('role', 'note');
    strip.style.cssText =
      'display:flex;align-items:baseline;gap:7px;margin:2px 0 0 2px;' +
      'font:' + MIN_TEXT + 'px/1.5 ' + SANS + ';color:' + C.slateMoss + ';';

    var tick = document.createElement('span');
    tick.style.cssText =
      'display:inline-block;width:3px;height:' + (MIN_TEXT - 1) + 'px;background:' +
      C.evergreen + ';flex:0 0 3px;position:relative;top:1px;';

    var parts = [
      opts.source ? 'Source: ' + safeSegment(opts.source, 'source') : null,
      opts.asOf   ? 'as of ' + safeSegment(opts.asOf, 'asOf')       : null,
      safeSegment(opts.flags || 'no adjustments', 'flags')
    ];
    // Rule 4.4 — on an interactive artifact the strip reports the view too.
    // Pass view: 'unfiltered' explicitly rather than omitting it, so a
    // screenshotted filtered view can never carry a strip that describes the
    // full dataset.
    if (opts.view) parts.push(safeSegment(opts.view, 'view'));

    var text = document.createElement('span');
    text.textContent = parts.filter(Boolean).join(SEP);

    strip.appendChild(tick);
    strip.appendChild(text);
    // Keep reading order stable: chart, then navigator, then provenance —
    // whichever helper happened to run first.
    var nav = scope.querySelector('.cascadia-nav[data-cascadia-nav="' + owner + '"]');
    (nav || host).insertAdjacentElement('afterend', strip);
    return strip;
  }

  /**
   * Rules 3.3 / 3.4 — an annotation at the data, colour-matched to the series
   * it explains.
   *
   * The colour match is not decoration. Ajani et al. (TVCG 2022) measured the
   * focus treatment as three parts — highlight, sentence at the data, and the
   * annotation text matched to the highlight — producing 2.5-3x higher recall
   * of the intended conclusion. v1.0 implemented only the highlight.
   *
   * PLACE IT BESIDE THE MARK, NEVER OVER IT. The label below paints a paper
   * text-outline around its glyphs so it stays legible against a busy plot,
   * and that outline is opaque: it erases whatever sits beneath it. A label
   * dropped on top of a bar leaves a pale stub through the bar that reads as
   * a value the data does not contain. The helper cannot detect this — it is
   * handed a coordinate and draws where it is told — so the caller owns it.
   * Where a plot has no free space beside the mark, extend the value axis to
   * make headroom rather than printing over the data.
   *
   * This helper has now made the same class of mistake twice. A filled anchor
   * dot was removed because two naive readers read it as a datum; the outline
   * that replaced the need for a filled box does the same thing in reverse,
   * by removing marks instead of adding one. Anything this helper paints
   * inside the plot area is a potential false reading.
   *
   * WIDTH IS CAPPED, not taken on trust. The label centres on a data
   * coordinate, so a box wider than the plot overhangs it and ECharts clips
   * the overhang without warning — at 390 px one shipped annotation lost two
   * characters and read "e gap is the fill splitting buys". Pass
   * `opts.container` (element, id or px) to cap against the real plot width;
   * with no container the cap is computed from the narrowest supported
   * canvas.
   *
   * Returns a markPoint config. Keep the text under ~14 words.
   */
  function cascadiaAnnotation(text, opts) {
    opts = opts || {};

    // Half the canvas, because the label is centred on its coordinate and the
    // coordinate can sit anywhere along the axis. Floored at 96px: below that
    // a 14-word annotation wraps to a column and stops being readable, and
    // the right answer at that width is to move the annotation out of the
    // plot (Rule 5.5's drop order, step 4) rather than to shrink it further.
    var cap = Math.max(96, Math.round(canvasWidth(opts.container) * 0.5));
    var width = Math.min(opts.width || 180, cap);

    return {
      // No visible anchor. A filled dot in the series colour reads as a data
      // point — two independent naive readers mistook it for one. Rule 3.4
      // accepts proximity as the redundant linkage channel, so the label sits
      // close to its mark and carries no false datum.
      symbol: 'circle',
      symbolSize: 0,
      data: [{
        coord: opts.coord,
        itemStyle: { color: opts.color || C.evergreen },
        label: {
          show: true,
          formatter: text,
          position: opts.position || 'top',
          distance: opts.distance == null ? 8 : opts.distance,
          // Rule 2.3.7 — colour-matched to the mark, at the TEXT contrast.
          // The mark keeps the full palette hue; this is prose, so it takes
          // the hue's text ink and clears 4.5:1. Pass a palette hex as
          // opts.color and the ink is substituted for you.
          color: textInkFor(opts.color || C.evergreen),
          fontFamily: SERIF,
          fontSize: opts.fontSize || 13,
          align: opts.align || 'center',
          width: width,
          overflow: 'break',
          // Legibility over marks comes from a glyph outline, not a filled box.
          // The outline still occludes — see the header comment. It buys
          // legibility where the label brushes a gridline; it does not make
          // the label safe to place over data.
          textBorderColor: C.paper,
          textBorderWidth: 3,
          padding: 0
        }
      }]
    };
  }

  /**
   * Rule 1.3 — banking to 45 degrees (Cleveland 1985; Heer & Agrawala 2006).
   *
   * Returns the pixel height at which the average absolute segment slope of
   * `values` approaches 45 degrees for the given plot width. Use it to set the
   * chart container height instead of a global CSS default, which is what
   * silently decides how every trend in a portfolio reads.
   *
   * Clamped to a sane range; returns null on degenerate input.
   */
  function cascadiaBankedHeight(values, width, opts) {
    opts = opts || {};
    if (!Array.isArray(values) || values.length < 2 || !width) return null;
    var nums = values.filter(function (v) { return typeof v === 'number' && isFinite(v); });
    if (nums.length < 2) return null;

    var min = Math.min.apply(null, nums), max = Math.max.apply(null, nums);
    var range = max - min;
    if (range === 0) return null;

    var n = nums.length - 1;
    var dx = width / n;                       // horizontal px per segment
    var sumAbsDy = 0;
    for (var i = 0; i < n; i++) sumAbsDy += Math.abs(nums[i + 1] - nums[i]);
    var meanAbsDyData = sumAbsDy / n;
    if (meanAbsDyData === 0) return null;

    // Slope 1 in pixel space => height * (meanAbsDy / range) === dx
    var height = dx * range / meanAbsDyData;
    var lo = opts.min || 140, hi = opts.max || 520;
    return Math.round(Math.max(lo, Math.min(hi, height)));
  }

  /**
   * Rules 5.1 / 5.2 — the access layers a theme can reach.
   *
   * Sets role and an authored accessible name on the container, and points it
   * at the visible summary and data table. The KEYBOARD LAYER IS NOT HERE and
   * cannot be: ECharts renders to canvas, which is not in the DOM, so the
   * navigable structure must be built as sibling focusable elements (see
   * Data Navigator, Elavsky et al. 2023). This helper gets you layers 1 and 2
   * and makes the absence of layer 3 explicit rather than silent.
   *
   * `label` must be L1 + L2 only — chart type, encodings, axis ranges, units,
   * then extrema and comparisons. NOT interpretation. Blind readers ranked
   * domain interpretation among the LEAST useful description content
   * (Lundgard & Satyanarayan, TVCG 2022); "insightful" alt text is a
   * regression, not a bonus.
   */
  function cascadiaAccessible(el, opts) {
    var host = (typeof el === 'string') ? document.getElementById(el) : el;
    if (!host) return null;
    opts = opts || {};

    host.setAttribute('role', 'img');
    if (opts.label) host.setAttribute('aria-label', opts.label);

    var describedBy = [];
    if (opts.summaryId) describedBy.push(opts.summaryId);
    if (opts.tableId)   describedBy.push(opts.tableId);
    if (describedBy.length) host.setAttribute('aria-describedby', describedBy.join(' '));

    if (!opts.tableId && !opts.tableExempt) {
      // Rule 5.1 is INVARIANT. Fail loudly in development rather than shipping
      // a chart that quietly has no non-visual route to its data.
      if (root.console && root.console.warn) {
        root.console.warn('[cascadia] Rule 5.1: no data table wired for', host.id || host,
          '- pass tableId, or tableExempt:true if the title and summary carry the full content.');
      }
    }
    return host;
  }


  /**
   * Rule 5.1 layer 3 — keyboard-navigable structure over the data points.
   *
   * ECharts draws to canvas, which is not in the DOM, so there is nothing for a
   * screen reader or a keyboard to traverse. This builds the missing structure
   * as a sibling element and drives it from the same arrays the chart and its
   * data table already use — the Data Navigator pattern (Elavsky, Nadolskis &
   * Moritz, IEEE VIS 2023), where navigation rules are decoupled from input
   * modality so keyboard, screen reader and switch all drive one structure.
   *
   * ONE tab stop per chart, not one per datum. Chartability is explicit that
   * putting a tabindex on every mark is the wrong build: "Interactive elements
   * must have a tab stop, while non-interactive elements must not." Arrow keys
   * move a cursor inside that single stop.
   *
   * Bindings are fixed across the system (Rule 5.1):
   *   Down  descend a level   chart -> series -> point
   *   Up    ascend a level
   *   Left / Right   previous / next sibling, bounded, never wrapping silently
   *   Home / End     first / last sibling
   *   Enter          full detail of the current node
   *   Escape         back to chart level
   *
   * Usage:
   *   cascadiaNavigator(el, {
   *     chart:  echartsInstance,          // optional, for the visual cursor
   *     label:  'Chart-level announcement, L1 + L2',
   *     series: [{ name, points: [{ label, value, seriesIndex, dataIndex }] }],
   *     onFocus: function (node) { ... }  // optional extra visual highlight
   *   });
   *
   * Idempotent: re-calling replaces the navigator for the same host, so a chart
   * that re-renders on every filter change does not accumulate them.
   */
  function cascadiaNavigator(el, spec) {
    var host = (typeof el === 'string') ? document.getElementById(el) : el;
    if (!host || !spec || !spec.series) return null;

    var prev = host.parentNode && host.parentNode.querySelector(
      '[data-cascadia-nav="' + (host.id || '') + '"]');
    if (prev) prev.parentNode.removeChild(prev);

    var wrap = document.createElement('div');
    wrap.className = 'cascadia-nav';
    wrap.setAttribute('data-cascadia-nav', host.id || '');
    wrap.style.cssText = 'margin:2px 0 0;';

    var btn = document.createElement('div');
    btn.tabIndex = 0;
    btn.setAttribute('role', 'application');
    btn.setAttribute('aria-roledescription', 'chart navigator');
    btn.setAttribute('aria-label',
      'Chart navigator. ' + (spec.label || '') +
      ' Press the down arrow to enter, left and right to move, up to go back.');
    btn.style.cssText =
      'display:inline-block;font:' + MIN_TEXT + 'px/1.5 ' + SANS + ';color:' + C.slateMoss +
      ';border:1px solid ' + C.mist + ';border-radius:2px;padding:3px 9px;' +
      'min-height:24px;cursor:default;background:' + C.paper + ';';
    btn.textContent = 'Explore this chart by keyboard';

    // Announcements. polite, atomic — a cursor move should not interrupt, but
    // it must be read whole rather than word by word.
    var live = document.createElement('p');
    live.setAttribute('aria-live', 'polite');
    live.setAttribute('aria-atomic', 'true');
    live.style.cssText =
      'position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;' +
      'clip:rect(0 0 0 0);white-space:nowrap;border:0;';

    // Visible cursor text for sighted keyboard users — the same string the
    // screen reader gets, so the two experiences do not diverge.
    var cursor = document.createElement('span');
    cursor.style.cssText =
      'display:none;margin-left:9px;font:' + MIN_TEXT + 'px/1.5 ' + SANS +
      ';color:' + C.basalt + ';';

    wrap.appendChild(btn);
    wrap.appendChild(cursor);
    wrap.appendChild(live);
    host.insertAdjacentElement('afterend', wrap);

    var LEVEL = { CHART: 0, SERIES: 1, POINT: 2 };
    var level = LEVEL.CHART, si = 0, pi = 0;

    function say(msg) {
      live.textContent = '';
      // force a re-announcement even when the string repeats
      root.setTimeout(function () { live.textContent = msg; }, 30);
      cursor.textContent = msg;
      cursor.style.display = msg ? 'inline' : 'none';
    }

    function pts(i) { return (spec.series[i] && spec.series[i].points) || []; }

    function highlight() {
      if (!spec.chart || level !== LEVEL.POINT) return;
      var p = pts(si)[pi];
      if (!p || p.seriesIndex == null || p.dataIndex == null) return;
      try {
        spec.chart.dispatchAction({ type: 'downplay' });
        spec.chart.dispatchAction({ type: 'highlight',
          seriesIndex: p.seriesIndex, dataIndex: p.dataIndex });
        spec.chart.dispatchAction({ type: 'showTip',
          seriesIndex: p.seriesIndex, dataIndex: p.dataIndex });
      } catch (e) { /* a chart form that cannot highlight is not a failure */ }
    }
    function clearHighlight() {
      if (!spec.chart) return;
      try {
        spec.chart.dispatchAction({ type: 'downplay' });
        spec.chart.dispatchAction({ type: 'hideTip' });
      } catch (e) {}
    }

    function announce() {
      if (level === LEVEL.CHART) {
        say('Chart level. ' + spec.series.length + ' ' +
            (spec.series.length === 1 ? 'series' : 'series') + '. ' +
            'Down arrow to enter.');
        clearHighlight();
      } else if (level === LEVEL.SERIES) {
        var s = spec.series[si];
        say('Series ' + (si + 1) + ' of ' + spec.series.length + ': ' + s.name +
            '. ' + pts(si).length + ' points' + (s.summary ? '. ' + s.summary : '') +
            '. Down arrow for points.');
        clearHighlight();
      } else {
        var p = pts(si)[pi];
        say('Point ' + (pi + 1) + ' of ' + pts(si).length + '. ' +
            (p ? p.label + ': ' + p.value : 'no value'));
        highlight();
      }
      if (spec.onFocus) spec.onFocus({ level: level, seriesIndex: si, pointIndex: pi });
    }

    function move(delta) {
      if (level === LEVEL.SERIES) {
        var n = spec.series.length, next = si + delta;
        if (next < 0)  { say('Start of series list. ' + spec.series[si].name); return; }
        if (next >= n) { say('End of series list. ' + spec.series[si].name); return; }
        si = next; pi = 0; announce();
      } else if (level === LEVEL.POINT) {
        var m = pts(si).length, np = pi + delta;
        // Bounded cursor (Rule 5.1) — announce the boundary, never wrap silently
        if (np < 0)  { say('Start of ' + spec.series[si].name + '.'); return; }
        if (np >= m) { say('End of ' + spec.series[si].name + '.'); return; }
        pi = np; announce();
      }
    }

    btn.addEventListener('keydown', function (e) {
      var k = e.key;
      if (['ArrowDown','ArrowUp','ArrowLeft','ArrowRight','Home','End','Enter','Escape']
          .indexOf(k) < 0) return;
      e.preventDefault(); e.stopPropagation();
      if (k === 'ArrowDown') {
        if (level === LEVEL.CHART && spec.series.length) { level = LEVEL.SERIES; si = 0; pi = 0; announce(); }
        else if (level === LEVEL.SERIES && pts(si).length) { level = LEVEL.POINT; pi = 0; announce(); }
        else say('Lowest level reached.');
      } else if (k === 'ArrowUp') {
        if (level === LEVEL.POINT) { level = LEVEL.SERIES; announce(); }
        else if (level === LEVEL.SERIES) { level = LEVEL.CHART; announce(); }
        else say('Chart level. Down arrow to enter.');
      } else if (k === 'ArrowRight') move(1);
      else if (k === 'ArrowLeft') move(-1);
      else if (k === 'Home') {
        if (level === LEVEL.SERIES) { si = 0; pi = 0; announce(); }
        else if (level === LEVEL.POINT) { pi = 0; announce(); }
      } else if (k === 'End') {
        if (level === LEVEL.SERIES) { si = spec.series.length - 1; pi = 0; announce(); }
        else if (level === LEVEL.POINT) { pi = pts(si).length - 1; announce(); }
      } else if (k === 'Enter') {
        if (level === LEVEL.POINT) {
          var p = pts(si)[pi];
          say(spec.series[si].name + ', ' + (p ? p.label + ': ' + (p.detail || p.value) : ''));
        } else announce();
      } else if (k === 'Escape') { level = LEVEL.CHART; si = 0; pi = 0; announce(); }
    });

    btn.addEventListener('focus', function () {
      btn.style.borderColor = C.evergreen;
      if (level === LEVEL.CHART) say('Chart navigator ready. Down arrow to enter.');
    });
    btn.addEventListener('blur', function () {
      btn.style.borderColor = C.mist;
      cursor.style.display = 'none';
      clearHighlight();
    });

    return wrap;
  }

  /**
   * Keep a chart sized to its container.
   *
   * A chart initialised while its container has zero width — inside a hidden
   * tab, a collapsed section, a details element, anything not laid out yet —
   * renders at zero and NEVER RECOVERS on a window resize listener alone,
   * because no window resize event is coming. The container changed, not the
   * window. ResizeObserver is the only thing that sees it.
   *
   * DEFERRED WITH setTimeout, NEVER requestAnimationFrame. This is the part
   * to read twice. rAF does not fire while the page is not compositing, and
   * a container that is hidden or off-screen is precisely the case this
   * observer exists to handle — so an rAF-deferred resize sits pending
   * forever and the chart stays at zero. This bug was fixed once,
   * reintroduced by an rAF "improvement" that looked strictly better, and
   * fixed again. If you are about to swap the setTimeout for rAF, that is
   * the third time.
   *
   * The defer itself is needed because the observer fires inside layout and
   * echarts.resize() reads geometry; resizing synchronously inside the
   * callback loops the observer against itself.
   *
   * Returns a disposer. Call it when the chart is disposed.
   */
  function cascadiaResize(el, chart, opts) {
    var host = (typeof el === 'string') ? document.getElementById(el) : el;
    if (!host || !chart || typeof chart.resize !== 'function') return function () {};
    opts = opts || {};
    var delay = opts.delay == null ? 0 : opts.delay;
    var pending = null;

    function apply() {
      pending = null;
      if (chart.isDisposed && chart.isDisposed()) return;
      if (!host.clientWidth) return;          // still zero — wait for the next report
      chart.resize();
    }
    function schedule() {
      if (pending !== null) root.clearTimeout(pending);
      pending = root.setTimeout(apply, delay);
    }

    if (typeof root.ResizeObserver === 'function') {
      var ro = new root.ResizeObserver(schedule);
      ro.observe(host);
      schedule();                              // catch a container already sized
      return function () {
        if (pending !== null) root.clearTimeout(pending);
        ro.disconnect();
      };
    }

    // No ResizeObserver: fall back to the window listener and say so. The
    // fallback does not fix the zero-width case and is not pretending to.
    root.addEventListener('resize', schedule);
    schedule();
    return function () {
      if (pending !== null) root.clearTimeout(pending);
      root.removeEventListener('resize', schedule);
    };
  }

  /** Rule 5.6 — expose the reduced-motion state so pages can branch on it. */
  function cascadiaMotion() {
    return { reduced: reducedMotion(), duration: reducedMotion() ? 0 : 400 };
  }

  var API = {
    colors: C,
    palette: theme.color.slice(),

    // Rule 2.3.7 — the same five hues at TEXT contrast. Marks take
    // CASCADIA.colors and clear 3:1; text takes CASCADIA.textInk and clears
    // 4.5:1. Evergreen and Lupine already cleared and are the same value in
    // both, which is the point: only the three that failed are darkened, and
    // only along their own hue, so a series keeps its identity between its
    // mark and its label.
    //
    // The rule is compiled in here rather than left as prose for each module
    // to re-derive. CASCADIA.textInkFor(hex) maps a palette hex to its ink
    // and passes anything it does not recognise straight through.
    textInk: INK,
    textInkFor: textInkFor,

    // Rule 2.3.4 — scatter points under 8px and strokes under 2px use only
    // these three. Colour difference falls off sharply on small symmetric
    // marks (Szafir, TVCG 2018), and the Cascadia hues sit in a ten-point
    // lightness band, so there is no lightness fallback when chroma shrinks.
    smallMarkPalette: [C.evergreen, C.glacier, C.lichen],
    allPairsTrio:     [C.evergreen, C.glacier, C.lichen],   // v1.0 name, kept

    // Rule 2.3.5 — at most four encoded categories in a single chart.
    // Five only where every series is directly labelled and the chart is
    // wider than 768px. Convergent: UK Gov Analysis Function says four,
    // Datawrapper says three to four, Chartability caps at five.
    maxCategories: 4,
    minTextPx: MIN_TEXT,

    seq: ['#8FBA9F', '#65A583', '#3D8D63', '#1E7A4C', '#0F5535'],
    diverging: { neg: C.madrona, mid: C.rain, pos: C.evergreen },

    // Rule 1.2 — Cleveland & McGill (1984), most to least accurate.
    // Reference, not enforcement: the theme cannot see what you are asking
    // the reader to compare.
    encodingRank: [
      'position on a common scale',
      'position on non-aligned scales',
      'length / direction / angle',
      'area',
      'volume / curvature',
      'shading / colour saturation'
    ],

    // Rule 1.1 — declare one before choosing a form.
    relationships: ['deviation', 'correlation', 'ranking', 'distribution',
                    'change over time', 'magnitude', 'part-to-whole',
                    'spatial', 'flow'],

    serif: SERIF,
    sans: SANS,

    // Rule 5.3 / WCAG 1.4.10 — the narrowest canvas the system supports.
    // Helpers that size a text box size it for this width when the caller
    // gives them nothing better to measure.
    minCanvasPx: MIN_CANVAS,

    theme: theme,
    version: '2.3',

    title: cascadiaTitle,
    provenance: cascadiaProvenance,
    annotation: cascadiaAnnotation,
    bankedHeight: cascadiaBankedHeight,
    accessible: cascadiaAccessible,
    navigator: cascadiaNavigator,
    resize: cascadiaResize,
    motion: cascadiaMotion
  };

  if (root.echarts && root.echarts.registerTheme) {
    root.echarts.registerTheme('cascadia', theme);
  }
  root.CASCADIA = API;
  root.cascadiaTitle        = cascadiaTitle;
  root.cascadiaProvenance   = cascadiaProvenance;
  root.cascadiaAnnotation   = cascadiaAnnotation;
  root.cascadiaBankedHeight = cascadiaBankedHeight;
  root.cascadiaAccessible   = cascadiaAccessible;
  root.cascadiaNavigator    = cascadiaNavigator;
  root.cascadiaResize       = cascadiaResize;

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
