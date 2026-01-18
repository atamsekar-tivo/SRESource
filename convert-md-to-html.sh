#!/bin/bash
# Convert all markdown files to HTML

set -e

cd "$(dirname "$0")/docs"

echo "Converting Markdown files to HTML..."

for md_file in *.md; do
    if [ "$md_file" = "FORMATTING_GUIDE.md" ]; then
        continue
    fi
    
    html_file="${md_file%.md}.html"
    
    echo "Converting: $md_file -> $html_file"
    
    pandoc "$md_file" \
        -f markdown \
        -t html5 \
        --css-extra="/css/custom.css" \
        --standalone \
        --toc \
        --toc-depth=3 \
        --template=<(cat <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title$</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.8;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 20px;
            padding: 20px;
        }
        
        nav {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            height: fit-content;
            position: sticky;
            top: 20px;
        }
        
        nav h2 {
            font-size: 1em;
            color: #1976D2;
            margin-bottom: 15px;
            border-bottom: 2px solid #2196F3;
            padding-bottom: 10px;
        }
        
        nav ul {
            list-style: none;
        }
        
        nav li {
            margin-bottom: 8px;
        }
        
        nav a {
            color: #2196F3;
            text-decoration: none;
            font-size: 0.9em;
            display: block;
            padding: 6px 10px;
            border-radius: 4px;
            transition: all 0.3s;
        }
        
        nav a:hover {
            background: #f0f0f0;
            transform: translateX(5px);
        }
        
        main {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        
        h1 {
            color: #1976D2;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #2196F3;
        }
        
        h2 {
            color: #1976D2;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e0e0e0;
        }
        
        h3 {
            color: #2196F3;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        p {
            margin-bottom: 15px;
            line-height: 1.8;
        }
        
        code {
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            color: #d63384;
        }
        
        pre {
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 15px 0;
            border-left: 3px solid #00ff00;
        }
        
        pre code {
            background: transparent;
            color: #00ff00;
            padding: 0;
            border-radius: 0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th {
            background: #2196F3;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        tbody tr:hover {
            background: #f5f5f5;
        }
        
        ul, ol {
            margin-left: 30px;
            margin-bottom: 15px;
        }
        
        li {
            margin-bottom: 8px;
        }
        
        blockquote {
            border-left: 4px solid #2196F3;
            padding-left: 15px;
            margin: 15px 0;
            color: #666;
        }
        
        .back-link {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: #2196F3;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            transition: background 0.3s;
        }
        
        .back-link:hover {
            background: #1976D2;
        }
        
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
            }
            
            nav {
                position: relative;
                top: 0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <h2>Contents</h2>
            $toc$
        </nav>
        <main>
            $body$
            <a href="/index.html" class="back-link">← Back to Home</a>
        </main>
    </div>
</body>
</html>
EOF
) \
        -o "$html_file"
done

echo "Conversion complete!"
