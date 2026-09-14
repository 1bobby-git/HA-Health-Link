"""Production UI + synthetic HA shell contracts. Not a physical iOS/HA test.
Run: python tests/frontend/unified_browser_checks.py
The inherited 26 behavior tests are deliberately not rerun by this file.
"""
import unittest
from studio_browser_checks import StudioUI, ROOT


class UnifiedUI(StudioUI):
    def setUp(self):
        super().setUp()
        self.page.route('**/health_link_brand/logo.png*', lambda route: route.fulfill(
            body=(ROOT/'custom_components/health_link/brand/logo.png').read_bytes(), content_type='image/png'))
        self.page.evaluate((ROOT/'tests/frontend/native_header_fixture.js').read_text())
        self.page.add_style_tag(content=':root{--header-height:56px;--ha-space-3:12px;--ha-space-2:8px;--ha-space-6:24px}.demo-banner[hidden]{display:none}')
        self.page.locator('.demo-banner').evaluate('(e)=>e.hidden=true')
        self.page.evaluate('panel.panel={title:"HealthLink",config:{version:"0.3.8"}}; panel.hass={...hassFixture,connected:true,dockedSidebar:"docked",kioskMode:false};panel._render()')
        self.page.wait_for_function('panel.shadowRoot.getElementById("healthLinkLogo").naturalWidth===600')

    def root_bounds(self):
        return self.page.locator('.hc-root').bounding_box()

    def test_unified_ha_narrow_not_component_width_controls_header(self):
        for width,narrow,shown in [(870,True,True),(871,False,False),(616,False,False),(1440,True,True)]:
            self.page.set_viewport_size({'width':width,'height':904})
            self.page.evaluate('(n)=>panel.narrow=n',narrow)
            self.assertEqual(self.page.locator('#nativeHaHeader').is_visible(),shown)
        self.assertEqual(self.page.locator('.hc-header [data-action=menu]').count(),0)
        self.assertEqual(self.page.locator('.hl-appbar').count(),0)

    def test_unified_sidebar_hidden_and_kiosk(self):
        self.page.evaluate('panel.narrow=false;panel.hass={...panel._hass,dockedSidebar:"always_hidden"}')
        self.assertTrue(self.page.locator('#nativeHaHeader').is_visible())
        self.page.evaluate('panel.hass={...panel._hass,kioskMode:true}')
        self.assertFalse(self.page.locator('#nativeHaHeader').is_visible())
        self.page.evaluate('panel.narrow=true')
        self.assertFalse(self.page.locator('#nativeHaHeader').is_visible())

    def test_unified_safe_area_and_header_height_not_doubled(self):
        self.page.set_viewport_size({'width':390,'height':844})
        self.page.locator('#frame').evaluate('(e)=>e.style.cssText="--safe-area-inset-top:62px;--safe-area-inset-bottom:34px"')
        self.page.evaluate('panel.narrow=true')
        self.assertEqual(self.page.locator('#nativeHaHeader').bounding_box()['y'],62)
        self.assertEqual(self.root_bounds()['y'],118)
        self.assertEqual(self.root_bounds()['y']+self.root_bounds()['height'],810)
        self.page.locator('.hc-root').evaluate('(e)=>e.scrollTop=e.scrollHeight')
        self.assertEqual(self.page.locator('#nativeHaHeader').bounding_box()['y'],62)
        self.page.evaluate('panel.narrow=false')
        self.assertEqual(self.root_bounds()['y'],62)
        self.page.locator('#frame').evaluate('(e)=>e.style.cssText="--safe-area-inset-top:0px;--safe-area-inset-bottom:0px"')
        self.assertEqual(self.root_bounds()['y'],0)

    def test_unified_breakpoint_changes_keep_editor_and_draft(self):
        self.page.evaluate('panel.narrow=true');self.editor();self.fill()
        self.page.evaluate('window.draftNode=panel.shadowRoot.getElementById("cName");panel.narrow=false;panel.narrow=true;panel._render()')
        self.assertTrue(self.page.evaluate('draftNode===panel.shadowRoot.getElementById("cName")'))
        self.assertEqual(self.page.locator('#cName').input_value(),'새 조합 센서')
        self.assertTrue(self.page.locator('#editor').is_visible())

    def test_unified_header_icon_geometry_in_both_themes_and_errors(self):
        for dark in [False,True]:
            for width in [320,350,390,560,800,870,871,1100,1440]:
                self.page.set_viewport_size({'width':width,'height':904})
                for connected in [True,False]:
                    self.page.evaluate('([dark,connected])=>{panel.hass={...panel._hass,language:"ko",themes:{darkMode:dark},connected};panel._render()}',[dark,connected])
                    for selector,kind in [('.hl-settings','settings'),('#refreshProfiles','refresh')]:
                        item=self.page.locator(selector)
                        b=item.bounding_box();self.assertGreaterEqual(b['width'],44);self.assertGreaterEqual(b['height'],44)
                        svg=item.locator('svg');r=svg.bounding_box()
                        self.assertEqual((r['width'],r['height']),(20,20))
                        self.assertEqual(svg.get_attribute('data-icon'),kind)
                        self.assertEqual(svg.get_attribute('aria-hidden'),'true')
                        self.assertEqual(svg.get_attribute('focusable'),'false')
                        self.assertEqual(svg.evaluate('(e)=>getComputedStyle(e).stroke'),'none')
                        self.assertGreater(svg.locator('path').evaluate('(e)=>e.getBBox().width'),10)
                        self.assertAlmostEqual(r['x']+10,b['x']+b['width']/2,delta=1)
                        self.assertAlmostEqual(r['y']+10,b['y']+b['height']/2,delta=1)
                        self.assertTrue(item.get_attribute('aria-label'))
                        self.assertTrue(item.get_attribute('title'))
                    logo=self.page.locator('.hc-brand').bounding_box()
                    actions=self.page.locator('.hc-header-tools').bounding_box()
                    self.assertLessEqual(logo['x']+logo['width'],actions['x']+1)
                    widths=self.page.locator('.hc-root').evaluate('(e)=>[e.clientWidth,e.scrollWidth]')
                    self.assertLessEqual(widths[1],widths[0]+1)

    def test_unified_icons_work_without_ha_icon_registration(self):
        self.assertTrue(self.page.evaluate('!customElements.get("ha-icon") && !customElements.get("ha-svg-icon")'))
        self.assertEqual(self.page.locator('.hl-settings path').evaluate('(e)=>e.namespaceURI'),'http://www.w3.org/2000/svg')
        before=len(self.calls('/status'))
        self.page.locator('#refreshProfiles').click();self.page.wait_for_function('!panel._loading')
        self.assertEqual(len(self.calls('/status')),before+1)
        self.assertEqual(self.page.locator('.hl-settings').get_attribute('href'),'/config/integrations/integration/health_link')
        self.page.locator('#refreshProfiles').focus();self.page.keyboard.press('Tab');self.assertEqual(self.page.locator('.hl-settings').evaluate('(e)=>getComputedStyle(e).outlineStyle'),'solid')
        self.assertTrue(all(url.startswith('https://healthlink-preview.test/') for url in self.requests))

    def test_unified_native_menu_event_uses_host_element(self):
        self.page.evaluate('panel.narrow=true;window.menuEvents=0;panel.addEventListener("hass-toggle-menu",()=>menuEvents++)')
        self.page.locator('#nativeHaHeader button').click()
        self.assertEqual(self.page.evaluate('menuEvents'),1)

    def test_unified_reduced_motion_forced_colors(self):
        self.page.emulate_media(forced_colors='active',reduced_motion='reduce')
        self.page.locator('.hl-settings').focus()
        self.assertEqual(self.page.locator('.hl-settings').evaluate('(e)=>getComputedStyle(e).outlineStyle'),'solid')
        self.assertEqual(self.page.locator('.hl-settings svg').evaluate('(e)=>getComputedStyle(e).fill'),'rgb(0, 0, 0)')
        self.assertEqual(self.page.locator('#refreshProfiles').evaluate('(e)=>getComputedStyle(e).transitionDuration'),'0s')

    def test_unified_korean_labels_search_and_unknown_text_safety(self):
        self.nav('explorer')
        self.page.locator('#search').fill('심박수')
        self.assertEqual(self.page.locator('[data-metric-row]:not([hidden])').count(),1)
        self.page.locator('#search').fill('Heart Rate')
        self.assertEqual(self.page.locator('[data-metric-row]:not([hidden])').count(),1)
        self.page.locator('#search').fill('심장')
        self.assertEqual(self.page.locator('[data-metric-row]:not([hidden])').count(),1)
        self.page.locator('#search').fill('')
        self.page.locator('#newSensor').click()
        self.assertIn('심박수',self.page.locator('#inputA').inner_text())

    def test_unified_ecg_guide_requires_no_api_write(self):
        self.nav('explorer');self.page.locator('[data-action=ecg-guide]').click()
        self.assertTrue(self.page.locator('#ecgGuide').is_visible())
        self.assertEqual(self.page.evaluate('panel.shadowRoot.activeElement.id'),'ecgGuideTitle')
        text=self.page.locator('#ecgGuide').inner_text()
        for phrase in ['export.zip','민감','본인','심전도(ECG)']:
            self.assertIn(phrase,text)
        self.page.locator('#ecgGuide summary').click()
        self.assertIn('PDF',self.page.locator('#ecgGuide').inner_text())
        self.assertFalse(any(x['type'].endswith(('/save','/delete','/expose')) for x in self.page.evaluate('mock.calls')))

    def test_unified_design_tokens(self):
        for width,height,logo,top in [(1440,72,36,32),(870,62,32,26),(390,58,28,22)]:
            self.page.set_viewport_size({'width':width,'height':904})
            self.assertEqual(self.page.locator('.hc-header-row').evaluate('(e)=>getComputedStyle(e).minHeight'),str(height)+'px')
            self.assertEqual(self.page.locator('#healthLinkLogo').bounding_box()['height'],logo)
            self.assertEqual(self.page.locator('.hc-main').evaluate('(e)=>getComputedStyle(e).paddingTop'),str(top)+'px')
            self.assertEqual(self.page.locator('.hc-hero').evaluate('(e)=>getComputedStyle(e).borderRadius'),'16px')
            self.assertEqual(self.page.locator('.hc-card').first.evaluate('(e)=>getComputedStyle(e).borderRadius'),'14px')
            self.assertEqual(self.page.locator('#tab-today').evaluate('(e)=>getComputedStyle(e).fontSize'),'14px')

    def test_unified_native_header_size_follows_ha_token(self):
        self.page.evaluate('panel.narrow=true')
        for height in [40,56,64]:
            self.page.locator('#frame').evaluate('(e,h)=>e.style.setProperty("--header-height",h+"px")',height)
            self.assertEqual(self.root_bounds()['y'],height)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(UnifiedUI(name) for name in dir(UnifiedUI) if name.startswith('test_unified_'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
