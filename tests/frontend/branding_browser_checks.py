"""Original artwork/contrast regressions adapted to the shared header.
Run separately from the base 26 and unified 12 checks; synthetic HA only.
"""
import hashlib
import unittest
from studio_browser_checks import ROOT, WIDTHS
from unified_browser_checks import UnifiedUI


def luminance(rgb):
    linear = [x / 255 / 12.92 if x / 255 <= .04045 else ((x / 255 + .055) / 1.055) ** 2.4 for x in rgb]
    return sum(x * w for x, w in zip(linear, [.2126, .7152, .0722]))


def contrast(a, b):
    low, high = sorted([luminance(a), luminance(b)])
    return (high + .05) / (low + .05)


class BrandingUI(UnifiedUI):
    def setUp(self):
        super().setUp()
        self.page.route('**/health_link_static/brand/logo.png*', lambda route: route.fulfill(
            body=(ROOT/'custom_components/health_link/frontend/brand/logo.png').read_bytes(), content_type='image/png'))

    def logo_ready(self):
        self.page.wait_for_function('''()=>{const e=panel.shadowRoot.getElementById('healthLinkLogo');return e.complete&&e.naturalWidth===600&&!e.hidden}''')

    def test_brand_canonical_original_bytes_and_dimensions(self):
        original=(ROOT/'custom_components/health_link/brand/logo.png').read_bytes()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(original)).encode()+b'\0'+original).hexdigest(),'5647226142f5b85f69e3c6f280b9337d6dce7278')
        self.assertEqual(original,(ROOT/'custom_components/health_link/frontend/brand/logo.png').read_bytes())
        logo=self.page.locator('#healthLinkLogo')
        self.assertEqual(logo.evaluate('(e)=>[e.naturalWidth,e.naturalHeight]'),[600,200])
        self.assertEqual(logo.get_attribute('alt'),'HealthLink')
        self.assertEqual(logo.get_attribute('width'),'600')
        self.assertEqual(logo.get_attribute('height'),'200')
        self.assertIn('/health_link_brand/logo.png',logo.get_attribute('src'))
        self.assertEqual(self.page.locator('.hc-brand-caption').count(),0)
        self.assertFalse(self.page.locator('#logoFallback').is_visible())

    def test_brand_summary_contrast_in_both_themes_and_empty_state(self):
        selectors=['.hc-hero h2','.hc-hero-kicker','.hc-hero-status','.hc-metric strong','.hc-metric span','.hc-hero-foot','.hl-inline','.hc-hero-foot button']
        for dark in [False,True]:
            self.page.evaluate('(dark)=>panel.hass={...panel._hass,themes:{darkMode:dark}}',dark)
            for profile in ['demo-a','demo-b']:
                self.page.locator('#profile').select_option(profile);self.page.wait_for_function('!panel._loading')
                self.assertEqual(self.page.locator('.hc-hero').evaluate('(e)=>getComputedStyle(e).backgroundImage'),'none')
                for selector in selectors:
                    colors=self.page.locator(selector).first.evaluate(r'''e=>{const rgb=s=>s.match(/[\d.]+/g).map(Number);let p=e,bg;while(p){const c=rgb(getComputedStyle(p).backgroundColor);if(c.length===3||c[3]===1){bg=c.slice(0,3);break}p=p.parentElement}return [rgb(getComputedStyle(e).color).slice(0,3),bg]}''')
                    self.assertGreaterEqual(contrast(*colors),4.5,(dark,profile,selector,colors))
        self.page.locator('.hc-hero-status').evaluate('(e)=>e.dataset.state="error"')
        colors=self.page.locator('.hc-hero-status').evaluate(r'''e=>{const rgb=s=>s.match(/[\d.]+/g).slice(0,3).map(Number);let s=getComputedStyle(e);return [rgb(s.color),rgb(s.backgroundColor)]}''')
        self.assertGreaterEqual(contrast(*colors),4.5)

    def test_brand_mobile_size_ratio_no_crop_or_header_overlap(self):
        for width in WIDTHS:
            self.page.set_viewport_size({'width':width,'height':1000});self.logo_ready()
            image=self.page.locator('#healthLinkLogo');box=image.bounding_box()
            self.assertAlmostEqual(box['width']/box['height'],3,places=2)
            self.assertEqual(image.evaluate('(e)=>getComputedStyle(e).objectFit'),'contain')
            self.assertEqual(image.evaluate('(e)=>getComputedStyle(e).filter'),'none')
            boxes=self.page.locator('.hc-header-row button:visible,.hc-header-row a:visible').evaluate_all('(nodes)=>nodes.map(e=>e.getBoundingClientRect().toJSON())')
            for i,a in enumerate(boxes):
                for b in boxes[i+1:]:
                    self.assertFalse(min(a['right'],b['right'])-max(a['x'],b['x'])>1 and min(a['bottom'],b['bottom'])-max(a['y'],b['y'])>1)
        self.page.locator('.hc-brand').hover()
        self.assertEqual(self.page.locator('.hc-brand').evaluate('(e)=>getComputedStyle(e).filter'),'none')

    def test_brand_original_path_failure_uses_local_identical_asset(self):
        self.page.route('**/health_link_brand/logo.png*',lambda route:route.fulfill(status=404,body=''))
        self.page.evaluate('panel._render()')
        self.page.wait_for_function('''()=>{const e=panel.shadowRoot.getElementById('healthLinkLogo');return e.complete&&e.naturalWidth===600&&e.src.includes('/health_link_static/')}''')
        self.assertFalse(self.page.locator('#logoFallback').is_visible())

    def test_brand_transient_total_failure_recovers_on_next_render(self):
        fail=lambda route:route.fulfill(status=404,body='')
        for pattern in ['**/health_link_brand/logo.png*','**/health_link_static/brand/logo.png*']:self.page.route(pattern,fail)
        self.page.evaluate('panel._render()');self.page.wait_for_function('panel._logoFailed')
        self.assertTrue(self.page.locator('#logoFallback').is_visible())
        for pattern in ['**/health_link_brand/logo.png*','**/health_link_static/brand/logo.png*']:self.page.unroute(pattern,fail)
        self.page.evaluate('panel._load()');self.page.wait_for_function('!panel._loading');self.logo_ready()

    def test_brand_cached_image_remains_visible_after_repeated_refresh(self):
        for _ in range(6):self.page.evaluate('panel._render()');self.logo_ready()
        self.assertEqual(self.page.evaluate('panel.shadowRoot.querySelectorAll("style").length'),1)
        self.assertTrue(all(x.startswith('https://healthlink-preview.test/') for x in self.requests))

    def test_brand_theme_switch_preserves_editor_and_form(self):
        self.editor();self.fill();self.page.evaluate('panel.hass={...panel._hass,themes:{darkMode:true}}')
        self.assertTrue(self.page.locator('#editor').is_visible())
        self.assertEqual(self.page.locator('#cName').input_value(),'새 조합 센서')
        self.page.keyboard.press('Escape');self.page.locator('[data-action=discard-editor]').click();self.nav('today');self.logo_ready()

    def test_brand_forced_colors_keeps_summary_text_and_focus_visible(self):
        self.page.emulate_media(forced_colors='active',reduced_motion='reduce')
        self.page.locator('.hc-hero-foot button').focus();self.page.keyboard.press('Tab');self.page.keyboard.press('Shift+Tab')
        self.assertEqual(self.page.locator('.hc-hero-foot button').evaluate('(e)=>getComputedStyle(e).outlineStyle'),'solid')
        self.assertEqual(self.page.locator('.hc-hero-foot button').evaluate('(e)=>getComputedStyle(e).transitionDuration'),'0s')


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(BrandingUI(name) for name in dir(BrandingUI) if name.startswith('test_brand_'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
