import "./health-link-panel.js?v=0.3.3";

const HealthLinkPanel = customElements.get("health-link-panel");
const proto = HealthLinkPanel?.prototype;

if (!proto) throw new Error("HealthLink panel base component is unavailable");

const baseBind = proto._bind;

proto._profileControls = function () {
  const options = this._profiles.map(p => `<option value="${this._esc(p.config_entry_id)}" ${p.config_entry_id === this._entryId ? "selected" : ""}>${this._esc(p.title)}${p.available === false ? this._t(" · 연결 대기", " · waiting") : ""}</option>`).join("");
  return `<div class="profile-picker"><span class="control-label">${this._t("건강 프로필", "Health profile")}</span><select id="profile" aria-label="${this._t("건강 프로필 선택", "Select health profile")}" ${options ? "" : "disabled"}>${options || `<option>${this._t("등록된 프로필 없음", "No profiles")}</option>`}</select></div>
    <button id="refreshProfiles" class="icon-button secondary" title="${this._t("새로고침", "Refresh")}" aria-label="${this._t("새로고침", "Refresh")}">↻</button>
    <a class="button-link primary-action" href="/config/integrations/dashboard/add?domain=health_link">+ ${this._t("프로필 추가", "Add profile")}</a>
    <a class="button-link secondary" href="/config/integrations/integration/health_link">${this._t("설정", "Settings")}</a>`;
};

