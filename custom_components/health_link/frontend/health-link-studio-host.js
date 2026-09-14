/** Native Home Assistant chrome for the custom-panel integration boundary.
 * This is NOT the Supervisor-only ha-panel-app and never imitates its markup.
 * HA loads ha-top-app-bar-fixed via its router's hass-loading-screen dependency.
 * Only host-supplied narrow/sidebar/kiosk properties determine visibility.
 */
export function nativeHeaderVisible(narrow, hass) {
  return !hass?.kioskMode && (Boolean(narrow) || hass?.dockedSidebar === 'always_hidden');
}

export function mountNativeHeader(ui) {
  const root = ui.shadowRoot.querySelector('.hc-root');
  const layout = document.createElement('div');
  layout.className = 'hl-layout';
  root.before(layout);
  const native = document.createElement('ha-top-app-bar-fixed');
  native.id = 'nativeHaHeader';
  native.hidden = true;
  const title = document.createElement('span');
  title.slot = 'title';
  title.id = 'nativeHaTitle';
  title.textContent = 'HealthLink';
  native.append(title);
  layout.append(native, root);
  // No shim/redefinition of HA elements is ever registered in production.
  // Allow cold navigation while the real HA element is still upgrading.
  customElements.whenDefined('ha-top-app-bar-fixed').then(() => {
    if (ui._active && native.isConnected) syncNativeHeader(ui);
  });
  syncNativeHeader(ui);
}

export function syncNativeHeader(ui) {
  const native = ui.shadowRoot.getElementById('nativeHaHeader');
  if (!native) return;
  const ready = Boolean(customElements.get('ha-top-app-bar-fixed'));
  const show = nativeHeaderVisible(ui._narrow, ui._hass);
  native.hidden = !(ready && show);
  ui.toggleAttribute('native-header-shown', ready && show);
  if (ready) {
    native.narrow = Boolean(ui._narrow);
    const scrollRoot = ui.shadowRoot.querySelector('.hc-root');
    if (native.scrollTarget !== scrollRoot) native.scrollTarget = scrollRoot;
  }
  ui.shadowRoot.getElementById('nativeHaTitle').textContent = ui._panel?.title || 'HealthLink';
}
