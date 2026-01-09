from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator, field_validator
from datetime import datetime, timezone
from typing import ClassVar, Dict, List, Optional, Any, Tuple, Literal
from enum import Enum
from reclaim_sdk.resources.base import BaseResource
from reclaim_sdk.client import ReclaimClient


class HabitType(str, Enum):
    """Type of habit scheduling."""
    CUSTOM_DAILY = "CUSTOM_DAILY"


class ChangeReason(str, Enum):
    """Reasons for habit schedule changes."""
    SMART_SERIES_EVENT_MOVED = "SMART_SERIES_EVENT_MOVED"
    SMART_SERIES_EVENT_CREATED = "SMART_SERIES_EVENT_CREATED"
    SMART_SERIES_EVENT_DELETED = "SMART_SERIES_EVENT_DELETED"
    SMART_SERIES_EVENT_LOCKED = "SMART_SERIES_EVENT_LOCKED"
    SMART_SERIES_EVENT_UNLOCKED = "SMART_SERIES_EVENT_UNLOCKED"
    SMART_SERIES_EVENT_REMOVED_DUE_TO_NO_TIME = "SMART_SERIES_EVENT_REMOVED_DUE_TO_NO_TIME"
    SMART_SERIES_EVENT_DURATION_CHANGED = "SMART_SERIES_EVENT_DURATION_CHANGED"
    SMART_SERIES_EVENT_UPDATED = "SMART_SERIES_EVENT_UPDATED"
    # Catch-all for unknown reasons from API
    UNKNOWN = "UNKNOWN"


class EventCategory(str, Enum):
    """Event category for habits."""
    WORK = "WORK"
    PERSONAL = "PERSONAL"


class Habit(BaseResource):
    """
    Legacy Daily Habit resource.

    Note: Most active habits have been migrated to Smart Habits.
    Use SmartHabit.list() for current active habits.
    This class is for legacy habits accessible via /api/assist/habits/daily.
    """

    ENDPOINT: ClassVar[str] = "/api/assist/habits/daily"

    title: Optional[str] = Field(None, description="Habit title")
    enabled: bool = Field(False, description="Whether habit is enabled")
    duration_min: Optional[int] = Field(None, alias="durationMin", description="Minimum duration in minutes")
    duration_max: Optional[int] = Field(None, alias="durationMax", description="Maximum duration in minutes")
    ideal_time: Optional[str] = Field(None, alias="idealTime", description="Ideal time of day (HH:MM:SS)")
    event_category: Optional[str] = Field(None, alias="eventCategory", description="WORK or PERSONAL")
    event_sub_type: Optional[str] = Field(None, alias="eventSubType", description="Event subtype")
    type: Optional[HabitType] = Field(None, description="Habit type")
    priority: Optional[str] = Field(None, description="Priority (P1-P4)")
    notification: bool = Field(True, description="Whether to send notifications")
    always_private: bool = Field(False, alias="alwaysPrivate", description="Always private")
    auto_decline: bool = Field(False, alias="autoDecline", description="Auto-decline conflicts")
    index: Optional[float] = Field(None, description="Sort index")
    elevated: bool = Field(False, description="Elevated priority")
    adjusted: bool = Field(False, description="Has been adjusted")
    time_policy_type: Optional[str] = Field(None, alias="timePolicyType", description="Time policy type")
    one_off_policy: Optional[Dict] = Field(None, alias="oneOffPolicy", description="Custom scheduling policy")
    defense_aggression: Optional[str] = Field(None, alias="defenseAggression", description="Defense aggression level")
    reserved_words: Optional[List[str]] = Field(None, alias="reservedWords", description="Reserved words for matching")

    def mark_complete(self) -> None:
        """Mark the habit as complete for today."""
        response = self._client.post(f"/api/planner/done/habit/{self.id}")
        if "taskOrHabit" in response:
            self._update_from_response(response["taskOrHabit"])

    def start(self) -> None:
        """Start working on this habit."""
        response = self._client.post(f"/api/planner/start/habit/{self.id}")
        if "taskOrHabit" in response:
            self._update_from_response(response["taskOrHabit"])

    def stop(self) -> None:
        """Stop working on this habit."""
        response = self._client.post(f"/api/planner/stop/habit/{self.id}")
        if "taskOrHabit" in response:
            self._update_from_response(response["taskOrHabit"])