proto._styles = function () { return `
  :host {
    display:block;
    min-height:100%;
    color:var(--primary-text-color);
    background:var(--primary-background-color);
    font-family:var(--paper-font-body1_-_font-family, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
    --hl-radius-lg:12px;
    --hl-radius-md:10px;
    --hl-radius-sm:8px;
    --hl-border:color-mix(in srgb,var(--divider-color) 86%,transparent);
    --hl-soft:color-mix(in srgb,var(--secondary-background-color) 72%,var(--card-background-color));
    --hl-primary-soft:color-mix(in srgb,var(--primary-color) 9%,var(--card-background-color));
    --hl-success:var(--success-color,#22a06b);
    --hl-warning:var(--warning-color,#d97706);
  }
  * { box-sizing:border-box; }
  a { color:inherit; }
  .wrap { max-width:1280px; margin:0 auto; padding:26px 24px 64px; }
  .topbar { display:flex; gap:24px; align-items:flex-start; justify-content:space-between; margin-bottom:22px; }
  .brand-block { min-width:240px; }
  .brand-block h1 { margin:0; }
  .brand-block img { width:min(320px,62vw); height:auto; display:block; }
  .brand-block .sub { margin:8px 0 0; max-width:620px; }
  #profileControls { display:flex; align-items:flex-end; justify-content:flex-end; gap:8px; flex-wrap:wrap; }
  .profile-picker { display:flex; flex-direction:column; gap:5px; }
  .control-label { color:var(--secondary-text-color); font-size:11px; font-weight:700; letter-spacing:.02em; }
  h2 { font-size:21px; line-height:1.25; margin:28px 0 5px; letter-spacing:-.015em; }
  h3 { margin:0 0 7px; font-size:16px; line-height:1.35; }
  .sub,.note,.section-sub { color:var(--secondary-text-color); font-size:13px; line-height:1.55; }
  .section-sub { margin-bottom:14px; }
  select,input,button { font:inherit; }
  select,input { min-height:40px; border:1px solid var(--hl-border); border-radius:var(--hl-radius-sm); padding:7px 10px; background:var(--card-background-color); color:var(--primary-text-color); }
  button,.button-link { min-height:40px; border:1px solid transparent; border-radius:var(--hl-radius-sm); padding:0 13px; cursor:pointer; background:var(--primary-color); color:var(--text-primary-color,#fff); font-weight:700; display:inline-flex; align-items:center; justify-content:center; text-decoration:none; white-space:nowrap; }
  button.secondary,.button-link.secondary { color:var(--primary-text-color); background:var(--card-background-color); border-color:var(--hl-border); }
  .button-link.primary-action { background:var(--primary-color); color:#fff; }
  .icon-button { min-width:40px; padding:0; font-size:19px; }
  button.danger { background:var(--error-color); color:#fff; }
  button:focus-visible,select:focus-visible,input:focus-visible,[role=tab]:focus-visible,a:focus-visible { outline:3px solid color-mix(in srgb,var(--primary-color) 42%,transparent); outline-offset:2px; }
  .tabs-shell { border:1px solid var(--hl-border); border-radius:var(--hl-radius-md); background:var(--card-background-color); padding:0 10px; box-shadow:0 1px 2px rgba(0,0,0,.025); }
  .tabs { display:flex; gap:5px; overflow:auto; padding:0; border:0; scrollbar-width:thin; }
  [role=tab] { position:relative; min-height:48px; padding:0 14px; border:0; border-radius:0; background:transparent; color:var(--secondary-text-color); font-weight:700; white-space:nowrap; }
  [role=tab]::after { content:""; position:absolute; left:14px; right:14px; bottom:0; height:2px; border-radius:2px 2px 0 0; background:transparent; }
  [role=tab][aria-selected=true] { color:var(--primary-color); background:transparent; }
  [role=tab][aria-selected=true]::after { background:var(--primary-color); }
  .panel-body { padding-top:4px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; }
  .summary-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:14px; }
  .dashboard-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:14px; }
  .card,.summary-card,.panel-card { border:1px solid var(--hl-border); border-radius:var(--hl-radius-lg); padding:18px; background:var(--card-background-color); box-shadow:0 1px 3px rgba(0,0,0,.045); }
  .summary-card { min-height:158px; display:flex; flex-direction:column; justify-content:space-between; }
  .summary-card .eyebrow { display:flex; align-items:center; gap:8px; color:var(--secondary-text-color); font-size:12px; font-weight:700; }
  .summary-card .status-value { font-size:24px; line-height:1.2; font-weight:800; letter-spacing:-.03em; margin:13px 0 7px; }
  .summary-card .detail { color:var(--secondary-text-color); font-size:12px; line-height:1.45; }
  .status-dot { width:8px; height:8px; border-radius:50%; background:var(--primary-color); flex:0 0 auto; }
  .status-dot.success { background:var(--hl-success); } .status-dot.warning { background:var(--hl-warning); } .status-dot.muted { background:var(--secondary-text-color); }
  .metric .value { font-size:27px; font-weight:800; line-height:1.15; margin-top:8px; letter-spacing:-.025em; }
  .metric .label { color:var(--secondary-text-color); font-size:12px; font-weight:700; }
  .ok { color:var(--hl-success); } .warn { color:var(--hl-warning); } .bad { color:var(--error-color); }
  .info-banner { display:grid; grid-template-columns:auto 1fr auto; gap:14px; align-items:center; margin-top:18px; padding:16px 18px; border:1px solid color-mix(in srgb,var(--primary-color) 20%,var(--hl-border)); border-radius:var(--hl-radius-lg); background:var(--hl-primary-soft); }
  .info-icon { width:42px; height:42px; border-radius:var(--hl-radius-md); display:grid; place-items:center; color:var(--primary-color); background:color-mix(in srgb,var(--primary-color) 11%,transparent); font-size:20px; font-weight:800; }
  .info-banner strong { display:block; margin-bottom:3px; font-size:14px; }
  .setup { border-color:color-mix(in srgb,var(--primary-color) 35%,var(--hl-border)); background:var(--hl-primary-soft); }
  .section-head { display:flex; align-items:end; justify-content:space-between; gap:12px; margin-top:26px; }
  .section-head h2 { margin:0; }
  .section-action { color:var(--primary-color); font-size:12px; font-weight:700; text-decoration:none; }
  .progress-track { height:7px; border-radius:999px; overflow:hidden; background:color-mix(in srgb,var(--divider-color) 72%,transparent); margin-top:10px; }
  .progress-fill { height:100%; min-width:0; border-radius:inherit; background:var(--primary-color); }
  .progress-fill.success { background:var(--hl-success); }
  .progress-fill.warning { background:var(--hl-warning); }
  .goal-list,.status-list,.quick-list { display:grid; gap:0; }
  .goal-item,.status-item,.quick-item { display:grid; grid-template-columns:auto 1fr auto; gap:12px; align-items:center; min-height:64px; padding:12px 0; border-bottom:1px solid var(--hl-border); }
  .goal-item:last-child,.status-item:last-child,.quick-item:last-child { border-bottom:0; }
  .goal-icon,.quick-icon { width:34px; height:34px; border-radius:var(--hl-radius-sm); display:grid; place-items:center; background:var(--hl-soft); color:var(--primary-color); font-weight:800; }
  .goal-title,.quick-title { font-weight:800; font-size:13px; }
  .goal-meta,.quick-desc { color:var(--secondary-text-color); font-size:11px; margin-top:3px; }
  .goal-value,.status-value-sm { font-weight:800; font-size:14px; text-align:right; }
  .goal-progress-wrap { grid-column:2 / 4; margin-top:-2px; }
  .status-name { color:var(--secondary-text-color); font-size:12px; }
  .quick-item { cursor:pointer; text-decoration:none; color:inherit; }
  .quick-item:hover { color:var(--primary-color); }
  .quick-arrow { color:var(--secondary-text-color); font-size:18px; }
  .insight-card { border:1px solid color-mix(in srgb,var(--primary-color) 18%,var(--hl-border)); border-radius:var(--hl-radius-md); padding:15px; background:color-mix(in srgb,var(--primary-color) 5%,var(--card-background-color)); }
  .insight-title { font-weight:800; margin-bottom:5px; }
  .insight-copy { color:var(--secondary-text-color); font-size:12px; line-height:1.55; }
  .toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:14px 0; }
  .search { flex:1; min-width:220px; }
  .tablewrap { overflow:auto; border:1px solid var(--hl-border); border-radius:var(--hl-radius-md); background:var(--card-background-color); }
  table { width:100%; border-collapse:collapse; min-width:720px; }
  th,td { padding:12px 14px; border-bottom:1px solid var(--hl-border); text-align:left; vertical-align:middle; }
  th { font-size:11px; color:var(--secondary-text-color); position:sticky; top:0; background:var(--card-background-color); text-transform:none; letter-spacing:.02em; }
  tbody tr:hover { background:var(--hl-soft); }
  .tag { display:inline-flex; border-radius:999px; padding:3px 8px; font-size:11px; background:var(--hl-soft); }
  .switch { min-width:72px; }
  .builder { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
  .field { display:flex; flex-direction:column; gap:6px; }
  .field.full { grid-column:1/-1; }
  label { font-size:12px; font-weight:800; }
  .composer-list { display:grid; gap:8px; margin-top:14px; }
  .row { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 0; border-bottom:1px solid var(--hl-border); }
  .row:last-child { border-bottom:0; }
  .pair { word-break:break-all; padding:12px; border-radius:var(--hl-radius-sm); background:var(--hl-soft); font-family:monospace; font-size:12px; }
  .error { padding:12px 14px; border-radius:var(--hl-radius-md); background:color-mix(in srgb,var(--error-color) 11%,var(--card-background-color)); border:1px solid color-mix(in srgb,var(--error-color) 30%,var(--hl-border)); color:var(--error-color); margin:14px 0; }
  .empty { text-align:center; padding:46px 18px; color:var(--secondary-text-color); }
  .footer-note { margin-top:26px; padding-top:16px; border-top:1px solid var(--hl-border); color:var(--secondary-text-color); font-size:11px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }
  @media(max-width:980px){ .summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.dashboard-grid{grid-template-columns:1fr}.topbar{align-items:stretch;flex-direction:column}#profileControls{justify-content:flex-start} }
  @media(max-width:700px){ .wrap{padding:16px 12px 42px}.brand-block img{width:min(280px,76vw)}.tabs-shell{padding:0 4px}.summary-grid{grid-template-columns:1fr}.builder{grid-template-columns:1fr}.field.full{grid-column:auto}.info-banner{grid-template-columns:auto 1fr}.info-banner .banner-action{grid-column:1/-1}.profile-picker{width:100%}.profile-picker select{width:100%}#profileControls{width:100%}.button-link{flex:1}.summary-card{min-height:134px} }
  @media(prefers-reduced-motion:reduce){ *{scroll-behavior:auto!important;transition:none!important} }
`; };

