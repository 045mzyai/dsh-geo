/* GEO Platform - SPA前端 */
const API = '';
let currentPage = 'quickstart';
let companyData = null;
let casesData = null;
let currentUser = null;

// ========== Auth ==========

function getToken() { return localStorage.getItem('geo_token'); }
function setToken(t) { localStorage.setItem('geo_token', t); }
function clearToken() { localStorage.removeItem('geo_token'); }

function isLoggedIn() { return !!getToken(); }

async function checkAuth() {
  const token = getToken();
  if (!token) { showLogin(); return false; }
  try {
    const resp = await fetch(`${API}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!resp.ok) { clearToken(); showLogin(); return false; }
    const data = await resp.json();
    currentUser = data.user;
    updateSidebarUser();
    return true;
  } catch(e) {
    clearToken(); showLogin(); return false;
  }
}

function showLogin() {
  currentUser = null;
  document.querySelector('.sidebar').style.display = 'none';
  const main = document.getElementById('main-content');
  main.innerHTML = `
    <div class="auth-wrap">
      <div class="auth-card">
        <div class="auth-brand">
          <h1>GEO Platform</h1>
          <p>生成式引擎优化平台</p>
        </div>
        <div class="auth-tabs">
          <button class="auth-tab active" data-tab="login">登录</button>
          <button class="auth-tab" data-tab="register">注册</button>
        </div>
        <div id="auth-form-login" class="auth-form active">
          <input type="email" id="login-email" placeholder="邮箱" autocomplete="email">
          <input type="password" id="login-password" placeholder="密码" autocomplete="current-password">
          <button class="auth-submit" id="btn-login">登录</button>
        </div>
        <div id="auth-form-register" class="auth-form">
          <input type="text" id="reg-name" placeholder="姓名">
          <input type="email" id="reg-email" placeholder="邮箱" autocomplete="email">
          <input type="password" id="reg-password" placeholder="密码（至少6位）" autocomplete="new-password">
          <input type="text" id="reg-company" placeholder="企业名称（选填）">
          <button class="auth-submit" id="btn-register">注册</button>
        </div>
        <div id="auth-error" class="auth-error"></div>
      </div>
    </div>
  `;
  setupAuthEvents();
}

function setupAuthEvents() {
  document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.tab;
      document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
      document.getElementById(`auth-form-${target}`).classList.add('active');
      document.getElementById('auth-error').textContent = '';
    });
  });
  document.getElementById('btn-login').addEventListener('click', doLogin);
  document.getElementById('btn-register').addEventListener('click', doRegister);
  document.getElementById('login-password').addEventListener('keydown', e => { if(e.key==='Enter') doLogin(); });
  document.getElementById('reg-password').addEventListener('keydown', e => { if(e.key==='Enter') doRegister(); });
}

async function doLogin() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('auth-error');
  errEl.textContent = '';
  if (!email || !password) { errEl.textContent = '请填写邮箱和密码'; return; }
  const btn = document.getElementById('btn-login');
  btn.textContent = '登录中...'; btn.disabled = true;
  try {
    const resp = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await resp.json();
    if (data.error) { errEl.textContent = data.error; btn.textContent='登录'; btn.disabled=false; return; }
    setToken(data.token);
    currentUser = data.user;
    document.querySelector('.sidebar').style.display = '';
    updateSidebarUser();
    renderPage();
  } catch(e) {
    errEl.textContent = '网络错误，请重试';
    btn.textContent='登录'; btn.disabled=false;
  }
}

async function doRegister() {
  const name = document.getElementById('reg-name').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const company = document.getElementById('reg-company').value.trim();
  const errEl = document.getElementById('auth-error');
  errEl.textContent = '';
  if (!name || !email || !password) { errEl.textContent = '请填写姓名、邮箱和密码'; return; }
  if (password.length < 6) { errEl.textContent = '密码至少6位'; return; }
  const btn = document.getElementById('btn-register');
  btn.textContent = '注册中...'; btn.disabled = true;
  try {
    const resp = await fetch(`${API}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password, company_name: company })
    });
    const data = await resp.json();
    if (data.error) { errEl.textContent = data.error; btn.textContent='注册'; btn.disabled=false; return; }
    setToken(data.token);
    currentUser = data.user;
    document.querySelector('.sidebar').style.display = '';
    updateSidebarUser();
    renderPage();
  } catch(e) {
    errEl.textContent = '网络错误，请重试';
    btn.textContent='注册'; btn.disabled=false;
  }
}

function logout() {
  clearToken();
  currentUser = null;
  companyData = null;
  showLogin();
}

function updateSidebarUser() {
  let el = document.getElementById('sidebar-user');
  if (!el) {
    const brand = document.querySelector('.sidebar-brand');
    el = document.createElement('div');
    el.id = 'sidebar-user';
    el.className = 'sidebar-user';
    brand.insertAdjacentElement('afterend', el);
  }
  if (currentUser) {
    const planLabel = { free: '免费版', pro: '专业版', enterprise: '企业版' }[currentUser.plan] || currentUser.plan;
    el.innerHTML = `
      <div class="user-info">
        <span class="user-name">${currentUser.name}</span>
        <span class="user-plan">${planLabel}</span>
      </div>
      <button class="btn-logout" onclick="logout()">退出</button>
    `;
  }
}

// ========== Router ==========

document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    el.classList.add('active');
    currentPage = el.dataset.page;
    renderPage();
  });
});

async function renderPage() {
  if (!isLoggedIn()) { showLogin(); return; }
  const main = document.getElementById('main-content');
  if (!companyData) {
    try { await loadCompany(); } catch(e) { console.warn('loadCompany failed:', e); }
  }
  const renderers = {
    quickstart: renderQuickstart,
    dashboard: renderDashboard,
    diagnose: renderDiagnose,
    monitor: renderMonitor,
    optimize: renderOptimize,
    content: renderContent,
    tasks: renderTasks,
    report: renderReport,
    keywords: renderKeywords,
    scheduler: renderScheduler,
    competitors: renderCompetitors,
    benchmark: renderBenchmark,
    sheep: renderSheep,
    strategies: renderStrategies,
    ingest: renderIngest,
    chat: renderChat,
    gdo: renderGDO,
    decision: renderDecision,
    maturity: renderMaturity,
    abtest: renderABTest,
    pdfdedup: renderPdfDedup,
    compliance: renderCompliance,
    billing: renderBilling,
  };
  const fn = renderers[currentPage];
  if (fn) fn(main);
}

async function loadCompany() {
  const resp = await fetch(`${API}/api/companies`, { headers: authHeaders() });
  if (resp.status === 401) { clearToken(); showLogin(); return; }
  if (!resp.ok) throw new Error(`companies API: ${resp.status}`);
  const companies = await resp.json();
  if (companies.length > 0) {
    companyData = companies[0];
    const reportResp = await fetch(`${API}/api/companies/${companyData.id}/report`, { headers: authHeaders() });
    if (!reportResp.ok) throw new Error(`report API: ${reportResp.status}`);
    companyData.report = await reportResp.json();
  }
  try {
    const casesResp = await fetch(`${API}/api/cases`, { headers: authHeaders() });
    if (casesResp.ok) casesData = await casesResp.json();
  } catch(e) { console.warn('load cases failed:', e); }
}

