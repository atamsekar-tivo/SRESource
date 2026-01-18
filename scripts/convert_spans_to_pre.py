#!/usr/bin/env python3
"""
Convert code-block divs to pre/code tags with Highlight.js support
while preserving the visual polish (dark theme, proper spacing).
Keeps span-based manual colors for fallback, removes them for Highlight.js processing.
"""
import sys
import re
import html
from pathlib import Path

def convert_file(path: Path):
    if not path.exists():
        print(f"File not found: {path}")
        return 1
    
    text = path.read_text()
    
    # Replace <div class="code-block">...</div> with <pre><code class="language-python">escaped</code></pre>
    def repl_codeblock(m):
        inner = m.group(1)
        # Remove span tags but keep inner text
        stripped = re.sub(r'<span[^>]*>([^<]*)</span>', r'\1', inner, flags=re.S|re.I)
        stripped = re.sub(r'<[^>]+>', '', stripped)  # Any remaining tags
        stripped = stripped.strip('\n')
        # Unescape and re-escape for HTML
        unesc = html.unescape(stripped)
        esc = html.escape(unesc)
        return f"<pre><code class=\"language-python\">{esc}</code></pre>"
    
    text = re.sub(r'<div[^>]*class="code-block"[^>]*>(.*?)</div>', repl_codeblock, text, flags=re.S|re.I)
    
    path.write_text(text)
    print(f"Converted and wrote: {path}")
    return 0

if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('docs/k8s-python-api.html')
    sys.exit(convert_file(target))
