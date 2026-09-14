/** Component Web UI Design System v1.0 (2026-09-14 user-supplied guide).
 * Component container queries are unrelated to the HA shell's narrow threshold.
 * There are no global selectors, external fonts or host DOM traversal here.
 */
export const UNIFIED_STYLES = String.raw`
:host { font-family:var(--paper-font-body1_-_font-family,Roboto,Noto,sans-serif); }
:host([native-header-shown]) { background:var(--app-header-background-color,var(--primary-background-color,#fff)); }
.hl-layout { display:flex;flex-direction:column;height:100%;min-height:0; }
.hl-layout > .hc-root { height:auto;min-height:0;flex:1 1 auto; }
#nativeHaHeader {
  flex:0 0 auto;height:var(--header-height);min-width:0;
  /* v0.3.7's panel host already consumed the physical device safe areas.
     The owned native instance must not consume those same insets again. */
  --safe-area-inset-top:0px;--safe-area-inset-bottom:0px;
  --safe-area-inset-left:0px;--safe-area-inset-right:0px;
}
#nativeHaHeader[hidden] { display:none!important; }
.hc-root {
  --app-bg:#f7f8fa;--app-surface:#fff;--app-text:#191f28;--app-muted:#667182;
  --app-line:#e9ecf1;--app-soft:#f1f3f6;--app-primary:#2563eb;--app-primary-soft:#edf3ff;
  --app-success:#147455;--app-success-soft:#e9f6ef;--app-warning:#805500;
  --app-warning-soft:#fff4dc;--app-danger:#b4233d;--app-danger-soft:#fff0f2;
  --app-radius-xl:16px;--app-radius-lg:14px;--app-radius-md:10px;--app-radius-sm:6px;
  --app-shadow-card:0 8px 28px rgba(25,36,59,.06);
  --app-shadow-floating:0 8px 24px rgba(25,36,59,.12);--app-content-max:1248px;
  --hc-bg:var(--app-bg);--hc-surface:var(--app-surface);--hc-ink:var(--app-text);
  --hc-muted:var(--app-muted);--hc-line:var(--app-line);--hc-soft:var(--app-soft);
  --hc-blue:var(--app-primary);--hc-blue-soft:var(--app-primary-soft);
  --hc-green:var(--app-success);--hc-green-soft:var(--app-success-soft);
  --hc-warning:var(--app-warning);--hc-warning-soft:var(--app-warning-soft);
  --hc-danger:var(--app-danger);--hc-danger-soft:var(--app-danger-soft);
  --hc-radius-hero:var(--app-radius-xl);--hc-radius-card:var(--app-radius-lg);
  --hc-radius-block:var(--app-radius-md);--hc-radius-button:var(--app-radius-md);
  --hc-radius-field:var(--app-radius-md);--hc-radius-badge:var(--app-radius-sm);
  --hc-shadow:var(--app-shadow-card);
  --hc-font:-apple-system,BlinkMacSystemFont,"Pretendard","Noto Sans KR","Noto Sans CJK KR","Malgun Gothic",sans-serif;
  font:400 15px/1.6 var(--hc-font);
  position:relative;
  scrollbar-gutter:auto;
}
.hc-root[data-theme="dark"] {
  --app-bg:#11151c;--app-surface:#1b222c;--app-text:#f1f4fa;--app-muted:#afbacb;
  --app-line:#303b4b;--app-soft:#252e3c;--app-primary:#91b6ff;--app-primary-soft:#233b61;
  --app-success:#89d8b5;--app-success-soft:#1c3b31;--app-warning:#f8d992;
  --app-warning-soft:#3a3020;--app-danger:#ffacb9;--app-danger-soft:#432936;
  --app-shadow-card:0 8px 28px rgba(0,0,0,.12);
  --app-shadow-floating:0 8px 24px rgba(0,0,0,.24);
  /* Rebind: the legacy dark selector has literal hc-* values. */
  --hc-bg:var(--app-bg);--hc-surface:var(--app-surface);--hc-ink:var(--app-text);
  --hc-muted:var(--app-muted);--hc-line:var(--app-line);--hc-soft:var(--app-soft);
  --hc-blue:var(--app-primary);--hc-blue-soft:var(--app-primary-soft);
  --hc-green:var(--app-success);--hc-green-soft:var(--app-success-soft);
  --hc-warning:var(--app-warning);--hc-warning-soft:var(--app-warning-soft);
  --hc-danger:var(--app-danger);--hc-danger-soft:var(--app-danger-soft);
  --hc-shadow:var(--app-shadow-card);
}
.hc-root .hc-wrap { width:100%;max-width:var(--app-content-max);padding-inline:40px; }
.hc-root .hc-header { position:static;background:var(--hc-surface);box-shadow:none;border-bottom:1px solid var(--hc-line); }
.hc-root .hc-header-row { min-height:72px;gap:20px;justify-content:space-between;flex-wrap:nowrap; }
.hc-root .hc-brand { flex:0 0 auto;min-height:44px;min-width:44px;padding:0;max-width:44%; }
.hc-root .hc-brand img { width:auto;height:36px;max-width:100%;aspect-ratio:3/1;object-fit:contain;object-position:left center; }
.hc-root[data-theme="dark"] .hc-brand[data-logo-surface="light"] { padding:2px 4px;border-radius:6px; }
.hc-root .hc-header-tools { display:flex;margin-left:auto;gap:10px;align-items:center;min-width:0; }
.hc-root .hc-header-tools > .hc-icon-button { margin-left:0; }
.hc-root .hc-connection { display:inline-flex;white-space:nowrap;font-size:12px;font-weight:600;gap:7px; }
.hc-root .hc-connection::before { width:7px;height:7px;border-radius:2px; }
.hc-root .hl-version { font-size:12px;font-weight:400;color:var(--hc-muted);background:var(--hc-soft);padding:4px 8px;border-radius:6px;white-space:nowrap; }
.hc-root .hl-profile-row { display:flex;justify-content:flex-end;padding:0 0 12px; }
.hc-root .hc-entry { display:flex;align-items:center;gap:10px;padding:0;max-width:340px;width:100%; }
.hc-root .hc-entry label { margin:0;white-space:nowrap;font-size:13px;color:var(--hc-muted);font-weight:600; }
.hc-root .hc-entry select { min-height:44px;padding:8px 12px;font-size:16px; }
.hc-root .hc-tabs { align-items:flex-end;min-height:46px;gap:28px;overflow-x:auto;white-space:nowrap; }
.hc-root .hc-tabs button { min-height:46px;padding:10px 0 12px;font-size:14px;font-weight:600; }
.hc-root .hc-tabs button[aria-selected="true"] { font-weight:750; }
.hc-root .hc-main { padding-top:32px;padding-bottom:48px; }
.hc-root h1 { font-size:38px;font-weight:750;line-height:1.3;letter-spacing:-.035em; }
.hc-root h2 { font-size:22px;font-weight:700;line-height:1.4;letter-spacing:-.025em; }
.hc-root .hc-page-heading { margin-bottom:24px;align-items:flex-start; }
.hc-root .hc-page-heading p { font-size:15px;line-height:1.6;margin-top:12px; }
.hc-root .hl-eyebrow { font-size:12px;font-weight:700;letter-spacing:.12em;color:var(--hc-blue);margin-bottom:10px; }
.hc-root .hc-page-heading .hc-primary { min-height:46px;padding:0 16px;font-size:14px; }
.hc-root :where(button,.hl-button) { min-height:46px;border-radius:10px;font-size:14px;font-weight:600; }
.hc-root button.hc-secondary { color:var(--hc-ink);background:var(--hc-surface);border:1px solid var(--hc-line); }
.hc-root :where(button.hc-icon-button,.hl-settings) { width:44px;height:44px;min-height:44px;min-width:44px;padding:10px; }
.hc-root .hc-hero { padding:24px 24px 0;min-height:0;border-radius:16px;box-shadow:var(--app-shadow-card); }
.hc-root[data-theme="dark"] .hc-hero { box-shadow:var(--app-shadow-card); }
.hc-root .hc-hero-main { min-height:110px;padding-bottom:8px;gap:24px; }
.hc-root .hc-hero h2 { font-size:28px;line-height:1.4;font-weight:750; }
.hc-root .hc-hero-kicker { font-size:13px; }
.hc-root .hc-metric strong { font-size:40px;line-height:1.25;font-weight:750; }
.hc-root .hc-hero-foot { margin-top:16px;padding:16px 0;min-height:0; }
.hc-root .hc-hero-foot button { min-height:46px;border-radius:10px;font-size:14px; }
.hc-root .hc-hero-status { border-radius:6px; }
.hc-root .hc-card,.hc-root .hc-promo { border-radius:14px; }
.hc-root .hc-card { box-shadow:var(--app-shadow-card); }
.hc-root .hc-card-head { padding:18px 24px; }
.hc-root .hc-card-head h2 { font-size:21px;font-weight:700; }
.hc-root .hc-card-body { padding:0 24px; }
.hc-root .hc-grid { margin-top:32px;gap:24px;grid-template-columns:minmax(0,1fr) 288px; }
.hc-root .hl-no-top { margin-top:0; }
.hc-root .hl-stack { gap:16px; }
.hc-root .hl-section { margin-top:32px; }
.hc-root .hc-list-row { min-height:72px;padding:16px 0; }
.hc-root .hc-list-row strong { font-weight:600;font-size:15px; }
.hc-root .hc-list-row small { font-size:13px; }
.hc-root .hl-promo { padding:24px; }
.hc-root .hl-promo h2 { font-size:22px; }
.hc-root .hc-alert,.hc-root .hl-notice { border-radius:10px; }
.hc-root .hc-dialog { box-shadow:var(--app-shadow-floating); }
.hc-root .hc-table tbody th small { display:block;font-weight:400;color:var(--hc-muted); }
.hc-root .hl-heading-actions { display:flex;gap:10px;flex-wrap:wrap;align-items:center; }
.hc-root .hc-footer { margin-top:32px; }
.hc-root .hl-skip-link { position:absolute;inset:8px auto auto 8px;z-index:10;transform:translateY(-150%);padding:10px 16px;min-height:44px;background:var(--hc-surface);color:var(--hc-ink);border-radius:10px;box-shadow:var(--app-shadow-floating); }
.hc-root .hl-skip-link:focus { transform:none; }
.hc-root .hl-guide-body { padding:24px; }
.hc-root .hl-guide-body p { margin-top:8px;font-size:14px;line-height:1.6;color:var(--hc-muted); }
.hc-root .hl-guide-body strong { color:var(--hc-ink); }
.hc-root .hl-guide-steps { margin:16px 0 24px;padding-left:24px; }
.hc-root .hl-guide-steps li { padding:10px 0 10px 4px; }
.hc-root .hl-guide-steps li::marker { color:var(--hc-blue);font-weight:700; }
.hc-root .hl-guide-notes { background:var(--hc-soft);border-radius:10px;padding:16px 20px;margin-top:20px; }
.hc-root .hl-guide-notes summary { font-weight:600; }
.hc-root .hl-guide-sensors { display:grid;grid-template-columns:1fr 1fr;gap:8px 24px;padding-left:20px;font-size:14px; }
@container ha-component (max-width:870px) {
  .hc-root .hc-wrap { padding-inline:28px; }
  .hc-root .hc-header-row { min-height:62px;gap:16px; }
  .hc-root .hc-brand img { height:32px;width:auto; }
  .hc-root .hc-main { padding-top:26px; }
  .hc-root .hc-grid { grid-template-columns:1fr;gap:16px; }
  .hc-root .hl-stack+aside { margin-top:0; }
}
@container ha-component (max-width:560px) {
  .hc-root .hc-wrap { padding-inline:20px; }
  .hc-root .hc-header-row { min-height:58px;gap:10px; }
  .hc-root .hc-brand img { height:28px;width:auto; }
  .hc-root .hc-header-tools { display:flex;gap:6px; }
  .hc-root .hc-connection { display:inline-flex;font-size:12px; }
  .hc-root .hl-version { display:none; }
  .hc-root .hc-entry { max-width:none;flex-basis:auto; }
  .hc-root .hc-tabs { gap:24px; }
  .hc-root .hc-main { padding-top:22px;padding-bottom:36px; }
  .hc-root h1 { font-size:28px; }
  .hc-root .hc-page-heading { margin-bottom:22px;gap:16px; }
  .hc-root .hc-page-heading p { font-size:15px; }
  .hc-root .hc-hero { padding:20px 18px 0;border-radius:16px; }
  .hc-root .hc-hero h2 { font-size:24px; }
  .hc-root .hc-hero-main { min-height:0;gap:20px; }
  .hc-root .hc-metric strong { font-size:32px; }
  .hc-root .hc-card-head { padding:16px 18px; }
  .hc-root .hc-card-head h2 { font-size:21px; }
  .hc-root .hc-card-body { padding:0 18px; }
  .hc-root .hl-query-body,.hc-root .hl-guide-body { padding:20px 18px; }
  .hc-root .hl-guide-sensors { grid-template-columns:1fr; }
  .hc-root .hl-promo { padding:20px; }
}
@container ha-component (max-width:350px) {
  .hc-root .hc-wrap { padding-inline:16px; }
  .hc-root .hc-header-row { gap:6px; }
  .hc-root .hc-header-tools { gap:4px; }
  .hc-root .hc-connection { font-size:12px;gap:5px; }
  .hc-root .hc-tabs { gap:20px; }
  .hc-root .hc-brand img { height:28px;width:auto; }
}
@media(forced-colors:active) {
  .hc-root .hc-card,.hc-root .hc-hero { border-color:CanvasText;box-shadow:none; }
  .hc-root .hc-connection::before { background:CanvasText; }
  .hc-root .hl-skip-link { border:1px solid CanvasText; }
}

.hc-root .hl-icon {
  display:block;flex:0 0 20px;width:20px;height:20px;
  fill:currentColor;stroke:none;pointer-events:none;
}
.hc-root .hl-icon path { fill:currentColor;stroke:none; }
.hc-root .hl-settings { color:var(--hc-ink);border:1px solid transparent;border-radius:10px; }
.hc-root .hl-settings:hover { background:var(--hc-soft); }
.hc-root .hl-settings:focus-visible { outline:3px solid var(--hc-blue);outline-offset:3px; }
.hc-root .hc-header-tools { flex:0 1 auto; }
/* Long disconnected/error copy may wrap, but never evicts either 44px action. */
.hc-root .hc-connection { min-width:0;white-space:normal;overflow-wrap:anywhere;line-height:1.4; }
.hc-root .hc-connection::before { flex:0 0 7px; }
@media(forced-colors:active) {
  .hc-root .hl-settings { color:ButtonText!important;border-color:ButtonText; }
  .hc-root .hl-icon { forced-color-adjust:auto; }
}
`;
