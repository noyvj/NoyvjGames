# PWA + Ad Banner Setup

Site-shell level — same manifest, service worker, and ad bar shared across the hub page and every game page. Written up after the fact (the shell was already built when this doc was requested); kept here as the durable reference for future changes.

## 1. Manifest (`manifest.json`, site root)

```json
{
  "name": "CodingIsANoyvj",
  "short_name": "Noyvj Games",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0b0d17",
  "theme_color": "#0b0d17",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

Linked in every page's `<head>` via `<link rel="manifest" href="/manifest.json">`.

Icons are placeholder solid-color PNGs (`/icons/icon-192.png`, `/icons/icon-512.png`) — swap for real art later.

## 2. Service worker (`sw.js`, site root)

Cache-first strategy, precaching the hub shell and each game's core files as they're built. Registered on every page via:

```html
<script>
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js");
  }
</script>
```

Requires HTTPS (or localhost) to function — confirmed as part of the GitHub Pages setup.

## 3. Ad bar (shared partial, `ad-bar.css` at site root, included on hub + every game page)

Fixed-height bar (bottom of viewport), reserved space to avoid layout jump.

**Labeling requirements (added after initial build, before any real ad unit goes live):**
- Visible "Advertisement — not part of the game" label inside the bar, so it reads as clearly separate from game UI.
- Background color (`#14161f`) distinct from every button/interactive background color used anywhere on the site — checked against both `style.css` (hub) and `games/sol/style.css` at time of writing.
- A `border-top` separating the bar from page content.
- A few pixels of dead space (margin) between the ad bar's edge and the nearest real interactive element on every page it appears on.

```html
<div class="ad-bar ad-bar--bottom">
  <span class="ad-bar-label">Advertisement — not part of the game</span>
  <!-- Google AdSense manual display ad unit -->
  <ins class="adsbygoogle"
       style="display:block; width:320px; height:50px;"
       data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
       data-ad-slot="XXXXXXXXXX"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
```

Once per page, near the top of `<head>` (loads the AdSense library):

```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX" crossorigin="anonymous"></script>
```

`ca-pub-XXXXXXXXXXXXXXXX` and the ad slot ID are placeholders until AdSense approval — see Open Item below.

## Setup order

1. Apply for Google AdSense early — approval can take days to weeks.
2. Confirm HTTPS via hosting (GitHub Pages provides this automatically).
3. Add `ads.txt` to the site root once AdSense gives the exact line.
4. Manifest + service worker + ad bar shell — **done**.
5. Ad-bar labeling (color/border/spacing/disclosure) — **done**, ahead of any real ad unit going live.
6. Once AdSense approves: drop in real client/slot IDs — ad bar goes live everywhere at once since it's shared.

## Open item

`ads.txt` content and the real `data-ad-client` / `data-ad-slot` values only exist once the AdSense application is approved — everything above works with placeholders until then.
