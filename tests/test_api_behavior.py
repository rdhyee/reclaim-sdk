"""
API Behavior Tests.

These tests document the actual behavior of the Reclaim API,
including what endpoints work and which ones fail or are forbidden.

This serves as living documentation of API capabilities.
"""

import pytest

from reclaim_sdk.client import ReclaimClient
from reclaim_sdk.exceptions import ReclaimAPIError, RecordNotFound


class TestSwaggerDocumentedEndpoints:
    """
    Tests for endpoints documented in Swagger spec.
    https://api.app.reclaim.ai/swagger/reclaim-api-0.1.yml
    """

    @pytest.mark.integration
    def test_habits_daily_list(self, client):
        """GET /api/assist/habits/daily - List legacy habits."""
        result = client.get("/api/assist/habits/daily")
        assert isinstance(result, list)

    @pytest.mark.integration
    def test_habits_daily_get_by_id(self, client):
        """GET /api/assist/habits/daily/{id} - Get single habit."""
        habits = client.get("/api/assist/habits/daily")
        if habits:
            habit_id = habits[0]["id"]
            result = client.get(f"/api/assist/habits/daily/{habit_id}")
            assert "id" in result
            assert result["id"] == habit_id

    @pytest.mark.integration
    def test_habits_templates_list(self, client):
        """GET /api/assist/habits/templates - List habit templates."""
        result = client.get("/api/assist/habits/templates")
        assert isinstance(result, list)
        assert len(result) > 0  # Should have preset templates

    @pytest.mark.integration
    def test_habits_template_get(self, client):
        """GET /api/assist/habits/template?templateKey=LUNCH - Get specific template."""
        result = client.get("/api/assist/habits/template?templateKey=LUNCH")
        assert "displayTitle" in result or "name" in result

    @pytest.mark.integration
    def test_changelog_smart_habits(self, client):
        """GET /api/changelog/smart-habits - Get habit changelog."""
        # First get a series ID from events
        events = client.get("/api/events")
        smart_habits = [e for e in events if e.get("reclaimEventType") == "SMART_HABIT"]

        if smart_habits:
            series_id = smart_habits[0].get("assist", {}).get("seriesLineageId")
            if series_id:
                result = client.get(f"/api/changelog/smart-habits?lineageIds={series_id}")
                assert isinstance(result, list)

    @pytest.mark.integration
    def test_timeschemes_list(self, client):
        """GET /api/timeschemes - List time schemes (Hours)."""
        result = client.get("/api/timeschemes")
        assert isinstance(result, list)
        assert len(result) >= 3  # At least Working/Personal/Meeting Hours

    @pytest.mark.integration
    def test_tasks_list(self, client):
        """GET /api/tasks - List tasks."""
        result = client.get("/api/tasks")
        assert isinstance(result, list)

    @pytest.mark.integration
    def test_users_current(self, client):
        """GET /api/users/current - Get current user."""
        result = client.get("/api/users/current")
        assert "id" in result
        assert "email" in result

    @pytest.mark.integration
    def test_events_list(self, client):
        """GET /api/events - List calendar events."""
        result = client.get("/api/events")
        assert isinstance(result, list)


class TestUndocumentedWorkingEndpoints:
    """
    Tests for endpoints NOT in Swagger but that work.
    These are discovered through reverse-engineering.
    """

    @pytest.mark.integration
    def test_planner_done_habit(self, client):
        """POST /api/planner/done/habit/{id} - Mark habit complete (WORKS)."""
        habits = client.get("/api/assist/habits/daily")
        if habits:
            habit_id = habits[0]["id"]
            # This should work without raising
            result = client.post(f"/api/planner/done/habit/{habit_id}")
            assert "taskOrHabit" in result or "events" in result

    @pytest.mark.integration
    def test_planner_start_habit(self, client):
        """POST /api/planner/start/habit/{id} - Start habit (WORKS)."""
        habits = client.get("/api/assist/habits/daily")
        if habits:
            habit_id = habits[0]["id"]
            result = client.post(f"/api/planner/start/habit/{habit_id}")
            assert "taskOrHabit" in result or "events" in result

    @pytest.mark.integration
    def test_planner_stop_habit(self, client):
        """POST /api/planner/stop/habit/{id} - Stop habit (WORKS)."""
        habits = client.get("/api/assist/habits/daily")
        if habits:
            habit_id = habits[0]["id"]
            result = client.post(f"/api/planner/stop/habit/{habit_id}")
            assert "taskOrHabit" in result or "events" in result


