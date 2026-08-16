/* GEO 落地页交互 —— 免费快扫 + 内容渲染 */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };

  var GRADE_CLASS = {
    'A+': 'g-Aplus', 'A': 'g-A', 'B+': 'g-Bplus', 'B': 'g-B',
    'C+': 'g-Cplus', 'C': 'g-C', 'D': 'g-D'
  };
  var SEV_LABEL = { fatal: '致命', high: '高', medium: '中', low: '低' };

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ===== Features ===== */
  function loadFeatures() {
    fetch('/api/public/features').then(function (r) { return r.json(); }).then(function (res) {
      if (!res || !res.success) return renderFeaturesHardcoded();
      var html = res.data.map(function (f) {
        var tag = f.tag ? '<span class="tag">' + escapeHtml(f.tag) + '</span>' : '';
        return '<div class="feat"><div class="ico">' + escapeHtml(f.icon) + '</div>' +
          '<h3>' + escapeHtml(f.name) + tag + '</h3><p>' + escapeHtml(f.desc) + '</p></div>';
      }).join('');
      $('feat-grid').innerHTML = html;
    }).catch(function () { renderFeaturesHardcoded(); });
  }

  function renderFeaturesHardcoded() {
    var feats = [
      ['★', 'SHEEP 五维评分', 'S/H/E1/E2/P 五维 + GEM 综合分，自洽多采样与证据锚定反思', '独家'],
      ['⚙', '网站 GEO 诊断', '抓取页面，技术 SEO、结构化数据、AI 可读性体检', ''],
      ['⚡', '一键优化产物', '生成 llms.txt / robots.txt / sitemap.xml / meta / FAQ', ''],
      ['◉', 'AI 引擎可见性监控', '定时检测在 DeepSeek/Kimi/豆包/文心/通义中的被引用与准确率', ''],
      ['❖', '竞品追踪', '声音份额、引用差距、排名对比分析', ''],
      ['⚠', '内容合规门禁', '极限词/伪造背书/绝对化承诺/关键词堆砌检测，发布前硬约束', '独家'],
      ['▲', '六层成熟度', '全站 GEO 成熟度分层评估', ''],
      ['✉', 'RAG 知识问答', '基于已入库企业知识的检索增强对话', ''],
      ['▤', '报告与导出', 'PDF 体检报告、CSV 监控历史、执行仪表板', '']
    ];
    $('feat-grid').innerHTML = feats.map(function (f) {
      var tag = f[3] ? '<span class="tag">' + f[3] + '</span>' : '';
      return '<div class="feat"><div class="ico">' + f[0] + '</div><h3>' + f[1] + tag + '</h3><p>' + f[2] + '</p></div>';
    }).join('');
  }

  /* ===== Cases ===== */
  function loadCases() {
    fetch('/api/public/cases').then(function (r) { return r.json(); }).then(function (res) {
      if (!res || !res.success || !res.data || !res.data.length) {
        $('case-grid').innerHTML = '<div class="cases-empty">暂无公开案例，登录后可查看完整案例库。</div>';
        return;
      }
      $('case-grid').innerHTML = res.data.map(function (c) {
        var gc = GRADE_CLASS[c.grade] || 'g-D';
        var adv = c.core_advantage ? '<p>' + escapeHtml(c.core_advantage) + '</p>' : '';
        return '<div class="case">' +
          '<div class="co">' + escapeHtml(c.company_name) + '</div>' +
          '<div class="dom">' + escapeHtml(c.domain || '') + '</div>' +
          '<div class="scoreline"><span class="n">' + (c.score || 0) + '</span>' +
          '<span class="gl ' + gc + '">等级 ' + escapeHtml(c.grade || 'D') + '</span></div>' +
          (c.summary ? '<p>' + escapeHtml(c.summary) + '</p>' : '') + adv +
          '</div>';
      }).join('');
    }).catch(function () {
      $('case-grid').innerHTML = '<div class="cases-empty">案例加载失败，请稍后刷新。</div>';
    });
  }

  /* ===== Free scan ===== */
  function showError(msg) {
    var el = $('scan-error');
    el.textContent = msg;
    el.classList.add('show');
  }
  function clearError() { var el = $('scan-error'); el.textContent = ''; el.classList.remove('show'); }

  function runScan(url) {
    clearError();
    var box = $('scan-result');
    box.className = 'scan-result show';
    box.innerHTML = '<div class="scan-loading">正在抓取并分析网址，请稍候…</div>';
    var btn = $('scan-btn'); var orig = btn.textContent;
    btn.disabled = true; btn.textContent = '分析中…';

    fetch('/api/public/quick-scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    }).then(function (r) {
      return r.json().then(function (body) { return { status: r.status, body: body }; });
    }).then(function (out) {
      btn.disabled = false; btn.textContent = orig;
      var body = out.body || {};
      if (out.status === 429 || (body && body.error && body.error.indexOf('上限') > -1)) {
        box.className = 'scan-result';
        showError(body.error || '免费快扫次数已达上限，登录后不限次。');
        return;
      }
      if (!body.success) {
        box.className = 'scan-result';
        showError(body.error || '分析失败，请检查网址后重试。');
        return;
      }
      renderScanResult(body.data);
    }).catch(function () {
      btn.disabled = false; btn.textContent = orig;
      box.className = 'scan-result';
      showError('网络错误，请稍后重试。');
    });
  }

  function renderScanResult(d) {
    var box = $('scan-result');
    box.className = 'scan-result show';
    var score = d.score || 0;
    var gc = GRADE_CLASS[d.grade] || 'g-D';
    var p = Math.max(0, Math.min(100, score));

    var checklist = (d.checklist || []).map(function (c) {
      var cls = c.pass ? 'pass' : 'fail';
      var ico = c.pass ? '✓' : '✕';
      return '<div class="chk ' + cls + '"><div class="ico">' + ico + '</div>' +
        '<div><div class="t">' + escapeHtml(c.label) + '</div>' +
        '<div class="d">' + escapeHtml(c.detail || '') + '</div></div></div>';
    }).join('');

    var issues = (d.top_issues || []).map(function (i) {
      var sev = i.severity || 'low';
      return '<div class="issue-item"><span class="sev sev-' + sev + '">' + (SEV_LABEL[sev] || sev) + '</span>' +
        '<span>' + escapeHtml(i.message || '') + '</span></div>';
    }).join('');

    var spaNote = d.is_spa ? '<div class="issue-item"><span class="sev sev-high">SPA</span>' +
      '<span>检测到单页应用空壳，AI 爬虫无法提取页面文本/结构化数据，登录后查看一键优化方案。</span></div>' : '';

    box.innerHTML =
      '<div class="result-card">' +
        '<div class="score-row">' +
          '<div class="score-ring" style="--p:' + p + '%"><div class="num">' + score + '<small>/100</small></div></div>' +
          '<div class="score-meta">' +
            '<h3>GEO 就绪度 <span class="grade ' + gc + '">' + escapeHtml(d.grade || 'D') + '</span></h3>' +
            '<div class="url">' + escapeHtml(d.url || '') + '</div>' +
            '<div style="margin-top:8px;color:var(--text-muted);font-size:14px">共发现 ' + (d.issue_count || 0) + ' 项问题</div>' +
          '</div>' +
        '</div>' +
        '<div class="checklist">' + checklist + '</div>' +
        (issues || spaNote ? '<div class="top-issues"><h4>最关键问题</h4>' + spaNote + issues + '</div>' : '') +
        '<div class="locked">' +
          '<div style="font-size:15px;font-weight:700;color:#fff">完整报告与优化能力已锁定</div>' +
          '<div style="color:var(--text-muted);font-size:13px;margin-top:6px">登录解锁以下能力</div>' +
          '<div class="lock-list">' +
            '<span>SHEEP 五维 + GEM 综合分</span>' +
            '<span>一键生成 llms.txt / JSON-LD / FAQ</span>' +
            '<span>AI 引擎可见性监控</span>' +
            '<span>竞品声音份额对比</span>' +
            '<span>PDF 体检报告导出</span>' +
          '</div>' +
          '<a class="btn btn-primary" href="/app">登录解锁完整能力</a>' +
        '</div>' +
      '</div>';
    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /* ===== Init ===== */
  document.addEventListener('DOMContentLoaded', function () {
    loadFeatures();
    loadCases();
    $('scan-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var url = ($('scan-url').value || '').trim();
      if (!url) { showError('请输入网址'); return; }
      runScan(url);
    });
  });
})();
