# PBI-4: Host release proxy on a free-forever platform

[View in Backlog](../backlog.md#user-content-pbi-4)

## Overview
Migrate the existing `release_proxy` Flask service running on Railway to a free or nearly-free platform with sustainable availability.

## Problem Statement
Railway free credits ran out, stopping the service. We need a durable, low-cost or free alternative to serve release metadata and assets.

## User Stories
- As a maintainer, I want the release proxy hosted on a free-forever platform so distribution remains reliable without ongoing cost.

## Technical Approach
- Implement a Cloudflare Worker that replicates the `release_proxy` endpoints:
  - `GET /` service info
  - `GET /releases` fetches and filters GitHub releases (omit SHA256 initially)
  - `GET /releases/download/<tag>/<asset>` streams assets via GitHub API
- Use Worker secrets for `GITHUB_TOKEN`, optional `REPO_OWNER`, `REPO_NAME`.
- Cache `/releases` responses briefly using the default Workers Cache.
- Keep response structure compatible with the current app.

## UX/UI Considerations
No UI changes. Endpoints remain the same for the consumer in the app.

## Acceptance Criteria
- Worker deployed and publicly reachable.
- `/releases` returns a filtered list of releases including `.exe` assets.
- `/releases/download/<tag>/<asset>` streams downloads successfully.
- Secrets managed in Workers, not in code.
- Documented deploy steps.

## Dependencies
- Cloudflare account + Workers
- GitHub Personal Access Token with repo read access

## Open Questions
- Do we need SHA256 hashing at edge? (likely separate task using KV/R2)

## Related Tasks
- [Tasks](./tasks.md)
