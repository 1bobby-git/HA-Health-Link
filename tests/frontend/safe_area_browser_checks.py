"""Run with: python tests/frontend/safe_area_browser_checks.py.

Reuses the 26 Studio API/interaction regressions and adds mobile safe-area
geometry tests. HA-provided CSS insets are synthetic; this is not an iOS device
or VoiceOver test. Production ES modules and the unchanged logo are served.
"""
import unittest
import studio_browser_checks as base


class SafeAreaUI(base.StudioUI):
    def setUp(self):
        super().setUp()
        logo = base.ROOT / 'custom_components/health_link/brand/logo.png'
        for pattern in ['**/health_link_brand/logo.png*', '**/health_link_static/brand/logo.png*']:
            self.page.route(pattern, lambda route: route.fulfill(body=logo.read_bytes(), content_type='image/png'))
        self.page.evaluate('panel._render()')
        self.page.wait_for_function('panel.shadowRoot.getElementById("healthLinkLogo").naturalWidth===600')

    def mobile(self, width=416, height=904):
        self.page.set_viewport_size({'width': width, 'height': height})
        self.page.locator('.demo-banner').evaluate('(e)=>e.hidden=true')
        self.page.add_style_tag(content='.demo-banner[hidden]{display:none!important}')

    def insets(self, top=0, right=0, bottom=0, left=0, content_left=None, content_right=None):
        self.page.locator('#frame').evaluate('''(e, values)=>{
            for(const [key,value] of Object.entries(values)) {
                const name='--safe-area-'+key.replaceAll('_','-');
                if(value===null)e.style.removeProperty(name);
                else e.style.setProperty(name,value+'px');
            }
        }''', {'inset_top':top,'inset_right':right,'inset_bottom':bottom,'inset_left':left,
              'content_inset_left':content_left,'content_inset_right':content_right})

    def rect(self, selector):
        return self.page.locator(selector).bounding_box()

    def test_safe_area_portrait_keeps_scroll_below_system_bar(self):
        self.mobile(); self.insets(top=62,bottom=34)
        root = self.rect('.hc-root')
        self.assertAlmostEqual(root['y'],62,delta=0.1)
        self.assertAlmostEqual(root['height'],904-62-34,delta=0.1)
        for selector in ['.hc-brand','[data-action=menu]','#refreshProfiles','.hl-settings','.hc-tabs']:
            self.assertGreaterEqual(self.rect(selector)['y'],62)
        self.page.locator('.hc-root').evaluate('(e)=>e.scrollTop=e.scrollHeight')
        self.assertAlmostEqual(self.rect('.hc-root')['y'],62,delta=0.1)
        self.assertLessEqual(self.rect('.hc-footer')['y']+self.rect('.hc-footer')['height'],904-34)
        self.assertEqual(self.page.evaluate('document.body.style.paddingTop'),'')

    def test_safe_area_mobile_widths_both_themes(self):
        for dark in [False,True]:
            self.page.evaluate('(dark)=>panel.hass={...hassFixture,themes:{darkMode:dark}}',dark)
            for width in [320,349,350,351,390,416,430,559,560,561,768,870]:
                with self.subTest(dark=dark,width=width):
                    self.mobile(width); self.insets(top=62,bottom=34)
                    self.assertGreaterEqual(self.rect('.hc-brand')['y'],62)
                    root=self.page.locator('.hc-root').evaluate('(e)=>[e.clientWidth,e.scrollWidth]')
                    self.assertLessEqual(root[1],root[0]+1)
                    controls=[self.rect(x) for x in ['[data-action=menu]','.hc-brand','#refreshProfiles','.hl-settings']]
                    for a,b in zip(controls,controls[1:]):
                        self.assertLessEqual(a['x']+a['width'],b['x']+1)
                    image=self.rect('#healthLinkLogo')
                    self.assertAlmostEqual(image['width']/image['height'],3,places=2)

    def test_safe_area_absent_does_not_add_desktop_space(self):
        self.mobile(1440,1100)
        self.assertEqual(self.page.locator('health-link-panel').evaluate('(e)=>getComputedStyle(e).paddingTop'),'0px')
        self.assertEqual(self.rect('.hc-root')['y'],0)
        self.assertEqual(self.page.locator('.hc-header-row').evaluate('(e)=>getComputedStyle(e).minHeight'),'94px')
        self.assertEqual(self.page.locator('.hc-hero').evaluate('(e)=>getComputedStyle(e).backgroundColor'),'rgb(255, 255, 255)')

    def test_safe_area_sidebar_consumed_horizontal_inset_is_not_repeated(self):
        self.mobile(1100,500); self.insets(left=59,right=59,bottom=21,content_left=0,content_right=59)
        root=self.rect('.hc-root')
        self.assertEqual(root['x'],0)
        self.assertAlmostEqual(root['x']+root['width'],1100-59,delta=0.1)
        self.assertEqual(self.page.locator('.hc-header .hc-wrap').evaluate('(e)=>getComputedStyle(e).paddingLeft'),'40px')
        self.insets(left=59,right=59,bottom=21,content_left=59,content_right=0)
        self.assertEqual(self.rect('.hc-root')['x'],59)
        self.assertAlmostEqual(self.rect('.hc-root')['x']+self.rect('.hc-root')['width'],1100,delta=0.1)

    def test_safe_area_orientation_change_retains_draft(self):
        self.mobile(); self.insets(top=62,bottom=34); self.editor(); self.fill()
        self.page.evaluate('window.draftNode=panel.shadowRoot.getElementById("cName")')
        self.mobile(904,416); self.insets(left=59,right=59,bottom=21)
        self.assertEqual(self.rect('.hc-root')['y'],0)
        self.assertEqual(self.rect('.hc-root')['x'],59)
        self.assertTrue(self.page.evaluate('draftNode===panel.shadowRoot.getElementById("cName")'))
        self.assertEqual(self.page.locator('#cName').input_value(),'새 조합 센서')
        save=self.rect('#saveComposer')
        self.assertLessEqual(save['y']+save['height'],416-21)
        self.assertLessEqual(save['x']+save['width'],904-59)

    def test_safe_area_modal_uses_viewport_insets(self):
        self.mobile(); self.insets(top=62,bottom=34); self.editor()
        self.assertGreaterEqual(self.rect('.hc-sheet-head')['y'],62)
        self.assertGreaterEqual(self.rect('.hc-sheet-head [data-action=close-editor]').get('y',0),62)
        save=self.rect('#saveComposer')
        self.assertLessEqual(save['y']+save['height'],904-34)
        self.page.keyboard.press('Escape')
        self.assertFalse(self.page.locator('#editor').is_visible())
        self.assertEqual(self.page.evaluate('panel.shadowRoot.activeElement.id'),'newSensor')
        self.assertEqual(self.rect('.hc-root')['y'],62)

    def test_safe_area_changes_and_explicit_zero_do_not_accumulate(self):
        self.mobile()
        for top in [62,62,47,0,62,0]:
            self.insets(top=top,bottom=34)
            self.page.evaluate('panel._render();panel._render()')
            self.assertAlmostEqual(self.rect('.hc-root')['y'],top,delta=0.1)
        self.assertEqual(self.page.locator('health-link-panel').evaluate('(e)=>getComputedStyle(e).paddingTop'),'0px')

    def test_safe_area_menu_and_settings_are_usable(self):
        self.mobile(); self.insets(top=62,bottom=34)
        self.page.evaluate('''()=>{
          window.menuEvents=0;
          panel.addEventListener('hass-toggle-menu',()=>window.menuEvents++);
          panel.shadowRoot.addEventListener('click',e=>{if(e.target.closest('.hl-settings'))e.preventDefault()});
        }''')
        self.page.locator('[data-action=menu]').click()
        self.assertEqual(self.page.evaluate('menuEvents'),1)
        self.page.locator('.hl-settings').focus()
        self.assertTrue(self.page.evaluate('panel.shadowRoot.activeElement.classList.contains("hl-settings")'))
        self.assertEqual(self.page.locator('.hl-settings').get_attribute('href'),'/config/integrations/integration/health_link')
        for selector in ['[data-action=menu]','#refreshProfiles','.hl-settings']:
            box=self.rect(selector)
            self.assertGreaterEqual(box['height'],44)
            self.assertGreaterEqual(box['width'],44)


if __name__ == '__main__':
    unittest.main(verbosity=2)
