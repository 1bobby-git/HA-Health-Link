const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../custom_components/health_link/frontend/health-link-panel.js'), 'utf8');
const modernSource = fs.readFileSync(path.join(__dirname, '../custom_components/health_link/frontend/health-link-panel-modern.js'), 'utf8');
function panel() {
  let Panel;
  const context = {
    HTMLElement: class { attachShadow() { this.shadowRoot = {innerHTML:'', getElementById:()=>null, querySelectorAll:()=>[]}; } },
    customElements: { define: (_name, ctor) => {Panel=ctor;} },
    window: {addEventListener(){},removeEventListener(){},setInterval(){return 1;},clearInterval(){}},
    document: {visibilityState:'visible',addEventListener(){},removeEventListener(){}},
    URLSearchParams, Date, console,
  };
  vm.runInNewContext(source,context);
  const p=new Panel(); p._active=true; p._hass={language:'ko'}; p._render=()=>{};
  return p;
}
function deferred(){let resolve; const promise=new Promise(r=>{resolve=r;});return {promise,resolve};}

test('refresh discovers another profile while preserving selected person',async()=>{
  const p=panel(); p._profiles=[{config_entry_id:'a',title:'A',available:true}];p._entryId='a';
  p._callWS=async request=>request.type==='health_link/status' ? [{config_entry_id:'a',title:'A',available:true},{config_entry_id:'b',title:'B',available:false}] : {token:'limited-brand-token'};
  await p._refreshProfiles();
  assert.equal(p._profiles.length,2);assert.equal(p._entryId,'a');
  assert.match(p._profileControls(),/value="b"/);
});

test('late response cannot place person A data into person B',async()=>{
  const p=panel();p._profiles=['a','b'].map(id=>({config_entry_id:id,available:true}));
  const a=deferred(),b=deferred();
  p._callWS=request=>request.config_entry_id==='a'?a.promise:b.promise;
  const first=p._switchProfile('a'),second=p._switchProfile('b');
  b.resolve([{id:'B-data'}]);await second;
  a.resolve([{id:'A-data'}]);await first;
  assert.equal(p._entryId,'b');assert.equal(p._catalog[0].id,'B-data');
});

test('unavailable profile never borrows the first loaded profile',async()=>{
  const p=panel();p._profiles=[{config_entry_id:'a',title:'A',available:true},{config_entry_id:'b',title:'B',available:false}];
  p._catalog=[{secret:'old A data'}];p._composers=[{secret:'old A composer'}];p._callWS=()=>{throw Error('No query allowed');};
  await p._switchProfile('b');assert.equal(p._catalog.length,0);assert.equal(p._composers.length,0);
  assert.equal(p._profile().title,'B');assert.match(p._content(p._profile()),/설정 확인/);
  p._entryId='deleted';assert.equal(p._profile(),undefined);
});

test('background refresh does not reset the Composer form',async()=>{
  const p=panel();p._tab='composer';p._entryId='a';p._profiles=[{config_entry_id:'a',available:true}];
  p._render=()=>{throw Error('Must not redraw active Composer form');};
  p._callWS=async request=>request.type==='health_link/status'?[{config_entry_id:'a',available:true},{config_entry_id:'b',available:true}]:{token:'brand'};
  await p._refreshProfiles();assert.equal(p._profiles.length,2);
});

test('logo uses the token-authenticated local Brands API',async()=>{
  const p=panel();p._callWS=async request=>{assert.equal(request.type,'brands/access_token');return {token:'abc+/='};};
  await p._loadBrand();
  assert.match(p._logoSource(),/^\/api\/brands\/integration\/health_link\/logo.png\?/);
  assert.match(p._logoSource(),/token=abc%2B%2F%3D/);assert.match(p._logoSource(),/v=0.1.5/);
});

test('token failure uses bundled public artwork rather than an external app',async()=>{
  const p=panel();p._callWS=async()=>{throw Error('offline');};await p._loadBrand();
  assert.equal(p._logoSource(),'/health_link_static/brand/logo.png?v=0.1.5');
  p.disconnectedCallback();assert.equal(p._active,false);assert.equal(p._refreshTimer,null);
});

test('modern Studio keeps small radii and clearer information hierarchy',()=>{
  assert.match(modernSource,/--hl-radius-lg:12px/);
  assert.match(modernSource,/--hl-radius-md:10px/);
  assert.match(modernSource,/--hl-radius-sm:8px/);
  assert.match(modernSource,/오늘 요약/);
  assert.match(modernSource,/분석 준비도/);
  assert.match(modernSource,/최근 인사이트/);
  assert.match(modernSource,/빠른 작업/);
  assert.match(modernSource,/ECG·건강 원본 가져오기/);
});

test('modern Studio keeps settings separate and uses native integration routes',()=>{
  assert.match(modernSource,/\/config\/integrations\/integration\/health_link/);
  assert.match(modernSource,/\/config\/integrations\/dashboard\/add\?domain=health_link/);
  assert.doesNotMatch(modernSource,/config_panel_domain/);
});
