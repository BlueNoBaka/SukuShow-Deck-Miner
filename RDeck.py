import logging
import os
from RSkill import *
from copy import copy
from math import ceil
from enum import Enum

logger = logging.getLogger(__name__)


class Rarity(Enum):
    R = 3
    SR = 4
    UR = 5
    LR = 7
    DR = 8
    BR = 9


STATUS_CURVES = {
    Rarity.R: [(1, 1), (30, 50), (40, 70), (60, 100), (70, 110), (80, 120)],
    Rarity.SR: [(1, 1), (40, 50), (60, 70), (80, 100), (90, 110), (100, 120)],
    Rarity.UR: [(1, 1), (60, 50), (80, 70), (100, 100), (110, 110), (120, 120)],
    Rarity.LR: [(1, 1), (100, 70), (120, 100), (130, 110), (140, 120)],
    Rarity.DR: [(1, 1), (100, 70), (120, 100), (130, 110), (140, 120)],
    Rarity.BR: [(1, 1), (80, 70), (100, 100), (110, 110), (120, 120)],
}

HP_CURVES = {
    Rarity.R: [(1, 20), (30, 50), (40, 70), (60, 100)],
    Rarity.SR: [(1, 20), (40, 50), (60, 70), (80, 100)],
    Rarity.UR: [(1, 20), (60, 50), (80, 70), (100, 100)],
    Rarity.LR: [(1, 20), (100, 70), (120, 100)],
    Rarity.DR: [(1, 20), (100, 70), (120, 100)],
    Rarity.BR: [(1, 20), (80, 70), (100, 100)],
}

# 音游特训1无技能减费效果，复用了特训0的技能Id
# 故与特训0合并不再单列，以免读取不存在的技能Id
EVOLUTION = {
    Rarity.R: [(40, 0), (60, 2), (70, 3), (80, 4)],
    Rarity.SR: [(60, 0), (80, 2), (90, 3), (100, 4)],
    Rarity.UR: [(80, 0), (100, 2), (110, 3), (120, 4)],
    Rarity.LR: [(100, 0), (120, 2), (130, 3), (140, 4)],
    Rarity.DR: [(100, 0), (120, 2), (130, 3), (140, 4)],
    Rarity.BR: [(80, 0), (100, 2), (110, 3), (120, 4)],
}


def _interpolate_value(curve, lv):
    if lv <= curve[0][0]:
        return curve[0][1]

    for i in range(1, len(curve)):
        lv_start, val_start = curve[i - 1]
        lv_end, val_end = curve[i]
        if lv <= lv_end:
            t = (lv - lv_start) / (lv_end - lv_start)
            return val_start + t * (val_end - val_start)

    return curve[-1][1]


def _get_card_status(rarity: Rarity, lv: int) -> tuple[float, float, int]:
    status = _interpolate_value(STATUS_CURVES[rarity], lv)
    hp = _interpolate_value(HP_CURVES[rarity], lv)
    evo = _get_evolution(rarity, lv)
    return status, hp, evo


def _get_evolution(rarity: Rarity, lv: int) -> int:
    stages = EVOLUTION[rarity]
    for limit, stage in stages:
        if lv <= limit:
            return stage
    return stages[-1][1]


