import os
import base64
import requests
import markdown
import re
import urllib.parse

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

# Cache for uploaded PDFs: maps local path -> WordPress URL
pdf_upload_cache = {}

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

def test_wordpress_connection(wp_url, headers):
    """Test if we can connect to WordPress and if user has proper permissions."""
    try:
        # Test basic connection
        response = requests.get(f"{wp_url}/wp-json/", headers=headers, timeout=5)
        print(f"✅ WordPress REST API accessible: {response.status_code}")
        
        # Test authentication
        response = requests.get(f"{wp_url}/wp-json/wp/v2/users/me", headers=headers, timeout=5)
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Authenticated as: {user_info.get('name')}")
            caps = user_info.get('capabilities', {})
            if caps.get('upload_files'):
                print(f"✅ User has upload_files capability")
            else:
                print(f"⚠️  User may NOT have upload_files capability")
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def extract_pdf_paths(md_content):
    """Extract all PDF file paths from markdown content."""
    # Match patterns like ./pdfreports/filename.pdf or [text](./pdfreports/filename.pdf)
    pattern = r'\./pdfreports/[^\s\)"\']+'
    matches = re.findall(pattern, md_content)
    return list(set(matches))  # Remove duplicates

def upload_pdf_to_wordpress(wp_url, headers, local_path):
    """Upload a PDF file to WordPress Media Library and return the media URL."""
    if local_path in pdf_upload_cache:
        print(f"  Using cached URL for {local_path}")
        return pdf_upload_cache[local_path]
    
    if not os.path.exists(local_path):
        print(f"  ❌ PDF file not found: {local_path}")
        return None
    
    filename = os.path.basename(local_path)
    
    try:
        # Read file content
        with open(local_path, 'rb') as f:
            file_content = f.read()
        
        # Create headers for file upload (must not include Content-Type for multipart)
        upload_headers = headers.copy()
        
        # Upload file
        files = {'file': (filename, file_content, 'application/pdf')}
        response = requests.post(
            f"{wp_url}/wp-json/wp/v2/media",
            headers=upload_headers,
            files=files
        )
        
        print(f"  📤 Upload response for {filename}: {response.status_code}")
        
        if response.status_code in [200, 201]:
            response_data = response.json()
            media_url = response_data.get('source_url')
            if media_url:
                pdf_upload_cache[local_path] = media_url
                print(f"  ✅ Uploaded {filename}: {media_url}")
                return media_url
            else:
                print(f"  ⚠️  File uploaded but no source_url in response: {response_data}")
                return None
        else:
            error_msg = response.text[:500] if response.text else "No error details"
            print(f"  ❌ Failed to upload {filename}: HTTP {response.status_code}")
            print(f"     Error: {error_msg}")
            return None
    except Exception as e:
        print(f"  ❌ Error uploading {local_path}: {type(e).__name__}: {e}")
        import traceback
        print(f"     Traceback: {traceback.format_exc()[:200]}")
        return None

def replace_pdf_paths_with_urls(html_content, pdf_urls_map):
    """Replace relative PDF paths with WordPress media URLs in HTML content."""
    for local_path, wp_url in pdf_urls_map.items():
        if wp_url:
            # Replace the relative path with the WordPress URL
            html_content = html_content.replace(local_path, wp_url)
    return html_content

def sync():
    wp_url = os.environ['WP_URL'].rstrip('/')
    headers = get_auth_header()
    
    print(f"🔗 Syncing to: {wp_url}\n")
    
    # Test WordPress connection first
    if not test_wordpress_connection(wp_url, headers):
        print("\n❌ Cannot proceed - WordPress connection failed")
        return

    for file_path, post_id in FILE_TO_POST_ID.items():
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Extract and upload PDFs first
        pdf_paths = extract_pdf_paths(md_content)
        pdf_urls_map = {}
        
        if pdf_paths:
            print(f"\n📄 Processing PDFs for {file_path}:")
            for pdf_path in pdf_paths:
                # Convert relative path to absolute
                abs_pdf_path = pdf_path.lstrip('./')
                wp_media_url = upload_pdf_to_wordpress(wp_url, headers, abs_pdf_path)
                pdf_urls_map[pdf_path] = wp_media_url

        # Use card layout for eventos, standard markdown for everything else
        if file_path == 'recursos-dir/eventos.md':
            html_content = md_table_to_cards(md_content)
        else:
            html_content = markdown.markdown(md_content, extensions=['tables'])

        # Replace relative PDF paths with WordPress URLs
        html_content = replace_pdf_paths_with_urls(html_content, pdf_urls_map)

        response = requests.post(
            f"{wp_url}/wp-json/wp/v2/pages/{post_id}",
            headers=headers,
            json={'content': html_content}
        )

        print(f"✅ Updated page {post_id} ({file_path}): {response.status_code}\n")

if __name__ == '__main__':
    sync()