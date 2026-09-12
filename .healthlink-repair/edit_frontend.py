from pathlib import Path
import hashlib
source = (Path.cwd() / 'custom_components/health_link/frontend/health-link-panel.js').read_text()
assert hashlib.sha1(b'blob '+str(len(source.encode())).encode()+b'\0'+source.encode()).hexdigest() == '10489bdcf063c7a6bcfe4f3d6ffc152276b57a25'
s = source

def replace(a,b):
 global s
 assert s.count(a)==1, (a[:100],s.count(a))
 s=s.replace(a,b)
replace('    this._error = null;\n  }', '''    this._error = null;
    this._active = false;
    this._requestId = 0;
    this._refreshTimer = null;
    this._refreshingProfiles = false;
    this._brandUrl = null;
    this._brandRefreshAt = 0;
    this._brandPromise = null;
    this._onFocus = () => { if (document.visibilityState !== "hidden") this._refreshProfiles(); };
  }''')
replace('    if (first) this._load();', '    if (first && this._active) this._load();')
replace('''  connectedCallback() {
    this._render();
  }''','''  connectedCallback() {
    if (this._active) return;
    this._active = true;
    this._render();
    window.addEventListener("focus", this._onFocus);
    document.addEventListener("visibilitychange", this._onFocus);
    this._refreshTimer = window.setInterval(this._onFocus, 15000);
    if (this._hass) this._load();
  }

  disconnectedCallback() {
    this._active = false;
    this._requestId++;
    this._loading = false;
    window.clearInterval(this._refreshTimer);
    this._refreshTimer = null;
    window.removeEventListener("focus", this._onFocus);
    document.removeEventListener("visibilitychange", this._onFocus);
  }

  async _loadBrand() {
    if (this._brandPromise) return this._brandPromise;
    if (Date.now() < this._brandRefreshAt) return;
    this._brandPromise = (async () => {
      try {
        const result = await this._callWS({ type: "brands/access_token" });
        if (typeof result.token !== "string" || !result.token) throw new Error("Brand token unavailable");
        const query = new URLSearchParams({ token: result.token, v: "0.1.5" });
        this._brandUrl = `/api/brands/integration/health_link/logo.png?${query}`;
        this._brandRefreshAt = Date.now() + 30 * 60 * 1000;
      } catch {
        // Only public brand artwork falls back locally. Never use a long-lived HA token.
        this._brandUrl = null;
        this._brandRefreshAt = Date.now() + 60000;
      }
      if (this._active) this._updateLogo();
    })();
    try { await this._brandPromise; } finally { this._brandPromise = null; }
  }

  _logoSource() {
    return this._brandUrl || "/health_link_static/brand/logo.png?v=0.1.5";
  }

  _updateLogo() {
    const image = this.shadowRoot?.getElementById("healthLinkLogo");
    if (!image) return;
    image.src = this._logoSource();
    image.onerror = () => {
      image.onerror = null;
      image.src = "/health_link_static/brand/logo.png?v=0.1.5";
    };
  }

  _profileControls() {
    const options = this._profiles.map(p => `<option value="${this._esc(p.config_entry_id)}" ${p.config_entry_id === this._entryId ? "selected" : ""}>${this._esc(p.title)}${p.available === false ? this._t(" · 연결 대기", " · waiting") : ""}</option>`).join("");
    return `<select id="profile" aria-label="${this._t("건강 프로필 선택", "Select health profile")}" ${options ? "" : "disabled"}>${options || `<option>${this._t("등록된 프로필 없음", "No profiles")}</option>`}</select>
      <button id="refreshProfiles" class="secondary">${this._t("새로고침", "Refresh")}</button>
      <a class="manage" href="/config/integrations/integration/health_link">${this._t("프로필 추가·설정", "Add/manage profiles")}</a>`;
  }

  _bindProfileControls() {
    this.shadowRoot.getElementById("profile")?.addEventListener("change", e => this._switchProfile(e.target.value));
    this.shadowRoot.getElementById("refreshProfiles")?.addEventListener("click", () => this._load());
  }

  async _refreshProfiles() {
    if (!this._active || !this._hass || this._loading || this._refreshingProfiles) return;
    this._refreshingProfiles = true;
    try {
      const profiles = await this._callWS({ type: "health_link/status" });
      if (!this._active) return;
      const previous = this._profile();
      this._profiles = profiles;
      const selected = profiles.find(p => p.config_entry_id === this._entryId);
      if (!selected || selected.available !== previous?.available) {
        await this._switchProfile(selected?.config_entry_id || profiles[0]?.config_entry_id || null);
      } else if (this._tab === "today" || this._tab === "connect") {
        this._render();
      } else {
        // Do not wipe Composer inputs or timeline results during background refresh.
        const controls = this.shadowRoot.getElementById("profileControls");
        if (controls) { controls.innerHTML = this._profileControls(); this._bindProfileControls(); }
      }
      await this._loadBrand();
    } catch {
      // A temporarily disconnected HA must not clear another profile's form.
    } finally { this._refreshingProfiles = false; }
  }

  async _switchProfile(id) {
    this._entryId = id;
    this._catalog = [];
    this._composers = [];
    this._error = null;
    this._loading = true;
    this._render();
    const requestId = ++this._requestId;
    try {
      if (id && this._profile()?.available !== false) await this._loadProfileData(requestId);
    } catch (err) {
      if (requestId === this._requestId) this._error = String(err?.message || err);
    } finally {
      if (requestId === this._requestId && this._active) { this._loading = false; this._render(); }
    }
  }''')
