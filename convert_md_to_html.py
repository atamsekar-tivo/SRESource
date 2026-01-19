#!/usr/bin/env python3
"""
Convert markdown files to HTML with professional styling
"""

import os
import subprocess
from pathlib import Path

def convert_md_to_html():
    """Convert all markdown files to HTML"""
    
    docs_dir = Path(__file__).parent / "docs"
    # HTML template (aligned with k8s-python-api look-and-feel)
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="icon" href="assets/favicon.ico">
    <link rel="stylesheet" href="css/html-docs.css">
    <link rel="stylesheet" href="css/pandoc-code.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
</head>
<body>
    <div class="page">
        <header>
            <h1>{title}</h1>
            <p>SRESource — production-ready runbooks with copy-pasteable commands.</p>
            <div class="meta">
                <span class="pill">Commands First</span>
                <span class="pill">Safe Defaults</span>
                <span class="pill">Prod Ready</span>
            </div>
        </header>
        <div class="layout">
            <nav>
                <h2>Contents</h2>
                {toc}
            </nav>
            <main>
                {content}
                <a href="/index.html" class="back-link">← Back to Home</a>
            </main>
        </div>
    </div>
    <script>
        // Highlight.js
        hljs.highlightAll();

        // Add copy buttons to code blocks
        document.querySelectorAll('div.sourceCode').forEach((block) => {{
            const button = document.createElement('button');
            button.className = 'code-copy';
            button.textContent = 'Copy';

            button.addEventListener('click', () => {{
                const code = block.querySelector('code');
                if (!code) return;

                const text = code.innerText.trim();
                navigator.clipboard?.writeText(text).then(() => {{
                    button.textContent = 'Copied';
                    setTimeout(() => (button.textContent = 'Copy'), 1800);
                }}).catch(() => {{
                    // Fallback: select text for manual copy
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(code);
                    selection.removeAllRanges();
                    selection.addRange(range);
                }});
            }});

            block.appendChild(button);
        }});
    </script>
</body>
</html>"""
    
    # Skip files
    skip_files = {'FORMATTING_GUIDE.md', 'index.md'}
    
    md_files = [f for f in docs_dir.glob('*.md') if f.name not in skip_files]
    
    for md_file in md_files:
        html_file = md_file.with_suffix('.html')
        print(f"Converting: {md_file.name} -> {html_file.name}")
        
        try:
            # Convert with pandoc
            result = subprocess.run(
                [
                    'pandoc',
                    str(md_file),
                    '-f',
                    'markdown',
                    '-t',
                    'html5',
                    '--toc',
                    '--toc-depth=3',
                    '--syntax-highlighting=tango',
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            content = result.stdout

            # Drop the top-level <h1> from markdown to avoid duplicate titles (header already shows it)
            if '<h1' in content and '</h1>' in content:
                start = content.find('<h1')
                end = content.find('</h1>', start)
                if end != -1:
                    content = content[:start] + content[end + len('</h1>'):]
            
            # Generate TOC via regex (captures multi-line headings)
            import re
            toc_lines = []
            for tag, indent in (('h2', ''), ('h3', ' style="margin-left: 20px;"')):
                pattern = rf'<{tag}\s+id="([^"]+)">(.*?)</{tag}>'
                for match in re.finditer(pattern, content, re.DOTALL):
                    id_attr, text = match.groups()
                    text = text.strip()
                    toc_lines.append(f'<li{indent}><a href="#{id_attr}">{text}</a></li>')
            
            toc_html = '<ul>' + '\n'.join(toc_lines) + '</ul>' if toc_lines else '<p>No sections</p>'
            
            # Get title
            title = md_file.stem.replace('-', ' ').title()
            for line in content.split('\n'):
                if line.startswith('<h1'):
                    parts = line.split('>')
                    if len(parts) > 1:
                        title = parts[1].split('<')[0]
                    break
            
            # Generate HTML
            html_content = html_template.format(
                title=title,
                toc=toc_html,
                content=content
            )
            
            # Write file
            with open(html_file, 'w') as f:
                f.write(html_content)
            
            print(f"  ✓ Created {html_file.name}")
            
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Error converting {md_file.name}: {e.stderr}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\nConversion complete!")

if __name__ == '__main__':
    convert_md_to_html()
