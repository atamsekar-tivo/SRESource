#!/usr/bin/env python3
"""
Flask-based SRESource documentation server.
"""

import logging
import re
from pathlib import Path

import markdown
from flask import Flask, abort, redirect, render_template
from markupsafe import Markup

app = Flask(__name__, template_folder="templates")
app.config["DOCS_DIR"] = Path(__file__).parent / "docs"

# Verify docs directory exists
if not app.config["DOCS_DIR"].exists():
    app.logger.warning("Docs directory not found at %s", app.config["DOCS_DIR"])
else:
    app.logger.info("Docs directory found at %s", app.config["DOCS_DIR"])

# Navigation structure (migrated from mkdocs.yml)
NAV_STRUCTURE = {
    "home": {
        "title": "Home",
        "file": "index.md",
        "path": "/",
    },
    "getting_started": {
        "title": "Getting Started",
        "file": "FORMATTING_GUIDE.md",
        "path": "/getting-started",
    },
    "kubernetes_python": {
        "title": "Kubernetes Python API",
        "file": "k8s-python-api.html",
        "path": "/kubernetes-python",
    },
    "kubernetes": {
        "title": "Kubernetes",
        "path": "/kubernetes",
        "children": {
            "debugging": {
                "title": "Kubernetes Debugging",
                "file": "kubernetes-debugging-commands.html",
                "path": "/kubernetes/debugging",
            },
            "eks": {
                "title": "EKS Production Guide",
                "file": "production-debugging-eks.html",
                "path": "/kubernetes/eks",
            },
        },
    },
    "os": {
        "title": "Operating Systems",
        "path": "/os",
        "children": {
            "unix_linux": {
                "title": "Unix/Linux Debugging",
                "file": "production-debugging-unix-linux.html",
                "path": "/os/unix-linux",
            },
            "linux_internals": {
                "title": "Linux Internals",
                "file": "linux-internals.html",
                "path": "/os/linux-internals",
            },
        },
    },
    "networking": {
        "title": "Networking",
        "path": "/networking",
        "children": {
            "debugging": {
                "title": "Network Debugging",
                "file": "production-networking-debugging.html",
                "path": "/networking/debugging",
            }
        },
    },
    "cicd": {
        "title": "CI/CD",
        "path": "/cicd",
        "children": {
            "tools": {
                "title": "CI/CD Tools & Platforms",
                "file": "production-debugging-ci-cd-tools.html",
                "path": "/cicd/tools",
            },
            "templates": {
                "title": "CI/CD Pipeline Templates",
                "file": "cicd-pipeline-templates.html",
                "path": "/cicd/templates",
            },
        },
    },
    "cloud": {
        "title": "Cloud & Infrastructure",
        "path": "/cloud",
        "children": {
            "iam": {
                "title": "IAM & Access Control",
                "file": "production-debugging-iam.html",
                "path": "/cloud/iam",
            },
            "kafka": {
                "title": "Kafka Debugging",
                "file": "kafka-debugging.html",
                "path": "/cloud/kafka",
            },
        },
    },
    "databases": {
        "title": "Databases",
        "path": "/databases",
        "children": {
            "rdbms": {
                "title": "MySQL & PostgreSQL",
                "file": "production-debugging-databases.html",
                "path": "/databases/rdbms",
            }
        },
    },
    "tools": {
        "title": "Tools & Resources",
        "path": "/tools",
        "children": {
            "guide": {
                "title": "Essential Tools Guide",
                "file": "TOOLS_GUIDE.html",
                "path": "/tools/guide",
            },
            "python": {
                "title": "Python Automation & Debugging",
                "file": "python-debugging-libs.html",
                "path": "/tools/python",
            },
            "rca": {
                "title": "Root Cause Analysis Playbook",
                "file": "root-cause-analysis.html",
                "path": "/tools/rca",
            },
            "interview_playbook": {
                "title": "SRE Interview Playbook (Advanced)",
                "file": "SRE_INTERVIEW_PLAYBOOK_2026.md",
                "path": "/tools/interview-playbook",
            },
            "platform_patterns": {
                "title": "Platform Engineering Patterns (2026)",
                "file": "PLATFORM_ENGINEERING_PATTERNS_2026.md",
                "path": "/tools/platform-patterns",
            },
            "prep_tracks": {
                "title": "Interview Prep Tracks (15/30/60 Days)",
                "file": "INTERVIEW_PREP_TRACKS_2026.md",
                "path": "/tools/prep-tracks",
            },
            "mock_bank": {
                "title": "Mock Interview Question Bank",
                "file": "MOCK_INTERVIEW_BANK_2026.md",
                "path": "/tools/mock-interview-bank",
            },
            "cheatsheets": {
                "title": "SRE Cheat Sheets (Rapid Revision)",
                "file": "SRE_CHEATSHEETS_2026.md",
                "path": "/tools/cheatsheets",
            },
            "books": {
                "title": "Recommended Books (Best Picks)",
                "file": "RECOMMENDED_BOOKS_TECH_INTERVIEWS_2026.md",
                "path": "/tools/recommended-books",
            },
            "top50": {
                "title": "Top 50 Interview Questions + Answers",
                "file": "TOP_50_SRE_INTERVIEW_QA_2026.md",
                "path": "/tools/top-50-questions",
            },
        },
    },
}

@app.context_processor
def inject_nav():
    """Make navigation available to every template, including error pages."""
    return {"nav_structure": NAV_STRUCTURE}

