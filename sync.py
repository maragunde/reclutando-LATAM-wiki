import os
import base64
import requests
import markdown

# Map each file to its WordPress page ID
FILE_TO_POST_ID = {
    'recursos-dir/eventos.md': 53,
    'recursos-dir/grupos.md': 55,
    'recursos-dir/tools.md': 57,
    'recursos-dir/blogs.md': 59,
    'recursos-dir/newsletters.md': 61,
    'recursos-dir/podcasts.md': 63,
    'recursos-dir/reportes.md': 65,
    'recursos-dir/videos.md': 67,
    'recursos-dir/cursos.md': 69,
    'recursos-dir/vendors.md': 71,
}

def get_auth_header():
    user = os.environ['WP_USER']
    password = os.environ['WP_APP_PASSWORD']
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {'Authorization': f'Basic {token}', 'Content-Type': 'application/json'}

def sync():
    wp_url = os.environ['WP_URL']
    headers = get_auth_header()

    for file_path, post_id in FILE_TO_POST_ID.items():
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        html_content = markdown.markdown(md_content)

        response = requests.post(
            f"{wp_url}/wp-json/wp/v2/pages/{post_id}",
            headers=headers,
            json={'content': html_content}
        )

        print(f"Updated page {post_id} ({file_path}): {response.status_code}")

if __name__ == '__main__':
    sync()