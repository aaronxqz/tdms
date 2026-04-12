# Task Distribution and Management System

**Document Version:** 1.2  
**Last Updated:** 2026-04-12  
**Status:** Complete

---

## Update Log

| Version | Date       | Change Summary                                                                 |
|---------|------------|--------------------------------------------------------------------------------|
| 1.0     | —          | Initial draft created                                                          |
| 1.1     | 2026-04-10 | Structural polish; added Google Calendar API integration spec; added Goal layer, system-wide counters, search, and status history |
| 1.2     | 2026-04-12 | Specification finalised and marked complete. Full-stack implementation delivered: FastAPI backend (release v1.0.0), React/Vite frontend, PostgreSQL persistence via SQLAlchemy and Alembic, background breach-timer scheduler (APScheduler), Google Calendar OAuth 2.0 integration, and comprehensive pytest test suite. All functional requirements from Sections 3–9 are implemented and verified. |

---

## 1. Overview

This document defines the specification for the **Task Distribution and Management System (TDMS)** — a structured framework for decomposing goals into discrete, time-bounded, and trackable task chunks. It is designed to support personal and team-level task scheduling with clear visibility into priority, lifecycle state, and assignment status.

**Core Design Principles:**

- **Achievable** — Every task chunk is scoped to a realistic, bounded unit of work.
- **Distributed** — Work is spread across goals and assignees with no single bottleneck.
- **Visible** — At any given moment, the state of every task chunk can be queried and reviewed.

---

## 2. System Components

The TDMS is composed of five primary components:

### 2.1 README

This document. Contains system introduction, component definitions, format requirements, and the update log. It is updated as the system evolves.

### 2.2 Goal Registry

A structured record of all active goals. Each goal serves as a parent container for one or more task chunks. The Goal Registry allows users to trace the relationship between high-level objectives and the individual task chunks that fulfill them.

**Goal Record Format:**

| Field         | Type    | Required | Description                                         |
|---------------|---------|----------|-----------------------------------------------------|
| `goal_id`     | String  | Yes      | Unique identifier for the goal (e.g., `GOAL-001`)  |
| `title`       | String  | Yes      | Short descriptive name for the goal                 |
| `description` | String  | No       | Extended explanation of the goal's scope            |
| `linked_chunks` | List  | Yes      | List of `chunk_id` values associated with this goal |
| `created_at`  | Date    | Yes      | Date the goal was registered                        |

### 2.3 To-Be-Assigned List

An ordered queue of task chunks awaiting scheduling. Task chunks in this list are sorted by urgency level (highest first), then by creation time (earliest first) within the same urgency level. See Section 3 for the full task chunk format specification.

### 2.4 Assigned List

The set of task chunks that have been scheduled and are currently in progress. Each entry in this list is associated with a calendar event (see Section 6: Google Calendar Integration). Entries include all fields from the task chunk format plus the following:

| Field          | Type      | Required | Description                              |
|----------------|-----------|----------|------------------------------------------|
| `assigned_date` | Date     | Yes      | The date this chunk was scheduled        |
| `start_time`   | Time      | Yes      | Scheduled start time                     |
| `calendar_event_id` | String | No    | Google Calendar event ID, populated after sync |

### 2.5 System Dashboard

A real-time summary view of all task chunks across the system, queryable by status and goal. See Section 5 for counter definitions.

---

## 3. Task Chunk Format Specification

Each task chunk in the To-Be-Assigned List is represented using the following format:

```
(REF-XXXX) (time_period +/- time_divergent) Content_text_in_brief [Reference_link] [Urgency_label]
```

### 3.1 Fields

#### `chunk_id` *(required)*

A unique reference number for the task chunk, formatted as `REF-XXXX` (e.g., `REF-0042`). Used for search, linking to goals, and tracking history.

#### `time_period` *(required)*

An integer representing the estimated duration of the task chunk, in hours.

#### `time_divergent` *(optional)*

An optional uncertainty margin, also expressed in hours. When specified, the time estimate is rendered as a range:

```
([time_period - time_divergent] to [time_period + time_divergent] hrs)
```

When omitted, `time_divergent` defaults to `0` and only the base estimate is shown.

**Examples:**

- `(3)` → Estimated 3 hours, no uncertainty
- `(3 +/- 1)` → Estimated 2 to 4 hours

#### `content_text_in_brief` *(required)*

A plain-text description of the task chunk. This field must be manually authored and should clearly state what needs to be accomplished.

#### `reference_link` *(optional)*

A plain-text URL pointing to relevant resources (documentation, course materials, issue trackers, etc.). Hyperlink rendering is planned for a future release.

#### `urgency_label` *(optional, default: Low)*

A human-readable urgency classification. Users interact with urgency labels only; internal numeric levels are managed by the system. See Section 4 for the full urgency table.

