"""博士模块种子数据（Phase 1）。

数据来源：docs/北京在职博士-易录取版.md 与 docs/北京在职博士-机器人具身智能.md
（2026-08-24 整理）。本脚本把两文档中"已筛选的院校 / 导师 / 方向"抽取为结构化记录，
首次运行（表为空）时写入，幂等。

用法：
    cd backend
    python scripts/seed_phd.py
"""

from __future__ import annotations

from datetime import date

from app.agents.phd.agent import PhDMatchEngine, _is_home_school
from app.db.base import Base, SessionLocal, engine
from app.models.phd import PhDAdvisor, PhDTarget, ResearchDirection


# ── 研究方向主数据（6 个，用户转型目标里的方向）──
DIRECTIONS = [
    {"key": "post_training", "name": "大模型后训练（Post-Training）",
     "description": "llm 主攻：SFT/DPO/GRPO/对齐", "interest_weight": 100},
    {"key": "vla", "name": "VLA / 具身智能",
     "description": "长期方向：视觉-语言-动作", "interest_weight": 100},
    {"key": "embodied", "name": "具身智能 / 机器人",
     "description": "长期研究目标", "interest_weight": 95},
    {"key": "multimodal", "name": "多模态 / VLM",
     "description": "vlm 卡位", "interest_weight": 90},
    {"key": "robotics_control", "name": "机器人控制 / 智能系统",
     "description": "具身相关：控制工程/智能系统", "interest_weight": 90},
    {"key": "spatiotemporal", "name": "时空预测 / 小样本预报",
     "description": "科研底座（洪水预报）", "interest_weight": 85},
]

# ── 院校 / 项目机会（13 个，两文档去重合并）──
# direction_key / track_key / tier / city / in_service_friendly /
# min_publication(none/ei/sci) / application_deadline / notes
TARGETS = [
    {"institution": "北京邮电大学", "city": "北京", "tier": "211",
     "direction_key": "robotics_control", "track_key": "embodied",
     "in_service_friendly": True, "min_publication": "none",
     "application_deadline": date(2026, 5, 15),
     "notes": "AI学院智能机器人方向；申请-考核制；北航背景加分；英语CET-6≥425"},
    {"institution": "中国石油大学（北京）", "city": "北京", "tier": "211",
     "direction_key": "robotics_control", "track_key": "ai-algo",
     "in_service_friendly": True, "min_publication": "none",
     "application_deadline": None,
     "notes": "学费最低1.5万/年；英语CET-4≥425或校内补考；竞争小；全年报名"},
    {"institution": "北京科技大学", "city": "北京", "tier": "211",
     "direction_key": "robotics_control", "track_key": "ai-algo",
     "in_service_friendly": True, "min_publication": "none",
     "application_deadline": None,
     "notes": "2026大幅扩招；工业智能新方向；企业课题可作论文"},
    {"institution": "北京交通大学", "city": "北京", "tier": "211",
     "direction_key": "robotics_control", "track_key": "embodied",
     "in_service_friendly": True, "min_publication": "none",
     "application_deadline": None,
     "notes": "控制工程方向对口；定向就业英语无硬性分数"},
    {"institution": "北京信息科技大学", "city": "北京", "tier": "市属",
     "direction_key": "robotics_control", "track_key": "embodied",
     "in_service_friendly": True, "min_publication": "none",
     "application_deadline": date(2026, 5, 11),
     "notes": "门槛最低但方向窄；高动态导航与控制技术"},
    {"institution": "华北电力大学", "city": "北京", "tier": "211",
     "direction_key": "robotics_control", "track_key": "embodied",
     "in_service_friendly": False, "min_publication": "none",
     "application_deadline": None,
     "notes": "要求硕士毕业后工作3年以上；智能机器人与无人系统方向对口"},
    {"institution": "北京航空航天大学（本校）", "city": "北京", "tier": "985",
     "direction_key": "vla", "track_key": "embodied",
     "in_service_friendly": True, "min_publication": "none",
     "application_deadline": None,
     "notes": "本校在读主场优势；非全名额≤10%；优先联系导师"},
    {"institution": "北京大学", "city": "北京", "tier": "985",
     "direction_key": "embodied", "track_key": "embodied",
     "in_service_friendly": False, "min_publication": "none",
     "application_deadline": date(2025, 12, 19),
     "notes": "前沿工程博士；要求硕士+5年；年限不足"},
    {"institution": "清华大学", "city": "北京", "tier": "985",
     "direction_key": "embodied", "track_key": "embodied",
     "in_service_friendly": False, "min_publication": "none",
     "application_deadline": date(2025, 12, 31),
     "notes": "创新领军工程博士；要求硕士+5年；年限不足"},
    {"institution": "中国人民大学（高瓴AI）", "city": "北京", "tier": "985",
     "direction_key": "vla", "track_key": "embodied",
     "in_service_friendly": False, "min_publication": "none",
     "application_deadline": date(2025, 12, 10),
     "notes": "明确具身智能方向；要求入学前3年工作+成果；年限不足"},
    {"institution": "中国人民大学（信息学院）", "city": "北京", "tier": "985",
     "direction_key": "vla", "track_key": "embodied",
     "in_service_friendly": False, "min_publication": "none",
     "application_deadline": date(2025, 12, 10),
     "notes": "含具身智能；可深圳培养"},
    {"institution": "北京理工大学", "city": "北京", "tier": "985",
     "direction_key": "robotics_control", "track_key": "embodied",
     "in_service_friendly": False, "min_publication": "none",
     "application_deadline": None,
     "notes": "自动化学院智能机器人；非全简章待发布"},
    {"institution": "中国科学院大学（自动化所）", "city": "北京", "tier": "中科院",
     "direction_key": "robotics_control", "track_key": "embodied",
     "in_service_friendly": False, "min_publication": "none",
     "application_deadline": date(2026, 1, 9),
     "notes": "自动化所基本不招普通非全，除非专项计划"},
]

