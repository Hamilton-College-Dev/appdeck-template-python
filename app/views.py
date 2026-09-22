"""The HTML and CSS for the pages."""

from html import escape

CSS = """
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0 auto; padding: 2.5rem 1.25rem; max-width: 40rem;
    font: 16px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  h1 { font-size: 1.75rem; margin: 0 0 .25rem; letter-spacing: -.02em; }
  .sub { opacity: .75; margin: 0 0 2rem; }
  form { display: flex; gap: .5rem; margin: 0 0 1.5rem; }
  input[type=text] {
    flex: 1; min-width: 0; padding: .6rem .75rem; font: inherit;
    border: 1px solid currentColor; border-radius: .4rem;
    background: transparent; color: inherit;
  }
  button {
    padding: .6rem 1rem; font: inherit; cursor: pointer;
    border: 1px solid currentColor; border-radius: .4rem;
    background: transparent; color: inherit;
  }
  ul { list-style: none; padding: 0; margin: 0; }
  li { padding: .75rem 0; border-top: 1px solid rgba(128,128,128,.3); }
  time { display: block; font-size: .8rem; opacity: .6; }
  .badge {
    display: inline-block; padding: .15rem .55rem; border-radius: 999px;
    font-size: .75rem; border: 1px solid currentColor; opacity: .85;
  }
  footer { margin-top: 3rem; font-size: .85rem; opacity: .65; }
  a { color: inherit; }
  code { font-size: .9em; }
"""


def page(title, body):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>"""


def home(notes, using_database):
    storage = "Saving to the database" if using_database else "Saving in memory, resets on restart"

    if notes:
        items = "\n".join(
            f'  <li>{escape(n["body"])}'
            f'<time>{n["created_at"].strftime("%Y-%m-%d %H:%M")}</time></li>'
            for n in notes
        )
    else:
        items = '  <li style="opacity:.6">Nothing here yet. Add the first note.</li>'

    return page("Python starter", f"""<h1>It works.</h1>
<p class="sub">Your Python app is running. <span class="badge">{escape(storage)}</span></p>

<form method="post" action="/notes">
  <input type="text" name="body" placeholder="Write a note" maxlength="500" required>
  <button type="submit">Add</button>
</form>

<ul>
{items}
</ul>

<footer>
  Edit <code>app/main.py</code> to change this page.<br>
  Health check: <a href="/healthz">/healthz</a> &middot; Status: <a href="/api/status">/api/status</a>
</footer>""")


def not_found():
    return page("Not found", '<h1>404</h1>\n<p>There is no page at that address. <a href="/">Go home</a>.</p>')


def server_error():
    return page("Something broke", '<h1>500</h1>\n<p>Something went wrong on our end. Check the logs.</p>')


def too_large():
    return page("Too much", '<h1>413</h1>\n<p>That was more data than this page accepts. <a href="/">Go back</a>.</p>')