@app.route('/<path:filename>.md')
def legacy_md_redirect(filename):
    """Redirect legacy .md paths to their current routes (HTML-rendered)."""
    file_key = f"{filename}.md"
    if file_key in ROUTE_INDEX:
        return redirect(ROUTE_INDEX[file_key], code=302)
    abort(404)

def get_all_routes():
    """Extract all routes from navigation structure"""
    routes = []
    
    def traverse(nav):
        for item in nav.values():
            if "path" in item:
                routes.append(
                    {
                        "path": item["path"],
                        "file": item.get("file"),
                        "title": item.get("title"),
                    }
                )
            if "children" in item:
                traverse(item["children"])
    
    traverse(NAV_STRUCTURE)
    return routes

ROUTE_INDEX = {item["file"]: item["path"] for item in get_all_routes() if item.get("file")}
PATH_INDEX = {item["path"]: item for item in get_all_routes() if item.get("file")}


def clean_ui_symbols(text):
    """Replace emoji-style markers with professional text labels."""
    replacements = {
        "✅": "[Recommended]",
        "❌": "[Do Not]",
        "⚠️": "[Caution]",
        "⚠": "[Caution]",
        "🚀": "[Deploy]",
        "📋": "[Checklist]",
        "📚": "[Docs]",
        "🔧": "[Setup]",
        "🎉": "[Done]",
        "🐳": "[Docker]",
        "☸️": "[Kubernetes]",
        "☸": "[Kubernetes]",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def read_markdown_file(filename):
    """Read and parse markdown file"""
    file_path = app.config["DOCS_DIR"] / filename
    
    if not file_path.exists():
        app.logger.warning("Markdown file not found: %s", file_path)
        return None, None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = clean_ui_symbols(content)
    except OSError:
        app.logger.exception("Error reading markdown file %s", file_path)
        return None, None
    
    # Convert markdown to HTML
    try:
        html_content = markdown.markdown(
            content,
            extensions=[
                "markdown.extensions.toc",
                "markdown.extensions.codehilite",
                "markdown.extensions.fenced_code",
                "markdown.extensions.tables",
            ],
        )
    except Exception:
        app.logger.exception("Error converting markdown file %s", file_path)
        return None, None
    
    # Extract title from first heading
    title_match = re.search(r"<h1[^>]*>(.+?)</h1>", html_content)
    title = title_match.group(1) if title_match else filename
    
    return Markup(html_content), title

def read_html_file(filename):
    """Read pre-generated HTML file"""
    file_path = app.config["DOCS_DIR"] / filename
    
    if not file_path.exists():
        app.logger.warning("HTML file not found: %s", file_path)
        return None, None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        app.logger.exception("Error reading HTML file %s", file_path)
        return None, None

    title_match = re.search(r"<title>(.+?)</title>", content, flags=re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else filename

    # Normalize full HTML documents so internal pages share one visual standard.
    body_match = re.search(r"<body[^>]*>(.*?)</body>", content, flags=re.IGNORECASE | re.DOTALL)
    if body_match:
        content = body_match.group(1)
    content = clean_ui_symbols(content)
    content = re.sub(r"<script\b[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<style\b[^>]*>.*?</style>", "", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(
        r"<link\b[^>]*rel=[\"']stylesheet[\"'][^>]*>",
        "",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    
    return Markup(content), title

def get_breadcrumbs(current_path):
    """Generate breadcrumb navigation"""
    breadcrumbs = [{"title": "Home", "path": "/"}]
    
    if current_path == "/":
        return breadcrumbs
    
    # Navigate through NAV_STRUCTURE to find current item
    parts = current_path.strip("/").split("/")
    
    def find_in_nav(nav, parts_list, depth=0):
        if depth >= len(parts_list):
            return None
        
        for item in nav.values():
            if item.get("path") == "/" + "/".join(parts_list[: depth + 1]):
                breadcrumbs.append({"title": item.get("title"), "path": item.get("path")})
                if depth < len(parts_list) - 1 and "children" in item:
                    find_in_nav(item["children"], parts_list, depth + 1)
                return True
        return None
    
    find_in_nav(NAV_STRUCTURE, parts)
    return breadcrumbs

def render_doc_page(path):
    """Render documentation page from NAV_STRUCTURE mapping."""
    route_info = PATH_INDEX.get(path)
    if not route_info:
        abort(404)

    filename = route_info["file"]
    is_html = filename.lower().endswith(".html")
    reader = read_html_file if is_html else read_markdown_file
    content, title = reader(filename)
    if content is None:
        abort(404)

    breadcrumbs = get_breadcrumbs(path)

    return render_template(
        "page.html",
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=is_html,
    )


def make_route_handler(route_path):
    """Build a route handler function for route_path."""

    def handler():
        return render_doc_page(route_path)

    handler.__name__ = f"route_{route_path.strip('/').replace('/', '_') or 'home'}"
    return handler


for route in get_all_routes():
    path = route.get("path")
    if not path or not route.get("file"):
        continue
    endpoint_name = f"doc_{path.strip('/').replace('/', '_') or 'home'}"
    app.add_url_rule(path, endpoint=endpoint_name, view_func=make_route_handler(path))

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template("404.html", nav_structure=NAV_STRUCTURE), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    app.logger.exception("500 Error: %s", error)
    return render_template("500.html", nav_structure=NAV_STRUCTURE), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all other exceptions"""
    app.logger.exception("Unhandled Exception: %s", error)
    return render_template("500.html", nav_structure=NAV_STRUCTURE), 500

@app.template_filter('format_nav')
def format_nav(nav_dict):
    """Jinja2 filter for formatting navigation"""
    return nav_dict

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # For development
    app.run(host='0.0.0.0', port=8080, debug=False)
