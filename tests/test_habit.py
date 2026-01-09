"""
Tests for Habit and SmartHabit resources.
"""

import pytest
from datetime import datetime, timezone

from reclaim_sdk.resources.habit import (
    Habit,
    SmartHabit,
    SmartHabitInstance,
    SmartHabitPeriod,
    HabitChangeLogEntry,
    HabitRecurrence,
    HabitStatus,
    EventCategory,
    EventType,
    ChangeReason,
    RecurrenceFrequency,
)


class TestSmartHabitUnit:
    """Unit tests for SmartHabit (no API calls)."""

    @pytest.mark.unit
    def test_smart_habit_instance_count_with_periods(self):
        """Instance count property works with periods."""
        habit = SmartHabit(
            lineage_id=123,
            calendar_id=1,
            title="Test Habit",
            periods=[
                SmartHabitPeriod(
                    event_key="key1",
                    series_id=123,
                    start="2024-01-01",
                    end="2024-01-02",
                ),
                SmartHabitPeriod(
                    event_key="key2",
                    series_id=123,
                    start="2024-01-03",
                    end="2024-01-04",
                ),
            ],
        )
        assert habit.instance_count == 2

    @pytest.mark.unit
    def test_smart_habit_str(self):
        """SmartHabit str representation."""
        habit = SmartHabit(
            lineage_id=123,
            calendar_id=1,
            title="Test Habit",
        )
        assert "Test Habit" in str(habit)
        assert "enabled" in str(habit)

    @pytest.mark.unit
    def test_smart_habit_repr(self):
        """SmartHabit repr includes key info."""
        habit = SmartHabit(
            lineage_id=123,
            calendar_id=1,
            title="Test Habit",
        )
        repr_str = repr(habit)
        assert "lineage_id=123" in repr_str
        assert "Test Habit" in repr_str
        assert "ACTIVE" in repr_str

    @pytest.mark.unit
    def test_smart_habit_series_id_alias(self):
        """series_id property is alias for lineage_id."""
        habit = SmartHabit(
            lineage_id=123,
            calendar_id=1,
            title="Test Habit",
        )
        assert habit.series_id == 123
        assert habit.series_id == habit.lineage_id

    @pytest.mark.unit
    def test_smart_habit_mutable(self):
        """SmartHabit is mutable (can update fields)."""
        habit = SmartHabit(
            lineage_id=123,
            calendar_id=1,
            title="Test Habit",
        )
        habit.title = "New Title"
        assert habit.title == "New Title"

    @pytest.mark.unit
    def test_smart_habit_status(self):
        """SmartHabit status and is_enabled work."""
        habit = SmartHabit(
            lineage_id=123,
            calendar_id=1,
            title="Test Habit",
            status=HabitStatus.ACTIVE,
        )
        assert habit.is_enabled is True

        habit.status = HabitStatus.DISABLED
        assert habit.is_enabled is False

    @pytest.mark.unit
    def test_smart_habit_category_from_event_type(self):
        """Category is inferred from event_type."""
        work_habit = SmartHabit(
            lineage_id=123,
            calendar_id=1,
            title="Work Habit",
            event_type=EventType.SOLO_WORK,
        )
        assert work_habit.category == EventCategory.WORK

        personal_habit = SmartHabit(
            lineage_id=124,
            calendar_id=1,
            title="Personal Habit",
            event_type=EventType.PERSONAL,
        )
        assert personal_habit.category == EventCategory.PERSONAL

    @pytest.mark.unit
    def test_smart_habit_recurrence(self):
        """HabitRecurrence model works."""
        recurrence = HabitRecurrence(
            frequency=RecurrenceFrequency.WEEKLY,
            ideal_days=["MONDAY", "WEDNESDAY", "FRIDAY"],
            interval=1,
        )
        assert recurrence.frequency == RecurrenceFrequency.WEEKLY
        assert len(recurrence.ideal_days) == 3

    @pytest.mark.unit
    def test_smart_habit_instance_timezone_aware_from_naive(self):
        """SmartHabitInstance field_validator converts naive datetimes to UTC."""
        instance = SmartHabitInstance(
            event_id="e1",
            calendar_id=1,
            start=datetime(2024, 1, 1, 9, 0),  # naive
            end=datetime(2024, 1, 1, 10, 0),  # naive
            status="PUBLISHED",
            pinned=False,
        )
        assert instance.start.tzinfo == timezone.utc
        assert instance.end.tzinfo == timezone.utc

    @pytest.mark.unit
    def test_smart_habit_instance_timezone_preserves_aware(self):
        """SmartHabitInstance field_validator preserves existing timezone."""
        from datetime import timezone as tz
        instance = SmartHabitInstance(
            event_id="e1",
            calendar_id=1,
            start=datetime(2024, 1, 1, 9, 0, tzinfo=tz.utc),
            end=datetime(2024, 1, 1, 10, 0, tzinfo=tz.utc),
            status="PUBLISHED",
            pinned=False,
        )
        assert instance.start.tzinfo == tz.utc
        assert instance.end.tzinfo == tz.utc

    @pytest.mark.unit
    def test_changelog_entry_reason_enum(self):
        """HabitChangeLogEntry uses ChangeReason enum."""
        entry = HabitChangeLogEntry(
            id=1,
            changed_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
            series_id=123,
            event_id="e1",
            reason=ChangeReason.SMART_SERIES_EVENT_MOVED,
        )
        assert entry.reason == ChangeReason.SMART_SERIES_EVENT_MOVED
        assert entry.is_move is True
        assert entry.is_create is False


