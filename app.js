const API_BASE = ''; // relative path for same-origin or API proxy

// State Management
let allPredictions = [];
let top20ShowcaseData = [];
let predictFiltered = [];
let optionFiltered = [];

let predictPage = 1;
let predictPageSize = 25;
let optionPage = 1;
let optionPageSize = 25;

let activeAbortController = null;
let debounceTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    initControls();
    initTabs();
    initPagination();
    fetchFilterOptions().then(() => {
        const initialPct = parseFloat(document.getElementById('percentileInput').value) || 92.5;
        updateRankEst(initialPct);
        fetchPredictionsDebounced();
    });
});

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function initControls() {
    const slider = document.getElementById('percentileSlider');
    const input = document.getElementById('percentileInput');

    slider.addEventListener('input', (e) => {
        let val = parseFloat(e.target.value);
        if (isNaN(val)) val = 92.5;
        val = Math.max(0, Math.min(100, val));
        input.value = val;
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

    // Dropdown and Toggle change handlers
    const controlIds = [
        'categorySelect', 'genderSelect', 'quotaSelect', 'capRoundSelect',
        'districtSelect', 'branchSelect', 'top20OnlyToggle', 'prioritizeTop20Toggle'
    ];
    controlIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                fetchPredictionsDebounced();
            });
        }
    });

    document.getElementById('btnPredict').addEventListener('click', () => {
        fetchPredictions();
    });

    document.getElementById('searchTop20').addEventListener('input', filterTop20Table);
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

    // Non-linear empirical rank interpolation approximation for instant UI response
    let estRank = 1;
    if (pct >= 99.9) estRank = Math.round(1 + (100 - pct) * 10000);
    else if (pct >= 99.0) estRank = Math.round(1020 + (99.9 - pct) * 2058);
    else if (pct >= 95.0) estRank = Math.round(2873 + (99.0 - pct) * 3250);
    else if (pct >= 90.0) estRank = Math.round(15874 + (95.0 - pct) * 2950);
    else if (pct >= 80.0) estRank = Math.round(30623 + (90.0 - pct) * 2818);
    else if (pct >= 50.0) estRank = Math.round(58800 + (80.0 - pct) * 2130);
    else estRank = Math.round(122713 + (50.0 - pct) * 1000);

    const estRankEl = document.getElementById('estRankValue');
    if (estRankEl) {
        estRankEl.innerText = estRank.toLocaleString();
    }
}

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            const targetEl = document.getElementById(targetId);
            if (targetEl) targetEl.classList.add('active');
        });
    });
}

function initPagination() {
    document.getElementById('btnPredictPrev').addEventListener('click', () => {
        if (predictPage > 1) { predictPage--; renderPredictTable(); }
    });
    document.getElementById('btnPredictNext').addEventListener('click', () => {
        const totalPages = Math.ceil(predictFiltered.length / predictPageSize) || 1;
        if (predictPage < totalPages) { predictPage++; renderPredictTable(); }
    });
    document.getElementById('predictPageSize').addEventListener('change', (e) => {
        predictPageSize = parseInt(e.target.value) || 25;
        predictPage = 1;
        renderPredictTable();
    });

    document.getElementById('btnOptionPrev').addEventListener('click', () => {
        if (optionPage > 1) { optionPage--; renderOptionForm(); }
    });
    document.getElementById('btnOptionNext').addEventListener('click', () => {
        const totalPages = Math.ceil(optionFiltered.length / optionPageSize) || 1;
        if (optionPage < totalPages) { optionPage++; renderOptionForm(); }
    });
    document.getElementById('optionPageSize').addEventListener('change', (e) => {
        optionPageSize = parseInt(e.target.value) || 25;
        optionPage = 1;
        renderOptionForm();
    });
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

async function fetchFilterOptions() {
    try {
        const res = await fetch(`${API_BASE}/api/options`);
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const data = await res.json();
        
        if (data.success && data.options) {
            populateSelect('districtSelect', data.options.districts, 'All Districts');
            populateSelect('branchSelect', data.options.courses, 'All Engineering Branches');
            populateSelect('categorySelect', data.options.category_groups, null, 'OPEN');
        }
    } catch (err) {
        console.warn('Could not fetch dynamic options from server:', err);
        // Fallback default dropdown populations
        populateSelect('districtSelect', ['Pune', 'Mumbai', 'Sangli', 'Chhatrapati Sambhajinagar', 'Amravati'], 'All Districts');
        populateSelect('branchSelect', ['Computer Engineering', 'Information Technology', 'Artificial Intelligence & Data Science', 'Electronics & Telecommunication Engineering', 'Mechanical Engineering'], 'All Engineering Branches');
    }
}

function populateSelect(elemId, items, allLabel, defaultVal) {
    const sel = document.getElementById(elemId);
    if (!sel || !items) return;
    sel.innerHTML = '';
    
    if (allLabel) {
        const opt = document.createElement('option');
        opt.value = 'ALL';
        opt.innerText = allLabel;
        opt.selected = !defaultVal || defaultVal === 'ALL';
        sel.appendChild(opt);
    }

    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item;
        opt.innerText = item;
        if (defaultVal && item === defaultVal) opt.selected = true;
        sel.appendChild(opt);
    });
}