class TestForbiddenEndpoints:
    """
    Tests documenting endpoints that return Forbidden.
    These are useful to track in case API access changes.
    """

    @pytest.mark.integration
    def test_calendars_forbidden(self, client):
        """GET /api/calendars - Returns Forbidden."""
        with pytest.raises(ReclaimAPIError, match="Forbidden"):
            client.get("/api/calendars")

    @pytest.mark.integration
    def test_planner_log_work_habit_forbidden(self, client):
        """POST /api/planner/log-work/habit/{id} - Returns Forbidden."""
        habits = client.get("/api/assist/habits/daily")
        if habits:
            habit_id = habits[0]["id"]
            with pytest.raises(ReclaimAPIError, match="Forbidden"):
                client.post(f"/api/planner/log-work/habit/{habit_id}?minutes=15")

    @pytest.mark.integration
    def test_planner_add_time_habit_forbidden(self, client):
        """POST /api/planner/add-time/habit/{id} - Returns Forbidden."""
        habits = client.get("/api/assist/habits/daily")
        if habits:
            habit_id = habits[0]["id"]
            with pytest.raises(ReclaimAPIError, match="Forbidden"):
                client.post(f"/api/planner/add-time/habit/{habit_id}?minutes=15")

    @pytest.mark.integration
    def test_planner_prioritize_habit_forbidden(self, client):
        """POST /api/planner/prioritize/habit/{id} - Returns Forbidden."""
        habits = client.get("/api/assist/habits/daily")
        if habits:
            habit_id = habits[0]["id"]
            with pytest.raises(ReclaimAPIError, match="Forbidden"):
                client.post(f"/api/planner/prioritize/habit/{habit_id}")

    @pytest.mark.integration
    def test_smart_series_forbidden(self, client):
        """GET /api/assist/smart-series/{id} - Returns Forbidden."""
        # Get a series ID from events
        events = client.get("/api/events")
        smart_habits = [e for e in events if e.get("reclaimEventType") == "SMART_HABIT"]

        if smart_habits:
            series_id = smart_habits[0].get("assist", {}).get("seriesLineageId")
            if series_id:
                with pytest.raises(ReclaimAPIError, match="Forbidden"):
                    client.get(f"/api/assist/smart-series/{series_id}")


class TestSmartHabitViaEvents:
    """
    Tests for accessing Smart Habits through the events API.
    This is the only way to get active habit information.
    """

    @pytest.mark.integration
    def test_events_contain_smart_habits(self, client):
        """Events API returns Smart Habit events."""
        events = client.get("/api/events")
        smart_habits = [e for e in events if e.get("reclaimEventType") == "SMART_HABIT"]
        # Should have some if user has active habits
        assert isinstance(smart_habits, list)

    @pytest.mark.integration
    def test_smart_habit_events_have_series_id(self, client):
        """Smart Habit events have seriesLineageId for grouping."""
        events = client.get("/api/events")
        smart_habits = [e for e in events if e.get("reclaimEventType") == "SMART_HABIT"]

        if smart_habits:
            event = smart_habits[0]
            assert "assist" in event
            assert "seriesLineageId" in event["assist"]

    @pytest.mark.integration
    def test_smart_habit_events_have_scheduling_info(self, client):
        """Smart Habit events have scheduling information."""
        events = client.get("/api/events")
        smart_habits = [e for e in events if e.get("reclaimEventType") == "SMART_HABIT"]

        if smart_habits:
            event = smart_habits[0]
            assert "eventStart" in event
            assert "eventEnd" in event
            assert "title" in event
            assert "type" in event  # WORK or PERSONAL
