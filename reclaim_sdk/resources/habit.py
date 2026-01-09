from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator, field_validator
from datetime import datetime, timezone, time
from typing import ClassVar, Dict, List, Optional, Any, Tuple
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
    UNKNOWN = "UNKNOWN"


class EventCategory(str, Enum):
    """Event category for habits."""
    WORK = "WORK"
    PERSONAL = "PERSONAL"


class HabitStatus(str, Enum):
    """Status of a Smart Habit."""
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class RecurrenceFrequency(str, Enum):
    """Frequency of habit recurrence."""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class EventType(str, Enum):
    """Type of calendar event."""
    SOLO_WORK = "SOLO_WORK"
    FOCUS_TIME = "FOCUS_TIME"
    MEETING = "MEETING"
    PERSONAL = "PERSONAL"


class DefenseAggression(str, Enum):
    """How aggressively to defend the habit time."""
    DEFAULT = "DEFAULT"
    AGGRESSIVE = "AGGRESSIVE"
    PASSIVE = "PASSIVE"


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


class HabitRecurrence(BaseModel):
    """Recurrence configuration for a Smart Habit."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    frequency: RecurrenceFrequency = Field(RecurrenceFrequency.WEEKLY, description="Recurrence frequency")
    ideal_days: List[str] = Field(default_factory=list, alias="idealDays", description="Preferred days (MONDAY, TUESDAY, etc.)")
    interval: int = Field(1, description="Interval between occurrences")
    days_between_periods: int = Field(1, alias="daysBetweenPeriods", description="Minimum days between periods")


class SmartHabitPeriod(BaseModel):
    """A scheduled period/instance of a Smart Habit."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    event_key: str = Field(..., alias="eventKey", description="Unique event key")
    series_id: int = Field(..., alias="seriesId", description="Series ID")
    start: str = Field(..., description="Period start date (YYYY-MM-DD)")
    end: str = Field(..., description="Period end date (YYYY-MM-DD)")
    done: bool = Field(False, description="Whether period is completed")
    locked: bool = Field(False, description="Whether period is locked/pinned")
    event_start: Optional[datetime] = Field(None, alias="eventStart", description="Scheduled event start time")
    event_end: Optional[datetime] = Field(None, alias="eventEnd", description="Scheduled event end time")
    event_status: str = Field("NONE", alias="eventStatus", description="Event status (DONE, NONE, PUBLISHED)")
    scheduler_status: str = Field("NOT_SKIPPED", alias="schedulerStatus", description="Scheduler status")
    scheduler_skipped: bool = Field(False, alias="schedulerSkipped", description="Whether scheduler skipped this")

    @field_validator("event_start", "event_end", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Optional[datetime]:
        """Parse datetime strings, return None for missing values."""
        if v is None:
            return None
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
        if isinstance(v, str):
            # Parse ISO format datetime
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                return None
        return None


class SmartHabitInstance(BaseModel):
    """A single scheduled instance of a Smart Habit on the calendar.

    This is a simplified view used when listing habits via /api/events.
    For richer data, use SmartHabitPeriod from the /api/smart-habits endpoint.
    """

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
    Smart Habit resource with full CRUD support.

    Smart Habits are the current active habit system in Reclaim.ai.
    This class uses the /api/smart-habits endpoint for full access.

    Usage:
        # List all habits
        habits = SmartHabit.list()

        # Get a specific habit
        habit = SmartHabit.get(lineage_id)

        # Update a habit
        habit.title = "New Title"
        habit.save()

        # Disable/Enable
        habit.disable()
        habit.enable()
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        validate_assignment=True,
    )

    ENDPOINT: ClassVar[str] = "/api/smart-habits"

    # Core identifiers
    lineage_id: int = Field(..., alias="lineageId", description="Smart series lineage ID (primary identifier)")
    calendar_id: int = Field(..., alias="calendarId", description="Calendar ID")
    status: HabitStatus = Field(HabitStatus.ACTIVE, description="Habit status (ACTIVE/DISABLED)")

    # Main habit properties (from activeSeries)
    title: str = Field(..., description="Habit title")
    description: str = Field("", description="Habit description")
    ideal_time: Optional[str] = Field(None, alias="idealTime", description="Ideal time of day (HH:MM:SS)")
    duration_min: int = Field(30, alias="durationMinMins", description="Minimum duration in minutes")
    duration_max: int = Field(30, alias="durationMaxMins", description="Maximum duration in minutes")
    priority: str = Field("P2", description="Priority (P1-P4)")
    event_type: EventType = Field(EventType.SOLO_WORK, alias="eventType", description="Event type")
    defense_aggression: DefenseAggression = Field(DefenseAggression.DEFAULT, alias="defenseAggression")
    auto_decline: bool = Field(False, alias="autoDecline", description="Auto-decline conflicts")
    recurrence: Optional[HabitRecurrence] = Field(None, description="Recurrence configuration")

    # Scheduling periods
    periods: List[SmartHabitPeriod] = Field(default_factory=list, description="Scheduled periods")

    # For backward compatibility with old API
    instances: List[SmartHabitInstance] = Field(default_factory=list, description="Legacy instances (deprecated)")

    # Private client reference
    _client: Optional[ReclaimClient] = PrivateAttr(default=None)

    # Backward compatibility alias
    @property
    def series_id(self) -> int:
        """Alias for lineage_id for backward compatibility."""
        return self.lineage_id

    @property
    def category(self) -> EventCategory:
        """Infer category from event_type for backward compatibility."""
        if self.event_type == EventType.PERSONAL:
            return EventCategory.PERSONAL
        return EventCategory.WORK

    @property
    def next_period(self) -> Optional[SmartHabitPeriod]:
        """Get the next scheduled period."""
        if not self.periods:
            return None

        now = datetime.now(timezone.utc)

        # Find future periods with scheduled times
        future = [p for p in self.periods if p.event_start and p.event_start > now and not p.done]

        if future:
            return min(future, key=lambda x: x.event_start)

        return None

    @property
    def next_instance(self) -> Optional[SmartHabitInstance]:
        """Get the next scheduled instance (backward compatibility)."""
        if not self.instances:
            return None

        now = datetime.now(timezone.utc)
        future = [i for i in self.instances if i.start > now]

        if future:
            return min(future, key=lambda x: x.start)

        return max(self.instances, key=lambda x: x.start) if self.instances else None

    @property
    def instance_count(self) -> int:
        """Number of scheduled instances/periods."""
        return len(self.periods) if self.periods else len(self.instances)

    @property
    def is_enabled(self) -> bool:
        """Check if habit is enabled."""
        return self.status == HabitStatus.ACTIVE

    @classmethod
    def _get_client(cls, client: Optional[ReclaimClient] = None) -> ReclaimClient:
        """Get client instance."""
        return client if client is not None else ReclaimClient()

    @classmethod
    def get(cls, lineage_id: int, client: Optional[ReclaimClient] = None) -> "SmartHabit":
        """
        Fetch a Smart Habit by lineage ID.

        Args:
            lineage_id: The habit's lineage ID
            client: Optional client instance

        Returns:
            SmartHabit instance
        """
        client = cls._get_client(client)

        # The API returns the habit in the list format, so we fetch all and filter
        # (There's no direct GET /api/smart-habits/{id} endpoint)
        data_list = client.get(cls.ENDPOINT)

        for data in data_list:
            if data.get("lineageId") == lineage_id:
                habit = cls._from_api_response(data)
                habit._client = client
                return habit

        from reclaim_sdk.exceptions import RecordNotFound
        raise RecordNotFound(f"SmartHabit with lineage_id {lineage_id} not found")

    @classmethod
    def list(cls, client: Optional[ReclaimClient] = None) -> List["SmartHabit"]:
        """
        List all Smart Habits.

        Args:
            client: Optional client instance

        Returns:
            List of SmartHabit objects
        """
        client = cls._get_client(client)
        data_list = client.get(cls.ENDPOINT)

        habits = []
        for data in data_list:
            habit = cls._from_api_response(data)
            habit._client = client
            habits.append(habit)

        return habits

    @classmethod
    def _from_api_response(cls, data: Dict[str, Any]) -> "SmartHabit":
        """
        Create SmartHabit from API response.

        The API returns a nested structure with activeSeries containing the main data.
        """
        active_series = data.get("activeSeries", {})

        # Extract recurrence
        recurrence_data = active_series.get("recurrence")
        recurrence = HabitRecurrence.model_validate(recurrence_data) if recurrence_data else None

        # Extract periods
        periods_data = data.get("periods", [])
        periods = [SmartHabitPeriod.model_validate(p) for p in periods_data]

        # Build flat structure for SmartHabit
        habit_data = {
            "lineageId": data.get("lineageId"),
            "calendarId": data.get("calendarId"),
            "status": data.get("status", "ACTIVE"),
            "title": active_series.get("title", ""),
            "description": active_series.get("description", ""),
            "idealTime": active_series.get("idealTime"),
            "durationMinMins": active_series.get("durationMinMins", 30),
            "durationMaxMins": active_series.get("durationMaxMins", 30),
            "priority": active_series.get("attendees", [{}])[0].get("priority", "P2") if active_series.get("attendees") else "P2",
            "eventType": active_series.get("eventType", "SOLO_WORK"),
            "defenseAggression": active_series.get("defenseAggression", "DEFAULT"),
            "autoDecline": active_series.get("autoDecline", False),
            "recurrence": recurrence,
            "periods": periods,
        }

        return cls.model_validate(habit_data)

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

    def save(self) -> None:
        """
        Save changes to this habit.

        Uses PATCH to update the habit on the server.
        """
        if self._client is None:
            self._client = ReclaimClient()

        # Build update payload
        update_data = {
            "title": self.title,
            "description": self.description,
            "durationMinMins": self.duration_min,
            "durationMaxMins": self.duration_max,
            "autoDecline": self.auto_decline,
        }

        if self.ideal_time:
            update_data["idealTime"] = self.ideal_time

        if self.recurrence:
            update_data["recurrence"] = self.recurrence.model_dump(by_alias=True)

        response = self._client.patch(f"{self.ENDPOINT}/{self.lineage_id}", json=update_data)

        # Update self from response
        updated = self._from_api_response(response)
        for field_name in self.model_fields:
            if field_name not in ("_client",):
                setattr(self, field_name, getattr(updated, field_name))

    def enable(self) -> None:
        """Enable this habit."""
        if self._client is None:
            self._client = ReclaimClient()

        # Enable endpoint may return empty response
        try:
            self._client.post(f"{self.ENDPOINT}/{self.lineage_id}/enable")
        except Exception:
            pass  # Endpoint succeeded but returned empty body
        self.status = HabitStatus.ACTIVE

    def disable(self) -> None:
        """Disable this habit."""
        if self._client is None:
            self._client = ReclaimClient()

        # Disable endpoint may return empty response
        try:
            self._client.delete(f"{self.ENDPOINT}/{self.lineage_id}/disable")
        except Exception:
            pass  # Endpoint succeeded but returned empty body
        self.status = HabitStatus.DISABLED

    def refresh(self) -> None:
        """Refresh this habit from the server."""
        if self._client is None:
            self._client = ReclaimClient()

        refreshed = self.get(self.lineage_id, self._client)
        for field_name in self.model_fields:
            if field_name not in ("_client",):
                setattr(self, field_name, getattr(refreshed, field_name))

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
        if client is None:
            client = self._client if self._client is not None else ReclaimClient()

        entries = client.get(f"/api/changelog/smart-habits?lineageIds={self.lineage_id}")

        parsed = [HabitChangeLogEntry.model_validate(e) for e in entries]
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
            series_ids = [h.lineage_id for h in habits]

        if not series_ids:
            return []

        ids_param = ",".join(str(sid) for sid in series_ids)
        entries = client.get(f"/api/changelog/smart-habits?lineageIds={ids_param}")

        parsed = [HabitChangeLogEntry.model_validate(e) for e in entries]
        parsed.sort(key=lambda x: x.changed_at, reverse=True)

        return parsed[:limit]

    def __str__(self) -> str:
        status_str = "enabled" if self.is_enabled else "disabled"
        return f"SmartHabit('{self.title}', {status_str}, {self.instance_count} periods)"

    def __repr__(self) -> str:
        return f"SmartHabit(lineage_id={self.lineage_id}, title='{self.title}', status='{self.status.value}')"


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
            reason = data.get("reason")
            if reason and isinstance(reason, str):
                try:
                    ChangeReason(reason)
                except ValueError:
                    data["reason"] = ChangeReason.UNKNOWN.value

            move_meta = data.get("eventMovedMetadata", {})
            if isinstance(move_meta, dict):
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