proto._render = function () {
  if (!this.shadowRoot) return;
  const p = this._profile();
  this.shadowRoot.innerHTML = `<style>${this._styles()}</style><main class="wrap">
    <header class="topbar"><div class="brand-block"><h1><img id="healthLinkLogo" src="${this._esc(this._logoSource())}" alt="HealthLink" width="600" height="200"></h1><div class="sub">${this._t("Apple 건강과 집을 더 건강한 일상으로 연결합니다.","Turn Apple Health and home data into clearer daily context.")}</div></div>
    <div id="profileControls">${this._profileControls()}</div></header>
    ${this._error ? `<div class="error" role="alert">${this._esc(this._error)}</div>` : ""}
    <div class="tabs-shell"><nav class="tabs" role="tablist" aria-label="HealthLink">
      ${this._tabButton("today",this._t("오늘","Today"))}
      ${this._tabButton("explorer",this._t("건강 데이터","Health data"))}
      ${this._tabButton("timeline",this._t("타임라인","Timeline"))}
      ${this._tabButton("composer",this._t("센서 만들기","Create sensor"))}
      ${this._tabButton("insights",this._t("인사이트","Insights"))}
      ${this._tabButton("connect",this._t("연결 상태","Connection"))}
    </nav></div>
    <section class="panel-body" role="tabpanel">${this._loading ? `<div class="empty">${this._t("데이터를 불러오는 중입니다…","Loading your data…")}</div>` : this._content(p)}</section>
    <footer class="footer-note"><span>HealthLink Studio · v0.3.3</span><span>${this._t("의료 진단이 아닌 개인 웰니스·자동화 컨텍스트입니다.","Personal wellness and automation context, not medical diagnosis.")}</span></footer>
  </main>`;
  this._bind();
  this._updateLogo();
};

