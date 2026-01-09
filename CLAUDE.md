# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **reclaim-sdk**, an unofficial Python SDK for the Reclaim.ai API. It provides a Pydantic-based interface for managing tasks within Reclaim.ai. The SDK is reverse-engineered from the Reclaim.ai web app and the [Swagger Spec](https://api.app.reclaim.ai/swagger/reclaim-api-0.1.yml).

**Current version**: 0.6.4

## Development Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Install dependencies only
pip install -r requirements.txt

# Linting
flake8 reclaim_sdk/
black reclaim_sdk/

# Format code
black reclaim_sdk/
```

## Testing

The test suite uses pytest with markers for unit and integration tests.

```bash
# Run all tests (requires RECLAIM_TOKEN)
RECLAIM_TOKEN=your_token pytest tests/ -v

# Run with 1Password (recommended)
op run --env-file=/path/to/env -- pytest tests/ -v

# Run only unit tests (no API required)
pytest tests/ -v -m unit

# Run only integration tests
pytest tests/ -v -m integration

# Run specific test file
pytest tests/test_habit.py -v
```

**Test categories:**
- `test_client.py` - Client configuration and HTTP handling
- `test_task.py` - Task CRUD and properties
- `test_hours.py` - Time schemes (Hours)
- `test_habit.py` - Smart Habits, Legacy Habits, Changelog
- `test_api_behavior.py` - Documents working vs forbidden endpoints

## Authentication

The SDK requires a Reclaim API token from https://app.reclaim.ai/settings/developer

Two configuration methods:
1. Environment variable: `RECLAIM_TOKEN=your_token`
2. Programmatic: `ReclaimClient.configure(token="your_token")`

## Architecture

### Singleton Client Pattern

`ReclaimClient` (`client.py`) is a singleton that manages HTTP requests to the Reclaim API:
- Uses `httpx` for HTTP requests
- Automatically handles datetime serialization (converts to UTC ISO format with Z suffix)
- Maps HTTP errors to typed exceptions

### Resource Pattern

All API resources inherit from `BaseResource` (`resources/base.py`), which provides:
- Pydantic model validation
- CRUD operations: `get()`, `list()`, `save()`, `delete()`, `refresh()`
- Automatic API data serialization via `to_api_data()` / `from_api_data()`

To add a new resource:
1. Create a new file in `reclaim_sdk/resources/`
2. Inherit from `BaseResource`
3. Set the `ENDPOINT` class variable
4. Define Pydantic fields (use `alias` for camelCase API field names)

### Current Resources

- **Task** (`resources/task.py`): Full task management including create, update, delete, mark complete/incomplete, start/stop, log work, add time, prioritize
- **Hours** (`resources/hours.py`): Read-only access to time schemes (custom hours)
- **SmartHabit** (`resources/habit.py`): Read-only access to active habits (extracted from calendar events)
- **Habit** (`resources/habit.py`): Legacy daily habits with limited planner actions (start/stop/done)

### Key Implementation Details

**Time chunks**: Reclaim uses 15-minute chunks internally. The `Task` model provides convenience properties (`duration`, `min_work_duration`, `max_work_duration`) that convert hours to/from chunks (multiply/divide by 4).

**Field aliasing**: API uses camelCase, SDK uses snake_case. Use Pydantic's `alias` parameter for mapping (e.g., `Field(alias="eventCategory")`).

**Task actions**: Beyond CRUD, tasks support planner actions via dedicated endpoints:
- `/api/planner/done/task/{id}` - mark complete
- `/api/planner/start/task/{id}` - start working
- `/api/planner/log-work/task/{id}` - log time spent
- `/api/planner/prioritize/task/{id}` - prioritize

### Habits: Two Systems

Reclaim has two habit systems with different API access:

| Type | Endpoint | API Support | Status |
|------|----------|-------------|--------|
| **Smart Habits** (current) | Via `/api/events` only | Read-only | Active habits with scheduling |
| **Legacy Daily Habits** | `/api/assist/habits/daily` | Full CRUD + some actions | Mostly disabled/migrated |

**Smart Habits** (`SmartHabit` class):
- No direct CRUD API - extracted from calendar events with `reclaimEventType=SMART_HABIT`
- Each habit has a `seriesLineageId` that groups scheduled instances
- Use `SmartHabit.list()` to get all active habits with their scheduled instances
- Use `habit.get_changelog()` to see scheduling history (moves, conflicts)
- Use `SmartHabit.get_all_changelogs()` for all habits at once
- Endpoints like `/api/assist/smart-series/{id}` return Forbidden

**Legacy Habits** (`Habit` class):
- Full CRUD via `/api/assist/habits/daily`
- Limited planner actions: `done`, `start`, `stop` work; `log-work`, `add-time`, `prioritize` return Forbidden
- Most habits show as disabled (migrated to Smart Habits)

## Dependencies

- `httpx[http2]` - HTTP client
- `pydantic>=2.0.0` - Data validation
- `python-dateutil` - Date parsing

## Exception Hierarchy

```
ReclaimAPIError (base)
├── RecordNotFound (404)
├── InvalidRecord (400, 422)
└── AuthenticationError (401)
```
