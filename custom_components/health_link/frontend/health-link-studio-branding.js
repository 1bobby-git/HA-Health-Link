/** HealthLink-specific branding layered over the shared Wallet design tokens.
 * Source artwork is served by HA from custom_components/health_link/brand/logo.png.
 * No remote image request, image filter, cropping, or replacement artwork.
 */
export const STUDIO_BRAND = Object.freeze({
  logoUrl: '/health_link_brand/logo.png?v=56472261',
  fallbackUrl: '/health_link_static/brand/logo.png?v=56472261',
  width: 600,
  height: 200,
});

export function bindStudioLogo(ui) {
  const image = ui.shadowRoot.getElementById('healthLinkLogo');
  const text = ui.shadowRoot.getElementById('logoFallback');
  if (!image || !text) return;
  image.width = STUDIO_BRAND.width;
  image.height = STUDIO_BRAND.height;
  image.decoding = 'async';
  const caption = ui.shadowRoot.querySelector('.hc-brand-caption');
  if (caption) caption.textContent = ui._t('나의 건강, 한곳에', 'Your health, in one place');

  // A transient 404 must not leave every subsequent render in text-only mode.
  let triedFallback = image.src === new URL(STUDIO_BRAND.fallbackUrl, document.baseURI).href;
  const showImage = () => {
    if (!image.isConnected) return;
    image.hidden = false;
    text.hidden = true;
    ui._logoFailed = false;
  };
  const handleError = () => {
    if (!image.isConnected) return;
    if (!triedFallback) {
      triedFallback = true;
      image.src = STUDIO_BRAND.fallbackUrl;
      return;
    }
    image.hidden = true;
    text.hidden = false;
    ui._logoFailed = true;
  };
  image.addEventListener('load', showImage);
  image.addEventListener('error', handleError);
  if (image.complete) {
    if (image.naturalWidth > 0) showImage();
    else handleError();
  }
}

export const STUDIO_BRANDING_STYLES = String.raw`
/* User-approved HealthLink variation: light summary rather than navy emphasis.
 * Neutral surface tokens also keep text readable when Home Assistant is dark.
 */
.hc-root { --hc-hero-bg:var(--hc-surface); }
.hc-root .hc-brand { flex-shrink:0; }
.hc-root .hc-brand img { width:166px;height:auto;aspect-ratio:3 / 1;object-fit:contain; }
.hc-root .hc-brand:hover:not(:disabled) { filter:none; }
.hc-root .hc-brand:active:not(:disabled) { transform:none; }
.hc-root .hc-hero {
  background:var(--hc-surface);
  color:var(--hc-ink);
  border:1px solid var(--hc-line);
  box-shadow:0 8px 28px #19243b05;
}
.hc-root[data-theme="dark"] .hc-hero { box-shadow:none; }
.hc-root .hc-hero h2,.hc-root .hc-hero .hc-metric strong { color:var(--hc-ink); }
.hc-root .hc-hero-kicker { color:var(--hc-muted);font-size:13px;font-weight:600; }
.hc-root .hc-hero-status {
  display:inline-flex;
  align-items:center;
  padding:5px 10px;
  border-radius:8px;
  color:var(--hc-ink);
  background:var(--hc-soft);
  font-size:13px;
  line-height:1.6;
}
.hc-root .hc-hero-status[data-state="pending"] {
  color:var(--hc-warning);background:var(--hc-warning-soft);
}
.hc-root .hc-hero-status[data-state="error"] {
  color:var(--hc-danger);background:var(--hc-danger-soft);
}
.hc-root .hc-hero .hc-metric span { color:var(--hc-muted);font-size:14px; }
.hc-root .hc-hero-foot { color:var(--hc-muted);border-top:1px solid var(--hc-line); }
.hc-root .hc-hero-foot .hl-inline { color:var(--hc-ink); }
.hc-root .hc-hero-foot button {
  color:var(--hc-blue);
  background:var(--hc-blue-soft);
  border:1px solid transparent;
  font-weight:650;
}
.hc-root .hc-hero :focus-visible { outline-color:var(--hc-blue); }
.hc-root .hc-hero-details { color:var(--hc-ink);background:var(--hc-soft); }
.hc-root .hl-hero-metrics .hc-metric + .hc-metric {
  border-left:1px solid var(--hc-line);padding-left:24px;
}
@container ha-component (max-width:560px) {
  .hc-root .hc-brand img { width:136px; }
  .hc-root .hl-hero-metrics .hc-metric + .hc-metric { padding-left:16px; }
}
@container ha-component (max-width:350px) {
  .hc-root .hc-brand img { width:115px; }
}
@media (forced-colors:active) {
  .hc-root .hc-hero,.hc-root .hc-hero-status,.hc-root .hc-hero-foot button {
    background:Canvas;color:CanvasText;border:1px solid CanvasText;
  }
  .hc-root .hc-hero :where(h2,p,span,strong) { color:CanvasText; }
  .hc-root .hc-hero-foot,.hc-root .hl-hero-metrics .hc-metric + .hc-metric { border-color:CanvasText; }
  .hc-root .hc-hero :focus-visible { outline-color:Highlight; }
}
`;
