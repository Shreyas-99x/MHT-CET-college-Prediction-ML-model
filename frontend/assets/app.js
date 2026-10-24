/* ======================================================================
   MHT CET College Predictor — Redesigned Frontend Logic
   Handles API calls, card rendering, tab management, and animations
   ====================================================================== */

const API_BASE = '';

// State
let allPredictions = [];
let top20ShowcaseData = [];
let predictFiltered = [];
let optionFiltered = [];

let predictPage = 1;
let predictPageSize = 12;
let optionPage = 1;
let optionPageSize = 25;

let activeAbortController = null;
let debounceTimer = null;

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    initControls();
    initTabs();
    initPagination();
    initScrollEffects();
    initNavHighlight();
    fetchStats();
    fetchFilterOptions().then(() => {
        const pct = parseFloat(document.getElementById('percentileInput').value) || 92.5;
        updateRankEst(pct);
        fetchPredictions();
    });
});

// ===== UTILITIES =====
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function getChanceClass(tag) {
    const s = String(tag || '');
    if (s.includes('High') || s.includes('Safe')) return 'safe';
    if (s.includes('Moderate') || s.includes('Target')) return 'target';
    return 'dream';
}

// ===== SCROLL & NAV EFFECTS =====
function initScrollEffects() {
    const nav = document.getElementById('mainNav');
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        },
        { threshold: 0.1 }
    );

    // Observe animatable elements
    document.querySelectorAll('.stat-card, .bento-card, .college-card, .pred-card').forEach(el => {
        observer.observe(el);
    });

    window.addEventListener('scroll', () => {
        if (window.scrollY > 20) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });
}

function initNavHighlight() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav__link');

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    navLinks.forEach(link => {
                        link.classList.remove('active');
                        if (link.getAttribute('href') === '#' + entry.target.id) {
                            link.classList.add('active');
                        }
                    });
                }
            });
        },
        { rootMargin: '-40% 0px -60% 0px' }
    );

    sections.forEach(section => observer.observe(section));
}

// ===== CONTROLS =====
function initControls() {
    const slider = document.getElementById('percentileSlider');
    const input = document.getElementById('percentileInput');

    slider.addEventListener('input', (e) => {
        let val = parseFloat(e.target.value);
        if (isNaN(val)) val = 92.5;
        val = Math.max(0, Math.min(100, val));
        input.value = val.toFixed(2);
        updateRankEst(val);
        fetchPredictionsDebounced();
    });

    input.addEventListener('input', (e) => {
        let val = parseFloat(e.target.value);
        if (isNaN(val)) val = 0;
        val = Math.max(0, Math.min(100, val));
        slider.value = val;
        updateRankEst(val);
        fetchPredictionsDebounced();
    });

    const controlIds = [
        'categorySelect', 'genderSelect', 'quotaSelect', 'capRoundSelect',
        'districtSelect', 'branchSelect', 'top20OnlyToggle', 'prioritizeTop20Toggle'
    ];
    controlIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', fetchPredictionsDebounced);
    });

    document.getElementById('btnPredict').addEventListener('click', fetchPredictions);
    document.getElementById('searchTop20').addEventListener('input', filterTop20Cards);
    document.getElementById('searchPredict').addEventListener('input', () => {
        predictPage = 1;
        applyPredictFilters();
    });
    document.getElementById('btnExportCsv').addEventListener('click', exportPredictCsv);
    document.getElementById('btnDownloadOptionCsv').addEventListener('click', exportOptionCsv);
}

