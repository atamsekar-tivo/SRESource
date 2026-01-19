#!/usr/bin/env python3
"""
Flask-based SRESource documentation server
Replaces mkdocs with dynamic Flask application
"""

import os
import re
import markdown
from pathlib import Path
from flask import Flask, render_template, abort
from datetime import datetime
from markupsafe import Markup

app = Flask(__name__, template_folder='templates')
app.config['DOCS_DIR'] = Path(__file__).parent / 'docs'

# Navigation structure (migrated from mkdocs.yml)
NAV_STRUCTURE = {
    'home': {
        'title': 'Home',
        'file': 'index.md',
        'path': '/'
    },
    'getting_started': {
        'title': 'Getting Started',
        'file': 'FORMATTING_GUIDE.md',
        'path': '/getting-started'
    },
    'kubernetes_python': {
        'title': 'Kubernetes Python API',
        'file': 'k8s-python-api.html',
        'path': '/kubernetes-python'
    },
    'kubernetes': {
        'title': 'Kubernetes',
        'path': '/kubernetes',
        'children': {
            'debugging': {
                'title': 'Kubernetes Debugging',
                'file': 'kubernetes-debugging-commands.html',
                'path': '/kubernetes/debugging'
            },
            'eks': {
                'title': 'EKS Production Guide',
                'file': 'production-debugging-eks.html',
                'path': '/kubernetes/eks'
            }
        }
    },
    'os': {
        'title': 'Operating Systems',
        'path': '/os',
        'children': {
            'unix_linux': {
                'title': 'Unix/Linux Debugging',
                'file': 'production-debugging-unix-linux.html',
                'path': '/os/unix-linux'
            },
            'linux_internals': {
                'title': 'Linux Internals',
                'file': 'linux-internals.html',
                'path': '/os/linux-internals'
            }
        }
    },
    'networking': {
        'title': 'Networking',
        'path': '/networking',
        'children': {
            'debugging': {
                'title': 'Network Debugging',
                'file': 'production-networking-debugging.html',
                'path': '/networking/debugging'
            }
        }
    },
    'cicd': {
        'title': 'CI/CD',
        'path': '/cicd',
        'children': {
            'tools': {
                'title': 'CI/CD Tools & Platforms',
                'file': 'production-debugging-ci-cd-tools.html',
                'path': '/cicd/tools'
            },
            'templates': {
                'title': 'CI/CD Pipeline Templates',
                'file': 'cicd-pipeline-templates.html',
                'path': '/cicd/templates'
            }
        }
    },
    'cloud': {
        'title': 'Cloud & Infrastructure',
        'path': '/cloud',
        'children': {
            'iam': {
                'title': 'IAM & Access Control',
                'file': 'production-debugging-iam.html',
                'path': '/cloud/iam'
            },
            'kafka': {
                'title': 'Kafka Debugging',
                'file': 'kafka-debugging.html',
                'path': '/cloud/kafka'
            }
        }
    },
    'databases': {
        'title': 'Databases',
        'path': '/databases',
        'children': {
            'rdbms': {
                'title': 'MySQL & PostgreSQL',
                'file': 'production-debugging-databases.html',
                'path': '/databases/rdbms'
            }
        }
    },
    'tools': {
        'title': 'Tools & Resources',
        'path': '/tools',
        'children': {
            'guide': {
                'title': 'Essential Tools Guide',
                'file': 'TOOLS_GUIDE.html',
                'path': '/tools/guide'
            },
            'python': {
                'title': 'Python Automation & Debugging',
                'file': 'python-debugging-libs.html',
                'path': '/tools/python'
            },
            'rca': {
                'title': 'Root Cause Analysis Playbook',
                'file': 'root-cause-analysis.html',
                'path': '/tools/rca'
            }
        }
    }
}

def get_all_routes():
    """Extract all routes from navigation structure"""
    routes = []
    
    def traverse(nav):
        for key, item in nav.items():
            if 'path' in item:
                routes.append({
                    'path': item['path'],
                    'file': item.get('file'),
                    'title': item.get('title'),
                })
            if 'children' in item:
                traverse(item['children'])
    
    traverse(NAV_STRUCTURE)
    return routes

def read_markdown_file(filename):
    """Read and parse markdown file"""
    file_path = app.config['DOCS_DIR'] / filename
    
    if not file_path.exists():
        return None, None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        content,
        extensions=['markdown.extensions.toc', 'markdown.extensions.codehilite', 'markdown.extensions.fenced_code', 'markdown.extensions.tables']
    )
    
    # Extract title from first heading
    title_match = re.search(r'<h1[^>]*>(.+?)</h1>', html_content)
    title = title_match.group(1) if title_match else filename
    
    return Markup(html_content), title

