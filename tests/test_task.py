"""
Tests for Task resource.
"""

import pytest
from datetime import datetime, timedelta

from reclaim_sdk.resources.task import Task, TaskPriority, TaskStatus, EventColor


class TestTaskUnit:
    """Unit tests for Task (no API calls)."""

    @pytest.mark.unit
    def test_task_duration_property(self):
        """Duration property converts time chunks to hours."""
        task = Task.model_construct(time_chunks_required=8)  # 8 chunks = 2 hours
        assert task.duration == 2.0

    @pytest.mark.unit
    def test_task_duration_setter(self):
        """Duration setter converts hours to time chunks."""
        task = Task.model_construct(time_chunks_required=None)
        task.duration = 1.5  # 1.5 hours = 6 chunks
        assert task.time_chunks_required == 6

    @pytest.mark.unit
    def test_task_min_work_duration_property(self):
        """Min work duration converts chunks to hours."""
        task = Task.model_construct(min_chunk_size=2)  # 2 chunks = 0.5 hours
        assert task.min_work_duration == 0.5

    @pytest.mark.unit
    def test_task_max_work_duration_property(self):
        """Max work duration converts chunks to hours."""
        task = Task.model_construct(max_chunk_size=4)  # 4 chunks = 1 hour
        assert task.max_work_duration == 1.0

    @pytest.mark.unit
    def test_task_up_next_property(self):
        """Up next property maps to on_deck."""
        task = Task.model_construct(on_deck=True)
        assert task.up_next is True

    @pytest.mark.unit
    def test_task_priority_enum(self):
        """TaskPriority enum has correct values."""
        assert TaskPriority.P1.value == "P1"
        assert TaskPriority.P2.value == "P2"
        assert TaskPriority.P3.value == "P3"
        assert TaskPriority.P4.value == "P4"

    @pytest.mark.unit
    def test_task_status_enum(self):
        """TaskStatus enum has correct values."""
        assert TaskStatus.NEW.value == "NEW"
        assert TaskStatus.SCHEDULED.value == "SCHEDULED"
        assert TaskStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert TaskStatus.COMPLETE.value == "COMPLETE"
        assert TaskStatus.ARCHIVED.value == "ARCHIVED"


class TestTaskIntegration:
    """Integration tests for Task."""

    @pytest.mark.integration
    def test_task_list(self, client):
        """Can list tasks."""
        tasks = Task.list(client)
        assert isinstance(tasks, list)
        # Should have at least some tasks
        assert len(tasks) > 0

    @pytest.mark.integration
    def test_task_list_returns_task_objects(self, client):
        """Task.list returns Task objects."""
        tasks = Task.list(client)
        if tasks:
            assert isinstance(tasks[0], Task)
            assert hasattr(tasks[0], "title")
            assert hasattr(tasks[0], "status")

    @pytest.mark.integration
    def test_task_get_by_id(self, client):
        """Can get task by ID."""
        tasks = Task.list(client)
        if tasks:
            task = Task.get(tasks[0].id, client)
            assert task.id == tasks[0].id
            assert task.title == tasks[0].title

    @pytest.mark.integration
    def test_task_has_expected_fields(self, client):
        """Tasks have expected fields populated."""
        tasks = Task.list(client)
        if tasks:
            task = tasks[0]
            # These fields should exist (may be None)
            assert hasattr(task, "title")
            assert hasattr(task, "priority")
            assert hasattr(task, "status")
            assert hasattr(task, "due")
            assert hasattr(task, "time_chunks_required")

    @pytest.mark.integration
    def test_task_crud_lifecycle(self, client, sample_task_data):
        """Test full CRUD lifecycle for a task."""
        # Create
        task = Task(
            title=sample_task_data["title"],
            notes=sample_task_data["notes"],
            due=sample_task_data["due"],
            priority=TaskPriority.P3,
        )
        task.duration = 1.0
        task.save()

        assert task.id is not None
        created_id = task.id

        try:
            # Read
            fetched = Task.get(created_id, client)
            assert fetched.title == sample_task_data["title"]

            # Update
            task.title = "Updated Test Task"
            task.save()

            refreshed = Task.get(created_id, client)
            assert refreshed.title == "Updated Test Task"

        finally:
            # Delete (cleanup)
            task.delete()

            # Verify deleted
            with pytest.raises(Exception):
                Task.get(created_id, client)
