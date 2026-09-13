const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.join(__dirname, '..');
const frontend = path.join(root,'custom_components/health_link/frontend');
const branding = fs.readFileSync(path.join(frontend,'health-link-studio-branding.js'),'utf8');
const controller = fs.readFileSync(path.join(frontend,'health-link-panel-modern.js'),'utf8');
const setup = fs.readFileSync(path.join(root,'custom_components/health_link/__init__.py'),'utf8');

test('header artwork is byte-identical to the requested canonical GitHub logo',()=>{
  const original=fs.readFileSync(path.join(root,'custom_components/health_link/brand/logo.png'));
  const fallback=fs.readFileSync(path.join(frontend,'brand/logo.png'));
  const sha=crypto.createHash('sha1').update(`blob ${original.length}\0`).update(original).digest('hex');
  assert.equal(sha,'5647226142f5b85f69e3c6f280b9337d6dce7278');
  assert.deepEqual(original,fallback);
  assert.equal(original.readUInt32BE(16),600);
  assert.equal(original.readUInt32BE(20),200);
});
test('canonical local asset route and UI cache revisions are wired to production',()=>{
  assert.match(setup,/"\/health_link_brand\/logo\.png"/);
  assert.match(setup,/Path\(__file__\)\.parent \/ "brand" \/ "logo\.png"/);
  assert.match(setup,/ui=20260914\.1/);
  assert.match(controller,/health-link-studio-branding\.js\?v=20260914\.1/);
  assert.match(controller,/bindStudioLogo\(this\)/);
  assert.match(controller,/\$\{STYLES\}\$\{STUDIO_BRANDING_STYLES\}/);
  assert.doesNotMatch(branding,/https?:\/\//);
});
test('white summary uses semantic foregrounds rather than legacy pale-on-navy colors',()=>{
  assert.match(branding,/--hc-hero-bg:var\(--hc-surface\)/);
  assert.match(branding,/background:var\(--hc-surface\)/);
  assert.match(branding,/\.hc-hero h2,[^\n]+color:var\(--hc-ink\)/);
  assert.match(branding,/\.hc-hero-foot button[\s\S]+color:var\(--hc-blue\)/);
  assert.doesNotMatch(branding,/radial-gradient|#b9c5d9|#bce7d8|#bfccdf|#dae4f8/);
  assert.match(branding,/forced-colors:active/);
});
test('branding module syntax is valid',()=>{
  require('node:child_process').execFileSync(process.execPath,['--check',path.join(frontend,'health-link-studio-branding.js')]);
});

require('./test_studio_safe_area.cjs');