function updateRankEst(pct) {
    pct = parseFloat(pct);
    if (isNaN(pct)) pct = 92.5;
    pct = Math.max(0.0, Math.min(100.0, pct));

    document.getElementById('kpiPercentile').innerText = `${pct.toFixed(2)}%`;

    let estRank = 1;
    if (pct >= 99.9) estRank = Math.round(1 + (100 - pct) * 10000);
    else if (pct >= 99.0) estRank = Math.round(1020 + (99.9 - pct) * 2058);
    else if (pct >= 95.0) estRank = Math.round(2873 + (99.0 - pct) * 3250);
    else if (pct >= 90.0) estRank = Math.round(15874 + (95.0 - pct) * 2950);
    else if (pct >= 80.0) estRank = Math.round(30623 + (90.0 - pct) * 2818);
    else if (pct >= 50.0) estRank = Math.round(58800 + (80.0 - pct) * 2130);
    else estRank = Math.round(122713 + (50.0 - pct) * 1000);

    const el = document.getElementById('estRankValue');
    if (el) el.innerText = estRank.toLocaleString();
}

// ===== TABS =====
function initTabs() {
    const tabs = document.querySelectorAll('.result-tab');
    const panels = document.querySelectorAll('.tab-panel');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            panels.forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            const target = document.getElementById(tab.dataset.tab);
            if (target) target.classList.add('active');
        });
    });
}

// ===== PAGINATION =====
function initPagination() {
    document.getElementById('btnPredictPrev').addEventListener('click', () => {
        if (predictPage > 1) { predictPage--; renderPredictionCards(); }
    });
    document.getElementById('btnPredictNext').addEventListener('click', () => {
        const total = Math.ceil(predictFiltered.length / predictPageSize) || 1;
        if (predictPage < total) { predictPage++; renderPredictionCards(); }
    });
    document.getElementById('predictPageSize').addEventListener('change', (e) => {
        predictPageSize = parseInt(e.target.value) || 12;
        predictPage = 1;
        renderPredictionCards();
    });

    document.getElementById('btnOptionPrev').addEventListener('click', () => {
        if (optionPage > 1) { optionPage--; renderOptionForm(); }
    });
    document.getElementById('btnOptionNext').addEventListener('click', () => {
        const total = Math.ceil(optionFiltered.length / optionPageSize) || 1;
        if (optionPage < total) { optionPage++; renderOptionForm(); }
    });
    document.getElementById('optionPageSize').addEventListener('change', (e) => {
        optionPageSize = parseInt(e.target.value) || 25;
        optionPage = 1;
        renderOptionForm();
    });
}

// ===== API CALLS =====
async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.success) {
            const colEl = document.getElementById('statColleges');
            const brEl = document.getElementById('statBranches');
            const distEl = document.getElementById('statDistricts');
            if (colEl) colEl.innerText = (data.total_colleges || 500) + '+';
            if (brEl) brEl.innerText = data.total_branches || 98;
            if (distEl) distEl.innerText = data.total_districts || 30;
        }
    } catch (err) {
        console.warn('Could not fetch stats:', err);
    }
}

async function fetchFilterOptions() {
    try {
        const res = await fetch(`${API_BASE}/api/options`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.success && data.options) {
            populateSelect('districtSelect', data.options.districts, 'All Districts');
            populateSelect('branchSelect', data.options.courses, 'All Branches');
            populateSelect('categorySelect', data.options.category_groups, 'All Categories', 'OPEN');
        }
    } catch (err) {
        console.warn('Could not fetch options:', err);
        populateSelect('districtSelect', ['Pune', 'Mumbai', 'Sangli'], 'All Districts');
        populateSelect('branchSelect', ['Computer Engineering', 'Information Technology', 'AI & Data Science'], 'All Branches');
    }
}

function populateSelect(id, items, allLabel, defaultVal) {
    const sel = document.getElementById(id);
    if (!sel || !items) return;
    sel.innerHTML = '';

    if (allLabel) {
        const opt = document.createElement('option');
        opt.value = 'ALL';
        opt.textContent = allLabel;
        opt.selected = !defaultVal || defaultVal === 'ALL';
        sel.appendChild(opt);
    }

    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = item;
        if (defaultVal && item === defaultVal) opt.selected = true;
        sel.appendChild(opt);
    });
}

function fetchPredictionsDebounced() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchPredictions, 300);
}

