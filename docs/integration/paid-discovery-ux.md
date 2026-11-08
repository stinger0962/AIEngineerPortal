# Paid-product discovery UX

This milestone changes paid-mode discovery and account guidance only. The shared
folding-screen homepage and door transition remain unchanged. Personal portal
routes and branding are preserved; paid-only mobile navigation wraps instead of
hiding feature links off-screen.

The catalogue explains the difference between Ziwei (birth-information-based
chart exploration) and Qian (a question-based reflection), with preparation tips
and explicit links. It does not invent new functionality, prices, eligibility,
release dates or availability. A shared notice says real payments/top-ups are
unavailable. A selected feature remains visible above its account gate so users
understand where they arrived. Disabled accounts offer a way back to discovery,
not an email form or payment action. Initial account availability checks no longer
flash an editable email field.

Accessibility checks cover semantic headings/articles/navigation, current-page
indication, a main-content skip link, visible keyboard focus, Enter navigation,
reduced motion, readable text, and horizontal overflow at 320/390/1440px. These
are focused checks, not a claim of a complete WCAG audit. Hosted browser tests
mock disabled account responses and block external/API feature calls; existing
real backend account integration still runs separately. Screenshots are retained
as CI artifacts for visual review. No credentials, email or payments are used.
