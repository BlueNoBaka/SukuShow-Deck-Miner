import logging
import os

logger = logging.getLogger(__name__)


class Skill:
    def __init__(self, db, series_id: int, lv=14) -> None:
        self.condition: list[str] = []
        self.effect: list[int] = []
        self.skill_id = str(series_id*100 + lv)
        self.cost = db[self.skill_id]["ConsumeAP"]
        self.condition = db[self.skill_id]["RhythmGameSkillConditionIds"]
        self.effect = db[self.skill_id]["RhythmGameSkillEffectId"]

    def __str__(self) -> str:
        return (
            f"Skill ID:  {self.skill_id}    Cost: {self.cost}\n"
            f"Condition: {self.condition}\n"
            f"Effect:    {self.effect}"
        )

    def cost_change(self, value):
        self.cost = max(0, self.cost + value)


class CenterSkill:
    def __init__(self, db, series_id: int, lv=14) -> None:
        self.condition: list[str] = []
        self.effect: list[int] = []
        self.skill_id: str = "0"
        if series_id == 0:
            return
        self.skill_id = str(series_id*100 + lv)
        self.condition = db[self.skill_id]["CenterSkillConditionIds"]
        self.effect = db[self.skill_id]["CenterSkillEffectId"]

    def __str__(self) -> str:
        return (
            f"Skill ID:  {self.skill_id}\n"
            f"Condition: {self.condition}\n"
            f"Effect:    {self.effect}"
        )


class CenterAttribute:
    def __init__(self, db, series_id: int) -> None:
        self.target: list[str] = []
        self.effect: list[int] = []
        self.skill_id: str = "0"
        if series_id == 0:
            return
        self.skill_id = str(series_id + 1)
        self.target = db[self.skill_id].get("TargetIds", None)
        self.effect = db[self.skill_id].get("CenterAttributeEffectId", None)

    def __str__(self) -> str:
        return (
            f"Skill ID:  {self.skill_id}\n"
            f"Target: {self.target}\n"
            f"Effect:    {self.effect}"
        )


if __name__ == "__main__":
    import RCardData
    db_skill = RCardData.db_load(os.path.join("Data", "RhythmGameSkills.json"))
    db_skill.update(RCardData.db_load(os.path.join("Data", "CenterSkills.json")))
    db_skill.update(RCardData.db_load(os.path.join("Data", "CenterAttributes.json")))
    skill1 = Skill(db_skill, 30324122)
    logger.debug(skill1)
    skill1.costchange(-5)
    logger.debug(skill1)
    skill1.costchange(-100)
    logger.debug(skill1)
    logger.debug(CenterSkill(db_skill, 10214010, 1))
    logger.debug(CenterAttribute(db_skill, 20215230))
