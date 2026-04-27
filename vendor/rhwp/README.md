# rhwp vendor baseline

This directory vendors the npm artifacts used by HWP Master's embedded editor.

- Upstream: https://github.com/edwardkim/rhwp
- Baseline tag: `v0.7.6`
- npm packages: `@rhwp/core@0.7.6`, `@rhwp/editor@0.7.6`
- License: MIT

The runtime files copied into `assets/rhwp_studio/rhwp-core/` come from
`vendor/rhwp/npm/core/`. HWP Master adds its own localhost bridge UI in
`assets/rhwp_studio/` so save operations are routed through the Python app
instead of browser downloads.