function authHeaders() {
  const token = getToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function apiPost(url, data) {
  try {
    const resp = await fetch(`${API}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(data),
    });
    if (resp.status === 401) { clearToken(); showLogin(); return { error: '请先登录' }; }
    return await resp.json();
  } catch(e) {
    return { success: false, error: e.message };
  }
}

async function apiGet(url) {
  try {
    const resp = await fetch(`${API}${url}`, { headers: authHeaders() });
    if (resp.status === 401) { clearToken(); showLogin(); return { error: '请先登录' }; }
    return await resp.json();
  } catch(e) {
    return { success: false, error: e.message };
  }
}

// ========== 快速上手 ==========

const qsState = { company: '', url: '', industry: '', sheep: null };

function renderQuickstart(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>快速上手</h1><p>三步完成GEO体检：填写公司信息 → 网站体检评分 → AI引擎展示检查</p></div>
    </div>
    <div class="qs-steps">
      <div class="qs-step active" id="qs-ind-1"><span class="qs-step-num">1</span>公司信息</div>
      <div class="qs-step-line"></div>
      <div class="qs-step" id="qs-ind-2"><span class="qs-step-num">2</span>网站体检</div>
      <div class="qs-step-line"></div>
      <div class="qs-step" id="qs-ind-3"><span class="qs-step-num">3</span>AI展示检查</div>
    </div>
    <div id="qs-body">
      <div class="card" style="max-width:640px">
        <div class="card-header"><span class="card-title">填写公司信息</span><span style="font-size:12px;color:var(--text-muted)">约需2-4分钟完成全部体检</span></div>
        <div style="display:flex;flex-direction:column;gap:12px">
          <div>
            <label style="font-size:12px;color:var(--text-muted)">公司名称 *</label>
            <input type="text" id="qs-company" style="width:100%" placeholder="如：四川木子杨科技有限公司" value="${companyData ? companyData.name : ''}">
          </div>
          <div>
            <label style="font-size:12px;color:var(--text-muted)">公司官网 *</label>
            <input type="text" id="qs-url" style="width:100%" placeholder="如：mzyai.com 或 https://www.example.com" value="${companyData ? (companyData.website || '') : ''}">
          </div>
          <div>
            <label style="font-size:12px;color:var(--text-muted)">所属行业（可选，影响评分基准）</label>
            <input type="text" id="qs-industry" style="width:100%" placeholder="如：科技 / 文旅 / 制造" value="${companyData ? (companyData.industry || '') : ''}">
          </div>
          <button class="btn btn-primary" style="align-self:flex-start" onclick="qsStart()">开始GEO体检</button>
        </div>
      </div>
    </div>
  `;
}

function _qsSetStep(n) {
  for (let i = 1; i <= 3; i++) {
    const ind = document.getElementById(`qs-ind-${i}`);
    if (!ind) continue;
    ind.classList.remove('active', 'done');
    if (i < n) ind.classList.add('done');
    if (i === n) ind.classList.add('active');
  }
}

function qsGoto(page) {
  const nav = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (nav) nav.click();
}

async function qsStart() {
  const company = document.getElementById('qs-company').value.trim();
  const url = document.getElementById('qs-url').value.trim();
  const industry = document.getElementById('qs-industry').value.trim();
  if (!company || !url) {
    alert('请填写公司名称和官网地址');
    return;
  }
  qsState.company = company;
  qsState.url = url;
  qsState.industry = industry;

  _qsSetStep(2);
  const body = document.getElementById('qs-body');
  body.innerHTML = `
    <div class="card" style="max-width:640px">
      <div style="text-align:center;padding:28px">
        <div class="spinner" style="margin:0 auto 14px"></div>
        <div style="font-size:15px;font-weight:600;margin-bottom:6px">正在体检网站...</div>
        <div style="font-size:12px;color:var(--text-muted)">抓取官网页面 → 客观指标检测 → AI五维评估（SHEEP模型）</div>
      </div>
    </div>
  `;

  const result = await apiPost('/api/sheep-score', {
    company_name: company, industry, url, auto_diagnose: true,
  });
  if (!result.success) {
    body.innerHTML = `
      <div class="card" style="max-width:640px">
        <p style="color:var(--danger)">体检失败：${result.error || '未知错误'}</p>
        <button class="btn" onclick="renderPage()">返回重试</button>
      </div>
    `;
    return;
  }
  qsState.sheep = result.data;
  _qsRenderSheep(body, result.data);
}

function _qsRenderSheep(el, d) {
  const gem = d.gem_score;
  const gradeColor = gem >= 80 ? 'var(--accent)' : gem >= 60 ? 'var(--warning)' : 'var(--danger)';
  const dims = d.dimensions || {};
  const weakest = Object.entries(dims).sort((a, b) => a[1].score - b[1].score)[0];

  el.innerHTML = `
    <div class="grid-3" style="margin-bottom:14px">
      <div class="metric">
        <div class="metric-value" style="color:${gradeColor}">${gem}</div>
        <div class="metric-label">GEM综合分 (Grade ${d.grade})</div>
      </div>
      <div class="metric">
        <div class="metric-value">${d.diagnosis ? d.diagnosis.overall_score : '--'}</div>
        <div class="metric-label">网站技术体检分</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="font-size:18px;line-height:2.2">${weakest ? `${weakest[0]} ${weakest[1].name}` : '--'}</div>
        <div class="metric-label">最弱维度（优先补强）</div>
      </div>
    </div>
    <div class="card" style="margin-bottom:14px">
      <div class="card-header"><span class="card-title">SHEEP五维得分</span></div>
      ${Object.entries(dims).map(([k, v]) => {
        const color = v.score >= 70 ? 'var(--accent)' : v.score >= 50 ? 'var(--warning)' : 'var(--danger)';
        return `<div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;font-size:12px">
            <span><strong>${k}</strong> ${v.name}（权重${v.weight}）</span>
            <span style="color:${color}">${v.score}分 ${v.grade}</span>
          </div>
          <div class="progress-bar" style="height:8px"><div class="progress-fill" style="width:${v.score}%;background:${color}"></div></div>
        </div>`;
      }).join('')}
    </div>
    <div style="display:flex;gap:10px;align-items:center">
      <button class="btn btn-primary" onclick="qsStartMonitor()">下一步：检查AI引擎中的展示情况</button>
      <span style="font-size:12px;color:var(--text-muted)">向5个AI引擎发起真实查询，验证品牌是否被提及（约1-2分钟）</span>
    </div>
  `;
}

async function qsStartMonitor() {
  _qsSetStep(3);
  const body = document.getElementById('qs-body');
  body.innerHTML = `
    <div class="card" style="max-width:640px">
      <div style="text-align:center;padding:28px">
        <div class="spinner" style="margin:0 auto 14px"></div>
        <div style="font-size:15px;font-weight:600;margin-bottom:6px">正在向AI引擎发起查询...</div>
        <div style="font-size:12px;color:var(--text-muted)" id="qs-monitor-progress">DeepSeek / Kimi / 豆包 / 文心 / 通义 并行查询中</div>
      </div>
    </div>
  `;

  const startResp = await apiPost('/api/monitor/start', {
    company: qsState.company,
    industry: qsState.industry,
    keywords: null,
  });
  if (!startResp.success) {
    body.innerHTML = `
      <div class="card" style="max-width:640px">
        <p style="color:var(--danger)">监控启动失败：${startResp.error || '未知错误'}</p>
        <button class="btn" onclick="qsRenderFinal(null)">跳过此步，查看体检结论</button>
      </div>
    `;
    return;
  }
  _qsPollMonitor(startResp.task_id);
}

function _qsPollMonitor(taskId) {
  const body = document.getElementById('qs-body');
  const poll = async () => {
    try {
      const resp = await fetch(`${API}/api/monitor/status/${taskId}`);
      const result = await resp.json();
      if (!result.success) {
        qsRenderFinal(null);
        return;
      }
      const d = result.data;
      if (d.status === 'running') {
        const prog = document.getElementById('qs-monitor-progress');
        if (prog) prog.textContent = `步骤 ${d.current_step}/${d.total_steps}：${d.current_desc}（${d.progress || 0}%）`;
        setTimeout(poll, 2000);
      } else if (d.status === 'done') {
        qsRenderFinal(d.result);
      } else {
        qsRenderFinal(null);
      }
    } catch(e) {
      qsRenderFinal(null);
    }
  };
  setTimeout(poll, 1500);
}

function qsRenderFinal(monitor) {
  const body = document.getElementById('qs-body');
  if (!body) return;
  const sheep = qsState.sheep || {};
  const gem = sheep.gem_score || 0;
  const overall = monitor ? (monitor.overall || {}) : null;

  const actions = [];
  if (gem < 70) actions.push({ page: 'optimize', title: '网站优化', desc: '按体检问题清单逐项修复网站，提升AI可读性' });
  actions.push({ page: 'content', title: '内容生成', desc: '产出AI引擎偏好的结构化内容（发布前自动过合规检测）' });
  if (overall && (overall.avg_display_rate || 0) < 30) actions.push({ page: 'strategies', title: '内容优化策略', desc: '对已有内容做GEO改写，提升被引用概率' });
  actions.push({ page: 'scheduler', title: '定时监控', desc: '设置周期性监控，持续跟踪AI展示率变化' });
  actions.push({ page: 'compliance', title: '内容合规检测', desc: '发布内容前手动复检，规避监管红线' });

  body.innerHTML = `
    ${overall ? `
    <div class="grid-4" style="margin-bottom:14px">
      <div class="metric">
        <div class="metric-value" style="color:${overall.avg_display_rate > 30 ? 'var(--accent)' : 'var(--danger)'}">${overall.avg_display_rate || 0}%</div>
        <div class="metric-label">AI引擎展示率</div>
      </div>
      <div class="metric">
        <div class="metric-value">${overall.total_mentions || 0} / ${overall.total_queries || 0}</div>
        <div class="metric-label">被提及 / 总查询</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="color:${(overall.avg_accuracy || 0) >= 70 ? 'var(--accent)' : 'var(--warning)'}">${overall.avg_accuracy || 0}%</div>
        <div class="metric-label">信息准确率</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="color:${(overall.negative_rate || 0) > 0 ? 'var(--danger)' : 'var(--accent)'}">${overall.negative_rate || 0}%</div>
        <div class="metric-label">负面提及率</div>
      </div>
    </div>` : `
    <div class="card" style="margin-bottom:14px"><p style="font-size:13px;color:var(--text-muted)">AI展示检查未完成，以下结论仅基于网站体检。可稍后在「AI监控」页重新发起查询。</p></div>`}

    <div class="card">
      <div class="card-header"><span class="card-title">体检结论与下一步</span></div>
      <div style="font-size:13px;line-height:1.8;margin-bottom:12px">
        ${qsConclusion(gem, overall)}
      </div>
      <div style="display:flex;flex-direction:column;gap:8px">
        ${actions.map((a, i) => `
          <div style="display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid var(--border);border-radius:6px;background:rgba(255,255,255,0.02)">
            <span style="font-size:12px;color:var(--text-muted);width:20px">${i + 1}</span>
            <div style="flex:1">
              <div style="font-size:13px;font-weight:600">${a.title}</div>
              <div style="font-size:12px;color:var(--text-muted)">${a.desc}</div>
            </div>
            <button class="btn" onclick="qsGoto('${a.page}')">前往</button>
          </div>
        `).join('')}
      </div>
    </div>
    <div style="margin-top:12px">
      <button class="btn" onclick="qsGoto('report')">查看完整诊断报告</button>
      <button class="btn" style="margin-left:8px" onclick="qsGoto('ingest')">深度入库（抓取全站页面）</button>
    </div>
  `;
}

function qsConclusion(gem, overall) {
  const parts = [];
  if (gem >= 80) parts.push(`网站GEO基础扎实（GEM ${gem}分），重点放在内容产出与AI引擎可见性上。`);
  else if (gem >= 60) parts.push(`网站GEO中等（GEM ${gem}分），存在明确短板，先修复网站再做内容推广。`);
  else parts.push(`网站GEO基础薄弱（GEM ${gem}分），AI引擎难以有效读取网站内容，建议优先完成网站优化。`);
  if (overall) {
    const rate = overall.avg_display_rate || 0;
    if (rate >= 50) parts.push(`AI引擎展示率${rate}%，品牌已有一定可见性，继续扩大内容覆盖面。`);
    else if (rate > 0) parts.push(`AI引擎展示率仅${rate}%，多数查询中品牌未被提及，需要系统性内容建设。`);
    else parts.push('AI引擎查询中品牌几乎零提及，处于GEO起点，优化空间最大。');
    if ((overall.negative_rate || 0) > 0) parts.push(`检测到${overall.negative_rate}%负面提及，建议优先排查负面信息来源。`);
  }
  return parts.join(' ');
}

// ========== Dashboard ==========

function renderDashboard(el) {
  if (!companyData || !companyData.report) {
    el.innerHTML = '<div class="loading">加载中...</div>';
    return;
  }

  const r = companyData.report;
  const report = r.report;
  const metrics = r.metrics;
  const issues = r.issues;
  const competitors = r.competitors;
  const tasks = r.tasks;

  const scoreColor = report.score >= 70 ? 'var(--accent)' : report.score >= 40 ? 'var(--warning)' : 'var(--danger)';
  const circumference = 2 * Math.PI * 52;
  const dashOffset = circumference - (report.score / 130) * circumference;

  // 案例效果（优化前后对比）
  const caseCard = (casesData && casesData.length > 0) ? (() => {
    const c = casesData[0];
    const [before, after, git] = c.before_after || [{}, {}, {}];
    const rows = [
      { label: '页面诊断', before: before.diagnose ?? '—', after: after.diagnose ?? '—', unit: '/100', best: 100 },
      { label: 'GEM评分', before: before.gem ?? '—', after: after.gem ?? '—', unit: '', best: null },
      { label: 'E2生态集成', before: before.E2 ?? '—', after: after.E2 ?? '—', unit: '', best: null },
    ];
    return `
      <div class="card" style="grid-column:1/-1">
        <div class="card-header" style="display:flex;align-items:center;justify-content:space-between">
          <span class="card-title">平台效果案例：${c.company_name}（${c.domain}）</span>
          <span style="font-size:12px;color:var(--text-muted)">诊断→优化→复诊闭环 | git: ${git.baseline || 'v1.0-baseline'} → ${git.optimized || 'v1.0-geo-optimized'}</span>
        </div>
        <div class="grid-3" style="margin-top:12px">
          ${rows.map(r => {
            const delta = (typeof r.before === 'number' && typeof r.after === 'number') ? r.after - r.before : null;
            const deltaHtml = delta === null ? '' :
              `<span style="color:${delta >= 0 ? 'var(--accent)' : 'var(--danger)'};font-weight:700"> ${delta >= 0 ? '+' : ''}${delta}${r.unit}</span>`;
            return `
              <div style="background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);padding:14px">
                <div style="font-size:12px;color:var(--text-muted)">${r.label}</div>
                <div style="display:flex;align-items:baseline;gap:10px;margin-top:6px">
                  <span style="font-size:13px;color:var(--text-muted);text-decoration:line-through">${r.before}</span>
                  <span style="color:var(--text-dim)">→</span>
                  <span style="font-size:22px;font-weight:800;color:${r.after >= (r.best || r.before + 1) ? 'var(--accent)' : 'var(--info)'}">${r.after}</span>
                  <span style="font-size:12px;color:var(--text-muted)">${r.unit}</span>
                  ${deltaHtml}
                </div>
              </div>
            `;
          }).join('')}
        </div>
        <p style="font-size:12px;color:var(--text-muted);margin-top:10px;line-height:1.7">${c.summary}</p>
      </div>
    `;
  })() : '';

  const keyMetrics = [
    { label: '大模型引用率', value: getMetric(metrics, '官网内容被大模型引用率'), unit: '%', color: 'var(--danger)' },
    { label: '信息准确率', value: getMetric(metrics, '信息准确率'), unit: '%', color: 'var(--warning)' },
    { label: '页面收录率', value: getMetric(metrics, '官网核心页面收录率'), unit: '%', color: 'var(--warning)' },
    { label: '信源总量', value: getMetric(metrics, '信源总量'), unit: '条', color: 'var(--info)' },
  ];

  el.innerHTML = `
    <div class="page-header">
      <div>
        <h1>${companyData.name}</h1>
        <p>${companyData.domain} | ${companyData.industry} | ${companyData.city}</p>
      </div>
    </div>

    ${caseCard}

    <div class="grid-2" style="margin-bottom:16px">
      <div class="card" style="display:flex;align-items:center;gap:24px">
        <div class="score-ring">
          <svg width="120" height="120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--border)" stroke-width="8"/>
            <circle cx="60" cy="60" r="52" fill="none" stroke="${scoreColor}" stroke-width="8"
              stroke-dasharray="${circumference}" stroke-dashoffset="${dashOffset}"
              stroke-linecap="round" style="transition:stroke-dashoffset 1s ease"/>
          </svg>
          <span class="value" style="color:${scoreColor}">${report.score}</span>
          <span class="label">/130</span>
        </div>
        <div>
          <div style="font-size:14px;color:var(--text-muted)">GEO健康度</div>
          <div style="font-size:24px;font-weight:700;color:${scoreColor}">${report.grade}级</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px">成都本地中小科技服务行业后20%分位</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">核心问题</span></div>
        <p style="font-size:13px;color:var(--text-muted);line-height:1.7">${report.core_issue}</p>
      </div>
    </div>

    <div class="grid-4" style="margin-bottom:16px">
      ${keyMetrics.map(m => `
        <div class="metric">
          <div class="metric-value" style="color:${m.color}">${m.value}<span style="font-size:14px;color:var(--text-muted)">${m.unit}</span></div>
          <div class="metric-label">${m.label}</div>
        </div>
      `).join('')}
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header"><span class="card-title">网站问题 (${issues.length})</span></div>
        ${issues.slice(0, 6).map(i => `
          <div class="issue-item">
            <div class="issue-severity" style="background:${severityColor(i.severity)}"></div>
            <div class="issue-content">
              <div class="issue-title">${i.title}</div>
              <div class="issue-desc">${i.description}</div>
            </div>
            <span class="badge badge-${i.severity}">${i.severity}</span>
          </div>
        `).join('')}
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">竞品对标</span></div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>公司</th><th>信源量</th><th>准确率</th><th>差距</th></tr></thead>
            <tbody>
              ${competitors.map(c => `
                <tr>
                  <td>${c.competitor_name.replace('成都','')}</td>
                  <td>${c.source_count}条</td>
                  <td>${c.ai_accuracy}%</td>
                  <td style="color:var(--danger)">${(c.ai_accuracy - getMetric(metrics, '信息准确率')).toFixed(1)}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

// ========== Diagnose ==========

function renderDiagnose(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>网站诊断</h1><p>输入URL进行GEO诊断，检测技术SEO、结构化数据、AI可读性</p></div>
    </div>
    <div class="input-group">
      <input type="url" id="diag-url" placeholder="输入网址，如 mzyai.com" style="flex:1" value="mzyai.com">
      <button class="btn btn-primary" onclick="runDiagnose()">开始诊断</button>
    </div>
    <div style="margin-top:8px;max-width:640px">
      <label style="font-size:12px;color:var(--text-muted)">源码目录（可选，用于SPA深度分析）</label>
      <input type="text" id="diag-source-dir" style="width:100%" placeholder="如：D:/08_AICode/www.mzyai.com">
    </div>
    <div id="diag-result"></div>
  `;
}

async function runDiagnose() {
  const url = document.getElementById('diag-url').value.trim();
  const sourceDir = document.getElementById('diag-source-dir').value.trim();
  if (!url && !sourceDir) return;
  const resultEl = document.getElementById('diag-result');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div>正在诊断...</div>';

  const payload = { url };
  if (sourceDir) payload.source_dir = sourceDir;
  const result = await apiPost('/api/diagnose', payload);
  if (!result.success) {
    resultEl.innerHTML = `<div class="card"><p style="color:var(--danger)">诊断失败: ${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const scoreColor = d.score >= 70 ? 'var(--accent)' : d.score >= 40 ? 'var(--warning)' : 'var(--danger)';

  resultEl.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-size:13px;color:var(--text-muted)">${d.domain}</div>
          <div style="font-size:36px;font-weight:800;color:${scoreColor}">${d.score}<span style="font-size:16px;color:var(--text-muted)">/100</span></div>
        </div>
        <div style="text-align:right">
          <div style="font-size:12px;color:var(--text-muted)">状态码: ${d.status_code || 'N/A'} | HTML: ${(d.html_size || 0) / 1024 | 0}KB</div>
          ${d.is_spa ? '<div style="font-size:12px;color:var(--warning);font-weight:600;margin-top:4px">SPA单页应用（HTML空壳）</div>' : ''}
        </div>
      </div>
    </div>

    ${d.source_analysis ? `
    <div class="card" style="margin-bottom:14px">
      <div class="card-header"><span class="card-title">源码分析</span></div>
      <div style="font-size:13px;line-height:1.8">
        ${d.source_analysis.framework ? `<div>框架: <strong>${d.source_analysis.framework}</strong></div>` : ''}
        ${d.source_analysis.entry_html ? `<div>入口: ${d.source_analysis.entry_html}</div>` : ''}
        <div>llms.txt: ${d.source_analysis.has_llms_txt ? '已部署' : '未部署'}</div>
        ${d.source_analysis.existing_meta ? `<div>已有meta: ${d.source_analysis.existing_meta.length}个</div>` : ''}
        ${d.source_analysis.existing_json_ld_count !== undefined ? `<div>已有JSON-LD: ${d.source_analysis.existing_json_ld_count}个</div>` : ''}
      </div>
    </div>` : ''}

    <div class="grid-2">
      <div class="card">
        <div class="card-header"><span class="card-title">检查项</span></div>
        ${Object.entries(d.checks).map(([key, check]) => `
          <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
            <span style="font-size:13px">${checkLabel(key)}</span>
            <span style="font-size:12px;color:${check.pass ? 'var(--accent)' : 'var(--danger)'}">${check.pass ? 'PASS' : 'FAIL'}</span>
          </div>
          ${check.detail ? `<div style="font-size:11px;color:var(--text-muted);padding:0 0 8px">${check.detail}</div>` : ''}
        `).join('')}
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">发现的问题 (${d.issues.length})</span></div>
        ${d.issues.length === 0 ? '<p style="color:var(--accent);font-size:13px">未发现问题</p>' :
          d.issues.map(i => `
            <div class="issue-item">
              <div class="issue-severity" style="background:${severityColor(i.severity)}"></div>
              <div class="issue-content">
                <div class="issue-title">${i.category}: ${i.message}</div>
                ${i.fix ? `<div style="font-size:11px;color:var(--accent);margin-top:2px">修复: ${i.fix}</div>` : ''}
              </div>
              <span class="badge badge-${i.severity}">${i.severity}</span>
            </div>
          `).join('')}
      </div>
    </div>
  `;
}

// ========== Monitor ==========

function renderMonitor(el) {
  const cid = companyData ? companyData.id : '';
  el.innerHTML = `
    <div class="page-header">
      <div><h1>AI搜索监控</h1><p>5个AI引擎并行查询品牌展示率、信息准确率、负面提及率</p></div>
    </div>
    <div class="input-group">
      <input type="text" id="monitor-company" placeholder="公司名称" style="flex:1" value="${companyData ? companyData.name : ''}">
      <button class="btn btn-primary" onclick="runMonitor()">查询监控</button>
    </div>
    <div class="card" style="margin-top:10px">
      <div class="card-header"><span class="card-title">自定义查询词（可选）</span></div>
      <textarea id="monitor-keywords" style="width:100%;height:70px;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:12px;line-height:1.6" placeholder="每行一个查询词（最多取前4个），留空则用公司名自动推导（如：公司名 / 公司名怎么样 / 行业推荐）"></textarea>
    </div>
    <div id="monitor-result"></div>
    <div id="monitor-visibility" style="margin-top:16px"></div>
    <div id="monitor-history" style="margin-top:16px"></div>
  `;
  if (cid) {
    loadVisibilityScore(cid);
    loadMonitorHistory(cid);
  }
}

async function loadVisibilityScore(cid) {
  const el = document.getElementById('monitor-visibility');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>加载可见性评分...</div>';
  const data = await apiGet(`/api/monitor/visibility-score/${cid}`);
  if (data.score === null || data.score === undefined) {
    el.innerHTML = '<div class="card"><p style="color:var(--text-muted);padding:12px">暂无评分数据，请先执行监控</p></div>';
    return;
  }
  const gradeColor = { A: 'var(--accent)', B: 'var(--accent)', C: 'var(--warning)', D: 'var(--danger)', F: 'var(--danger)' };
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">可见性评分</span><span style="font-size:12px;color:var(--text-muted)">${data.created_at || ''}</span></div>
      <div style="display:flex;align-items:center;gap:24px;padding:16px">
        <div style="text-align:center;min-width:100px">
          <div style="font-size:42px;font-weight:700;color:${gradeColor[data.grade] || 'var(--text-muted)'}">${data.score}</div>
          <div style="font-size:14px;color:var(--text-muted)">评分 / 100</div>
          <div style="margin-top:4px"><span class="badge badge-${data.grade === 'A' || data.grade === 'B' ? 'success' : data.grade === 'C' ? 'medium' : 'high'}">等级 ${data.grade}</span></div>
        </div>
        <div style="flex:1;display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
          <div class="metric">
            <div class="metric-value" style="color:${data.display_rate > 30 ? 'var(--accent)' : 'var(--danger)'}">${data.display_rate}%</div>
            <div class="metric-label">展示率</div>
          </div>
          <div class="metric">
            <div class="metric-value" style="color:${data.accuracy > 70 ? 'var(--accent)' : 'var(--warning)'}">${data.accuracy}%</div>
            <div class="metric-label">准确率</div>
          </div>
          <div class="metric">
            <div class="metric-value" style="color:${data.negative_rate > 0 ? 'var(--danger)' : 'var(--accent)'}">${data.negative_rate}%</div>
            <div class="metric-label">负面率</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function loadMonitorHistory(cid) {
  const el = document.getElementById('monitor-history');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>加载历史记录...</div>';
  const data = await apiGet(`/api/monitor/history/${cid}?per_page=10`);
  if (!data.data || data.data.length === 0) {
    el.innerHTML = '<div class="card"><p style="color:var(--text-muted);padding:12px">暂无历史记录</p></div>';
    return;
  }
  const rows = data.data.map(r => `
    <tr>
      <td style="font-size:12px;color:var(--text-muted)">${r.created_at || ''}</td>
      <td>${r.display_rate || 0}%</td>
      <td>${r.accuracy_score || 0}%</td>
      <td>${r.mention_count || 0}/${r.total_queries || 0}</td>
      <td><span class="badge badge-${r.snapshot_type === 'scheduled' ? 'success' : 'medium'}">${r.snapshot_type === 'scheduled' ? '定时' : '手动'}</span></td>
    </tr>
  `).join('');
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">监控历史</span><span style="font-size:12px;color:var(--text-muted)">共${data.total}条</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>时间</th><th>展示率</th><th>准确率</th><th>提及/查询</th><th>类型</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}

async function runMonitor() {
  const company = document.getElementById('monitor-company').value.trim();
  if (!company) return;
  const resultEl = document.getElementById('monitor-result');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div>启动监控任务...</div>';

  const customKeywords = document.getElementById('monitor-keywords').value
    .split(/\n/)
    .map(k => k.trim())
    .filter(k => k);

  const startResp = await apiPost('/api/monitor/start', {
    company,
    keywords: customKeywords.length ? customKeywords : null,
    industry: companyData ? companyData.industry : '',
    city: companyData ? companyData.city : '',
  });
  if (!startResp.success) {
    resultEl.innerHTML = `<div class="card"><p style="color:var(--danger)">${startResp.error}</p></div>`;
    return;
  }
  _pollMonitor(startResp.task_id, resultEl);
}

function _pollMonitor(taskId, el) {
  const poll = async () => {
    try {
      const resp = await fetch(`${API}/api/monitor/status/${taskId}`, { headers: authHeaders() });
      if (resp.status === 401) { clearToken(); showLogin(); return; }
      const result = await resp.json();
      if (!result.success) {
        el.innerHTML = `<div class="card"><p style="color:var(--danger)">任务查询失败</p></div>`;
        return;
      }
      const d = result.data;
      if (d.status === 'running') {
        const pct = d.progress || 0;
        el.innerHTML = `
          <div class="card" style="margin-top:16px">
            <div style="text-align:center;padding:20px">
              <div class="spinner" style="margin:0 auto 12px"></div>
              <div style="font-size:14px;font-weight:600;margin-bottom:8px">5个AI引擎并行查询中... ${pct}%</div>
              <div class="progress-bar" style="width:300px;margin:0 auto"><div class="progress-fill" style="width:${pct}%"></div></div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:8px">步骤 ${d.current_step}/${d.total_steps}: ${d.current_desc}</div>
            </div>
          </div>
        `;
        setTimeout(poll, 2000);
      } else if (d.status === 'done') {
        _renderMonitorResult(el, d.result);
        if (companyData) {
          loadVisibilityScore(companyData.id);
          loadMonitorHistory(companyData.id);
        }
      } else if (d.status === 'failed') {
        el.innerHTML = `<div class="card"><p style="color:var(--danger)">监控失败: ${d.error || '未知错误'}</p></div>`;
      }
    } catch(e) { console.warn('_pollMonitor:', e); }
  };
  setTimeout(poll, 1000);
}

function _renderMonitorResult(el, d) {
  const overall = d.overall || {};

  el.innerHTML = `
    <div class="grid-4" style="margin-bottom:16px">
      <div class="metric">
        <div class="metric-value" style="color:${overall.avg_display_rate > 30 ? 'var(--accent)' : 'var(--danger)'}">${overall.avg_display_rate || 0}%</div>
        <div class="metric-label">平均展示率</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="color:${overall.avg_accuracy > 70 ? 'var(--accent)' : 'var(--warning)'}">${overall.avg_accuracy || 0}%</div>
        <div class="metric-label">信息准确率</div>
      </div>
      <div class="metric">
        <div class="metric-value">${overall.total_mentions || 0} <span style="font-size:13px;color:var(--text-muted)">/ ${overall.total_queries || 0}</span></div>
        <div class="metric-label">被提及 / 总查询</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="color:${(overall.negative_rate || 0) > 0 ? 'var(--danger)' : 'var(--accent)'}">${overall.negative_rate || 0}%</div>
        <div class="metric-label">负面提及率</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><span class="card-title">各平台展示情况</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>平台</th><th>展示率</th><th>准确度</th><th>备注</th></tr></thead>
          <tbody>
            ${Object.entries(d.platforms || {}).map(([key, p]) => `
              <tr>
                <td style="font-weight:600">${p.label || key}</td>
                <td>
                  <div style="display:flex;align-items:center;gap:8px">
                    <div class="progress-bar" style="width:80px">
                      <div class="progress-fill" style="width:${p.display_rate || 0}%;background:${(p.display_rate||0) > 30 ? 'var(--accent)' : 'var(--danger)'}"></div>
                    </div>
                    <span>${p.display_rate || 0}%（${p.mention_count || 0}/${p.total_queries || 0}）</span>
                  </div>
                </td>
                <td><span class="badge badge-${p.accuracy === '高' ? 'success' : p.accuracy === '中' ? 'medium' : 'high'}">${p.accuracy || '-'}</span></td>
                <td style="font-size:12px;color:var(--text-muted)">${p.note || '-'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// ========== Optimize ==========

function renderOptimize(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>网站AI优化</h1><p>一键生成llms.txt、JSON-LD、robots.txt等AI友好配置</p></div>
      <div style="display:flex;gap:8px">
        <button class="btn btn-primary" onclick="generateAll()">一键生成全部</button>
        <button class="btn" onclick="patchSource()">源码注入</button>
      </div>
    </div>
    <div class="card" style="margin-bottom:14px;max-width:640px">
      <div style="display:flex;flex-direction:column;gap:10px">
        <div>
          <label style="font-size:12px;color:var(--text-muted)">源码目录（可选，填入后"源码注入"可直改index.html）</label>
          <input type="text" id="opt-source-dir" style="width:100%" placeholder="如：D:/08_AICode/www.mzyai.com 或 /opt/mzyai.com">
        </div>
        <div>
          <label style="font-size:12px;color:var(--text-muted)">ICP备案号（可选，注入到JSON-LD和footer）</label>
          <input type="text" id="opt-icp" style="width:100%" placeholder="如：蜀ICP备2024067258号">
        </div>
      </div>
    </div>
    <div class="tabs">
      <div class="tab active" data-tab="llms" onclick="switchOptTab(this,'llms')">llms.txt</div>
      <div class="tab" data-tab="jsonld" onclick="switchOptTab(this,'jsonld')">JSON-LD</div>
      <div class="tab" data-tab="robots" onclick="switchOptTab(this,'robots')">robots.txt</div>
    </div>
    <div id="opt-content">
      <p style="color:var(--text-muted);font-size:13px)">点击"一键生成全部"生成配置文件，或"源码注入"直接修改源码index.html</p>
    </div>
  `;
}

function switchOptTab(tabEl, tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  tabEl.classList.add('active');
  if (window._optData) showOptTab(tab);
}

async function generateAll() {
  const resultEl = document.getElementById('opt-content');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div>生成中...</div>';

  const result = await apiPost('/api/optimize', {
    action: 'generate_all',
    company: companyData ? companyData.name : '四川木子杨科技有限公司',
    domain: companyData ? companyData.domain : 'mzyai.com',
    description: companyData ? companyData.description : 'AI网关聚合服务',
    industry: companyData ? companyData.industry : 'AI网关聚合服务',
    city: companyData ? companyData.city : '成都',
    allow_ai_crawlers: true,
  });

  if (!result.success) {
    resultEl.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  window._optData = result.data;
  showOptTab('llms');
}

function showOptTab(tab) {
  const d = window._optData;
  const resultEl = document.getElementById('opt-content');

  if (tab === 'llms' && d.llms_txt) {
    resultEl.innerHTML = `
      <div class="card">
        <div class="card-header"><span class="card-title">llms.txt</span><span style="font-size:12px;color:var(--text-muted)">部署路径: ${d.llms_txt.deploy_path}</span></div>
        <div class="code-block"><button class="copy-btn" onclick="copyCode(this)">复制</button>${escapeHtml(d.llms_txt.content)}</div>
      </div>
    `;
  } else if (tab === 'jsonld' && d.json_ld) {
    resultEl.innerHTML = `
      <div class="card">
        <div class="card-header"><span class="card-title">JSON-LD 结构化数据</span><span style="font-size:12px;color:var(--text-muted)">${d.json_ld.deploy}</span></div>
        ${d.json_ld.schemas.map(s => `
          <div style="margin-bottom:12px">
            <div style="font-size:12px;color:var(--accent);margin-bottom:4px;font-weight:600">${s.type}</div>
            <div class="code-block"><button class="copy-btn" onclick="copyCode(this)">复制</button>${escapeHtml(s.json_ld)}</div>
          </div>
        `).join('')}
      </div>
    `;
  } else if (tab === 'robots' && d.robots_txt) {
    resultEl.innerHTML = `
      <div class="card">
        <div class="card-header"><span class="card-title">robots.txt</span><span style="font-size:12px;color:var(--text-muted)">部署路径: ${d.robots_txt.deploy_path}</span></div>
        <div class="code-block"><button class="copy-btn" onclick="copyCode(this)">复制</button>${escapeHtml(d.robots_txt.content)}</div>
      </div>
    `;
  }

  if (d.deploy_checklist) {
    resultEl.innerHTML += `
      <div class="card" style="margin-top:16px">
        <div class="card-header"><span class="card-title">部署清单</span></div>
        ${d.deploy_checklist.map(item => `<div style="padding:6px 0;font-size:13px;color:var(--text-muted)">${item}</div>`).join('')}
      </div>
    `;
  }
}

async function patchSource() {
  const sourceDir = document.getElementById('opt-source-dir').value.trim();
  const icp = document.getElementById('opt-icp').value.trim();
  if (!sourceDir) {
    alert('请填写源码目录路径（如 D:/08_AICode/www.mzyai.com）');
    return;
  }
  const resultEl = document.getElementById('opt-content');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div>正在注入GEO补丁到源码...</div>';

  const result = await apiPost('/api/optimize', {
    action: 'patch_source',
    source_dir: sourceDir,
    company: companyData ? companyData.name : '四川木子杨科技有限公司',
    domain: companyData ? companyData.domain : 'mzyai.com',
    description: companyData ? companyData.description : 'AI网关聚合服务',
    industry: companyData ? companyData.industry : 'AI网关聚合服务',
    city: companyData ? companyData.city : '成都',
    icp: icp,
    allow_ai_crawlers: true,
  });

  if (!result.success) {
    resultEl.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }
  const d = result.data;
  resultEl.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">源码注入完成</span></div>
      <div style="font-size:13px;line-height:1.8">
        <p>已修改 <strong>${d.entry_html}</strong>，注入 ${d.patches_applied.length} 项GEO补丁：</p>
        <ul>${d.patches_applied.map(p => `<li>${p}</li>`).join('')}</ul>
        ${d.generated_files.length > 0 ? `<p>生成静态文件：</p><ul>${d.generated_files.map(f => `<li>${f}</li>`).join('')}</ul>` : ''}
        <p style="margin-top:8px;color:var(--text-muted)">${d.message}</p>
      </div>
    </div>
  `;
}

// ========== Content ==========

function renderContent(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>GEO内容生成</h1><p>生成AI搜索友好的FAQ、公司介绍、竞品对比、接入教程</p></div>
    </div>
    <div class="input-group">
      <select id="content-type">
        <option value="faq">FAQ常见问题</option>
        <option value="about">公司介绍</option>
        <option value="comparison">竞品对比</option>
        <option value="guide">接入教程</option>
      </select>
      <button class="btn btn-primary" onclick="generateContent()">生成内容</button>
    </div>
    <div id="content-result"></div>
  `;
}

async function generateContent() {
  const type = document.getElementById('content-type').value;
  const resultEl = document.getElementById('content-result');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div>生成中...</div>';

  const result = await apiPost('/api/content/generate', {
    action: 'generate',
    content_type: type,
    company: companyData ? companyData.name : '四川木子杨科技有限公司',
    domain: companyData ? companyData.domain : 'mzyai.com',
    industry: companyData ? companyData.industry : 'AI网关聚合服务',
    keywords: ['AI网关', '大模型API', 'API接入', '成都AI公司'],
  });

  if (!result.success) {
    resultEl.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  resultEl.innerHTML = `
    <div class="card">
      <div class="card-header">
        <span class="card-title">${typeLabel(type)}</span>
        <span class="badge badge-${result.data.mode === 'production' ? 'success' : 'pending'}">${result.data.mode === 'production' ? 'AI生成' : 'Demo'}</span>
      </div>
      <div class="code-block"><button class="copy-btn" onclick="copyCode(this)">复制</button>${escapeHtml(result.data.content)}</div>
    </div>
  `;
}

// ========== Tasks ==========

function renderTasks(el) {
  if (!companyData || !companyData.report) {
    el.innerHTML = '<div class="loading">加载中...</div>';
    return;
  }

  const tasks = companyData.report.tasks || [];

  el.innerHTML = `
    <div class="page-header">
      <div><h1>优化任务</h1><p>按ROI排序的GEO优化任务清单</p></div>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead><tr><th>ROI</th><th>优先级</th><th>类型</th><th>任务</th><th>状态</th></tr></thead>
          <tbody>
            ${tasks.map(t => `
              <tr>
                <td><span style="font-weight:700;color:${t.roi_score >= 7 ? 'var(--accent)' : t.roi_score >= 5 ? 'var(--warning)' : 'var(--text-muted)'}">${t.roi_score}</span></td>
                <td><span class="badge badge-${t.priority === 'high' ? 'high' : t.priority === 'medium' ? 'medium' : 'low'}">${t.priority}</span></td>
                <td style="font-size:12px">${typeLabel(t.task_type)}</td>
                <td>
                  <div style="font-weight:600;font-size:13px">${t.title}</div>
                  <div style="font-size:11px;color:var(--text-muted)">${t.description}</div>
                </td>
                <td><span class="badge badge-${t.status === 'done' ? 'done' : 'pending'}">${t.status === 'done' ? '已完成' : '待处理'}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// ========== Report ==========

function renderReport(el) {
  const cid = companyData ? companyData.id : '';
  el.innerHTML = `
    <div class="page-header">
      <div><h1>综合GEO诊断报告</h1><p>多模型并发探针 + AI深度合成 + 30/60/90天行动计划</p></div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <button class="btn btn-primary" onclick="runProbe()">多模型探针</button>
        <button class="btn" onclick="runActionPlan()">行动计划</button>
        <button class="btn" onclick="runFullReport()">完整报告</button>
        <a class="btn" href="javascript:exportPdf(${cid || 1})" style="text-decoration:none">PDF导出</a>
        <a class="btn" href="javascript:exportCsv(${cid || 1})" style="text-decoration:none">CSV导出</a>
      </div>
    </div>
    <div id="report-result">
      <div class="card">
        <p style="color:var(--text-muted);font-size:13px">选择上方操作开始生成报告：</p>
        <ul style="color:var(--text-muted);font-size:13px;padding-left:20px;margin-top:8px">
          <li><strong>多模型探针</strong>：5个AI模型并发查询品牌信息，统计展示率</li>
          <li><strong>行动计划</strong>：AI生成30/60/90天分阶段优化方案</li>
          <li><strong>完整报告</strong>：探针+合成+行动计划一体化</li>
          <li><strong>PDF导出</strong>：基于已有数据生成可打印报告</li>
          <li><strong>CSV导出</strong>：导出监控历史数据为CSV</li>
        </ul>
      </div>
    </div>
    <div id="report-history" style="margin-top:16px"></div>
  `;
  if (cid) loadReportHistory(cid);
}

async function loadReportHistory(cid) {
  const el = document.getElementById('report-history');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>加载报告历史...</div>';
  const data = await apiGet(`/api/report-history/${cid}`);
  if (!data.success || !data.data || data.data.length === 0) {
    el.innerHTML = '<div class="card"><p style="color:var(--text-muted);padding:12px">暂无报告历史</p></div>';
    return;
  }
  const rows = data.data.map(r => `
    <tr>
      <td style="font-size:12px;color:var(--text-muted)">${r.created_at || ''}</td>
      <td style="font-weight:600;color:${(r.score||0) >= 70 ? 'var(--accent)' : (r.score||0) >= 40 ? 'var(--warning)' : 'var(--danger)'}">${r.score || 0}</td>
      <td><span class="badge badge-${(r.grade||'D') >= 'B' ? 'success' : (r.grade||'D') >= 'C' ? 'medium' : 'high'}">${r.grade || 'D'}</span></td>
      <td><a class="btn btn-sm" href="javascript:exportPdf(${cid})" style="padding:2px 8px;font-size:11px;text-decoration:none">查看</a></td>
    </tr>
  `).join('');
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">报告历史</span><span style="font-size:12px;color:var(--text-muted)">共${data.data.length}份</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>生成时间</th><th>评分</th><th>等级</th><th>操作</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}

async function exportPdf(cid) {
  const token = getToken();
  if (!token) { showLogin(); return; }
  const resp = await fetch(`${API}/api/report-pdf/${cid}`, { headers: { 'Authorization': `Bearer ${token}` } });
  if (resp.status === 401) { clearToken(); showLogin(); return; }
  const html = await resp.text();
  const w = window.open('', '_blank');
  if (w) { w.document.write(html); w.document.close(); }
  else alert('请允许弹窗以查看PDF报告');
}

async function exportCsv(cid) {
  const token = getToken();
  if (!token) { showLogin(); return; }
  const resp = await fetch(`${API}/api/report-csv/${cid}`, { headers: { 'Authorization': `Bearer ${token}` } });
  if (resp.status === 401) { clearToken(); showLogin(); return; }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `monitor_history_${cid}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

async function runProbe() {
  const resultEl = document.getElementById('report-result');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div>5个AI模型并发探针中，预计30秒...</div>';

  const result = await apiPost('/api/probe', {
    company: companyData ? companyData.name : '四川木子杨科技有限公司',
  });

  if (!result.success) {
    resultEl.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const probeResults = d.probe_results || {};

  let totalMentions = 0, totalQueries = 0;
  Object.values(probeResults).forEach(p => {
    totalMentions += p.mention_count || 0;
    totalQueries += p.total_queries || 0;
  });
  const avgRate = totalQueries > 0 ? (totalMentions / totalQueries * 100).toFixed(1) : 0;

  resultEl.innerHTML = `
    <div class="grid-3" style="margin-bottom:16px">
      <div class="metric">
        <div class="metric-value">${Object.keys(probeResults).length}</div>
        <div class="metric-label">探测模型数</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="color:${avgRate > 30 ? 'var(--accent)' : 'var(--danger)'}">${avgRate}%</div>
        <div class="metric-label">平均展示率</div>
      </div>
      <div class="metric">
        <div class="metric-value">${totalMentions}/${totalQueries}</div>
        <div class="metric-label">提及/总查询</div>
      </div>
    </div>

    ${Object.entries(probeResults).map(([modelId, pData]) => `
      <div class="card" style="margin-bottom:12px">
        <div class="card-header">
          <span class="card-title">${pData.label}</span>
          <span style="font-size:13px;color:${pData.display_rate > 30 ? 'var(--accent)' : 'var(--danger)'}">展示率 ${pData.display_rate}%</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>查询</th><th>提及</th><th>准确度</th><th>回答摘要</th></tr></thead>
            <tbody>
              ${pData.results.filter(r => !r.error).map(r => `
                <tr>
                  <td style="max-width:200px;font-size:12px">${r.query}</td>
                  <td><span class="badge badge-${r.mentioned ? 'success' : 'high'}">${r.mentioned ? '是' : '否'}</span></td>
                  <td><span class="badge badge-${r.accuracy === '高' ? 'success' : r.accuracy === '中' ? 'medium' : 'high'}">${r.accuracy}</span></td>
                  <td style="font-size:11px;color:var(--text-muted);max-width:300px">${(r.answer || '').substring(0, 120)}...</td>
                </tr>
              `).join('')}
              ${pData.results.filter(r => r.error).map(r => `
                <tr><td style="font-size:12px">${r.query}</td><td colspan="3" style="color:var(--danger);font-size:12px">${r.error}</td></tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `).join('')}
  `;
}

async function runActionPlan() {
  const resultEl = document.getElementById('report-result');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div>AI生成30/60/90天行动计划中，预计60秒...</div>';

  const result = await apiPost('/api/action-plan', {
    company: companyData ? companyData.name : '四川木子杨科技有限公司',
    company_id: companyData ? companyData.id : null,
  });

  if (!result.success) {
    resultEl.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const plan = result.data.action_plan;
  if (!plan || !plan.phase_plan) {
    resultEl.innerHTML = `<div class="card"><div class="code-block">${escapeHtml(result.data.raw_content || '生成失败')}</div></div>`;
    return;
  }

  const summary = plan.summary || {};
  const phases = plan.phase_plan || [];
  const phaseColors = { P0: 'var(--danger)', P1: 'var(--warning)', P2: 'var(--accent)' };

  resultEl.innerHTML = `
    <div class="card" style="margin-bottom:16px;background:rgba(16,185,129,0.05);border-color:var(--accent-dim)">
      <div style="font-size:15px;font-weight:700;margin-bottom:8px">${summary.headline || '行动计划'}</div>
      <p style="font-size:13px;color:var(--text-muted)">${summary.overview || ''}</p>
      <p style="font-size:13px;color:var(--accent);margin-top:8px"><strong>最优先行动：</strong>${summary.priority_action || ''}</p>
    </div>

    ${plan.strengths ? `
    <div class="grid-2" style="margin-bottom:16px">
      <div class="card">
        <div class="card-title" style="color:var(--accent);margin-bottom:8px">优势</div>
        ${(plan.strengths || []).map(s => `<div style="font-size:13px;padding:4px 0">+ ${s}</div>`).join('')}
      </div>
      <div class="card">
        <div class="card-title" style="color:var(--danger);margin-bottom:8px">差距</div>
        ${(plan.gaps || []).map(g => `<div style="font-size:13px;padding:4px 0">- ${g}</div>`).join('')}
      </div>
    </div>
    ` : ''}

    ${phases.map(phase => {
      const color = phaseColors[phase.phase] || 'var(--text-muted)';
      const tasks = phase.tasks || [];
      return `
        <div class="card" style="margin-bottom:12px;border-left:4px solid ${color}">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span style="color:${color};font-weight:700;font-size:16px">${phase.phase}</span>
              <span style="color:var(--text-muted);font-size:13px;margin-left:8px">${phase.period || ''}</span>
              <span style="font-weight:600;font-size:14px;margin-left:8px">${phase.title || ''}</span>
            </div>
          </div>
          <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">${phase.goal || ''}</p>
          <div class="table-wrap">
            <table>
              <thead><tr><th>任务</th><th>负责人</th><th>交付物</th><th>验收指标</th></tr></thead>
              <tbody>
                ${tasks.map(t => `
                  <tr>
                    <td style="font-weight:600;font-size:13px">${t.task || ''}</td>
                    <td style="font-size:12px">${t.owner || '-'}</td>
                    <td style="font-size:12px">${t.deliverable || '-'}</td>
                    <td style="font-size:12px;color:var(--text-muted)">${t.metric || '-'}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
          <div style="margin-top:8px;font-size:12px;color:${color};font-weight:600">验收指标：${phase.success_metric || ''}</div>
        </div>
      `;
    }).join('')}
  `;
}

async function runFullReport() {
  const resultEl = document.getElementById('report-result');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div>生成完整报告中（探针+合成+行动计划），预计2分钟...</div>';

  const result = await apiPost('/api/full-report', {
    company: companyData ? companyData.name : '四川木子杨科技有限公司',
    company_id: companyData ? companyData.id : null,
  });

  if (!result.success) {
    resultEl.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const probe = d.probe || {};
  const synth = d.synthesis || {};
  const plan = d.action_plan || {};

  let probeHtml = '<div class="card"><p style="color:var(--text-muted)">探针数据不可用</p></div>';
  if (probe.probe_results) {
    const probeResults = probe.probe_results;
    let totalMentions = 0, totalQueries = 0;
    Object.values(probeResults).forEach(p => { totalMentions += p.mention_count || 0; totalQueries += p.total_queries || 0; });
    const avgRate = totalQueries > 0 ? (totalMentions / totalQueries * 100).toFixed(1) : 0;

    probeHtml = `
      <div class="card">
        <div class="card-header"><span class="card-title">多模型探针结果</span><span style="color:${avgRate > 30 ? 'var(--accent)' : 'var(--danger)'}">平均展示率 ${avgRate}%</span></div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>AI引擎</th><th>展示率</th><th>提及/查询</th></tr></thead>
            <tbody>
              ${Object.entries(probeResults).map(([id, p]) => `
                <tr><td style="font-weight:600">${p.label}</td><td style="color:${p.display_rate > 30 ? 'var(--accent)' : 'var(--danger)'}">${p.display_rate}%</td><td>${p.mention_count}/${p.total_queries}</td></tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>`;
  }

  let synthHtml = '';
  if (synth.report_content) {
    synthHtml = `
      <div class="card" style="margin-top:16px">
        <div class="card-header"><span class="card-title">AI深度合成诊断</span></div>
        <div style="font-size:13px;line-height:1.8;color:var(--text)">${synth.report_content.replace(/\n/g, '<br>')}</div>
      </div>`;
  }

  let planHtml = '';
  if (plan.action_plan && plan.action_plan.phase_plan) {
    const ap = plan.action_plan;
    const phases = ap.phase_plan || [];
    const phaseColors = { P0: 'var(--danger)', P1: 'var(--warning)', P2: 'var(--accent)' };
    planHtml = `
      <div style="margin-top:16px">
        <div class="card" style="background:rgba(16,185,129,0.05);border-color:var(--accent-dim);margin-bottom:12px">
          <div style="font-weight:700;font-size:15px">${(ap.summary || {}).headline || ''}</div>
          <p style="font-size:13px;color:var(--accent);margin-top:4px">最优先行动：${(ap.summary || {}).priority_action || ''}</p>
        </div>
        ${phases.map(phase => {
          const color = phaseColors[phase.phase] || 'var(--text-muted)';
          return `
            <div class="card" style="margin-bottom:12px;border-left:4px solid ${color}">
              <div style="font-weight:700;color:${color}">${phase.phase} ${phase.period || ''} — ${phase.title || ''}</div>
              <p style="font-size:12px;color:var(--text-muted);margin:4px 0">${phase.goal || ''}</p>
              ${(phase.tasks || []).map(t => `<div style="font-size:12px;padding:2px 0">• ${t.task} | ${t.deliverable || '-'} | ${t.metric || '-'}</div>`).join('')}
              <div style="font-size:12px;color:${color};margin-top:4px">验收：${phase.success_metric || ''}</div>
            </div>`;
        }).join('')}
      </div>`;
  }

  resultEl.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <div style="font-size:14px;color:var(--text-muted)">生成时间：${d.generated_at}</div>
      <a class="btn" href="/api/report-pdf/${companyData ? companyData.id : 1}" target="_blank">PDF导出</a>
    </div>
    ${probeHtml}
    ${synthHtml}
    ${planHtml}
  `;
}

// ========== Helpers ==========

function getMetric(metrics, name) {
  const m = metrics.find(m => m.metric_name === name);
  return m ? m.metric_value : 0;
}

function severityColor(sev) {
  const map = { fatal: 'var(--danger)', high: '#f87171', medium: 'var(--warning)', low: 'var(--info)' };
  return map[sev] || 'var(--text-muted)';
}

function checkLabel(key) {
  const map = {
    https: 'HTTPS安全', meta_tags: 'Meta标签', structured_data: '结构化数据',
    llms_txt: 'llms.txt', headings: '标题层级', links: '链接结构', ai_readability: 'AI可读性',
    trust_signals: '备案/信任信号',
  };
  return map[key] || key;
}

function typeLabel(type) {
  const map = { faq: 'FAQ', about: '公司介绍', comparison: '竞品对比', guide: '教程',
    content: '内容', fix: '修复', tech: '技术', product: '产品' };
  return map[type] || type;
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function copyCode(btn) {
  const block = btn.parentElement;
  const text = block.textContent.replace('复制', '').trim();
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '已复制';
    setTimeout(() => btn.textContent = '复制', 1500);
  });
}

// ========== Keywords ==========

function renderKeywords(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>8维拓词扩展</h1><p>自动推断业务画像，从8个维度扩展关键词，AI失败时模板回退</p></div>
    </div>
    <div class="input-group">
      <input type="text" id="kw-seed" placeholder="输入种子关键词，如：AI网关" style="flex:1" value="AI网关">
      <button class="btn btn-primary" onclick="runExpand()">扩展关键词</button>
    </div>
    <div id="kw-result"></div>
  `;
  loadExistingKeywords();
}

async function loadExistingKeywords() {
  if (!companyData) return;
  try {
    const resp = await fetch(`${API}/api/keywords/list/${companyData.id}`);
    const result = await resp.json();
    if (result.success && result.data.length > 0) {
      renderKeywordTable(result.data);
    }
  } catch(e) { console.warn('loadExistingKeywords:', e); }
}

async function runExpand() {
  const seed = document.getElementById('kw-seed').value.trim();
  if (!seed) return;
  const resultEl = document.getElementById('kw-result');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div>AI 8维拓词中...</div>';

  const result = await apiPost('/api/keywords/expand', {
    company_id: companyData ? companyData.id : 1,
    seed_keyword: seed,
  });

  if (!result.success) {
    resultEl.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const profile = d.profile || {};
  const dimensions = d.dimensions || [];
  const summary = d.summary || {};
  const dimColors = ['var(--accent)', 'var(--info)', 'var(--warning)', '#a78bfa', '#f472b6', '#fb923c', '#34d399', '#60a5fa'];

  resultEl.innerHTML = `
    <div class="card" style="margin-bottom:12px;background:rgba(16,185,129,0.05);border-color:var(--accent-dim)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-size:14px;font-weight:700;color:var(--accent)">${profile.name || '企业服务'}</div>
          <div style="font-size:12px;color:var(--text-muted)">${profile.business_model || ''}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:2px">${profile.keyword_strategy || ''}</div>
        </div>
        <div style="text-align:right">
          <span class="badge badge-${d.ai_sourced ? 'success' : 'medium'}">${d.ai_sourced ? 'AI生成' : '模板回退'}</span>
        </div>
      </div>
    </div>

    <div class="grid-4" style="margin-bottom:12px">
      <div class="metric"><div class="metric-value" style="color:var(--accent)">${summary.total_keywords || 0}</div><div class="metric-label">总词数</div></div>
      <div class="metric"><div class="metric-value">${summary.average_recommendation_score || 0}</div><div class="metric-label">平均推荐分</div></div>
      <div class="metric"><div class="metric-value">${summary.average_business_score || 0}</div><div class="metric-label">平均商业分</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--accent)">${summary.high_recommendation_ratio || 0}%</div><div class="metric-label">高推荐占比</div></div>
    </div>

    <div class="grid-2">
      ${dimensions.map((dim, i) => {
        const color = dimColors[i % dimColors.length];
        const items = dim.items || [];
        return `
          <div class="card" style="margin-bottom:12px">
            <div class="card-header">
              <span class="card-title" style="color:${color}">${dim.name}</span>
              <span style="font-size:12px;color:var(--text-muted)">${dim.count}词</span>
            </div>
            ${items.map(item => `
              <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid var(--border)">
                <div style="flex:1">
                  <span style="font-size:13px;font-weight:500">${item.keyword}</span>
                  ${item.reason ? `<div style="font-size:10px;color:var(--text-muted)">${item.reason}</div>` : ''}
                </div>
                <div style="display:flex;gap:6px;align-items:center">
                  <div style="font-size:11px;color:var(--accent)">推${item.recommendation_score}</div>
                  <div style="font-size:11px;color:var(--warning)">商${item.business_score}</div>
                </div>
              </div>
            `).join('')}
          </div>
        `;
      }).join('')}
    </div>
  `;

  loadExistingKeywords();
}

function renderKeywordTable(rows) {
  const grouped = {};
  rows.forEach(r => {
    if (!grouped[r.seed_keyword]) grouped[r.seed_keyword] = [];
    grouped[r.seed_keyword].push(r);
  });

  const dimLabels = { semantic: '语义', scenario: '场景', commercial: '商业', ranking: '榜单', review: '评测', brand: '品牌', question: '问答', technical: '技术' };

  let html = '<div class="card" style="margin-top:16px"><div class="card-header"><span class="card-title">历史扩展记录</span></div>';
  Object.entries(grouped).forEach(([seed, items]) => {
    html += `<div style="margin-bottom:12px"><div style="font-size:13px;font-weight:600;margin-bottom:6px">种子词：${seed} (${items.length}个扩展)</div>`;
    html += '<div style="display:flex;flex-wrap:wrap;gap:6px">';
    items.forEach(item => {
      const dim = dimLabels[item.dimension] || item.dimension || item.category;
      html += `<span style="font-size:12px;padding:3px 8px;border-radius:4px;background:rgba(255,255,255,0.05);border:1px solid var(--border)">${item.expanded_keyword} <span style="color:var(--text-muted)">${dim} ${item.recommendation_score || 0}</span></span>`;
    });
    html += '</div></div>';
  });
  html += '</div>';

  const existing = document.getElementById('kw-result');
  if (existing) {
    const oldTable = existing.querySelector('.card:last-child');
    if (oldTable) oldTable.remove();
    existing.insertAdjacentHTML('beforeend', html);
  }
}

// ========== Scheduler ==========

function renderScheduler(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>定时监控</h1><p>设置APScheduler定时任务，自动追踪AI引用率变化趋势</p></div>
      <button class="btn btn-primary" onclick="runManualSnapshot()">立即执行一次快照</button>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">新建定时任务</span></div>
      <div class="input-group" style="margin-bottom:0">
        <select id="sched-type" style="width:120px">
          <option value="monitor">AI引用率监控</option>
          <option value="keyword">关键词拓词</option>
        </select>
        <input type="text" id="sched-cron" placeholder="Cron表达式，如 0 9 * * *" style="flex:1" value="0 9 * * *">
        <button class="btn" onclick="createJob()">创建任务</button>
      </div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:6px">Cron格式：分 时 日 月 周（如 0 9 * * * = 每天9:00，0 9 * * 1 = 每周一9:00）</div>
    </div>
    <div id="sched-jobs"></div>
    <div id="sched-trend"></div>
  `;
  loadSchedulerJobs();
  loadTrendData();
}

async function loadSchedulerJobs() {
  try {
    const resp = await fetch(`${API}/api/scheduler/jobs${companyData ? '?company_id=' + companyData.id : ''}`);
    const result = await resp.json();
    if (!result.success) return;

  const jobs = result.data || [];
  const el = document.getElementById('sched-jobs');
  if (!el) return;

  if (jobs.length === 0) {
    el.innerHTML = '<div class="card"><p style="color:var(--text-muted);font-size:13px">暂无定时任务</p></div>';
    return;
  }

  const typeLabels = { monitor: 'AI引用率监控', keyword: '关键词拓词' };
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">定时任务列表</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>类型</th><th>Cron</th><th>状态</th><th>运行次数</th><th>上次运行</th><th>操作</th></tr></thead>
          <tbody>
            ${jobs.map(j => `
              <tr>
                <td style="font-weight:600">${typeLabels[j.job_type] || j.job_type}</td>
                <td style="font-family:JetBrains Mono,monospace;font-size:12px">${j.cron_expr}</td>
                <td><span class="badge badge-${j.enabled ? 'success' : 'pending'}">${j.enabled ? '启用' : '停用'}</span></td>
                <td>${j.run_count || 0}</td>
                <td style="font-size:12px;color:var(--text-muted)">${j.last_run_at || '-'}</td>
                <td>
                  <button class="btn" style="padding:2px 8px;font-size:11px" onclick="toggleJob(${j.id}, ${!j.enabled})">${j.enabled ? '停用' : '启用'}</button>
                  <button class="btn" style="padding:2px 8px;font-size:11px;color:var(--danger)" onclick="deleteJob(${j.id})">删除</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
  } catch(e) { console.warn('loadSchedulerJobs:', e); }
}

async function createJob() {
  const jobType = document.getElementById('sched-type').value;
  const cronExpr = document.getElementById('sched-cron').value.trim();
  if (!cronExpr) return;

  const result = await apiPost('/api/scheduler/jobs', {
    company_id: companyData ? companyData.id : 1,
    job_type: jobType,
    cron_expr: cronExpr,
  });

  if (result.success) {
    loadSchedulerJobs();
  } else {
    alert('创建失败: ' + (result.error || '未知错误'));
  }
}

async function toggleJob(jobId, enabled) {
  try {
    await fetch(`${API}/api/scheduler/jobs/${jobId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
    loadSchedulerJobs();
  } catch(e) { console.warn('toggleJob:', e); }
}

async function deleteJob(jobId) {
  try {
    await fetch(`${API}/api/scheduler/jobs/${jobId}`, { method: 'DELETE' });
    loadSchedulerJobs();
  } catch(e) { console.warn('deleteJob:', e); }
}

async function runManualSnapshot() {
  const el = document.getElementById('sched-trend');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>启动快照任务...</div>';

  const startResp = await apiPost('/api/monitor/snapshot/start', {
    company_id: companyData ? companyData.id : 1,
  });
  if (!startResp.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${startResp.error || '快照启动失败'}</p></div>`;
    return;
  }

  const taskId = startResp.task_id;
  const poll = async () => {
    try {
      const resp = await fetch(`${API}/api/monitor/snapshot/status/${taskId}`);
      const result = await resp.json();
      if (!result.success) {
        el.innerHTML = `<div class="card"><p style="color:var(--danger)">快照任务查询失败</p></div>`;
        return;
      }
      const d = result.data;
      if (d.status === 'running') {
        el.innerHTML = `<div class="loading"><div class="spinner"></div>AI引用率快照执行中（5模型并行）... ${d.current_desc || ''}</div>`;
        setTimeout(poll, 3000);
      } else if (d.status === 'done') {
        loadTrendData();
      } else if (d.status === 'failed') {
        el.innerHTML = `<div class="card"><p style="color:var(--danger)">快照失败: ${d.error || '未知错误'}</p></div>`;
      }
    } catch(e) { console.warn('snapshot poll:', e); }
  };
  setTimeout(poll, 2000);
}

async function loadTrendData() {
  if (!companyData) return;
  try {
    const resp = await fetch(`${API}/api/monitor/trend/${companyData.id}?limit=30`);
    const result = await resp.json();
    if (!result.success || !result.data.length) return;

  const el = document.getElementById('sched-trend');
  if (!el) return;

  const snapshots = result.data;
  const maxRate = Math.max(...snapshots.map(s => s.display_rate * 100), 1);

  // 简易SVG趋势图
  const chartW = 700, chartH = 200, padL = 50, padR = 20, padT = 20, padB = 30;
  const plotW = chartW - padL - padR, plotH = chartH - padT - padB;

  const points = snapshots.map((s, i) => {
    const x = padL + (i / Math.max(snapshots.length - 1, 1)) * plotW;
    const y = padT + plotH - (s.display_rate * 100 / maxRate) * plotH;
    return { x, y, s };
  });

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const areaD = pathD + ` L${points[points.length - 1].x.toFixed(1)},${(padT + plotH).toFixed(1)} L${points[0].x.toFixed(1)},${(padT + plotH).toFixed(1)} Z`;

  el.innerHTML = `
    <div class="card" style="margin-top:16px">
      <div class="card-header"><span class="card-title">AI引用率变化趋势</span><span style="font-size:12px;color:var(--text-muted)">${snapshots.length}个数据点</span></div>
      <svg viewBox="0 0 ${chartW} ${chartH}" style="width:100%;height:auto">
        <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + plotH}" stroke="var(--border)" stroke-width="1"/>
        <line x1="${padL}" y1="${padT + plotH}" x2="${padL + plotW}" y2="${padT + plotH}" stroke="var(--border)" stroke-width="1"/>
        <text x="${padL - 8}" y="${padT + 4}" text-anchor="end" fill="var(--text-muted)" font-size="10">${maxRate.toFixed(0)}%</text>
        <text x="${padL - 8}" y="${padT + plotH + 4}" text-anchor="end" fill="var(--text-muted)" font-size="10">0%</text>
        <path d="${areaD}" fill="rgba(16,185,129,0.1)" stroke="none"/>
        <path d="${pathD}" fill="none" stroke="var(--accent)" stroke-width="2"/>
        ${points.map(p => `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3" fill="var(--accent)"/>`).join('')}
        ${points.filter((_, i) => i % Math.max(1, Math.floor(snapshots.length / 8)) === 0).map(p =>
          `<text x="${p.x.toFixed(1)}" y="${padT + plotH + 16}" text-anchor="middle" fill="var(--text-muted)" font-size="9">${(p.s.created_at || '').substring(5, 10)}</text>`
        ).join('')}
      </svg>
    </div>

    <div class="card" style="margin-top:12px">
      <div class="card-header"><span class="card-title">快照记录</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>时间</th><th>类型</th><th>查询数</th><th>提及数</th><th>展示率</th><th>准确率</th></tr></thead>
          <tbody>
            ${snapshots.slice().reverse().map(s => `
              <tr>
                <td style="font-size:12px">${s.created_at || '-'}</td>
                <td><span class="badge badge-${s.snapshot_type === 'scheduled' ? 'success' : 'medium'}">${s.snapshot_type === 'scheduled' ? '定时' : '手动'}</span></td>
                <td>${s.total_queries}</td>
                <td>${s.mention_count}</td>
                <td style="color:${s.display_rate > 0.3 ? 'var(--accent)' : 'var(--danger)'}">${(s.display_rate * 100).toFixed(1)}%</td>
                <td>${(s.accuracy_score * 100).toFixed(1)}%</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
  } catch(e) { console.warn('loadTrendData:', e); }
}

// ========== 竞品追踪 ==========

function renderCompetitors(el) {
  const cid = companyData ? companyData.id : '';
  el.innerHTML = `
    <div class="page-header">
      <div><h1>竞品追踪</h1><p>声音份额分析、引用差距对比、竞品GEO评分追踪</p></div>
      <button class="btn btn-primary" onclick="showAddCompetitorModal()">添加竞品</button>
    </div>
    <div id="competitor-compare"></div>
    <div id="competitor-list"></div>
    <div id="competitor-modal"></div>
  `;
  if (cid) {
    loadCompetitorCompare(cid);
    loadCompetitorList(cid);
  }
}

async function loadCompetitorCompare(cid) {
  const el = document.getElementById('competitor-compare');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>加载对比数据...</div>';
  const data = await apiGet(`/api/competitors/compare/${cid}`);
  if (!data.success) {
    el.innerHTML = '<div class="card"><p style="color:var(--danger)">加载失败</p></div>';
    return;
  }
  const entities = data.entities || [];
  const maxScore = Math.max(...entities.map(e => e.geo_score), 1);
  el.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">声音份额</span></div>
      <div style="padding:16px">
        ${entities.map(e => `
          <div style="margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
              <span style="font-size:13px;font-weight:${e.is_self ? '700' : '400'};color:${e.is_self ? 'var(--accent)' : 'var(--text)'}">${e.name}${e.is_self ? ' (本企业)' : ''}</span>
              <span style="font-size:12px;color:var(--text-muted)">GEO ${e.geo_score} · SOV ${e.share_of_voice}%${e.is_self ? '' : ` · 差距 ${e.citation_gap > 0 ? '+' : ''}${e.citation_gap}`}</span>
            </div>
            <div class="progress-bar" style="width:100%">
              <div class="progress-fill" style="width:${e.geo_score / maxScore * 100}%;background:${e.is_self ? 'var(--accent)' : 'var(--text-muted)'}"></div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
    <div class="grid-3" style="margin-bottom:16px">
      <div class="metric">
        <div class="metric-value">${data.my_score}</div>
        <div class="metric-label">本企业GEO分</div>
      </div>
      <div class="metric">
        <div class="metric-value">${data.avg_competitor_score}</div>
        <div class="metric-label">竞品平均分</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="color:${data.my_rank <= 2 ? 'var(--accent)' : 'var(--warning)'}">第${data.my_rank}</div>
        <div class="metric-label">排名 / 共${data.total_entities}家</div>
      </div>
    </div>
  `;
}

async function loadCompetitorList(cid) {
  const el = document.getElementById('competitor-list');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>加载竞品列表...</div>';
  const data = await apiGet(`/api/competitors/${cid}`);
  if (!data.success || !data.data || data.data.length === 0) {
    el.innerHTML = '<div class="card"><p style="color:var(--text-muted);padding:12px">暂无竞品数据，点击右上角添加</p></div>';
    return;
  }
  const rows = data.data.map(c => `
    <tr>
      <td style="font-weight:600">${c.competitor_name}</td>
      <td style="font-size:12px;color:var(--text-muted)">${c.competitor_domain || '-'}</td>
      <td>${c.geo_score || 0}</td>
      <td>${c.source_count || 0}</td>
      <td>${(c.ai_accuracy || 0).toFixed(1)}%</td>
      <td style="font-size:12px;color:var(--text-muted)">${c.notes || '-'}</td>
      <td>
        <button class="btn btn-sm" onclick="deleteCompetitor(${c.id})" style="padding:2px 8px;font-size:11px">删除</button>
      </td>
    </tr>
  `).join('');
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">竞品列表</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>名称</th><th>域名</th><th>GEO分</th><th>引用源</th><th>AI准确率</th><th>备注</th><th>操作</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}

function showAddCompetitorModal() {
  const el = document.getElementById('competitor-modal');
  el.innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)document.getElementById('competitor-modal').innerHTML=''">
      <div class="modal-content">
        <h3 style="margin-bottom:16px">添加竞品</h3>
        <div style="display:flex;flex-direction:column;gap:10px">
          <input type="text" id="comp-name" placeholder="竞品名称" style="padding:8px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px">
          <input type="text" id="comp-domain" placeholder="竞品域名（选填）" style="padding:8px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px">
          <input type="number" id="comp-score" placeholder="GEO评分" value="0" style="padding:8px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px">
          <input type="number" id="comp-sources" placeholder="引用源数" value="0" style="padding:8px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px">
          <input type="number" id="comp-accuracy" placeholder="AI准确率%" value="0" style="padding:8px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px">
          <textarea id="comp-notes" placeholder="备注（选填）" style="padding:8px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;height:50px"></textarea>
        </div>
        <div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end">
          <button class="btn" onclick="document.getElementById('competitor-modal').innerHTML=''">取消</button>
          <button class="btn btn-primary" onclick="addCompetitor()">添加</button>
        </div>
      </div>
    </div>
  `;
}

async function addCompetitor() {
  const cid = companyData ? companyData.id : '';
  if (!cid) return;
  const data = await apiPost(`/api/competitors/${cid}`, {
    name: document.getElementById('comp-name').value.trim(),
    domain: document.getElementById('comp-domain').value.trim(),
    geo_score: parseInt(document.getElementById('comp-score').value) || 0,
    source_count: parseInt(document.getElementById('comp-sources').value) || 0,
    ai_accuracy: parseFloat(document.getElementById('comp-accuracy').value) || 0,
    notes: document.getElementById('comp-notes').value.trim(),
  });
  if (data.error) { alert(data.error); return; }
  document.getElementById('competitor-modal').innerHTML = '';
  loadCompetitorCompare(cid);
  loadCompetitorList(cid);
}

async function deleteCompetitor(compId) {
  if (!confirm('确认删除？')) return;
  const cid = companyData ? companyData.id : '';
  try {
    const resp = await fetch(`${API}/api/competitors/${compId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    const data = await resp.json();
    if (data.error) { alert(data.error); return; }
  } catch(e) { alert('删除失败'); return; }
  loadCompetitorCompare(cid);
  loadCompetitorList(cid);
}

// ========== GEO基准测试 ==========

function renderBenchmark(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>GEO基准测试</h1><p>7维引用质量评估 + 3种印象评分算法，量化品牌在AI回答中的可见度</p></div>
      <button class="btn btn-primary" onclick="runBenchmark()">执行基准测试</button>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><span class="card-title">测试参数</span></div>
        <div style="display:flex;flex-direction:column;gap:10px">
          <div><label style="font-size:12px;color:var(--text-muted)">公司名称</label><input type="text" id="bm-company" style="width:100%" value="${companyData ? companyData.name : '四川木子杨科技有限公司'}"></div>
          <div><label style="font-size:12px;color:var(--text-muted)">行业</label><input type="text" id="bm-industry" style="width:100%" value="${companyData ? (companyData.industry || '科技') : '科技'}"></div>
          <div><label style="font-size:12px;color:var(--text-muted)">自定义查询（每行一个，空=使用默认）</label><textarea id="bm-queries" style="width:100%;height:80px" placeholder="请推荐一家科技公司\\n木子杨怎么样"></textarea></div>
          <div><label style="font-size:12px;color:var(--text-muted)">测试模型</label><input type="text" id="bm-models" style="width:100%" value="deepseek-v4-pro,kimi-k3,glm-5.2" placeholder="逗号分隔"></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">7维评估体系</span></div>
        <div style="font-size:13px;line-height:1.8">
          <div><strong style="color:var(--accent)">Relevance</strong> — 引用与查询的相关性</div>
          <div><strong style="color:var(--accent)">Influence</strong> — 对答案完整性的贡献</div>
          <div><strong style="color:var(--accent)">Diversity</strong> — 观点多样性</div>
          <div><strong style="color:var(--accent)">Uniqueness</strong> — 信息独特性</div>
          <div><strong style="color:var(--accent)">Follow</strong> — 引导后续行动能力</div>
          <div><strong style="color:var(--warning)">SubjPos</strong> — 引用位置(first/middle/last)</div>
          <div><strong style="color:var(--warning)">SubjCount</strong> — 被提及次数</div>
        </div>
        <div style="margin-top:12px;font-size:12px;color:var(--text-muted)">印象评分算法：wordpos(词数×位置衰减) / word(纯词数) / pos(位置加权)</div>
      </div>
    </div>
    <div id="bm-result"></div>
  `;
}

async function runBenchmark() {
  const company = document.getElementById('bm-company').value.trim();
  const industry = document.getElementById('bm-industry').value.trim();
  const queriesText = document.getElementById('bm-queries').value.trim();
  const modelsText = document.getElementById('bm-models').value.trim();
  if (!company) return;

  const queries = queriesText ? queriesText.split('\n').map(s => s.trim()).filter(Boolean) : null;
  const models = modelsText ? modelsText.split(',').map(s => s.trim()).filter(Boolean) : null;

  const el = document.getElementById('bm-result');
  el.innerHTML = '<div class="loading"><div class="spinner"></div>正在启动异步基准测试...</div>';

  // 启动异步任务
  const startResp = await apiPost('/api/benchmark/start', { company_name: company, industry, queries, models });
  if (!startResp.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${startResp.error}</p></div>`;
    return;
  }

  const taskId = startResp.task_id;
  // 轮询状态
  await _pollBenchmark(taskId, el);
}

async function _pollBenchmark(taskId, el) {
  const poll = async () => {
    try {
      const resp = await fetch(`${API}/api/benchmark/status/${taskId}`);
      const result = await resp.json();
      if (!result.success) {
        el.innerHTML = `<div class="card"><p style="color:var(--danger)">查询失败</p></div>`;
        return;
      }

    const d = result.data;
    if (d.status === 'running') {
      const pct = d.progress || 0;
      el.innerHTML = `
        <div class="card" style="margin-top:16px">
          <div style="text-align:center;padding:20px">
            <div class="spinner" style="margin:0 auto 12px"></div>
            <div style="font-size:14px;font-weight:600;margin-bottom:8px">GEO基准测试执行中... ${pct}%</div>
            <div class="progress-bar" style="width:300px;margin:0 auto"><div class="progress-fill" style="width:${pct}%"></div></div>
            <div style="font-size:12px;color:var(--text-muted);margin-top:8px">步骤 ${d.current_step}/${d.total_steps}: ${d.current_desc}</div>
          </div>
        </div>
      `;
      setTimeout(poll, 2000);
    } else if (d.status === 'done') {
      _renderBenchmarkResult(el, d.result);
    } else if (d.status === 'failed') {
      el.innerHTML = `<div class="card"><p style="color:var(--danger)">测试失败: ${d.error || '未知错误'}</p></div>`;
    }
    } catch(e) { console.warn('_pollBenchmark:', e); }
  };
  setTimeout(poll, 1000);
}

function _renderBenchmarkResult(el, d) {
  const evalScores = d.avg_eval_scores || {};
  const geoScore = d.geo_benchmark_score || 0;
  const scoreColor = geoScore >= 60 ? 'var(--accent)' : geoScore >= 30 ? 'var(--warning)' : 'var(--danger)';

  el.innerHTML = `
    <div class="grid-2" style="margin-top:16px">
      <div class="card">
        <div style="text-align:center;padding:12px">
          <div class="metric-value" style="font-size:48px;color:${scoreColor}">${geoScore}</div>
          <div class="metric-label">GEO基准分</div>
        </div>
        <div style="display:flex;justify-content:space-around;padding:8px 0;border-top:1px solid var(--border)">
          <div style="text-align:center"><div style="font-size:20px;font-weight:700;color:var(--accent)">${d.total_mentions}</div><div style="font-size:11px;color:var(--text-muted)">被提及</div></div>
          <div style="text-align:center"><div style="font-size:20px;font-weight:700">${d.total_queries}</div><div style="font-size:11px;color:var(--text-muted)">总查询</div></div>
          <div style="text-align:center"><div style="font-size:20px;font-weight:700;color:${d.display_rate > 0.3 ? 'var(--accent)' : 'var(--danger)'}">${(d.display_rate * 100).toFixed(1)}%</div><div style="font-size:11px;color:var(--text-muted)">展示率</div></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">5维评估均分</span></div>
        ${Object.entries(evalScores).map(([k, v]) => {
          const pct = (v / 5 * 100).toFixed(0);
          return `<div style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;font-size:12px"><span>${k}</span><span style="color:${v >= 3.5 ? 'var(--accent)' : 'var(--warning)'}">${v}/5 (${pct}%)</span></div>
            <div class="progress-bar"><div class="progress-fill" style="width:${pct}%;background:${v >= 3.5 ? 'var(--accent)' : 'var(--warning)'}"></div></div>
          </div>`;
        }).join('')}
      </div>
    </div>
    <div class="card" style="margin-top:12px">
      <div class="card-header"><span class="card-title">详细结果</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>模型</th><th>查询</th><th>提及</th><th>位置</th><th>次数</th><th>相关性</th><th>影响力</th><th>多样性</th><th>独特性</th><th>引导力</th></tr></thead>
          <tbody>
            ${(d.results || []).map(r => {
              if (r.error) return `<tr><td colspan="10" style="color:var(--danger)">${r.model}: ${r.error}</td></tr>`;
              const e = r.eval_scores || {};
              const pos = r.mention_position || 'none';
              const posColor = pos === 'first' ? 'var(--accent)' : pos === 'middle' ? 'var(--warning)' : 'var(--danger)';
              return `<tr>
                <td style="font-size:12px">${r.model}</td>
                <td style="font-size:11px;max-width:150px;overflow:hidden;text-overflow:ellipsis">${r.query}</td>
                <td>${r.mention_count > 0 ? '<span style="color:var(--accent)">YES</span>' : '<span style="color:var(--text-muted)">NO</span>'}</td>
                <td style="color:${posColor}">${pos}</td>
                <td>${r.mention_count || 0}</td>
                <td>${e.relevance || '-'}</td>
                <td>${e.influence || '-'}</td>
                <td>${e.diversity || '-'}</td>
                <td>${e.uniqueness || '-'}</td>
                <td>${e.follow || '-'}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// ========== SHEEP GEM评分 ==========

function renderSheep(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>SHEEP GEM评分</h1><p>五维加权评分模型，覆盖9个主流中文AI模型的引用表现</p></div>
      <button class="btn btn-primary" onclick="runSheep()">计算GEM评分</button>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><span class="card-title">评分参数</span></div>
        <div style="display:flex;flex-direction:column;gap:10px">
          <div><label style="font-size:12px;color:var(--text-muted)">公司名称</label><input type="text" id="sh-company" style="width:100%" value="${companyData ? companyData.name : '四川木子杨科技有限公司'}"></div>
          <div><label style="font-size:12px;color:var(--text-muted)">行业</label><input type="text" id="sh-industry" style="width:100%" value="${companyData ? (companyData.industry || '科技') : '科技'}"></div>
          <div><label style="font-size:12px;color:var(--text-muted)">网站URL</label><input type="text" id="sh-url" style="width:100%" value="${companyData ? (companyData.website || '') : ''}" placeholder="https://example.com"></div>
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" id="sh-auto-diagnose" checked>
            <span style="font-size:13px">先诊断网站再评分（自动构建evidence）</span>
          </label>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">SHEEP五维模型</span></div>
        <div style="font-size:13px;line-height:1.8">
          <div><strong style="color:var(--accent)">S</strong> 语义覆盖度 (25%) — AI识别率+内容质量+跨模型覆盖</div>
          <div><strong style="color:var(--accent)">H</strong> 人类可信度 (25%) — 领域权威+作者专业度+来源可验证</div>
          <div><strong style="color:var(--warning)">E1</strong> 证据结构化 (20%) — Schema.org+信息架构+认知负荷</div>
          <div><strong style="color:var(--warning)">E2</strong> 生态集成度 (15%) — 多平台可见+交叉引用+API可访问</div>
          <div><strong style="color:var(--info)">P</strong> 性能监控 (15%) — AI采纳率+转化潜力+技术性能</div>
        </div>
        <div style="margin-top:8px;font-size:12px;color:var(--text-muted)">GEM = S×0.25 + H×0.25 + E1×0.20 + E2×0.15 + P×0.15</div>
        <div style="margin-top:4px;font-size:12px;color:var(--info)">勾选自动诊断后，将从网站爬取真实数据映射到5个维度作为evidence</div>
      </div>
    </div>
    <div id="sh-result"></div>
  `;
  loadModelWeights();
}

async function loadModelWeights() {
  try {
    const resp = await fetch(`${API}/api/sheep/model-weights`);
    const result = await resp.json();
    if (!result.success) return;
  const weights = result.data;
  const el = document.getElementById('sh-result');
  if (!el) return;
  const entries = Object.entries(weights).sort((a, b) => b[1] - a[1]);
  el.innerHTML = `
    <div class="card" style="margin-top:16px">
      <div class="card-header"><span class="card-title">9个中国AI模型权重</span></div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        ${entries.map(([name, w]) => `<div style="text-align:center;padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:rgba(255,255,255,0.03)">
          <div style="font-size:13px;font-weight:600">${name}</div>
          <div style="font-size:16px;font-weight:700;color:var(--accent)">${(w * 100).toFixed(0)}%</div>
        </div>`).join('')}
      </div>
    </div>
  `;
  } catch(e) { console.warn('loadModelWeights:', e); }
}

async function runSheep() {
  const company = document.getElementById('sh-company').value.trim();
  const industry = document.getElementById('sh-industry').value.trim();
  const url = document.getElementById('sh-url').value.trim();
  const autoDiagnose = document.getElementById('sh-auto-diagnose').checked;
  if (!company) return;

  const el = document.getElementById('sh-result');
  const loadingMsg = autoDiagnose && url
    ? '正在诊断网站并构建evidence，然后执行SHEEP五维评估...'
    : 'SHEEP五维评估中，AI分析5个维度并计算GEM分数...';
  el.innerHTML = `<div class="loading"><div class="spinner"></div>${loadingMsg}</div>`;

  const result = await apiPost('/api/sheep-score', { company_name: company, industry, url, auto_diagnose: autoDiagnose });
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const gem = d.gem_score;
  const grade = d.grade;
  const gradeColor = gem >= 80 ? 'var(--accent)' : gem >= 60 ? 'var(--warning)' : 'var(--danger)';
  const dims = d.dimensions || {};

  // 保留模型权重展示
  const weightsHtml = el.querySelector('.card') ? el.querySelector('.card').outerHTML : '';

  el.innerHTML = `
    <div class="grid-2" style="margin-top:16px">
      <div class="card" style="text-align:center">
        <div style="font-size:64px;font-weight:800;color:${gradeColor}">${gem}</div>
        <div style="font-size:24px;font-weight:700;color:${gradeColor}">Grade ${grade}</div>
        <div class="metric-label" style="margin-top:4px">GEM Score</div>
        ${d.evidence_source === 'auto_diagnosis' ? '<div style="font-size:11px;color:var(--info);margin-top:4px">evidence来源：网站自动诊断</div>' : '<div style="font-size:11px;color:var(--text-muted);margin-top:4px">evidence来源：AI自评</div>'}
        ${d.diagnosis ? `<div style="font-size:11px;color:var(--text-muted);margin-top:2px">网站诊断评分: ${d.diagnosis.overall_score}/100 (HTTP ${d.diagnosis.status_code})</div>` : ''}
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">五维雷达</span></div>
        ${Object.entries(dims).map(([k, v]) => {
          const pct = v.score;
          const color = pct >= 70 ? 'var(--accent)' : pct >= 50 ? 'var(--warning)' : 'var(--danger)';
          return `<div style="margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;font-size:12px">
              <span><strong>${k}</strong> ${v.name} (${v.weight})</span>
              <span style="color:${color}">${v.score} (${v.grade})</span>
            </div>
            <div class="progress-bar" style="height:8px"><div class="progress-fill" style="width:${pct}%;background:${color}"></div></div>
          </div>`;
        }).join('')}
      </div>
    </div>
    <div class="card" style="margin-top:12px">
      <div class="card-header"><span class="card-title">维度详情</span></div>
      ${Object.entries(d.details || {}).map(([k, v]) => {
        const dim = dims[k];
        return `<div style="margin-bottom:12px;padding:8px;border-left:3px solid ${dim && dim.score >= 70 ? 'var(--accent)' : 'var(--warning)'};background:rgba(255,255,255,0.02)">
          <div style="font-size:13px;font-weight:600;margin-bottom:4px">${k} — ${dim ? dim.name : ''}</div>
          <div style="font-size:12px;color:var(--text-muted);line-height:1.6">${v}</div>
        </div>`;
      }).join('')}
    </div>
    ${(d.improvement_suggestions || []).length > 0 ? `
    <div class="card" style="margin-top:12px">
      <div class="card-header"><span class="card-title">改进建议</span></div>
      <ul style="font-size:13px;line-height:1.8;padding-left:20px">
        ${d.improvement_suggestions.map(s => `<li>${s}</li>`).join('')}
      </ul>
    </div>` : ''}
    ${weightsHtml}
  `;
}

// ========== GEO内容优化策略 ==========

function renderStrategies(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>GEO内容优化策略</h1><p>9种策略提升AI引用率，覆盖结构化数据、语义密度、实体关联等维度</p></div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">输入内容</span></div>
      <textarea id="cs-content" style="width:100%;height:120px;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:10px;font-size:13px" placeholder="输入要优化的内容..."></textarea>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn btn-primary" onclick="applyAllStrategies()">应用全部9种策略</button>
        <button class="btn" onclick="applySelectedStrategies()">应用选中策略</button>
      </div>
    </div>
    <div id="cs-strategies-list"></div>
    <div id="cs-result"></div>
  `;
  loadStrategiesList();
}

async function loadStrategiesList() {
  try {
    const resp = await fetch(`${API}/api/content-strategies`);
    const result = await resp.json();
    if (!result.success) return;
  const el = document.getElementById('cs-strategies-list');
  if (!el) return;
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">9种优化策略</span></div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
        ${result.data.map(s => `
          <label style="display:flex;align-items:flex-start;gap:6px;padding:8px;border:1px solid var(--border);border-radius:6px;cursor:pointer;background:rgba(255,255,255,0.02)">
            <input type="checkbox" class="cs-check" value="${s.key}" checked style="margin-top:2px">
            <div>
              <div style="font-size:13px;font-weight:600">${s.name}</div>
              <div style="font-size:11px;color:var(--text-muted)">${s.description}</div>
            </div>
          </label>
        `).join('')}
      </div>
    </div>
  `;
  } catch(e) { console.warn('loadStrategiesList:', e); }
}

async function applyAllStrategies() {
  const content = document.getElementById('cs-content').value.trim();
  if (!content) return;
  await _applyStrategies(content, null);
}

async function applySelectedStrategies() {
  const content = document.getElementById('cs-content').value.trim();
  if (!content) return;
  const selected = Array.from(document.querySelectorAll('.cs-check:checked')).map(el => el.value);
  if (!selected.length) return;
  await _applyStrategies(content, selected);
}

async function _applyStrategies(content, selected) {
  const el = document.getElementById('cs-result');
  const count = selected ? selected.length : 9;
  el.innerHTML = `<div class="loading"><div class="spinner"></div>正在应用${count}种优化策略...</div>`;

  const result = await apiPost('/api/content-strategies/apply', { content, selected });
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const results = d.results || {};
  const strategyNames = {
    authoritative: '权威语气', citing_credible: '引用可信来源', more_quotes: '权威引语',
    stats_optimization: '统计数据', technical_terms: '专业术语', simple_language: '简化语言',
    unique_words: '独特词汇', fluent: '流畅度优化', seo_optimize: 'SEO关键词优化',
  };

  el.innerHTML = `
    <div class="card" style="margin-top:16px">
      <div class="card-header"><span class="card-title">优化结果对比</span><span style="font-size:12px;color:var(--text-muted)">原文${d.original_content.length}字</span></div>
      ${Object.entries(results).map(([key, r]) => {
        if (r.error) return `<div style="padding:8px;border-bottom:1px solid var(--border);color:var(--danger)">${strategyNames[key] || key}: ${r.error}</div>`;
        const lenDiff = r.optimized_length - r.original_length;
        return `
          <details style="border-bottom:1px solid var(--border);padding:8px 0">
            <summary style="cursor:pointer;font-size:13px;font-weight:600;display:flex;justify-content:space-between;align-items:center">
              <span>${strategyNames[key] || r.name}</span>
              <span style="font-size:11px;color:${lenDiff > 0 ? 'var(--accent)' : 'var(--warning)'}">${r.optimized_length}字 (${lenDiff > 0 ? '+' : ''}${lenDiff})</span>
            </summary>
            <div style="margin-top:8px;padding:8px;background:rgba(255,255,255,0.03);border-radius:4px;font-size:13px;line-height:1.6;white-space:pre-wrap">${r.optimized_content}</div>
          </details>
        `;
      }).join('')}
    </div>
  `;
}

// ========== 公司入库 ==========

function renderIngest(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>公司官网入库</h1><p>URL归一化 + 公网地址校验 + 候选链接提取 + 页面角色分类</p></div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">输入公司官网</span></div>
      <div class="input-group">
        <input type="text" id="ingest-url" placeholder="https://example.com" style="flex:1" value="">
        <button class="btn btn-primary" onclick="runIngest()">开始入库</button>
      </div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:6px">自动校验公网地址、提取首页候选链接、按角色分类（首页/关于/团队/产品）</div>
    </div>
    <div id="ingest-result"></div>
  `;
}

async function runIngest() {
  const url = document.getElementById('ingest-url').value.trim();
  if (!url) return;
  const el = document.getElementById('ingest-result');
  el.innerHTML = '<div class="loading"><div class="spinner"></div>正在抓取和分析网站...</div>';

  const result = await apiPost('/api/company/ingest', { url });
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const roleColors = { homepage: 'var(--accent)', about: 'var(--info)', team: '#a78bfa', product: '#fb923c', other: 'var(--text-muted)' };
  const roleLabels = { homepage: '首页', about: '关于', team: '团队', product: '产品', other: '其他' };

  el.innerHTML = `
    <div class="grid-3" style="margin-bottom:16px">
      <div class="metric"><div class="metric-value" style="color:var(--accent)">${d.page_count}</div><div class="metric-label">发现页面</div></div>
      <div class="metric"><div class="metric-value">${d.status_code}</div><div class="metric-label">HTTP状态</div></div>
      <div class="metric"><div class="metric-value" style="font-size:16px">${(d.title || '').substring(0, 20)}</div><div class="metric-label">页面标题</div></div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">候选页面列表</span><span style="font-size:12px;color:var(--text-muted)">按相关性打分排序</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>URL</th><th>标题</th><th>角色</th><th>得分</th></tr></thead>
          <tbody>
            ${(d.pages || []).map(p => `
              <tr>
                <td style="font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis">${p.url}</td>
                <td style="font-size:12px">${p.title}</td>
                <td><span class="badge" style="background:rgba(255,255,255,0.05);color:${roleColors[p.role] || 'var(--text-muted)'}">${roleLabels[p.role] || p.role}</span></td>
                <td style="font-size:12px;color:${p.score > 50 ? 'var(--accent)' : 'var(--text-muted)'}">${p.score}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
    <div class="card" style="margin-top:12px">
      <div class="card-header"><span class="card-title">入库信息</span></div>
      <div style="font-size:13px;line-height:1.8">
        <div><strong>原始URL：</strong>${url}</div>
        <div><strong>归一化URL：</strong>${d.url}</div>
        <div><strong>最终URL：</strong>${d.final_url}</div>
      </div>
    </div>
  `;
}

// ========== RAG问答 ==========

function renderChat(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>RAG问答</h1><p>对话持久化 + 诊断报告上下文注入 + SSE流式输出</p></div>
    </div>
    <div class="grid-2">
      <div class="card" style="display:flex;flex-direction:column;gap:10px">
        <div class="card-header"><span class="card-title">提问</span></div>
        <div>
          <label style="font-size:12px;color:var(--text-muted)">频道</label>
          <select id="chat-channel" style="width:100%;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px">
            <option value="geo_basic">GEO基础</option>
            <option value="diagnosis">诊断解读</option>
            <option value="optimization">优化策略</option>
            <option value="benchmark">基准测试</option>
          </select>
        </div>
        <textarea id="chat-input" style="width:100%;height:100px;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:10px;font-size:13px" placeholder="输入问题，如：如何提升AI搜索中的品牌展示率？"></textarea>
        <div style="display:flex;gap:8px">
          <button class="btn btn-primary" onclick="sendChat()">发送</button>
          <button class="btn" onclick="sendChatStream()">流式发送</button>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">上下文信息</span></div>
        <div style="font-size:12px;color:var(--text-muted);line-height:1.8">
          <div>系统自动从数据库加载以下上下文：</div>
          <div>- 公司信息（名称/域名/行业）</div>
          <div>- 最新诊断报告（评分/主要问题）</div>
          <div>- 已扩展关键词（Top10）</div>
          <div>- 最新监控快照（展示率/准确率）</div>
          <div style="margin-top:8px;color:var(--info)">上下文注入到system prompt，AI回答更精准</div>
        </div>
      </div>
    </div>
    <div id="chat-result" style="margin-top:16px"></div>
    <div id="chat-history" style="margin-top:16px"></div>
  `;
  loadChatHistory();
}

async function sendChat() {
  const question = document.getElementById('chat-input').value.trim();
  const channel = document.getElementById('chat-channel').value;
  if (!question) return;
  const el = document.getElementById('chat-result');
  el.innerHTML = '<div class="loading"><div class="spinner"></div>AI思考中...</div>';

  const result = await apiPost('/api/chat', { company_id: companyData ? companyData.id : 1, question, channel });
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  el.innerHTML = `
    <div class="card">
      <div class="card-header">
        <span class="card-title">AI回答</span>
        <span style="font-size:11px;color:var(--text-muted)">${d.model} | ${channel}</span>
      </div>
      <div style="font-size:13px;line-height:1.8;color:var(--text);white-space:pre-wrap">${escapeHtml(d.answer)}</div>
    </div>
  `;
  loadChatHistory();
}

async function sendChatStream() {
  const question = document.getElementById('chat-input').value.trim();
  const channel = document.getElementById('chat-channel').value;
  if (!question) return;
  const el = document.getElementById('chat-result');
  el.innerHTML = '<div class="card"><div class="card-header"><span class="card-title">AI流式回答</span></div><div id="chat-stream-text" style="font-size:13px;line-height:1.8;white-space:pre-wrap"></div></div>';

  const textEl = document.getElementById('chat-stream-text');
  try {
    const resp = await fetch(`${API}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company_id: companyData ? companyData.id : 1, question, channel }),
    });

    const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.content) textEl.textContent += data.content;
        if (data.done) { loadChatHistory(); }
      } catch (e) { /* skip */ }
    }
  }
  } catch(e) { console.warn('sendChatStream:', e); textEl.textContent = '流式请求失败: ' + e.message; }
}

async function loadChatHistory() {
  if (!companyData) return;
  try {
    const resp = await fetch(`${API}/api/chat/conversations/${companyData.id}?limit=10`);
    const result = await resp.json();
    if (!result.success || !result.data.length) return;

  const el = document.getElementById('chat-history');
  if (!el) return;
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">对话历史</span></div>
      ${result.data.map(c => `
        <div style="margin-bottom:12px;padding:8px;border-bottom:1px solid var(--border)">
          <div style="font-size:12px;color:var(--accent);font-weight:600">${escapeHtml(c.question)}</div>
          <div style="font-size:13px;color:var(--text);margin-top:4px;white-space:pre-wrap">${escapeHtml(c.answer.substring(0, 200))}${c.answer.length > 200 ? '...' : ''}</div>
          <div style="font-size:10px;color:var(--text-muted);margin-top:2px">${c.channel} | ${c.model} | ${c.created_at}</div>
        </div>
      `).join('')}
    </div>
  `;
  } catch(e) { console.warn('loadChatHistory:', e); }
}

// ========== GDO决策审计 ==========

function renderGDO(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>GDO决策背书审计</h1><p>生成式决策优化 — 客户找上门后，AI仍参与比较/验证/谈判。审计企业"AI可验证决策证据"完整度</p></div>
    </div>
    <div class="card" style="margin-bottom:12px">
      <div class="card-header"><span class="card-title">审计输入</span></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <input type="text" id="gdo-company" placeholder="公司名称" style="background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px" value="${companyData ? companyData.name : ''}">
        <input type="text" id="gdo-domain" placeholder="官网域名" style="background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px" value="${companyData ? companyData.domain : ''}">
        <input type="text" id="gdo-industry" placeholder="行业（可选）" style="background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px">
        <input type="text" id="gdo-competitor" placeholder="竞争对手名称（可选，用于模拟对比）" style="background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px">
      </div>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button class="btn btn-primary" onclick="runGDOAudit()">开始审计</button>
        <button class="btn" onclick="runGDOSimulate()">模拟AI决策</button>
      </div>
    </div>
    <div id="gdo-result"></div>
  `;
}

async function runGDOAudit() {
  const company = document.getElementById('gdo-company').value.trim();
  const domain = document.getElementById('gdo-domain').value.trim();
  const industry = document.getElementById('gdo-industry').value.trim();
  if (!company || !domain) return;
  const el = document.getElementById('gdo-result');
  el.innerHTML = '<div class="loading"><div class="spinner"></div>GDO审计中（5维度×6检查项）...</div>';

  const result = await apiPost('/api/gdo/audit', { company_name: company, domain, industry });
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const dims = d.dimensions || [];
  const levelColors = { S: 'var(--accent)', A: '#34d399', B: 'var(--warning)', C: '#fb923c', D: 'var(--danger)' };

  el.innerHTML = `
    <div class="grid-3" style="margin-bottom:16px">
      <div class="metric"><div class="metric-value" style="color:${levelColors[d.level] || 'var(--text)'}">${d.overall_score}</div><div class="metric-label">GDO总分 (${d.level}级)</div></div>
      <div class="metric"><div class="metric-value">${dims.length}</div><div class="metric-label">审计维度</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--danger)">${(d.critical_gaps || []).length}</div><div class="metric-label">关键缺口</div></div>
    </div>
    ${d.summary ? `<div class="card" style="margin-bottom:12px;background:rgba(16,185,129,0.05)"><div style="font-size:13px;line-height:1.8">${escapeHtml(d.summary)}</div></div>` : ''}
    <div class="grid-2">
      ${dims.map(dim => `
        <div class="card" style="margin-bottom:12px">
          <div class="card-header">
            <span class="card-title" style="color:${levelColors[dim.level || 'D']}">${dim.name}</span>
            <span style="font-size:14px;font-weight:700;color:${levelColors[dim.level || 'D']}">${dim.score}</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">${dim.description || ''}</div>
          ${dim.found_items && dim.found_items.length ? `<div style="margin-bottom:6px"><div style="font-size:11px;color:var(--accent);font-weight:600">已满足</div>${dim.found_items.map(i => `<div style="font-size:12px;color:var(--accent)">+ ${escapeHtml(i)}</div>`).join('')}</div>` : ''}
          ${dim.missing_items && dim.missing_items.length ? `<div style="margin-bottom:6px"><div style="font-size:11px;color:var(--danger);font-weight:600">缺失</div>${dim.missing_items.map(i => `<div style="font-size:12px;color:var(--danger)">- ${escapeHtml(i)}</div>`).join('')}</div>` : ''}
          ${dim.suggestions && dim.suggestions.length ? `<div><div style="font-size:11px;color:var(--warning);font-weight:600">建议</div>${dim.suggestions.map(s => `<div style="font-size:12px;color:var(--warning)">> ${escapeHtml(s)}</div>`).join('')}</div>` : ''}
        </div>
      `).join('')}
    </div>
    ${d.critical_gaps && d.critical_gaps.length ? `
      <div class="card" style="margin-top:12px;border-color:var(--danger)">
        <div class="card-header"><span class="card-title" style="color:var(--danger)">关键缺口</span></div>
        ${d.critical_gaps.map(g => `<div style="font-size:13px;color:var(--danger);padding:4px 0">! ${escapeHtml(g)}</div>`).join('')}
      </div>
    ` : ''}
    ${d.priority_actions && d.priority_actions.length ? `
      <div class="card" style="margin-top:12px">
        <div class="card-header"><span class="card-title">优先行动建议</span></div>
        ${d.priority_actions.map((a, i) => `<div style="font-size:13px;padding:4px 0"><span style="color:var(--accent);font-weight:700">${i + 1}.</span> ${escapeHtml(a)}</div>`).join('')}
      </div>
    ` : ''}
  `;
}

async function runGDOSimulate() {
  const company = document.getElementById('gdo-company').value.trim();
  const domain = document.getElementById('gdo-domain').value.trim();
  const competitor = document.getElementById('gdo-competitor').value.trim();
  if (!company || !domain) return;
  const el = document.getElementById('gdo-result');
  el.innerHTML = '<div class="loading"><div class="spinner"></div>模拟AI决策场景...</div>';

  const result = await apiPost('/api/gdo/simulate', { company_name: company, domain, competitor });
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  el.innerHTML = `
    <div class="card">
      <div class="card-header">
        <span class="card-title">${d.scenario === 'comparison' ? '竞品对比模拟' : '合作验证模拟'}</span>
        <span style="font-size:11px;color:var(--text-muted)">${d.model}</span>
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px">${escapeHtml(d.question)}</div>
      <div style="font-size:13px;line-height:1.8;color:var(--text);white-space:pre-wrap;padding:12px;background:rgba(255,255,255,0.03);border-radius:6px;border:1px solid var(--border)">${escapeHtml(d.ai_response)}</div>
    </div>
  `;
}

// ========== AI决策测试 ==========

function renderDecision(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>AI决策测试</h1><p>模拟客户签约前的5种AI决策场景，检测企业在AI验证环节的表现</p></div>
    </div>
    <div class="card" style="margin-bottom:12px">
      <div class="card-header"><span class="card-title">测试配置</span></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px">
        <input type="text" id="dt-company" placeholder="公司名称" style="background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px" value="${companyData ? companyData.name : ''}">
        <input type="text" id="dt-domain" placeholder="官网域名" style="background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px" value="${companyData ? companyData.domain : ''}">
        <input type="text" id="dt-competitor" placeholder="竞争对手（可选）" style="background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px">
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px">选择测试场景：</div>
      <div id="dt-scenarios" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px"></div>
      <button class="btn btn-primary" onclick="runDecisionTest()">开始测试</button>
    </div>
    <div id="dt-result"></div>
  `;
  loadDecisionScenarios();
}

async function loadDecisionScenarios() {
  try {
    const resp = await fetch(`${API}/api/decision-test/scenarios`);
    const result = await resp.json();
    if (!result.success) return;
  const el = document.getElementById('dt-scenarios');
  el.innerHTML = result.data.map((s, i) => `
    <label style="display:flex;align-items:center;gap:4px;font-size:12px;padding:4px 8px;border:1px solid var(--border);border-radius:4px;cursor:pointer">
      <input type="checkbox" value="${s.key}" ${i < 3 ? 'checked' : ''}>
      ${s.name}
    </label>
  `).join('');
  } catch(e) { console.warn('loadDecisionScenarios:', e); }
}

async function runDecisionTest() {
  const company = document.getElementById('dt-company').value.trim();
  const domain = document.getElementById('dt-domain').value.trim();
  const competitor = document.getElementById('dt-competitor').value.trim();
  if (!company || !domain) return;
  const scenarios = Array.from(document.querySelectorAll('#dt-scenarios input:checked')).map(cb => cb.value);
  if (!scenarios.length) return;

  const el = document.getElementById('dt-result');
  el.innerHTML = '<div class="loading"><div class="spinner"></div>AI决策测试中（每个场景约10秒）...</div>';

  const result = await apiPost('/api/decision-test', { company_name: company, domain, competitor, scenarios });
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const s = d.summary;
  const sentimentColors = { positive: 'var(--accent)', negative: 'var(--danger)', neutral: 'var(--warning)' };
  const sentimentLabels = { positive: '正面', negative: '负面', neutral: '中性' };

  el.innerHTML = `
    <div class="grid-4" style="margin-bottom:16px">
      <div class="metric"><div class="metric-value">${s.total}</div><div class="metric-label">测试场景</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--accent)">${s.positive}</div><div class="metric-label">正面</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--warning)">${s.neutral}</div><div class="metric-label">中性</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--danger)">${s.negative}</div><div class="metric-label">负面</div></div>
    </div>
    <div class="card" style="margin-bottom:12px;text-align:center">
      <div style="font-size:14px;color:${sentimentColors[s.overall_sentiment]}">总体AI决策倾向：${sentimentLabels[s.overall_sentiment]}</div>
    </div>
    ${d.scenarios.map(sc => `
      <div class="card" style="margin-bottom:12px">
        <div class="card-header">
          <span class="card-title">${sc.scenario_name}</span>
          ${sc.analysis ? `<span class="badge badge-${sc.analysis.sentiment === 'positive' ? 'success' : sc.analysis.sentiment === 'negative' ? 'danger' : 'medium'}">${sentimentLabels[sc.analysis.sentiment]}</span>` : ''}
        </div>
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">${escapeHtml(sc.question)}</div>
        ${sc.error ? `<div style="color:var(--danger)">错误：${escapeHtml(sc.error)}</div>` : `
          <div style="font-size:13px;line-height:1.8;color:var(--text);white-space:pre-wrap;padding:12px;background:rgba(255,255,255,0.03);border-radius:6px;border:1px solid var(--border);max-height:300px;overflow-y:auto">${escapeHtml(sc.ai_response)}</div>
          ${sc.analysis ? `
            <div style="display:flex;gap:12px;margin-top:8px;font-size:11px">
              ${sc.analysis.positive_signals.length ? `<span style="color:var(--accent)">正面信号：${sc.analysis.positive_signals.join(', ')}</span>` : ''}
              ${sc.analysis.negative_signals.length ? `<span style="color:var(--danger)">负面信号：${sc.analysis.negative_signals.join(', ')}</span>` : ''}
            </div>
          ` : ''}
        `}
      </div>
    `).join('')}
  `;
}

// ========== 六层成熟度 ==========

function renderMaturity(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>六层全域AI营销成熟度</h1><p>SEO→AEO→GEO→GAO→GMO→GDO 六层评分模型</p></div>
    </div>
    <div class="card" style="margin-bottom:12px">
      <div class="card-header"><span class="card-title">评分输入</span></div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px">系统自动从诊断报告、基准测试、SHEEP评分、GDO审计、关键词数据中提取各层得分</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
        <label style="font-size:12px;display:flex;align-items:center;gap:4px"><input type="checkbox" id="mt-diag" checked> 网站诊断</label>
        <label style="font-size:12px;display:flex;align-items:center;gap:4px"><input type="checkbox" id="mt-bench" checked> 基准测试</label>
        <label style="font-size:12px;display:flex;align-items:center;gap:4px"><input type="checkbox" id="mt-sheep" checked> SHEEP评分</label>
        <label style="font-size:12px;display:flex;align-items:center;gap:4px"><input type="checkbox" id="mt-gdo" checked> GDO审计</label>
      </div>
      <div style="display:flex;gap:8px">
        <input type="number" id="mt-kw" placeholder="关键词数" style="width:120px;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px" value="80">
        <input type="number" id="mt-st" placeholder="策略数" style="width:120px;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px" value="9">
        <button class="btn btn-primary" onclick="runMaturity()">计算成熟度</button>
      </div>
    </div>
    <div id="mt-result"></div>
  `;
  loadMaturityLayers();
}

async function loadMaturityLayers() {
  try {
    const resp = await fetch(`${API}/api/maturity/layers`);
    const result = await resp.json();
    if (!result.success) return;
  const el = document.getElementById('mt-result');
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">六层模型说明</span></div>
      ${result.data.map((l, i) => `
        <div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--border)">
          <div style="width:32px;height:32px;border-radius:50%;background:var(--bg-darker);display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:var(--accent)">L${i + 1}</div>
          <div style="flex:1">
            <div style="font-size:13px;font-weight:600">${l.name} <span style="color:var(--accent)">「${l.goal}」</span></div>
            <div style="font-size:11px;color:var(--text-muted)">${l.description}</div>
          </div>
          <div style="font-size:12px;color:var(--text-muted)">权重${l.weight}%</div>
        </div>
      `).join('')}
    </div>
  `;
  } catch(e) { console.warn('loadMaturityLayers:', e); }
}

async function runMaturity() {
  const el = document.getElementById('mt-result');
  el.innerHTML = '<div class="loading"><div class="spinner"></div>计算六层成熟度...</div>';

  const payload = {};
  if (document.getElementById('mt-diag').checked) payload.diagnosis = { score: 70, checks: { meta_tags: { title: 'test', description: 'test' }, structured_data: { json_ld_count: 2 }, ai_readability: { text_length: 1200, h1_count: 1, h2_count: 5 }, links: { internal_count: 10, external_count: 5 }, contact_info: { has_phone: true, has_email: true, has_address: false, has_contact_page: true }, llms_txt: { exists: true } } };
  if (document.getElementById('mt-bench').checked) payload.benchmark = { citation_rate: 0.35, avg_rank: 2.5 };
  if (document.getElementById('mt-sheep').checked) payload.sheep = { gem_score: 52, level: 'C+' };
  if (document.getElementById('mt-gdo').checked) payload.gdo = { overall_score: 65, level: 'C', summary: '基础证据存在但关键维度有缺口' };
  payload.keywords_count = parseInt(document.getElementById('mt-kw').value) || 0;
  payload.strategies_count = parseInt(document.getElementById('mt-st').value) || 0;

  const result = await apiPost('/api/maturity/score', payload);
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const levelColors = { S: 'var(--accent)', A: '#34d399', B: 'var(--warning)', C: '#fb923c', D: 'var(--danger)' };
  const layers = d.layers || [];

  el.innerHTML = `
    <div class="grid-3" style="margin-bottom:16px">
      <div class="metric"><div class="metric-value" style="color:${levelColors[d.level]}">${d.overall_score}</div><div class="metric-label">总评分 (${d.level} - ${d.level_label})</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--danger)">${d.weakest_layer.score}</div><div class="metric-label">最薄弱：${d.weakest_layer.name}</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--accent)">${d.strongest_layer.score}</div><div class="metric-label">最强：${d.strongest_layer.name}</div></div>
    </div>
    <div class="card" style="margin-bottom:12px">
      <div class="card-header"><span class="card-title">六层评分雷达</span></div>
      ${layers.map((l, i) => {
        const pct = l.score;
        const color = levelColors[l.level] || 'var(--text-muted)';
        return `
          <div style="margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
              <div style="font-size:13px;font-weight:600">L${i + 1} ${l.name} <span style="color:var(--accent)">「${l.goal}」</span></div>
              <div style="font-size:14px;font-weight:700;color:${color}">${l.score} (${l.level})</div>
            </div>
            <div class="progress-bar" style="width:100%;height:8px">
              <div class="progress-fill" style="width:${pct}%;background:${color};height:8px"></div>
            </div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:2px">权重${l.weight}% | ${Object.entries(l.details || {}).map(([k, v]) => `${k}:${v}`).join(', ')}</div>
          </div>
        `;
      }).join('')}
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">模型来源</span></div>
      <div style="font-size:12px;color:var(--text-muted);line-height:1.8">
        <div>${d.model}</div>
        <div>来源：${d.source}</div>
      </div>
    </div>
  `;
}

// ========== GEO A/B测试 ==========

function renderABTest(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>GEO A/B测试</h1><p>固定问题集×多AI平台×优化前后对比×信源分类统计</p></div>
    </div>
    <div class="card" style="margin-bottom:12px">
      <div class="card-header"><span class="card-title">创建测试套件</span></div>
      <div style="margin-bottom:10px">
        <input type="text" id="abtest-name" placeholder="测试名称，如：工业检测设备GEO测试" style="width:100%;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;margin-bottom:8px">
        <input type="text" id="abtest-company" placeholder="公司名称" style="width:100%;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;margin-bottom:8px" value="${companyData ? companyData.name : ''}">
        <input type="text" id="abtest-domain" placeholder="官网域名" style="width:100%;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;margin-bottom:8px" value="${companyData ? companyData.domain : ''}">
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:4px">问题列表（每行一个）：</div>
      <textarea id="abtest-questions" style="width:100%;height:120px;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:12px" placeholder="工业检测设备有哪些品牌？&#10;XX品牌的检测设备怎么样？&#10;工业检测设备选型要注意什么？">XX公司是做什么的？\nXX公司的产品有哪些？\nXX公司适合什么行业？\n工业检测设备推荐哪家？\nXX公司值得合作吗？</textarea>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button class="btn btn-primary" onclick="createABTest()">创建套件</button>
        <button class="btn" onclick="loadABSuites()">查看已有套件</button>
      </div>
    </div>
    <div id="abtest-result"></div>
  `;
}

async function createABTest() {
  const name = document.getElementById('abtest-name').value.trim();
  const company = document.getElementById('abtest-company').value.trim();
  const questions = document.getElementById('abtest-questions').value.split('\n').map(q => q.trim()).filter(q => q);
  if (!name || !company || !questions.length) return;
  const el = document.getElementById('abtest-result');
  el.innerHTML = '<div class="loading"><div class="spinner"></div>创建测试套件...</div>';

  const result = await apiPost('/api/geo-abtest/create', { company_id: companyData ? companyData.id : 1, name, questions });
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const testId = result.data.id;
  el.innerHTML = `
    <div class="card" style="border-color:var(--accent-dim)">
      <div class="card-header"><span class="card-title">套件已创建 (ID: ${testId})</span></div>
      <div style="font-size:13px;line-height:1.8">
        <div>名称：${name}</div>
        <div>问题数：${questions.length}</div>
        <div>平台：Kimi/DeepSeek/GLM/MiniMax/HY3</div>
      </div>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button class="btn btn-primary" onclick="runABTest(${testId}, 'before')">运行优化前测试</button>
        <button class="btn" onclick="runABTest(${testId}, 'after')">运行优化后测试</button>
        <button class="btn" onclick="compareABTest(${testId})">对比结果</button>
      </div>
    </div>
    <div id="abtest-run-result"></div>
  `;
}

async function runABTest(testId, phase) {
  const company = document.getElementById('abtest-company').value.trim();
  const domain = document.getElementById('abtest-domain').value.trim();
  const el = document.getElementById('abtest-run-result');
  if (!el) return;
  el.innerHTML = `<div class="loading"><div class="spinner"></div>执行${phase === 'before' ? '优化前' : '优化后'}测试中（5平台×5问题=25次AI调用）...</div>`;

  const result = await apiPost(`/api/geo-abtest/run/${testId}`, { company_name: company, company_domain: domain, phase });
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const stats = d.stats;
  const platforms = stats.by_platform || {};

  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">${phase === 'before' ? '优化前' : '优化后'}测试结果</span></div>
      <div class="grid-4" style="margin-bottom:12px">
        <div class="metric"><div class="metric-value">${stats.total_queries}</div><div class="metric-label">总查询数</div></div>
        <div class="metric"><div class="metric-value" style="color:var(--accent)">${stats.total_mentions}</div><div class="metric-label">品牌提及数</div></div>
        <div class="metric"><div class="metric-value">${stats.overall_mention_rate}%</div><div class="metric-label">总提及率</div></div>
        <div class="metric"><div class="metric-value" style="color:var(--accent)">${stats.official_site_mentions}</div><div class="metric-label">官网引用数</div></div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>平台</th><th>总查询</th><th>品牌提及</th><th>官网引用</th><th>提及率</th><th>官网率</th></tr></thead>
          <tbody>
            ${Object.entries(platforms).map(([platform, data]) => `
              <tr>
                <td style="font-size:12px">${platform}</td>
                <td style="font-size:12px">${data.total}</td>
                <td style="font-size:12px;color:var(--accent)">${data.mentioned}</td>
                <td style="font-size:12px;color:var(--accent)">${data.official_site || 0}</td>
                <td style="font-size:12px">${data.mention_rate}%</td>
                <td style="font-size:12px">${data.official_rate}%</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      <div style="margin-top:12px">
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:4px">信源分类统计：</div>
        ${Object.entries(stats.by_source || {}).map(([source, count]) => {
          const labels = { official_site: '官网', b2b_platform: 'B2B平台', self_media: '自媒体', third_party_media: '第三方媒体', other: '其他', none: '未提及' };
          const colors = { official_site: 'var(--accent)', b2b_platform: 'var(--info)', self_media: '#a78bfa', third_party_media: '#fb923c', other: 'var(--text-muted)', none: 'var(--text-muted)' };
          return `<span style="display:inline-block;font-size:12px;padding:3px 8px;margin:2px;border-radius:4px;background:rgba(255,255,255,0.05);color:${colors[source] || 'var(--text)'}">${labels[source] || source}: ${count}</span>`;
        }).join('')}
      </div>
    </div>
  `;
}

async function compareABTest(testId) {
  const el = document.getElementById('abtest-run-result');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>加载对比数据...</div>';

  const result = await apiGet(`/api/geo-abtest/compare/${testId}`);
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  const stats = d.stats || {};
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">${d.name} - ${d.phase} 阶段数据</span></div>
      <div style="font-size:13px;line-height:1.8">
        <div>总查询：${stats.total_queries || 0}</div>
        <div>品牌提及：${stats.total_mentions || 0}（${stats.overall_mention_rate || 0}%）</div>
        <div>官网引用：${stats.official_site_mentions || 0}（${stats.official_site_rate || 0}%）</div>
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-top:8px">提示：需分别运行"优化前"和"优化后"测试后，在此查看各阶段数据对比</div>
    </div>
  `;
}

async function loadABSuites() {
  const el = document.getElementById('abtest-result');
  const result = await apiGet('/api/geo-abtest/suites');
  if (!result.success || !result.data.length) {
    el.innerHTML = '<div class="card"><p style="color:var(--text-muted)">暂无测试套件</p></div>';
    return;
  }

  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">已有测试套件</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>名称</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead>
          <tbody>
            ${result.data.map(s => `
              <tr>
                <td style="font-size:12px">${s.id}</td>
                <td style="font-size:12px">${s.name}</td>
                <td style="font-size:12px">${s.status}</td>
                <td style="font-size:11px;color:var(--text-muted)">${s.created_at}</td>
                <td><button class="btn" style="padding:2px 8px;font-size:11px" onclick="compareABTest(${s.id})">查看</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// ========== PDF去重审计 ==========

function renderPdfDedup(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>PDF去重审计</h1><p>检测网站重复PDF文件，生成301重定向规则，合并重复内容保留SEO权益</p></div>
    </div>
    <div class="card" style="margin-bottom:12px">
      <div class="card-header"><span class="card-title">审计输入</span></div>
      <div style="margin-bottom:10px">
        <input type="text" id="pdf-domain" placeholder="网站域名（如 example.com）" style="width:100%;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;margin-bottom:8px" value="${companyData ? companyData.domain : ''}">
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:4px">或手动输入PDF URL列表（每行一个）：</div>
      <textarea id="pdf-urls" style="width:100%;height:100px;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:12px" placeholder="https://example.com/product-a.pdf&#10;https://example.com/product-b.pdf"></textarea>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button class="btn btn-primary" onclick="runPdfAudit()">开始审计</button>
      </div>
    </div>
    <div id="pdf-result"></div>
  `;
}

async function runPdfAudit() {
  const domain = document.getElementById('pdf-domain').value.trim();
  const urlsText = document.getElementById('pdf-urls').value.trim();
  const el = document.getElementById('pdf-result');

  if (!domain && !urlsText) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>审计PDF文件中（下载+哈希比对）...</div>';

  let payload = {};
  if (urlsText) {
    payload.urls = urlsText.split('\n').map(u => u.trim()).filter(u => u);
  } else {
    payload.domain = domain;
  }

  const result = await apiPost('/api/pdf-dedup/audit', payload);
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  if (d.error) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${d.error}</p></div>`;
    return;
  }

  const summary = d.summary || {};
  const duplicates = d.duplicates || [];

  el.innerHTML = `
    <div class="grid-4" style="margin-bottom:16px">
      <div class="metric"><div class="metric-value">${d.total_urls || d.pdfs_found || 0}</div><div class="metric-label">PDF总数</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--accent)">${d.unique_pdfs || 0}</div><div class="metric-label">唯一PDF</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--danger)">${d.total_duplicates || 0}</div><div class="metric-label">重复文件</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--warning)">${summary.recommended_redirects || 0}</div><div class="metric-label">建议301重定向</div></div>
    </div>
    ${duplicates.length === 0 ? `
      <div class="card" style="text-align:center;border-color:var(--accent-dim)">
        <div style="font-size:14px;color:var(--accent)">未发现重复PDF</div>
      </div>
    ` : duplicates.map(group => `
      <div class="card" style="margin-bottom:12px;border-color:var(--warning)">
        <div class="card-header">
          <span class="card-title" style="color:var(--warning)">重复组 (hash: ${group.hash}...)</span>
          <span style="font-size:12px;color:var(--text-muted)">${group.duplicate_count + 1}份相同文件</span>
        </div>
        <div style="margin-bottom:8px">
          <div style="font-size:12px;color:var(--accent);font-weight:600">规范URL（保留）：</div>
          <div style="font-size:12px;color:var(--accent);word-break:break-all">${group.canonical_url}</div>
        </div>
        <div style="margin-bottom:8px">
          <div style="font-size:12px;color:var(--danger);font-weight:600">重复URL（需301重定向）：</div>
          ${group.duplicate_urls.map(url => `<div style="font-size:12px;color:var(--danger);word-break:break-all">${url}</div>`).join('')}
        </div>
        <div style="background:rgba(255,255,255,0.03);border-radius:6px;padding:8px;margin-top:8px">
          <div style="font-size:12px;color:var(--text-muted);font-weight:600;margin-bottom:4px">Nginx 301重定向规则：</div>
          ${group.redirect_rules.map(rule => `<div style="font-size:11px;font-family:monospace;color:var(--info)">rewrite ^${new URL(rule.from).pathname}$ ${rule.to} permanent;</div>`).join('')}
        </div>
      </div>
    `).join('')}
  `;
}

// ========== 内容合规检测 ==========

const COMPLIANCE_TYPE_NAMES = {
  superlative: '极限词',
  fake_endorsement: '伪造权威背书',
  absolute_claim: '绝对化承诺',
  keyword_stuffing: '关键词堆砌',
};

function renderCompliance(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>内容合规检测</h1><p>2026-07 AI内容监管新规：极限词/伪造背书/绝对化承诺/关键词堆砌四类风险检测，发布前必检</p></div>
    </div>
    <div class="card" style="margin-bottom:12px">
      <div class="card-header"><span class="card-title">待检测内容</span></div>
      <textarea id="compliance-content" style="width:100%;height:160px;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:13px;line-height:1.6" placeholder="粘贴要发布的文案、FAQ、文章正文..."></textarea>
      <div style="margin-top:8px">
        <input type="text" id="compliance-keywords" placeholder="关键词密度检测（可选，逗号分隔，如：品牌名,核心产品词）" style="width:100%;background:var(--bg-darker);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:12px">
      </div>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button class="btn btn-primary" onclick="runComplianceCheck()">开始检测</button>
        <button class="btn" onclick="loadComplianceRules()">查看检测规则</button>
      </div>
    </div>
    <div id="compliance-result"></div>
  `;
}

async function loadComplianceRules() {
  const el = document.getElementById('compliance-result');
  const result = await apiGet('/api/compliance/rules');
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }
  el.innerHTML = result.data.map(r => `
    <div class="card" style="margin-bottom:8px">
      <div class="card-header"><span class="card-title">${r.name}</span></div>
      <div style="font-size:12px;color:var(--text);margin-bottom:4px">${r.description}</div>
      <div style="font-size:11px;color:var(--text-muted)">依据：${r.basis}</div>
    </div>
  `).join('');
}

async function runComplianceCheck() {
  const content = document.getElementById('compliance-content').value.trim();
  const keywordsText = document.getElementById('compliance-keywords').value.trim();
  const el = document.getElementById('compliance-result');

  if (!content) {
    el.innerHTML = '<div class="card"><p style="color:var(--warning)">请输入待检测内容</p></div>';
    return;
  }
  el.innerHTML = '<div class="loading"><div class="spinner"></div>检测合规风险中...</div>';

  const payload = { content };
  if (keywordsText) {
    payload.keywords = keywordsText.split(/[,，]/).map(k => k.trim()).filter(k => k);
  }

  const result = await apiPost('/api/compliance/check', payload);
  if (!result.success) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${result.error}</p></div>`;
    return;
  }

  const d = result.data;
  if (d.error) {
    el.innerHTML = `<div class="card"><p style="color:var(--danger)">${d.error}</p></div>`;
    return;
  }

  const levelMap = {
    high: { label: '高风险 — 禁止发布', color: 'var(--danger)' },
    medium: { label: '中风险 — 需佐证或修正', color: 'var(--warning)' },
    low: { label: '低风险', color: 'var(--info)' },
    pass: { label: '合规通过', color: 'var(--accent)' },
  };
  const level = levelMap[d.risk_level] || levelMap.pass;
  const sevColor = { high: 'var(--danger)', medium: 'var(--warning)', low: 'var(--info)' };
  const sevLabel = { high: '高', medium: '中', low: '低' };

  el.innerHTML = `
    <div class="grid-4" style="margin-bottom:16px">
      <div class="metric"><div class="metric-value" style="color:${level.color}">${level.label}</div><div class="metric-label">风险等级</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--danger)">${d.high_count || 0}</div><div class="metric-label">高风险项</div></div>
      <div class="metric"><div class="metric-value" style="color:var(--warning)">${d.medium_count || 0}</div><div class="metric-label">中风险项</div></div>
      <div class="metric"><div class="metric-value">${d.total_violations || 0}</div><div class="metric-label">违规总数</div></div>
    </div>
    ${d.total_violations === 0 ? `
      <div class="card" style="text-align:center;border-color:var(--accent-dim)">
        <div style="font-size:14px;color:var(--accent)">未检出合规风险，内容可发布</div>
      </div>
    ` : `
      <div class="card">
        <div class="card-header"><span class="card-title">违规明细（${d.total_violations}项）</span></div>
        <table style="width:100%;font-size:12px;border-collapse:collapse">
          <thead>
            <tr style="color:var(--text-muted);text-align:left;border-bottom:1px solid var(--border)">
              <th style="padding:6px">级别</th><th style="padding:6px">类型</th><th style="padding:6px">命中词</th><th style="padding:6px">上下文</th><th style="padding:6px">修正建议</th>
            </tr>
          </thead>
          <tbody>
            ${d.violations.map(v => `
              <tr style="border-bottom:1px solid var(--border)">
                <td style="padding:6px;color:${sevColor[v.severity]};font-weight:600">${sevLabel[v.severity]}</td>
                <td style="padding:6px">${COMPLIANCE_TYPE_NAMES[v.type] || v.type}</td>
                <td style="padding:6px;color:${sevColor[v.severity]}">${v.term}</td>
                <td style="padding:6px;color:var(--text-muted)">${v.context}</td>
                <td style="padding:6px;color:var(--text-muted)">${v.suggestion}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `}
  `;
}

// ========== 套餐计费 ==========

function renderBilling(el) {
  el.innerHTML = `
    <div class="page-header">
      <div><h1>套餐计费</h1><p>查看用量、升级套餐、管理订阅</p></div>
    </div>
    <div id="billing-usage"></div>
    <div id="billing-plans"></div>
  `;
  loadBillingUsage();
  loadBillingPlans();
}

async function loadBillingUsage() {
  const el = document.getElementById('billing-usage');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>加载用量...</div>';
  const data = await apiGet('/api/billing/usage');
  if (data.error) { el.innerHTML = `<div class="card"><p style="color:var(--danger)">${data.error}</p></div>`; return; }
  const u = data.usage;
  const pct = (used, limit) => limit > 0 ? Math.min(100, used / limit * 100) : 0;
  const barColor = (used, limit) => pct(used, limit) > 80 ? 'var(--danger)' : pct(used, limit) > 50 ? 'var(--warning)' : 'var(--accent)';
  el.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">当前用量</span><span class="badge badge-success">${data.plan_name}</span></div>
      <div style="padding:16px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px">
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span style="font-size:13px">企业数</span><span style="font-size:13px;color:var(--text-muted)">${u.companies.used}/${u.companies.limit === 999 ? '不限' : u.companies.limit}</span></div>
          <div class="progress-bar" style="width:100%"><div class="progress-fill" style="width:${pct(u.companies.used, u.companies.limit)}%;background:${barColor(u.companies.used, u.companies.limit)}"></div></div>
        </div>
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span style="font-size:13px">本月监控</span><span style="font-size:13px;color:var(--text-muted)">${u.monitors_per_month.used}/${u.monitors_per_month.limit === 9999 ? '不限' : u.monitors_per_month.limit}</span></div>
          <div class="progress-bar" style="width:100%"><div class="progress-fill" style="width:${pct(u.monitors_per_month.used, u.monitors_per_month.limit)}%;background:${barColor(u.monitors_per_month.used, u.monitors_per_month.limit)}"></div></div>
        </div>
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span style="font-size:13px">本月报告</span><span style="font-size:13px;color:var(--text-muted)">${u.reports_per_month.used}/${u.reports_per_month.limit === 9999 ? '不限' : u.reports_per_month.limit}</span></div>
          <div class="progress-bar" style="width:100%"><div class="progress-fill" style="width:${pct(u.reports_per_month.used, u.reports_per_month.limit)}%;background:${barColor(u.reports_per_month.used, u.reports_per_month.limit)}"></div></div>
        </div>
      </div>
    </div>
  `;
}

async function loadBillingPlans() {
  const el = document.getElementById('billing-plans');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div>加载套餐...</div>';
  const data = await apiGet('/api/billing/plans');
  if (!data.success) { el.innerHTML = '<div class="card"><p>加载失败</p></div>'; return; }
  const currentPlan = currentUser ? currentUser.plan : 'free';
  el.innerHTML = `
    <div class="grid-3">
      ${data.data.map(p => `
        <div class="card" style="border:${p.id === currentPlan ? '2px solid var(--accent)' : '1px solid var(--border)'};position:relative">
          ${p.id === currentPlan ? '<div style="position:absolute;top:-1px;right:-1px;background:var(--accent);color:var(--bg);font-size:11px;padding:2px 8px;border-radius:0 0 0 6px">当前</div>' : ''}
          <div style="padding:20px">
            <h3 style="font-size:16px;font-weight:700;margin-bottom:8px">${p.name}</h3>
            <div style="margin-bottom:16px">
              <span style="font-size:28px;font-weight:700;color:var(--accent)">¥${p.price}</span>
              <span style="font-size:13px;color:var(--text-muted)">/${p.period}</span>
            </div>
            <div style="margin-bottom:16px">
              ${p.features.map(f => `<div style="font-size:13px;color:var(--text-muted);margin-bottom:6px">✓ ${f}</div>`).join('')}
            </div>
            ${p.id === currentPlan
              ? '<button class="btn" style="width:100%;opacity:0.5;cursor:default" disabled>当前套餐</button>'
              : `<button class="btn btn-primary" style="width:100%" onclick="upgradePlan('${p.id}')">升级到${p.name}</button>`
            }
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

async function upgradePlan(planId) {
  if (!confirm(`确认升级套餐？`)) return;
  const data = await apiPost('/api/billing/upgrade', { plan: planId });
  if (data.error) { alert(data.error); return; }
  if (data.success) {
    setToken(data.token);
    currentUser = { ...currentUser, plan: data.plan };
    updateSidebarUser();
    loadBillingUsage();
    loadBillingPlans();
    alert(data.message);
  }
}

// ========== Init ==========

(async () => {
  if (await checkAuth()) {
    renderPage();
  }
})();
