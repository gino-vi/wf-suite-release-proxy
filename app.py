#!/usr/bin/env python3
"""
WF Suite Release Proxy Service
=============================

A lightweight Flask service that provides public access to GitHub releases
from a private repository without exposing source code.

Environment Variables Required:
- GITHUB_TOKEN: Your GitHub Personal Access Token
- REPO_OWNER: Repository owner (default: gino-vi)
- REPO_NAME: Repository name (default: Wangfang-Suite)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os
import logging
from datetime import datetime, timedelta
from functools import wraps
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for web requests

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO_OWNER = os.environ.get('REPO_OWNER', 'gino-vi')
REPO_NAME = os.environ.get('REPO_NAME', 'Wangfang-Suite')
CACHE_DURATION_MINUTES = 5

# Simple in-memory cache
cache = {
    'data': None,
    'timestamp': None
}

def rate_limit(max_requests_per_minute=60):
    """Simple rate limiting decorator"""
    requests_log = []
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            now = time.time()
            # Clean old requests
            requests_log[:] = [req_time for req_time in requests_log if now - req_time < 60]
            
            if len(requests_log) >= max_requests_per_minute:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            requests_log.append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_cache_valid():
    """Check if cached data is still valid"""
    if cache['data'] is None or cache['timestamp'] is None:
        return False
    
    cache_age = datetime.now() - cache['timestamp']
    return cache_age < timedelta(minutes=CACHE_DURATION_MINUTES)

@app.route('/')
def home():
    """Service information endpoint"""
    return jsonify({
        'service': 'WF Suite Release Proxy',
        'status': 'operational',
        'repository': f'{REPO_OWNER}/{REPO_NAME}',
        'endpoints': {
            '/releases': 'Get available releases',
            '/releases/download/<tag_name>/<asset_name>': 'Download release asset',
            '/health': 'Health check'
        }
    })

@app.route('/releases')
@rate_limit(max_requests_per_minute=30)
def get_releases():
    """Get releases from GitHub repository"""
    try:
        # Return cached data if valid
        if is_cache_valid():
            logger.info("Returning cached release data")
            return jsonify(cache['data'])
        
        # Validate GitHub token
        if not GITHUB_TOKEN:
            logger.error("GitHub token not configured")
            return jsonify({'error': 'Service configuration error'}), 500
        
        # Setup headers for GitHub API
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'WF-Suite-Release-Proxy/1.0'
        }
        
        # Fetch releases from GitHub
        url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases'
        logger.info(f"Fetching releases from: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        all_releases = response.json()
        logger.info(f"Retrieved {len(all_releases)} releases from GitHub")
        
        # Filter and clean release data for public consumption
        public_releases = []
        for release in all_releases:
            # Skip draft releases
            if release.get('draft', False):
                continue
            
            # Filter assets to only include .exe files
            filtered_assets = []
            for asset in release.get('assets', []):
                if asset['name'].endswith('.exe'):
                    filtered_assets.append({
                        'name': asset['name'],
                        'browser_download_url': asset['browser_download_url'],
                        'size': asset.get('size', 0),
                        'created_at': asset.get('created_at')
                    })
            
            # Only include releases that have .exe assets
            if filtered_assets:
                public_release = {
                    'tag_name': release['tag_name'],
                    'name': release.get('name', release['tag_name']),
                    'prerelease': release.get('prerelease', False),
                    'body': release.get('body', ''),
                    'html_url': release['html_url'],
                    'published_at': release.get('published_at'),
                    'assets': filtered_assets
                }
                public_releases.append(public_release)
        
        # Update cache
        cache['data'] = public_releases
        cache['timestamp'] = datetime.now()
        
        logger.info(f"Returning {len(public_releases)} public releases")
        return jsonify(public_releases)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        return jsonify({'error': 'Failed to fetch releases from GitHub'}), 502
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test GitHub API connectivity
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        } if GITHUB_TOKEN else {}
        
        response = requests.get(
            f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}',
            headers=headers,
            timeout=5
        )
        
        github_status = 'connected' if response.status_code == 200 else 'error'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'github_api': github_status,
            'cache_valid': is_cache_valid(),
            'repository': f'{REPO_OWNER}/{REPO_NAME}'
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/releases/download/<tag_name>/<asset_name>')
@rate_limit(max_requests_per_minute=10)  # Lower rate limit for downloads
def download_release_asset(tag_name, asset_name):
    """Download a release asset using GitHub token authentication"""
    try:
        # Validate GitHub token
        if not GITHUB_TOKEN:
            logger.error("GitHub token not configured")
            return jsonify({'error': 'Service configuration error'}), 500
        
        # Validate asset name (only allow .exe files)
        if not asset_name.endswith('.exe'):
            logger.warning(f"Invalid asset requested: {asset_name}")
            return jsonify({'error': 'Only .exe files are allowed'}), 400
        
        # Setup headers for GitHub API
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/octet-stream',
            'User-Agent': 'WF-Suite-Release-Proxy/1.0'
        }
        
        # Construct GitHub download URL
        download_url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/assets'
        
        # First, get the release to find the asset ID
        release_url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{tag_name}'
        logger.info(f"Fetching release info for {tag_name}")
        
        release_response = requests.get(release_url, headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'WF-Suite-Release-Proxy/1.0'
        }, timeout=10)
        release_response.raise_for_status()
        
        release_data = release_response.json()
        
        # Find the asset ID for the requested file
        asset_id = None
        for asset in release_data.get('assets', []):
            if asset['name'] == asset_name:
                asset_id = asset['id']
                break
        
        if not asset_id:
            logger.warning(f"Asset {asset_name} not found in release {tag_name}")
            return jsonify({'error': 'Asset not found'}), 404
        
        # Download the asset using GitHub API
        asset_url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/assets/{asset_id}'
        logger.info(f"Downloading asset {asset_name} from {asset_url}")
        
        def generate():
            """Stream the file content"""
            with requests.get(asset_url, headers=headers, stream=True, timeout=30) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
        
        # Get file size for Content-Length header
        asset_size = next((asset['size'] for asset in release_data.get('assets', []) if asset['name'] == asset_name), 0)
        
        # Stream the file back to the client
        from flask import Response
        return Response(
            generate(),
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{asset_name}"',
                'Content-Length': str(asset_size) if asset_size > 0 else None
            }
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        return jsonify({'error': 'Failed to download from GitHub'}), 502
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': 'Download failed'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Validate configuration
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN environment variable is required")
        exit(1)
    
    logger.info(f"Starting WF Suite Release Proxy for {REPO_OWNER}/{REPO_NAME}")
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(
        debug=False,
        host='0.0.0.0',
        port=port
    ) 