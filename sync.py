import os
import base64
import requests
import markdown
import re

FILE_TO_POST_ID = {
    'recursos-dir/eventos.md': 53,
    'recursos-dir/grupos.md':  55,
    'recursos-dir/tools.md':   57,
    'recursos-dir/blogs.md':   59,
    'recursos-dir/newsletters.md': 61,
    'recursos-dir/podcasts.md': 63,
    'recursos-dir/reportes.md': 65,
    'recursos-dir/videos.md':  67,
    'recursos-dir/cursos.md':  69,
    'recursos-dir/vendors.md': 71,
}

def md_table_to_cards(md_content):
    """Convert the eventos MD table into styled HTML cards."""
    lines = md_content.strip().split('\n')
    rows = []
    for line in lines:
        if line.startswith('|') and '---' not in line and line.strip() != '':
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            rows.append(cells)

    if len(rows) < 2:
        return markdown.markdown(md_content, extensions=['tables'])

    # rows[0] = headers, rows[1:] = data
    events = rows[1:]

    cards_html = '''
<style>
.eventos-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    margin: 24px 0;
}
.evento-card {
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 20px;
    background: #fff;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}
.evento-card h3 {
    margin: 0 0 8px;
    font-size: 16px;
    color: #111;
}
.evento-card .desc {
    font-size: 14px;
    color: #555;
    margin-bottom: 12px;
    line-height: 1.5;
}
.evento-card .meta {
    font-size: 13px;
    color: #777;
    margin-bottom: 4px;
}
.evento-card .meta strong {
    color: #333;
}
.evento-card a {
    display: inline-block;
    margin-top: 14px;
    padding: 8px 16px;
    background: #111;
    color: #fff;
    border-radius: 6px;
    text-decoration: none;
    font-size: 13px;
}
.evento-card a:hover { background: #333; }
</style>
<div class="eventos-grid">
'''
    for event in events:
        if len(event) < 5:
            continue
        nombre, desc, fecha, link_raw, donde = event[0], event[1], event[2], event[3], event[4]

        # Extract URL from markdown link [LINK](url)
        url_match = re.search(r'\[.*?\]\((.*?)\)', link_raw)
        url = url_match.group(1) if url_match else '#'

        cards_html += f'''
    <div class="evento-card">
        <h3>{nombre}</h3>
        <p class="desc">{desc}</p>
        <p class="meta">📅 <strong>{fecha}</strong></p>
        <p class="meta">📍 {donde}</p>
        <a href="{url}" target="_blank" rel="noopener">Ver evento →</a>
    </div>'''

    cards_html += '\n</div>'
    return cards_html

def get_auth_header():
    user = os.environ['WP_USER']
    password = os.environ['WP_APP_PASSWORD']
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {'Authorization': f'Basic {token}'}

def sync():
    wp_url = os.environ['WP_URL'].rstrip('/')
    headers = get_auth_header()

    for file_path, post_id in FILE_TO_POST_ID.items():
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Use card layout for eventos, standard markdown for everything else
        if file_path == 'recursos-dir/eventos.md':
            html_content = md_table_to_cards(md_content)
        else:
            html_content = markdown.markdown(md_content, extensions=['tables'])

        response = requests.post(
            f"{wp_url}/wp-json/wp/v2/pages/{post_id}",
            headers=headers,
            json={'content': html_content}
        )

        print(f"Updated page {post_id} ({file_path}): {response.status_code}")

if __name__ == '__main__':
    sync()