class Card():
    _cardobj_cache = {}
    _friend_cache = {}
    def __init__(self, db_card, db_skill, series_id, lv_list=None):
        if lv_list == None:
            lv_list = [140, 14, 14]
        self.card_id: str = f"{series_id}"
        self.full_name: str = f"[{db_card[self.card_id]['Name']}] {db_card[self.card_id]['Description']}".replace('\xa0', ' ')
        self.characters_id: int = db_card[self.card_id]["CharactersId"]
        self.card_level: int = lv_list[0]

        self.smile: int
        self.pure: int
        self.cool: int
        self.mental: int

        evo = self._init_status(db_card)
        self.center_attribute: CenterAttribute = CenterAttribute(db_skill, db_card[self.card_id]["CenterAttributeSeriesId"])
        self.center_skill: CenterSkill = CenterSkill(db_skill, db_card[self.card_id]["CenterSkillSeriesId"], lv_list[1])
        self.skill_unit: Skill = Skill(db_skill, int(f"3{self.card_id[1:]}{evo}"), lv_list[2])
        self.cost: int = self.skill_unit.cost
        self.active_count: int = 0
        self.is_except: bool = False

    @classmethod
    def get_instance(cls, db_card, db_skill, series_id, lv_list = None):
        key = series_id
        if key not in cls._cardobj_cache:
            # 只有第一次会执行繁琐的数据库查找和计算
            cls._cardobj_cache[key] = cls(db_card, db_skill, series_id, lv_list)
        
        # 使用 copy 或 deepcopy 取决于 Skill 类是否是可变的
        return copy(cls._cardobj_cache[key])
    
    @classmethod
    def get_friend(cls, db_card, db_skill, series_id, lv_list = None):
        key = series_id
        if key not in cls._friend_cache:
            # 只有第一次会执行繁琐的数据库查找和计算
            cls._friend_cache[key] = cls(db_card, db_skill, series_id, lv_list)
        
        # 使用 copy 或 deepcopy 取决于 Skill 类是否是可变的
        return copy(cls._friend_cache[key])

    def __copy__(self):
        cls = self.__class__
        new = cls.__new__(cls)

        new.__dict__ = self.__dict__.copy()

        return new

    def __str__(self) -> str:
        return (
            # f"Card ID: {self.card_id}\n"
            f"Name: {self.full_name}"
            # f"Character ID: {self.characters_id}\n"
            # f"Smile: {self.smile}   Pure: {self.pure}   Cool: {self.cool}\n"
            # f"Mental: {self.mental}\n"
            # f"Active Count: {self.active_count}\n"
            # f"===== Center Attribute =====\n{self.center_attribute}\n"
            # f"===== Center Skill =====\n{self.center_skill}\n"
            # f"===== Skill =====\n"
            # f"Cost: {self.cost}\n{self.skill_unit}"
        )

    def _init_status(self, db_card):
        rarity = Rarity(db_card[self.card_id]["Rarity"])
        status_norm, hp_norm, evo = _get_card_status(rarity, self.card_level)
        self.smile = ceil(db_card[self.card_id]["MaxSmile"][-3] * status_norm / 100)
        self.pure = ceil(db_card[self.card_id]["MaxPure"][-3] * status_norm / 100)
        self.cool = ceil(db_card[self.card_id]["MaxCool"][-3] * status_norm / 100)
        self.mental = ceil(db_card[self.card_id]["MaxMental"][-3] * hp_norm / 100)
        return evo

    def get_skill(self):
        self.active_count += 1
        return self.skill_unit.condition, self.skill_unit.effect

    def get_center_attribute(self):
        return zip(self.center_attribute.target, self.center_attribute.effect)

    def get_center_skill(self):
        return zip(self.center_skill.condition, self.center_skill.effect)

    def cost_change(self, value):
        self.cost = max(0, self.cost + value)


class Deck():
    def __init__(self, db_card, db_skill, card_info: list) -> None:
        self.cards: list[Card] = []
        self.queue: list[Card] = []
        self.friend: Card = None
        self.appeal: int = 0
        self.card_log: list[str] = []
        self.topcard: Card
        for card in card_info:
            self.cards.append(Card.get_instance(db_card, db_skill, card[0], card[1]))
        self.reset()

    def reset(self):
        self.queue = [card for card in self.cards if not card.is_except]
        if not self.queue:
            self.queue.append(None)
            # 卡组全部除外时特殊处理
        self.topcard = self.queue[0]
    
    def exceptcard(self, card: Card):
        card.is_except = True
        # 模拟器只在重置牌库时检查除外标记
        # 对于LR梢这种先重置牌库再标记除外的卡，就会导致已被除外的LR梢多在牌库里出现一次
        # 因此在触发除外时额外检查牌库中是否有刚被除外的卡，避免未被除外
        for index, deckcard in enumerate(self.queue):
            if deckcard.is_except:
                self.queue.pop(index)
                if not self.queue:
                    self.reset()
                else:
                    self.topcard = self.queue[0]
                break
        

    def topskill(self):
        self.card_log.append(self.topcard.full_name)
        result = self.queue.pop(0).get_skill()
        if len(self.queue) == 0:
            self.reset()
        self.topcard = self.queue[0]
        return result

    def appeal_calc(self, music_type):
        result = 0
        for card in self.cards:
            appeals = [card.smile, card.pure, card.cool]
            appeals[music_type - 1] *= 10
            result += sum(appeals)
        if self.friend:
            appeals = [self.friend.smile, self.friend.pure, self.friend.cool]
            appeals[music_type - 1] *= 10
            result += sum(appeals)
        result = ceil(result / 10)
        self.appeal = result
        return result

    def mental_calc(self):
        result = 0
        for card in self.cards:
            result += card.mental
        if self.friend:
            result += self.friend.mental
        return result

    def used_all_skill_calc(self):
        return len(self.card_log)


if __name__ == "__main__":
    import RCardData
    db_carddata = RCardData.db_load(os.path.join("Data", "CardDatas.json"))
    db_skill = RCardData.db_load(os.path.join("Data", "RhythmGameSkills.json"))
    db_skill.update(RCardData.db_load(os.path.join("Data", "CenterSkills.json")))
    db_skill.update(RCardData.db_load(os.path.join("Data", "CenterAttributes.json")))

    d = Deck(db_carddata, db_skill, [(1011501, None),
                                     (1021523, None),
                                     (1023901, None),
                                     (1033514, None),
                                     (1032518, None),
                                     (1031519, None)])
    for card in d.cards:
        logger.debug(card)
    for condition, effect in d.topskill():
        logger.debug(f"Condition: {condition}  |   Effect: {effect}")
    logger.debug(d.cards[0].active_count)
