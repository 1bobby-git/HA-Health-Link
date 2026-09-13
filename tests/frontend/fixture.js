// Synthetic fixtures ONLY. Production code never imports this file.
const stamp = '2026-09-13T12:35:00Z';
const profiles = [{config_entry_id:'demo-a',title:'예시 프로필 A',available:true,sample_count:12480,type_count:8,last_sync:stamp,goal_progress:{steps:{current:6240,target:8000,progress:78},exercise_minutes:{current:25,target:30,progress:83},water_ml:{current:1200,target:2000,progress:60}},daily_focus:'steps',daily_goal_context:'in_progress',recovery_context:'within_baseline',recovery_confidence:76,data_confidence:82,steps_vs_same_time_baseline:12,companion_active:true,companion_sensor_count:8,companion_device_count:1,source_mode:'auto'}, {config_entry_id:'demo-b',title:'예시 프로필 B',available:true,sample_count:0,type_count:0,last_sync:null,goal_progress:{},recovery_context:'insufficient_data',companion_active:false,companion_sensor_count:0,companion_device_count:0,source_mode:'auto'}];
const catalog = [{type_id:'HKQuantityTypeIdentifierStepCount',display_name:'걸음 수',domain:'activity',sample_count:8040,last_sample:stamp,exposed:1},{type_id:'HKQuantityTypeIdentifierHeartRate',display_name:'심박수',domain:'heart',sample_count:3000,last_sample:stamp,exposed:0},{type_id:'HKCategoryTypeIdentifierSleepAnalysis',display_name:'수면',domain:'sleep',sample_count:1440,last_sample:stamp,exposed:0}];
const composers = [{id:'activity_context',name:'나의 활동 컨텍스트',version:1}];
window.mock = {profiles,catalog,composers,calls:[],handlers:{},delays:{}};
window.mock.defaultResponse = payload => {
  const id = payload.config_entry_id;
  switch (payload.type) {
    case 'health_link/status': return structuredClone(mock.profiles);
    case 'health_link/catalog/list': return structuredClone(id === 'demo-b' ? [] : mock.catalog);
    case 'health_link/composer/list': return structuredClone(id === 'demo-b' ? [] : mock.composers);
    case 'health_link/catalog/expose': mock.catalog.find(x => x.type_id === payload.type_id).exposed = payload.exposed; return {ok:true,reload_required:true};
    case 'health_link/composer/validate': return {valid:true};
    case 'health_link/composer/save': mock.composers.push({id:payload.definition_id,name:payload.name,version:1});return {ok:true,reload_required:true};
    case 'health_link/composer/delete': mock.composers = mock.composers.filter(x => x.id !== payload.definition_id);return {ok:true,removed:true};
    case 'health_link/timeline/query': return {start:'2026-09-12T12:35:00Z',end:stamp,events:[{time:stamp,source:'healthkit',id:payload.type_id,value:0,unit:'count'},{time:stamp,source:'home_assistant',id:payload.entity_ids[0] || 'sensor.room_temperature',value:24,unit:'°C'}]};
    case 'health_link/insights/correlation': return {pairs:24,correlation:0.4,strength:'moderate'};
    case 'health_link/optimizer/observe': return {pairs:24,preferred_observed_range:{low:23,high:25}};
    default: throw new Error('Unexpected fixture call: '+payload.type);
  }
};
window.hassFixture = {language:'ko',themes:{darkMode:false},user:{is_admin:true},config:{time_zone:'Asia/Seoul'},states:{'sensor.room_temperature':{state:'24',attributes:{friendly_name:'침실 온도'}},'sensor.co2':{state:'650',attributes:{friendly_name:'침실 CO₂'}},'sensor.empty':{state:'',attributes:{friendly_name:'빈 값'}}},callWS:async payload => {
  mock.calls.push(structuredClone(payload));
  if (mock.delays[payload.type]) await new Promise(r => setTimeout(r,mock.delays[payload.type]));
  if (mock.handlers[payload.type]) return mock.handlers[payload.type](payload);
  return mock.defaultResponse(payload);
}};
window.panel = document.querySelector('health-link-panel');
panel.hass = hassFixture;
document.getElementById('demoTheme')?.addEventListener('click', () => { panel.hass = {...hassFixture,themes:{darkMode:!panel._hass.themes.darkMode}}; });