---

## 4. Urgency Levels

| Label     | Internal Level | Behavior                                                                                                  |
|-----------|:--------------:|-----------------------------------------------------------------------------------------------------------|
| Very High | 1              | Task chunk is immediately moved to the Assigned List. The assignment form is shown automatically upon selection. This label does not appear in the To-Be-Assigned List. |
| High      | 2              | Reminder triggered after 72 hours in the queue. Status set to `BREACH_ACTION`.                           |
| Medium    | 3              | Reminder triggered after 72 hours in the queue. Status set to `BREACH`.                                  |
| Low       | 4              | Default urgency. Reminder triggered after 168 hours (7 days) in the queue. Status set to `BREACH`.       |
| Very Low  | 5              | No timer or reminder. Status remains `OK` indefinitely.                                                   |

**Sorting Rule:** Task chunks in the To-Be-Assigned List are sorted from highest urgency to lowest (Very High → Very Low), then by creation time (earliest first) within the same urgency tier.

---

## 5. Status Definitions and Lifecycle

### 5.1 Status Values

| Status          | Description                                                                                                   |
|-----------------|---------------------------------------------------------------------------------------------------------------|
| `OK`            | The task chunk is within its permitted wait time. No action required.                                         |
| `BREACH`        | The task chunk has exceeded its permitted wait time. A user acknowledgment (ACK) is required.                 |
| `BREACH_ACTION` | An escalated breach state. Triggered for High-urgency task chunks. Requires immediate user acknowledgment.    |
| `IN_PROGRESS`   | The task chunk has been assigned and is actively being worked on.                                             |
| `COMPLETED`     | The task chunk has been fulfilled successfully.                                                               |
| `FAILED`        | The task chunk was not fulfilled and has been marked as failed.                                               |

### 5.2 BREACH Acknowledgment Flow

When a task chunk enters `BREACH` or `BREACH_ACTION`, the system triggers an alert. The user is presented with a dialog:

> *"This task chunk has exceeded its scheduled wait time and has not yet been assigned. Click below to acknowledge and reduce its urgency."*
>
> **[ I acknowledge — reduce urgency to \[Level + 1\] ]**

Upon confirmation, the task chunk's urgency is decremented by one level (e.g., High → Medium). This mechanism ensures that any persistently unassigned task chunk eventually reaches **Very Low** urgency, preventing indefinite escalation.

> **Note:** Level 5 (Very Low) is the terminal urgency state. A task chunk at Level 5 will not trigger further breach alerts.

### 5.3 Status Change History

Each task chunk maintains a full log of status transitions in the following format:

| Field        | Type      | Description                                           |
|--------------|-----------|-------------------------------------------------------|
| `chunk_id`   | String    | Reference number of the affected task chunk           |
| `from_status`| Enum      | Previous status value                                 |
| `to_status`  | Enum      | New status value                                      |
| `timestamp`  | Datetime  | UTC datetime of the transition                        |
| `trigger`    | String    | What caused the change (e.g., `USER_ACK`, `TIMER`, `MANUAL_ASSIGN`) |
| `note`       | String    | Optional free-text note recorded at the time of change |

---

## 6. System-Wide Counters and Dashboard

The system maintains the following real-time aggregate metrics, queryable at any time via the dashboard:

| Metric              | Description                                                        |
|---------------------|--------------------------------------------------------------------|
| **Waiting**         | Number of task chunks currently in the To-Be-Assigned List         |
| **In Progress**     | Number of task chunks currently assigned and being worked on       |
| **Completed**       | Number of task chunks successfully fulfilled                       |
| **Failed**          | Number of task chunks marked as failed                             |
| **Breached**        | Number of task chunks currently in `BREACH` or `BREACH_ACTION` status |
| **Waiting Time Avg**| Average time (in hours) a task chunk spends in the To-Be-Assigned List before assignment |

All counters support filtering by goal, urgency level, and date range.

---

## 7. Search

The system supports full-text and structured search over all task chunks, including historical records.

**Searchable fields:**

- `chunk_id` (exact match)
- `content_text_in_brief` (keyword search)
- `status` (filter)
- `urgency_label` (filter)
- `goal_id` (filter)
- `created_at` / `assigned_date` (date range filter)

Search results include task chunks in all lifecycle states, including completed and failed chunks, allowing users to reference past work.

---

## 8. Web Forms

### 8.1 Task Chunk Creation Form

Triggered when a user adds a new task chunk. Collects the following:

- Content description
- Estimated time (with optional divergent)
- Urgency level (displayed as labels, not numbers)
- Goal association (linked from the Goal Registry)
- Optional reference link

Upon submission, the system assigns a unique `chunk_id`, sets the initial status to `OK`, and starts the urgency timer (except for Very Low urgency). If **Very High** is selected, the assignment form (8.2) is immediately presented instead.

