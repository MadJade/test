from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
import re

app = Flask(__name__)

def fetch_invidious_search_results(query, base_url="https://invidious.nerdvpn.de"):
    search_url = f"{base_url}/search?q={query}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/87.0.4280.88 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return {"error": f"Error fetching data: {e}"}, 500

    soup = BeautifulSoup(response.text, 'html.parser')
    video_divs = soup.find_all('div', class_='pure-u-1 pure-u-md-1-4')

    videos = []

    for video in video_divs:
        video_data = {}

        # Extract Thumbnail
        thumbnail_div = video.find('div', class_='thumbnail')
        if thumbnail_div:
            a_tag = thumbnail_div.find('a', href=True)
            if a_tag:
                img_tag = a_tag.find('img', class_='thumbnail')
                if img_tag and img_tag.get('src'):
                    thumbnail_url = img_tag['src']
                    if thumbnail_url.startswith('/'):
                        thumbnail_url = base_url + thumbnail_url
                    video_data['thumbnail'] = thumbnail_url
                else:
                    video_data['thumbnail'] = None
            else:
                video_data['thumbnail'] = None
        else:
            video_data['thumbnail'] = None

        # Extract Title and URL
        title_div = video.find('div', class_='video-card-row')
        if title_div:
            a_tag = title_div.find('a', href=True)
            if a_tag:
                title = a_tag.get_text(strip=True)
                video_url = a_tag['href']
                if video_url.startswith('/'):
                    video_url = base_url + video_url
                video_data['title'] = title
                video_data['url'] = video_url
            else:
                video_data['title'] = None
                video_data['url'] = None
        else:
            video_data['title'] = None
            video_data['url'] = None

        # Initialize fields
        channel_name = None
        views = 0
        upload_date = None

        # Extract Channel Name, Views, and Upload Date
        flexible_divs = video.find_all('div', class_='video-card-row flexible')
        for flexible_div in flexible_divs:
            flex_left_div = flexible_div.find('div', class_='flex-left')
            flex_right_div = flexible_div.find('div', class_='flex-right')

            # Extract Channel Name
            if flex_left_div:
                channel_p = flex_left_div.find('p', class_='channel-name')
                if channel_p:
                    channel_name_text = channel_p.get_text(separator=' ', strip=True)
                    channel_name = re.split(r'\s+[\u2713\u2714✔✓]\s*', channel_name_text)[0].strip()
                else:
                    # Assume it's upload_date
                    video_data_p = flex_left_div.find('p', class_='video-data')
                    if video_data_p:
                        upload_date = video_data_p.get_text(strip=True)

            # Extract Views
            if flex_right_div:
                video_data_p = flex_right_div.find('p', class_='video-data')
                if video_data_p:
                    text = video_data_p.get_text(strip=True)
                    views_match = re.search(r'([\d.,KkMm]+)', text)
                    if views_match:
                        views_str = views_match.group(1)
                        parsed_views = parse_views(views_str)
                        if parsed_views is not None:
                            views = parsed_views

        video_data['channel_name'] = channel_name if channel_name else None
        video_data['views'] = views
        video_data['upload_date'] = upload_date if upload_date else None

        # Append to list if title and url are present
        if video_data.get('title') and video_data.get('url'):
            videos.append(video_data)

    return {"videos": videos}

def parse_views(views_str):
    views_str = views_str.replace(',', '').replace('.', '').upper()
    multiplier = 1
    if 'K' in views_str:
        multiplier = 1_000
        views_str = views_str.replace('K', '')
    elif 'M' in views_str:
        multiplier = 1_000_000
        views_str = views_str.replace('M', '')
    try:
        return int(float(views_str) * multiplier)
    except ValueError:
        return 0

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', default="", type=str).strip()
    if not query:
        return jsonify({"error": "Query parameter 'q' is required."}), 400

    base_invidious_url = "https://invidious.nerdvpn.de"
    result = fetch_invidious_search_results(query, base_invidious_url)

    # Check if an error occurred during fetching
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]

    return jsonify(result)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Invidious Search API",
        "usage": "/search?q=<your_query>"
    })

if __name__ == "__main__":
    # Run the Flask app on localhost:5000
    app.run(host='0.0.0.0', port=5000, debug=True)