start=s.index('  async _load() {');end=s.index('  _fmt(',start)
s=s[:start]+'''  async _load() {
    if (!this._hass || this._loading || !this._active) return;
    this._loading = true;
    this._error = null;
    const requestId = ++this._requestId;
    this._render();
    try {
      const profiles = await this._callWS({ type: "health_link/status" });
      if (!this._active || requestId !== this._requestId) return;
      this._profiles = profiles;
      if (!profiles.some(p => p.config_entry_id === this._entryId)) {
        this._entryId = profiles[0]?.config_entry_id || null;
        this._catalog = [];
        this._composers = [];
      }
      if (this._entryId && this._profile()?.available !== false) await this._loadProfileData(requestId);
      else { this._catalog = []; this._composers = []; }
      await this._loadBrand();
    } catch (err) {
      if (requestId === this._requestId) this._error = String(err?.message || err);
    } finally {
      if (requestId === this._requestId && this._active) { this._loading = false; this._render(); }
    }
  }

  async _loadProfileData(requestId = this._requestId) {
    const id = this._entryId;
    const [catalog, composers] = await Promise.all([
      this._callWS({ type: "health_link/catalog/list", config_entry_id: id }),
      this._callWS({ type: "health_link/composer/list", config_entry_id: id }),
    ]);
    // Responses for the previous person must never be shown under the new name.
    if (this._active && id === this._entryId && requestId === this._requestId) {
      this._catalog = catalog;
      this._composers = composers;
    }
  }

  _profile() { return this._profiles.find(p => p.config_entry_id === this._entryId); }
''' +s[end:]
replace('    h2 { font-size:20px; margin:24px 0 12px; }','''    h1 img { width: min(360px, 75vw); height: auto; display:block; }
    #profileControls { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
    .manage { color:var(--primary-color); padding:10px 6px; }
    h2 { font-size:20px; margin:24px 0 12px; }''')
replace('''    const profiles = this._profiles.map(x => `<option value="${this._esc(x.config_entry_id)}" ${x.config_entry_id===this._entryId?'selected':''}>${this._esc(x.title)}</option>`).join("");\n''','')
replace('<header><div><h1>❤ HealthLink</h1>','<header><div><h1><img id="healthLinkLogo" src="${this._esc(this._logoSource())}" alt="HealthLink" width="600" height="200"></h1>')
replace('''      ${this._profiles.length>1?`<select id="profile" aria-label="${this._t('건강 프로필','Health profile')}">${profiles}</select>`:''}</header>''','      <div id="profileControls">${this._profileControls()}</div></header>')
replace('    this._bind();\n  }','    this._bind();\n    this._updateLogo();\n  }')
replace("    if (this._tab === 'today') return this._today(p);",'''    if (p.available === false) return `<div class="card setup"><h2>${this._esc(p.title)}</h2><p>${this._t('등록된 프로필입니다. 현재 연결 대기 또는 설정 확인이 필요합니다. 다른 사용자의 데이터로 대신 표시하지 않습니다.','This profile is registered but waiting for connection or setup. Data from another person is never substituted.')}</p><p class="note">${this._esc(p.entry_state || '')}</p><a class="manage" href="/config/integrations/integration/health_link">${this._t('HealthLink 설정 확인','Check HealthLink settings')}</a></div>`;
    if (this._tab === 'today') return this._today(p);''')
replace("    this.shadowRoot.getElementById('profile')?.addEventListener('change',async e=>{this._entryId=e.target.value;this._loading=true;this._render();try{await this._loadProfileData();}finally{this._loading=false;this._render();}});",'    this._bindProfileControls();')
a=s.index("${this._metric('HealthLink Full Transport'");b=s.index("${this._metric(this._t('소스'",a)
s=s[:a]+"${this._metric(this._t('연결 iPhone','Connected iPhones'),p.companion_device_count||0)}"+s[b:]
a=s.index("      <h2>${this._t('전체 HealthKit 확장'");b=s.index('`;\n  }',a)
s=s[:a]+'''      <div class="card" style="margin-top:12px"><div class="note">${this._t('데이터 소스는 공식 Home Assistant iOS 앱의 Apple 건강 센서(Labs)입니다. 별도 HealthLink 앱은 없으며, 해당 iPhone이 HA로 보낸 항목만 가져옵니다. 한 프로필에는 같은 사람의 iPhone만 연결하세요.','Data comes from Apple Health Sensors (Labs) in the official Home Assistant iOS app. No separate HealthLink app is required. Connect only phones belonging to the same person to each profile.')}</div></div>'''+s[b:]
(Path.cwd() / 'custom_components/health_link/frontend/health-link-panel.js').write_text(s)
print('Frontend profile refresh and authenticated brand rendering applied.')
