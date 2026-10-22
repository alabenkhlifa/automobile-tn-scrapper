// Small SVG chart kit: time series, columns, diverging bars, sparklines.
// Every chart re-renders on resize and shows a tooltip on hover/focus.
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const C = { ink: '#0f172a', mu: '#64748b', grid: '#f1f5f9', axis: '#e2e8f0', ac: '#4f46e5' };

  // "Nice" axis ticks covering [lo, hi]
  function ticks(lo, hi, count = 4) {
    if (lo === hi) { lo -= 1; hi += 1; }
    const raw = (hi - lo) / count;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw);
    const start = Math.floor(lo / step) * step, end = Math.ceil(hi / step) * step;
    const out = [];
    for (let v = start; v <= end + step * 0.01; v += step) out.push(+v.toFixed(6));
    return out;
  }

  function el(tag, attrs = {}, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function mount(host, render) {
    host.classList.add('chart');
    const tip = document.createElement('div');
    tip.className = 'tip';
    tip.setAttribute('role', 'status');
    let width = 0;
    const draw = () => {
      const w = Math.round(host.clientWidth);
      if (!w || w === width) return;
      width = w;
      host.querySelectorAll(':scope > svg, :scope > .tip').forEach(s => s.remove());
      render(w, tip);
      host.appendChild(tip);
    };
    if (host._ro) host._ro.disconnect();
    host._ro = new ResizeObserver(draw);
    host._ro.observe(host);
    draw();
  }

  function placeTip(tip, host, x, y, html) {
    tip.innerHTML = html;
    tip.classList.add('on');
    const hw = host.clientWidth, tw = tip.offsetWidth;
    const left = x + 14 + tw > hw ? x - 14 - tw : x + 14;
    tip.style.left = Math.max(0, left) + 'px';
    tip.style.top = Math.max(0, y - tip.offsetHeight / 2) + 'px';
  }

  // series: [{label, color, points: [[Date, value], ...]}]
  function line(host, opts) {
    const { series, height = 260, format, dateFormat, area = series.length === 1, markers = [], gapDays = 3 } = opts;
    mount(host, (w, tip) => {
      const visible = series.filter(s => !s.hidden && s.points.length);
      const all = visible.flatMap(s => s.points);
      if (!all.length) return;
      const xs = all.map(p => +p[0]), ys = all.map(p => p[1]);
      const x0 = Math.min(...xs), x1 = Math.max(...xs);
      const pad = (Math.max(...ys) - Math.min(...ys)) * 0.08 || Math.abs(ys[0]) * 0.05 || 1;
      const yt = ticks(opts.zero ? 0 : Math.min(...ys) - pad, Math.max(...ys) + pad);
      const ymin = yt[0], ymax = yt[yt.length - 1];
      const L = 8, R = 52, T = 10, B = 24;
      const sx = x => L + (x1 === x0 ? 0.5 : (x - x0) / (x1 - x0)) * (w - L - R);
      const sy = y => T + (1 - (y - ymin) / (ymax - ymin)) * (height - T - B);
      const svg = el('svg', { viewBox: `0 0 ${w} ${height}`, height, role: 'img', 'aria-label': opts.label || '' });

      yt.forEach(v => {
        el('line', { x1: L, x2: w - R, y1: sy(v), y2: sy(v), stroke: v === ymin ? C.axis : C.grid }, svg);
        el('text', { x: w - R + 8, y: sy(v) + 4 }, svg).textContent = format(v, true);
      });
      // Month labels, thinned to fit
      const months = [];
      for (let d = new Date(new Date(x0).getFullYear(), new Date(x0).getMonth() + 1, 1); +d <= x1; d.setMonth(d.getMonth() + 1)) months.push(new Date(d));
      const every = Math.ceil(months.length / Math.max(1, Math.floor((w - L - R) / 70)));
      months.forEach((m, i) => {
        if (i % every) return;
        const x = sx(+m);
        el('line', { x1: x, x2: x, y1: height - B, y2: height - B + 4, stroke: C.axis }, svg);
        el('text', { x, y: height - 6, 'text-anchor': 'middle' }, svg).textContent = dateFormat(m, 'month');
      });

      markers.forEach(m => {
        if (+m.date < x0 || +m.date > x1) return;
        const x = sx(+m.date);
        el('line', { x1: x, x2: x, y1: T, y2: height - B, stroke: m.color || C.mu, 'stroke-dasharray': '3 3' }, svg);
        const t = el('text', { x: x + 6, y: T + 10, fill: m.color || C.mu }, svg);
        t.textContent = m.label;
        t.style.fill = m.color || C.mu;
      });

      visible.forEach(s => {
        // Days with no data break the line instead of being bridged
        const d = s.points.map((p, i) => `${i && +p[0] - +s.points[i - 1][0] <= gapDays * 864e5 ? 'L' : 'M'}${sx(+p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join('');
        if (area) {
          const gid = 'g' + Math.random().toString(36).slice(2);
          const defs = el('defs', {}, svg);
          const lg = el('linearGradient', { id: gid, x1: 0, x2: 0, y1: 0, y2: 1 }, defs);
          el('stop', { offset: 0, 'stop-color': s.color, 'stop-opacity': 0.16 }, lg);
          el('stop', { offset: 1, 'stop-color': s.color, 'stop-opacity': 0 }, lg);
          const last = s.points[s.points.length - 1], first = s.points[0];
          el('path', { d: `${d}L${sx(+last[0])},${sy(ymin)}L${sx(+first[0])},${sy(ymin)}Z`, fill: `url(#${gid})` }, svg);
        }
        el('path', { d, fill: 'none', stroke: s.color, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, svg);
      });

      // Hover layer
      const guide = el('line', { y1: T, y2: height - B, stroke: C.mu, 'stroke-width': 1, opacity: 0 }, svg);
      const dots = visible.map(s => el('circle', { r: 4, fill: s.color, stroke: '#fff', 'stroke-width': 2, opacity: 0 }, svg));
      const hit = el('rect', { x: L, y: 0, width: w - L - R, height, fill: 'transparent', tabindex: 0 }, svg);
      const dates = [...new Set(all.map(p => +p[0]))].sort((a, b) => a - b);
      let idx = dates.length - 1;
      const show = i => {
        idx = Math.max(0, Math.min(dates.length - 1, i));
        const t = dates[idx], x = sx(t);
        guide.setAttribute('x1', x); guide.setAttribute('x2', x); guide.setAttribute('opacity', 0.35);
        let rows = '', ymid = 0, n = 0;
        visible.forEach((s, k) => {
          const p = s.points.find(q => +q[0] === t);
          if (!p) { dots[k].setAttribute('opacity', 0); return; }
          dots[k].setAttribute('cx', x); dots[k].setAttribute('cy', sy(p[1])); dots[k].setAttribute('opacity', 1);
          ymid += sy(p[1]); n++;
          rows += `<div class="tip-row"><i style="background:${s.color}"></i>${s.label}<b>${format(p[1])}</b></div>`;
        });
        placeTip(tip, host, x, n ? ymid / n : height / 2, `<div class="tip-date">${dateFormat(new Date(t), 'day')}</div>${rows}`);
      };
      const hide = () => { guide.setAttribute('opacity', 0); dots.forEach(d => d.setAttribute('opacity', 0)); tip.classList.remove('on'); };
      const nearest = evt => {
        const r = svg.getBoundingClientRect();
        const x = (evt.clientX - r.left) * (w / r.width);
        let best = 0;
        dates.forEach((t, i) => { if (Math.abs(sx(t) - x) < Math.abs(sx(dates[best]) - x)) best = i; });
        return best;
      };
      hit.addEventListener('pointermove', e => show(nearest(e)));
      hit.addEventListener('pointerleave', hide);
      hit.addEventListener('focus', () => show(idx));
      hit.addEventListener('blur', hide);
      hit.addEventListener('keydown', e => {
        if (e.key === 'ArrowLeft') { show(idx - 1); e.preventDefault(); }
        if (e.key === 'ArrowRight') { show(idx + 1); e.preventDefault(); }
      });
      host.prepend(svg);
    });
  }

  // bins: [{label, value, tip, hi}]
  function columns(host, opts) {
    const { bins, height = 220, format, labelEvery = 1 } = opts;
    mount(host, (w, tip) => {
      const L = 8, R = 44, T = 8, B = 24;
      const max = Math.max(...bins.map(b => b.value), 1);
      const yt = ticks(0, max, 3);
      const ymax = yt[yt.length - 1];
      const sy = v => T + (1 - v / ymax) * (height - T - B);
      const bw = (w - L - R) / bins.length;
      const svg = el('svg', { viewBox: `0 0 ${w} ${height}`, height, role: 'img', 'aria-label': opts.label || '' });
      yt.forEach(v => {
        el('line', { x1: L, x2: w - R, y1: sy(v), y2: sy(v), stroke: v === 0 ? C.axis : C.grid }, svg);
        el('text', { x: w - R + 8, y: sy(v) + 4 }, svg).textContent = format(v);
      });
      bins.forEach((b, i) => {
        const x = L + i * bw, h = height - B - sy(b.value);
        const g = el('g', { tabindex: 0, 'aria-label': `${b.label}: ${format(b.value)}` }, svg);
        el('rect', { x: x + Math.min(3, bw * 0.12), y: sy(b.value), width: Math.max(1, bw - Math.min(6, bw * 0.24)), height: Math.max(0, h), rx: 2, fill: b.hi ? C.ac : '#c7d2fe' }, g);
        const hit = el('rect', { x, y: T, width: bw, height: height - T - B, fill: 'transparent' }, g);
        if (i % labelEvery === 0) el('text', { x: x + bw / 2, y: height - 6, 'text-anchor': 'middle' }, svg).textContent = b.short ?? b.label;
        const show = () => placeTip(tip, host, x + bw / 2, sy(b.value) - 10, b.tip || `<div class="tip-date">${b.label}</div><div class="tip-row">${format(b.value)}</div>`);
        hit.addEventListener('pointerenter', show);
        g.addEventListener('focus', show);
        hit.addEventListener('pointerleave', () => tip.classList.remove('on'));
        g.addEventListener('blur', () => tip.classList.remove('on'));
      });
      host.prepend(svg);
    });
  }

  // items: [{label, up, down, tip}] — rises above the axis, drops below
  function diverging(host, opts) {
    const { items, height = 220, upColor = '#dc2626', downColor = '#047857', upLabel, downLabel } = opts;
    mount(host, (w, tip) => {
      const L = 8, R = 44, T = 10, B = 24;
      const max = Math.max(...items.map(i => Math.max(i.up, i.down)), 1);
      const mid = T + (height - T - B) / 2;
      const yt = ticks(0, max, 2), top = yt[yt.length - 1];
      const scale = v => v / top * ((height - T - B) / 2);
      const bw = (w - L - R) / items.length;
      const svg = el('svg', { viewBox: `0 0 ${w} ${height}`, height, role: 'img', 'aria-label': opts.label || '' });
      yt.filter(v => v > 0).forEach(v => {
        [mid - scale(v), mid + scale(v)].forEach(y => {
          el('line', { x1: L, x2: w - R, y1: y, y2: y, stroke: C.grid }, svg);
          el('text', { x: w - R + 8, y: y + 4 }, svg).textContent = v;
        });
      });
      el('line', { x1: L, x2: w - R, y1: mid, y2: mid, stroke: C.axis }, svg);
      el('text', { x: w - R + 8, y: mid + 4 }, svg).textContent = '0';
      const every = Math.ceil(items.length / Math.max(1, Math.floor((w - L - R) / 56)));
      items.forEach((it, i) => {
        const x = L + i * bw, inset = Math.min(4, bw * 0.15);
        const g = el('g', { tabindex: 0 }, svg);
        if (it.up) el('rect', { x: x + inset, y: mid - scale(it.up) - 1, width: bw - inset * 2, height: scale(it.up), rx: 2, fill: upColor }, g);
        if (it.down) el('rect', { x: x + inset, y: mid + 1, width: bw - inset * 2, height: scale(it.down), rx: 2, fill: downColor }, g);
        const hit = el('rect', { x, y: T, width: bw, height: height - T - B, fill: 'transparent' }, g);
        if (i % every === 0) el('text', { x: x + bw / 2, y: height - 6, 'text-anchor': 'middle' }, svg).textContent = it.short;
        const show = () => placeTip(tip, host, x + bw / 2, mid, it.tip);
        hit.addEventListener('pointerenter', show);
        g.addEventListener('focus', show);
        hit.addEventListener('pointerleave', () => tip.classList.remove('on'));
        g.addEventListener('blur', () => tip.classList.remove('on'));
      });
      host.prepend(svg);
    });
  }

  function spark(values, { w = 84, h = 32, color = C.ac } = {}) {
    const v = values.filter(x => x != null);
    if (v.length < 2) return '';
    const lo = Math.min(...v), hi = Math.max(...v), r = hi - lo || 1;
    const d = v.map((y, i) => `${i ? 'L' : 'M'}${(2 + i / (v.length - 1) * (w - 4)).toFixed(1)},${(h - 2 - (y - lo) / r * (h - 4)).toFixed(1)}`).join('');
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><path d="${d}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
  }

  window.Charts = { line, columns, diverging, spark };
})();
