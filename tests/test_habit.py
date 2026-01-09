"""
Tests for Habit and SmartHabit resources.
"""

import pytest
from datetime import datetime, timezone

from reclaim_sdk.resources.habit import (
    Habit,
    SmartHabit,
    SmartHabitInstance,
    HabitChangeLogEntry,
    EventCategory,
    ChangeReason,
)


class TestSmartHabitUnit:
    """Unit tests for SmartHabit (no API calls)."""

    @pytest.mark.unit
    def test_smart_habit_instance_count(self):
        """Instance count property works."""
        habit = SmartHabit(
            series_id=123,
            title="Test Habit",
            category=EventCategory.WORK,
            instances=[
                SmartHabitInstance(
                    event_id="e1",
                    calendar_id=1,
                    start=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
                    end=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
                    status="PUBLISHED",
                    pinned=False,
                ),
                SmartHabitInstance(
                    event_id="e2",
                    calendar_id=1,
                    start=datetime(2024, 1, 2, 9, 0, tzinfo=timezone.utc),
                    end=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc),
                    status="PUBLISHED",
                    pinned=False,
                ),
            ],
        )
        assert habit.instance_count == 2

    @pytest.mark.unit
    def test_smart_habit_str(self):
        """SmartHabit str representation."""
        habit = SmartHabit(
            series_id=123,
            title="Test Habit",
            category=EventCategory.WORK,
            instances=[],
        )
        assert "Test Habit" in str(habit)

    @pytest.mark.unit
    def test_smart_habit_repr(self):
        """SmartHabit repr includes key info."""
        habit = SmartHabit(
            series_id=123,
            title="Test Habit",
            category=EventCategory.WORK,
            instances=[],
        )
        repr_str = repr(habit)
        assert "series_id=123" in repr_str
        assert "Test Habit" in repr_str
        assert "WORK" in repr_str

    @pytest.mark.unit
    def test_smart_habit_frozen(self):
        """SmartHabit is frozen (immutable)."""
        habit = SmartHabit(
            series_id=123,
            title="Test Habit",
            category=EventCategory.WORK,
            instances=[],
        )
        with pytest.raises(Exception):  # ValidationError for frozen model
            habit.title = "New Title"

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
        # Should have habits if user has any active
        # (This will pass even with 0 habits)

    @pytest.mark.integration
    def test_smart_habit_has_instances(self, client):
        """Smart Habits have scheduled instances."""
        habits = SmartHabit.list(client)
        if habits:
            # At least one habit should have instances
            habits_with_instances = [h for h in habits if h.instance_count > 0]
            assert len(habits_with_instances) > 0

    @pytest.mark.integration
    def test_smart_habit_has_expected_fields(self, client):
        """Smart Habits have expected fields."""
        habits = SmartHabit.list(client)
        if habits:
            h = habits[0]
            assert hasattr(h, "series_id")
            assert hasattr(h, "title")
            assert hasattr(h, "category")
            assert hasattr(h, "color")
            assert hasattr(h, "instances")
            assert h.category in ("WORK", "PERSONAL")

    @pytest.mark.integration
    def test_smart_habit_get_by_title(self, client):
        """Can find habit by title."""
        habits = SmartHabit.list(client)
        if habits:
            # Search for the first habit's title
            target = habits[0].title
            found = SmartHabit.get_by_title(target, client)
            assert found is not None
            assert found.title == target

    @pytest.mark.integration
    def test_smart_habit_get_by_title_partial(self, client):
        """Can find habit by partial title."""
        habits = SmartHabit.list(client)
        if habits:
            # Search using first few characters (lowercase)
            target = habits[0].title[:4].lower()
            found = SmartHabit.get_by_title(target, client)
            assert found is not None

    @pytest.mark.integration
    def test_smart_habit_get_by_title_not_found(self, client):
        """Returns None for non-existent habit."""
        found = SmartHabit.get_by_title("xyznonexistent123", client)
        assert found is None

    @pytest.mark.integration
    def test_smart_habit_next_instance(self, client):
        """Next instance property works."""
        habits = SmartHabit.list(client)
        if habits:
            h = habits[0]
            if h.instances:
                next_inst = h.next_instance
                assert next_inst is not None
                assert isinstance(next_inst, SmartHabitInstance)


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
            # These should not raise
            h.start()
            h.stop()
            # Note: We don't test mark_complete as it changes state


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
            # May or may not have entries depending on habit history

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
        """Move entries have previous/new times."""
        habits = SmartHabit.list(client)
        if habits:
            h = habits[0]
            changelog = h.get_changelog(client, limit=50)
            moves = [e for e in changelog if e.is_move]
            if moves:
                move = moves[0]
                assert move.previous_start is not None
                assert move.new_start is not None

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
            # Check descending order
            for i in range(len(changelogs) - 1):
                assert changelogs[i].changed_at >= changelogs[i + 1].changed_at
