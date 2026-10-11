# Brand files

The storefront draws the logo from these files. To change the logo, replace them with files of
the same names (transparent PNG); nothing in the code needs to change.

| File | Used for | Drawn at |
|---|---|---|
| `logo-wordmark.png` | Header, every page (the word only) | `--brand-logo-header-height` in `src/theme/brand.css` |
| `logo-full.png` | Footer (mark above the word) | `--brand-logo-footer-height` |
| `logo-mark.png` | Source of the icons below | — |

Icons in `public/`: `favicon.svg` (the mark, embedded), `favicon.png` (64 px fallback),
`apple-touch-icon.png` (180 px, home-screen icon on phones).

The current files were cut from the owner's logo image (11 Oct 2026): background removed, colours
kept (green `#2b4732`, gold `#c49c4c`), and a small generator watermark in the corner left out.
The gold drop is pale: keep the logo on the light canvas or soft colours, not on the yellow panel.
