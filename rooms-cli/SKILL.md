---
name: rooms-cli
description: "使用 rooms-cli 查询会议室地图、搜索会议室、查看占用、预订和释放会议室。适用于找会议室、查某个房间的议程、精确预订或释放会议室。"
---

## Workflow

Collect required inputs first:

- `where` for fuzzy search, such as city/building/floor/room keywords
- `room_id` for agenda or booking
- `building_id` / `floor_id` when the scope is already known
- `schedule_id` for release
- precise meeting time for `book`

Default to `--json` for agent workflows.
Use `map` and `search` to discover ids first; writes should use exact ids.

Only handle `auth/config/map/search/agenda/book/release`.

## Discovery

Refresh the local city-building-floor map when location cache may be stale:

```bash
rooms-cli map refresh --json
```

Read the cached hierarchy:

```bash
rooms-cli map get --json
rooms-cli map get --flat --json
```

Fuzzy search by keywords:

```bash
rooms-cli search --where "北京 研发园 F/G 3F" --json
rooms-cli search --where "嫩江厅" --json
rooms-cli search --where "研发园FG 3F" --when "tomorrow 2-3pm" --json
```

Rules:

- `--where` is for fuzzy discovery only.
- `--when` is optional search assistance, not a substitute for exact booking time.
- Prefer extracting exact `roomId`, `buildingId`, `floorId` from search results before follow-up actions.

## Agenda

Check booked agenda for one or more rooms:

```bash
rooms-cli agenda --room-id 63 --json
rooms-cli agenda --room-id 63,64 --date 2026-03-14 --json
```

Use this to confirm occupancy before booking, or to inspect an existing room by exact id.

## Booking

Booking must use exact ids and exact time.

```bash
rooms-cli book \
  --room-id "$ROOM_ID" \
  --title "$TITLE" \
  --start "2026-03-14 14:00" \
  --end "2026-03-14 15:00" \
  --json
```

If attendees are needed:

```bash
rooms-cli book \
  --room-id "$ROOM_ID" \
  --title "$TITLE" \
  --start "2026-03-14 14:00" \
  --end "2026-03-14 15:00" \
  --attendee "$MIS_1" \
  --attendee "$MIS_2" \
  --json
```

Execution rules:

- Do not book from fuzzy names alone; resolve to an exact `room_id` first.
- Prefer reading current occupancy first when the target slot may conflict.
- After booking, return at least `scheduleId`, room name, and final time window.

## Release

Release a booked meeting room by exact schedule id:

```bash
rooms-cli release --schedule-id "$SCHEDULE_ID" --json
```

Rules:

- Only use `release` when the user clearly wants to free the room.
- Confirm `schedule_id` from prior output or an explicit user-provided id.

## Auth and Config

Check current login/config when commands fail with auth/session errors:

```bash
rooms-cli auth whoami --json
rooms-cli auth token
rooms-cli config show --json
```

If login is needed, use MTCLILoginHelper.app:

```bash
open /Applications/MTCLILoginHelper.app
```

Select Rooms service and complete login in the app.

## Execution Rules

- Reads can use fuzzy search; writes must use exact ids.
- Prefer `map` + `search` for discovery, then `agenda` or `book`.
- If the user asks for “找一个合适的会议室”, first search candidates and summarize the best ids/options before booking.
- If command returns auth/session errors, refresh login and retry once.

## Reference

Prefer the latest repo docs:

- `/Users/huanghao/workspace/mt-cli/man/rooms-cli.1`
- `/Users/huanghao/workspace/mt-cli/man/rooms-cli.config.5`
- `/Users/huanghao/workspace/mt-cli/docs/design/20260312-rooms-cli-design.md`
