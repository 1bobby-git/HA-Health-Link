const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname,'..');
const styles = fs.readFileSync(path.join(root,'custom_components/health_link/frontend/health-link-studio-branding.js'),'utf8');
const setup = fs.readFileSync(path.join(root,'custom_components/health_link/__init__.py'),'utf8');

test('Studio owns all four safe areas with HA values before env fallback',()=>{
  assert.match(setup,/handle_safe_area=True/);
  for(const edge of ['top','bottom','left','right']) {
    assert.ok(styles.includes(`--hl-safe-${edge}:var(--safe-area-inset-${edge},env(safe-area-inset-${edge},0px))`));
  }
  assert.match(styles,/:host\s*\{[\s\S]*?box-sizing:border-box;[\s\S]*?padding:var\(--hl-safe-top\) var\(--hl-content-right\) var\(--hl-safe-bottom\) var\(--hl-content-left\)/);
});
test('horizontal content insets preserve HA sidebar-consumed zero values',()=>{
  assert.ok(styles.includes('--hl-content-left:var(--safe-area-content-inset-left,var(--hl-safe-left))'));
  assert.ok(styles.includes('--hl-content-right:var(--safe-area-content-inset-right,var(--hl-safe-right))'));
  for(const gutter of [40,28,20,16]) assert.ok(styles.includes(`.hc-root .hc-wrap { padding-left:${gutter}px;padding-right:${gutter}px; }`));
});
test('top-layer dialog receives raw viewport insets once',()=>{
  assert.match(styles,/\.hc-root \.hc-dialog\s*\{\s*box-sizing:border-box;\s*padding:var\(--hl-safe-top\) var\(--hl-safe-right\) var\(--hl-safe-bottom\) var\(--hl-safe-left\)/);
  assert.match(styles,/\.hc-root \.hc-sheet-head \{ padding:18px 20px; \}/);
  assert.match(styles,/\.hc-root \.hc-sheet-foot \{ padding:16px 20px 20px; \}/);
});
