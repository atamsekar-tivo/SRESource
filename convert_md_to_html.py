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
    
    # HTML template
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.8;
            color: #333;
            background-color: #f5f5f5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 20px;
            padding: 20px;
        }}
        
        nav {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            height: fit-content;
            position: sticky;
            top: 20px;
        }}
        
        nav h2 {{
            font-size: 1em;
            color: #1976D2;
            margin-bottom: 15px;
            border-bottom: 2px solid #2196F3;
            padding-bottom: 10px;
        }}
        
        nav ul {{
            list-style: none;
        }}
        
        nav li {{
            margin-bottom: 5px;
        }}
        
        nav a {{
            color: #2196F3;
            text-decoration: none;
            font-size: 0.9em;
            display: block;
            padding: 6px 10px;
            border-radius: 4px;
            transition: all 0.3s;
        }}
        
        nav a:hover {{
            background: #f0f0f0;
            transform: translateX(5px);
        }}
        
        main {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        h1 {{
            color: #1976D2;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #2196F3;
        }}
        
        h2 {{
            color: #1976D2;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        h3 {{
            color: #2196F3;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        
        p {{
            margin-bottom: 15px;
            line-height: 1.8;
        }}
        
        code {{
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            color: #d63384;
        }}
        
        pre {{
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 15px 0;
            border-left: 3px solid #00ff00;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        pre code {{
            background: transparent;
            color: #00ff00;
            padding: 0;
            border-radius: 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        th {{
            background: #2196F3;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tbody tr:hover {{
            background: #f5f5f5;
        }}
        
        ul, ol {{
            margin-left: 30px;
            margin-bottom: 15px;
        }}
        
        li {{
            margin-bottom: 8px;
        }}
        
        blockquote {{
            border-left: 4px solid #2196F3;
            padding-left: 15px;
            margin: 15px 0;
            color: #666;
        }}
        
        .back-link {{
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: #2196F3;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            transition: background 0.3s;
        }}
        
        .back-link:hover {{
            background: #1976D2;
        }}
        
        .toc {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        
        .toc ul {{
            margin-left: 20px;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                grid-template-columns: 1fr;
            }}
            
            nav {{
                position: relative;
                top: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <h2>Contents</h2>
            {toc}
        </nav>
        <main>
            {content}
            <a href="/index.html" class="back-link">← Back to Home</a>
        </main>
    </div>
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
                ['pandoc', str(md_file), '-f', 'markdown', '-t', 'html5', '--toc', '--toc-depth=3'],
                capture_output=True,
                text=True,
                check=True
            )
            
            content = result.stdout
            
            # Generate TOC
            toc_lines = []
            for line in content.split('\n'):
                if line.startswith('<h2 id='):
                    parts = line.split('>')
                    if len(parts) > 1:
                        text = parts[1].split('<')[0]
                        id_attr = line.split('id="')[1].split('"')[0] if 'id="' in line else ''
                        if id_attr:
                            toc_lines.append(f'<li><a href="#{id_attr}">{text}</a></li>')
                elif line.startswith('<h3 id='):
                    parts = line.split('>')
                    if len(parts) > 1:
                        text = parts[1].split('<')[0]
                        id_attr = line.split('id="')[1].split('"')[0] if 'id="' in line else ''
                        if id_attr:
                            toc_lines.append(f'<li style="margin-left: 20px;"><a href="#{id_attr}">{text}</a></li>')
            
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
