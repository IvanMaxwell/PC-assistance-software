/* =====================================================================
   PC Automation Framework – Frontend Application
   ===================================================================== */

const API = '';  // Same origin

// ── State ──────────────────────────────────────────────────────────
const API_BASE = window.location.origin;
let allTools = [];
let lastExecData = null;      // store last execution response for toggling
let statusInterval = null;

// ── Init ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Ensure we start on chat page
    switchPage('chat');

    setupNavigation();
    setupChat();
    setupToolsPage();
    setupHistory();
    setupExecutionPage();
    fetchStatus();
    fetchTools();
    statusInterval = setInterval(fetchStatus, 3000); // Poll every 3 seconds
});

// ── Navigation ──────────────────────────────────────────────────────
function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = btn.dataset.page;
            switchPage(page);
        });
    });
}

function switchPage(page) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const navBtn = document.querySelector(`[data-page="${page}"]`);
    const pageEl = document.getElementById(`page-${page}`);
    if (navBtn) navBtn.classList.add('active');
    if (pageEl) pageEl.classList.add('active');
}

// ── Status Polling ──────────────────────────────────────────────────
async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status`);
        const data = await res.json();
        updateStatusCards(data);
        updateAgentBadges(data);
        setConnectionStatus(true);
    } catch (e) {
        setConnectionStatus(false);
    }
}

function updateStatusCards(data) {
    const s = data.system || {};
    setText('stat-cpu', `${s.cpu_percent ?? '—'}%`);
    setText('stat-ram', `${s.memory_used_gb ?? '—'} / ${s.memory_total_gb ?? '—'} GB`);
    setText('stat-disk', `${s.disk_free_gb ?? '—'} GB free`);
    setBarWidth('bar-cpu', s.cpu_percent);
    setBarWidth('bar-ram', s.memory_percent);
    setBarWidth('bar-disk', s.disk_percent);
}

function updateAgentBadges(data) {
    const agents = data.agents || {};
    const cm = agents.cm_agent || {};
    const cs = agents.cs_agent || {};
    const badge_cm = document.getElementById('badge-cm');
    const badge_cs = document.getElementById('badge-cs');
    const badge_tools = document.getElementById('badge-tools-count');
    if (badge_cm) badge_cm.textContent = `CM: ${cm.backend || 'offline'}`;
    if (badge_cs) badge_cs.textContent = `CS: ${cs.backend || 'offline'}`;
    if (badge_tools) badge_tools.textContent = `${data.tool_count ?? 0} tools`;
}

function setConnectionStatus(online) {
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    if (dot) { dot.className = 'status-dot ' + (online ? 'online' : 'offline'); }
    if (txt) txt.textContent = online ? 'Connected' : 'Offline';
}

// ── Chat ────────────────────────────────────────────────────────────
function setupChat() {
    const input = document.getElementById('chat-input');
    const btn = document.getElementById('send-btn');

    btn.addEventListener('click', () => sendChat());
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
    });
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const cmd = input.value.trim();
    if (!cmd) return;
    input.value = '';

    // Add user message
    addChatMessage(cmd, 'user');

    // Show typing indicator
    const typingId = addChatMessage('Processing…', 'bot', true);

    // Disable input
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;
    input.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd }),
        });
        const data = await res.json();
        lastExecData = data;

        // Remove typing indicator
        removeChatMessage(typingId);

        // Add CM Agent reply
        const cm = data.cm_response;
        if (cm && cm.reply) {
            addChatMessage(`<span class="label">CM Agent:</span> ${cm.reply}`, 'bot');
            if (cm.explanation) {
                addChatMessage(cm.explanation, 'bot');
            }
        }

        // Add summary
        if (data.summary) {
            addChatMessage(`<span class="label">Result:</span> ${data.summary}`, 'bot');
        } else {
            addChatMessage('Execution completed. See Execution Viewer for details.', 'bot');
        }

        // Update execution viewer
        renderExecution(data);

    } catch (e) {
        removeChatMessage(typingId);
        addChatMessage(`<span style="color:var(--red)">Error: ${e.message}</span>`, 'bot');
    }

    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
}

let msgCounter = 0;
function addChatMessage(html, type, isTyping = false) {
    const id = `msg-${++msgCounter}`;
    const container = document.getElementById('chat-messages');
    const avatar = type === 'user' ? '👤' : '⚡';
    const cls = type === 'user' ? 'user-message' : 'bot-message';
    const div = document.createElement('div');
    div.className = `message ${cls}`;
    div.id = id;
    div.innerHTML = `
        <div class="msg-avatar">${avatar}</div>
        <div class="msg-body">
            <div class="msg-text${isTyping ? ' dim' : ''}">${html}</div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeChatMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ── Execution Viewer ────────────────────────────────────────────────