async function fetchPredictions() {
    if (activeAbortController) activeAbortController.abort();
    activeAbortController = new AbortController();

    const pctInput = parseFloat(document.getElementById('percentileInput').value);
    const pct = isNaN(pctInput) ? 92.5 : Math.max(0, Math.min(100, pctInput));

    const payload = {
        percentile: pct,
        category_group: document.getElementById('categorySelect').value,
        gender_quota: document.getElementById('genderSelect').value,
        university_quota: document.getElementById('quotaSelect').value,
        cap_round: document.getElementById('capRoundSelect').value,
        districts: [document.getElementById('districtSelect').value],
        branches: [document.getElementById('branchSelect').value],
        top_20_only: document.getElementById('top20OnlyToggle').checked,
        prioritize_top_20: document.getElementById('prioritizeTop20Toggle').checked,
    };

    // Show loading
    document.getElementById('loadingState').style.display = 'block';
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('predictionsGrid').innerHTML = '';

    try {
        const res = await fetch(`${API_BASE}/api/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: activeAbortController.signal,
        });

        if (!res.ok) throw new Error(`Server error ${res.status}`);
        const data = await res.json();

        document.getElementById('loadingState').style.display = 'none';

        if (data.success) {
            showErrorBanner(null);
            allPredictions = data.predictions || [];
            top20ShowcaseData = data.top_20_showcase || [];

            if (data.calculated_rank) {
                document.getElementById('estRankValue').innerText = data.calculated_rank.toLocaleString();
            }

            renderTop20Cards(top20ShowcaseData);
            applyPredictFilters();
            updateKpis(allPredictions);
        } else {
            showErrorBanner(data.error || 'Prediction failed');
        }
    } catch (err) {
        document.getElementById('loadingState').style.display = 'none';
        if (err.name === 'AbortError') return;
        console.error('API Error:', err);
        showErrorBanner('Server offline — showing fallback data.');
        runOfflineFallback(pct);
    }
}

function showErrorBanner(msg) {
    const banner = document.getElementById('errorBanner');
    if (!banner) return;
    if (msg) {
        banner.innerHTML = `<span>⚠️ ${escapeHtml(msg)}</span><span class="close-btn" onclick="showErrorBanner(null)">✕</span>`;
        banner.style.display = 'flex';
    } else {
        banner.style.display = 'none';
    }
}

// ===== KPI UPDATE =====
function updateKpis(items) {
    const top20 = items.filter(i => i['Is Top 20']).length;
    const safe = items.filter(i => getChanceClass(i['Chance Tag']) === 'safe').length;
    const target = items.filter(i => getChanceClass(i['Chance Tag']) === 'target').length;
    const dream = items.filter(i => getChanceClass(i['Chance Tag']) === 'dream').length;

    animateNumber('kpiTop20', top20);
    animateNumber('kpiSafe', safe);
    animateNumber('kpiTarget', target);
    animateNumber('kpiDream', dream);
}

function animateNumber(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const start = parseInt(el.innerText) || 0;
    const diff = target - start;
    const duration = 400;
    const startTime = performance.now();

    function step(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        el.innerText = Math.round(start + diff * eased);
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// ===== RENDER TOP 20 CARDS =====
function renderTop20Cards(items) {
    const grid = document.getElementById('top20Grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (!items || items.length === 0) {
        grid.innerHTML = '<p style="text-align:center; color:#a09a93; grid-column:1/-1; padding:40px;">No Top 20 data available.</p>';
        return;
    }

    items.forEach((item, idx) => {
        const chanceClass = getChanceClass(item['Your Admission Chance (CSE)'] || '');
        const chanceLabel = item['Your Admission Chance (CSE)'] || '—';

        const cseCutoff = item['CSE Cutoff (%ile)'];
        const itCutoff = item['IT Cutoff (%ile)'];
        const cseStr = typeof cseCutoff === 'number' ? cseCutoff.toFixed(2) + '%' : 'N/A';
        const itStr = typeof itCutoff === 'number' ? itCutoff.toFixed(2) + '%' : 'N/A';

        const card = document.createElement('div');
        card.className = 'college-card animate-in';
        card.style.animationDelay = `${idx * 0.06}s`;
        card.innerHTML = `
            <div class="college-card__rank">#${item.Rank}</div>
            <h3 class="college-card__name">${escapeHtml(item['Short Name'])}</h3>
            <p class="college-card__full-name">${escapeHtml(item['Full Name'])}</p>
            <div class="college-card__info">
                <span class="college-card__tag">📍 ${escapeHtml(item['City / District'])}</span>
                <span class="college-card__tag">🏛️ ${escapeHtml(item.Status || '')}</span>
                <span class="college-card__tag">Code: ${escapeHtml(item.Code)}</span>
            </div>
            <div class="college-card__cutoffs">
                <div class="cutoff-item">
                    <div class="cutoff-item__label">CSE Cutoff</div>
                    <div class="cutoff-item__value">${cseStr}</div>
                </div>
                <div class="cutoff-item">
                    <div class="cutoff-item__label">IT Cutoff</div>
                    <div class="cutoff-item__value">${itStr}</div>
                </div>
            </div>
            <div class="college-card__chance">
                <span class="badge badge--${chanceClass}">${escapeHtml(chanceLabel)}</span>
            </div>
        `;
        grid.appendChild(card);
    });
}

function filterTop20Cards() {
    const query = (document.getElementById('searchTop20').value || '').toLowerCase();
    const cards = document.querySelectorAll('#top20Grid .college-card');
    cards.forEach(card => {
        card.style.display = card.innerText.toLowerCase().includes(query) ? '' : 'none';
    });
}

// ===== RENDER PREDICTION CARDS =====
function applyPredictFilters() {
    const query = (document.getElementById('searchPredict').value || '').toLowerCase().trim();

    predictFiltered = allPredictions.filter(item => {
        if (!query) return true;
        return (
            String(item['College Name'] || '').toLowerCase().includes(query) ||
            String(item['College Code'] || '').toLowerCase().includes(query) ||
            String(item['Course'] || '').toLowerCase().includes(query) ||
            String(item['District'] || '').toLowerCase().includes(query)
        );
    });

    renderPredictionCards();

    // Build option form
    const prioritize = document.getElementById('prioritizeTop20Toggle').checked;
    optionFiltered = [...allPredictions].sort((a, b) => {
        if (prioritize) {
            if (a['Is Top 20'] !== b['Is Top 20']) return b['Is Top 20'] ? 1 : -1;
            if (a['Is Top 20'] && b['Is Top 20']) return (a['Top 20 Rank'] || 99) - (b['Top 20 Rank'] || 99);
        }
        return (b['Weighted Cutoff Percentile'] || 0) - (a['Weighted Cutoff Percentile'] || 0);
    });
    renderOptionForm();
}

function renderPredictionCards() {
    const grid = document.getElementById('predictionsGrid');
    if (!grid) return;

    const total = predictFiltered.length;
    const totalPages = Math.ceil(total / predictPageSize) || 1;
    predictPage = Math.max(1, Math.min(predictPage, totalPages));
    document.getElementById('predictPageInfo').innerText = `Page ${predictPage} of ${totalPages} (${total} results)`;

    // Show/hide empty state
    const emptyEl = document.getElementById('emptyState');
    if (total === 0) {
        grid.innerHTML = '';
        if (emptyEl) emptyEl.style.display = 'block';
        return;
    }
    if (emptyEl) emptyEl.style.display = 'none';

    const start = (predictPage - 1) * predictPageSize;
    const items = predictFiltered.slice(start, start + predictPageSize);

    grid.innerHTML = '';
    items.forEach((item, idx) => {
        const chanceClass = getChanceClass(item['Chance Tag']);
        const prob = Number(item['Admission Probability'] || 0);
        const isTop20 = item['Is Top 20'];

        const card = document.createElement('div');
        card.className = `pred-card animate-in ${isTop20 ? 'pred-card--top20' : ''}`;
        card.style.animationDelay = `${idx * 0.04}s`;

        card.innerHTML = `
            <div class="pred-card__header">
                <span class="pred-card__name">${escapeHtml(item['College Name'])}</span>
                <span class="pred-card__code">${escapeHtml(item['College Code'])}</span>
            </div>
            <div class="pred-card__course">${escapeHtml(item['Course'])}</div>
            <div class="pred-card__meta">
                <span>📍 ${escapeHtml(item['District'])}</span>
                <span>📂 ${escapeHtml(item['Category'])}</span>
                ${isTop20 ? `<span class="badge badge--gold">🏆 #${item['Top 20 Rank']}</span>` : ''}
            </div>
            <div class="pred-card__footer">
                <div class="pred-card__prob">
                    ${prob.toFixed(1)}%
                    <small>Admission Prob.</small>
                </div>
                <span class="badge badge--${chanceClass}">${escapeHtml(item['Chance Tag'])}</span>
            </div>
            <div class="prob-bar">
                <div class="prob-bar__fill prob-bar__fill--${chanceClass}" style="width:${prob}%"></div>
            </div>
        `;
        grid.appendChild(card);
    });
}

// ===== RENDER OPTION TABLE =====
function renderOptionForm() {
    const tbody = document.getElementById('optionTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const total = optionFiltered.length;
    const totalPages = Math.ceil(total / optionPageSize) || 1;
    optionPage = Math.max(1, Math.min(optionPage, totalPages));
    document.getElementById('optionPageInfo').innerText = `Page ${optionPage} of ${totalPages} (${total} items)`;

    if (total === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#a09a93; padding:24px;">No preference options available.</td></tr>';
        return;
    }

    const start = (optionPage - 1) * optionPageSize;
    const items = optionFiltered.slice(start, start + optionPageSize);

    items.forEach((item, idx) => {
        const prefNum = start + idx + 1;
        const chanceClass = getChanceClass(item['Chance Tag']);
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>#${prefNum}</strong></td>
            <td>${item['Is Top 20'] ? `<span class="badge badge--gold">🏆 #${item['Top 20 Rank']}</span>` : '<span class="badge badge--tier">Standard</span>'}</td>
            <td><code>${escapeHtml(item['College Code'])}</code></td>
            <td><strong>${escapeHtml(item['College Name'])}</strong></td>
            <td>${escapeHtml(item['Course'])}</td>
            <td>${Number(item['Weighted Cutoff Percentile'] || 0).toFixed(2)}%</td>
            <td><span class="badge badge--${chanceClass}">${escapeHtml(item['Chance Tag'])}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// ===== EXPORT CSV =====
function exportPredictCsv() {
    if (!allPredictions || allPredictions.length === 0) {
        alert('No prediction data to export.');
        return;
    }

    const headers = ['College Code', 'College Name', 'Course', 'Category', 'District',
        'Admission Probability (%)', 'Chance Tag', 'Latest Cutoff Percentile',
        'Is Top 20', 'Top 20 Rank'];

    const rows = [headers.join(',')];
    allPredictions.forEach(item => {
        rows.push([
            `"${item['College Code'] || ''}"`,
            `"${String(item['College Name'] || '').replace(/"/g, '""')}"`,
            `"${String(item['Course'] || '').replace(/"/g, '""')}"`,
            `"${item['Category'] || ''}"`,
            `"${item['District'] || ''}"`,
            `"${item['Admission Probability'] || 0}"`,
            `"${item['Chance Tag'] || ''}"`,
            `"${item['Latest Cutoff Percentile'] || ''}"`,
            `"${item['Is Top 20'] ? 'YES' : 'NO'}"`,
            `"${item['Top 20 Rank'] || ''}"`
        ].join(','));
    });

    downloadCsv(rows.join('\n'), `CETPredict_Results_${document.getElementById('percentileInput').value}pct.csv`);
}

function exportOptionCsv() {
    if (!optionFiltered || optionFiltered.length === 0) {
        alert('No preference data to export.');
        return;
    }

    const headers = ['Preference No', 'College Code', 'College Name', 'Course',
        'Category', 'District', 'Cutoff %', 'Chance', 'Top 20'];

    const rows = [headers.join(',')];
    optionFiltered.forEach((item, idx) => {
        rows.push([
            `"${idx + 1}"`,
            `"${item['College Code'] || ''}"`,
            `"${String(item['College Name'] || '').replace(/"/g, '""')}"`,
            `"${String(item['Course'] || '').replace(/"/g, '""')}"`,
            `"${item['Category'] || ''}"`,
            `"${item['District'] || ''}"`,
            `"${item['Weighted Cutoff Percentile'] || ''}"`,
            `"${item['Chance Tag'] || ''}"`,
            `"${item['Is Top 20'] ? 'Top 20 #' + item['Top 20 Rank'] : 'Standard'}"`
        ].join(','));
    });

    downloadCsv(rows.join('\n'), `DTE_Preference_${document.getElementById('percentileInput').value}pct.csv`);
}

function downloadCsv(content, filename) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ===== OFFLINE FALLBACK =====
function runOfflineFallback(pct) {
    allPredictions = [
        {
            'College Code': 6006, 'College Name': 'COEP Technological University, Pune',
            'Course': 'Computer Engineering', 'Category': 'OPEN', 'District': 'Pune',
            'Is Top 20': true, 'Top 20 Rank': 1, 'College Tier': '🏆 Top 20',
            'Latest Cutoff Percentile': 99.75, 'Weighted Cutoff Percentile': 99.75,
            'Admission Probability': pct >= 99.7 ? 88.0 : (pct >= 99.0 ? 45.0 : 5.0),
            'Chance Tag': pct >= 99.7 ? '🟢 High / Safe' : (pct >= 99.0 ? '🟡 Moderate / Target' : '🔴 Low / Dream'),
        },
        {
            'College Code': 3012, 'College Name': 'VJTI, Mumbai',
            'Course': 'Computer Engineering', 'Category': 'OPEN', 'District': 'Mumbai',
            'Is Top 20': true, 'Top 20 Rank': 2, 'College Tier': '🏆 Top 20',
            'Latest Cutoff Percentile': 99.65, 'Weighted Cutoff Percentile': 99.65,
            'Admission Probability': pct >= 99.6 ? 85.0 : (pct >= 98.8 ? 40.0 : 4.0),
            'Chance Tag': pct >= 99.6 ? '🟢 High / Safe' : (pct >= 98.8 ? '🟡 Moderate / Target' : '🔴 Low / Dream'),
        }
    ];

    top20ShowcaseData = [
        { 'Rank': 1, 'Code': 6006, 'Short Name': 'COEP Pune', 'Full Name': 'COEP Technological University, Pune', 'City / District': 'Pune', 'Status': 'Govt Autonomous', 'CSE Cutoff (%ile)': 99.75, 'IT Cutoff (%ile)': 99.50, 'Your Admission Chance (CSE)': pct >= 99.7 ? '🟢 High Chance' : (pct >= 99.0 ? '🟡 Moderate Chance' : '🔴 Low Chance') },
        { 'Rank': 2, 'Code': 3012, 'Short Name': 'VJTI Mumbai', 'Full Name': 'VJTI, Mumbai', 'City / District': 'Mumbai', 'Status': 'Govt Autonomous', 'CSE Cutoff (%ile)': 99.65, 'IT Cutoff (%ile)': 99.40, 'Your Admission Chance (CSE)': pct >= 99.6 ? '🟢 High Chance' : (pct >= 98.8 ? '🟡 Moderate Chance' : '🔴 Low Chance') }
    ];

    renderTop20Cards(top20ShowcaseData);
    applyPredictFilters();
    updateKpis(allPredictions);
}
