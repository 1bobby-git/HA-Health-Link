"""Original logo and light-summary regression tests (synthetic health data).

Run alongside studio_browser_checks.py. Uses the real approved PNG bytes;
only HA WebSocket calls are mocked by the shared test harness.
"""
import hashlib
import unittest
from studio_browser_checks import ROOT, WIDTHS, StudioUI


def luminance(rgb):
    values = [x / 255 for x in rgb]
    linear = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in values]
    return sum(x * weight for x, weight in zip(linear, [.2126, .7152, .0722]))


def contrast(a, b):
    lower, upper = sorted([luminance(a), luminance(b)])
    return (upper + .05) / (lower + .05)


class BrandingUI(StudioUI):
    def setUp(self):
        super().setUp()
        # Reuse the behavioral harness while mapping the new production image
        # routes to the real, unchanged repository PNGs for branding checks.
        self.page.route('**/health_link_brand/logo.png*', lambda route: route.fulfill(
            body=(ROOT / 'custom_components/health_link/brand/logo.png').read_bytes(),
            content_type='image/png'))
        self.page.route('**/health_link_static/brand/logo.png*', lambda route: route.fulfill(
            body=(ROOT / 'custom_components/health_link/frontend/brand/logo.png').read_bytes(),
            content_type='image/png'))
        self.page.evaluate('panel._render()')
        self.logo_ready()

    def logo_ready(self):
        self.page.wait_for_function('''() => {
          const image=panel.shadowRoot.getElementById('healthLinkLogo');
          return image && image.complete && image.naturalWidth===600 && !image.hidden;
        }''')

    def test_brand_canonical_original_bytes_and_dimensions(self):
        data = (ROOT / 'custom_components/health_link/brand/logo.png').read_bytes()
        digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        self.assertEqual(digest, '5647226142f5b85f69e3c6f280b9337d6dce7278')
        self.assertEqual(data, (ROOT / 'custom_components/health_link/frontend/brand/logo.png').read_bytes())
        self.logo_ready()
        image = self.page.locator('#healthLinkLogo')
        self.assertIn('/health_link_brand/logo.png?v=56472261', image.get_attribute('src'))
        self.assertEqual(image.get_attribute('alt'), 'HealthLink')
        self.assertEqual(image.get_attribute('width'), '600')
        self.assertEqual(image.get_attribute('height'), '200')
        self.assertEqual(image.evaluate('(e)=>[e.naturalWidth,e.naturalHeight]'), [600,200])
        self.assertIn('나의 건강, 한곳에', self.page.locator('.hc-brand-caption').inner_text())
        self.assertFalse(self.page.locator('#logoFallback').is_visible())

    def test_brand_summary_contrast_in_both_themes_and_empty_state(self):
        targets = ['.hc-hero h2','.hc-hero-kicker','.hc-hero-status',
                   '.hc-hero .hc-metric strong','.hc-hero .hc-metric span',
                   '.hc-hero-foot','.hc-hero-foot .hl-inline','.hc-hero-foot button']
        for dark in [False, True]:
            self.page.evaluate('(dark)=>panel.hass={...hassFixture,themes:{darkMode:dark}}', dark)
            for profile in ['demo-a','demo-b']:
                self.page.locator('#profile').select_option(profile)
                self.page.wait_for_function('!panel._loading')
                hero = self.page.locator('.hc-hero')
                background = hero.evaluate('(e)=>getComputedStyle(e).backgroundColor')
                self.assertEqual(background, 'rgb(27, 34, 44)' if dark else 'rgb(255, 255, 255)')
                self.assertEqual(hero.evaluate('(e)=>getComputedStyle(e).backgroundImage'), 'none')
                for selector in targets:
                    with self.subTest(dark=dark,profile=profile,selector=selector):
                        colors = self.page.locator(selector).first.evaluate(r'''e=>{
                          const rgb=s=>s.match(/[\d.]+/g).map(Number);
                          let parent=e,bg;
                          while(parent){
                            const c=rgb(getComputedStyle(parent).backgroundColor);
                            if(c.length===3||c[3]===1){bg=c.slice(0,3);break;}
                            parent=parent.parentElement;
                          }
                          return {fg:rgb(getComputedStyle(e).color).slice(0,3),bg};
                        }''')
                        self.assertGreaterEqual(contrast(colors['fg'], colors['bg']), 4.5, colors)
        self.page.evaluate('''() => {
          const badge=panel.shadowRoot.querySelector('.hc-hero-status');
          badge.dataset.state='error';
        }''')
        colors=self.page.locator('.hc-hero-status').evaluate(r'''e=>{
          const rgb=s=>s.match(/[\d.]+/g).slice(0,3).map(Number);
          const s=getComputedStyle(e);return [rgb(s.color),rgb(s.backgroundColor)];
        }''')
        self.assertGreaterEqual(contrast(*colors),4.5)

    def test_brand_mobile_size_ratio_no_crop_or_header_overlap(self):
        for width in WIDTHS:
            self.page.set_viewport_size({'width':width,'height':1000})
            self.logo_ready()
            image=self.page.locator('#healthLinkLogo')
            size=image.bounding_box()
            self.assertAlmostEqual(size['width']/size['height'],3,places=2)
            self.assertEqual(image.evaluate('(e)=>getComputedStyle(e).objectFit'),'contain')
            self.assertEqual(image.evaluate('(e)=>getComputedStyle(e).filter'),'none')
            controls=self.page.locator('.hc-header-row button:visible,.hc-header-row a:visible,.hc-header-row select:visible').evaluate_all('''nodes=>nodes.map(e=>{
              const r=e.getBoundingClientRect();return {name:e.getAttribute('aria-label')||e.id||e.textContent,x:r.x,y:r.y,right:r.right,bottom:r.bottom};
            })''')
            for i,a in enumerate(controls):
                for b in controls[i+1:]:
                    overlap=min(a['right'],b['right'])-max(a['x'],b['x'])>1 and min(a['bottom'],b['bottom'])-max(a['y'],b['y'])>1
                    self.assertFalse(overlap, (width,a,b))
        self.page.locator('.hc-brand').hover()
        self.assertEqual(self.page.locator('.hc-brand').evaluate('(e)=>getComputedStyle(e).filter'),'none')

    def test_brand_original_path_failure_uses_local_identical_asset(self):
        self.page.route('**/health_link_brand/logo.png*', lambda route: route.fulfill(status=404,body=''))
        self.page.evaluate('panel._render()')
        self.page.wait_for_function('''() => {
          const image=panel.shadowRoot.getElementById('healthLinkLogo');
          return image.complete && image.naturalWidth===600 && image.src.includes('/health_link_static/');
        }''')
        self.assertFalse(self.page.locator('#logoFallback').is_visible())
        self.assertFalse(self.page.evaluate('panel._logoFailed'))

    def test_brand_transient_total_failure_recovers_on_next_render(self):
        fail = lambda route: route.fulfill(status=404,body='')
        self.page.route('**/health_link_brand/logo.png*', fail)
        self.page.route('**/health_link_static/brand/logo.png*', fail)
        self.page.evaluate('panel._render()')
        self.page.wait_for_function('panel._logoFailed')
        self.assertTrue(self.page.locator('#logoFallback').is_visible())
        self.page.unroute('**/health_link_brand/logo.png*', fail)
        self.page.unroute('**/health_link_static/brand/logo.png*', fail)
        self.page.evaluate('panel._load()')
        self.page.wait_for_function('!panel._loading')
        self.logo_ready()
        self.assertFalse(self.page.evaluate('panel._logoFailed'))
        self.assertFalse(self.page.locator('#logoFallback').is_visible())

    def test_brand_cached_image_remains_visible_after_repeated_refresh(self):
        self.logo_ready()
        for _ in range(6):
            self.page.evaluate('panel._render()')
            self.logo_ready()
        self.assertEqual(self.page.locator('health-link-panel').evaluate('(e)=>e.shadowRoot.querySelectorAll("style").length'),1)
        self.assertFalse(self.page.locator('#logoFallback').is_visible())
        self.assertTrue(all(x.startswith('https://healthlink-preview.test/') for x in self.requests))

    def test_brand_theme_switch_preserves_editor_and_form(self):
        self.editor();self.fill()
        self.page.evaluate('panel.hass={...hassFixture,themes:{darkMode:true}}')
        self.assertTrue(self.page.locator('#editor').is_visible())
        self.assertEqual(self.page.locator('#cName').input_value(),'새 조합 센서')
        self.page.keyboard.press('Escape')
        self.page.locator('[data-action=discard-editor]').click()
        self.nav('today')
        self.logo_ready()
        self.assertEqual(self.page.locator('.hc-hero').evaluate('(e)=>getComputedStyle(e).backgroundImage'),'none')

    def test_brand_forced_colors_keeps_summary_text_and_focus_visible(self):
        self.page.emulate_media(forced_colors='active',reduced_motion='reduce')
        self.page.locator('.hc-hero-foot button').focus()
        self.assertEqual(self.page.locator('.hc-hero').evaluate('(e)=>getComputedStyle(e).backgroundImage'),'none')
        self.assertEqual(self.page.locator('.hc-hero-foot button').evaluate('(e)=>getComputedStyle(e).outlineStyle'),'solid')
        self.assertEqual(self.page.locator('.hc-hero-foot button').evaluate('(e)=>getComputedStyle(e).transitionDuration'),'0s')


def load_tests(loader, tests, pattern):
    # The inherited 26 behavioral checks are run separately, not counted twice.
    return unittest.TestSuite(BrandingUI(name) for name in dir(BrandingUI) if name.startswith('test_brand_'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