class TestSmartHabitIntegration:
    """Integration tests for SmartHabit."""

    @pytest.mark.integration
    def test_smart_habit_list(self, client):
        """Can list Smart Habits."""
        habits = SmartHabit.list(client)
        assert isinstance(habits, list)

    @pytest.mark.integration
    def test_smart_habit_has_periods(self, client):
        """Smart Habits have scheduled periods."""
        habits = SmartHabit.list(client)
        if habits:
            habits_with_periods = [h for h in habits if h.instance_count > 0]
            assert len(habits_with_periods) > 0

    @pytest.mark.integration
    def test_smart_habit_has_expected_fields(self, client):
        """Smart Habits have expected fields."""
        habits = SmartHabit.list(client)
        if habits:
            h = habits[0]
            assert hasattr(h, "lineage_id")
            assert hasattr(h, "series_id")  # alias
            assert hasattr(h, "title")
            assert hasattr(h, "category")
            assert hasattr(h, "status")
            assert hasattr(h, "periods")
            assert h.category in (EventCategory.WORK, EventCategory.PERSONAL)

    @pytest.mark.integration
    def test_smart_habit_get_by_id(self, client):
        """Can get habit by lineage ID."""
        habits = SmartHabit.list(client)
        if habits:
            target_id = habits[0].lineage_id
            habit = SmartHabit.get(target_id, client)
            assert habit.lineage_id == target_id

    @pytest.mark.integration
    def test_smart_habit_get_by_title(self, client):
        """Can find habit by title."""
        habits = SmartHabit.list(client)
        if habits:
            target = habits[0].title
            found = SmartHabit.get_by_title(target, client)
            assert found is not None
            assert found.title == target

    @pytest.mark.integration
    def test_smart_habit_get_by_title_partial(self, client):
        """Can find habit by partial title."""
        habits = SmartHabit.list(client)
        if habits:
            target = habits[0].title[:4].lower()
            found = SmartHabit.get_by_title(target, client)
            assert found is not None

    @pytest.mark.integration
    def test_smart_habit_get_by_title_not_found(self, client):
        """Returns None for non-existent habit."""
        found = SmartHabit.get_by_title("xyznonexistent123", client)
        assert found is None

    @pytest.mark.integration
    def test_smart_habit_next_period(self, client):
        """Next period property works."""
        habits = SmartHabit.list(client)
        if habits:
            h = habits[0]
            if h.periods:
                next_p = h.next_period
                # May be None if all periods are in the past
                if next_p:
                    assert isinstance(next_p, SmartHabitPeriod)

    @pytest.mark.integration
    def test_smart_habit_enable_disable(self, client):
        """Can enable and disable habits."""
        habits = SmartHabit.list(client)
        if habits:
            h = habits[0]
            original_status = h.status

            # Disable
            h.disable()
            assert h.status == HabitStatus.DISABLED

            # Re-enable
            h.enable()
            assert h.status == HabitStatus.ACTIVE

            # Restore original state if different
            if original_status == HabitStatus.DISABLED:
                h.disable()


