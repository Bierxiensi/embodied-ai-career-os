"""Project + Milestone 模型测试。"""
import pytest
from app.db.base import SessionLocal


def test_create_project():
    """创建项目，验证字段写入。"""
    db = SessionLocal()
    try:
        from app.models.project import Project

        p = Project(
            name="SO101 Embodied AI",
            goal="打造 ROS2 + VLA 真机闭环",
            status="active",
            current_version="V1",
            sort_order=0,
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        assert p.id is not None
        assert p.name == "SO101 Embodied AI"
        assert p.status == "active"
        assert p.current_version == "V1"
    finally:
        db.rollback()
        db.close()


def test_create_milestone():
    """创建里程碑，验证 FK 关联。"""
    db = SessionLocal()
    try:
        from app.models.project import Project
        from app.models.milestone import Milestone

        p = Project(name="Test Project", goal="Test", status="active",
                     current_version="V0", sort_order=0)
        db.add(p)
        db.commit()
        db.refresh(p)

        m = Milestone(
            project_id=p.id,
            version="V0",
            title="基础控制",
            goal="Python 控制舵机",
            status="in_progress",
            sort_order=0,
        )
        db.add(m)
        db.commit()
        db.refresh(m)

        assert m.id is not None
        assert m.project_id == p.id
        assert m.version == "V0"
    finally:
        db.rollback()
        db.close()


def test_task_with_project_fk():
    """Task 可选关联 Project 和 Milestone。"""
    db = SessionLocal()
    try:
        from app.models.project import Project
        from app.models.milestone import Milestone
        from app.models.task import Task

        p = Project(name="P", goal="G", status="active",
                     current_version="V0", sort_order=0)
        db.add(p)
        db.commit()
        db.refresh(p)

        m = Milestone(project_id=p.id, version="V0", title="M",
                       goal="G", status="in_progress", sort_order=0)
        db.add(m)
        db.commit()
        db.refresh(m)

        t = Task(
            title="Test task",
            status="todo",
            project_id=p.id,
            milestone_id=m.id,
        )
        db.add(t)
        db.commit()
        db.refresh(t)

        assert t.project_id == p.id
        assert t.milestone_id == m.id
    finally:
        db.rollback()
        db.close()


def test_task_without_project_works():
    """旧 Task 无 project_id/milestone_id 仍正常工作。"""
    db = SessionLocal()
    try:
        from app.models.task import Task

        t = Task(title="Old task", status="todo")
        db.add(t)
        db.commit()
        db.refresh(t)
        assert t.id is not None
        assert t.project_id is None
        assert t.milestone_id is None
    finally:
        db.rollback()
        db.close()
