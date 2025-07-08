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