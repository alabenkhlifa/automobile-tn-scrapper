// Marché auto dashboard: hash-routed app over the files in data/.
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // State, storage, i18n
  // ---------------------------------------------------------------------------
  const store = {
    get(k) { try { return localStorage.getItem('ma.' + k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem('ma.' + k, v); } catch { /* private mode */ } },
  };
  const state = { lang: store.get('lang') === 'en' ? 'en' : 'fr', period: store.get('period') || 'all', data: null, history: null, files: {}, exportFn: null };

  const I18N = {
    fr: {
      brand: 'Marché auto', dashboards: 'Tableaux', sources: 'Sources', frozen: 'gelé',
      'nav.neuf': 'Neuf TN', 'nav.occasion': 'Occasion TN', 'nav.europe': 'Europe', 'nav.historique': 'Historique',
      export: 'Exporter CSV', period3: '3 mois', period6: '6 mois', periodAll: 'Tout', period: 'Période',
      updated: d => `mis à jour le ${d}`, scrapedOn: d => `relevé du ${d}`,
      staleTitle: 'Relevé gelé', staleText: d => `Cette source n’a pas été mise à jour récemment. Ces chiffres datent du relevé du ${d}.`,
      loading: 'Chargement des données…', loadError: 'Impossible de charger les données du tableau.', retry: 'Réessayer',
      search: 'Rechercher…', all: 'Tous', allF: 'Toutes', noResults: 'Aucun résultat pour ces filtres.',
      rows: (a, b, n) => `${a}–${b} sur ${n}`, prev: 'Précédent', next: 'Suivant', since: d => `depuis le ${d}`,
      in7d: 'sur 7 jours', share: 'part', listings: 'annonces', trims: 'finitions', median: 'Médiane', open: 'Ouvrir l’annonce',
      priceMedian: 'Prix médian', count: 'Annonces', models: 'modèles', countries: 'pays',
      // New
      'new.title': 'Voitures neuves · Tunisie', 'new.sub': (n, b) => `Catalogue automobile.tn · ${n} finitions, ${b} marques`,
      'new.kMedian': 'Prix médian', 'new.kTrims': 'Finitions', 'new.kMin': 'Prix le plus bas', 'new.kBrands': 'Marques',
      'new.electrified': n => `${n} électrifiées`, 'new.chart': 'Prix médian du catalogue', 'new.chartSub': 'Médiane des prix catalogue à chaque relevé hebdomadaire',
      'new.budget': 'Finitions par budget', 'new.fuel': 'Énergie', 'new.body': 'Carrosserie',
      'new.brands': 'Prix par marque', 'new.brandsSub': 'Du modèle le moins cher au plus cher ; le trait marque la médiane',
      'new.all': 'Toutes les finitions', 'new.allSub': 'Prix catalogue officiels publiés sur automobile.tn',
      'col.brand': 'Marque', 'col.from': 'Dès', 'col.median': 'Médiane', 'col.max': 'Max', 'col.range': 'Fourchette',
      'col.trim': 'Finition', 'col.body': 'Carrosserie', 'col.fuel': 'Énergie', 'col.cv': 'CV', 'col.hp': 'ch', 'col.price': 'Prix',
      // Used
      'used.title': 'Voitures d’occasion · Tunisie', 'used.sub': (n, r) => `Annonces 9annas.tn · ${n} retenues sur ${r}`,
      'used.kCount': 'Annonces suivies', 'used.kMedian': 'Prix médian demandé', 'used.kKm': 'Kilométrage médian', 'used.kBrands': 'Marques',
      'used.year': y => `année médiane ${y}`, 'used.kCompare': m => `${m} · Tunisie`, 'used.compareSub': (e, n) => `Europe ${e} · ${n} annonces`, 'used.dropped': n => `${n} annonces écartées`, 'used.droppedHint': 'Prix hors 3 000–400 000 DT ou année invraisemblable',
      'used.chart': 'Évolution du marché', 'used.chartSub': 'Toutes les annonces suivies depuis avril 2026',
      'used.fuel': 'Énergie', 'used.gearbox': 'Boîte de vitesses', 'used.hist': 'Répartition des prix demandés', 'used.histSub': q => `La moitié centrale des annonces demande entre ${q[0]} et ${q[2]} DT`,
      'used.gov': 'Gouvernorats', 'used.models': 'Modèles les plus annoncés', 'used.modelsSub': 'Prix demandés en Tunisie, comparés aux annonces européennes du même modèle',
      'used.listings': 'Annonces', 'used.listingsSub': 'Les plus récentes d’abord ; cliquez pour ouvrir l’annonce sur 9annas.tn',
      'col.model': 'Modèle', 'col.count': 'Annonces', 'col.tn': 'Médiane TN', 'col.iqr': '25–75 %', 'col.eu': 'Médiane Europe', 'col.trend': 'Tendance',
      'col.listing': 'Annonce', 'col.year': 'Année', 'col.km': 'Km', 'col.gov': 'Gouvernorat', 'col.country': 'Pays',
      'f.brand': 'Marque', 'f.gov': 'Gouvernorat', 'f.maxPrice': 'Prix max', 'f.minYear': 'Année min', 'f.body': 'Carrosserie', 'f.fuel': 'Énergie', 'f.country': 'Pays', 'f.type': 'Type',
      // Europe
      'eu.title': 'Voitures en Europe', 'eu.sub': n => `AutoScout24 · ${n} annonces en Allemagne, France, Italie et Belgique · ≤ 8 ans, ≤ 100 000 €`,
      'eu.kCount': 'Annonces', 'eu.kMedian': 'Prix médian', 'eu.kKm': 'Kilométrage médian', 'eu.kCheapest': 'Pays le moins cher',
      'eu.chart': 'Prix médian par pays', 'eu.chartSub': 'Chaque jour, depuis le 15 avril 2026', 'eu.byCountry': 'Par pays',
      'eu.hist': 'Répartition des prix', 'eu.histSub': 'Annonces par tranche de 5 000 €', 'eu.makes': 'Marques', 'eu.listings': 'Annonces',
      'eu.listingsSub': 'Cliquez pour ouvrir l’annonce sur AutoScout24',
      // History
      'hist.title': 'Historique du catalogue neuf', 'hist.sub': n => `Changements détectés entre les relevés hebdomadaires d’automobile.tn · ${n} relevés`,
      'hist.kScrapes': 'Relevés comparés', 'hist.kSize': 'Taille du catalogue', 'hist.kDrops': 'Baisses de prix', 'hist.kRises': 'Hausses de prix',
      'hist.chart': 'Changements de prix par relevé', 'hist.chartSub': 'Nombre de finitions dont le prix a baissé ou augmenté',
      'hist.rises': 'hausses', 'hist.drops': 'baisses', 'hist.brands': 'Marques les plus touchées', 'hist.brandsSub': 'changements de prix',
      'hist.changes': 'Changements de prix', 'hist.added': 'Ajoutées', 'hist.removed': 'Retirées', 'hist.catalog': 'Finitions ajoutées et retirées',
      'col.date': 'Date', 'col.old': 'Ancien prix', 'col.new': 'Nouveau prix', 'col.change': 'Variation', 'type.drops': 'Baisses', 'type.rises': 'Hausses',
    },
    en: {
      brand: 'Car market', dashboards: 'Dashboards', sources: 'Sources', frozen: 'frozen',
      'nav.neuf': 'New · TN', 'nav.occasion': 'Used · TN', 'nav.europe': 'Europe', 'nav.historique': 'History',
      export: 'Export CSV', period3: '3 months', period6: '6 months', periodAll: 'All', period: 'Period',
      updated: d => `updated ${d}`, scrapedOn: d => `scraped ${d}`,
      staleTitle: 'Frozen data', staleText: d => `This source has not been updated recently. These figures come from the ${d} scrape.`,
      loading: 'Loading data…', loadError: 'Could not load the dashboard data.', retry: 'Retry',
      search: 'Search…', all: 'All', allF: 'All', noResults: 'No results for these filters.',
      rows: (a, b, n) => `${a}–${b} of ${n}`, prev: 'Previous', next: 'Next', since: d => `since ${d}`,
      in7d: 'in 7 days', share: 'share', listings: 'listings', trims: 'trims', median: 'Median', open: 'Open listing',
      priceMedian: 'Median price', count: 'Listings', models: 'models', countries: 'countries',
      'new.title': 'New cars · Tunisia', 'new.sub': (n, b) => `automobile.tn catalog · ${n} trims, ${b} brands`,
      'new.kMedian': 'Median price', 'new.kTrims': 'Trims', 'new.kMin': 'Lowest price', 'new.kBrands': 'Brands',
      'new.electrified': n => `${n} electrified`, 'new.chart': 'Catalog median price', 'new.chartSub': 'Median list price at each weekly scrape',
      'new.budget': 'Trims by budget', 'new.fuel': 'Fuel', 'new.body': 'Body type',
      'new.brands': 'Prices by brand', 'new.brandsSub': 'From the cheapest to the most expensive model; the tick marks the median',
      'new.all': 'All trims', 'new.allSub': 'Official list prices published on automobile.tn',
      'col.brand': 'Brand', 'col.from': 'From', 'col.median': 'Median', 'col.max': 'Max', 'col.range': 'Range',
      'col.trim': 'Trim', 'col.body': 'Body', 'col.fuel': 'Fuel', 'col.cv': 'Tax HP', 'col.hp': 'hp', 'col.price': 'Price',
      'used.title': 'Used cars · Tunisia', 'used.sub': (n, r) => `9annas.tn listings · ${n} kept of ${r}`,
      'used.kCount': 'Tracked listings', 'used.kMedian': 'Median asking price', 'used.kKm': 'Median mileage', 'used.kBrands': 'Brands',
      'used.year': y => `median year ${y}`, 'used.kCompare': m => `${m} · Tunisia`, 'used.compareSub': (e, n) => `Europe ${e} · ${n} listings`, 'used.dropped': n => `${n} listings excluded`, 'used.droppedHint': 'Price outside 3,000–400,000 DT or implausible year',
      'used.chart': 'Market trend', 'used.chartSub': 'All listings tracked since April 2026',
      'used.fuel': 'Fuel', 'used.gearbox': 'Gearbox', 'used.hist': 'Asking price distribution', 'used.histSub': q => `The middle half of listings ask between ${q[0]} and ${q[2]} DT`,
      'used.gov': 'Governorates', 'used.models': 'Most listed models', 'used.modelsSub': 'Asking prices in Tunisia next to European listings of the same model',
      'used.listings': 'Listings', 'used.listingsSub': 'Newest first; click to open the listing on 9annas.tn',
      'col.model': 'Model', 'col.count': 'Listings', 'col.tn': 'Median TN', 'col.iqr': '25–75 %', 'col.eu': 'Median Europe', 'col.trend': 'Trend',
      'col.listing': 'Listing', 'col.year': 'Year', 'col.km': 'km', 'col.gov': 'Governorate', 'col.country': 'Country',
      'f.brand': 'Brand', 'f.gov': 'Governorate', 'f.maxPrice': 'Max price', 'f.minYear': 'Min year', 'f.body': 'Body', 'f.fuel': 'Fuel', 'f.country': 'Country', 'f.type': 'Type',
      'eu.title': 'Cars in Europe', 'eu.sub': n => `AutoScout24 · ${n} listings in Germany, France, Italy and Belgium · ≤ 8 years, ≤ €100,000`,
      'eu.kCount': 'Listings', 'eu.kMedian': 'Median price', 'eu.kKm': 'Median mileage', 'eu.kCheapest': 'Cheapest country',
      'eu.chart': 'Median price by country', 'eu.chartSub': 'Daily, since April 15, 2026', 'eu.byCountry': 'By country',
      'eu.hist': 'Price distribution', 'eu.histSub': 'Listings per €5,000 band', 'eu.makes': 'Makes', 'eu.listings': 'Listings',
      'eu.listingsSub': 'Click to open the listing on AutoScout24',
      'hist.title': 'New-car catalog history', 'hist.sub': n => `Changes detected between weekly automobile.tn scrapes · ${n} scrapes`,
      'hist.kScrapes': 'Scrapes compared', 'hist.kSize': 'Catalog size', 'hist.kDrops': 'Price drops', 'hist.kRises': 'Price rises',
      'hist.chart': 'Price changes per scrape', 'hist.chartSub': 'Number of trims whose price went down or up',
      'hist.rises': 'rises', 'hist.drops': 'drops', 'hist.brands': 'Most affected brands', 'hist.brandsSub': 'price changes',
      'hist.changes': 'Price changes', 'hist.added': 'Added', 'hist.removed': 'Removed', 'hist.catalog': 'Trims added and removed',
      'col.date': 'Date', 'col.old': 'Old price', 'col.new': 'New price', 'col.change': 'Change', 'type.drops': 'Drops', 'type.rises': 'Rises',
    },
  };
  const VALUES = {
    en: {
      Essence: 'Petrol', Diesel: 'Diesel', Hybride: 'Hybrid', 'Électrique': 'Electric', Autre: 'Other', 'Non précisé': 'Not stated',
      Manuelle: 'Manual', Automatique: 'Automatic', Berline: 'Sedan', Citadine: 'City car', Utilitaire: 'Van', Compacte: 'Compact', 'Pick up': 'Pickup', Monospace: 'MPV', Cabriolet: 'Convertible', 'Coupé': 'Coupe',
      petrol: 'Petrol', diesel: 'Diesel', electric: 'Electric', hybrid: 'Hybrid', 'plug-in hybrid': 'Plug-in hybrid', other: 'Other', lpg: 'LPG',
      used: 'Used', new: 'New', de: 'Germany', fr: 'France', it: 'Italy', be: 'Belgium',
    },
    fr: {
      petrol: 'Essence', diesel: 'Diesel', electric: 'Électrique', hybrid: 'Hybride', 'plug-in hybrid': 'Hybride rechargeable', other: 'Autre', lpg: 'GPL',
      used: 'Occasion', new: 'Neuve', de: 'Allemagne', fr: 'France', it: 'Italie', be: 'Belgique',
    },
  };
  const t = (k, ...a) => { const v = I18N[state.lang][k] ?? I18N.fr[k] ?? k; return typeof v === 'function' ? v(...a) : v; };
  const tv = v => (v == null ? '–' : VALUES[state.lang][v] ?? v);

  // ---------------------------------------------------------------------------
  // Formatting
  // ---------------------------------------------------------------------------
  const locale = () => (state.lang === 'fr' ? 'fr-FR' : 'en-US');
  const num = v => (v == null ? '–' : new Intl.NumberFormat(locale(), { maximumFractionDigits: 0 }).format(v));
  const dt = v => (v == null ? '–' : `${num(v)} DT`);
  const eur = v => (v == null ? '–' : state.lang === 'fr' ? `${num(v)} €` : `€${num(v)}`);
  const axis = (v, cur) => {
    const s = Math.abs(v) >= 1000 ? `${num(v / 1000)}k` : num(v);
    return cur === '€' ? (state.lang === 'fr' ? `${s} €` : `€${s}`) : cur ? `${s} ${cur}` : s;
  };
  const pct = (a, b) => (a && b != null ? (b - a) / a * 100 : null);
  const fpct = v => (v == null ? '–' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${new Intl.NumberFormat(locale(), { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(Math.abs(v))} %`);
  const dir = v => (v > 0.05 ? 'up' : v < -0.05 ? 'down' : '');
  const D = s => new Date(String(s).slice(0, 10) + 'T00:00:00');
  // Dates never break across lines ("26 janv." stays together)
  const fdate = (d, kind = 'day') => new Intl.DateTimeFormat(locale(), kind === 'month' ? { month: 'short' } : kind === 'short' ? { day: 'numeric', month: 'short' } : kind === 'num' ? { day: '2-digit', month: '2-digit' } : { day: 'numeric', month: 'short', year: 'numeric' }).format(d instanceof Date ? d : D(d)).replace(/ /g, '\u00a0');
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fold = s => String(s ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const html = (strings, ...vals) => strings.reduce((a, s, i) => a + s + (i < vals.length ? vals[i] ?? '' : ''), '');

  const ICON = {
    tag: '<path d="M2.5 8.6V3a.5.5 0 0 1 .5-.5h5.6l5 5a1 1 0 0 1 0 1.4l-4.2 4.2a1 1 0 0 1-1.4 0z"/><circle cx="5.5" cy="5.5" r="1"/>',
    car: '<path d="M3 9.5 4.3 6a1.5 1.5 0 0 1 1.4-1h4.6a1.5 1.5 0 0 1 1.4 1L13 9.5M2.5 9.5h11v2.5h-11zM4 12v1.5M12 12v1.5"/><circle cx="5" cy="10.8" r=".4"/><circle cx="11" cy="10.8" r=".4"/>',
    globe: '<circle cx="8" cy="8" r="5.5"/><path d="M2.5 8h11M8 2.5c1.6 1.6 2.4 3.4 2.4 5.5S9.6 11.9 8 13.5M8 2.5C6.4 4.1 5.6 5.9 5.6 8s.8 3.9 2.4 5.5"/>',
    clock: '<circle cx="8" cy="8" r="5.5"/><path d="M8 5v3.2l2 1.3"/>',
    search: '<circle cx="7" cy="7" r="4.25"/><path d="m10.2 10.2 3.3 3.3"/>',
    download: '<path d="M8 2.5v8M4.8 7.6 8 10.8l3.2-3.2M3 13.5h10"/>',
    ext: '<path d="M9.5 2.5h4v4M13.5 2.5 7.5 8.5M11.5 9.5v3a1 1 0 0 1-1 1h-7a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1h3"/>',
    sort: '<path d="M5 6.5 8 3.5l3 3M5 9.5l3 3 3-3"/>',
    asc: '<path d="M5 9.5 8 6.5l3 3"/>',
    desc: '<path d="M5 6.5 8 9.5l3-3"/>',
    alert: '<path d="M8 2.5 14 13H2zM8 6.5v3"/><circle cx="8" cy="11.3" r=".3"/>',
    image: '<rect x="2.5" y="3.5" width="11" height="9" rx="1.5"/><circle cx="6" cy="6.8" r="1"/><path d="m3 11.5 3.2-3 2.3 2 1.8-1.5 2.7 2.5"/>',
  };
  const icon = (name, cls = '') => `<svg class="${cls}" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[name]}</svg>`;

  // ---------------------------------------------------------------------------
  // Data
  // ---------------------------------------------------------------------------
  async function getJSON(path) {
    if (!state.files[path]) {
      state.files[path] = fetch(path, { cache: 'no-cache' }).then(r => {
        if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
        return r.json();
      }).catch(e => { delete state.files[path]; throw e; });
    }
    return state.files[path];
  }
  const unpack = p => p.rows.map(r => Object.fromEntries(p.cols.map((c, i) => [c, r[i]])));

  // Restrict a series to the chosen period, measured back from its last point
  function inPeriod(series) {
    if (!series.length || state.period === 'all') return series;
    const days = state.period === '3m' ? 91 : 182;
    const end = D(series[series.length - 1].date);
    return series.filter(p => (end - D(p.date)) / 864e5 <= days);
  }

  // ---------------------------------------------------------------------------
  // Shell
  // ---------------------------------------------------------------------------
  const ROUTES = [
    { id: 'neuf', icon: 'tag', count: () => state.data?.new?.count },
    { id: 'occasion', icon: 'car', count: () => state.data?.used?.count },
    { id: 'europe', icon: 'globe', count: () => state.data?.eu?.count },
    { id: 'historique', icon: 'clock', count: () => state.data?.catalog?.entries?.length },
  ];
  const route = () => {
    const id = (location.hash.match(/^#\/([a-z]+)/) || [])[1];
    return ROUTES.some(r => r.id === id) ? id : 'occasion';
  };

  function navItems() {
    const cur = route();
    return ROUTES.map(r => `<a class="nav-item" href="#/${r.id}" ${r.id === cur ? 'aria-current="page"' : ''}>${icon(r.icon)}<span>${t('nav.' + r.id)}</span>${r.count() != null ? `<span class="count">${num(r.count())}</span>` : ''}</a>`).join('');
  }
  function langSwitch() {
    return `<div class="lang" role="group" aria-label="Langue / Language"><button type="button" data-lang="fr" aria-pressed="${state.lang === 'fr'}">FR</button><button type="button" data-lang="en" aria-pressed="${state.lang === 'en'}">EN</button></div>`;
  }
  function sources() {
    const s = state.data?.sources;
    if (!s) return '';
    return ['used', 'eu', 'new'].map(k => {
      const src = s[k];
      return `<div class="source"><span>${esc(src.name)}</span><span title="${esc(t('scrapedOn', fdate(src.scraped_at)))}"><i class="dot ${src.stale ? 'stale' : ''}"></i>${src.stale ? `${t('frozen')} ${fdate(src.scraped_at, 'short')}` : fdate(src.scraped_at, 'short')}</span></div>`;
    }).join('');
  }
  function sourcesCompact() {
    const s = state.data?.sources;
    if (!s) return '';
    return ['used', 'eu', 'new'].map(k => `<span><i class="dot ${s[k].stale ? 'stale' : ''}"></i>${esc(s[k].name)} ${s[k].stale ? `${t('frozen')} ` : ''}${fdate(s[k].scraped_at, 'num')}</span>`).join('');
  }
  const mark = '<span class="brand-mark"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 12.5 6 8l3 2.5 4.5-6"/></svg></span>';

  function renderShell() {
    document.documentElement.lang = state.lang;
    document.getElementById('app').innerHTML = html`
      <div class="app">
        <aside class="side" aria-label="${t('dashboards')}">
          <a class="brand" href="#/occasion">${mark}${t('brand')}</a>
          <div class="side-label">${t('dashboards')}</div>
          <nav>${navItems()}</nav>
          <div class="side-label">${t('sources')}</div>
          ${sources()}
          <div class="side-foot">${langSwitch()}<a href="https://github.com/alabenkhlifa/automobile-tn-scrapper">GitHub</a></div>
        </aside>
        <div>
          <header class="topbar">
            <div class="topbar-row"><a class="brand" href="#/occasion" style="padding:0">${mark}${t('brand')}</a>${langSwitch()}</div>
            <div class="topbar-sources">${sourcesCompact()}</div>
            <nav>${navItems()}</nav>
          </header>
          <main class="main" id="main" tabindex="-1"></main>
        </div>
      </div>`;
    document.querySelectorAll('[data-lang]').forEach(b => b.addEventListener('click', () => {
      state.lang = b.dataset.lang;
      store.set('lang', state.lang);
      render();
    }));
  }

  // ---------------------------------------------------------------------------
  // Building blocks
  // ---------------------------------------------------------------------------
  function header(title, sub, { period = true } = {}) {
    const p = [['3m', t('period3')], ['6m', t('period6')], ['all', t('periodAll')]];
    return html`<div class="head"><div class="head-text"><h1>${title}</h1><p>${sub}</p></div>
      ${period ? `<div class="seg" role="group" aria-label="${t('period')}">${p.map(([k, l]) => `<button type="button" data-period="${k}" aria-pressed="${state.period === k}">${l}</button>`).join('')}</div>` : ''}
      <button type="button" class="btn primary" id="export" aria-label="${t('export')}">${icon('download')}<span>${t('export')}</span></button></div>`;
  }
  function staleNotice(src) {
    if (!src?.stale) return '';
    return `<div class="notice" role="note">${icon('alert')}<div><b>${t('staleTitle')}.</b> ${t('staleText', fdate(src.scraped_at))}</div></div>`;
  }
  function kpi(label, value, unit, sub, subClass = '', spark = null, title = '') {
    return html`<div class="kpi"><span class="kpi-label">${label}</span><div style="min-width:0"><div class="kpi-value">${value}${unit ? `<small>${unit}</small>` : ''}</div>
      <div class="kpi-sub ${subClass}" ${title ? `title="${esc(title)}"` : ''}>${sub}</div></div>${spark ? Charts.spark(spark) : ''}</div>`;
  }
  function bars(items, { total, soft = false, scroll = false, fmt = num } = {}) {
    const max = Math.max(...items.map(i => i[1]), 1);
    const sum = total ?? items.reduce((a, i) => a + i[1], 0);
    return `<div class="bars ${scroll ? 'scroll' : ''}">${items.map(([k, v]) => `<div class="bar"><span class="bar-label" title="${esc(tv(k))}">${esc(tv(k))}</span><span class="bar-track"><span class="bar-fill ${soft ? 'soft' : ''}" style="width:${(v / max * 100).toFixed(1)}%"></span></span><span class="bar-value">${fmt(v)}</span><span class="bar-share">${sum ? Math.round(v / sum * 100) + ' %' : ''}</span></div>`).join('')}</div>`;
  }
  function card(id, title, hint = '', body = '', sub = '') {
    return `<section class="card" ${id ? `id="${id}"` : ''}><div class="card-head"><h2>${title}</h2>${hint}</div>${sub ? `<div class="card-sub">${sub}</div>` : ''}${body}</section>`;
  }
  const skeleton = h => `<div class="skeleton" style="height:${h}px;margin-top:10px"></div>`;
  const thumb = (src, alt) => (src ? `<img class="thumb" src="${esc(src)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" width="48" height="36" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'thumb'}))">` : `<span class="thumb"></span>`);
  const ext = (href, label) => `<a class="ext" href="${esc(href)}" target="_blank" rel="noopener" aria-label="${esc(label)}" title="${esc(label)}">${icon('ext')}</a>`;
  const rangeBar = (q, max) => (q ? `<span class="range" aria-hidden="true"><b style="left:${Math.min(100, q[0] / max * 100)}%;width:${Math.max(1, Math.min(100, q[2] / max * 100) - Math.min(100, q[0] / max * 100))}%"></b><i style="left:${Math.min(99, q[1] / max * 100)}%"></i></span>` : '');

  // Sortable, filterable, paginated table
  function dataTable(host, cfg) {
    const ps = cfg.pageSize || 25;
    let q = '', page = 0, sort = cfg.sort || null;
    const fv = {};
    const filters = cfg.filters || [];
    host.innerHTML = html`<div class="tools">
        ${cfg.search !== false ? `<label class="field">${icon('search')}<span class="visually-hidden">${t('search')}</span><input class="input" type="search" placeholder="${t('search')}" data-q></label>` : ''}
        ${filters.map((f, i) => `<label><span class="visually-hidden">${f.label}</span><select class="select" data-f="${i}"><option value="">${f.label} : ${f.allLabel || t('all')}</option>${f.options.map(o => `<option value="${esc(o[0])}">${esc(o[1])}</option>`).join('')}</select></label>`).join('')}
        ${cfg.extraTools || ''}<span class="count" aria-live="polite"></span></div>
      <div class="table-wrap"><table><thead><tr>${cfg.columns.map((c, i) => `<th scope="col" class="${c.num ? 'num' : ''} ${c.hideSm ? 'hide-sm' : ''}">${c.sort ? `<button type="button" data-s="${i}">${c.label}${icon('sort')}</button>` : `<span>${c.label}</span>`}</th>`).join('')}</tr></thead><tbody></tbody></table></div>
      <div class="pager"><span></span><div><button type="button" class="btn" data-p="-1">${t('prev')}</button><button type="button" class="btn" data-p="1">${t('next')}</button></div></div>`;
    const tbody = host.querySelector('tbody'), count = host.querySelector('.count'), pager = host.querySelector('.pager');
    const rows = () => {
      let r = cfg.rows;
      if (q) r = r.filter(row => (row._t ??= fold(cfg.text(row))).includes(q));
      filters.forEach((f, i) => { if (fv[i]) r = r.filter(row => f.test(row, fv[i])); });
      if (sort) {
        const c = cfg.columns[sort.i], m = sort.dir === 'asc' ? 1 : -1;
        r = [...r].sort((a, b) => {
          const x = c.sort(a), y = c.sort(b);
          if (x == null) return 1; if (y == null) return -1;
          return (typeof x === 'string' ? x.localeCompare(y, locale()) : x - y) * m;
        });
      }
      return r;
    };
    const draw = () => {
      const r = rows();
      const pages = Math.max(1, Math.ceil(r.length / ps));
      page = Math.min(page, pages - 1);
      const slice = r.slice(page * ps, page * ps + ps);
      tbody.innerHTML = slice.length
        ? slice.map(row => `<tr>${cfg.columns.map(c => `<td class="${c.num ? 'num' : ''} ${c.cls || ''} ${c.hideSm ? 'hide-sm' : ''}">${c.render(row)}</td>`).join('')}</tr>`).join('')
        : `<tr><td colspan="${cfg.columns.length}" class="empty">${t('noResults')}</td></tr>`;
      count.textContent = `${num(r.length)} ${cfg.unit || ''}`;
      pager.querySelector('span').textContent = r.length ? t('rows', num(page * ps + 1), num(Math.min(r.length, page * ps + ps)), num(r.length)) : '';
      pager.querySelector('[data-p="-1"]').disabled = page === 0;
      pager.querySelector('[data-p="1"]').disabled = page >= pages - 1;
      pager.style.display = r.length > ps ? '' : 'none';
      host.querySelectorAll('th').forEach((th, i) => {
        const b = th.querySelector('button');
        if (!b) return;
        const on = sort && sort.i === i;
        on ? th.setAttribute('aria-sort', sort.dir === 'asc' ? 'ascending' : 'descending') : th.removeAttribute('aria-sort');
        b.querySelector('svg').outerHTML = icon(on ? (sort.dir === 'asc' ? 'asc' : 'desc') : 'sort');
      });
    };
    let timer;
    host.querySelector('[data-q]')?.addEventListener('input', e => { clearTimeout(timer); timer = setTimeout(() => { q = fold(e.target.value.trim()); page = 0; draw(); }, 120); });
    host.querySelectorAll('[data-f]').forEach(s => s.addEventListener('change', () => { fv[s.dataset.f] = s.value; page = 0; draw(); }));
    host.querySelectorAll('[data-s]').forEach(b => b.addEventListener('click', () => {
      const i = +b.dataset.s, c = cfg.columns[i];
      sort = sort && sort.i === i ? { i, dir: sort.dir === 'asc' ? 'desc' : 'asc' } : { i, dir: c.num ? 'desc' : 'asc' };
      page = 0; draw();
    }));
    host.querySelectorAll('[data-p]').forEach(b => b.addEventListener('click', () => { page += +b.dataset.p; draw(); host.scrollIntoView({ block: 'nearest' }); }));
    draw();
    return {
      csv() {
        const cols = cfg.columns.filter(c => c.csv !== false);
        const cell = v => { const s = String(v ?? ''); return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
        return [cols.map(c => cell(c.csvLabel || c.label.replace(/<[^>]+>/g, ''))).join(','), ...rows().map(r => cols.map(c => cell(c.csv ? c.csv(r) : c.sort ? c.sort(r) : '')).join(','))].join('\n');
      },
    };
  }

  function download(name, text) {
    const url = URL.createObjectURL(new Blob(['﻿' + text], { type: 'text/csv;charset=utf-8' }));
    const a = Object.assign(document.createElement('a'), { href: url, download: name });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const sortedOptions = (rows, key, label = v => v) => [...new Set(rows.map(r => r[key]).filter(Boolean))].sort((a, b) => String(label(a)).localeCompare(String(label(b)), locale())).map(v => [v, label(v)]);
  // Filter options for free-text marketplace fields: skip one-off junk values
  const commonOptions = (rows, key, min = 5) => {
    const n = {};
    rows.forEach(r => { if (r[key]) n[r[key]] = (n[r[key]] || 0) + 1; });
    return Object.keys(n).filter(k => n[k] >= min && k.length <= 24).sort((a, b) => a.localeCompare(b, locale())).map(v => [v, v]);
  };

  // Load a column-packed file into a table card body
  async function lazyTable(host, path, build) {
    host.innerHTML = skeleton(320);
    try {
      const rows = unpack(await getJSON(path));
      return build(rows);
    } catch (e) {
      host.innerHTML = `<div class="error" style="margin-top:10px"><span>${t('loadError')} <span class="mu">(${esc(e.message)})</span></span><button class="btn" type="button">${t('retry')}</button></div>`;
      host.querySelector('button').addEventListener('click', () => lazyTable(host, path, build));
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Pages
  // ---------------------------------------------------------------------------
  function pageNew(main) {
    const N = state.data.new, src = state.data.sources.new;
    const S = inPeriod(state.history.new);
    const first = S[0], last = S[S.length - 1];
    const ch = pct(first?.median, last?.median);
    main.innerHTML = html`
      ${header(t('new.title'), `${t('new.sub', num(N.count), num(N.brands))} · ${t('scrapedOn', fdate(src.scraped_at))}`)}
      ${staleNotice(src)}
      <div class="kpis">
        ${kpi(t('new.kMedian'), num(N.median), 'DT', `${fpct(ch)} ${t('since', fdate(first.date, 'short'))}`, dir(ch), S.map(p => p.median))}
        ${kpi(t('new.kTrims'), num(N.count), '', `${last.n - first.n >= 0 ? '+' : '−'}${num(Math.abs(last.n - first.n))} ${t('since', fdate(first.date, 'short'))}`, '', S.map(p => p.n))}
        ${kpi(t('new.kMin'), num(N.min), 'DT', esc(N.cheapest[0].name), '', null, N.cheapest[0].name)}
        ${kpi(t('new.kBrands'), num(N.brands), '', t('new.electrified', num(N.electrified)))}
      </div>
      <div class="row">
        ${card('', t('new.chart'), `<span class="hint">${fdate(first.date)} – ${fdate(last.date)}</span>`, '<div id="c-new"></div>', t('new.chartSub'))}
        ${card('', t('new.budget'), '<span class="hint">DT</span>', bars(N.segments.map(s => [s.hi ? `${axis(s.lo)} – ${axis(s.hi)}` : `${axis(s.lo)} +`, s.n])) + `<h3>${t('new.fuel')}<span class="hint">${t('trims')}</span></h3>` + bars(N.fuel, { soft: true }))}
      </div>
      ${card('t-brands', t('new.brands'), '', '<div id="tb-brands"></div>', t('new.brandsSub'))}
      ${card('t-trims', t('new.all'), '', '<div id="tb-trims"></div>', t('new.allSub'))}`;
    Charts.line(main.querySelector('#c-new'), {
      series: [{ label: t('priceMedian'), color: '#4f46e5', points: S.map(p => [D(p.date), p.median]) }],
      format: (v, ax) => (ax ? axis(v) : dt(v)), dateFormat: fdate, height: 280, label: t('new.chart'), gapDays: 10,
    });
    const maxP = Math.max(...N.brandRange.map(b => b.max));
    const cap = Math.min(maxP, 500000);
    const brands = dataTable(main.querySelector('#tb-brands'), {
      rows: N.brandRange, text: r => r.brand, pageSize: 10, unit: t('col.brand').toLowerCase() + 's', sort: { i: 1, dir: 'desc' },
      columns: [
        { label: t('col.brand'), sort: r => r.brand, render: r => `<b style="font-weight:500">${esc(r.brand)}</b>` },
        { label: t('trims'), num: true, sort: r => r.n, render: r => num(r.n) },
        { label: t('col.from'), num: true, sort: r => r.min, render: r => num(r.min) },
        { label: t('col.median'), num: true, sort: r => r.median, render: r => `<b style="font-weight:600">${num(r.median)}</b>` },
        { label: t('col.max'), num: true, sort: r => r.max, render: r => num(r.max) },
        { label: `${t('col.range')} <span class="mu">0 – ${axis(cap)}</span>`, hideSm: true, csv: false, render: r => rangeBar([r.min, r.median, r.max], cap) },
      ],
    });
    state.exportFn = () => download('prix-par-marque.csv', brands.csv());
    lazyTable(main.querySelector('#tb-trims'), 'data/new_trims.json', rows => {
      const tb = dataTable(main.querySelector('#tb-trims'), {
        rows, text: r => `${r.brand} ${r.model} ${r.trim}`, unit: t('trims'), sort: { i: 6, dir: 'asc' },
        filters: [
          { label: t('f.brand'), options: sortedOptions(rows, 'brand'), test: (r, v) => r.brand === v, allLabel: t('allF') },
          { label: t('f.body'), options: sortedOptions(rows, 'body', tv), test: (r, v) => r.body === v, allLabel: t('allF') },
          { label: t('f.fuel'), options: sortedOptions(rows, 'fuel', tv), test: (r, v) => r.fuel === v, allLabel: t('allF') },
        ],
        columns: [
          { label: t('col.trim'), sort: r => `${r.brand} ${r.model} ${r.trim}`, render: r => `<span class="cell-title">${thumb(r.thumb)}<span><b style="font-weight:500">${esc(r.brand)} ${esc(r.model)}</b><br><span class="mu">${esc(r.trim)}</span></span></span>`, csv: r => `${r.brand} ${r.model} ${r.trim}` },
          { label: t('col.body'), hideSm: true, sort: r => tv(r.body), render: r => esc(tv(r.body)) },
          { label: t('col.fuel'), hideSm: true, sort: r => tv(r.fuel), render: r => esc(tv(r.fuel)) },
          { label: t('col.cv'), num: true, hideSm: true, sort: r => r.cv, render: r => num(r.cv) },
          { label: t('col.hp'), num: true, hideSm: true, sort: r => r.hp, render: r => num(r.hp) },
          { label: '', csv: false, render: r => (r.url ? ext(r.url, 'automobile.tn') : '') },
          { label: t('col.price'), num: true, sort: r => r.price, render: r => `<b style="font-weight:600">${dt(r.price)}</b>` },
        ],
      });
      state.exportFn = () => download('finitions-neuves.csv', tb.csv());
    });
  }

  function pageUsed(main) {
    const U = state.data.used, src = state.data.sources.used;
    const S = inPeriod(state.history.used);
    const first = S[0], last = S[S.length - 1];
    const weekAgo = [...S].reverse().find(p => (D(last.date) - D(p.date)) / 864e5 >= 7) || first;
    const ch = pct(first.median, last.median);
    const q = U.quartiles;
    // Tunisia next to Europe for the model with the most European listings among the top 10
    const cmp = [...U.models.slice(0, 10)].filter(m => m.euMedian).sort((a, b) => b.euN - a.euN)[0] || U.models[0];
    main.innerHTML = html`
      ${header(t('used.title'), `${t('used.sub', num(U.count), num(U.raw))} · ${t('updated', fdate(src.scraped_at))}`)}
      ${staleNotice(src)}
      <div class="kpis">
        ${kpi(t('used.kCount'), num(U.count), '', `+${num(last.n - weekAgo.n)} ${t('in7d')}`, '', S.map(p => p.n))}
        ${kpi(t('used.kMedian'), num(U.median), 'DT', `${fpct(ch)} ${t('since', fdate(first.date, 'short'))}`, dir(ch), S.map(p => p.median))}
        ${kpi(t('used.kKm'), num(U.medianKm), 'km', t('used.year', U.medianYear))}
        ${kpi(t('used.kCompare', cmp.name), num(cmp.quartiles[1]), 'DT', t('used.compareSub', eur(cmp.euMedian), num(cmp.euN)))}
      </div>
      <div class="row">
        ${card('', t('used.chart'), `<div class="seg" role="group" aria-label="${t('used.chart')}"><button type="button" data-m="median" aria-pressed="true">${t('priceMedian')}</button><button type="button" data-m="n" aria-pressed="false">${t('count')}</button></div>`, '<div id="c-used"></div>', t('used.chartSub'))}
        ${card('', t('used.fuel'), `<span class="hint">${t('listings')}</span>`, bars(U.fuel) + `<h3>${t('used.gearbox')}<span class="hint">${t('listings')}</span></h3>` + bars(U.transmission, { soft: true }))}
      </div>
      <div class="row even">
        ${card('', t('used.hist'), '<span class="hint">DT</span>', '<div id="c-hist"></div>', t('used.histSub', q.map(num)))}
        ${card('', t('used.gov'), `<span class="hint">${t('listings')}</span>`, bars(U.governorates, { scroll: true }))}
      </div>
      ${card('', t('used.models'), '', '<div id="tb-models"></div>', t('used.modelsSub'))}
      ${card('', t('used.listings'), '', '<div id="tb-listings"></div>', t('used.listingsSub'))}`;

    const chartHost = main.querySelector('#c-used');
    const drawUsed = m => Charts.line(chartHost, {
      series: [{ label: m === 'n' ? t('count') : t('priceMedian'), color: '#4f46e5', points: S.map(p => [D(p.date), p[m]]) }],
      format: (v, ax) => (m === 'n' ? num(v) : ax ? axis(v) : dt(v)), dateFormat: fdate, height: 280, zero: m === 'n', label: t('used.chart'),
    });
    drawUsed('median');
    main.querySelectorAll('[data-m]').forEach(b => b.addEventListener('click', () => {
      main.querySelectorAll('[data-m]').forEach(x => x.setAttribute('aria-pressed', x === b));
      drawUsed(b.dataset.m);
    }));

    const step = U.hist.step;
    Charts.columns(main.querySelector('#c-hist'), {
      height: 260, format: num, labelEvery: 4, label: t('used.hist'),
      bins: U.hist.counts.map((v, i) => {
        const lo = i * step, hi = lo + step, last = i === U.hist.counts.length - 1;
        const label = last ? `${axis(lo)} +` : `${axis(lo)} – ${axis(hi)}`;
        return { value: v, short: axis(lo), label, hi: hi > q[0] && lo <= q[2], tip: `<div class="tip-date">${label} DT</div><div class="tip-row">${t('listings')}<b>${num(v)}</b></div><div class="tip-row">${t('share')}<b>${Math.round(v / U.count * 100)} %</b></div>` };
      }),
    });

    const models = U.models.map(m => {
      const pts = S.map(p => p.models?.[m.name]).filter(v => v != null);
      return { ...m, trend: pts.length > 1 ? pct(pts[0], pts[pts.length - 1]) : null, spark: pts };
    });
    const mt = dataTable(main.querySelector('#tb-models'), {
      rows: models, text: r => r.name, pageSize: 10, unit: t('models'), sort: { i: 1, dir: 'desc' },
      columns: [
        { label: t('col.model'), sort: r => r.name, render: r => `<b style="font-weight:500">${esc(r.name)}</b>` },
        { label: t('col.count'), num: true, sort: r => r.n, render: r => num(r.n) },
        { label: t('col.tn'), num: true, sort: r => r.quartiles?.[1], render: r => `<b style="font-weight:600">${dt(r.quartiles?.[1])}</b>` },
        { label: t('col.iqr'), hideSm: true, csv: r => r.quartiles ? `${r.quartiles[0]}-${r.quartiles[2]}` : '', render: r => `${rangeBar(r.quartiles, 150000)} <span class="mu" style="margin-left:8px">${axis(r.quartiles?.[0])}–${axis(r.quartiles?.[2])}</span>` },
        { label: t('col.eu'), num: true, sort: r => r.euMedian, render: r => (r.euMedian ? `${eur(r.euMedian)} <span class="mu">· ${r.euN}</span>` : '<span class="mu">–</span>') },
        { label: t('col.trend'), num: true, hideSm: true, sort: r => r.trend, render: r => (r.trend == null ? '<span class="mu">–</span>' : `<span class="tag ${dir(r.trend)}">${fpct(r.trend)}</span>`) },
      ],
    });
    state.exportFn = () => download('modeles-occasion.csv', mt.csv());

    lazyTable(main.querySelector('#tb-listings'), 'data/used_listings.json', rows => {
      const lt = dataTable(main.querySelector('#tb-listings'), {
        rows, text: r => `${r.title} ${r.brand} ${r.model} ${r.gov}`, unit: t('listings'),
        filters: [
          { label: t('f.brand'), options: commonOptions(rows, 'brand'), test: (r, v) => r.brand === v, allLabel: t('allF') },
          { label: t('f.gov'), options: commonOptions(rows, 'gov'), test: (r, v) => r.gov === v },
          { label: t('f.maxPrice'), options: [20000, 30000, 50000, 80000, 120000].map(v => [v, dt(v)]), test: (r, v) => r.price <= +v },
          { label: t('f.minYear'), options: [2010, 2015, 2018, 2020, 2022].map(v => [v, String(v)]), test: (r, v) => r.year >= +v, allLabel: t('allF') },
        ],
        columns: [
          { label: t('col.listing'), sort: r => r.title, render: r => `<span class="cell-title">${thumb(r.thumb)}<span>${esc(r.title)}</span></span>`, csv: r => r.title },
          { label: t('col.year'), num: true, sort: r => r.year, render: r => r.year },
          { label: t('col.km'), num: true, hideSm: true, sort: r => r.km, render: r => num(r.km) },
          { label: t('col.gov'), hideSm: true, sort: r => r.gov, render: r => esc(r.gov || '–') },
          { label: t('col.fuel'), hideSm: true, sort: r => tv(r.fuel), render: r => esc(tv(r.fuel)) },
          { label: '', csv: r => `https://9annas.tn/ad/${r.id}`, csvLabel: 'url', render: r => ext(`https://9annas.tn/ad/${r.id}`, t('open')) },
          { label: t('col.price'), num: true, sort: r => r.price, render: r => `<b style="font-weight:600">${dt(r.price)}</b>` },
        ],
      });
      state.exportFn = () => download('annonces-occasion.csv', lt.csv());
    });
  }

  function pageEU(main) {
    const E = state.data.eu, src = state.data.sources.eu;
    const S = inPeriod(state.history.eu);
    const first = S[0], last = S[S.length - 1];
    const ch = pct(first.median, last.median);
    const cheapest = [...E.countries].sort((a, b) => a.quartiles[1] - b.quartiles[1])[0];
    // Indigo / sky / slate only: green and amber already mean price direction and stale data
    const colors = { de: '#4f46e5', fr: '#0ea5e9', it: '#1e293b', be: '#94a3b8' };
    const hidden = new Set();
    main.innerHTML = html`
      ${header(t('eu.title'), `${t('eu.sub', num(E.count))} · ${t('updated', fdate(src.scraped_at))}`)}
      ${staleNotice(src)}
      <div class="kpis">
        ${kpi(t('eu.kCount'), num(E.count), '', `4 ${t('countries')}`)}
        ${kpi(t('eu.kMedian'), state.lang === 'fr' ? num(E.median) : '€' + num(E.median), state.lang === 'fr' ? '€' : '', `${fpct(ch)} ${t('since', fdate(first.date, 'short'))}`, dir(ch), S.map(p => p.median))}
        ${kpi(t('eu.kKm'), num(E.medianKm), 'km', t('used.year', E.medianYear))}
        ${kpi(t('eu.kCheapest'), tv(cheapest.code), '', `${t('median')} ${eur(cheapest.quartiles[1])}`)}
      </div>
      <div class="row">
        ${card('', t('eu.chart'), '<div class="legend" id="lg"></div>', '<div id="c-eu"></div>', t('eu.chartSub'))}
        ${card('', t('eu.byCountry'), `<span class="hint">${t('col.iqr')}</span>`, `<div class="bars">${E.countries.map(c => `<div class="bar" style="grid-template-columns:minmax(80px,100px) minmax(0,1fr) 72px"><span class="bar-label"><i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${colors[c.code]};margin-right:7px"></i>${tv(c.code)}</span>${rangeBar(c.quartiles, 80000).replace('class="range"', 'class="range" style="width:100%"')}<span class="bar-value">${eur(c.quartiles[1])}</span></div><div class="card-sub" style="margin:-4px 0 6px">${num(c.n)} ${t('listings')} · ${eur(c.quartiles[0])} – ${eur(c.quartiles[2])}</div>`).join('')}</div>` + `<h3>${t('f.fuel')}<span class="hint">${t('listings')}</span></h3>` + bars(E.fuel.slice(0, 5), { soft: true }))}
      </div>
      <div class="row even">
        ${card('', t('eu.hist'), '<span class="hint">€</span>', '<div id="c-euh"></div>', t('eu.histSub'))}
        ${card('', t('eu.makes'), `<span class="hint">${t('listings')}</span>`, bars(E.makes, { total: E.count, scroll: true }))}
      </div>
      ${card('', t('eu.listings'), '', '<div id="tb-eu"></div>', t('eu.listingsSub'))}`;

    const lg = main.querySelector('#lg');
    const drawEU = () => Charts.line(main.querySelector('#c-eu'), {
      series: ['de', 'fr', 'it', 'be'].map(k => ({ label: tv(k), color: colors[k], hidden: hidden.has(k), points: S.filter(p => p.countries?.[k]).map(p => [D(p.date), p.countries[k]]) })),
      format: (v, ax) => (ax ? axis(v, '€') : eur(v)), dateFormat: fdate, height: 280, area: false, label: t('eu.chart'),
    });
    lg.innerHTML = ['de', 'fr', 'it', 'be'].map(k => `<button type="button" data-c="${k}" aria-pressed="true"><i style="background:${colors[k]}"></i>${tv(k)}</button>`).join('');
    lg.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
      const k = b.dataset.c;
      if (hidden.has(k)) hidden.delete(k); else if (hidden.size < 3) hidden.add(k);
      b.setAttribute('aria-pressed', !hidden.has(k));
      drawEU();
    }));
    drawEU();

    const step = E.hist.step;
    Charts.columns(main.querySelector('#c-euh'), {
      height: 260, format: num, labelEvery: 4, label: t('eu.hist'),
      bins: E.hist.counts.map((v, i) => {
        const lo = i * step, last = i === E.hist.counts.length - 1;
        const label = last ? `${axis(lo, '€')} +` : `${axis(lo, '€')} – ${axis(lo + step, '€')}`;
        return { value: v, short: axis(lo), label, hi: lo + step > E.quartiles[0] && lo <= E.quartiles[2], tip: `<div class="tip-date">${label}</div><div class="tip-row">${t('listings')}<b>${num(v)}</b></div><div class="tip-row">${t('share')}<b>${Math.round(v / E.count * 100)} %</b></div>` };
      }),
    });

    lazyTable(main.querySelector('#tb-eu'), 'data/eu_listings.json', rows => {
      const et = dataTable(main.querySelector('#tb-eu'), {
        rows, text: r => `${r.title} ${r.make} ${r.model}`, unit: t('listings'),
        filters: [
          { label: t('f.country'), options: ['de', 'fr', 'it', 'be'].map(k => [k, tv(k)]), test: (r, v) => r.country === v },
          { label: t('f.brand'), options: sortedOptions(rows, 'make'), test: (r, v) => r.make === v, allLabel: t('allF') },
          { label: t('f.fuel'), options: sortedOptions(rows, 'fuel', tv), test: (r, v) => r.fuel === v, allLabel: t('allF') },
        ],
        columns: [
          { label: t('col.listing'), sort: r => r.title, render: r => `<span class="cell-title">${thumb(r.thumb)}<span>${esc(r.title)}</span></span>`, csv: r => r.title },
          { label: t('col.country'), sort: r => tv(r.country), render: r => `<span class="tag">${esc(String(r.country).toUpperCase())}</span>`, csv: r => r.country },
          { label: t('col.year'), num: true, sort: r => r.year, render: r => r.year ?? '–' },
          { label: t('col.km'), num: true, hideSm: true, sort: r => r.km, render: r => num(r.km) },
          { label: t('col.hp'), num: true, hideSm: true, sort: r => r.hp, render: r => num(r.hp) },
          { label: t('col.fuel'), hideSm: true, sort: r => tv(r.fuel), render: r => esc(tv(r.fuel)) },
          { label: '', csv: r => r.url, csvLabel: 'url', render: r => (r.url ? ext(r.url, t('open')) : '') },
          { label: t('col.price'), num: true, sort: r => r.price, render: r => `<b style="font-weight:600">${eur(r.price)}</b>` },
        ],
      });
      state.exportFn = () => download('annonces-europe.csv', et.csv());
    });
  }

  function pageHistory(main) {
    const C = state.data.catalog, src = state.data.sources.new;
    const E = C.entries;
    const drops = E.reduce((a, e) => a + e.price_drops, 0), rises = E.reduce((a, e) => a + e.price_increases, 0);
    const byBrand = {};
    C.priceChanges.forEach(c => { byBrand[c.brand] = (byBrand[c.brand] || 0) + 1; });
    main.innerHTML = html`
      ${header(t('hist.title'), `${t('hist.sub', num(E.length))} · ${fdate(E[0].date)} – ${fdate(E[E.length - 1].date)}`, { period: false })}
      ${staleNotice(src)}
      <div class="kpis">
        ${kpi(t('hist.kScrapes'), num(E.length), '', `${fdate(E[0].date)} – ${fdate(E[E.length - 1].date)}`)}
        ${kpi(t('hist.kSize'), num(E[E.length - 1].total_after), t('trims'), `${E[E.length - 1].total_after - E[0].total_before >= 0 ? '+' : '−'}${num(Math.abs(E[E.length - 1].total_after - E[0].total_before))} ${t('since', fdate(E[0].date))}`, '', E.map(e => e.total_after))}
        ${kpi(t('hist.kDrops'), num(drops), '', `${num(C.priceChanges.filter(c => c.pct < 0).length)} ${t('trims')}`, 'down')}
        ${kpi(t('hist.kRises'), num(rises), '', `${num(C.priceChanges.filter(c => c.pct > 0).length)} ${t('trims')}`, 'up')}
      </div>
      <div class="row">
        ${card('', t('hist.chart'), `<div class="legend"><span class="tag up">${t('hist.rises')}</span><span class="tag down">${t('hist.drops')}</span></div>`, '<div id="c-div"></div>', t('hist.chartSub'))}
        ${card('', t('hist.brands'), `<span class="hint">${t('hist.brandsSub')}</span>`, bars(Object.entries(byBrand).sort((a, b) => b[1] - a[1]), { scroll: true }))}
      </div>
      ${card('', t('hist.changes'), '', '<div id="tb-changes"></div>')}
      ${card('', t('hist.catalog'), `<div class="tabs" role="tablist"><button type="button" role="tab" data-tab="added" aria-selected="true">${t('hist.added')} · ${num(C.added.length)}</button><button type="button" role="tab" data-tab="removed" aria-selected="false">${t('hist.removed')} · ${num(C.removed.length)}</button></div>`, '<div id="tb-catalog"></div>')}`;

    Charts.diverging(main.querySelector('#c-div'), {
      height: 280, label: t('hist.chart'),
      items: E.map(e => ({ up: e.price_increases, down: e.price_drops, short: fdate(e.date, 'short'),
        tip: `<div class="tip-date">${fdate(e.date)}</div><div class="tip-row"><i style="background:#dc2626"></i>${t('type.rises')}<b>${num(e.price_increases)}</b></div><div class="tip-row"><i style="background:#047857"></i>${t('type.drops')}<b>${num(e.price_drops)}</b></div><div class="tip-row">${t('trims')}<b>${num(e.total_after)}</b></div>` })),
    });
    const brands = sortedOptions(C.priceChanges, 'brand');
    const ct = dataTable(main.querySelector('#tb-changes'), {
      rows: C.priceChanges, text: r => r.name, unit: '', sort: { i: 0, dir: 'desc' },
      filters: [
        { label: t('f.type'), options: [['drops', t('type.drops')], ['rises', t('type.rises')]], test: (r, v) => (v === 'drops' ? r.pct < 0 : r.pct > 0) },
        { label: t('f.brand'), options: brands, test: (r, v) => r.brand === v, allLabel: t('allF') },
      ],
      columns: [
        { label: t('col.date'), sort: r => r.date, render: r => `<span class="mu">${fdate(r.date)}</span>` },
        { label: t('col.trim'), sort: r => r.name, render: r => esc(r.name) },
        { label: t('col.old'), num: true, hideSm: true, sort: r => r.old, render: r => `<span class="mu">${num(r.old)}</span>` },
        { label: t('col.new'), num: true, sort: r => r.new, render: r => `<b style="font-weight:600">${num(r.new)}</b>` },
        { label: t('col.change'), num: true, sort: r => r.pct, render: r => `<span class="tag ${dir(r.pct)}">${fpct(r.pct)}</span>` },
      ],
    });
    state.exportFn = () => download('changements-prix.csv', ct.csv());

    const drawCat = which => dataTable(main.querySelector('#tb-catalog'), {
      rows: C[which], text: r => r.name, unit: t('trims'), pageSize: 10, sort: { i: 0, dir: 'desc' },
      columns: [
        { label: t('col.date'), sort: r => r.date, render: r => `<span class="mu">${fdate(r.date)}</span>` },
        { label: t('col.trim'), sort: r => r.name, render: r => esc(r.name) },
        { label: t('col.price'), num: true, sort: r => r.price, render: r => `<b style="font-weight:600">${dt(r.price)}</b>` },
      ],
    });
    drawCat('added');
    main.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => {
      main.querySelectorAll('[data-tab]').forEach(x => x.setAttribute('aria-selected', x === b));
      drawCat(b.dataset.tab);
    }));
  }

  const PAGES = { neuf: pageNew, occasion: pageUsed, europe: pageEU, historique: pageHistory };
  const TITLES = { neuf: 'new.title', occasion: 'used.title', europe: 'eu.title', historique: 'hist.title' };

  // ---------------------------------------------------------------------------
  // Render + boot
  // ---------------------------------------------------------------------------
  function render() {
    renderShell();
    const main = document.getElementById('main');
    const id = route();
    document.title = `${t(TITLES[id])} · ${t('brand')}`;
    state.exportFn = null;
    PAGES[id](main);
    main.querySelectorAll('[data-period]').forEach(b => b.addEventListener('click', () => {
      state.period = b.dataset.period;
      store.set('period', state.period);
      render();
    }));
    main.querySelector('#export')?.addEventListener('click', () => state.exportFn && state.exportFn());
  }

  async function boot() {
    renderShell();
    const main = document.getElementById('main');
    main.innerHTML = `<div class="head"><div class="head-text"><h1>${t('loading')}</h1></div></div><div class="kpis">${`<div class="kpi">${skeleton(52)}</div>`.repeat(4)}</div>${skeleton(300)}`;
    try {
      [state.data, state.history] = await Promise.all([getJSON('data/dashboard.json'), getJSON('data/history.json')]);
    } catch (e) {
      main.innerHTML = `<div class="error"><span>${t('loadError')} <span class="mu">(${esc(e.message)})</span></span><button class="btn" type="button">${t('retry')}</button></div>`;
      main.querySelector('button').addEventListener('click', boot);
      return;
    }
    render();
  }

  window.addEventListener('hashchange', () => {
    if (!state.data) return;
    render();
    window.scrollTo(0, 0);
    document.getElementById('main')?.focus({ preventScroll: true });
  });
  boot();
})();
