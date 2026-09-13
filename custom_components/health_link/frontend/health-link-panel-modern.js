/** HealthLink Studio — presentation-only redesign, design system 1.0.0.
 * No external runtime dependencies. Existing administrator WebSocket APIs only.
 */
import { TABS, STYLES, esc, numeric, headerView, bodyView, editorView, errorView, resultView } from './health-link-studio-view.js?v=20260913.1';

class HealthLinkPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'});
    this._hass = null; this._profiles = []; this._catalog = []; this._composers = [];
    this._entryId = null; this._tab = 'today'; this._analysis = 'timeline';
    this._loading = false; this._loaded = false; this._errors = {}; this._checkedAt = null;
    this._fields = {}; this._results = {}; this._mutations = new Map(); this._notice = '';
    this._requestId = 0; this._queryGeneration = 0; this._editor = null;
    this._active = false; this._refreshingProfiles = false; this._logoFailed = false;
    this._logoUrl = new URL('./brand/logo.png', import.meta.url).href;
    this._onFocus = () => { if (document.visibilityState !== 'hidden') this._refreshProfiles(); };
    this._beforeUnload = event => {
      if (this._editor?.dirty || this._editor?.busy) { event.preventDefault(); event.returnValue = ''; }
    };
  }

  set hass(value) {
    const first = !this._hass, language = this._hass?.language, previousAdmin = this._hass?.user?.is_admin;
    this._hass = value;
    if (!this._active) return;
    this._theme();
    if (value?.user?.is_admin === false) {
      this._requestId++; this._profiles = []; this._resetProfile(null);
      this._closeEditor(true); this._render(); return;
    }
    if (first || previousAdmin === false) this._load();
    else if (language !== value?.language) this._render();
  }
  set panel(value) { this._panel = value; }
  get _ko() { return (this._hass?.language || navigator.language || 'en').toLowerCase().startsWith('ko'); }
  _t(ko, en) { return this._ko ? ko : en; }
  _profile() { return this._profiles.find(p => p.config_entry_id === this._entryId); }
  _number(value) { const n = numeric(value); return n === null ? '—' : new Intl.NumberFormat(this._ko ? 'ko-KR' : 'en-US', {maximumFractionDigits:2}).format(n); }
  _date(value) {
    if (!value) return '—';
    const date = new Date(value); if (!Number.isFinite(date.getTime())) return '—';
    const options = {year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'};
    try { return new Intl.DateTimeFormat(this._ko ? 'ko-KR' : 'en-US', {...options, timeZone:this._hass?.config?.time_zone}).format(date); }
    catch { return date.toLocaleString(this._ko ? 'ko-KR' : 'en-US'); }
  }
  _callWS(payload) {
    if (!this._hass || this._hass.user?.is_admin === false) return Promise.reject({code:'unauthorized', message:'Administrator access required'});
    return this._hass.callWS(payload);
  }
  _theme() {
    const root = this.shadowRoot.querySelector('.hc-root');
    if (root) root.dataset.theme = this._hass?.themes?.darkMode ? 'dark' : 'light';
  }

  connectedCallback() {
    if (this._active) return;
    this._active = true;
    if (!this.shadowRoot.querySelector('.hc-root')) this._mount();
    this._theme(); this._render();
    window.addEventListener('focus', this._onFocus);
    document.addEventListener('visibilitychange', this._onFocus);
    window.addEventListener('beforeunload', this._beforeUnload);
    this._refreshTimer = window.setInterval(this._onFocus, 15000);
    if (this._hass) this._load();
  }
  disconnectedCallback() {
    this._active = false; this._requestId++; this._queryGeneration++; this._loading = false;
    window.clearInterval(this._refreshTimer); this._refreshTimer = null;
    window.removeEventListener('focus', this._onFocus);
    document.removeEventListener('visibilitychange', this._onFocus);
    window.removeEventListener('beforeunload', this._beforeUnload);
    this._closeEditor(true, false);
  }
  _mount() {
    this.shadowRoot.innerHTML = `<style>${STYLES}</style><div class="hc-root"><div id="headerHost"></div><main class="hc-wrap hc-main"><div id="statusHost"></div>${TABS.map(([id]) => `<section id="panel-${id}" role="tabpanel" aria-labelledby="tab-${id}" tabindex="-1" hidden></section>`).join('')}<footer class="hc-footer"><span>HealthLink Studio</span><span id="checkTime"></span></footer></main><dialog id="editor" class="hc-dialog" aria-labelledby="editorTitle" aria-modal="true"></dialog><div id="live" class="hc-sr-only" role="status" aria-live="polite"></div></div>`;
    this.shadowRoot.addEventListener('click', e => this._click(e));
    this.shadowRoot.addEventListener('keydown', e => this._keydown(e));
    this.shadowRoot.addEventListener('input', e => this._input(e));
    this.shadowRoot.addEventListener('change', e => this._change(e));
    this.shadowRoot.addEventListener('focusout', e => {
      if (e.target.closest('#composeForm') && this._editor?.validated) this._validateComposer(false);
    });
    this.shadowRoot.addEventListener('submit', e => {
      if (e.target.id === 'queryForm') { e.preventDefault(); this._query(); }
      if (e.target.id === 'composeForm' || e.target.id === 'deleteForm') { e.preventDefault(); this._saveEditor(); }
    });
    const dialog = this.shadowRoot.getElementById('editor');
    dialog.addEventListener('cancel', e => { e.preventDefault(); this._closeEditor(); });
    dialog.addEventListener('click', e => {
      if (e.target !== dialog) return;
      const r = dialog.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) this._closeEditor();
    });
  }
  _render({body = true} = {}) {
    if (!this._active) return;
    const root = this.shadowRoot.querySelector('.hc-root'); if (!root) return;
    const focused = this.shadowRoot.activeElement;
    const insideEditor = focused?.closest('#editor');
    const focusId = !insideEditor && focused?.id;
    const selection = focusId && typeof focused.selectionStart === 'number' ? [focused.selectionStart, focused.selectionEnd] : null;
    const scroll = root.scrollTop;
    this.shadowRoot.getElementById('headerHost').innerHTML = headerView(this);
    const settings = this.shadowRoot.querySelector('.hl-settings');
    settings?.setAttribute('aria-label', this._t('HealthLink 설정','HealthLink settings'));
    const image = this.shadowRoot.getElementById('healthLinkLogo');
    const fallback = () => { this._logoFailed = true; image.hidden = true; this.shadowRoot.getElementById('logoFallback').hidden = false; };
    image.addEventListener('error', fallback, {once:true});
    image.addEventListener('load', () => {
      image.width = image.naturalWidth; image.height = image.naturalHeight;
    }, {once:true});
    if (this._logoFailed) fallback();
    for (const [id] of TABS) {
      const panel = this.shadowRoot.getElementById(`panel-${id}`); panel.hidden = id !== this._tab;
      if (id !== this._tab) panel.replaceChildren();
      else if (body) {
        panel.innerHTML = bodyView(this);
        for (const [key, value] of Object.entries(this._fields)) {
          const input = panel.querySelector(`#${key}`); if (input) input.value = value;
        }
      }
    }
    this._status(); this._filterMetrics();
    if (!insideEditor && focusId) {
      const next = this.shadowRoot.getElementById(focusId);
      if (next && !next.closest('[hidden]')) {
        next.focus({preventScroll:true});
        if (selection && next.setSelectionRange) { try { next.setSelectionRange(...selection); } catch { /* select/search may not support ranges */ } }
      }
    }
    root.scrollTop = scroll;
  }
  _status() {
    const host = this.shadowRoot.getElementById('statusHost'); if (!host) return;
    const markup = (this._errors.status ? errorView(this, this._errors.status, this._t('상태 확인에 실패했어요. 이전에 받은 정보는 최신이 아닐 수 있어요.','Status check failed. Previously received information may be out of date.')) : '') +
      (this._errors.action ? errorView(this, this._errors.action) : '') +
      (this._notice ? `<p class="hl-notice" role="status">${esc(this._notice)}</p>` : '');
    if (host.innerHTML !== markup) host.innerHTML = markup;
    this.shadowRoot.getElementById('checkTime').textContent = this._checkedAt ? this._t('상태 확인: ','Status checked: ') + this._date(this._checkedAt) : this._t('아직 상태를 확인하지 않았어요.','Status has not been checked yet.');
  }
  _announce(text) { const live = this.shadowRoot.getElementById('live'); if (live) live.textContent = text; }
  _resetProfile(id) {
    this._queryGeneration++;
    if (this._editor && this._editor.entryId !== id) this._closeEditor(true, false);
    this._entryId = id; this._catalog = []; this._composers = []; this._fields = {};
    this._results = {}; this._errors = {}; this._notice = ''; this._loaded = false;
  }
  async _load() {
    if (!this._active || !this._hass || this._hass.user?.is_admin === false) return;
    const requestId = ++this._requestId;
    this._loading = true; this._errors.status = null; this._render({body:!this._loaded});
    try {
      const profiles = await this._callWS({type:'health_link/status'});
      if (!this._active || requestId !== this._requestId) return;
      if (!Array.isArray(profiles)) throw new Error('Invalid profile response');
      this._profiles = profiles; this._checkedAt = new Date().toISOString();
      const chosen = profiles.find(p => p.config_entry_id === this._entryId) || profiles[0];
      if (chosen?.config_entry_id !== this._entryId) this._resetProfile(chosen?.config_entry_id || null);
      const id = this._entryId;
      if (id && chosen?.available !== false) {
        const data = await Promise.allSettled([
          this._callWS({type:'health_link/catalog/list',config_entry_id:id}),
          this._callWS({type:'health_link/composer/list',config_entry_id:id}),
        ]);
        if (!this._active || requestId !== this._requestId || id !== this._entryId) return;
        for (const [index, key] of ['catalog','composers'].entries()) {
          if (data[index].status === 'fulfilled' && Array.isArray(data[index].value)) {
            this[`_${key}`] = data[index].value; this._errors[key] = null;
          } else this._errors[key] = data[index].reason || new Error(`Invalid ${key} response`);
        }
      } else { this._catalog = []; this._composers = []; }
      this._loaded = true;
    } catch (error) {
      if (requestId === this._requestId) this._errors.status = error;
    } finally {
      if (this._active && requestId === this._requestId) { this._loading = false; this._render(); }
    }
  }
  _switchProfile(id) {
    this._requestId++; this._queryGeneration++;
    this._resetProfile(id); this._closeEditor(true); this._load();
  }
  async _refreshProfiles() {
    const focused = this.shadowRoot.activeElement;
    if (!this._active || !this._hass || this._loading || this._refreshingProfiles || this._editor || focused?.matches('input,select,textarea') || this._hass.user?.is_admin === false) return;
    const requestId = this._requestId, id = this._entryId;
    this._refreshingProfiles = true;
    try {
      const profiles = await this._callWS({type:'health_link/status'});
      if (!this._active || requestId !== this._requestId || id !== this._entryId) return;
      if (!Array.isArray(profiles)) throw new Error('Invalid profile response');
      const previous = this._profile(), selected = profiles.find(p => p.config_entry_id === id);
      this._profiles = profiles; this._checkedAt = new Date().toISOString(); this._errors.status = null;
      if (!selected || selected.available !== previous?.available) {
        this._switchProfile(selected?.config_entry_id || profiles[0]?.config_entry_id || null);
      } else this._render({body:this._tab === 'today' || this._tab === 'connect'});
    } catch (error) {
      if (this._active && requestId === this._requestId) { this._errors.status = error; this._render({body:false}); }
    } finally { this._refreshingProfiles = false; }
  }
  _navigate(tab) {
    if (!TABS.some(([id]) => id === tab) || this._editor) return;
    this._queryGeneration++;
    for (const key of ['timeline','insights']) if (this._results[key]?.state === 'loading') delete this._results[key];
    this._tab = tab; this._render();
    this.shadowRoot.getElementById(`tab-${tab}`)?.focus({preventScroll:true});
  }
  _click(event) {
    const tab = event.target.closest('[data-tab]');
    if (tab) { this._navigate(tab.dataset.tab); return; }
    const el = event.target.closest('[data-action]'); if (!el || el.disabled) return;
    const action = el.dataset.action;
    if (action === 'menu') this.dispatchEvent(new CustomEvent('hass-toggle-menu',{bubbles:true,composed:true}));
    if (action === 'overview') this._navigate('today');
    if (action === 'data') this._navigate('explorer');
    if (action === 'connection') this._navigate('connect');
    if (action === 'refresh') this._load();
    if (action === 'create') this._openEditor('create', el);
    if (action === 'delete') this._openEditor('delete', el);
    if (action === 'expose') this._expose(Number(el.dataset.index));
    if (action === 'close-editor') this._closeEditor();
    if (action === 'keep-editor') { this.shadowRoot.getElementById('discardPrompt').hidden = true; (this.shadowRoot.getElementById('cName') || this.shadowRoot.querySelector('#editor [data-action=close-editor]'))?.focus(); }
    if (action === 'discard-editor') this._closeEditor(true);
    if (action === 'mode' && this._analysis !== el.dataset.mode) {
      this._queryGeneration++; this._analysis = el.dataset.mode;
      for (const key of ['timeline','insights']) if (this._results[key]?.state === 'loading') delete this._results[key];
      this._render(); this.shadowRoot.querySelector(`[data-mode="${this._analysis}"]`)?.focus();
    }
  }
  _keydown(event) {
    // Native inertness handles the background. Explicit wrapping also prevents
    // Chromium from moving focus to browser chrome at the end of the dialog.
    if (this._editor && event.key === 'Tab') {
      const dialog = this.shadowRoot.getElementById('editor');
      const focusable = [...dialog.querySelectorAll('button,input,select,textarea,a[href],[tabindex]')]
        .filter(el => !el.matches(':disabled,[tabindex="-1"]') && el.getClientRects().length && !el.closest('[hidden]'));
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && event.target === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && event.target === last) { event.preventDefault(); first?.focus(); }
      return;
    }
    const tab = event.target.closest('[role="tab"]');
    if (!tab || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();
    const index = TABS.findIndex(([id]) => id === tab.dataset.tab);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? TABS.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + TABS.length) % TABS.length;
    this._navigate(TABS[next][0]);
  }
  _input(event) {
    const el = event.target; if (!el.id) return;
    if (el.closest('#editor')) { if (this._editor) this._editor.dirty = true; return; }
    if (!el.matches('input,select')) return;
    this._fields[el.id] = el.value;
    if (el.id === 'search' || el.id === 'exposureFilter') this._filterMetrics();
    if (el.closest('#queryForm')) {
      this._queryGeneration++; delete this._results[this._analysis];
      this._updateQueryResult();
    }
  }
  _change(event) {
    if (event.target.id === 'profile') { this._switchProfile(event.target.value); return; }
    this._input(event);
    if (event.target.id === 'inputBKind') this._syncEditorFields();
  }
  _filterMetrics() {
    const search = this.shadowRoot.getElementById('search'); if (!search) return;
    const q = search.value.trim().toLowerCase(), filter = this.shadowRoot.getElementById('exposureFilter').value;
    let total = 0, visible = 0;
    this.shadowRoot.querySelectorAll('[data-metric-row]').forEach(row => {
      row.hidden = !row.dataset.name.includes(q) || (filter !== 'all' && row.dataset.exposed !== String(filter === 'exposed'));
      total++; if (!row.hidden) visible++;
    });
    const noMatches = this.shadowRoot.getElementById('noMatches'); if (noMatches) noMatches.hidden = visible > 0;
    this.shadowRoot.getElementById('filterCount').textContent = this._t(`전체 ${this._number(total)}개 중 ${this._number(visible)}개 표시`,`${this._number(visible)} of ${this._number(total)} shown`);
  }
  _updateQueryResult() {
    const target = this.shadowRoot.getElementById('queryResult'); if (!target) return;
    target.innerHTML = resultView(this, this._analysis);
    const busy = this._results[this._analysis]?.state === 'loading';
    const submit = this.shadowRoot.querySelector('#queryForm button[type="submit"]');
    if (submit) {
      submit.disabled = busy || !this._catalog.some(x => numeric(x.sample_count) > 0);
      submit.setAttribute('aria-busy', String(busy));
      submit.textContent = busy ? this._t('조회 중…','Loading…') : this._analysis === 'insights' ? this._t('연관 분석하기','Analyze associations') : this._t('기록 조회','Show records');
    }
  }
  async _query() {
    const $ = id => this.shadowRoot.getElementById(id), key = this._analysis;
    if (this._results[key]?.state === 'loading' || !this._entryId) return;
    const metric = $(key === 'insights' ? 'inMetric' : 'tlMetric'), entity = $(key === 'insights' ? 'inEntity' : 'tlEntity');
    const missing = !metric?.value ? metric : key === 'insights' && !entity?.value ? entity : null;
    for (const input of [metric, entity]) input?.removeAttribute('aria-invalid');
    if (!metric?.value || missing) {
      if (missing) { missing.setAttribute('aria-invalid','true'); missing.focus(); }
      $('queryError').innerHTML = `<p class="hc-error" role="alert">${this._t('조회할 건강 항목과 필요한 집 센서를 선택해 주세요.','Choose a health metric and the required home sensor.')}</p>`; return;
    }
    $('queryError').replaceChildren();
    const id = this._entryId, generation = ++this._queryGeneration;
    const typeId = metric.value, entityId = entity.value;
    const days = Number($('inDays')?.value || 60), hours = Number($('tlHours')?.value || 24), goal = $('inGoal')?.value || 'high';
    this._results[key] = {state:'loading'}; this._updateQueryResult();
    try {
      const data = key === 'timeline' ? await this._callWS({type:'health_link/timeline/query',config_entry_id:id,type_id:typeId,entity_ids:entityId ? [entityId] : [],hours}) : await Promise.allSettled([
        this._callWS({type:'health_link/insights/correlation',config_entry_id:id,type_id:typeId,entity_id:entityId,days}),
        this._callWS({type:'health_link/optimizer/observe',config_entry_id:id,outcome_type_id:typeId,environment_entity_id:entityId,days,goal}),
      ]);
      if (!this._active || generation !== this._queryGeneration || id !== this._entryId || key !== this._analysis || this._tab !== 'timeline') return;
      this._results[key] = {state:'ready',data};
      this._announce(this._t('조회가 끝났어요. 아래 결과를 확인하세요.','Query finished. Review the results below.'));
    } catch (error) {
      if (this._active && generation === this._queryGeneration && id === this._entryId) this._results[key] = {state:'error',error};
    } finally {
      if (this._active && generation === this._queryGeneration && id === this._entryId) this._updateQueryResult();
    }
  }

  _openEditor(kind, opener) {
    if (this._editor || !this._entryId || this._profile()?.available === false || this._hass.user?.is_admin === false) return;
    const composer = kind === 'delete' ? this._composers.find(x => x.id === opener.dataset.id) : null;
    if (kind === 'delete' && !composer) return;
    this._editor = {kind,id:composer?.id,name:composer?.name,entryId:this._entryId,opener,dirty:false,busy:false,validated:false,stage:'editing'};
    const dialog = this.shadowRoot.getElementById('editor');
    dialog.innerHTML = editorView(this); this._syncEditorFields();
    this.shadowRoot.querySelector('.hc-root').dataset.modalOpen = 'true';
    dialog.showModal();
    (kind === 'create' ? this.shadowRoot.getElementById('cName') : dialog.querySelector('[data-action="close-editor"]'))?.focus();
  }
  _syncEditorFields() {
    if (this._editor?.kind !== 'create') return;
    const $ = id => this.shadowRoot.getElementById(id), kind = $('inputBKind').value;
    $('haField').hidden = kind !== 'ha'; $('inputBHa').disabled = kind !== 'ha';
    $('hkField').hidden = kind !== 'healthkit'; $('inputBHk').disabled = kind !== 'healthkit';
    $('op').disabled = kind === 'none'; if (kind === 'none') $('op').value = 'a';
  }
  _closeEditor(force = false, restoreFocus = true) {
    const editor = this._editor; if (!editor) return;
    if (!force && (editor.dirty || editor.busy)) {
      const prompt = this.shadowRoot.getElementById('discardPrompt');
      prompt.hidden = false;
      this.shadowRoot.getElementById('discardCopy').textContent = editor.busy ? this._t('닫아도 이미 전송한 요청은 계속 처리됩니다. 이 패널을 닫을까요?','An already submitted request continues after closing. Close this panel?') : this._t('아직 저장하지 않은 입력이 있어요. 입력을 버리고 닫을까요?','You have unsaved changes. Discard them and close?');
      prompt.querySelector('[data-action="keep-editor"]').focus(); return;
    }
    this._editor = null;
    const dialog = this.shadowRoot.getElementById('editor'); dialog?.close(); dialog?.replaceChildren();
    delete this.shadowRoot.querySelector('.hc-root')?.dataset.modalOpen;
    if (restoreFocus && this._active) {
      if (editor.opener?.isConnected) editor.opener.focus({preventScroll:true});
      else this.shadowRoot.getElementById(editor.kind === 'create' ? 'newSensor' : `tab-${this._tab}`)?.focus({preventScroll:true});
    }
  }
  _validateComposer(focus = true) {
    if (!this._editor || this._editor.kind !== 'create') return false;
    const $ = id => this.shadowRoot.getElementById(id), errors = {};
    const name = $('cName').value.trim(), id = $('cId').value.trim();
    if (!name || name.length > 96) errors.cName = this._t('센서 이름을 1~96자로 입력해 주세요.','Enter a sensor name from 1 to 96 characters.');
    if (!/^[a-z0-9_-]{1,64}$/.test(id)) errors.cId = this._t('영문 소문자·숫자·밑줄·하이픈으로 1~64자를 입력해 주세요.','Use 1–64 lowercase letters, numbers, underscores or hyphens.');
    else if (this._composers.some(x => x.id === id)) errors.cId = this._t('이미 사용 중인 ID예요. 다른 ID를 입력해 주세요.','This ID is already in use. Enter a different ID.');
    if (!$('inputA').value) errors.inputA = this._t('기준 건강 항목을 선택해 주세요.','Choose a health metric.');
    const kind = $('inputBKind').value;
    if (kind === 'ha' && !$('inputBHa').value) errors.inputBHa = this._t('조합할 집 센서를 선택해 주세요.','Choose a home sensor.');
    if (kind === 'healthkit' && !$('inputBHk').value) errors.inputBHk = this._t('조합할 건강 항목을 선택해 주세요.','Choose a health metric to combine.');
    for (const key of ['cName','cId','inputA','inputBHa','inputBHk']) {
      const error = $(`${key}-error`); error.hidden = !errors[key]; error.textContent = errors[key] || '';
      if (errors[key]) $(key).setAttribute('aria-invalid','true'); else $(key).removeAttribute('aria-invalid');
    }
    if (focus && Object.keys(errors).length) $(Object.keys(errors)[0]).focus();
    this._editor.validated = true;
    return !Object.keys(errors).length;
  }
  _editorBusy(editor, busy) {
    editor.busy = busy;
    if (this._editor !== editor || !this._active) return;
    const fields = this.shadowRoot.getElementById('editorFields'); if (fields) fields.disabled = busy;
    const button = this.shadowRoot.getElementById('saveComposer'); button.disabled = busy; button.setAttribute('aria-busy',String(busy));
    this.shadowRoot.getElementById('draftState').textContent = busy ? this._t('처리 중… 아직 완료되지 않았어요.','Processing… not completed yet.') : this._t('아직 저장하지 않았어요.','Not saved yet.');
  }
  async _saveEditor() {
    const editor = this._editor; if (!editor || editor.busy) return;
    const $ = id => this.shadowRoot.getElementById(id);
    if (editor.kind === 'create' && !this._validateComposer()) return;
    const name = $('cName')?.value.trim(), definitionId = editor.id || $('cId')?.value.trim();
    const key = `${editor.kind}:${editor.entryId}:${definitionId}`;
    if (this._mutations.has(key)) {
      $('editorError').innerHTML = errorView(this, new Error(this._t('같은 요청을 처리 중이에요. 완료 후 목록을 확인해 주세요.','The same request is still processing. Check the list after completion.'))); return;
    }
    let definition;
    if (editor.kind === 'create') {
      const kind = $('inputBKind').value, inputs = {a:{source:'healthkit',type_id:$('inputA').value}};
      if (kind === 'ha') inputs.b = {source:'ha',entity_id:$('inputBHa').value};
      if (kind === 'healthkit') inputs.b = {source:'healthkit',type_id:$('inputBHk').value};
      const formulas = {a:'a',avg:'(a+b)/2',add:'a+b',sub:'a-b',ratio:'ratio(a,b)',mul:'a*b'};
      definition = {inputs,formula:formulas[kind === 'none' ? 'a' : $('op').value],unit:$('unit').value.trim() || null,icon:'mdi:heart-plus'};
    }
    this._mutations.set(key,true); $('editorError').replaceChildren(); this._editorBusy(editor,true);
    try {
      if (editor.kind === 'create') {
        editor.stage = 'validating';
        const validation = await this._callWS({type:'health_link/composer/validate',definition});
        if (!validation.valid) throw new Error(validation.error || 'Invalid definition');
        if (!this._active || this._editor !== editor || editor.entryId !== this._entryId) return;
        // The API is an upsert. Recheck IDs immediately before save; never knowingly overwrite.
        const latest = await this._callWS({type:'health_link/composer/list',config_entry_id:editor.entryId});
        if (!Array.isArray(latest)) throw new Error('Cannot verify existing sensor IDs');
        if (latest.some(x => x.id === definitionId)) throw {code:'duplicate_id',message:'Existing composer ID'};
        if (!this._active || this._editor !== editor || editor.entryId !== this._entryId) return;
      }
      editor.stage = 'submitted';
      const response = await this._callWS(editor.kind === 'create'
        ? {type:'health_link/composer/save',config_entry_id:editor.entryId,definition_id:definitionId,name,definition}
        : {type:'health_link/composer/delete',config_entry_id:editor.entryId,definition_id:definitionId});
      if (!response?.ok) throw new Error('The server did not confirm this operation');
      if (!this._active || editor.entryId !== this._entryId) return;
      const notice = editor.kind === 'create' ? this._t('센서 설정을 저장했어요. HA 재로딩 후 실제 센서 반영을 확인해 주세요.','Sensor definition saved. Check the actual sensor after HA finishes reloading.') : response.removed ? this._t('조합 센서 설정을 삭제했어요. HA 재로딩 후 반영을 확인해 주세요.','Composed sensor definition deleted. Check the result after HA reloads.') : this._t('이 센서 설정은 이미 삭제되어 있어요.','This sensor definition was already removed.');
      if (this._editor === editor) { editor.dirty = false; this._closeEditor(true); }
      this._notice = notice; this._announce(notice); this._load();
    } catch (error) {
      if (this._active && this._editor === editor) $('editorError').innerHTML = errorView(this,error);
      else if (this._active && editor.entryId === this._entryId) { this._errors.action = error; this._status(); }
    } finally { this._mutations.delete(key); this._editorBusy(editor,false); }
  }
  async _expose(index) {
    const item = this._catalog[index], id = this._entryId; if (!item || !id) return;
    const key = `expose:${id}:${item.type_id}`; if (this._mutations.has(key)) return;
    this._mutations.set(key,true); this._errors.action = null; this._render();
    try {
      const response = await this._callWS({type:'health_link/catalog/expose',config_entry_id:id,type_id:item.type_id,exposed:!Boolean(item.exposed)});
      if (!response?.ok) throw new Error('The server did not confirm exposure settings');
      if (!this._active || id !== this._entryId) return;
      this._notice = this._t('HA 노출 설정을 저장했어요. 통합 재로딩 후 실제 센서 반영을 확인해 주세요.','HA exposure setting saved. Check the actual sensor after the integration reloads.');
      this._announce(this._notice);
      await this._load();
    } catch (error) {
      if (this._active && id === this._entryId) this._errors.action = error;
    } finally {
      this._mutations.delete(key);
      if (this._active && id === this._entryId) this._render();
    }
  }
}
if (!customElements.get('health-link-panel')) customElements.define('health-link-panel', HealthLinkPanel);
