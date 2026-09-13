"""Offline browser contract tests. Run: python tests/frontend/studio_browser_checks.py

Requires Playwright and Chromium (CHROMIUM_PATH may select an installed browser).
Real production modules are served by request interception, not rewritten stubs.
Only the hass.callWS boundary is mocked; no live health data or credentials.
"""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import os
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = [320,349,350,351,390,559,560,561,768,869,870,871,1024,1099,1100,1101,1440]

class StudioUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        executable = os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium')
        cls.browser = cls.playwright.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width':1440,'height':1100})
        self.page.set_default_timeout(4000)
        self.errors = []
        self.requests = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        def serve(route):
            self.requests.append(route.request.url)
            path = ROOT / unquote(urlsplit(route.request.url).path).lstrip('/')
            if not path.is_relative_to(ROOT):
                route.abort(); return
            route.fulfill(status=200 if path.is_file() else 404,
                body=path.read_bytes() if path.is_file() else b'',
                content_type='application/javascript' if path.suffix == '.js' else 'image/png' if path.suffix == '.png' else 'text/html',
                headers={'Access-Control-Allow-Origin':'*'})
        self.page.route('https://healthlink-preview.test/**', serve)
        html = (ROOT/'tests/frontend/preview.html').read_text().replace('<html lang="ko">', '<html lang="ko"><base href="https://healthlink-preview.test/tests/frontend/preview.html">')
        self.page.set_content(html)
        self.page.wait_for_function('window.panel && panel._loaded && !panel._loading')

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [])

    def nav(self, tab):
        self.page.locator('#tab-'+tab).click()

    def editor(self):
        self.nav('explorer')
        self.page.locator('#newSensor').click()

    def fill(self, id='new_context'):
        self.page.locator('#cName').fill('새 조합 센서')
        self.page.locator('#cId').fill(id)

    def calls(self, suffix):
        return self.page.evaluate('(suffix) => mock.calls.filter(x => x.type.endsWith(suffix))', suffix)

    def test_module_graph_and_no_external_runtime(self):
        self.assertTrue(any('health-link-panel-modern.js' in x for x in self.requests))
        self.assertTrue(any('health-link-studio-view.js?v=20260913.1' in x for x in self.requests))
        self.assertFalse(any('pairing' in x['type'] or 'token' in x['type'] for x in self.page.evaluate('mock.calls')))
        self.assertEqual(self.page.locator('.hc-hero').count(), 1)
        self.assertNotIn('큰 변화는', self.page.locator('.hc-root').inner_text())

    def test_keyboard_tabs_and_panels(self):
        self.page.locator('#tab-today').focus()
        for key, tab in [('ArrowRight','explorer'),('End','connect'),('Home','today'),('ArrowLeft','connect')]:
            self.page.keyboard.press(key)
            self.assertEqual(self.page.evaluate('panel.shadowRoot.activeElement.id'), 'tab-'+tab)
            self.assertEqual(self.page.locator('[role=tab][tabindex="0"]').count(),1)
            self.assertEqual(self.page.locator('[role=tabpanel]:not([hidden])').get_attribute('id'),'panel-'+tab)
        self.assertEqual(self.page.locator('[role=tab]').count(),4)

    def test_layout_boundary_matrix_and_themes(self):
        for dark in [False, True]:
            self.page.evaluate('(dark) => panel.hass={...hassFixture,themes:{darkMode:dark}}',dark)
            for width in WIDTHS:
                with self.subTest(dark=dark,width=width):
                    self.page.set_viewport_size({'width':width,'height':900})
                    bounds=self.page.locator('.hc-root').evaluate('(e)=>[e.clientWidth,e.scrollWidth]')
                    self.assertLessEqual(bounds[1],bounds[0]+1)
                    primary=self.page.locator('#connectData').evaluate('(e)=>[getComputedStyle(e).backgroundColor,getComputedStyle(e).color]')
                    self.assertEqual(primary,['rgb(37, 99, 235)','rgb(255, 255, 255)'])
        self.page.set_viewport_size({'width':1440,'height':1100})
        self.page.locator('#frame').evaluate('(e)=>{e.style.width="768px"}')
        self.assertEqual(self.page.locator('.hc-grid').evaluate('(e)=>getComputedStyle(e).gridTemplateColumns.split(" ").length'),1)

    def test_search_exposure_filters_and_zero_matches(self):
        self.nav('explorer')
        self.page.locator('#search').fill('heart')
        self.assertEqual(self.page.locator('[data-metric-row]:not([hidden])').count(),1)
        self.page.locator('#exposureFilter').select_option('exposed')
        self.assertTrue(self.page.locator('#noMatches').is_visible())
        self.assertIn('0개 표시',self.page.locator('#filterCount').inner_text())
        self.page.evaluate('panel._load()')
        self.assertEqual(self.page.locator('#search').input_value(),'heart')
        self.assertEqual(self.page.locator('#exposureFilter').input_value(),'exposed')

    def test_modal_focus_scroll_and_dirty_cancel(self):
        self.editor()
        self.assertEqual(self.page.evaluate('panel.shadowRoot.activeElement.id'),'cName')
        self.assertEqual(self.page.locator('.hc-root').evaluate('(e)=>getComputedStyle(e).overflow'),'hidden')
        self.assertNotEqual(self.page.evaluate('document.body.style.overflow'),'hidden')
        for _ in range(18):
            self.page.keyboard.press('Tab')
            self.assertTrue(self.page.evaluate('!!panel.shadowRoot.activeElement.closest("#editor")'))
        self.fill()
        self.page.keyboard.press('Escape')
        self.assertTrue(self.page.locator('#discardPrompt').is_visible())
        self.page.locator('[data-action=keep-editor]').click()
        self.assertEqual(self.page.locator('#cName').input_value(),'새 조합 센서')
        self.page.keyboard.press('Escape')
        self.page.locator('[data-action=discard-editor]').click()
        self.assertFalse(self.page.locator('#editor').is_visible())
        self.assertEqual(self.page.evaluate('panel.shadowRoot.activeElement.id'),'newSensor')
        self.assertEqual(self.page.locator('.hc-root').evaluate('(e)=>getComputedStyle(e).overflow'),'auto')

    def test_modal_backdrop_and_short_height(self):
        self.page.set_viewport_size({'width':900,'height':360})
        self.editor();self.fill()
        self.assertLessEqual(self.page.locator('#saveComposer').bounding_box()['y']+self.page.locator('#saveComposer').bounding_box()['height'],360)
        self.page.mouse.click(10,200)
        self.assertTrue(self.page.locator('#discardPrompt').is_visible())
        self.page.locator('[data-action=discard-editor]').click()
        self.assertFalse(self.page.locator('#editor').is_visible())

    def test_validation_sends_no_command(self):
        self.editor()
        self.page.locator('#saveComposer').click()
        self.assertEqual(self.page.evaluate('panel.shadowRoot.activeElement.id'),'cName')
        self.assertEqual(self.page.locator('#cName').get_attribute('aria-invalid'),'true')
        self.assertEqual(self.calls('/composer/validate'),[])
        self.fill('INVALID ID')
        self.page.locator('#saveComposer').click()
        self.assertEqual(self.page.evaluate('panel.shadowRoot.activeElement.id'),'cId')
        self.assertEqual(self.calls('/composer/save'),[])

    def test_refresh_retains_editor_dom_and_draft(self):
        self.editor();self.fill()
        self.page.evaluate('window.editorNode=panel.shadowRoot.getElementById("cName");panel._load()')
        self.page.wait_for_function('!panel._loading')
        self.assertTrue(self.page.evaluate('editorNode===panel.shadowRoot.getElementById("cName")'))
        self.assertEqual(self.page.locator('#cName').input_value(),'새 조합 센서')
        self.assertTrue(self.page.locator('#editor').is_visible())

    def test_save_failure_keeps_fields_and_local_error(self):
        self.page.evaluate('() => { mock.handlers["health_link/composer/save"]=()=>Promise.reject({code:"test_failure",message:"Offline fixture"}); }')
        self.editor();self.fill()
        self.page.locator('#saveComposer').click()
        self.page.wait_for_function('panel._editor && !panel._editor.busy')
        self.assertTrue(self.page.locator('#editorError [role=alert]').is_visible())
        self.assertEqual(self.page.locator('#cName').input_value(),'새 조합 센서')
        self.assertFalse(self.page.locator('#saveComposer').is_disabled())
        self.assertEqual(self.page.locator('#statusHost [role=alert]').count(),0)

    def test_valid_save_payload_and_single_submission(self):
        self.page.evaluate('mock.delays["health_link/composer/save"]=200')
        self.editor();self.fill()
        self.page.locator('#inputBKind').select_option('ha')
        self.page.locator('#inputBHa').select_option('sensor.room_temperature')
        self.page.locator('#op').select_option('ratio')
        self.page.locator('#unit').fill('%')
        self.page.evaluate('panel._saveEditor();panel._saveEditor()')
        self.page.wait_for_function('panel._editor===null && !panel._loading')
        calls=self.calls('/composer/save');self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['config_entry_id'],'demo-a')
        self.assertEqual(calls[0]['definition']['formula'],'ratio(a,b)')
        self.assertEqual(calls[0]['definition']['inputs']['b'],{'source':'ha','entity_id':'sensor.room_temperature'})
        self.assertIn('실제 센서 반영',self.page.locator('#statusHost').inner_text())

    def test_fresh_duplicate_id_is_not_overwritten(self):
        self.editor();self.fill()
        self.page.evaluate('mock.composers.push({id:"new_context",name:"다른 세션의 센서",version:1})')
        self.page.locator('#saveComposer').click()
        self.page.wait_for_function('!panel._editor.busy')
        self.assertEqual(self.calls('/composer/save'),[])
        self.assertIn('같은 ID',self.page.locator('#editorError').inner_text())

    def test_close_during_validation_does_not_send_save(self):
        self.page.evaluate('mock.delays["health_link/composer/validate"]=200')
        self.editor();self.fill();self.page.locator('#saveComposer').click()
        self.page.keyboard.press('Escape');self.page.locator('[data-action=discard-editor]').click()
        self.page.wait_for_timeout(280)
        self.assertEqual(self.calls('/composer/save'),[])
        self.assertFalse(self.page.locator('#editor').is_visible())

    def test_close_after_submitted_never_reopens(self):
        self.page.evaluate('mock.delays["health_link/composer/save"]=250')
        self.editor();self.fill();self.page.locator('#saveComposer').click()
        self.page.wait_for_function('mock.calls.some(x=>x.type==="health_link/composer/save")')
        self.page.keyboard.press('Escape');self.page.locator('[data-action=discard-editor]').click()
        self.page.wait_for_timeout(320)
        self.assertFalse(self.page.locator('#editor').is_visible())
        self.assertEqual(len(self.calls('/composer/save')),1)

    def test_delete_requires_confirmation_and_handles_failure(self):
        self.nav('explorer');self.page.locator('[data-action=delete]').click()
        self.assertEqual(self.calls('/composer/delete'),[])
        self.page.evaluate('() => { mock.handlers["health_link/composer/delete"]=()=>Promise.reject(new Error("Delete failed")); }')
        self.page.locator('#saveComposer').click()
        self.page.wait_for_function('!panel._editor.busy')
        self.assertTrue(self.page.locator('#editorError [role=alert]').is_visible())
        self.assertTrue(self.page.locator('#editor').is_visible())

    def test_profile_race_does_not_mix_catalogs(self):
        self.page.evaluate('mock.delays["health_link/catalog/list"]=250;panel._load()')
        self.page.locator('#profile').select_option('demo-b')
        self.page.wait_for_timeout(360)
        self.assertEqual(self.page.evaluate('panel._entryId'),'demo-b')
        self.assertEqual(self.page.evaluate('panel._catalog'),[])
        self.assertNotIn('12,480',self.page.locator('.hc-root').inner_text())

    def test_timeline_preserves_zero_and_has_caption(self):
        self.nav('timeline');self.page.locator('#queryForm button[type=submit]').click()
        self.page.wait_for_function('panel._results.timeline?.state==="ready"')
        self.assertIn('0 count',self.page.locator('#queryResult').inner_text())
        self.assertTrue(self.page.locator('#queryResult caption').is_visible())
        self.assertEqual(self.calls('/timeline/query')[0]['hours'],24)

    def test_late_timeline_after_mode_change_ignored(self):
        self.page.evaluate('mock.delays["health_link/timeline/query"]=200')
        self.nav('timeline');self.page.locator('#queryForm button[type=submit]').click()
        self.page.locator('[data-mode=insights]').click();self.page.wait_for_timeout(280)
        self.assertEqual(self.page.locator('#queryResult table').count(),0)
        self.assertEqual(self.page.evaluate('panel._analysis'),'insights')

    def test_partial_insight_success_is_retained(self):
        self.page.evaluate('() => { mock.handlers["health_link/optimizer/observe"]=()=>Promise.reject({code:"timestamp_unavailable",message:"Missing sample time"}); }')
        self.nav('timeline');self.page.locator('[data-mode=insights]').click()
        self.page.locator('#inEntity').select_option('sensor.room_temperature')
        self.page.locator('#queryForm button[type=submit]').click()
        self.page.wait_for_function('panel._results.insights?.state==="ready"')
        text=self.page.locator('#queryResult').inner_text()
        self.assertIn('0.4',text);self.assertIn('측정 시각',text)

    def test_empty_unknown_and_real_zero_are_distinct(self):
        self.page.evaluate('mock.profiles[0].data_confidence=null;mock.profiles[0].recovery_confidence=0;mock.profiles[0].steps_vs_same_time_baseline="unknown";panel._load()')
        self.page.wait_for_function('!panel._loading')
        text=self.page.locator('#panel-today').inner_text()
        self.assertIn('0%',text);self.assertIn('—',text);self.assertNotIn('NaN',text)
        self.page.locator('#profile').select_option('demo-b')
        self.page.wait_for_function('panel._entryId==="demo-b" && !panel._loading')
        self.assertIn('아직 미수신',self.page.locator('#panel-today').inner_text())

    def test_status_failure_keeps_previous_data_but_marks_stale(self):
        self.page.evaluate('mock.handlers["health_link/status"]=()=>Promise.reject(new Error("Offline"));panel._load()')
        self.page.wait_for_function('!panel._loading')
        self.assertIn('12,480',self.page.locator('#panel-today').inner_text())
        self.assertIn('최신이 아닐 수',self.page.locator('#statusHost').inner_text())

    def test_partial_catalog_error_retains_sensor_list(self):
        self.page.evaluate('mock.handlers["health_link/catalog/list"]=()=>Promise.reject(new Error("Catalog error"));panel._load()')
        self.page.wait_for_function('!panel._loading');self.nav('explorer')
        text=self.page.locator('#panel-explorer').inner_text()
        self.assertIn('나의 활동 컨텍스트',text);self.assertIn('갱신하지 못했어요',text)

    def test_sensitive_exposure_failure_is_explained(self):
        self.page.evaluate('() => { mock.handlers["health_link/catalog/expose"]=()=>Promise.reject({code:"sensitive_disabled",message:"Disabled"}); }')
        self.nav('explorer');self.page.locator('[data-action=expose]').nth(1).click()
        self.page.wait_for_function('panel._mutations.size===0')
        self.assertIn('민감 항목',self.page.locator('#statusHost').inner_text())
        self.assertFalse(self.page.locator('[data-action=expose]').nth(1).is_disabled())

    def test_admin_revocation_clears_all_profile_data(self):
        before=len(self.page.evaluate('mock.calls'))
        self.page.evaluate('panel.hass={...hassFixture,user:{is_admin:false}}')
        self.assertIn('관리자만',self.page.locator('.hc-root').inner_text())
        self.assertEqual(self.page.evaluate('panel._profiles'),[])
        self.assertNotIn('예시 프로필 A',self.page.locator('.hc-root').inner_text())
        self.assertEqual(before,len(self.page.evaluate('mock.calls')))

    def test_untrusted_names_are_text_not_html(self):
        self.page.evaluate('mock.catalog[0].display_name="<img src=x onerror=alert(1)>";panel._load()')
        self.page.wait_for_function('!panel._loading');self.nav('explorer')
        self.assertIn('<img src=x',self.page.locator('#catalogList').inner_text())
        self.assertEqual(self.page.locator('#catalogList img').count(),0)

    def test_detach_stops_timer_and_late_updates(self):
        self.page.evaluate('mock.delays["health_link/status"]=200;panel._load();panel.remove()')
        self.page.wait_for_timeout(260)
        self.assertIsNone(self.page.evaluate('panel._refreshTimer'))
        self.assertFalse(self.page.evaluate('panel._active'))
        self.page.evaluate('document.getElementById("frame").append(panel)')
        self.page.wait_for_function('panel._active && !panel._loading')
        self.assertIsNotNone(self.page.evaluate('panel._refreshTimer'))

    def test_touch_targets_and_form_field_dimensions(self):
        for tab in ['today','explorer','timeline','connect']:
            self.nav(tab)
            sizes=self.page.locator('.hc-root button:visible,.hl-link:visible,.hl-settings:visible').evaluate_all('(nodes)=>nodes.map(e=>({label:e.getAttribute("aria-label")||e.textContent,w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}))')
            for item in sizes:
                self.assertGreaterEqual(item['w'],43.9,item)
                self.assertGreaterEqual(item['h'],43.9,item)
        self.editor()
        for item in self.page.locator('#editor input:visible,#editor select:visible').evaluate_all('(nodes)=>nodes.map(e=>({height:e.getBoundingClientRect().height,font:getComputedStyle(e).fontSize}))'):
            self.assertGreaterEqual(item['height'],46)
            self.assertEqual(item['font'],'16px')

if __name__ == '__main__':
    unittest.main(verbosity=2)