# ── 导师（8 个，按 institution 关联机会；文档未列姓名者标注待确认）──
# institution 用于反查 target_id；title / research_area / recruiting /
# in_service_friendly / notes
ADVISORS = [
    {"institution": "北京邮电大学", "name": "北邮 AI学院·智能机器人方向导师（待确认）",
     "title": "教授", "research_area": "智能机器人 / 控制理论与控制工程",
     "recruiting": True, "in_service_friendly": True,
     "notes": "文档未列具体姓名，需检索人工智能学院导师"},
    {"institution": "北京航空航天大学（本校）", "name": "北航·本校导师（自动化/AI/机器人，待确认）",
     "title": "教授", "research_area": "视具体导师方向",
     "recruiting": True, "in_service_friendly": True,
     "notes": "2026-09-24 裁决：保留但降权（HOME_SCHOOL_PENALTY），申请季前最终裁决；非全名额需确认"},
    {"institution": "中国石油大学（北京）", "name": "中石大·自动化/智能控制方向导师（待确认）",
     "title": "副教授", "research_area": "自动化控制 / 智能控制",
     "recruiting": True, "in_service_friendly": True,
     "notes": "能源类院校机器人非传统强项，可找自动化方向"},
    {"institution": "中国科学院大学（自动化所）", "name": "国科大自动化所·机器人方向导师（待确认）",
     "title": "研究员", "research_area": "智能机器人与无人系统",
     "recruiting": False, "in_service_friendly": False,
     "notes": "基本不招普通非全，除非专项计划"},
    {"institution": "中国人民大学（高瓴AI）", "name": "人大高瓴·具身智能方向导师（待确认）",
     "title": "教授", "research_area": "具身智能 / 无人系统",
     "recruiting": True, "in_service_friendly": False,
     "notes": "方向明确但要求入学前3年工作+成果"},
    {"institution": "北京大学", "name": "段慧玲",
     "title": "教授", "research_area": "机器人与智能系统",
     "recruiting": True, "in_service_friendly": False,
     "notes": "前沿工程博士，要求硕士+5年"},
    {"institution": "北京大学", "name": "谢广明",
     "title": "教授", "research_area": "机器人与智能系统",
     "recruiting": True, "in_service_friendly": False,
     "notes": "前沿工程博士，要求硕士+5年"},
    {"institution": "北京大学", "name": "喻俊志",
     "title": "教授", "research_area": "机器人与智能系统",
     "recruiting": True, "in_service_friendly": False,
     "notes": "前沿工程博士，要求硕士+5年"},
]


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(ResearchDirection).count() == 0:
            for d in DIRECTIONS:
                db.add(ResearchDirection(**d))
            print(f"  + research_directions: {len(DIRECTIONS)} 条")

        target_id_by_inst: dict[str, int] = {}
        if db.query(PhDTarget).count() == 0:
            for t in TARGETS:
                row = PhDTarget(**t, source="seed")
                db.add(row)
                db.flush()
                target_id_by_inst[t["institution"]] = row.id
            print(f"  + phd_targets: {len(TARGETS)} 条")
        else:
            # 已存在则建立 institution → id 映射，供导师关联
            for t in db.query(PhDTarget).all():
                target_id_by_inst[t.institution] = t.id

        if db.query(PhDAdvisor).count() == 0:
            for a in ADVISORS:
                inst = a.pop("institution")
                tid = target_id_by_inst.get(inst)
                db.add(PhDAdvisor(target_id=tid, source="seed", **a))
            print(f"  + phd_advisors: {len(ADVISORS)} 条")

        db.commit()

        # 录入即匹配：把六维结果缓存进 match_json，前端直接展示
        advisors = db.query(PhDAdvisor).all()
        matched = 0
        for adv in advisors:
            if adv.match_json:
                continue
            target = db.get(PhDTarget, adv.target_id) if adv.target_id else None
            direction = (
                db.query(ResearchDirection)
                .filter(ResearchDirection.key == target.direction_key)
                .first()
                if target and target.direction_key
                else None
            )
            res = PhDMatchEngine.compute(
                direction_interest=direction.interest_weight if direction else 70,
                tier=target.tier if target else None,
                city=target.city if target else None,
                min_publication=target.min_publication if target else None,
                target_in_service=target.in_service_friendly if target else False,
                advisor_in_service=adv.in_service_friendly,
                application_deadline=target.application_deadline if target else None,
                is_home_school=_is_home_school(
                    target.institution if target else "", adv.name or ""
                ),
            )
            adv.match_json = {
                "overall": int(res.overall),
                "grade": res.grade,
                "dimensions": res.dimensions,
                "gaps": res.gaps,
            }
            matched += 1
        db.commit()
        if matched:
            print(f"  ~ 计算六维匹配: {matched} 条")
    finally:
        db.close()


if __name__ == "__main__":
    # 确保表存在（开发态用 create_all；生产走迁移）
    Base.metadata.create_all(bind=engine)
    print("种子博士模块数据：")
    seed()
    print("完成。")
