/** HealthLink Studio views. API operations live in health-link-panel-modern.js.
 * Design system 1.0.0, Copyright (c) 2026 1bobby-git, MIT (repository LICENSE).
 */
import { icon } from './health-link-studio-icons.js?v=20260914.3';
import { metricName, metricSearchText } from './health-link-studio-labels.js?v=20260914.3';
import { ecgHelpView } from './health-link-studio-help.js?v=20260914.3';

export const TABS = [
  ['today', '한눈에', 'Overview'], ['explorer', '건강 데이터', 'Health data'],
  ['timeline', '기록·분석', 'History & insights'], ['connect', '연결', 'Connection'],
];
export const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const numeric = value => value === null || value === undefined || value === '' || typeof value === 'boolean' || !Number.isFinite(Number(value)) ? null : Number(value);
const button = (action, text, cls = '', extra = '') => `<button type="button" data-action="${action}" class="${cls}" ${extra}>${text}</button>`;
const link = (text, href = '/config/integrations/integration/health_link', cls = 'hl-link') => `<a class="${cls}" href="${href}">${text}</a>`;
const badge = (text, state = '') => `<span class="hc-badge" data-state="${state}">${esc(text)}</span>`;
const empty = (title, copy = '', action = '') => `<div class="hc-empty"><strong>${esc(title)}</strong><p>${esc(copy)}</p>${action}</div>`;
const row = (label, value, detail = '') => `<li class="hc-list-row"><div><strong>${esc(label)}</strong>${detail ? `<small>${esc(detail)}</small>` : ''}</div><span class="hl-value">${esc(value)}</span></li>`;
const card = (title, body, aside = '') => `<section class="hc-card"><div class="hc-card-head"><h2>${esc(title)}</h2>${aside}</div><div class="hc-card-body">${body}</div></section>`;
const options = (items, key, name) => items.map(x => `<option value="${esc(x[key])}">${esc(x[name] || x[key])}</option>`).join('');
export const metricOptions = ui => options(ui._catalog.filter(x => numeric(x.sample_count) > 0).map(x => ({...x,display_name:metricName(ui,x)})), 'type_id', 'display_name');
export function entityOptions(ui) {
  const entries = Object.entries(ui._hass?.states || {}).filter(([, s]) => numeric(s.state) !== null);
  return (entries.length > 2500 ? `<option disabled>${ui._t(`전체 ${entries.length}개 중 2,500개 표시`,`Showing 2,500 of ${entries.length} numeric sensors`)}</option>` : '') + entries.slice(0, 2500).map(([id, s]) => `<option value="${esc(id)}">${esc(s.attributes?.friendly_name || id)} · ${esc(id)}</option>`).join('');
}
export function errorView(ui, error, title) {
  const t = ui._t.bind(ui);
  const messages = {
    unauthorized:t('관리자 계정으로 열어 주세요.','Open Studio with an administrator account.'),
    sensitive_disabled:t('민감 항목의 센서 노출은 HealthLink 설정에서 먼저 허용해 주세요.','Allow sensitive metric exposure in HealthLink settings first.'),
    timestamp_unavailable:t('이 데이터에는 원래 측정 시각이 없어 시간대별 연관 분석을 제공할 수 없어요.','This source has no original sample timestamps, so time-aligned associations are unavailable.'),
    profile_not_found:t('이 프로필을 사용할 수 없어요. 연결 설정을 확인해 주세요.','This profile is unavailable. Check its connection settings.'),
    duplicate_id:t('같은 ID의 센서가 이미 있어요. 다른 ID를 사용해 주세요.','A sensor already uses this ID. Choose another ID.'),
  };
  return `<div class="hc-alert" role="alert"><strong>${esc(title || t('작업을 완료하지 못했어요.','The operation could not be completed.'))}</strong><p>${esc(messages[error?.code] || t('입력과 연결 상태를 확인한 뒤 다시 시도해 주세요.','Check your input and connection, then retry.'))}</p><details><summary>${t('오류 상세','Error details')}</summary><p>${esc([error?.code, error?.message || String(error)].filter(Boolean).join(' · '))}</p></details></div>`;
}
export function headerView(ui) {
  const t = ui._t.bind(ui);
  const disconnected = ui._hass?.connected === false || ui._hass?.connection?.connected === false;
  const connected = ui._hass?.connected === true || ui._hass?.connection?.connected === true;
  const state = disconnected || ui._errors.status ? 'error' : connected ? 'online' : '';
  const status = disconnected ? t('HA 연결 끊김','HA offline') : ui._errors.status ? t('상태 확인 실패','Status check failed') : connected ? t('HA 연결됨','HA connected') : t('연결 확인 중','Checking connection');
  const version = ui._panel?.config?.version;
  const picker = ui._profiles.length > 1 ? `<div class="hl-profile-row"><div class="hc-entry"><label for="profile">${t('건강 프로필','Health profile')}</label><select id="profile">${ui._profiles.map(x => `<option value="${esc(x.config_entry_id)}" ${x.config_entry_id === ui._entryId ? 'selected' : ''}>${esc(x.title)}${x.available === false ? t(' · 확인 필요',' · attention needed') : ''}</option>`).join('')}</select></div></div>` : '';
  return `<header class="hc-header"><div class="hc-wrap"><div class="hc-header-row">
    ${button('overview', `<img id="healthLinkLogo" src="${esc(ui._logoUrl)}" width="600" height="200" alt="HealthLink"><span id="logoFallback" hidden>HealthLink</span>`, 'hc-brand', `aria-label="${t('HealthLink 한눈에','HealthLink overview')}" data-logo-surface="light"`)}
    <div class="hc-header-tools"><span class="hc-connection" data-state="${state}">${status}</span>
    ${version ? `<span class="hl-version">v${esc(version)}</span>` : ''}
    ${button('refresh', icon('refresh'), 'hc-icon-button hc-ghost', `id="refreshProfiles" aria-label="${t('상태 새로고침','Refresh status')}" title="${t('상태 새로고침','Refresh status')}" ${ui._loading ? 'disabled aria-busy="true"' : ''}`)}
    ${link(icon('settings'), '/config/integrations/integration/health_link', 'hl-settings')}</div></div>${picker}
    <nav class="hc-tabs" role="tablist" aria-label="HealthLink Studio">${TABS.map(([id, ko, en]) => `<button type="button" id="tab-${id}" role="tab" data-tab="${id}" aria-controls="panel-${id}" aria-selected="${ui._tab === id}" tabindex="${ui._tab === id ? '0' : '-1'}">${t(ko, en)}</button>`).join('')}</nav></div></header>`;
}
function heading(title, copy, action = '') {
  return `<div class="hc-page-heading"><div><p class="hl-eyebrow" aria-hidden="true">HEALTH &amp; HOME</p><h1 tabindex="-1" id="pageTitle">${esc(title)}</h1><p>${esc(copy)}</p></div>${action}</div>`;
}
function overview(ui, p) {
  const t = ui._t.bind(ui), n = ui._number.bind(ui), stamp = ui._date.bind(ui);
  const goals = Object.entries(p.goal_progress || {}), labels = {steps:t('걸음 수','Steps'),exercise_minutes:t('운동 시간','Exercise'),active_energy:t('활동 에너지','Active energy'),water_ml:t('물 기록','Recorded water'),sleep_minutes:t('수면','Sleep')};
  const units = {steps:t('걸음','steps'),exercise_minutes:t('분','min'),active_energy:'kcal',water_ml:'mL',sleep_minutes:t('분','min')};
  const goalRows = goals.map(([key, item]) => {
    const pct = numeric(item.progress), label = labels[key] || key;
    return `<li class="hc-list-row hl-goal"><div><strong>${esc(label)}</strong><small>${esc(n(item.current))} / ${esc(n(item.target))} ${esc(units[key] || '')}</small></div><span class="hl-value">${pct === null ? badge(t('미수신','Not received'), 'pending') : `${esc(n(Math.round(pct)))}<small>%</small>`}</span>${pct === null ? '' : `<progress class="hl-progress" max="100" value="${Math.min(100, Math.max(0, pct))}" aria-label="${esc(label)} ${t('목표 진행률','goal progress')}">${esc(n(pct))}%</progress>`}</li>`;
  }).join('');
  const received = numeric(p.sample_count) > 0;
  const focus = {none:t('지정된 포커스 없음','No priority focus'),...labels,recovery_context:t('회복 컨텍스트','Recovery context')}[p.daily_focus] || p.daily_focus || '—';
  const recovery = {above_baseline:t('개인 기준선보다 높음','Above personal baseline'),within_baseline:t('개인 기준선 범위 안','Within personal baseline'),below_baseline:t('개인 기준선보다 낮음','Below personal baseline'),insufficient_data:t('데이터가 더 필요해요','More data needed')}[p.recovery_context] || t('확인할 데이터가 없어요','No data to assess');
  return heading(t('건강과 일상, 한눈에','Your health, in context'), t('받아온 건강 기록과 직접 정한 목표를 확인하세요.','Review the records you received and the goals you set.'), button('connection', `${icon('plus')}${t('데이터 연결','Connect data')}`, 'hc-primary', 'id="connectData"')) +
    `<section class="hc-hero" aria-labelledby="receiptTitle"><div class="hc-hero-main"><div><p class="hc-hero-kicker">${t('나의 건강 기록','MY HEALTH RECORDS')}</p><h2 id="receiptTitle">${received ? t('받아온 건강 기록','Your received records') : t('아직 미수신이에요','No records received')}</h2><span class="hc-hero-status" data-state="${received ? '' : 'pending'}">${received ? t('저장된 기록 기준 · 실시간 상태가 아니에요','Stored records · not a live status') : t('Apple 건강 항목을 연결해 주세요','Connect your Apple Health metrics')}</span></div>
    <div class="hl-hero-metrics"><div class="hc-metric"><strong>${esc(n(p.type_count))}</strong><span>${t('건강 항목','health types')}</span></div><div class="hc-metric"><strong>${esc(n(p.sample_count))}</strong><span>${t('저장 기록','stored records')}</span></div></div></div>
    <div class="hc-hero-foot"><span>${t('최근 수신','Last received')}<strong class="hl-inline">${p.last_sync ? esc(stamp(p.last_sync)) : t('미수신','Not received')}</strong></span>${button('connection', `${t('수신 상태 보기','View collection status')}${icon('arrow')}`)}</div></section>
    ${p.companion_needs_selection ? `<div class="hc-alert hl-selection" data-state="info"><strong>${t('이 프로필에서 사용할 Apple 기기를 선택해 주세요.','Choose the Apple device for this profile.')}</strong><p>${t('서로 다른 사람의 기록이 섞이지 않도록 기기 선택이 필요해요.','A device selection is needed to keep each person’s records separate.')}</p>${link(t('연결 설정 열기','Open connection settings'))}</div>` : ''}
    <div class="hc-grid"><div class="hl-stack">${card(t('내가 정한 목표','My goals'), goalRows ? `<ul class="hc-list">${goalRows}</ul>` : empty(t('아직 설정한 목표가 없어요.','No goals set yet.'), t('걸음·수면 등 원하는 생활 목표만 직접 설정하세요.','Set only the lifestyle goals you want, such as steps or sleep.'), link(t('목표 설정하기','Set goals'))), link(t('목표 관리','Manage goals')))}
    ${card(t('개인 기준선과 비교','Personal baseline comparison'), `<ul class="hc-list">${row(t('오늘의 포커스','Today’s focus'), focus)}${row(t('개인 목표 상태','Personal goal status'), ({not_configured:t('목표 미설정','No goals configured'),all_reached:t('설정한 목표 달성','Configured goals reached'),in_progress:t('진행 중','In progress'),waiting_for_data:t('데이터 대기','Waiting for data')})[p.daily_goal_context] || '—')}${row(t('회복 컨텍스트','Recovery context'), recovery)}${row(t('회복 신뢰도','Recovery confidence'), numeric(p.recovery_confidence) === null ? '—' : n(p.recovery_confidence) + '%')}${row(t('같은 시간대 평소 대비 걸음','Steps vs same-time baseline'), numeric(p.steps_vs_same_time_baseline) === null ? '—' : n(p.steps_vs_same_time_baseline) + '%')}${row(t('데이터 신뢰도','Data confidence'), numeric(p.data_confidence) === null ? '—' : n(p.data_confidence) + '%', t('HealthLink가 반환한 분석 값이에요.','Analysis value returned by HealthLink.'))}</ul>`)}
    </div><aside class="hl-stack"><section class="hc-promo hl-promo"><span class="hl-promo-icon">${icon('pulse')}</span><h2>${t('건강 기록을<br>집의 변화와 함께','Health records.<br>Home context.')}</h2><p>${t('받아온 항목을 확인하고, 필요한 데이터만 HA 센서로 만들어 보세요.','Review received metrics and create only the HA sensors you need.')}</p>${button('data', `${t('건강 데이터 보기','View health data')}${icon('arrow')}`, 'hc-secondary')}</section>
    <div class="hl-privacy">${icon('shield')}<div><strong>${t('내 기록은 필요한 만큼만','Only the data you need')}</strong><p>${t('이 화면은 연결한 프로필의 수신 데이터만 표시해요. 의료적 정상·위험을 판단하지 않아요.','This screen shows received data for the selected profile. It does not diagnose health or risk.')}</p></div></div></aside></div>`;
}
function explorer(ui) {
  const t = ui._t.bind(ui), n = ui._number.bind(ui);
  const catalogError = ui._errors.catalog ? errorView(ui, ui._errors.catalog, t('건강 항목을 갱신하지 못했어요.','Health metrics could not be refreshed.')) : '';
  const rows = ui._catalog.map((x, i) => {
    const key = `expose:${ui._entryId}:${x.type_id}`, busy = ui._mutations.has(key);
    return `<li class="hc-list-row hl-data-row" data-metric-row data-name="${esc(metricSearchText(ui,x))}" data-exposed="${Boolean(x.exposed)}"><div><strong>${esc(metricName(ui,x))}</strong><small class="hl-id">${esc(x.type_id)}</small><small>${esc(n(x.sample_count))} ${t('개 기록','records')} · ${t('최근 데이터','Last data')} ${esc(ui._date(x.last_sample))}</small></div><div class="hl-row-actions">${badge(x.exposed ? t('HA 노출 설정됨','HA exposure enabled') : t('보관 중','Stored'), x.exposed ? 'success' : '')}${button('expose', busy ? t('저장 중…','Saving…') : x.exposed ? t('센서 숨기기','Hide sensor') : t('센서 생성','Create sensor'), 'hc-secondary', `data-index="${i}" ${busy ? 'disabled aria-busy="true"' : ''} aria-label="${esc(metricName(ui,x))} ${x.exposed ? t('센서 숨기기','hide sensor') : t('센서 생성','create sensor')}"`)}</div></li>`;
  }).join('');
  const composers = ui._composers.map(c => `<li class="hc-list-row"><div><strong>${esc(c.name)}</strong><small>${esc(c.id)} · v${esc(c.version)}</small></div>${button('delete', t('삭제','Delete'), 'hc-danger', `data-id="${esc(c.id)}" aria-label="${esc(c.name)} ${t('센서 삭제','delete sensor')}"`)}</li>`).join('');
  return heading(t('내 건강 데이터','My health data'), t('실제로 받은 항목을 확인하고, 필요한 센서만 생성하세요.','Review the metrics actually received and create only the sensors you need.'), `<div class="hl-heading-actions">${button('ecg-guide', t('심전도 가져오기 안내','ECG import guide'), 'hc-secondary')}${button('create', `${icon('plus')}${t('센서 만들기','Create sensor')}`, 'hc-primary', `id="newSensor" ${!metricOptions(ui) || ui._errors.composers ? 'disabled' : ''}`)}</div>`) +
    (!metricOptions(ui) ? `<p class="hc-note hl-before">${t('센서 만들기는 건강 기록을 받은 뒤 사용할 수 있어요.','Sensor creation becomes available after health records arrive.')}</p>` : '') + catalogError +
    `<div class="hc-toolbar"><div class="hl-search"><label for="search">${t('건강 항목 검색','Search health metrics')}</label><input id="search" type="search" placeholder="${t('이름, HealthKit ID, 영역','Name, HealthKit ID, domain')}" aria-controls="catalogList"></div><div class="hl-filter"><label for="exposureFilter">${t('표시 범위','Show')}</label><select id="exposureFilter"><option value="all">${t('전체 항목','All metrics')}</option><option value="exposed">${t('HA 노출 설정됨','HA exposure enabled')}</option><option value="stored">${t('보관 중','Stored only')}</option></select></div></div>
    ${card(t('받아온 건강 항목','Received metrics'), rows ? `<ul class="hc-list" id="catalogList">${rows}</ul><div id="noMatches" hidden>${empty(t('검색 결과가 없어요.','No matching metrics.'), t('검색어나 표시 범위를 바꿔 주세요.','Change the search or filter.'))}</div>` : empty(ui._errors.catalog ? t('항목 조회 실패','Metric lookup failed') : t('아직 받은 건강 항목이 없어요.','No health metrics received yet.'), t('연결 탭에서 데이터 수집 방법을 확인하세요.','Check the Connection tab to set up data collection.'), button('connection', t('연결 안내 보기','View connection guide'), 'hc-secondary')), `<span id="filterCount" class="hl-count" role="status"></span>`)}
    <div class="hl-section">${ui._errors.composers ? errorView(ui, ui._errors.composers, t('만든 센서 목록을 갱신하지 못했어요.','Custom sensors could not be refreshed.')) : ''}${card(t('내가 만든 조합 센서','My composed sensors'), composers ? `<ul class="hc-list">${composers}</ul>` : empty(ui._errors.composers ? t('센서 목록 조회 실패','Sensor list lookup failed') : t('아직 만든 센서가 없어요.','No composed sensors yet.'), t('건강 항목과 집 센서를 코드 없이 조합할 수 있어요.','Combine health metrics and home sensors without writing code.')))}</div>`;
}
function field(id, label, content, hint = '') {
  return `<div class="hc-field"><label for="${id}">${label}</label>${content}${hint ? `<p class="hc-hint" id="${id}-hint">${hint}</p>` : ''}<p class="hc-error" id="${id}-error" hidden></p></div>`;
}
function timeline(ui) {
  const t = ui._t.bind(ui), metrics = metricOptions(ui), entities = entityOptions(ui), insights = ui._analysis === 'insights';
  const form = insights ? `${field('inMetric', t('건강 항목','Health metric'), `<select id="inMetric" required>${metrics}</select>`)}${field('inEntity', t('집 환경 센서','Home/environment sensor'), `<select id="inEntity" required><option value="">${t('센서를 선택하세요','Choose a sensor')}</option>${entities}</select>`)}${field('inDays', t('분석 기간','Analysis window'), `<select id="inDays"><option value="30">30${t('일',' days')}</option><option value="60" selected>60${t('일',' days')}</option><option value="90">90${t('일',' days')}</option><option value="180">180${t('일',' days')}</option></select>`)}${field('inGoal', t('비교할 값의 방향','Preferred outcome direction'), `<select id="inGoal"><option value="high">${t('높은 값 기준','Higher values')}</option><option value="low">${t('낮은 값 기준','Lower values')}</option></select>`)}` : `${field('tlMetric', t('건강 항목','Health metric'), `<select id="tlMetric" required>${metrics}</select>`)}${field('tlEntity', t('함께 볼 집 센서','Home sensor to compare'), `<select id="tlEntity"><option value="">${t('선택 안 함','None')}</option>${entities}</select>`)}${field('tlHours', t('조회 기간','Time window'), `<select id="tlHours"><option value="24">24${t('시간',' hours')}</option><option value="168">7${t('일',' days')}</option><option value="720">30${t('일',' days')}</option></select>`)}`;
  const key = insights ? 'insights' : 'timeline', busy = ui._results[key]?.state === 'loading';
  return heading(t('기록으로 이해하는 일상','Understand your daily patterns'), t('건강 기록과 집의 변화를 같은 기간으로 비교하세요.','Compare health records and home changes over the same period.')) +
    `<div class="hl-modes" role="group" aria-label="${t('조회 방식','View mode')}">${button('mode', t('타임라인','Timeline'), '', `data-mode="timeline" aria-pressed="${!insights}"`)}${button('mode', t('연관 분석','Associations'), '', `data-mode="insights" aria-pressed="${insights}"`)}</div>
    <section class="hc-card"><div class="hc-card-head"><h2>${insights ? t('건강과 집의 관계 찾기','Find health and home relationships') : t('건강 + 집 타임라인','Health + home timeline')}</h2></div><div class="hl-query-body"><form id="queryForm" novalidate><div class="hl-fields">${form}</div><p class="hc-note hl-before">${insights ? t('함께 변한 경향을 확인하는 관측 분석이에요. 원인이나 의료적 효과를 뜻하지 않으며, 측정 시각이 없는 데이터는 분석할 수 없어요.','These are observed associations, not causes or medical effects. Sources without sample timestamps cannot be analyzed.') : t('집 센서는 선택 사항이에요. 조회 결과는 아래에 표시됩니다.','The home sensor is optional. Query results appear below.')}</p><div id="queryError"></div><button class="hc-primary" type="submit" ${!metrics || busy ? 'disabled' : ''} ${busy ? 'aria-busy="true"' : ''}>${busy ? t('조회 중…','Loading…') : insights ? t('연관 분석하기','Analyze associations') : t('기록 조회','Show records')}</button>${!metrics ? `<p class="hc-hint">${t('조회하려면 먼저 건강 기록을 받아야 해요.','Receive health records before running a query.')}</p>` : ''}</form></div></section>
    <div class="hl-section" id="queryResult">${resultView(ui, key)}</div>`;
}
export function resultView(ui, key) {
  const t = ui._t.bind(ui), result = ui._results[key];
  if (!result) return empty(t('조회할 항목과 기간을 선택하세요.','Choose a metric and time window.'), t('조회 버튼을 누르면 실제 기록을 가져옵니다.','Use the query button to fetch actual records.'));
  if (result.state === 'loading') return `<div class="hc-empty" role="status">${t('실제 기록을 불러오고 있어요…','Loading your records…')}</div>`;
  if (result.state === 'error') return errorView(ui, result.error);
  if (key === 'timeline') {
    const data = result.data, events = data.events || [], shown = events.slice(-300).reverse();
    if (!shown.length) return empty(t('선택한 기간에 기록이 없어요.','No records in the selected window.'), t('항목이나 조회 기간을 바꿔 보세요.','Try another metric or time window.'));
    return `<section class="hc-card hl-query-body"><div class="hc-table-scroll" tabindex="0" role="region" aria-label="${t('건강과 집 기록 표','Health and home records table')}"><table class="hc-table"><caption>${t('응답 기록','Returned records')} ${esc(ui._number(events.length))}${t('개 중 최근',' · latest')} ${shown.length}${t('개 표시',' shown')}<br>${esc(ui._date(data.start))} ~ ${esc(ui._date(data.end))}</caption><thead><tr>${[t('시간','Time'),t('출처','Source'),t('항목','Metric'),t('값','Value')].map(x => `<th scope="col">${x}</th>`).join('')}</tr></thead><tbody>${shown.map(x => `<tr><td>${esc(ui._date(x.time))}</td><td>${x.source === 'healthkit' ? 'HealthKit' : 'Home Assistant'}</td><th scope="row">${esc(x.source === 'healthkit' ? metricName(ui, ui._catalog.find(m => m.type_id === x.id) || {type_id:x.id}) : ui._hass?.states?.[x.id]?.attributes?.friendly_name || x.id)}<small>${esc(x.id)}</small></th><td>${esc(x.value ?? '—')} ${esc(x.unit || '')}</td></tr>`).join('')}</tbody></table></div></section>`;
  }
  const [corr, opt] = result.data;
  const parts = [corr.status === 'fulfilled' ? card(t('관측된 연관성','Observed association'), `<ul class="hc-list">${row(t('비교 가능한 샘플','Matched samples'), ui._number(corr.value.pairs))}${row(t('상관계수','Correlation'), ui._number(corr.value.correlation))}${row(t('연관 강도','Association strength'), ({strong:t('강함','Strong'),moderate:t('보통','Moderate'),weak:t('약함','Weak'),insufficient_data:t('데이터 부족','Insufficient data'),none:t('뚜렷하지 않음','No clear association')})[corr.value.strength] || corr.value.strength || '—')}</ul>`) : errorView(ui, corr.reason, t('상관 분석 실패','Correlation query failed')),
    opt.status === 'fulfilled' ? card(t('과거 관측 범위','Previously observed range'), `<ul class="hc-list">${row(t('조건에 해당하는 환경 범위','Environment range for the selected outcome'), opt.value.preferred_observed_range ? `${opt.value.preferred_observed_range.low} ~ ${opt.value.preferred_observed_range.high}` : '—')}</ul><p class="hc-note hl-before">${t('권장 설정값이 아니며 자동 제어 기준으로 단독 사용하지 마세요.','Not a recommended setting or a standalone trigger for automatic control.')}</p>`) : errorView(ui, opt.reason, t('관측 범위 조회 실패','Observed range query failed'))];
  return `<div class="hl-stack">${parts.join('')}</div>`;
}
function connection(ui, p) {
  const t = ui._t.bind(ui), state = p.companion_needs_selection ? t('Apple 기기 선택 필요','Choose an Apple device') : p.companion_active ? t('자동 수집 사용 중','Automatic collection enabled') : t('자동 수집 비활성','Automatic collection inactive');
  const mode = {auto:t('자동','Automatic'),companion:'Home Assistant Companion',bridge:t('브리지','Bridge'),both:t('Companion + 브리지','Companion + Bridge')}[p.source_mode] || p.source_mode || '—';
  return heading(t('연결과 수신 상태','Connection & collection'), t('프로필과 Apple 기기 설정, 마지막 수신 시각을 확인하세요.','Check the profile, Apple device settings and last received time.'), link(t('연결 설정 열기','Open connection settings'), undefined, 'hl-button hc-primary')) +
    `<div class="hc-grid hl-no-top"><div class="hl-stack">${card(t('이 프로필의 수집 상태','Collection for this profile'), `<ul class="hc-list">${row(t('수집 방식','Collection mode'),mode)}${row(t('Companion 수집','Companion collection'),state,t('수집 활성화는 기기의 실시간 연결을 뜻하지 않아요.','Enabled collection does not indicate live device connectivity.'))}${row(t('연결한 Apple 기기','Selected Apple devices'),ui._number(p.companion_device_count))}${row(t('수집 소스 센서','Source sensors'),ui._number(p.companion_sensor_count))}${row(t('최근 수신','Last received'),p.last_sync ? ui._date(p.last_sync) : t('미수신','Not received'))}</ul>`)}
    <section class="hc-card"><div class="hc-card-head"><h2>${t('데이터 연결 방법','How to connect data')}</h2></div><ol class="hl-steps"><li><strong>${t('공식 Home Assistant 앱 열기','Open the official Home Assistant app')}</strong><p>${t('별도의 HealthLink iOS 앱은 필요하지 않아요.','A separate HealthLink iOS app is not required.')}</p></li><li><strong>${t('공유할 Apple 건강 센서 켜기','Enable the Apple Health sensors to share')}</strong><p>${t('앱 설정 → 센서 → Apple 건강 센서(Labs)에서 원하는 항목을 선택하세요.','In app settings → Sensors → Apple Health Sensors (Labs), choose the metrics to share.')}</p></li><li><strong>${t('내 프로필에 맞는 Apple 기기 선택','Select this person’s Apple device')}</strong><p>${t('여러 사람의 건강 기록이 섞이지 않도록, 같은 사람의 기기만 연결하세요.','Connect only devices belonging to the same person to avoid mixing household records.')}</p>${link(t('프로필 설정 열기','Open profile settings'))}</li></ol></section></div>
    <aside class="hl-stack"><section class="hc-promo hl-promo"><h2>${t('기록 가져오기','Import records')}</h2><p>${t('ECG·Apple 건강 원본 가져오기는 기존 HA 통합 설정에서 진행해요.','Import ECG and Apple Health exports in the existing HA integration settings.')}</p>${link(t('가져오기 설정 열기','Open import settings'))}</section><div class="hl-privacy">${icon('shield')}<p>${t('민감 항목 노출·자동 제어·건강 데이터 쓰기 권한은 이 화면에서 자동으로 변경하지 않아요.','This screen never automatically changes sensitive exposure, automatic control or health write permissions.')}</p></div></aside></div>` + ecgHelpView(ui);
}
export function bodyView(ui) {
  const t = ui._t.bind(ui), p = ui._profile();
  if (ui._hass?.user?.is_admin === false) return empty(t('관리자만 사용할 수 있어요.','Administrator access required.'), t('건강 데이터 보호를 위해 관리자 계정으로 열어 주세요.','Use an administrator account to protect health data.'));
  if (!ui._loaded && ui._loading) return `<div class="hc-empty" role="status">${t('프로필과 건강 기록을 확인하고 있어요…','Checking profiles and health records…')}</div>`;
  if (!p) return ui._errors.status ? empty(t('프로필 상태를 확인하지 못했어요.','Profile status is unavailable.'), t('상단 새로고침으로 다시 확인해 주세요.','Use Refresh to check again.')) : heading(t('HealthLink 시작하기','Get started with HealthLink'), t('건강 기록을 받을 프로필을 먼저 추가하세요.','Add a profile to receive your health records.'), link(t('프로필 추가','Add profile'), '/config/integrations/dashboard/add?domain=health_link', 'hl-button hc-primary'));
  if (p.available === false) return heading(p.title, t('이 프로필은 연결이나 설정 확인이 필요해요. 다른 사람의 데이터는 표시하지 않아요.','This profile needs a connection or settings check. Another person’s data is never substituted.')) + card(t('프로필 확인 필요','Profile needs attention'), empty(p.entry_state || t('연결 대기','Waiting for connection'), '', link(t('HealthLink 설정 열기','Open HealthLink settings'))));
  if (ui._loading && !ui._loaded) return empty(t('불러오는 중…','Loading…'));
  return ui._tab === 'today' ? overview(ui, p) : ui._tab === 'explorer' ? explorer(ui) : ui._tab === 'timeline' ? timeline(ui) : connection(ui, p);
}
export function editorView(ui) {
  const t = ui._t.bind(ui), editor = ui._editor;
  const close = button('close-editor', icon('close'), 'hc-icon-button hc-ghost', `aria-label="${t('패널 닫기','Close panel')}"`);
  const cancel = button('close-editor', t('취소','Cancel'));
  const confirm = `<div id="discardPrompt" class="hc-alert" hidden><p id="discardCopy"></p><div class="hl-confirm-actions">${button('keep-editor', t('계속 작성','Keep editing'), 'hc-secondary')}${button('discard-editor', t('닫기','Close'), 'hc-danger')}</div></div>`;
  if (editor.kind === 'delete') return `<form class="hc-sheet" id="deleteForm"><div class="hc-sheet-head"><h2 id="editorTitle">${t('이 센서를 삭제할까요?','Delete this sensor?')}</h2>${close}</div><div class="hc-sheet-body"><p><strong>${esc(editor.name)}</strong></p><p class="hc-note">${esc(editor.id)}</p><p>${t('조합 센서 설정을 삭제합니다. 이 센서를 참조하는 자동화도 확인해 주세요.','Deletes the composed sensor definition. Check automations that reference it.')}</p><div id="editorError"></div></div><div class="hc-sheet-foot">${confirm}<p id="draftState" class="hc-draft"></p><div class="hc-sheet-actions">${cancel}<button type="submit" id="saveComposer" class="hc-danger">${t('이 센서 삭제','Delete this sensor')}</button></div></div></form>`;
  const metrics = metricOptions(ui), entities = entityOptions(ui), hint = t('영문 소문자·숫자·밑줄·하이픈, 최대 64자. 이미 사용 중인 ID는 선택할 수 없어요.','Lowercase letters, numbers, _ or -, up to 64 characters. Choose an unused ID.');
  return `<form class="hc-sheet" id="composeForm" novalidate><div class="hc-sheet-head"><h2 id="editorTitle">${t('센서 만들기','Create sensor')}</h2>${close}</div><div class="hc-sheet-body"><p class="hl-editor-intro">${t('건강 항목과 집 센서를 조합해 새로운 HA 센서를 만들어요.','Combine health metrics and home sensors into a new HA sensor.')}<br><strong>${esc(ui._profile()?.title)}</strong></p><div id="editorError"></div><fieldset id="editorFields" class="hl-fieldset">
    ${field('cName', t('센서 이름','Sensor name'), `<input id="cName" required maxlength="96" autocomplete="off" aria-describedby="cName-hint cName-error" placeholder="${t('예: 나의 활동 컨텍스트','e.g. My activity context')}">`, t('목록에서 알아보기 쉬운 이름을 입력하세요.','Enter a name you can recognize in the list.'))}
    ${field('cId', t('센서 ID','Sensor ID'), `<input id="cId" required maxlength="64" pattern="[a-z0-9_\\-]{1,64}" autocomplete="off" autocapitalize="none" spellcheck="false" aria-describedby="cId-hint cId-error" placeholder="my_health_context">`, hint)}
    ${field('inputA', t('A · 기준 건강 항목','A · Health metric'), `<select id="inputA" required aria-describedby="inputA-error">${metrics}</select>`)}
    ${field('inputBKind', t('B · 함께 사용할 데이터','B · Data to combine'), `<select id="inputBKind"><option value="none">${t('사용하지 않음 · A 값 그대로','None · use A only')}</option><option value="ha">Home Assistant</option><option value="healthkit">HealthKit</option></select>`)}
    <div id="haField" hidden>${field('inputBHa', 'B · Home Assistant', `<select id="inputBHa" aria-describedby="inputBHa-error"><option value="">${t('센서를 선택하세요','Choose a sensor')}</option>${entities}</select>`)}</div>
    <div id="hkField" hidden>${field('inputBHk', 'B · HealthKit', `<select id="inputBHk" aria-describedby="inputBHk-error">${metrics}</select>`)}</div>
    ${field('op', t('계산 방식','Calculation'), `<select id="op" disabled><option value="a">${t('A 값 그대로','A only')}</option><option value="avg">${t('평균 · (A + B) ÷ 2','Average · (A + B) ÷ 2')}</option><option value="add">A + B</option><option value="sub">A − B</option><option value="ratio">A ÷ B</option><option value="mul">A × B</option></select>`)}
    ${field('unit', t('단위 (선택)','Unit (optional)'), '<input id="unit" autocomplete="off" placeholder="%, kcal, …">')}
    </fieldset></div><div class="hc-sheet-foot">${confirm}<p class="hc-draft" id="draftState">${t('아직 저장하지 않았어요.','Not saved yet.')}</p><div class="hc-sheet-actions">${cancel}<button type="submit" class="hc-primary" id="saveComposer">${t('센서 만들기','Create sensor')}</button></div></div></form>`;
}