function setupExecutionPage() {
    document.getElementById('btn-show-flow')?.addEventListener('click', () => {
        // Toggle: show pipeline, hide summary
        document.getElementById('exec-flow').classList.remove('hidden');
        document.getElementById('result-summary').classList.add('hidden');
    });
    document.getElementById('btn-new-cmd')?.addEventListener('click', () => {
        switchPage('chat');
    });
}

function renderExecution(data) {
    const flow = document.getElementById('exec-flow');
    const summary = document.getElementById('result-summary');
    const empty = document.getElementById('exec-empty');
    const badge = document.getElementById('exec-status-badge');

    empty.style.display = 'none';

    // Show result summary (hide execution process)
    flow.classList.add('hidden');
    summary.classList.remove('hidden');

    // Update badge
    const hasErrors = data.results?.some(r => r.status === 'error' || r.status === 'failed');
    badge.textContent = hasErrors ? 'Partial Failure' : 'Success';
    badge.className = `badge ${hasErrors ? 'badge-amber' : 'badge-green'}`;

    // Fill result summary
    document.getElementById('result-icon').textContent = hasErrors ? '⚠️' : '✅';
    document.getElementById('result-title').textContent = hasErrors ? 'Execution Completed with Issues' : 'Execution Complete';
    document.getElementById('result-command').textContent = data.command || '';
    document.getElementById('result-summary-text').textContent = data.summary || 'No summary available.';

    // Meta
    const meta = document.getElementById('result-meta');
    meta.innerHTML = '';
    addMeta(meta, 'Time', `${data.elapsed_seconds ?? '—'}s`);
    addMeta(meta, 'Confidence', `${((data.confidence ?? 0) * 100).toFixed(0)}%`);
    if (data.cs_assessment) {
        addMeta(meta, 'Risk', data.cs_assessment.risk_level || 'N/A');
    }

    // Detailed results JSON
    document.getElementById('result-data').textContent = JSON.stringify(data.results, null, 2);

    // Also populate the pipeline flow for the "View Pipeline Details" button
    populatePipelineFlow(data);
}

function addMeta(container, label, value) {
    const div = document.createElement('div');
    div.className = 'meta-item';
    div.innerHTML = `<span class="meta-label">${label}:</span><span class="meta-value">${value}</span>`;
    container.appendChild(div);
}

