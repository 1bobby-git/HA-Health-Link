/** TEST ONLY. Geometry/lifecycle substitute, not the production HA implementation.
 * Production never imports this file; it uses elements registered by HA itself.
 */
customElements.define('ha-top-app-bar-fixed', class extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'}).innerHTML = `<style>:host{display:block}header{height:var(--header-height,56px);display:flex;align-items:center;gap:16px;padding:0 12px;box-sizing:border-box;background:var(--app-header-background-color,#efefef);color:var(--app-header-text-color,#191f28);font:16px/1.5 sans-serif}button{width:44px;height:44px;border:0;background:transparent;color:inherit;display:grid;place-items:center;flex:none}svg{width:24px;height:24px;fill:currentColor}</style><header><button aria-label="Home Assistant 메뉴 열기"><svg viewBox="0 0 24 24"><path d="M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"/></svg></button><slot name="title"></slot></header>`;
    this.shadowRoot.querySelector('button').addEventListener('click',()=>this.dispatchEvent(new CustomEvent('hass-toggle-menu',{bubbles:true,composed:true})));
  }
});
