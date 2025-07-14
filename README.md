# WF Suite Release Proxy

A lightweight Flask service that provides public access to GitHub releases from a private repository.

## Quick Start

### 1. Get Your GitHub Token
1. Go to [GitHub Settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give it a name: "WF Suite Release Proxy"
4. Select scope: `repo` (Full control of private repositories)
5. Generate token and copy it immediately

### 2. Deploy to Railway (Recommended - Free)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/new)

1. Go to [railway.app](https://railway.app) and sign up
2. Click "New Project" → "Empty Project"
3. Add a service and connect your GitHub account
4. Upload the `release_proxy` folder or connect to your repo
5. Set environment variables:
   - `GITHUB_TOKEN`: Your GitHub Personal Access Token
   - `REPO_OWNER`: `gino-vi`
   - `REPO_NAME`: `Wangfang-Suite`
6. Deploy and get your URL: `https://your-project.railway.app`

### 3. Alternative: Deploy to Render (Free)

1. Go to [render.com](https://render.com) and sign up
2. Click "New" → "Web Service"
3. Connect GitHub and select this repo/folder
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Set environment variables (same as Railway)
6. Deploy and get your URL

### 4. Alternative: Deploy to Heroku

1. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Login: `heroku login`
3. Create app: `heroku create your-app-name`
4. Set environment variables:
   ```bash
   heroku config:set GITHUB_TOKEN=your_token_here
   heroku config:set REPO_OWNER=gino-vi
   heroku config:set REPO_NAME=Wangfang-Suite
   ```
5. Deploy: `git push heroku main`

## Testing Your Deployment

### Test the endpoints:
```bash
# Check service status
curl https://your-app.railway.app/

# Check health
curl https://your-app.railway.app/health

# Get releases (what WF Suite will call)
curl https://your-app.railway.app/releases
```

## Configure WF Suite

Once deployed, you'll need to update WF Suite to use your proxy instead of direct GitHub access.

**Your proxy URL will be something like:**
- Railway: `https://your-project.railway.app`
- Render: `https://your-service.onrender.com`
- Heroku: `https://your-app.herokuapp.com`

## Service Features

- **Caching**: Responses cached for 5 minutes to reduce GitHub API calls
- **Rate Limiting**: 30 requests per minute per IP to prevent abuse
- **Error Handling**: Graceful error responses and logging
- **Security**: Only exposes release information, never source code
- **Monitoring**: Health check endpoint for uptime monitoring

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes | - | GitHub Personal Access Token |
| `REPO_OWNER` | No | `gino-vi` | Repository owner |
| `REPO_NAME` | No | `Wangfang-Suite` | Repository name |
| `PORT` | No | `5000` | Port to run on (set by platform) |

## API Endpoints

- `GET /` - Service information
- `GET /releases` - Get filtered release information
- `GET /health` - Health check for monitoring

## Security Notes

- The GitHub token is only stored on your server (never in client apps)
- Only release information is exposed (never source code)
- Rate limiting prevents abuse
- CORS enabled for web requests

## Troubleshooting

### Common Issues:

1. **"Service configuration error"** - GitHub token not set
2. **"Failed to fetch releases"** - Token doesn't have `repo` scope or repository doesn't exist
3. **Empty releases array** - No releases with .exe files found

### Check logs:
- Railway: Project → Deployments → View Logs
- Render: Service → Logs tab
- Heroku: `heroku logs --tail`

## Cost

All recommended platforms offer generous free tiers:
- **Railway**: 500 hours/month free
- **Render**: Unlimited for small apps (sleeps after 15min idle)
- **Heroku**: 550-1000 hours/month free (with verification)

This tiny service will use minimal resources and stay well within free limits. 