def read_html_file(filename):
    """Read pre-generated HTML file"""
    file_path = app.config['DOCS_DIR'] / filename
    
    if not file_path.exists():
        return None, None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract title from HTML title tag
    title_match = re.search(r'<title>(.+?)</title>', content)
    title = title_match.group(1) if title_match else filename
    
    return Markup(content), title

def get_breadcrumbs(current_path):
    """Generate breadcrumb navigation"""
    breadcrumbs = [{'title': 'Home', 'path': '/'}]
    
    if current_path == '/':
        return breadcrumbs
    
    # Navigate through NAV_STRUCTURE to find current item
    parts = current_path.strip('/').split('/')
    
    def find_in_nav(nav, parts_list, depth=0):
        if depth >= len(parts_list):
            return None
        
        for key, item in nav.items():
            if item.get('path') == '/' + '/'.join(parts_list[:depth+1]):
                breadcrumbs.append({'title': item.get('title'), 'path': item.get('path')})
                if depth < len(parts_list) - 1 and 'children' in item:
                    find_in_nav(item['children'], parts_list, depth + 1)
                return True
        return None
    
    find_in_nav(NAV_STRUCTURE, parts)
    return breadcrumbs

@app.route('/')
def index():
    """Homepage"""
    content, title = read_markdown_file('index.md')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE
    )

@app.route('/getting-started')
def getting_started():
    """Getting Started page"""
    content, title = read_markdown_file('FORMATTING_GUIDE.md')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/getting-started')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE
    )

@app.route('/kubernetes/debugging')
def kubernetes_debugging():
    """Kubernetes Debugging page"""
    content, title = read_html_file('kubernetes-debugging-commands.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/kubernetes/debugging')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/kubernetes/eks')
def kubernetes_eks():
    """EKS Production Guide"""
    content, title = read_html_file('production-debugging-eks.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/kubernetes/eks')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/os/unix-linux')
def os_unix_linux():
    """Unix/Linux Debugging"""
    content, title = read_html_file('production-debugging-unix-linux.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/os/unix-linux')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/os/linux-internals')
def os_linux_internals():
    """Linux Internals"""
    content, title = read_html_file('linux-internals.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/os/linux-internals')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/networking/debugging')
def networking_debugging():
    """Network Debugging"""
    content, title = read_html_file('production-networking-debugging.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/networking/debugging')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/cicd/tools')
def cicd_tools():
    """CI/CD Tools & Platforms"""
    content, title = read_html_file('production-debugging-ci-cd-tools.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/cicd/tools')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/cicd/templates')
def cicd_templates():
    """CI/CD Pipeline Templates"""
    content, title = read_html_file('cicd-pipeline-templates.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/cicd/templates')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/cloud/iam')
def cloud_iam():
    """IAM & Access Control"""
    content, title = read_html_file('production-debugging-iam.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/cloud/iam')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/cloud/kafka')
def cloud_kafka():
    """Kafka Debugging"""
    content, title = read_html_file('kafka-debugging.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/cloud/kafka')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/databases/rdbms')
def databases_rdbms():
    """MySQL & PostgreSQL"""
    content, title = read_html_file('production-debugging-databases.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/databases/rdbms')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/tools/guide')
def tools_guide():
    """Essential Tools Guide"""
    content, title = read_html_file('TOOLS_GUIDE.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/tools/guide')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/tools/python')
def tools_python():
    """Python Automation & Debugging"""
    content, title = read_html_file('python-debugging-libs.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/tools/python')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/tools/rca')
def tools_rca():
    """Root Cause Analysis Playbook"""
    content, title = read_html_file('root-cause-analysis.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/tools/rca')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.route('/kubernetes-python')
def kubernetes_python():
    """Kubernetes Python API"""
    content, title = read_html_file('k8s-python-api.html')
    if content is None:
        abort(404)
    
    breadcrumbs = get_breadcrumbs('/kubernetes-python')
    
    return render_template(
        'page.html',
        title=title,
        content=content,
        breadcrumbs=breadcrumbs,
        nav_structure=NAV_STRUCTURE,
        is_html=True
    )

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500

@app.template_filter('format_nav')
def format_nav(nav_dict):
    """Jinja2 filter for formatting navigation"""
    return nav_dict

if __name__ == '__main__':
    # For development
    app.run(host='0.0.0.0', port=8080, debug=True)