export const STYLES = String.raw`
/* HA Component UI v1.0.0 — Wallet baseline v1.11.0.
 * Presentation-only, scoped under .hc-root. No remote fonts or global HA overrides.
 * Recommended profile: preserves visual anchors, strengthens field boundaries,
 * uses >=44px controls and >=12px supporting copy. See guide for source differences.
 */
.hc-root {
  --hc-bg:#f7f8fa; --hc-surface:#fff; --hc-ink:#191f28; --hc-muted:#667182;
  --hc-line:#e9ecf1; --hc-soft:#f1f3f6; --hc-blue:#2563eb; --hc-blue-soft:#edf3ff;
  --hc-green:#147455; --hc-green-soft:#e9f6ef; --hc-danger:#b4233d;
  --hc-danger-soft:#fff0f2; --hc-field:#8490a2; --hc-dim:#677386;
  --hc-shadow:0 8px 32px #19243b05;
  --hc-primary-bg:#2563eb; --hc-primary-ink:#fff;
  --hc-warning:#805500; --hc-warning-soft:#fff4dc;
  --hc-hero-bg:radial-gradient(ellipse at 95% -20%,#314774 0,transparent 63%),#182237;
  --hc-font:-apple-system,BlinkMacSystemFont,"Pretendard","Noto Sans CJK KR","Malgun Gothic",sans-serif;
  --hc-radius-hero:24px; --hc-radius-card:19px; --hc-radius-block:18px;
  --hc-radius-button:12px; --hc-radius-field:11px; --hc-radius-badge:6px;
  --hc-space-1:4px; --hc-space-2:8px; --hc-space-3:12px; --hc-space-4:16px;
  --hc-space-5:20px; --hc-space-6:24px; --hc-space-7:28px;
  --hc-space-8:32px; --hc-space-9:36px; --hc-space-10:40px;
  --hc-duration-fast:150ms;
  display:block; height:100%; min-width:0; overflow:auto;
  background:var(--hc-bg); color:var(--hc-ink); color-scheme:light;
  font:15px/1.65 var(--hc-font); -webkit-font-smoothing:antialiased;
  container:ha-component / inline-size;
}
.hc-root[data-theme="dark"] {
  --hc-bg:#11151c; --hc-surface:#1b222c; --hc-ink:#f1f4fa; --hc-muted:#afbacb;
  --hc-line:#303b4b; --hc-soft:#252e3c; --hc-blue:#91b6ff; --hc-blue-soft:#233b61;
  --hc-green:#89d8b5; --hc-green-soft:#1c3b31; --hc-danger:#ffacb9;
  --hc-danger-soft:#432936; --hc-field:#69778c; --hc-dim:#b4c0d3;
  --hc-shadow:none; --hc-warning:#f8d992; --hc-warning-soft:#3a3020;
  color-scheme:dark;
}
.hc-root[data-modal-open="true"] {overflow:hidden}
.hc-root,.hc-root *,.hc-root *::before,.hc-root *::after {box-sizing:border-box}
.hc-root [hidden] {display:none!important}
.hc-root :where(h1,h2,h3,p) {margin:0}
.hc-root :where(h1,h2,h3) {line-height:1.35;letter-spacing:-.045em;word-break:keep-all;overflow-wrap:anywhere}
.hc-root h1 {font-size:38px;font-weight:750}
.hc-root h2 {font-size:23px;font-weight:720}
.hc-root h3 {font-size:18px;font-weight:700}
.hc-root a {color:var(--hc-blue);text-underline-offset:4px}
.hc-root :where(button,input,textarea,select) {font:inherit}
.hc-root :where(button,a,input,textarea,select,summary) {-webkit-tap-highlight-color:transparent}
.hc-root :focus-visible {outline:3px solid var(--hc-blue);outline-offset:4px}
.hc-root button {
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  min-width:44px;min-height:44px;padding:10px 16px;border:0;border-radius:var(--hc-radius-button);
  background:var(--hc-soft);color:var(--hc-ink);font-weight:650;line-height:1.45;cursor:pointer;
  transition:background var(--hc-duration-fast),transform var(--hc-duration-fast);
}
.hc-root button:hover:not(:disabled) {filter:brightness(.97)}
.hc-root button:active:not(:disabled) {transform:translateY(1px)}
.hc-root button:disabled {opacity:.5;cursor:not-allowed}
.hc-root button[aria-busy="true"] {cursor:progress}
.hc-root button.hc-primary {background:var(--hc-primary-bg);color:var(--hc-primary-ink);box-shadow:0 4px 12px #2563eb15}
.hc-root button.hc-secondary {background:var(--hc-blue-soft);color:var(--hc-blue)}
.hc-root button.hc-ghost {background:transparent}
.hc-root button.hc-danger {background:transparent;color:var(--hc-danger)}
.hc-root button.hc-icon-button {width:44px;padding:10px;flex:none}
.hc-root svg {width:20px;height:20px;flex:none}
.hc-wrap {max-width:1248px;margin:0 auto;padding-left:max(40px,env(safe-area-inset-left));padding-right:max(40px,env(safe-area-inset-right))}
.hc-header {background:var(--hc-surface);border-bottom:1px solid var(--hc-line)}
.hc-header-row {display:flex;align-items:center;min-height:94px;gap:14px}
.hc-root .hc-brand {display:flex;align-items:center;min-height:52px;padding:0;background:transparent;text-decoration:none;color:var(--hc-ink);font-size:21px;font-weight:800;letter-spacing:-.7px}
.hc-brand img {display:block;width:166px;height:auto;object-fit:contain}
.hc-root[data-theme="dark"] .hc-brand[data-logo-surface="light"] {padding:2px 9px;background:#fff;border-radius:12px}
.hc-brand #logoFallback{color:var(--hc-ink)}
.hc-root[data-theme=dark] .hc-brand #logoFallback{color:#191f28}
.hc-brand-caption {font-size:12px;color:var(--hc-muted);padding-left:19px;margin-left:6px;border-left:1px solid var(--hc-line)}
.hc-header-tools {margin-left:auto;display:flex;align-items:center;gap:14px}
.hc-connection {display:inline-flex;align-items:center;gap:7px;color:var(--hc-muted);font-size:12px}
.hc-connection::before {content:"";width:6px;height:6px;border-radius:50%;background:var(--hc-field)}
.hc-connection[data-state="online"]::before {background:var(--hc-green)}
.hc-connection[data-state="error"]::before {background:var(--hc-danger)}
.hc-entry {max-width:200px}
.hc-tabs {display:flex;gap:32px;min-height:53px;overflow-x:auto}
.hc-root .hc-tabs button {min-width:44px;position:relative;background:none;padding:12px 2px 16px;border-radius:0;color:var(--hc-muted);font-size:15px;font-weight:600;white-space:nowrap}
.hc-root .hc-tabs button[aria-selected="true"] {color:var(--hc-ink);font-weight:750}
.hc-tabs button[aria-selected="true"]::after {content:"";position:absolute;bottom:0;left:0;right:0;height:3px;border-radius:3px 3px 0 0;background:var(--hc-ink)}
.hc-main {padding-top:40px;padding-bottom:max(28px,env(safe-area-inset-bottom))}
.hc-page-heading {display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:30px}
.hc-page-heading p {margin-top:10px;color:var(--hc-muted);font-size:14px}
.hc-page-heading .hc-primary {min-height:50px;padding:13px 22px;white-space:nowrap}
.hc-kicker {font-size:12px;letter-spacing:.13em;color:var(--hc-muted);font-weight:650;margin-bottom:11px}
.hc-hero {position:relative;min-width:0;border-radius:var(--hc-radius-hero);background:var(--hc-hero-bg);color:#fff;padding:32px 36px 0;box-shadow:0 16px 36px #16244012}
.hc-hero-main {display:grid;grid-template-columns:minmax(280px,1fr) minmax(0,1.25fr);gap:30px;align-items:center;min-height:135px;padding-bottom:12px}
.hc-hero h2 {font-size:32px;font-weight:750;letter-spacing:-.035em}
.hc-hero-kicker {color:#b9c5d9;font-size:12px;margin-bottom:9px}
.hc-hero-status {display:block;color:#bce7d8;font-size:12px;margin-top:11px}
.hc-hero-status[data-state="pending"] {color:#f8d992}
.hc-hero-status[data-state="error"] {color:#ffb6c4}
.hc-metric {display:flex;align-items:baseline;justify-content:flex-end;flex-wrap:wrap;gap:12px;min-width:0;font-variant-numeric:tabular-nums}
.hc-metric strong {font-size:48px;font-weight:750;line-height:1.3;letter-spacing:-.035em;overflow-wrap:anywhere}
.hc-metric span {color:#bfccdf;font-size:16px}
.hc-hero-foot {display:flex;align-items:center;justify-content:space-between;gap:18px;margin-top:21px;padding:19px 0;border-top:1px solid #ffffff17;min-height:76px;font-size:13px;color:#edf2ff}
.hc-root .hc-hero-foot button {background:#ffffff0d;color:#dae4f8;font-size:13px;border:1px solid #ffffff15;white-space:nowrap}
.hc-hero :focus-visible {outline-color:#a9c7ff}
.hc-hero-details {background:#0c142530;margin:0 -36px;padding:0 36px;border-radius:0 0 var(--hc-radius-hero) var(--hc-radius-hero);font-size:12px;color:#b9c5d9}
.hc-root summary {cursor:pointer;min-height:44px;align-content:center;list-style-position:inside}
.hc-hero-details p {padding-bottom:16px;max-width:870px}
.hc-grid {display:grid;grid-template-columns:minmax(0,1fr) 304px;gap:32px;margin-top:36px;align-items:start}
.hc-section-title {display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px}
.hc-section-title h2 {font-size:21px}
.hc-section-title button {font-size:13px}
.hc-card {min-width:0;background:var(--hc-surface);border:1px solid var(--hc-line);border-radius:var(--hc-radius-card);box-shadow:var(--hc-shadow)}
.hc-card-head {display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;padding:19px 24px;border-bottom:1px solid var(--hc-line)}
.hc-card-head h3 {font-size:15px;letter-spacing:0}
.hc-card-head small {font-size:12px;color:var(--hc-muted)}
.hc-card-body {padding:0 24px}
.hc-list {list-style:none;padding:0;margin:0}
.hc-list-row {display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:center;min-height:76px;padding:16px 0;border-bottom:1px solid var(--hc-line)}
.hc-list-row:last-child {border:0}
.hc-list-row strong {font-size:15px;display:block;overflow-wrap:anywhere}
.hc-list-row small {font-size:12px;color:var(--hc-muted);display:block}
.hc-badge {display:inline-flex;align-items:center;gap:5px;background:var(--hc-soft);color:var(--hc-muted);border-radius:var(--hc-radius-badge);font-size:12px;padding:4px 8px;overflow-wrap:anywhere}
.hc-badge[data-state="success"] {background:var(--hc-green-soft);color:var(--hc-green)}
.hc-badge[data-state="error"] {background:var(--hc-danger-soft);color:var(--hc-danger)}
.hc-badge[data-state="pending"] {background:var(--hc-warning-soft);color:var(--hc-warning)}
.hc-card-foot {display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 24px;border-top:1px solid var(--hc-line);font-size:12px;color:var(--hc-muted)}
.hc-promo {background:var(--hc-blue-soft);border-radius:var(--hc-radius-card);padding:26px;min-height:220px;margin-top:62px}
.hc-promo h3 {font-size:20px;line-height:1.55}
.hc-promo p {font-size:13px;color:var(--hc-muted);margin-top:9px}
.hc-promo button {margin-top:18px}
.hc-empty {padding:38px 18px;text-align:center;color:var(--hc-muted);font-size:13px}
.hc-empty strong {display:block;color:var(--hc-ink);font-size:16px;margin-bottom:8px}
.hc-note {font-size:12px;color:var(--hc-muted);margin-top:18px;overflow-wrap:anywhere}
.hc-footer {display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:18px;margin-top:32px;padding-top:20px;border-top:1px solid var(--hc-line);font-size:12px;color:var(--hc-muted)}
.hc-toolbar {display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.hc-root label {display:block;font-size:13px;font-weight:600;margin-bottom:8px}
.hc-root :where(input,textarea,select) {border:1px solid var(--hc-field);border-radius:var(--hc-radius-field);padding:12px 13px;width:100%;min-width:0;min-height:46px;background:var(--hc-surface);color:var(--hc-ink);font-size:16px;line-height:1.5;font-variant-numeric:tabular-nums}
.hc-root :where(input,textarea)::placeholder {color:var(--hc-muted);opacity:1}
.hc-root textarea {resize:vertical;min-height:86px}
.hc-root [aria-invalid="true"] {border:2px solid var(--hc-danger)}
.hc-field {margin-bottom:22px}
.hc-hint {font-size:12px;min-height:20px;margin-top:6px;color:var(--hc-muted)}
.hc-error {font-size:13px;color:var(--hc-danger);margin-top:6px}
.hc-alert {background:var(--hc-danger-soft);color:var(--hc-danger);border:1px solid var(--hc-danger);border-radius:12px;padding:14px 18px;margin-bottom:18px;font-size:13px;overflow-wrap:anywhere}
.hc-alert[data-state="info"] {background:var(--hc-blue-soft);color:var(--hc-blue);border:0}
.hc-table-scroll {overflow:auto}
.hc-table {width:100%;border-collapse:collapse;text-align:left;font-size:14px}
.hc-table caption {text-align:left;padding-bottom:16px;color:var(--hc-muted);font-size:13px}
.hc-table :where(th,td) {padding:16px 12px;border-bottom:1px solid var(--hc-line);vertical-align:middle}
.hc-table th {font-size:12px;font-weight:600;background:var(--hc-soft);color:var(--hc-muted)}
.hc-root .hc-dialog {inset:0 0 0 auto;margin:0;width:min(580px,100%);max-width:none;height:100dvh;max-height:none;border:0;border-left:1px solid var(--hc-line);padding:0;color:var(--hc-ink);background:var(--hc-surface);box-shadow:-12px 0 60px #0a17382b;overflow:hidden}
.hc-dialog::backdrop {background:#14213b66;backdrop-filter:blur(4px)}
.hc-sheet {height:100%;display:flex;flex-direction:column}
.hc-sheet-head {display:flex;align-items:center;justify-content:space-between;gap:16px;padding:max(22px,env(safe-area-inset-top)) 26px 22px;border-bottom:1px solid var(--hc-line);flex:none}
.hc-sheet-head h2 {font-size:22px}
.hc-sheet-body {flex:1;min-height:0;overflow:auto;overscroll-behavior:contain;padding:26px}
.hc-sheet-foot {padding:17px 26px max(20px,env(safe-area-inset-bottom));border-top:1px solid var(--hc-line);background:var(--hc-surface);flex:none}
.hc-sheet-actions {display:flex;gap:10px}
.hc-sheet-actions .hc-primary {flex:1;min-height:50px}
.hc-draft {font-size:13px;color:var(--hc-muted);margin-bottom:11px;text-align:center}
.hc-sr-only {position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important}
@container ha-component (max-width:1100px) {
  .hc-hero {padding:28px 28px 0}.hc-hero-details {margin:0 -28px;padding:0 28px}
  .hc-hero-main {grid-template-columns:minmax(240px,1fr) minmax(0,1fr);gap:20px}
  .hc-hero h2 {font-size:28px}.hc-grid {grid-template-columns:minmax(0,1fr) 266px;gap:24px}
}
@container ha-component (max-width:870px) {
  .hc-wrap {padding-left:max(28px,env(safe-area-inset-left));padding-right:max(28px,env(safe-area-inset-right))}
  .hc-brand-caption {display:none}.hc-hero-main {grid-template-columns:1fr;gap:18px}.hc-metric {justify-content:flex-start}
  .hc-grid {grid-template-columns:1fr;gap:0}.hc-promo {margin-top:24px;min-height:190px}
  .hc-connection {display:none}
}
@container ha-component (max-width:560px) {
  .hc-wrap {padding-left:max(20px,env(safe-area-inset-left));padding-right:max(20px,env(safe-area-inset-right))}
  .hc-header-row {min-height:76px;gap:8px;flex-wrap:wrap}.hc-brand img {width:136px}
  .hc-header-tools {display:contents}.hc-header-tools>.hc-icon-button {margin-left:auto}
  .hc-entry {order:5;flex-basis:100%;max-width:none;padding-bottom:12px}
  .hc-tabs {gap:29px;min-height:50px}.hc-root .hc-tabs button {font-size:14px}
  .hc-main {padding-top:26px}.hc-page-heading {align-items:flex-start;flex-wrap:wrap;gap:17px;margin-bottom:23px}
  .hc-root h1 {font-size:28px}.hc-page-heading p {font-size:14px;margin-top:8px}
  .hc-page-heading .hc-primary {min-height:44px;font-size:14px;padding:11px 16px}
  .hc-hero {padding:22px 18px 0;border-radius:20px}.hc-hero h2 {font-size:25px}
  .hc-metric strong {font-size:36px}.hc-hero-foot {align-items:flex-start;gap:10px;margin-top:10px;padding:15px 0;flex-wrap:wrap}
  .hc-hero-details {margin:0 -18px;padding:0 18px;border-radius:0 0 20px 20px}
  .hc-grid {margin-top:27px}.hc-section-title h2 {font-size:19px}
  .hc-card-head {padding:15px 16px}.hc-card-body {padding:0 16px}.hc-card-foot {padding:12px 16px;flex-wrap:wrap}
  .hc-list-row {gap:8px;min-height:72px}.hc-promo {padding:24px}
  .hc-sheet-head {padding:18px 20px}.hc-sheet-body {padding:22px 20px}.hc-sheet-foot {padding:16px 20px max(20px,env(safe-area-inset-bottom))}
  .hc-footer {display:block}.hc-footer>span {display:block;margin-top:6px}
}
@container ha-component (max-width:350px) {
  .hc-wrap {padding-left:max(16px,env(safe-area-inset-left));padding-right:max(16px,env(safe-area-inset-right))}
  .hc-brand img {width:115px}.hc-root .hc-brand {font-size:18px}.hc-header-row {gap:4px}
  .hc-tabs {gap:25px}.hc-hero {padding:20px 14px 0}.hc-hero-details {margin:0 -14px;padding:0 14px}
}
@media(prefers-reduced-motion:reduce) {
  .hc-root *,.hc-root *::before,.hc-root *::after {transition:none!important;animation:none!important;scroll-behavior:auto!important}
}
@media(forced-colors:active) {
  .hc-root button,.hc-card,.hc-hero,.hc-badge {border:1px solid CanvasText}
  .hc-hero {background:Canvas;color:CanvasText}
  .hc-hero :where(h2,p,span,strong),.hc-root .hc-hero-foot button {color:CanvasText}
  .hc-hero-foot {border-color:CanvasText}
  .hc-tabs button[aria-selected="true"] {outline:2px solid Highlight}
}

:host{display:block;height:100%;min-width:0;overflow:hidden}
.hc-root{scrollbar-gutter:stable}
.hc-root .hl-link,.hc-root .hl-settings,.hc-root .hl-button{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;min-width:44px;text-decoration:none;font-size:14px;font-weight:650}
.hc-root .hl-button{padding:12px 20px;border-radius:12px;background:var(--hc-primary-bg);color:var(--hc-primary-ink)}
.hl-settings{border-radius:12px;color:var(--hc-ink)!important}
.hc-root .hc-card-head h2{font-size:18px;letter-spacing:-.025em}
.hl-stack{display:grid;gap:24px;min-width:0}.hl-section{margin-top:28px}.hl-no-top{margin-top:0}
.hl-promo{margin-top:0;min-height:0}.hl-promo h2{font-size:23px;line-height:1.45}.hl-promo p{font-size:14px}.hl-promo-icon{display:block;margin-bottom:16px;color:var(--hc-blue)}
.hl-hero-metrics{display:grid;grid-template-columns:1fr 1fr;gap:24px}.hl-hero-metrics .hc-metric{display:block;text-align:right}.hl-hero-metrics .hc-metric strong,.hl-hero-metrics .hc-metric span{display:block}
.hl-inline{display:block;margin-top:4px;font-size:15px;font-weight:650}.hl-value{font-variant-numeric:tabular-nums;text-align:right;overflow-wrap:anywhere;font-weight:650}.hl-value small{display:inline;font-size:13px;margin-left:3px}
.hl-progress{grid-column:1/-1;width:100%;height:6px;border:none;border-radius:4px;overflow:hidden;background:var(--hc-soft);accent-color:var(--hc-primary-bg)}
.hl-progress::-webkit-progress-bar{background:var(--hc-soft)}.hl-progress::-webkit-progress-value{background:var(--hc-primary-bg)}.hl-progress::-moz-progress-bar{background:var(--hc-primary-bg)}
.hl-privacy{display:flex;align-items:flex-start;gap:12px;padding:0 4px;color:var(--hc-muted);font-size:13px}.hl-privacy strong{color:var(--hc-ink)}.hl-privacy p{margin-top:6px}
.hl-selection{margin-top:24px}.hl-search{flex:1;min-width:0}.hl-filter{width:190px}.hl-count{font-size:12px;color:var(--hc-muted)}
.hl-row-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:flex-end}.hl-id{overflow-wrap:anywhere}.hl-before{margin:0 0 18px}
.hl-fields{display:grid;grid-template-columns:1fr 1fr;gap:0 24px}.hl-query-body{padding:24px}.hl-modes{display:flex;gap:12px;margin-bottom:24px}
.hl-modes [aria-pressed=true]{background:var(--hc-blue-soft);color:var(--hc-blue);box-shadow:inset 0 0 0 2px var(--hc-blue)}
.hc-table{min-width:620px}.hc-table tbody th{background:transparent;color:var(--hc-ink);font-size:13px;overflow-wrap:anywhere;max-width:280px}
.hl-steps{margin:0;padding:8px 24px 24px 48px}.hl-steps li{padding:16px 0 8px 4px}.hl-steps p{margin-top:6px;color:var(--hc-muted);font-size:14px}
.hl-editor-intro{color:var(--hc-muted);font-size:14px;margin-bottom:24px!important}.hl-fieldset{border:0;padding:0;margin:0;min-width:0}
.hl-confirm-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.hl-notice{margin:0 0 18px;background:var(--hc-blue-soft);color:var(--hc-blue);border-radius:12px;padding:14px 18px;font-size:14px}
.hc-root .hc-tabs{scroll-padding:6px}.hc-root .hc-tabs button:focus-visible{outline-offset:-4px}
.hc-root .hc-empty .hl-link,.hc-root .hc-empty button{margin-top:16px}
@container ha-component (max-width:870px){.hl-stack+aside{margin-top:24px}.hl-hero-metrics .hc-metric{text-align:left}.hl-hero-metrics{gap:16px}}
@container ha-component (max-width:560px){.hl-hero-metrics strong{font-size:32px}.hl-filter,.hl-search{width:100%;flex-basis:100%}.hl-data-row{grid-template-columns:1fr}.hl-row-actions{justify-content:space-between;margin-top:8px}.hl-fields{grid-template-columns:1fr}.hl-query-body{padding:20px 16px}.hl-stack{gap:20px}.hl-value{max-width:180px}.hc-list-row:not(.hl-data-row){grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.hc-header-tools .hc-entry{flex-basis:100%}.hc-header-tools .hl-settings{margin-left:0}}
@container ha-component (max-width:350px){.hc-tabs{gap:18px}.hc-root .hc-tabs button{font-size:13px}.hl-hero-metrics strong{font-size:28px}}
@media(max-width:580px){.hc-root .hc-dialog{width:100%}.hc-sheet-head{padding:18px 20px}.hc-sheet-body{padding:22px 20px}.hc-sheet-foot{padding:16px 20px max(20px,env(safe-area-inset-bottom))}}
@media(forced-colors:active){.hl-modes [aria-pressed=true]{outline:2px solid Highlight}.hl-settings,.hl-button{border:1px solid ButtonText}.hl-progress{border:1px solid CanvasText}}
`;