class TestLegacyHabitIntegration:
    """Integration tests for legacy Habit."""

    @pytest.mark.integration
    def test_habit_list(self, client):
        """Can list legacy habits."""
        habits = Habit.list(client)
        assert isinstance(habits, list)

    @pytest.mark.integration
    def test_habit_has_expected_fields(self, client):
        """Legacy habits have expected fields."""
        habits = Habit.list(client)
        if habits:
            h = habits[0]
            assert hasattr(h, "id")
            assert hasattr(h, "title")
            assert hasattr(h, "enabled")
            assert hasattr(h, "duration_min")
            assert hasattr(h, "duration_max")
            assert hasattr(h, "ideal_time")

    @pytest.mark.integration
    def test_habit_get_by_id(self, client):
        """Can get legacy habit by ID."""
        habits = Habit.list(client)
        if habits:
            h = Habit.get(habits[0].id, client)
            assert h.id == habits[0].id
            assert h.title == habits[0].title

    @pytest.mark.integration
    def test_habit_planner_actions(self, client):
        """Legacy habit planner actions work (start/stop)."""
        habits = Habit.list(client)
        if habits:
            h = habits[0]
            h.start()
            h.stop()


class TestHabitChangeLogIntegration:
    """Integration tests for HabitChangeLogEntry."""

    @pytest.mark.integration
    def test_smart_habit_get_changelog(self, client):
        """Can get changelog for a Smart Habit."""
        habits = SmartHabit.list(client)
        if habits:
            h = habits[0]
            changelog = h.get_changelog(client, limit=10)
            assert isinstance(changelog, list)

    @pytest.mark.integration
    def test_changelog_entry_has_expected_fields(self, client):
        """Changelog entries have expected fields."""
        habits = SmartHabit.list(client)
        if habits:
            h = habits[0]
            changelog = h.get_changelog(client, limit=5)
            if changelog:
                entry = changelog[0]
                assert hasattr(entry, "id")
                assert hasattr(entry, "changed_at")
                assert hasattr(entry, "series_id")
                assert hasattr(entry, "event_id")
                assert hasattr(entry, "reason")

    @pytest.mark.integration
    def test_changelog_move_entry_has_times(self, client):
        """Move entries may have previous/new times."""
        habits = SmartHabit.list(client)
        if habits:
            h = habits[0]
            changelog = h.get_changelog(client, limit=50)
            moves = [e for e in changelog if e.is_move]
            if moves:
                # Some move entries have times, some don't
                moves_with_times = [m for m in moves if m.previous_start and m.new_start]
                # Just verify the property exists and is accessible
                move = moves[0]
                assert hasattr(move, "previous_start")
                assert hasattr(move, "new_start")

    @pytest.mark.integration
    def test_get_all_changelogs(self, client):
        """Can get changelogs for all habits."""
        changelogs = SmartHabit.get_all_changelogs(client=client, limit=20)
        assert isinstance(changelogs, list)

    @pytest.mark.integration
    def test_changelog_sorted_by_date(self, client):
        """All changelogs are sorted newest first."""
        changelogs = SmartHabit.get_all_changelogs(client=client, limit=20)
        if len(changelogs) > 1:
            for i in range(len(changelogs) - 1):
                assert changelogs[i].changed_at >= changelogs[i + 1].changed_at
