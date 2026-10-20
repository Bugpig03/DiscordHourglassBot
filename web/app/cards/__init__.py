"""Shareable stat cards (Discord bot images and embeddable SVG cards), drawn in the website's style.

Every card is built once as SVG (app.cards.builders), then:
  - served as is by the public /api/card/... endpoints (embeddable anywhere);
  - converted to PNG with resvg for the Discord bot (/internal/card/...).
"""
