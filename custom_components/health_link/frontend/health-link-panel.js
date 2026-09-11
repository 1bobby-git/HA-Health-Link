class HealthLinkPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._profiles = [];
    this._catalog = [];
    this._composers = [];
    this._tab = "today";
    this._entryId = null;
    this._loading = false;
    this._error = null;
  }

  set hass(value) {
    const first = !this._hass;
    this._hass = value;
    if (first) this._load();
  }

  set panel(value) { this._panel = value; }

  connectedCallback() {
    this._render();
  }

  get _ko() { return (this._hass?.language || "").toLowerCase().startsWith("ko"); }
  _t(ko, en) { return this._ko ? ko : en; }

  async _callWS(payload) {
    if (!this._hass) throw new Error("Home Assistant is not ready");
    return this._hass.callWS(payload);
  }

  async _load() {
    if (!this._hass || this._loading) return;
    this._loading = true; this._error = null; this._render();
    try {
      this._profiles = await this._callWS({ type: "health_link/status" });
      if (!this._entryId && this._profiles.length) this._entryId = this._profiles[0].config_entry_id;
      if (this._entryId) await this._loadProfileData();
    } catch (err) {
      this._error = String(err?.message || err);
    } finally {
      this._loading = false; this._render();
    }
  }

  async _loadProfileData() {
    const id = this._entryId;
    [this._catalog, this._composers] = await Promise.all([
      this._callWS({ type: "health_link/catalog/list", config_entry_id: id }),
      this._callWS({ type: "health_link/composer/list", config_entry_id: id }),
    ]);
  }

  _profile() { return this._profiles.find(p => p.config_entry_id === this._entryId) || this._profiles[0]; }
  _fmt(value, suffix = "") { return value === null || value === undefined ? "—" : `${value}${suffix}`; }
  _esc(value) { return String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c])); }

  _styles() { return `
    :host { display:block; min-height:100%; color:var(--primary-text-color); background:var(--primary-background-color); font-family:var(--paper-font-body1_-_font-family, sans-serif); }
    * { box-sizing:border-box; }
    .wrap { max-width:1200px; margin:0 auto; padding:24px 20px 56px; }
    header { display:flex; gap:16px; align-items:center; justify-content:space-between; flex-wrap:wrap; margin-bottom:18px; }
    h1 { font-size:28px; margin:0; display:flex; align-items:center; gap:10px; }
    h2 { font-size:20px; margin:24px 0 12px; }
    h3 { margin:0 0 8px; font-size:16px; }
    .sub { color:var(--secondary-text-color); font-size:14px; margin-top:5px; }
    select,input,button { font:inherit; }
    select,input { min-height:42px; border:1px solid var(--divider-color); border-radius:10px; padding:8px 10px; background:var(--card-background-color); color:var(--primary-text-color); }
    button { min-height:40px; border:0; border-radius:10px; padding:0 14px; cursor:pointer; background:var(--primary-color); color:var(--text-primary-color, #fff); font-weight:600; }
    button.secondary { color:var(--primary-text-color); background:var(--secondary-background-color); border:1px solid var(--divider-color); }
    button.danger { background:var(--error-color); color:#fff; }
    button:focus-visible, select:focus-visible, input:focus-visible, [role=tab]:focus-visible { outline:3px solid var(--primary-color); outline-offset:2px; }
    .tabs { display:flex; gap:6px; overflow:auto; padding:4px 0 14px; border-bottom:1px solid var(--divider-color); }
    [role=tab] { background:transparent; color:var(--secondary-text-color); white-space:nowrap; }
    [role=tab][aria-selected=true] { background:var(--primary-color); color:#fff; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; }
    .card { border-radius:16px; padding:18px; background:var(--card-background-color); box-shadow:var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,.08)); border:1px solid var(--divider-color); }
    .metric .value { font-size:28px; font-weight:700; line-height:1.2; margin-top:8px; }
    .metric .label { color:var(--secondary-text-color); font-size:13px; }
    .ok { color:var(--success-color, #2e7d32); } .warn { color:var(--warning-color,#f9a825); } .bad { color:var(--error-color); }
    .setup { border:1px solid var(--primary-color); background:color-mix(in srgb,var(--primary-color) 8%,var(--card-background-color)); }
    .steps { margin:12px 0 0; padding-left:22px; line-height:1.8; }
    .toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:14px 0; }
    .search { flex:1; min-width:220px; }
    .tablewrap { overflow:auto; border:1px solid var(--divider-color); border-radius:14px; background:var(--card-background-color); }
    table { width:100%; border-collapse:collapse; min-width:720px; }
    th,td { padding:12px; border-bottom:1px solid var(--divider-color); text-align:left; vertical-align:middle; }
    th { font-size:12px; color:var(--secondary-text-color); position:sticky; top:0; background:var(--card-background-color); }
    .tag { display:inline-flex; border-radius:999px; padding:3px 8px; font-size:12px; background:var(--secondary-background-color); }
    .switch { min-width:72px; }
    .builder { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
    .field { display:flex; flex-direction:column; gap:6px; }
    .field.full { grid-column:1/-1; }
    label { font-size:13px; font-weight:600; }
    .note { color:var(--secondary-text-color); font-size:13px; line-height:1.5; }
    .composer-list { display:grid; gap:10px; margin-top:14px; }
    .row { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px; border:1px solid var(--divider-color); border-radius:12px; }
    .pair { word-break:break-all; padding:12px; border-radius:10px; background:var(--secondary-background-color); font-family:monospace; font-size:12px; }
    .error { padding:12px; border-radius:10px; background:color-mix(in srgb,var(--error-color) 14%,transparent); color:var(--error-color); margin-bottom:12px; }
    .empty { text-align:center; padding:40px 18px; color:var(--secondary-text-color); }
    @media(max-width:700px){ .wrap{padding:16px 12px 40px}.builder{grid-template-columns:1fr}.field.full{grid-column:auto} h1{font-size:24px} }
    @media(prefers-reduced-motion:reduce){ *{scroll-behavior:auto!important;transition:none!important} }
  `; }

  _render() {
    if (!this.shadowRoot) return;
    const p = this._profile();
    const profiles = this._profiles.map(x => `<option value="${this._esc(x.config_entry_id)}" ${x.config_entry_id===this._entryId?'selected':''}>${this._esc(x.title)}</option>`).join("");
    this.shadowRoot.innerHTML = `<style>${this._styles()}</style><main class="wrap">
      <header><div><h1>❤ HealthLink</h1><div class="sub">${this._t('Apple 건강과 집을 가장 쉽게 연결합니다.','Connect Apple Health and your home, without the setup burden.')}</div></div>
      ${this._profiles.length>1?`<select id="profile" aria-label="${this._t('건강 프로필','Health profile')}">${profiles}</select>`:''}</header>
      ${this._error?`<div class="error" role="alert">${this._esc(this._error)}</div>`:''}
      <nav class="tabs" role="tablist" aria-label="HealthLink">
        ${this._tabButton('today',this._t('오늘','Today'))}
        ${this._tabButton('explorer',this._t('건강 데이터','Health data'))}
        ${this._tabButton('timeline',this._t('타임라인','Timeline'))}
        ${this._tabButton('composer',this._t('센서 만들기','Create sensor'))}
        ${this._tabButton('insights',this._t('인사이트','Insights'))}
        ${this._tabButton('connect',this._t('연결 상태','Connection'))}
      </nav>
      <section role="tabpanel">${this._loading?`<div class="empty">${this._t('불러오는 중…','Loading…')}</div>`:this._content(p)}</section>
    </main>`;
    this._bind();
  }

  _tabButton(id,label){ return `<button role="tab" data-tab="${id}" aria-selected="${this._tab===id}">${label}</button>`; }

  _content(p) {
    if (!p) return `<div class="empty">${this._t('설정 → 기기 및 서비스에서 HealthLink를 먼저 추가하세요.','Add HealthLink in Settings → Devices & services.')}</div>`;
    if (this._tab === 'today') return this._today(p);
    if (this._tab === 'explorer') return this._explorer();
    if (this._tab === 'timeline') return this._timeline();
    if (this._tab === 'composer') return this._composer();
    if (this._tab === 'insights') return this._insights();
    return this._connect(p);
  }

  _today(p) {
    const noData = !p.sample_count;
    return `${p.companion_needs_selection?`<div class="card setup"><h3>${this._t('내 iPhone을 한 번만 선택하세요','Choose your iPhone once')}</h3><div class="note">${this._t('여러 iPhone의 건강 데이터가 섞이지 않도록 자동 가져오기를 잠시 멈췄습니다. 설정 → 기기 및 서비스 → HealthLink → 구성에서 본인의 iPhone만 선택하면 됩니다.','HealthLink paused automatic import so health data from multiple iPhones can never be mixed. Go to Settings → Devices & services → HealthLink → Configure and choose your iPhone.')}</div></div>`:''}${noData?`<div class="card setup"><h3>${this._t('1분이면 준비됩니다','Ready in about a minute')}</h3>
      <div class="note">${this._t('별도 YAML이나 센서 ID 입력은 필요 없습니다. iPhone의 Home Assistant 앱에서 Apple 건강 센서만 켜면 HealthLink가 자동으로 찾습니다.','No YAML or entity IDs are required. Enable Apple Health sensors in the Home Assistant iPhone app and HealthLink will find them automatically.')}</div>
      <ol class="steps"><li>${this._t('iPhone에서 Home Assistant 앱 열기','Open Home Assistant on iPhone')}</li><li>${this._t('설정 → 센서 → Apple 건강 센서','Settings → Sensors → Apple Health Sensors')}</li><li>${this._t('원하는 Apple 건강 센서를 켜기. “모든 센서를 활성화하기”가 보이면 한 번에 켤 수 있습니다.','Enable the Apple Health sensors you want. If “Enable all Apple Health sensors” is available, you can turn them on at once.')}</li></ol>
      <div class="toolbar"><button id="refresh">${this._t('다시 확인','Check again')}</button></div></div>`:''}
      <h2>${this._t('오늘','Today')}</h2><div class="grid">
      ${this._metric(this._t('걸음','Steps'),this._fmt(p.steps_today,' steps'),'mdi:walk')}
      ${this._metric(this._t('수면','Sleep'),this._minutes(p.sleep_duration),'')}
      ${this._metric(this._t('깊은 수면','Deep sleep'),this._minutes(p.sleep_deep),'')}
      ${this._metric(this._t('수면 효율','Sleep efficiency'),this._fmt(p.sleep_efficiency,'%'),'')}
      ${this._metric(this._t('회복 컨텍스트','Recovery context'),this._recovery(p.recovery_context),'')}
      ${this._metric(this._t('데이터 신뢰도','Data confidence'),this._fmt(p.data_confidence,'%'),'')}
      </div>
      <h2>${this._t('현재 상태','Current status')}</h2><div class="card"><div class="row"><span>${this._t('최근 동기화','Last sync')}</span><strong>${p.last_sync?new Date(p.last_sync).toLocaleString(): '—'}</strong></div><div class="row"><span>${this._t('가져온 건강 항목','Health data types')}</span><strong>${p.type_count||0}</strong></div><div class="row"><span>${this._t('저장된 샘플','Stored samples')}</span><strong>${p.sample_count||0}</strong></div></div>`;
  }
  _metric(label,value){return `<article class="card metric"><div class="label">${label}</div><div class="value">${value}</div></article>`;}
  _minutes(v){ if(v===null||v===undefined)return '—'; const h=Math.floor(v/60),m=Math.round(v%60); return h?`${h}${this._t('시간','h')} ${m}${this._t('분','m')}`:`${m}${this._t('분','m')}`; }
  _recovery(v){ const map={above_baseline:this._t('평소보다 좋음','Above baseline'),within_baseline:this._t('평소 범위','Within baseline'),below_baseline:this._t('평소보다 낮음','Below baseline'),insufficient_data:this._t('데이터가 더 필요함','More data needed')}; return map[v]||'—'; }

  _explorer() {
    const rows=this._catalog.map((x,i)=>`<tr data-name="${this._esc((x.display_name||x.type_id).toLowerCase())}"><td><strong>${this._esc(x.display_name||x.type_id)}</strong><div class="note">${this._esc(x.type_id)}</div></td><td><span class="tag">${this._esc(x.domain||'other')}</span></td><td>${x.sample_count||0}</td><td>${x.last_sample?new Date(x.last_sample).toLocaleString():'—'}</td><td><button class="${x.exposed?'secondary':''} switch" data-expose="${i}">${x.exposed?this._t('숨기기','Hide'):this._t('센서 생성','Create')}</button></td></tr>`).join('');
    return `<h2>${this._t('건강 데이터 탐색기','Health data explorer')}</h2><div class="note">${this._t('실제로 iPhone에서 들어온 HealthKit 항목만 먼저 보여줍니다. 필요한 항목만 HA 센서로 만들기 때문에 Recorder가 불필요하게 커지지 않습니다.','Only data actually received from your iPhone appears first. Create HA entities only for metrics you need, protecting Recorder from unnecessary growth.')}</div><div class="toolbar"><input id="search" class="search" type="search" placeholder="${this._t('심박, 수면, HRV 검색','Search heart rate, sleep, HRV')}"/><button id="refresh" class="secondary">${this._t('새로고침','Refresh')}</button></div>${rows?`<div class="tablewrap"><table><thead><tr><th>${this._t('항목','Metric')}</th><th>${this._t('영역','Domain')}</th><th>${this._t('샘플','Samples')}</th><th>${this._t('최근 데이터','Last data')}</th><th>${this._t('HA 센서','HA entity')}</th></tr></thead><tbody id="catalogBody">${rows}</tbody></table></div>`:`<div class="empty">${this._t('아직 건강 데이터가 없습니다. 오늘 탭의 안내에 따라 Apple 건강 센서를 켜세요.','No health data yet. Follow the Apple Health setup on the Today tab.')}</div>`}`;
  }

  _numericEntityOptions() {
    return this._hass ? Object.entries(this._hass.states)
      .filter(([,s])=>Number.isFinite(Number(s.state)))
      .slice(0,2500)
      .map(([id])=>`<option value="${this._esc(id)}">${this._esc(id)}</option>`).join('') : '';
  }

  _healthMetricOptions() {
    return this._catalog.filter(x=>x.sample_count>0)
      .map(x=>`<option value="${this._esc(x.type_id)}">${this._esc(x.display_name||x.type_id)}</option>`).join('');
  }

  _timeline() {
    const metrics=this._healthMetricOptions(), entities=this._numericEntityOptions();
    return `<h2>${this._t('건강 + 집 타임라인','Health + home timeline')}</h2>
      <div class="card"><div class="note">${this._t('몸의 데이터와 집 센서의 변화를 같은 시간축으로 확인합니다. 데이터는 Home Assistant 안에서만 조회됩니다.','See body data and home sensor changes on one timeline. Queries remain inside Home Assistant.')}</div>
      <div class="builder" style="margin-top:16px"><div class="field"><label for="tlMetric">HealthKit</label><select id="tlMetric">${metrics}</select></div><div class="field"><label for="tlEntity">Home Assistant</label><select id="tlEntity"><option value="">${this._t('선택 안 함','None')}</option>${entities}</select></div><div class="field"><label for="tlHours">${this._t('기간','Window')}</label><select id="tlHours"><option value="24">24${this._t('시간','h')}</option><option value="168">7${this._t('일',' days')}</option><option value="720">30${this._t('일',' days')}</option></select></div><div class="field" style="justify-content:end"><button id="loadTimeline">${this._t('타임라인 보기','Show timeline')}</button></div></div></div><div id="timelineResult" style="margin-top:14px"></div>`;
  }

  _insights() {
    const metrics=this._healthMetricOptions(), entities=this._numericEntityOptions();
    return `<h2>${this._t('내 건강과 집의 관계 찾기','Find relationships between health and home')}</h2><div class="card"><div class="note">${this._t('예: 깊은 수면과 침실 CO₂, HRV와 실내 온도. 결과는 관측된 연관성일 뿐 원인이나 의료 판단을 의미하지 않습니다.','Example: deep sleep vs bedroom CO₂, or HRV vs room temperature. Results are observed associations, not causes or medical conclusions.')}</div><div class="builder" style="margin-top:16px"><div class="field"><label for="inMetric">${this._t('건강 결과','Health outcome')}</label><select id="inMetric">${metrics}</select></div><div class="field"><label for="inEntity">${this._t('집 환경 센서','Home/environment sensor')}</label><select id="inEntity">${entities}</select></div><div class="field"><label for="inDays">${this._t('분석 기간','Analysis window')}</label><select id="inDays"><option value="30">30${this._t('일',' days')}</option><option value="60" selected>60${this._t('일',' days')}</option><option value="90">90${this._t('일',' days')}</option><option value="180">180${this._t('일',' days')}</option></select></div><div class="field"><label for="inGoal">${this._t('좋은 결과의 방향','Preferred outcome direction')}</label><select id="inGoal"><option value="high">${this._t('높을수록 좋음','Higher is better')}</option><option value="low">${this._t('낮을수록 좋음','Lower is better')}</option></select></div><div class="field full"><button id="runInsight">${this._t('내 데이터 분석','Analyze my data')}</button></div></div></div><div id="insightResult" style="margin-top:14px"></div>`;
  }

  _composer() {
    const metrics=this._catalog.filter(x=>x.sample_count>0).map(x=>`<option value="${this._esc(x.type_id)}">${this._esc(x.display_name||x.type_id)}</option>`).join('');
    const numericStates=this._numericEntityOptions();
    const list=this._composers.map(c=>`<div class="row"><div><strong>${this._esc(c.name)}</strong><div class="note">sensor · ${this._esc(c.id)} · v${c.version}</div></div><button class="danger" data-delete-composer="${this._esc(c.id)}">${this._t('삭제','Delete')}</button></div>`).join('');
    return `<h2>${this._t('건강 센서 만들기','Create a health sensor')}</h2><div class="card"><div class="note">${this._t('코드를 쓰지 않고 HealthKit 데이터와 집의 센서를 조합합니다. 저장하면 Home Assistant 센서가 자동으로 생성됩니다.','Combine HealthKit and home data without code. Saving creates a Home Assistant sensor automatically.')}</div>
      <div class="builder" style="margin-top:16px">
        <div class="field"><label for="cName">${this._t('센서 이름','Sensor name')}</label><input id="cName" value="${this._t('나의 건강 컨텍스트','My health context')}"/></div>
        <div class="field"><label for="cId">ID</label><input id="cId" value="my_health_context" pattern="[a-z0-9_-]+"/></div>
        <div class="field"><label for="inputA">A · HealthKit</label><select id="inputA">${metrics}</select></div>
        <div class="field"><label for="inputBKind">B · ${this._t('조합할 데이터','Data to combine')}</label><select id="inputBKind"><option value="ha">Home Assistant</option><option value="healthkit">HealthKit</option><option value="none">${this._t('사용 안 함','None')}</option></select></div>
        <div class="field full" id="haField"><label for="inputBHa">B · Home Assistant</label><select id="inputBHa">${numericStates}</select></div>
        <div class="field full" id="hkField" hidden><label for="inputBHk">B · HealthKit</label><select id="inputBHk">${metrics}</select></div>
        <div class="field"><label for="op">${this._t('계산 방식','Calculation')}</label><select id="op"><option value="avg">${this._t('평균','Average')}</option><option value="add">A + B</option><option value="sub">A − B</option><option value="ratio">A ÷ B</option><option value="mul">A × B</option><option value="a">A ${this._t('그대로','only')}</option></select></div>
        <div class="field"><label for="unit">${this._t('단위 (선택)','Unit (optional)')}</label><input id="unit" placeholder="%, score, …"/></div>
        <div class="field full"><button id="saveComposer">${this._t('센서 만들기','Create sensor')}</button></div>
      </div></div><h2>${this._t('내가 만든 센서','My sensors')}</h2><div class="composer-list">${list||`<div class="empty">${this._t('아직 만든 센서가 없습니다.','No custom health sensors yet.')}</div>`}</div>`;
  }

  _connect(p) {
    const companionState = p.companion_needs_selection ? this._t('iPhone 선택 필요','Choose iPhone') : p.companion_active ? this._t(`자동 연결 · ${p.companion_sensor_count||0}개 센서`,`Auto connected · ${p.companion_sensor_count||0} sensors`) : this._t('사용 안 함','Not active');
    let guide='';
    if(p.setup_state==='enable_health_sensors') guide=`<div class="card setup" style="margin-top:12px"><h3>${this._t('추가 앱 설치 없이 시작할 수 있습니다','Start without installing another app')}</h3><div class="note">${this._t('iPhone의 공식 Home Assistant 앱 → 설정 → 센서 → Apple 건강 센서에서 원하는 항목을 켜세요. HealthLink가 새 센서를 자동으로 감지하므로 HA 재시작, YAML, Webhook 입력은 필요 없습니다.','On iPhone, open the official Home Assistant app → Settings → Sensors → Apple Health Sensors and enable the items you want. HealthLink discovers new sensors automatically; no HA restart, YAML, or webhook entry is required.')}</div></div>`;
    if(p.setup_state==='choose_iphone') guide=`<div class="card setup" style="margin-top:12px"><h3>${this._t('내 iPhone만 선택해 주세요','Choose your iPhone')}</h3><div class="note">${this._t('가족의 건강 데이터가 섞이지 않도록 여러 iPhone이 있을 때만 한 번 선택이 필요합니다. 설정 → 기기 및 서비스 → HealthLink → 구성에서 선택할 수 있습니다.','A one-time choice is required only when multiple iPhones exist, so household health data is never mixed. Choose it in Settings → Devices & services → HealthLink → Configure.')}</div></div>`;
    return `<h2>${this._t('연결 상태','Connection')}</h2><div class="card setup"><h3>${this._t('기본 모드: 별도 HealthLink iOS 앱 불필요','Standard mode: no separate HealthLink iOS app')}</h3><div class="note">${this._t('HealthLink 본체는 Home Assistant에 설치되는 HACS 통합입니다. 건강 데이터는 이미 설치한 공식 Home Assistant iPhone 앱이 Apple Health/HealthKit에서 읽어 HA 센서로 전달하고, HealthLink가 이를 자동 수집·조합·분석합니다.','HealthLink itself is a HACS integration running in Home Assistant. The official Home Assistant iPhone app reads Apple Health/HealthKit and publishes HA sensors; HealthLink automatically collects, combines, and analyzes them.')}</div></div>${guide}<div class="grid" style="margin-top:12px">${this._metric('Home Assistant Companion',companionState)}${this._metric('HealthLink Full Transport',p.bridge_ready?this._t('서버 수신 준비됨','Server endpoint ready'):this._t('사용 불가','Unavailable'))}${this._metric(this._t('소스','Source mode'),this._esc(p.source_mode||'auto'))}</div>
      <h2>${this._t('전체 HealthKit 확장','Full HealthKit extension')}</h2><div class="card"><h3>${this._t('고급 기능 — 선택 사항','Advanced — optional')}</h3><div class="note">${this._t('ECG 원본, 세부 Workout/Route, 임상/FHIR처럼 공식 Companion 앱이 아직 전달하지 않는 HealthKit 객체까지 필요할 때만 추가 전송 계층이 필요합니다. 최우선 방향은 별도 앱을 강제하지 않고 공식 Home Assistant iOS 앱에 전체 HealthKit 전송 기능을 upstream 제안하는 것입니다. 독립 HealthLink iOS Bridge는 upstream으로 해결할 수 없을 때의 대체 경로입니다.','An additional transport layer is needed only for HealthKit objects the official Companion app does not yet deliver, such as raw ECG, richer Workout/Route, or clinical/FHIR data. The preferred direction is to upstream full HealthKit transport into the official Home Assistant iOS app so users are not forced to install another app. A standalone HealthLink iOS Bridge is a fallback only if upstream coverage cannot provide it.')}</div><div class="toolbar"><button id="pairInfo" class="secondary">${this._t('고급 전송 연결 정보 보기','Show advanced transport pairing info')}</button></div><div id="pairResult"></div></div>`;
  }

  _bind() {
    this.shadowRoot.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>{this._tab=b.dataset.tab;this._render();}));
    this.shadowRoot.getElementById('profile')?.addEventListener('change',async e=>{this._entryId=e.target.value;this._loading=true;this._render();try{await this._loadProfileData();}finally{this._loading=false;this._render();}});
    this.shadowRoot.querySelectorAll('#refresh').forEach(b=>b.addEventListener('click',()=>this._load()));
    const search=this.shadowRoot.getElementById('search'); if(search) search.addEventListener('input',()=>{const q=search.value.toLowerCase();this.shadowRoot.querySelectorAll('#catalogBody tr').forEach(r=>r.hidden=!r.dataset.name.includes(q));});
    this.shadowRoot.querySelectorAll('[data-expose]').forEach(b=>b.addEventListener('click',async()=>{const item=this._catalog[Number(b.dataset.expose)];b.disabled=true;try{await this._callWS({type:'health_link/catalog/expose',config_entry_id:this._entryId,type_id:item.type_id,exposed:!Boolean(item.exposed)});item.exposed=item.exposed?0:1;this._render();}catch(e){this._error=String(e.message||e);this._render();}}));
    const kind=this.shadowRoot.getElementById('inputBKind'); if(kind) kind.addEventListener('change',()=>{this.shadowRoot.getElementById('haField').hidden=kind.value!=='ha';this.shadowRoot.getElementById('hkField').hidden=kind.value!=='healthkit';});
    this.shadowRoot.getElementById('loadTimeline')?.addEventListener('click',()=>this._loadTimeline());
    this.shadowRoot.getElementById('runInsight')?.addEventListener('click',()=>this._runInsight());
    this.shadowRoot.getElementById('saveComposer')?.addEventListener('click',()=>this._saveComposer());
    this.shadowRoot.querySelectorAll('[data-delete-composer]').forEach(b=>b.addEventListener('click',async()=>{if(!confirm(this._t('이 센서를 삭제할까요?','Delete this sensor?')))return;await this._callWS({type:'health_link/composer/delete',config_entry_id:this._entryId,definition_id:b.dataset.deleteComposer});await this._load();}));
    this.shadowRoot.getElementById('pairInfo')?.addEventListener('click',()=>this._showPairing());
  }

  async _loadTimeline(){
    const metric=this.shadowRoot.getElementById('tlMetric')?.value, entity=this.shadowRoot.getElementById('tlEntity')?.value, hours=Number(this.shadowRoot.getElementById('tlHours')?.value||24), target=this.shadowRoot.getElementById('timelineResult');
    if(!metric||!target)return; target.innerHTML=`<div class="empty">${this._t('불러오는 중…','Loading…')}</div>`;
    try{const data=await this._callWS({type:'health_link/timeline/query',config_entry_id:this._entryId,type_id:metric,entity_ids:entity?[entity]:[],hours});const events=(data.events||[]).slice(-300).reverse();target.innerHTML=events.length?`<div class="tablewrap"><table><thead><tr><th>${this._t('시간','Time')}</th><th>${this._t('출처','Source')}</th><th>${this._t('항목','Item')}</th><th>${this._t('값','Value')}</th></tr></thead><tbody>${events.map(e=>`<tr><td>${this._esc(new Date(e.time).toLocaleString())}</td><td><span class="tag">${e.source==='healthkit'?'HealthKit':'Home'}</span></td><td>${this._esc(e.id)}</td><td>${this._esc(e.value)} ${this._esc(e.unit||'')}</td></tr>`).join('')}</tbody></table></div>`:`<div class="empty">${this._t('선택한 기간에 데이터가 없습니다.','No data in the selected window.')}</div>`;}catch(e){target.innerHTML=`<div class="error">${this._esc(e.message||e)}</div>`;}
  }

  async _runInsight(){
    const metric=this.shadowRoot.getElementById('inMetric')?.value, entity=this.shadowRoot.getElementById('inEntity')?.value, days=Number(this.shadowRoot.getElementById('inDays')?.value||60), goal=this.shadowRoot.getElementById('inGoal')?.value||'high', target=this.shadowRoot.getElementById('insightResult');
    if(!metric||!entity||!target)return; target.innerHTML=`<div class="empty">${this._t('분석 중…','Analyzing…')}</div>`;
    try{const [corr,opt]=await Promise.all([this._callWS({type:'health_link/insights/correlation',config_entry_id:this._entryId,type_id:metric,entity_id:entity,days}),this._callWS({type:'health_link/optimizer/observe',config_entry_id:this._entryId,outcome_type_id:metric,environment_entity_id:entity,days,goal})]);const range=opt.preferred_observed_range;target.innerHTML=`<div class="grid">${this._metric(this._t('비교 가능한 샘플','Matched samples'),corr.pairs)}${this._metric(this._t('상관계수','Correlation'),corr.correlation===null?'—':corr.correlation)}${this._metric(this._t('연관 강도','Association strength'),this._esc(corr.strength))}${this._metric(this._t('관측상 유리한 환경 범위','Observed preferred range'),range?`${this._esc(range.low)} ~ ${this._esc(range.high)}`:'—')}</div><div class="card" style="margin-top:12px"><div class="note">${this._t('이 결과는 사용자의 과거 데이터에서 함께 움직인 경향을 보여줄 뿐입니다. 원인·질병·치료 효과를 의미하지 않으며 자동 제어에 단독으로 사용하지 않습니다.','This result only shows patterns that moved together in your history. It does not establish cause, disease, or treatment effect and is not used alone for automatic control.')}</div></div>`;}catch(e){target.innerHTML=`<div class="error">${this._esc(e.message||e)}</div>`;}
  }

  async _saveComposer(){
    const $=id=>this.shadowRoot.getElementById(id);
    const name=$('cName').value.trim(), id=$('cId').value.trim().toLowerCase().replace(/\s+/g,'_');
    const kind=$('inputBKind').value; const inputs={a:{source:'healthkit',type_id:$('inputA').value}};
    if(kind==='ha')inputs.b={source:'ha',entity_id:$('inputBHa').value};
    if(kind==='healthkit')inputs.b={source:'healthkit',type_id:$('inputBHk').value};
    const formulas={avg:'(a+b)/2',add:'a+b',sub:'a-b',ratio:'ratio(a,b)',mul:'a*b',a:'a'};
    let op=$('op').value; if(kind==='none')op='a';
    const definition={formula:formulas[op],inputs,unit:$('unit').value.trim()||null,icon:'mdi:heart-plus'};
    try{const check=await this._callWS({type:'health_link/composer/validate',definition});if(!check.valid)throw new Error(check.error);await this._callWS({type:'health_link/composer/save',config_entry_id:this._entryId,definition_id:id,name,definition});await this._load();this._tab='composer';this._render();}catch(e){this._error=String(e.message||e);this._render();}
  }

  async _showPairing(){
    const target=this.shadowRoot.getElementById('pairResult'); if(!target)return; target.textContent=this._t('불러오는 중…','Loading…');
    try{const d=await this._callWS({type:'health_link/pairing/info',config_entry_id:this._entryId});target.innerHTML=`<div class="note">${this._esc(d.warning)}</div><p class="note">Webhook</p><div class="pair">${this._esc(d.webhook_path)}</div><p class="note">Profile ID</p><div class="pair">${this._esc(d.profile_id)}</div><p class="note">Secret</p><div class="pair">${this._esc(d.bridge_secret)}</div>`;}catch(e){target.textContent=String(e.message||e);}
  }
}
customElements.define('health-link-panel', HealthLinkPanel);
