"""Synthetic HA safe-area regression tests; no physical iPhone assertion.
Run base studio_browser_checks.py and unified_browser_checks.py separately.
"""
import unittest
from unified_browser_checks import UnifiedUI


class SafeAreaUI(UnifiedUI):
    def mobile(self,width=416,height=904):
        self.page.set_viewport_size({'width':width,'height':height})

    def insets(self,top=0,right=0,bottom=0,left=0,content_left=None,content_right=None):
        self.page.locator('#frame').evaluate('''(e,values)=>{for(const [k,v] of Object.entries(values)){const n='--safe-area-'+k.replaceAll('_','-');if(v===null)e.style.removeProperty(n);else e.style.setProperty(n,v+'px')}}''',{'inset_top':top,'inset_right':right,'inset_bottom':bottom,'inset_left':left,'content_inset_left':content_left,'content_inset_right':content_right})

    def rect(self,selector):
        return self.page.locator(selector).bounding_box()

    def test_safe_area_portrait_keeps_scroll_below_system_bar(self):
        self.mobile();self.insets(top=62,bottom=34)
        self.assertEqual(self.rect('.hc-root')['y'],62)
        self.assertEqual(self.rect('.hc-root')['height'],904-62-34)
        for selector in ['.hc-brand','#refreshProfiles','.hl-settings','.hc-tabs']:self.assertGreaterEqual(self.rect(selector)['y'],62)
        self.page.locator('.hc-root').evaluate('(e)=>e.scrollTop=e.scrollHeight')
        self.assertEqual(self.rect('.hc-root')['y'],62)
        footer=self.rect('.hc-footer');self.assertLessEqual(footer['y']+footer['height'],904-34)
        self.assertEqual(self.page.evaluate('document.body.style.paddingTop'),'')

    def test_safe_area_mobile_widths_both_themes(self):
        for dark in [False,True]:
            self.page.evaluate('(dark)=>panel.hass={...panel._hass,themes:{darkMode:dark}}',dark)
            for width in [320,349,350,351,390,416,430,559,560,561,768,870]:
                self.mobile(width);self.insets(top=62,bottom=34)
                self.assertGreaterEqual(self.rect('.hc-brand')['y'],62)
                size=self.page.locator('.hc-root').evaluate('(e)=>[e.clientWidth,e.scrollWidth]');self.assertLessEqual(size[1],size[0]+1)
                boxes=[self.rect(s) for s in ['.hc-brand','#refreshProfiles','.hl-settings']]
                for a,b in zip(boxes,boxes[1:]):self.assertLessEqual(a['x']+a['width'],b['x']+1)
                image=self.rect('#healthLinkLogo');self.assertAlmostEqual(image['width']/image['height'],3,places=2)

    def test_safe_area_absent_does_not_add_desktop_space(self):
        self.mobile(1440,1100)
        self.assertEqual(self.rect('.hc-root')['y'],0)
        self.assertEqual(self.page.locator('health-link-panel').evaluate('(e)=>getComputedStyle(e).paddingTop'),'0px')
        self.assertEqual(self.page.locator('.hc-header-row').evaluate('(e)=>getComputedStyle(e).minHeight'),'72px')
        self.assertEqual(self.page.locator('.hc-hero').evaluate('(e)=>getComputedStyle(e).backgroundColor'),'rgb(255, 255, 255)')

    def test_safe_area_sidebar_consumed_horizontal_inset_is_not_repeated(self):
        self.mobile(1100,500);self.insets(left=59,right=59,bottom=21,content_left=0,content_right=59)
        box=self.rect('.hc-root');self.assertEqual(box['x'],0);self.assertEqual(box['x']+box['width'],1041)
        self.assertEqual(self.page.locator('.hc-header .hc-wrap').evaluate('(e)=>getComputedStyle(e).paddingLeft'),'40px')
        self.insets(left=59,right=59,bottom=21,content_left=59,content_right=0)
        box=self.rect('.hc-root');self.assertEqual(box['x'],59);self.assertEqual(box['x']+box['width'],1100)

    def test_safe_area_orientation_change_retains_draft(self):
        self.mobile();self.insets(top=62,bottom=34);self.editor();self.fill()
        self.page.evaluate('window.draftNode=panel.shadowRoot.getElementById("cName")')
        self.mobile(904,416);self.insets(left=59,right=59,bottom=21)
        self.assertEqual(self.rect('.hc-root')['y'],0);self.assertEqual(self.rect('.hc-root')['x'],59)
        self.assertTrue(self.page.evaluate('draftNode===panel.shadowRoot.getElementById("cName")'))
        self.assertEqual(self.page.locator('#cName').input_value(),'새 조합 센서')
        save=self.rect('#saveComposer');self.assertLessEqual(save['y']+save['height'],395);self.assertLessEqual(save['x']+save['width'],845)

    def test_safe_area_modal_uses_viewport_insets(self):
        self.mobile();self.insets(top=62,bottom=34);self.editor()
        self.assertGreaterEqual(self.rect('.hc-sheet-head')['y'],62)
        self.assertGreaterEqual(self.rect('.hc-sheet-head [data-action=close-editor]')['y'],62)
        save=self.rect('#saveComposer');self.assertLessEqual(save['y']+save['height'],870)
        self.page.keyboard.press('Escape');self.assertFalse(self.page.locator('#editor').is_visible())
        self.assertEqual(self.page.evaluate('panel.shadowRoot.activeElement.id'),'newSensor')

    def test_safe_area_changes_and_explicit_zero_do_not_accumulate(self):
        self.mobile()
        for top in [62,62,47,0,62,0]:
            self.insets(top=top,bottom=34);self.page.evaluate('panel._render();panel._render()')
            self.assertEqual(self.rect('.hc-root')['y'],top)

    def test_safe_area_menu_and_settings_are_usable(self):
        self.mobile();self.insets(top=62,bottom=34);self.page.evaluate('panel.narrow=true;window.menuEvents=0;panel.addEventListener("hass-toggle-menu",()=>window.menuEvents++)')
        self.page.locator('#nativeHaHeader button').click();self.assertEqual(self.page.evaluate('menuEvents'),1)
        self.assertEqual(self.page.locator('.hl-settings').get_attribute('href'),'/config/integrations/integration/health_link')
        for selector in ['#nativeHaHeader button','#refreshProfiles','.hl-settings']:
            box=self.rect(selector);self.assertGreaterEqual(box['width'],44);self.assertGreaterEqual(box['height'],44)
            self.assertGreaterEqual(box['y'],62)


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(SafeAreaUI(name) for name in dir(SafeAreaUI) if name.startswith('test_safe_area_'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