function fetchPredictionsDebounced() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        fetchPredictions();
    }, 250);
}

// Single-request fetch to predict API
async function fetchPredictions() {
    if (activeAbortController) {
        activeAbortController.abort();
    }
    activeAbortController = new AbortController();

    const pctInput = parseFloat(document.getElementById('percentileInput').value);
    const pct = isNaN(pctInput) ? 92.5 : Math.max(0, Math.min(100, pctInput));
    
    const catGroup = document.getElementById('categorySelect').value;
    const genderQuota = document.getElementById('genderSelect').value;
    const universityQuota = document.getElementById('quotaSelect').value;
    const capRound = document.getElementById('capRoundSelect').value;
    const district = document.getElementById('districtSelect').value;
    const branch = document.getElementById('branchSelect').value;
    const top20Only = document.getElementById('top20OnlyToggle').checked;
    const prioritizeTop20 = document.getElementById('prioritizeTop20Toggle').checked;

    const payload = {
        percentile: pct,
        category_group: catGroup,
        gender_quota: genderQuota,
        university_quota: universityQuota,
        cap_round: capRound,
        districts: district === 'ALL' ? ['ALL'] : [district],
        branches: branch === 'ALL' ? ['ALL'] : [branch],
        top_20_only: top20Only,
        prioritize_top_20: prioritizeTop20
    };

    try {
        const res = await fetch(`${API_BASE}/api/predict`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload),
            signal: activeAbortController.signal
        });

        if (!res.ok) {
            throw new Error(`Server returned error status ${res.status}`);
        }

        const data = await res.json();
        if (data.success) {
            showErrorBanner(null);
            allPredictions = data.predictions || [];
            top20ShowcaseData = data.top_20_showcase || [];

            if (data.calculated_rank) {
                const estRankEl = document.getElementById('estRankValue');
                if (estRankEl) estRankEl.innerText = data.calculated_rank.toLocaleString();
            }

            renderTop20Table(top20ShowcaseData);
            applyPredictFilters();
            updateKpis(allPredictions);
        } else {
            showErrorBanner(data.error || 'Failed to fetch predictions');
        }
    } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('API Error:', err);
        showErrorBanner('API Offline. Showing local offline calculation.');
        runOfflineLocalFallback(pct, top20Only, prioritizeTop20);
    }
}

function updateKpis(items) {
    const top20Count = items.filter(i => i['Is Top 20']).length;
    const safeCount = items.filter(i => String(i['Chance Tag']).includes('High') || String(i['Chance Tag']).includes('Safe')).length;
    const targetCount = items.filter(i => String(i['Chance Tag']).includes('Moderate') || String(i['Chance Tag']).includes('Target')).length;
    const dreamCount = items.filter(i => String(i['Chance Tag']).includes('Low') || String(i['Chance Tag']).includes('Dream')).length;

    document.getElementById('kpiTop20').innerText = top20Count;
    document.getElementById('kpiSafe').innerText = safeCount;
    document.getElementById('kpiTarget').innerText = targetCount;
    document.getElementById('kpiDream').innerText = dreamCount;
}