function populatePipelineFlow(data) {
    const events = data.events || [];

    // FSM Timeline
    const fsm = document.getElementById('fsm-timeline');
    fsm.innerHTML = '';
    const states = [];
    events.filter(e => e.type === 'state').forEach(e => {
        if (!states.includes(e.from)) states.push(e.from);
        if (!states.includes(e.to)) states.push(e.to);
    });
    states.forEach((s, i) => {
        if (i > 0) fsm.innerHTML += `<span class="fsm-arrow">→</span>`;
        const cls = (i === states.length - 1) ? 'done' : 'done';
        fsm.innerHTML += `<span class="fsm-state ${cls}">${s}</span>`;
    });

    // CM Agent
    const cmEvt = events.find(e => e.type === 'cm_response');
    if (cmEvt) {
        document.getElementById('cm-section').style.display = '';
        document.getElementById('cm-reply').textContent = cmEvt.reply || '';
        document.getElementById('cm-explanation').textContent = cmEvt.explanation || '';
    }

    // Router
    const routerEvt = events.find(e => e.type === 'router');
    if (routerEvt) {
        document.getElementById('router-section').style.display = '';
        document.getElementById('router-card').innerHTML = `
            <p><strong>Query:</strong> ${routerEvt.query}</p>
            <p><strong>Matched Tool:</strong> <span style="color:var(--cyan)">${routerEvt.tool}</span></p>
            <p><strong>Score:</strong> ${routerEvt.score?.toFixed(2)}</p>
            <p><strong>Shortcut:</strong> ${routerEvt.hit ? '✅ Yes' : '❌ No'}</p>
        `;
    }

    // Plan
    const planEvt = events.find(e => e.type === 'plan');
    if (planEvt && planEvt.plan) {
        document.getElementById('plan-section').style.display = '';
        const plan = planEvt.plan;
        const wrap = document.getElementById('plan-table-wrap');
        let html = '<table class="plan-table"><thead><tr><th>#</th><th>Tool</th><th>Arguments</th><th>On Fail</th></tr></thead><tbody>';
        (plan.steps || []).forEach(step => {
            const args = JSON.stringify(step.arguments || step.params || {});
            html += `<tr>
                <td>${step.step_id ?? '?'}</td>
                <td>${step.tool_name || step.tool || '?'}</td>
                <td>${args.length > 40 ? args.slice(0, 40) + '…' : args}</td>
                <td>${step.on_failure || 'abort'}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        if (plan.reasoning) {
            html += `<p class="dim" style="margin-top:8px">Reasoning: ${plan.reasoning}</p>`;
        }
        wrap.innerHTML = html;
    }

    // Confidence
    const confEvt = events.find(e => e.type === 'confidence');
    if (confEvt) {
        document.getElementById('confidence-section').style.display = '';
        const pct = (confEvt.score * 100).toFixed(0);
        const fill = document.getElementById('confidence-fill');
        fill.style.width = pct + '%';
        fill.style.background = confEvt.score >= 0.8 ? 'var(--green)' : confEvt.score >= 0.5 ? 'var(--amber)' : 'var(--red)';
        document.getElementById('confidence-label').textContent = pct + '%';
        document.getElementById('confidence-label').style.color = confEvt.score >= 0.8 ? 'var(--green)' : confEvt.score >= 0.5 ? 'var(--amber)' : 'var(--red)';
    }

    // Risk Assessment
    const riskEvt = events.find(e => e.type === 'risk_assessment');
    if (riskEvt) {
        document.getElementById('risk-section').style.display = '';
        const card = document.getElementById('risk-card');
        const riskColor = riskEvt.risk_level === 'HIGH' ? 'var(--red)' : riskEvt.risk_level === 'MEDIUM' ? 'var(--amber)' : 'var(--green)';
        let html = `<p class="risk-level" style="color:${riskColor}">${riskEvt.risk_level} RISK</p>`;
        html += `<p style="margin-bottom:6px">Recommendation: <strong>${riskEvt.recommendation || '—'}</strong></p>`;
        if (riskEvt.concerns && riskEvt.concerns.length) {
            html += '<ul class="risk-concerns">';
            riskEvt.concerns.forEach(c => html += `<li>${c}</li>`);
            html += '</ul>';
        }
        card.innerHTML = html;
    }

    // Step Results
    const stepEvts = events.filter(e => e.type === 'step_result');
    if (stepEvts.length) {
        document.getElementById('steps-section').style.display = '';
        const container = document.getElementById('step-results');
        container.innerHTML = '';
        stepEvts.forEach(s => {
            const icon = s.status === 'success' ? '✅' : '❌';
            const cls = s.status === 'success' ? 'success' : 'failed';
            const div = document.createElement('div');
            div.className = 'step-item';
            div.innerHTML = `
                <span class="step-icon">${icon}</span>
                <span class="step-tool">${s.tool}</span>
                <span class="step-status ${cls}">${s.status.toUpperCase()}</span>
            `;
            container.appendChild(div);
        });
    }
}

// ── Tools Page ──────────────────────────────────────────────────────
function setupToolsPage() {
    document.getElementById('tool-search')?.addEventListener('input', filterTools);
    document.getElementById('tool-filter')?.addEventListener('change', filterTools);
    document.getElementById('sim-btn')?.addEventListener('click', runSimilarity);
    document.getElementById('sim-query')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') runSimilarity();
    });
}

async function fetchTools() {
    try {
        const res = await fetch(`${API_BASE}/api/tools`);
        const data = await res.json();
        allTools = data.tools || [];
        renderTools(allTools);
        populateCategoryFilter(allTools);
    } catch (e) {
        console.error('Failed to fetch tools:', e);
    }
}

function renderTools(tools) {
    const grid = document.getElementById('tools-grid');
    if (!grid) return;
    grid.innerHTML = '';
    tools.forEach(t => {
        const riskCls = t.risk === 'safe' ? 'risk-safe' : t.risk === 'medium' ? 'risk-medium' : 'risk-high';
        const paramList = (t.parameters || []).map(p =>
            `<span style="color:var(--text-dim);font-size:0.75rem;margin-right:4px">${p.name}${p.required ? '*' : ''}</span>`
        ).join(', ');

        const card = document.createElement('div');
        card.className = 'tool-card';
        card.innerHTML = `
            <div class="tool-name">${t.name}</div>
            <div class="tool-desc">${t.description || 'No description'}</div>
            <div class="tool-meta">
                <span class="risk-badge ${riskCls}">${t.risk}</span>
                <span class="cat-badge">${t.category}</span>
            </div>
            ${paramList ? `<div style="margin-top:8px">${paramList}</div>` : ''}
        `;
        grid.appendChild(card);
    });
}

function populateCategoryFilter(tools) {
    const select = document.getElementById('tool-filter');
    if (!select) return;
    const cats = [...new Set(tools.map(t => t.category))].sort();
    select.innerHTML = '<option value="all">All Categories</option>';
    cats.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c.charAt(0).toUpperCase() + c.slice(1);
        select.appendChild(opt);
    });
}

function filterTools() {
    const q = (document.getElementById('tool-search')?.value || '').toLowerCase();
    const cat = document.getElementById('tool-filter')?.value || 'all';
    const filtered = allTools.filter(t => {
        const matchQ = !q || t.name.toLowerCase().includes(q) || (t.description || '').toLowerCase().includes(q);
        const matchCat = cat === 'all' || t.category === cat;
        return matchQ && matchCat;
    });
    renderTools(filtered);
}

async function runSimilarity() {
    const query = document.getElementById('sim-query')?.value?.trim();
    if (!query) return;
    const container = document.getElementById('sim-results');
    container.innerHTML = '<p class="dim">Searching…</p>';
    try {
        const res = await fetch(`${API_BASE}/api/similarity?query=${encodeURIComponent(query)}`);
        const data = await res.json();
        container.innerHTML = '';
        if (data.matches && data.matches.length) {
            data.matches.forEach((m, i) => {
                const pct = Math.round(m.score * 100);
                container.innerHTML += `
                    <div class="sim-row">
                        <span class="sim-rank">#${i + 1}</span>
                        <span class="sim-tool">${m.tool}</span>
                        <div class="sim-score-bar"><div class="sim-score-fill" style="width:${pct}%"></div></div>
                        <span class="sim-score-val">${pct}%</span>
                    </div>
                `;
            });
        } else {
            container.innerHTML = '<p class="dim">No matches found. Router may not be available.</p>';
        }
    } catch (e) {
        container.innerHTML = `<p class="dim" style="color:var(--red)">Error: ${e.message}</p>`;
    }
}

// ── History Page ────────────────────────────────────────────────────
function setupHistory() {
    document.getElementById('refresh-history')?.addEventListener('click', fetchHistory);
    fetchHistory();
}

async function fetchHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/history`);
        const data = await res.json();
        const list = document.getElementById('history-list');
        if (!list) return;
        if (!data.entries || data.entries.length === 0) {
            list.innerHTML = '<p class="dim">No execution history yet. Send a command to get started.</p>';
            return;
        }
        list.innerHTML = '';
        data.entries.reverse().forEach(e => {
            const confPct = ((e.confidence || 0) * 100).toFixed(0);
            const confColor = e.confidence >= 0.8 ? 'var(--green)' : e.confidence >= 0.5 ? 'var(--amber)' : 'var(--red)';
            const div = document.createElement('div');
            div.className = 'history-item';
            div.innerHTML = `
                <span class="history-time">${formatTime(e.timestamp)}</span>
                <span class="history-request">${e.request || '—'}</span>
                <span class="history-confidence" style="color:${confColor}">${confPct}%</span>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error('Failed to fetch history:', e);
    }
}

// ── Helpers ─────────────────────────────────────────────────────────
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function setBarWidth(id, pct) {
    const el = document.getElementById(id);
    if (el && pct != null) el.style.width = Math.min(pct, 100) + '%';
}

function formatTime(iso) {
    if (!iso) return '—';
    try {
        const d = new Date(iso);
        return d.toLocaleString();
    } catch {
        return iso;
    }
}
