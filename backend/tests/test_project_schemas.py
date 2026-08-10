"""Project + Milestone Schema 测试。"""
import pytest
from app.schemas.project import (
    ProjectOut, ProjectCreate, ProjectPatch,
    MilestoneOut, MilestoneCreate, MilestonePatch,
)


def test_project_create_validation():
    """ProjectCreate 字段校验。"""
    p = ProjectCreate(name="Test", goal="Goal", status="active", current_version="V0")
    assert p.name == "Test"
    assert p.status == "active"
    assert p.sort_order == 0


def test_project_patch_partial():
    """ProjectPatch 排除未设字段。"""
    p = ProjectPatch(status="paused")
    data = p.model_dump(exclude_unset=True)
    assert data == {"status": "paused"}
    assert "name" not in data


def test_project_out_from_attributes():
    """ProjectOut 从 ORM 对象构造。"""
    from app.models.project import Project
    orm = Project(id=1, name="P", goal="G", status="active",
                   current_version="V1", sort_order=0)
    out = ProjectOut.model_validate(orm)
    assert out.id == 1
    assert out.status == "active"


def test_milestone_out():
    """MilestoneOut 基础字段。"""
    from app.models.milestone import Milestone
    orm = Milestone(id=1, project_id=1, version="V0", title="M",
                     goal="G", status="in_progress", sort_order=0)
    out = MilestoneOut.model_validate(orm)
    assert out.version == "V0"
    assert out.project_id == 1
