const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const crypto = require('node:crypto');
const frontend = path.join(__dirname,'../custom_components/health_link/frontend');
const load = name => import(pathToFileURL(path.join(frontend,name)).href);

test('native header uses HA state, not the component width',async()=>{
  const {nativeHeaderVisible} = await load('health-link-studio-host.js');
  assert.equal(nativeHeaderVisible(true,{dockedSidebar:'docked'}),true);
  assert.equal(nativeHeaderVisible(false,{dockedSidebar:'docked'}),false);
  assert.equal(nativeHeaderVisible(false,{dockedSidebar:'always_hidden'}),true);
  assert.equal(nativeHeaderVisible(true,{kioskMode:true}),false);
  const source=fs.readFileSync(path.join(frontend,'health-link-studio-host.js'),'utf8');
  assert.doesNotMatch(source,/matchMedia|innerWidth|870|871|parent\.document|customElements\.define/);
  assert.match(source,/createElement\('ha-top-app-bar-fixed'\)/);
  assert.doesNotMatch(source,/\.shadowRoot\.querySelector\('ha-drawer'\)/);
});
test('official icons use filled SVG geometry and no font or icon loader',async()=>{
  const {icon,ICON_PATHS}=await load('health-link-studio-icons.js');
  assert.equal(Object.keys(ICON_PATHS).length,7);
  for(const name of Object.keys(ICON_PATHS)) {
    const markup=icon(name);
    assert.match(markup,/viewBox="0 0 24 24"/);
    assert.match(markup,/fill="currentColor" stroke="none"/);
    assert.match(markup,/aria-hidden="true" focusable="false"/);
    assert.match(markup,/xmlns="http:\/\/www.w3.org\/2000\/svg"/);
    assert.doesNotMatch(markup,/ha-icon|<use|<image|stroke-width/);
  }
  assert.equal(icon('not_an_icon'),'');
  assert.equal(icon('__proto__'),'');
  // Fingerprints of the exact upstream cog/refresh paths, not a look-alike.
  for(const [name,digest] of Object.entries({'settings': '648d853f197dc8326fa5beef414aa40f1af4cfd34aee9ec53869da9ed32019ba', 'refresh': '5ca53023e69dc96149d0996569f2fbbe7017ffa127bcce7e5a54c03d0a0f2d17'})) {
    assert.equal(crypto.createHash('sha256').update(ICON_PATHS[name]).digest('hex'),digest);
  }
});
test('shared typography, sizes and accessible icon targets remain wired',()=>{
  const css=fs.readFileSync(path.join(frontend,'health-link-studio-unified.css.js'),'utf8');
  for(const token of ['--app-radius-xl:16px','--app-radius-lg:14px','--app-radius-md:10px','--app-content-max:1248px','"Noto Sans KR"']) assert.ok(css.includes(token));
  for(const height of [72,62,58]) assert.ok(css.includes(`min-height:${height}px`));
  assert.match(css,/width:20px;height:20px/);
  assert.match(css,/width:44px;height:44px;min-height:44px;min-width:44px/);
  assert.match(css,/#nativeHaHeader[\s\S]*?height:var\(--header-height\)/);
  for(const name of ['health-link-studio-host.js','health-link-studio-icons.js','health-link-studio-labels.js','health-link-studio-help.js','health-link-studio-unified.css.js']) {
    require('node:child_process').execFileSync(process.execPath,['--check',path.join(frontend,name)]);
  }
});
test('Korean labels preserve IDs and imported source identity',async()=>{
  const {metricName,metricSearchText}=await load('health-link-studio-labels.js');
  const ko={_t:(k,e)=>k},en={_t:(k,e)=>e};
  const item={type_id:'HKQuantityTypeIdentifierHeartRate',display_name:'Heart Rate',domain:'heart'};
  assert.equal(metricName(ko,item),'심박수');
  assert.match(metricSearchText(ko,item),/심장/);
  assert.match(metricSearchText(ko,item),/heart rate/);
  assert.equal(item.display_name,'Heart Rate');
  const raw={type_id:'apple_export.HKQuantityTypeIdentifierHeartRate.0123456789ab',display_name:'Heart Rate · Test Watch · 원본'};
  assert.equal(metricName(ko,raw),'심박수 · Test Watch · 원본');
  assert.equal(metricName(en,raw),'Heart rate · Test Watch · raw');
  assert.equal(metricName(ko,{type_id:'unknown',display_name:'사용자 이름'}),'사용자 이름');
});
test('ECG guide has an escaped profile and native settings path only',async()=>{
  const {ecgHelpView}=await load('health-link-studio-help.js');
  const html=ecgHelpView({_t:(k,e)=>k,_profile:()=>({title:'<img src=x>'})});
  for(const text of ['export.zip','심전도(ECG)','electrocardiograms','PDF','/config/integrations/integration/health_link','&lt;img src=x&gt;']) assert.ok(html.includes(text));
  assert.doesNotMatch(html,/<input|type="file"|<script|<img src=x>/);
});