function renderTop20Table(items) {
    const tbody = document.getElementById('top20TableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!items || items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#94a3b8; padding:20px;">No Top 20 colleges match criteria.</td></tr>`;
        return;
    }

    items.forEach(item => {
        const tr = document.createElement('tr');
        
        let chanceClass = 'badge-safe';
        const chanceStr = String(item['Your Admission Chance (CSE)'] || '');
        if (chanceStr.includes('Moderate')) chanceClass = 'badge-target';
        if (chanceStr.includes('Low')) chanceClass = 'badge-dream';

        tr.innerHTML = `
            <td><span class="badge badge-gold">#${item.Rank}</span></td>
            <td><code>${escapeHtml(item.Code)}</code></td>
            <td><strong>${escapeHtml(item['Short Name'])}</strong> <br><small style="color:#94a3b8">${escapeHtml(item['Full Name'])}</small></td>
            <td>${escapeHtml(item['City / District'])}</td>
            <td><small>${escapeHtml(item.Status)}</small></td>
            <td><strong>${escapeHtml(item['CSE Cutoff (%ile)'])} ${typeof item['CSE Cutoff (%ile)'] === 'number' ? '%' : ''}</strong></td>
            <td><strong>${escapeHtml(item['IT Cutoff (%ile)'])} ${typeof item['IT Cutoff (%ile)'] === 'number' ? '%' : ''}</strong></td>
            <td><span class="badge ${chanceClass}">${escapeHtml(item['Your Admission Chance (CSE)'])}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

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

    renderPredictTable();
    
    // Sort option form according to prioritizeTop20 toggle
    const prioritizeTop20 = document.getElementById('prioritizeTop20Toggle').checked;
    optionFiltered = [...allPredictions].sort((a, b) => {
        if (prioritizeTop20) {
            if (a['Is Top 20'] !== b['Is Top 20']) return b['Is Top 20'] ? 1 : -1;
            if (a['Is Top 20'] && b['Is Top 20']) return (a['Top 20 Rank'] || 99) - (b['Top 20 Rank'] || 99);
        }
        return b['Weighted Cutoff Percentile'] - a['Weighted Cutoff Percentile'];
    });

    renderOptionForm();
}

function renderPredictTable() {
    const tbody = document.getElementById('predictTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const totalItems = predictFiltered.length;
    const totalPages = Math.ceil(totalItems / predictPageSize) || 1;
    predictPage = Math.max(1, Math.min(predictPage, totalPages));

    document.getElementById('predictPageInfo').innerText = `Page ${predictPage} of ${totalPages} (${totalItems} items)`;

    if (totalItems === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:#94a3b8; padding:24px;">No college predictions found matching search/filter.</td></tr>`;
        return;
    }

    const startIdx = (predictPage - 1) * predictPageSize;
    const pageItems = predictFiltered.slice(startIdx, startIdx + predictPageSize);

    pageItems.forEach(item => {
        const tr = document.createElement('tr');
        
        let chanceClass = 'badge-safe';
        const tagStr = String(item['Chance Tag'] || '');
        if (tagStr.includes('Moderate') || tagStr.includes('Target')) chanceClass = 'badge-target';
        if (tagStr.includes('Low') || tagStr.includes('Dream')) chanceClass = 'badge-dream';

        const tierHtml = item['Is Top 20'] ? 
            `<span class="badge badge-gold">🏆 Top 20 #${item['Top 20 Rank']}</span>` : 
            `<small style="color:#94a3b8">${escapeHtml(item['College Tier'])}</small>`;

        tr.innerHTML = `
            <td>${tierHtml}</td>
            <td><code>${escapeHtml(item['College Code'])}</code></td>
            <td><strong>${escapeHtml(item['College Name'])}</strong></td>
            <td>${escapeHtml(item['Course'])}</td>
            <td>${escapeHtml(item['District'])}</td>
            <td><strong>${Number(item['Admission Probability']).toFixed(1)}%</strong></td>
            <td><span class="badge ${chanceClass}">${escapeHtml(item['Chance Tag'])}</span></td>
            <td>${Number(item['Latest Cutoff Percentile']).toFixed(2)}%</td>
            <td><small>${escapeHtml(item['Cutoff Range'] || '-')}</small></td>
            <td><div class="exp-text">${escapeHtml(item['Recommendation Explanation'] || '')}</div></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderOptionForm() {
    const tbody = document.getElementById('optionTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const totalItems = optionFiltered.length;
    const totalPages = Math.ceil(totalItems / optionPageSize) || 1;
    optionPage = Math.max(1, Math.min(optionPage, totalPages));

    document.getElementById('optionPageInfo').innerText = `Page ${optionPage} of ${totalPages} (${totalItems} items)`;

    if (totalItems === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#94a3b8; padding:24px;">No preference options available.</td></tr>`;
        return;
    }

    const startIdx = (optionPage - 1) * optionPageSize;
    const pageItems = optionFiltered.slice(startIdx, startIdx + optionPageSize);

    pageItems.forEach((item, idx) => {
        const prefNum = startIdx + idx + 1;
        const tr = document.createElement('tr');
        
        let chanceClass = 'badge-safe';
        const tagStr = String(item['Chance Tag'] || '');
        if (tagStr.includes('Moderate') || tagStr.includes('Target')) chanceClass = 'badge-target';
        if (tagStr.includes('Low') || tagStr.includes('Dream')) chanceClass = 'badge-dream';

        tr.innerHTML = `
            <td><strong>#${prefNum}</strong></td>
            <td>${item['Is Top 20'] ? `<span class="badge badge-gold">🏆 Top 20 #${item['Top 20 Rank']}</span>` : 'Standard'}</td>
            <td><code>${escapeHtml(item['College Code'])}</code></td>
            <td><strong>${escapeHtml(item['College Name'])}</strong></td>
            <td>${escapeHtml(item['Course'])}</td>
            <td>${Number(item['Weighted Cutoff Percentile']).toFixed(2)}%</td>
            <td><span class="badge ${chanceClass}">${escapeHtml(item['Chance Tag'])}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function filterTop20Table() {
    const query = (document.getElementById('searchTop20').value || '').toLowerCase();
    const rows = document.querySelectorAll('#top20TableBody tr');
    rows.forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
    });
}

function exportPredictCsv() {
    if (!allPredictions || allPredictions.length === 0) {
        alert('No prediction data available to export.');
        return;
    }

    const headers = [
        "College Code", "College Name", "Course", "Category", "District",
        "Admission Probability (%)", "Chance Tag", "Latest Cutoff Percentile",
        "Weighted Cutoff Percentile", "Cutoff Range", "Is Top 20", "Top 20 Rank", "Recommendation Explanation"
    ];

    const csvRows = [headers.join(',')];

    allPredictions.forEach(item => {
        const row = [
            `"${item['College Code'] || ''}"`,
            `"${String(item['College Name'] || '').replace(/"/g, '""')}"`,
            `"${String(item['Course'] || '').replace(/"/g, '""')}"`,
            `"${item['Category'] || ''}"`,
            `"${item['District'] || ''}"`,
            `"${item['Admission Probability'] || 0}"`,
            `"${item['Chance Tag'] || ''}"`,
            `"${item['Latest Cutoff Percentile'] || ''}"`,
            `"${item['Weighted Cutoff Percentile'] || ''}"`,
            `"${item['Cutoff Range'] || ''}"`,
            `"${item['Is Top 20'] ? 'YES' : 'NO'}"`,
            `"${item['Top 20 Rank'] || ''}"`,
            `"${String(item['Recommendation Explanation'] || '').replace(/"/g, '""')}"`
        ];
        csvRows.push(row.join(','));
    });

    downloadCsvFile(csvRows.join('\n'), `MHTCET_Predictions_${document.getElementById('percentileInput').value}pct.csv`);
}

function exportOptionCsv() {
    if (!optionFiltered || optionFiltered.length === 0) {
        alert('No preference list options available to export.');
        return;
    }

    const headers = [
        "Preference No", "College Code", "College Name", "Course",
        "Category", "District", "Historical Cutoff (%)", "Admission Chance", "Top 20 Priority"
    ];

    const csvRows = [headers.join(',')];

    optionFiltered.forEach((item, idx) => {
        const row = [
            `"${idx + 1}"`,
            `"${item['College Code'] || ''}"`,
            `"${String(item['College Name'] || '').replace(/"/g, '""')}"`,
            `"${String(item['Course'] || '').replace(/"/g, '""')}"`,
            `"${item['Category'] || ''}"`,
            `"${item['District'] || ''}"`,
            `"${item['Weighted Cutoff Percentile'] || ''}"`,
            `"${item['Chance Tag'] || ''}"`,
            `"${item['Is Top 20'] ? 'Top 20 Rank #' + item['Top 20 Rank'] : 'Standard'}"`
        ];
        csvRows.push(row.join(','));
    });

    downloadCsvFile(csvRows.join('\n'), `DTE_Preference_Form_${document.getElementById('percentileInput').value}pct.csv`);
}

function downloadCsvFile(content, fileName) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function runOfflineLocalFallback(pct, top20Only, prioritizeTop20) {
    // Basic local calculation fallback if server is unreachable
    allPredictions = [
        {
            'College Code': 6006, 'College Name': 'COEP Technological University, Pune', 'Course': 'Computer Engineering',
            'Category': 'OPEN', 'District': 'Pune', 'Is Top 20': true, 'Top 20 Rank': 1, 'College Tier': '🏆 Top 20 Maharashtra',
            'Latest Cutoff Percentile': 99.75, 'Weighted Cutoff Percentile': 99.75, 'Cutoff Range': '99.75% - 99.85%',
            'Admission Probability': pct >= 99.7 ? 88.0 : (pct >= 99.0 ? 45.0 : 5.0),
            'Chance Tag': pct >= 99.7 ? 'High / Safe' : (pct >= 99.0 ? 'Moderate / Target' : 'Low / Dream'),
            'Recommendation Explanation': `Local fallback computation for percentile ${pct.toFixed(2)}%.`
        },
        {
            'College Code': 3012, 'College Name': 'Veermata Jijabai Technological Institute (VJTI), Mumbai', 'Course': 'Computer Engineering',
            'Category': 'OPEN', 'District': 'Mumbai', 'Is Top 20': true, 'Top 20 Rank': 2, 'College Tier': '🏆 Top 20 Maharashtra',
            'Latest Cutoff Percentile': 99.65, 'Weighted Cutoff Percentile': 99.65, 'Cutoff Range': '99.65% - 99.80%',
            'Admission Probability': pct >= 99.6 ? 85.0 : (pct >= 98.8 ? 40.0 : 4.0),
            'Chance Tag': pct >= 99.6 ? 'High / Safe' : (pct >= 98.8 ? 'Moderate / Target' : 'Low / Dream'),
            'Recommendation Explanation': `Local fallback computation for percentile ${pct.toFixed(2)}%.`
        }
    ];

    top20ShowcaseData = [
        {'Rank': 1, 'Code': 6006, 'Short Name': 'COEP', 'Full Name': 'COEP Technological University, Pune', 'City / District': 'Pune', 'Status': 'Govt Autonomous', 'CSE Cutoff (%ile)': 99.75, 'IT Cutoff (%ile)': 99.50, 'Your Admission Chance (CSE)': pct >= 99.7 ? '🟢 High Chance' : (pct >= 99.0 ? '🟡 Moderate Chance' : '🔴 Low Chance')},
        {'Rank': 2, 'Code': 3012, 'Short Name': 'VJTI', 'Full Name': 'Veermata Jijabai Technological Institute (VJTI)', 'City / District': 'Mumbai', 'Status': 'Govt Autonomous', 'CSE Cutoff (%ile)': 99.65, 'IT Cutoff (%ile)': 99.40, 'Your Admission Chance (CSE)': pct >= 99.6 ? '🟢 High Chance' : (pct >= 98.8 ? '🟡 Moderate Chance' : '🔴 Low Chance')}
    ];

    renderTop20Table(top20ShowcaseData);
    applyPredictFilters();
    updateKpis(allPredictions);
}
