"""Shared HTML fragments used across every generated/static page."""

HEAD = """<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;700&family=Playfair+Display:ital@1&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/styles.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>%E2%82%BF</text></svg>">
"""

HEADER = """<header class="site-header">
  <div class="wrap">
    <a class="logo-link" href="{root}index.html">
      <img class="logo" src="{root}assets/logo.png" alt="The Crypto Playback">
    </a>
    <nav class="site-nav">
      <a href="{root}archive.html">Archive</a>
      <a href="{root}resources.html">Resources</a>
      <a href="{root}about.html">About</a>
    </nav>
  </div>
</header>
"""

DISCLAIMER = """<div class="disclaimer">
  <div class="wrap">
    <strong>THE CRYPTO PLAYBACK IS NOT FINANCIAL ADVICE.</strong>
    The material in this newsletter has no regard to any specific investment objectives, financial situation,
    or particular needs of any reader. It is published solely for informational purposes and is not to be
    construed as a solicitation nor does it constitute advice, investment or otherwise. References made to
    third parties are based on information obtained from sources believed to be reliable but not guaranteed
    as being accurate. Readers should not regard it as a substitute for the exercise of their own judgment.
    Our comments are an expression of opinion. While we believe our statements to be true, they always depend
    on the reliability of our own credible sources. We recommend that you consult with a licensed, qualified
    investment advisor before making any investment decisions.
  </div>
</div>
"""

FOOTER = """<footer class="site-footer">
  <div class="wrap">
    &copy; {year} The Crypto Playback &middot; <a href="{root}about.html">Contact</a>
  </div>
</footer>
"""


def page(root, title, body_html, year):
    """Wrap body_html in the full document shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<title>{title}</title>
{HEAD.format(root=root)}
</head>
<body>
{HEADER.format(root=root)}
{body_html}
{DISCLAIMER}
{FOOTER.format(root=root, year=year)}
</body>
</html>
"""