class SmartHabitInstance(BaseModel):
    """A single scheduled instance of a Smart Habit on the calendar."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    event_id: str = Field(..., alias="eventId", description="Calendar event ID")
    calendar_id: int = Field(..., alias="calendarId", description="Calendar ID")
    start: datetime = Field(..., alias="eventStart", description="Event start time")
    end: datetime = Field(..., alias="eventEnd", description="Event end time")
    status: str = Field(..., description="Event status (PUBLISHED, etc.)")
    pinned: bool = Field(False, description="Whether this instance is pinned/locked")

    @model_validator(mode="before")
    @classmethod
    def extract_pinned_from_assist(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pinned flag from nested assist object if present."""
        if isinstance(data, dict):
            assist = data.get("assist", {})
            if isinstance(assist, dict) and "pinned" not in data:
                data["pinned"] = assist.get("pinned", False)
        return data

    @field_validator("start", "end")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure datetime fields are timezone-aware (assume UTC if naive)."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class SmartHabit(BaseModel):
    """
    Smart Habit extracted from calendar events.

    Smart Habits are the current active habit system in Reclaim.ai.
    They don't have a direct CRUD API - we extract them from scheduled events.

    Usage:
        habits = SmartHabit.list()
        for habit in habits:
            print(f"{habit.title}: {len(habit.instances)} scheduled instances")
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        frozen=True,  # SmartHabit is read-only
    )

    series_id: int = Field(..., alias="seriesId", description="Smart series lineage ID")
    title: str = Field(..., description="Habit title (without status emoji)")
    category: EventCategory = Field(..., description="WORK or PERSONAL")
    color: Optional[str] = Field(None, description="Calendar color")
    instances: List[SmartHabitInstance] = Field(default_factory=list, description="Scheduled instances")

    # Store client reference for subsequent API calls
    _client: Optional[ReclaimClient] = PrivateAttr(default=None)

    @property
    def next_instance(self) -> Optional[SmartHabitInstance]:
        """Get the next scheduled instance."""
        if not self.instances:
            return None

        now = datetime.now(timezone.utc)

        # Filter future instances (timezone awareness guaranteed by field_validator)
        future = [i for i in self.instances if i.start > now]

        if future:
            return min(future, key=lambda x: x.start)

        # If no future instances, return the most recent
        return max(self.instances, key=lambda x: x.start)

    @property
    def instance_count(self) -> int:
        """Number of scheduled instances."""
        return len(self.instances)

    @classmethod
    def list(
        cls,
        client: Optional[ReclaimClient] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List["SmartHabit"]:
        """
        List all Smart Habits by extracting from calendar events.

        Args:
            client: Optional client instance. If provided, it will be bound
                   to returned SmartHabit instances for subsequent API calls.
            start: Optional start datetime for filtering events. If not provided,
                   uses the API's default range.
            end: Optional end datetime for filtering events. If not provided,
                 uses the API's default range.

        Returns:
            List of SmartHabit objects with their scheduled instances.
        """
        if client is None:
            client = ReclaimClient()

        # Build query params for date range filtering
        params: Dict[str, str] = {}
        if start is not None:
            params["start"] = start.isoformat()
        if end is not None:
            params["end"] = end.isoformat()

        events = client.get("/api/events", params=params if params else None)

        # Group events by series lineage ID
        habits_map: Dict[int, Dict[str, Any]] = {}

        for event in events:
            if event.get("reclaimEventType") != "SMART_HABIT":
                continue

            assist = event.get("assist", {})
            series_id = assist.get("seriesLineageId")

            # Use `is None` check to allow series_id=0 (though unlikely)
            if series_id is None:
                continue

            if series_id not in habits_map:
                # Clean title (remove status emoji prefix)
                title = event.get("title", "")
                # Common status prefixes used by Reclaim
                status_prefixes = ["✅ ", "🔒 ", "⏸️ ", "⏭️ ", "🔄 "]
                for prefix in status_prefixes:
                    if title.startswith(prefix):
                        title = title[len(prefix):]
                        break

                # Parse category as enum, default to WORK
                category_str = event.get("type", "WORK")
                try:
                    category = EventCategory(category_str)
                except ValueError:
                    category = EventCategory.WORK

                habits_map[series_id] = {
                    "series_id": series_id,
                    "title": title,
                    "category": category,
                    "color": event.get("color"),
                    "instances": [],
                }

            # Use model_validate for proper parsing
            instance = SmartHabitInstance.model_validate(event)
            habits_map[series_id]["instances"].append(instance)

        # Convert to SmartHabit objects and bind client
        habits = []
        for data in habits_map.values():
            habit = cls.model_validate(data)
            # Bind client for subsequent API calls (bypass frozen with object.__setattr__)
            object.__setattr__(habit, "_client", client)
            habits.append(habit)

        return habits

    @classmethod
    def get_by_title(cls, title: str, client: Optional[ReclaimClient] = None) -> Optional["SmartHabit"]:
        """
        Find a Smart Habit by title (case-insensitive partial match).

        Args:
            title: Title to search for (partial match supported)
            client: Optional ReclaimClient instance

        Returns:
            SmartHabit if found, None otherwise
        """
        habits = cls.list(client)
        title_lower = title.lower()
        for habit in habits:
            if title_lower in habit.title.lower():
                return habit
        return None

    def get_changelog(self, client: Optional[ReclaimClient] = None, limit: int = 50) -> List["HabitChangeLogEntry"]:
        """
        Get the scheduling changelog for this habit.

        Returns a list of changes (moves, creates, deletes, locks) ordered by most recent first.

        Args:
            client: Optional ReclaimClient instance. Uses bound client if not provided.
            limit: Maximum number of entries to return (default 50)

        Returns:
            List of HabitChangeLogEntry objects sorted by date (newest first)
        """
        # Use bound client, passed client, or singleton (in that order)
        if client is None:
            client = self._client if self._client is not None else ReclaimClient()

        entries = client.get(f"/api/changelog/smart-habits?lineageIds={self.series_id}")

        # Parse all entries first
        parsed = [HabitChangeLogEntry.model_validate(e) for e in entries]

        # Sort by changed_at descending (newest first), then limit
        parsed.sort(key=lambda x: x.changed_at, reverse=True)

        return parsed[:limit]

    @classmethod
    def get_all_changelogs(
        cls,
        series_ids: Optional[List[int]] = None,
        client: Optional[ReclaimClient] = None,
        limit: int = 100
    ) -> List["HabitChangeLogEntry"]:
        """
        Get changelogs for multiple habits at once.

        Args:
            series_ids: List of series IDs. If None, gets IDs from current habits.
            client: Optional ReclaimClient instance
            limit: Maximum entries to return

        Returns:
            List of HabitChangeLogEntry objects sorted by date (newest first)
        """
        if client is None:
            client = ReclaimClient()

        if series_ids is None:
            habits = cls.list(client)
            series_ids = [h.series_id for h in habits]

        if not series_ids:
            return []

        ids_param = ",".join(str(sid) for sid in series_ids)
        entries = client.get(f"/api/changelog/smart-habits?lineageIds={ids_param}")

        # Parse all entries
        parsed = [HabitChangeLogEntry.model_validate(e) for e in entries]

        # Sort by changed_at descending, then limit
        parsed.sort(key=lambda x: x.changed_at, reverse=True)

        return parsed[:limit]

    def __str__(self) -> str:
        return f"SmartHabit('{self.title}', {self.instance_count} instances)"

    def __repr__(self) -> str:
        return f"SmartHabit(series_id={self.series_id}, title='{self.title}', category='{self.category.value}', instances={self.instance_count})"


class HabitChangeLogEntry(BaseModel):
    """
    A changelog entry for a Smart Habit scheduling change.

    These entries track when habits are moved, created, deleted, locked, or unlocked.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    id: int = Field(..., description="Changelog entry ID")
    changed_at: datetime = Field(..., alias="changedAt", description="When the change occurred")
    series_id: int = Field(..., alias="assignmentId", description="Habit series ID")
    event_id: str = Field(..., alias="eventId", description="Affected event ID")
    reason: ChangeReason = Field(..., description="Reason for change")

    # Move-specific fields (populated when reason is SMART_SERIES_EVENT_MOVED)
    previous_start: Optional[datetime] = Field(None, description="Previous start time")
    previous_end: Optional[datetime] = Field(None, description="Previous end time")
    new_start: Optional[datetime] = Field(None, description="New start time")
    new_end: Optional[datetime] = Field(None, description="New end time")
    conflicts: List[Dict[str, Any]] = Field(default_factory=list, description="Conflicts that caused the move")

    @model_validator(mode="before")
    @classmethod
    def extract_move_metadata(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract move metadata from nested eventMovedMetadata if present."""
        if isinstance(data, dict):
            # Handle unknown reason values gracefully
            reason = data.get("reason")
            if reason and isinstance(reason, str):
                try:
                    ChangeReason(reason)
                except ValueError:
                    # Unknown reason - use UNKNOWN
                    data["reason"] = ChangeReason.UNKNOWN.value

            move_meta = data.get("eventMovedMetadata", {})
            if isinstance(move_meta, dict):
                # Only set if not already present (allow override)
                if "previous_start" not in data and "previousStart" not in data:
                    data["previous_start"] = move_meta.get("previousStart")
                if "previous_end" not in data and "previousEnd" not in data:
                    data["previous_end"] = move_meta.get("previousEnd")
                if "new_start" not in data and "newStart" not in data:
                    data["new_start"] = move_meta.get("newStart")
                if "new_end" not in data and "newEnd" not in data:
                    data["new_end"] = move_meta.get("newEnd")
                if "conflicts" not in data:
                    data["conflicts"] = move_meta.get("conflicts", [])
        return data

    @property
    def is_move(self) -> bool:
        """Check if this is a move event."""
        return self.reason == ChangeReason.SMART_SERIES_EVENT_MOVED

    @property
    def is_create(self) -> bool:
        """Check if this is a create event."""
        return self.reason == ChangeReason.SMART_SERIES_EVENT_CREATED

    @property
    def is_delete(self) -> bool:
        """Check if this is a delete event."""
        return self.reason == ChangeReason.SMART_SERIES_EVENT_DELETED

    @property
    def is_lock(self) -> bool:
        """Check if this is a lock event."""
        return self.reason == ChangeReason.SMART_SERIES_EVENT_LOCKED

    @property
    def is_unlock(self) -> bool:
        """Check if this is an unlock event."""
        return self.reason == ChangeReason.SMART_SERIES_EVENT_UNLOCKED

    @property
    def time_shift(self) -> Optional[Tuple[datetime, datetime]]:
        """
        Get the time shift as (from, to) tuple.

        Returns None if not a move event or times not available.
        """
        if self.is_move and self.previous_start and self.new_start:
            return (self.previous_start, self.new_start)
        return None

    def __str__(self) -> str:
        if self.is_move and self.previous_start and self.new_start:
            prev = self.previous_start.strftime("%m/%d %I:%M%p")
            new = self.new_start.strftime("%m/%d %I:%M%p")
            return f"Moved: {prev} -> {new}"
        return f"{self.reason.value} at {self.changed_at.strftime('%m/%d %I:%M%p')}"

    def __repr__(self) -> str:
        return f"HabitChangeLogEntry(id={self.id}, reason={self.reason.value!r}, changed_at={self.changed_at!r})"