proto._metric = function (label,value,detail="") {
  return `<article class="card metric"><div class="label">${this._esc(label)}</div><div class="value">${value}</div>${detail ? `<div class="note">${this._esc(detail)}</div>` : ""}</article>`;
};

proto._today = function (p) {
  const noData = !p.sample_count;
  const goals = p.goal_progress || {};
  const labels = {
    steps:this._t("걸음 수","Steps"), exercise_minutes:this._t("운동 시간","Exercise"),
    active_energy:this._t("활동 에너지","Active energy"), water_ml:this._t("물 기록","Recorded water"), sleep_minutes:this._t("수면","Sleep")
  };
  const units = {steps:this._t("걸음","steps"),exercise_minutes:this._t("분","min"),active_energy:"kcal",water_ml:"mL",sleep_minutes:this._t("분","min")};
  const focusMap = {none:this._t("특별히 확인할 항목이 없어요","Nothing needs attention"),steps:this._t("활동","Activity"),exercise_minutes:this._t("운동 시간","Exercise"),active_energy:this._t("활동 에너지","Active energy"),water_ml:this._t("물 기록","Recorded water"),sleep_minutes:this._t("수면","Sleep"),recovery_context:this._t("회복 신호","Recovery signal")};
  const contextMap = {not_configured:this._t("목표를 아직 설정하지 않았어요","No goals configured"),all_reached:this._t("설정한 목표를 모두 달성했어요","Configured goals reached"),in_progress:this._t("목표를 향해 진행 중이에요","Goals in progress"),waiting_for_data:this._t("데이터를 기다리고 있어요","Waiting for data")};
  const recoveryMap = {above_baseline:this._t("평소보다 좋아요","Above your usual range"),within_baseline:this._t("평소와 비슷해요","Within your usual range"),below_baseline:this._t("평소보다 낮아요","Below your usual range"),insufficient_data:this._t("데이터가 더 필요해요","More data needed")};
  const focus = focusMap[p.daily_focus] || p.daily_focus || this._t("데이터 확인 중","Checking data");
  const context = contextMap[p.daily_goal_context] || p.daily_goal_context || this._t("데이터 확인 중","Checking data");
  const recovery = recoveryMap[p.recovery_context] || this._recovery(p.recovery_context);
  const confidence = Number(p.data_confidence || 0);
  const recoveryConfidence = Number(p.recovery_confidence || 0);
  const stepChange = p.steps_vs_same_time_baseline;
  const stepGoal = goals.steps;
  const activityValue = stepGoal?.progress !== null && stepGoal?.progress !== undefined ? `${Math.round(stepGoal.progress)}%` : (stepChange !== null && stepChange !== undefined ? `${stepChange > 0 ? "+" : ""}${stepChange}%` : "—");
  const activityDetail = stepGoal?.target ? `${this._fmt(stepGoal.current)} / ${this._fmt(stepGoal.target)} ${units.steps}` : this._t("같은 시간대의 평소 기록과 비교합니다.","Compared with your usual same-time record.");
  const insight = confidence < 50
    ? {title:this._t("더 나은 분석을 위해 데이터를 수집하고 있어요","Collecting more data for better analysis"),copy:this._t("현재 연결된 건강 기록이 아직 적습니다. 며칠간 꾸준히 수집하면 개인 기준선과 인사이트가 더 정확해집니다.","There is not enough history yet. A few more days of regular data will improve personal baselines and insights.")}
    : p.recovery_context === "below_baseline"
      ? {title:this._t("회복 신호가 평소보다 낮게 나타났어요","Recovery signal is below your usual range"),copy:this._t("수면·심박·활동의 개인 기준선을 함께 확인하세요. HealthLink는 의료 판단을 하지 않습니다.","Review your personal sleep, heart and activity baselines together. HealthLink does not make medical conclusions.")}
      : {title:this._t("현재 데이터에서 큰 변화는 보이지 않아요","No major change stands out in current data"),copy:this._t("오늘의 목표와 같은 시간대 활동 변화를 함께 확인하면 일상 패턴을 이해하는 데 도움이 됩니다.","Review goals and same-time activity changes together to understand your daily pattern.")};
  const goalItems = Object.entries(goals).map(([key,item]) => {
    const pct = item.progress === null || item.progress === undefined ? null : Math.max(0,Math.round(item.progress));
    const capped = pct === null ? 0 : Math.min(100,pct);
    const current = item.current === null || item.current === undefined ? "—" : item.current;
    const target = item.target === null || item.target === undefined ? "—" : item.target;
    return `<div class="goal-item"><div class="goal-icon">${key === "steps" ? "↗" : key === "sleep_minutes" ? "◐" : key === "water_ml" ? "◌" : "●"}</div><div><div class="goal-title">${this._esc(labels[key] || key)}</div><div class="goal-meta">${this._esc(current)} / ${this._esc(target)} ${this._esc(units[key] || "")}</div></div><div class="goal-value">${pct === null ? "—" : `${pct}%`}</div><div class="goal-progress-wrap"><div class="progress-track"><div class="progress-fill ${pct !== null && pct >= 100 ? "success" : ""}" style="width:${capped}%"></div></div></div></div>`;
  }).join("");
  return `
    ${p.companion_needs_selection ? `<div class="info-banner"><div class="info-icon">!</div><div><strong>${this._t("내 Apple 기기를 선택해 주세요","Choose your Apple device")}</strong><div class="note">${this._t("여러 사람의 건강 데이터가 섞이지 않도록, 이 프로필에서 사용할 iPhone/iPad를 한 번 선택해야 합니다.","Choose the iPhone/iPad for this profile so household health data is never mixed.")}</div></div><a class="button-link secondary banner-action" href="/config/integrations/integration/health_link">${this._t("설정 열기","Open settings")} →</a></div>` : ""}
    ${noData ? `<div class="info-banner"><div class="info-icon">i</div><div><strong>${this._t("Apple 건강 데이터를 연결하면 분석이 시작됩니다","Connect Apple Health data to start analysis")}</strong><div class="note">${this._t("공식 Home Assistant 앱 → 설정 → 센서 → Apple 건강 센서(Labs)에서 원하는 항목을 켜세요.","In the official Home Assistant app, enable the Apple Health Sensors (Labs) you want to share.")}</div></div><button id="refresh" class="secondary banner-action">${this._t("다시 확인","Check again")}</button></div>` : ""}
    <div class="section-head"><div><h2>${this._t("오늘 요약","Today at a glance")}</h2><div class="section-sub">${this._t("지금 가장 중요한 건강 컨텍스트를 한눈에 확인하세요.","See the most useful health context first.")}</div></div></div>
    <div class="summary-grid">
      <article class="summary-card"><div><div class="eyebrow"><span class="status-dot success"></span>${this._t("오늘의 상태","Today status")}</div><div class="status-value">${this._esc(focus)}</div></div><div class="detail">${this._esc(context)}</div></article>
      <article class="summary-card"><div><div class="eyebrow"><span class="status-dot success"></span>${this._t("활동","Activity")}</div><div class="status-value">${this._esc(activityValue)}</div></div><div><div class="detail">${this._esc(activityDetail)}</div>${stepGoal?.progress !== null && stepGoal?.progress !== undefined ? `<div class="progress-track"><div class="progress-fill success" style="width:${Math.min(100,Math.max(0,stepGoal.progress))}%"></div></div>` : ""}</div></article>
      <article class="summary-card"><div><div class="eyebrow"><span class="status-dot ${recoveryConfidence >= 60 ? "success" : "muted"}"></span>${this._t("회복 신호","Recovery signal")}</div><div class="status-value">${this._esc(recovery)}</div></div><div class="detail">${this._t("개인 기준선과 비교한 웰니스 컨텍스트", "Wellness context compared with your own baseline")} · ${this._fmt(p.recovery_confidence,"%")}</div></article>
      <article class="summary-card"><div><div class="eyebrow"><span class="status-dot ${confidence >= 70 ? "success" : confidence >= 40 ? "warning" : "muted"}"></span>${this._t("분석 준비도","Data readiness")}</div><div class="status-value">${this._fmt(p.data_confidence,"%")}</div></div><div><div class="detail">${confidence >= 70 ? this._t("분석에 사용할 데이터가 충분해지고 있어요.","Enough data is building up for analysis.") : this._t("더 정확한 분석을 위해 데이터가 더 필요해요.","More data is needed for stronger analysis.")}</div><div class="progress-track"><div class="progress-fill ${confidence >= 70 ? "success" : confidence >= 40 ? "warning" : ""}" style="width:${Math.min(100,Math.max(0,confidence))}%"></div></div></div></article>
    </div>
    <div class="dashboard-grid">
      <section class="panel-card"><div class="section-head" style="margin-top:0"><div><h2>${this._t("내 목표","My goals")}</h2><div class="section-sub">${this._t("직접 설정한 생활 목표의 진행 상황입니다.","Progress toward the lifestyle goals you set.")}</div></div><a class="section-action" href="/config/integrations/integration/health_link">${this._t("목표 관리","Manage goals")} →</a></div>${goalItems ? `<div class="goal-list">${goalItems}</div>` : `<div class="empty" style="padding:26px 8px">${this._t("아직 설정한 목표가 없습니다.","No goals configured yet.")}<br><a class="section-action" href="/config/integrations/integration/health_link">${this._t("목표 설정하기","Set a goal")} →</a></div>`}</section>
      <section class="panel-card"><div class="section-head" style="margin-top:0"><div><h2>${this._t("데이터 상태","Data status")}</h2><div class="section-sub">${this._t("연결과 수집 상태를 빠르게 점검합니다.","Quickly check connection and collection health.")}</div></div><button class="secondary" data-jump-tab="connect">${this._t("연결 확인","Check connection")}</button></div><div class="status-list"><div class="status-item"><div><div class="status-name">${this._t("최근 동기화","Last sync")}</div></div><div></div><div class="status-value-sm">${p.last_sync ? new Date(p.last_sync).toLocaleString() : "—"}</div></div><div class="status-item"><div><div class="status-name">${this._t("연결된 건강 항목","Connected health types")}</div></div><div></div><div class="status-value-sm">${p.type_count || 0}${this._t("개"," types")}</div></div><div class="status-item"><div><div class="status-name">${this._t("누적 저장 기록","Stored records")}</div></div><div></div><div class="status-value-sm">${p.sample_count || 0}${this._t("개"," records")}</div></div></div></section>
      <section class="panel-card"><div class="section-head" style="margin-top:0"><div><h2>${this._t("최근 인사이트","Recent insight")}</h2><div class="section-sub">${this._t("숫자보다 의미를 먼저 보여드립니다.","Meaning first, not just numbers.")}</div></div><button class="secondary" data-jump-tab="insights">${this._t("모두 보기","View all")} →</button></div><div class="insight-card"><div class="insight-title">${this._esc(insight.title)}</div><div class="insight-copy">${this._esc(insight.copy)}</div></div></section>
      <section class="panel-card"><div class="section-head" style="margin-top:0"><div><h2>${this._t("빠른 작업","Quick actions")}</h2><div class="section-sub">${this._t("자주 쓰는 기능으로 바로 이동합니다.","Jump directly to common tasks.")}</div></div></div><div class="quick-list"><a class="quick-item" href="#" data-jump-tab="explorer"><span class="quick-icon">↗</span><span><span class="quick-title">${this._t("건강 데이터 보기","View health data")}</span><span class="quick-desc">${this._t("Apple 건강에서 수집된 항목을 확인합니다.","Review collected Apple Health metrics.")}</span></span><span class="quick-arrow">›</span></a><a class="quick-item" href="#" data-jump-tab="composer"><span class="quick-icon">＋</span><span><span class="quick-title">${this._t("새 센서 만들기","Create a sensor")}</span><span class="quick-desc">${this._t("건강·집 데이터를 조합해 HA 센서를 만듭니다.","Combine health and home data into an HA sensor.")}</span></span><span class="quick-arrow">›</span></a><a class="quick-item" href="#" data-jump-tab="connect"><span class="quick-icon">●</span><span><span class="quick-title">${this._t("연결 상태 확인","Check connection")}</span><span class="quick-desc">${this._t("Apple 기기와 건강 센서 연결을 점검합니다.","Check Apple device and health sensor connection.")}</span></span><span class="quick-arrow">›</span></a><a class="quick-item" href="/config/integrations/integration/health_link"><span class="quick-icon">ECG</span><span><span class="quick-title">${this._t("ECG·건강 원본 가져오기","Import ECG / Health export")}</span><span class="quick-desc">${this._t("네이티브 설정에서 ECG만 빠르게 가져올 수 있습니다.","Use native settings for the fast ECG-only import.")}</span></span><span class="quick-arrow">›</span></a></div></section>
    </div>`;
};

