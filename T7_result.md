# T7 Result: Distillery INDEX page (ISR)

## Task
Create webapp-next/app/distilleries/page.tsx with ISR 12h, getDistilleries(limit,offset) positional args, hasNext pagination, server-rendered links (no typeof window), error fallback, alphabetical sort, metadata export. Build+lint green.

## Files Created
- webapp-next/app/distilleries/page.tsx

## Verification
- Build: `npm run build` exited with code 0.
- Lint: `npx eslint .` exited with code 0.

## Notes
- The page uses the MaltRadarApi client to fetch distilleries with pagination.
- Implements ISR with revalidate = 43200 (12 hours).
- Sorts distilleries alphabetically by name.
- Includes previous/next pagination links using server-rendered Next.js Link.
- Error fallback returns empty array and zero total count.
- Exports metadata for SEO.
- No new components were created; used existing types and API.
- No modifications to T1-T6 files (read-only compliance).

## Outcome
The Distilleries index page is successfully implemented and passes build and lint checks.