### 8.2 Task Assignment Form

Presented when a task chunk is being scheduled. Collects:

- Assigned date
- Start time
- Optional notes

Upon submission, the system moves the task chunk from the To-Be-Assigned List to the Assigned List, updates the status to `IN_PROGRESS`, and — if Google Calendar integration is enabled — creates a corresponding calendar event (see Section 9).

---

## 9. Google Calendar API Integration

This section specifies how the TDMS integrates with the Google Calendar API to synchronize scheduled task chunks as calendar events.

### 9.1 Concept Overview

When a task chunk is assigned (via the assignment form), the system automatically creates a Google Calendar event representing the scheduled work block. This allows users to see their task schedule directly within Google Calendar, receive native reminders, and maintain a unified view of their time.

You do not need deep API knowledge to use this feature. The integration works through **OAuth 2.0 authentication** — on first use, the system will prompt you to log in with your Google account and grant permission for calendar access. After that, all sync operations happen automatically in the background.

### 9.2 How It Works (Step by Step)

1. **Authentication:** On first use, the system redirects the user to Google's login page. The user approves calendar read/write access. The system stores a secure token for future requests — the user only needs to do this once.

2. **Event Creation (on assignment):** When a task chunk is moved to the Assigned List, the system sends an HTTP POST request to the Google Calendar API with the task chunk's title, description, date, and start time. Google Calendar creates the event and returns a unique `calendar_event_id`, which is saved to the task chunk record.

3. **Event Update (on edit):** If the assigned date or start time of a task chunk is modified, the system sends an HTTP PATCH request using the stored `calendar_event_id` to update the existing calendar event.

4. **Event Deletion (on unassign or cancel):** If a task chunk is removed from the Assigned List or cancelled, the system sends an HTTP DELETE request to remove the corresponding calendar event.

5. **Event Completion (on completion):** When a task chunk is marked `COMPLETED`, the system optionally updates the calendar event title with a `✓` prefix to visually distinguish finished blocks.

### 9.3 Calendar Event Fields

Each calendar event created by the system will contain the following:

| Calendar Field | Source                                        |
|----------------|-----------------------------------------------|
| **Title**      | `[REF-XXXX] Content_text_in_brief`            |
| **Description**| Goal name + reference link (if any) + urgency label |
| **Start Time** | `assigned_date` + `start_time` from assignment form |
| **End Time**   | Start time + `time_period` (in hours)         |
| **Color**      | Mapped from urgency: Very High → Red, High → Orange, Medium → Yellow, Low → Blue, Very Low → Green |
| **Reminder**   | Default: 30 minutes before start             |

### 9.4 Permissions Required

The system requests the following Google API scope:

```
https://www.googleapis.com/auth/calendar.events
```

This grants the system permission to create, read, update, and delete events on your calendar. It does **not** grant access to other Google services.

### 9.5 API Rate Limits and Error Handling

The Google Calendar API imposes usage limits. The system handles these gracefully:

- If an API call fails (e.g., network error, token expiry), the system queues the operation and retries automatically.
- If the token has expired, the system silently refreshes it in the background.
- If the user has revoked access, the system will prompt re-authentication on the next sync attempt.
- All sync failures are logged and visible to the user in a "Sync Status" panel.

### 9.6 Future Enhancements

- **Bi-directional sync:** Allow edits made directly in Google Calendar to propagate back into TDMS.
- **Calendar selection:** Allow the user to choose which Google Calendar receives events (e.g., a dedicated "Tasks" calendar).
- **Recurring task support:** For task chunks that repeat on a schedule, generate recurring Google Calendar events automatically.
- **Google Meet integration:** Optionally attach a Meet link to assigned task chunks for collaborative sessions.

---

## 10. Example Task Chunk Entries

```
(REF-0001) (3) W9,W10,W11: Graph Basic; Graph Search (BFS & DFS); DAGs & Connectivity
  Goal: CS344 | Urgency: Low

(REF-0002) (3) W2, W3: Divide and Conquer & Basic Sorting; Recurrences & Recursion Trees
  Goal: CS344 | Urgency: Low

(REF-0003) (3) W4, W5: Linear Selection & Median; Recursion Tree Analysis
  Goal: CS344 | Urgency: Low

(REF-0004) (2) W6, W7: Dynamic Programming
  Goal: CS344 | Urgency: Low

(REF-0005) (3) W8, W9: Greedy Algorithms
  Goal: CS344 | Urgency: Low
```

---

## 11. Open Questions / To Be Defined

- Definition of task chunk management for the **CS417** goal (currently empty).
- Conflict resolution policy when two task chunks are assigned to overlapping time windows.
- Whether the Assigned List supports multiple assignees per task chunk (multi-user mode).
- Retention policy for completed and failed task chunks in the history log.