proto._connect = function (p) {
  const companionState = p.companion_needs_selection ? this._t("Apple 기기 선택 필요","Choose Apple device") : p.companion_active ? this._t(`연결됨 · ${p.companion_sensor_count || 0}개 센서`,`Connected · ${p.companion_sensor_count || 0} sensors`) : this._t("연결 대기","Waiting for connection");
  return `<div class="section-head"><div><h2>${this._t("연결 상태","Connection")}</h2><div class="section-sub">${this._t("공식 Home Assistant Companion 앱과 HealthLink의 연결 상태를 확인합니다.","Check the connection between the official Companion app and HealthLink.")}</div></div><a class="button-link secondary" href="/config/integrations/integration/health_link">${this._t("네이티브 설정 열기","Open native settings")}</a></div>
    <div class="info-banner"><div class="info-icon">i</div><div><strong>${this._t("별도 HealthLink iOS 앱은 필요하지 않습니다","No separate HealthLink iOS app is required")}</strong><div class="note">${this._t("같은 Home Assistant 서버에 등록된 iPhone/iPad의 공식 Companion 앱이 Apple 건강 센서(Labs)를 전달하고 HealthLink가 이를 분석합니다.","The official Companion app on an iPhone/iPad registered to this Home Assistant sends Apple Health Sensors (Labs), which HealthLink analyzes.")}</div></div></div>
    <div class="summary-grid">${this._metric("Home Assistant Companion",this._esc(companionState))}${this._metric(this._t("연결된 Apple 기기","Connected Apple devices"),p.companion_device_count || 0)}${this._metric(this._t("건강 센서","Health sensors"),p.companion_sensor_count || 0)}${this._metric(this._t("소스 모드","Source mode"),this._esc(p.source_mode || "auto"))}</div>
    ${p.companion_needs_selection ? `<div class="card setup" style="margin-top:14px"><h3>${this._t("이 프로필에서 사용할 Apple 기기를 선택하세요","Choose the Apple device for this profile")}</h3><div class="note">${this._t("설정 → 기기 및 서비스 → HealthLink에서 이 사람의 iPhone/iPad만 연결하세요. Apple Watch는 직접 선택하지 않습니다.","In Settings → Devices & services → HealthLink, connect only this person's iPhone/iPad. Apple Watch is not selected directly.")}</div></div>` : ""}`;
};

proto._bind = function () {
  baseBind.call(this);
  this.shadowRoot.querySelectorAll("[data-jump-tab]").forEach(el => el.addEventListener("click", event => {
    event.preventDefault();
    this._tab = el.dataset.jumpTab;
    this._render();
  }));
};
