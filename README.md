# WF Suite Release Proxy

A lightweight Flask service that provides public access to GitHub releases from a private repository.


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
