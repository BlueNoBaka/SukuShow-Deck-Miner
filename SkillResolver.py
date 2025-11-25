import logging
from enum import Enum
from RLiveStatus import *
from RDeck import Card

logger = logging.getLogger(__name__)


class TargetType(Enum):
    """
    C位特性目标
    """
    Member = 1
    Unit = 2
    Generation = 3
    StyleType = 4
    All = 5


UNIT_DICT = {101: {1021, 1031, 1041},
             102: {1022, 1032, 1042},
             103: {1023, 1033, 1043},
             105: {1051, 1052}}


def CheckTarget(target_id: str, card: Card = None):
    """
    根据ID检查给定条件是否满足。

    Args:
        target_id (str): 技能条件ID。
        card (Card): 。

    Returns:
        bool: 如果条件满足则返回 True，否则返回 False。
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"\n--- 检查C位特性目标ID: {target_id} ---")

    # 所有目标ID都是5位数字
    if len(target_id) != 5:
        logger.error(f"  错误: 目标ID '{target_id}' 长度不符合已知规则 (应为5位)。 -> 不满足")
        return False

    try:
        target_type = TargetType(int(target_id[0]))
        target_value = int(target_id[1:])
    except ValueError:
        logger.error(f"  错误: 无法解析条件ID '{target_id}' -> 不满足")
        return False

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"  解析结果: 目标类型={target_type.name}, 数值={target_value}")

    is_satisfied = False

    match target_type:
        case TargetType.Member:
            if card.characters_id == target_value:
                is_satisfied = True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  条件: 指定成员 -> {'满足' if is_satisfied else '不满足'} {card.full_name}")

        case TargetType.Unit:
            if card.characters_id in UNIT_DICT[target_value]:
                is_satisfied = True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  条件: 指定小组 -> {'满足' if is_satisfied else '不满足'} {card.full_name}")

        case TargetType.Generation:
            if str(card.characters_id).startswith(str(target_value)):
                is_satisfied = True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  条件: 指定期数 -> {'满足' if is_satisfied else '不满足'} {card.full_name}")

        case TargetType.StyleType:
            # 暂无实装此条件的卡牌
            pass

        case TargetType.All:
            is_satisfied = True

        case _:
            logger.error(f"  未知条件类型: {target_type.name} ({target_id})。 -> 不满足")

    return is_satisfied


def CheckMultiTarget(target_ids: list[str], card=None):
    result = any(CheckTarget(target_id, card) for target_id in target_ids)
    return result


class CenterAttributeEffectType(Enum):
    """
    C位特性效果类型
    """
    SmileRateChange = 1
    PureRateChange = 2
    CoolRateChange = 3
    SmileValueChange = 4
    PureValueChange = 5
    CoolValueChange = 6
    MentalRateChange = 7
    MentalValueChange = 8
    ConsumeAPChange = 9
    CoolTimeChange = 10
    APGainRateChange = 11
    VoltageGainRateChange = 12
    APRateChangeResetGuard = 13


def ApplyCenterAttribute(player_attrs: PlayerAttributes, effect_id: int, target: list[str] = None):
    """
    根据EffectsID解析并应用C位特性。

    Args:
        effect_id (int): C位特性效果的ID。
        target (str)
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"\n--- 解析效果ID: {effect_id} ---")

    # 将ID解析为字符串方便操作
    id_str = str(effect_id)

    # 根据ID字符串长度判断 EnumBaseValue 的位数
    if len(id_str) == 8:  # EnumBaseValue 是 1 位的情况 (1-9)
        enum_base_value = int(id_str[0])
        change_direction = int(id_str[1])
        value_data = int(id_str[2:])
    elif len(id_str) == 9:  # EnumBaseValue 是 2 位的情况 (10-13)
        enum_base_value = int(id_str[:2])
        change_direction = int(id_str[2])
        value_data = int(id_str[3:])
    else:
        logger.error(f"错误: 效果ID '{effect_id}' 长度不符合已知规则 (8或9位)。")
        return

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"  解析结果: 类型编号={enum_base_value}, 方向={change_direction}, 数值={value_data}")

    # 根据解析结果应用效果
    try:
        effect_type = CenterAttributeEffectType(enum_base_value)
    except ValueError:
        logger.error(f"错误: 未知的效果类型枚举值 '{enum_base_value}'。")
        return

    change_sign = 1 if change_direction == 0 else -1  # 0表示增加，1表示减少

    match effect_type:
        case CenterAttributeEffectType.SmileRateChange:
            # 比率变化按100.00% = 10000计算，所以需要除以10000
            change_amount = value_data / 10000.0
            for card in player_attrs.deck.cards:
                if CheckMultiTarget(target_ids=target, card=card):
                    card.smile *= (1 + change_amount)
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  对满足要求的目标应用效果: Smile值 {action} {change_amount*100:.0f}%")

        case CenterAttributeEffectType.PureRateChange:
            change_amount = value_data / 10000.0
            for card in player_attrs.deck.cards:
                if CheckMultiTarget(target_ids=target, card=card):
                    card.pure *= (1 + change_amount)
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  对满足要求的目标应用效果: Pure值 {action} {change_amount*100:.0f}%")

        case CenterAttributeEffectType.CoolRateChange:
            change_amount = value_data / 10000.0
            for card in player_attrs.deck.cards:
                if CheckMultiTarget(target_ids=target, card=card):
                    card.cool *= (1 + change_amount)
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  对满足要求的目标应用效果: Cool值 {action} {change_amount*100:.0f}%")

        case CenterAttributeEffectType.SmileValueChange:
            # 暂未实装，占位代码
            for card in player_attrs.deck.cards:
                if CheckMultiTarget(target_ids=target, card=card):
                    card.smile += value_data * change_sign
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  对满足要求的目标应用效果: Smile值 {action} {value_data}")

        case CenterAttributeEffectType.PureValueChange:
            # 暂未实装，占位代码
            for card in player_attrs.deck.cards:
                if CheckMultiTarget(target_ids=target, card=card):
                    card.pure += value_data * change_sign
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  对满足要求的目标应用效果: Pure值 {action} {value_data}")

        case CenterAttributeEffectType.CoolValueChange:
            # 暂未实装，占位代码
            for card in player_attrs.deck.cards:
                if CheckMultiTarget(target_ids=target, card=card):
                    card.cool += value_data * change_sign
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  对满足要求的目标应用效果: Cool值 {action} {value_data}")

        case CenterAttributeEffectType.MentalRateChange:
            change_amount = value_data / 10000.0
            for card in player_attrs.deck.cards:
                if CheckMultiTarget(target_ids=target, card=card):
                    card.mental = ceil(card.mental * (1 + change_amount * change_sign))
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  对满足要求的目标应用效果: 血量 {action} {change_amount*100:.0f}%")

        case CenterAttributeEffectType.MentalValueChange:
            for card in player_attrs.deck.cards:
                if CheckMultiTarget(target_ids=target, card=card):
                    card.mental += value_data * change_sign
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  对满足要求的目标应用效果: 血量 {action} {value_data}")

        case CenterAttributeEffectType.ConsumeAPChange:
            for card in player_attrs.deck.cards:
                if CheckMultiTarget(target_ids=target, card=card):
                    card.cost_change(value_data * change_sign)
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  对满足要求的目标应用效果: AP消耗 {action} {value_data}")

        case CenterAttributeEffectType.CoolTimeChange:
            change_amount_seconds = value_data / 100.0
            player_attrs.cooldown += change_amount_seconds * change_sign
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  应用效果: 技能CD {action} {change_amount_seconds:.0f}s")

        case CenterAttributeEffectType.APGainRateChange:
            change_amount = value_data / 100.0
            player_attrs.ap_gain_rate += change_amount * change_sign
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  应用效果: AP Gain Rate {action} {change_amount:.2f}%")

        case CenterAttributeEffectType.VoltageGainRateChange:
            change_amount = value_data / 100.0
            player_attrs.voltage_gain_rate += change_amount * change_sign
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  应用效果: Voltage Gain Rate {action} {change_amount:.2f}%")

        case CenterAttributeEffectType.APRateChangeResetGuard:
            # 暂未实装，占位代码
            change_amount = value_data / 100.0
            player_attrs.ap_rate += change_amount * change_sign
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  应用效果: APRateChangeResetGuard {action} {change_amount:.2f}%")

        case _:
            logger.error(f"  未知效果类型: {effect_type.name} ({enum_base_value})")


class SkillConditionType(Enum):
    """
    技能触发条件类型枚举。
    """
    FeverTime = 1
    VoltageLevel = 2
    MentalRate = 3  # 对应HP百分比
    UsedAllSkillCount = 4  # 合计打出技能次数
    UsedSkillCount = 5  # 单卡打出技能次数


class SkillComparisonOperator(Enum):
    """
    技能条件中的比较运算符。
    """
    UNDEFINED = 0  # 条件不检查数值大小
    ABOVE_OR_EQUAL = 1  # 以上 (>=)
    BELOW_OR_EQUAL = 2  # 以下 (<=)


@lru_cache(maxsize=None)
def parse_condition_id(condition_id: str):
    # 所有条件ID（非0）都是7位数字
    if len(condition_id) != 7:
        logger.error(f"  错误: 条件ID '{condition_id}' 长度不符合已知规则 (应为7位)。 -> 不满足")
        return

    try:
        condition_type = SkillConditionType(int(condition_id[0]))
        operator_or_flag = SkillComparisonOperator(int(condition_id[1]))
        condition_value = int(condition_id[2:])
    except ValueError:
        logger.error(f"  错误: 无法解析条件ID '{condition_id}'。 -> 不满足")
        return

    return condition_type, operator_or_flag, condition_value


def CheckSkillCondition(player_attrs: PlayerAttributes, condition_id: str, card: Card = None) -> bool:
    """
    根据ID检查给定条件是否满足。

    Args:
        player_attrs (PlayerAttributes): 玩家属性实例。
        condition_id (str): 技能条件ID。
        card (Card): 如果条件是 UsedSkillCount，指定要检查的卡牌

    Returns:
        bool: 如果条件满足则返回 True，否则返回 False。
    """

    # 特殊ID "0" 表示无条件，总是满足
    if condition_id == "0":
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("  条件: 无条件 -> 满足")
        return True

    condition_type, operator_or_flag, condition_value = parse_condition_id(condition_id)

    is_satisfied = False

    match condition_type:
        case SkillConditionType.FeverTime:
            is_satisfied = player_attrs.voltage.fever
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  条件: Fever 中 -> {'满足' if is_satisfied else '不满足'}")

        case SkillConditionType.VoltageLevel:
            # 获取 Voltage 对象的当前等级进行比较
            current_level = player_attrs.voltage.level

            if operator_or_flag == SkillComparisonOperator.ABOVE_OR_EQUAL:  # >=
                is_satisfied = (current_level >= condition_value)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: Voltage Lv. >= {condition_value} (当前: Lv.{current_level}) -> {'满足' if is_satisfied else '不满足'}")
            elif operator_or_flag == SkillComparisonOperator.BELOW_OR_EQUAL:  # <
                is_satisfied = (current_level <= condition_value)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: Voltage Lv. <= {condition_value} (当前: Lv.{current_level}) -> {'满足' if is_satisfied else '不满足'}")
            else:
                logger.error(f"  错误: 未知的 VoltageLevel 运算符 '{operator_or_flag}'。 -> 不满足")

        case SkillConditionType.MentalRate:
            # 血量百分比，condition_value 例如 5000 代表 50.00%
            current_value = player_attrs.mental.get_rate()
            required_rate = condition_value / 100.0  # 将5000转换为50.00(%)

            if operator_or_flag == SkillComparisonOperator.ABOVE_OR_EQUAL:  # >=
                is_satisfied = (current_value >= required_rate)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: HP >= {required_rate:.2f}% (当前: {current_value:.2f}%) -> {'满足' if is_satisfied else '不满足'}")
            elif operator_or_flag == SkillComparisonOperator.BELOW_OR_EQUAL:  # <
                is_satisfied = (current_value <= required_rate)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: HP <= {required_rate:.2f}% (当前: {current_value:.2f}%) -> {'满足' if is_satisfied else '不满足'}")
            else:
                logger.error(f"  错误: 未知的 MentalRate 运算符 '{operator_or_flag}'。 -> 不满足")

        case SkillConditionType.UsedAllSkillCount:
            # 合计打出技能次数
            current_value = player_attrs.deck.used_all_skill_calc()

            if operator_or_flag == SkillComparisonOperator.ABOVE_OR_EQUAL:  # >=
                is_satisfied = (current_value >= condition_value)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: 合计技能次数 >= {condition_value} (当前: {current_value}) -> {'满足' if is_satisfied else '不满足'}")
            elif operator_or_flag == SkillComparisonOperator.BELOW_OR_EQUAL:  # <
                is_satisfied = (current_value <= condition_value)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: 合计技能次数 <= {condition_value} (当前: {current_value}) -> {'满足' if is_satisfied else '不满足'}")
            else:
                logger.error(f"  错误: 未知的 UsedAllSkillCount 运算符 '{operator_or_flag}'。 -> 不满足")

        case SkillConditionType.UsedSkillCount:
            # 单卡打出次数
            current_value = card.active_count

            if operator_or_flag == SkillComparisonOperator.ABOVE_OR_EQUAL:  # >=
                is_satisfied = (current_value >= condition_value)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: 卡牌 {card.full_name} 使用次数 >= {condition_value} (当前: {current_value}) -> {'满足' if is_satisfied else '不满足'}")
            elif operator_or_flag == SkillComparisonOperator.BELOW_OR_EQUAL:  # <=
                is_satisfied = (current_value <= condition_value)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: 卡牌 {card.full_name} 使用次数 <= {condition_value} (当前: {current_value}) -> {'满足' if is_satisfied else '不满足'}")
            else:
                logger.error(f"  错误: 未知的 UsedSkillCount 运算符 '{operator_or_flag}'。 -> 不满足")

        case _:
            logger.error(f"  未知条件类型: {condition_type.name} ({condition_id})。 -> 不满足")

    return is_satisfied

def CheckMultiSkillCondition(player_attrs: PlayerAttributes, condition_id: list[str], card: Card = None) -> bool:
    result = all(CheckSkillCondition(player_attrs, condition, card) for condition in condition_id)
    return result

class SkillEffectType(Enum):
    """
    卡牌技能效果类型枚举。
    """
    APChange = 1
    ScoreGain = 2
    VoltagePointChange = 3
    MentalRateChange = 4
    DeckReset = 5
    CardExcept = 6
    NextAPGainRateChange = 7  # 实际效果为NextScoreGainRateChange
    NextVoltageGainRateChange = 8


@lru_cache(maxsize=None)
def parse_effect_id(effect_id: int):
    id_str = str(effect_id)

    if len(id_str) != 9:
        logger.error(f"错误: 效果ID '{effect_id}' 长度不符合已知规则 (应为9位)。")
        return

    try:
        # For rhythm game skills, the EnumBaseValue is always the first digit.
        enum_base_value = int(id_str[0])
        effect_type = SkillEffectType(enum_base_value)
        # The ChangeDirection is always the second digit.
        change_direction = int(id_str[1])
        # 根据 EnumBaseValue 判断是否有 UsageCount
        if effect_type in {SkillEffectType.NextAPGainRateChange,
                           SkillEffectType.NextVoltageGainRateChange}:
            # 对于类型 7 和 8，第三位是作用次数
            usage_count = int(id_str[2])
            value_data = int(id_str[3:])  # ValueData 从第四位开始
        else:
            usage_count = 1
            value_data = int(id_str[2:])
    except ValueError:
        logger.error(f"错误: 无法解析效果ID '{effect_id}' 的类型、方向或数值部分。")
        return

    return effect_type, usage_count, value_data, change_direction


def ApplySkillEffect(player_attrs: PlayerAttributes, effect_id: int, card: Card = None):
    """
    根据EffectID解析并应用技能。

    Args:
        player_attrs (PlayerAttributes): 要修改的玩家属性实例。
        effect_id (int): 技能效果的ID编号。
    """

    effect_type, usage_count, value_data, change_direction = parse_effect_id(effect_id)
    change_factor = 1 if change_direction == 0 else -1

    match effect_type:
        case SkillEffectType.APChange:
            # AP change, value is in 1/10000 units (e.g., 30000 -> 3.0000, 100000 -> 10.0000)
            ap_rate = player_attrs.ap_rate * player_attrs.ap_gain_rate / 100
            if change_factor == 1:
                ap_amount = value_data * change_factor * ap_rate / 10000.0
            else:
                ap_amount = value_data * change_factor / 10000.0
            player_attrs.ap = max(0, player_attrs.ap + ap_amount)
            if logger.isEnabledFor(logging.DEBUG):
                action = "恢复" if change_direction == 0 else "消耗"  # AP is typically recovered
                logger.debug(f"  应用效果: AP {action} {ap_amount:.1f} 点")

        case SkillEffectType.ScoreGain:
            # Direct score gain, value is a percentage (e.g., 122.85% -> 12285). Divide by 100.0
            score_rate = 100
            if player_attrs.next_score_gain_rate:
                score_rate += player_attrs.next_score_gain_rate.pop(0)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"分加成: * {score_rate:.2f}%")
            result = value_data * score_rate / 1000000
            player_attrs.score_add(result)
            if logger.isEnabledFor(logging.DEBUG):
                action = "获得" if change_direction == 0 else "减少"
                logger.debug(f"  应用效果: {action} Appeal值 {value_data / 100:.2f}% 的得分")

        case SkillEffectType.VoltagePointChange:
            # Voltage point change, value is direct points
            voltage_rate = player_attrs.voltage_gain_rate
            if change_factor == 1:
                if player_attrs.next_voltage_gain_rate:
                    voltage_rate += player_attrs.next_voltage_gain_rate.pop(0)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"电加成: * {voltage_rate:.2f}%")
                result = ceil(value_data * voltage_rate / 100)
            else:
                result = -1 * value_data
            player_attrs.voltage.add_points(result)
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  应用效果: Voltage Pt {action} {value_data} 点")

        case SkillEffectType.MentalRateChange:
            # MentalRateChange here is HP change, value is a percentage (e.g., 20.00% -> 2000). Divide by 100.0
            hp_percent = value_data / 100.0
            player_attrs.mental.skill_add(hp_percent * change_factor)
            if logger.isEnabledFor(logging.DEBUG):
                action = "恢复" if change_direction == 0 else "扣除"
                logger.debug(f"  应用效果: HP {action} {hp_percent:.2f}%")

        case SkillEffectType.DeckReset:
            # Deck reset, this is an action, typically no numerical value
            player_attrs.deck.reset()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  应用效果: 重置牌库")

        case SkillEffectType.CardExcept:
            card.is_except = True
            # 模拟器只在重置牌库时检查除外标记
            # 对于LR梢这种先重置牌库再标记除外的卡，就会导致已被除外的LR梢多在牌库里出现一次
            # 因此在触发除外时额外检查牌库中是否有刚被除外的卡，避免未被除外
            for index, deckcard in enumerate(player_attrs.deck.queue):
                if deckcard.is_except:
                    player_attrs.deck.queue.pop(index)
                    break
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  应用效果: 卡牌除外: {card.full_name}")

        case SkillEffectType.NextAPGainRateChange:
            bonus_percent = value_data / 100.0
            for i in range(usage_count):
                if len(player_attrs.next_score_gain_rate) > i:
                    player_attrs.next_score_gain_rate[i] += bonus_percent
                else:
                    player_attrs.next_score_gain_rate.append(bonus_percent)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  应用效果: 分加成 {bonus_percent:.2f}% ({usage_count} 次)")

        case SkillEffectType.NextVoltageGainRateChange:
            bonus_percent = value_data / 100.0
            for i in range(usage_count):
                if len(player_attrs.next_voltage_gain_rate) > i:
                    player_attrs.next_voltage_gain_rate[i] += bonus_percent
                else:
                    player_attrs.next_voltage_gain_rate.append(bonus_percent)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  应用效果: 电加成 {bonus_percent:.2f}% ({usage_count} 次)")

        case _:
            logger.error(f"  未知技能效果类型: {effect_type.name} ({effect_id})")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(player_attrs)


def UseCardSkill(player_attrs: PlayerAttributes, effects: list = None, conditions: list = None, card: Card = None):
    flags = []
    for condition in conditions:
        flags.append(CheckMultiSkillCondition(player_attrs, condition, card))
    for flag, effect in zip(flags, effects):
        if flag:
            ApplySkillEffect(player_attrs, effect, card)


class CenterSkillConditionType(Enum):
    """
    C位技能触发条件类型枚举。
    """
    LiveStart = 1
    LiveEnd = 2
    FeverStart = 3
    FeverTime = 4
    VoltageLevel = 5
    MentalRate = 6
    AfterUsedAllSkillCount = 7
    # 123可单独出现，4暂未出现，567只与3绑定出现


def CheckCenterSkillCondition(player_attrs: PlayerAttributes, condition_id: str, card: Card, event: str = None) -> bool:
    """
    根据ID检查给定条件是否满足。

    Args:
        player_attrs (PlayerAttributes): 玩家属性实例。
        condition_id (int): C位技能条件ID。
        card_id_to_check (int): 如果条件是 UsedSkillCount，指定要检查的卡牌ID。
                                默认为 1001 (用于模拟)。

    Returns:
        bool: 如果条件满足则返回 True，否则返回 False。
    """

    conditions = condition_id.split(",")
    result = True

    for condition_id in conditions:
        # 所有条件ID（非0）都是7位数字
        if len(condition_id) != 7:
            logger.error(f"  错误: 条件ID '{condition_id}' 长度不符合已知规则 (应为7位)。 -> 不满足")
            return False

        try:
            condition_type = CenterSkillConditionType(int(condition_id[0]))
            operator_or_flag = SkillComparisonOperator(int(condition_id[1]))
            condition_value = int(condition_id[2:])
        except ValueError:
            logger.error(f"  错误: 无法解析条件ID '{condition_id}' -> 不满足")
            return False

        is_satisfied = False

        match condition_type:
            case CenterSkillConditionType.LiveStart:
                is_satisfied = (event == "LiveStart")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: Live开始时 -> {'满足' if is_satisfied else '不满足'}")

            case CenterSkillConditionType.LiveEnd:
                is_satisfied = (event == "LiveEnd")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: Live结束时 -> {'满足' if is_satisfied else '不满足'}")

            case CenterSkillConditionType.FeverStart:
                is_satisfied = (event == "FeverStart")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: Fever开始时 -> {'满足' if is_satisfied else '不满足'}")

            case CenterSkillConditionType.FeverTime:
                is_satisfied = player_attrs.voltage.fever
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  条件: Fever Time 中 -> {'满足' if is_satisfied else '不满足'}")

            case CenterSkillConditionType.VoltageLevel:
                current_level = player_attrs.voltage.level

                if operator_or_flag == SkillComparisonOperator.ABOVE_OR_EQUAL:  # >=
                    is_satisfied = (current_level >= condition_value)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"  条件: Voltage Lv. >= {condition_value} (当前: Lv.{current_level}) -> {'满足' if is_satisfied else '不满足'}")
                elif operator_or_flag == SkillComparisonOperator.BELOW_OR_EQUAL:  # <
                    is_satisfied = (current_level <= condition_value)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"  条件: Voltage Lv. <= {condition_value} (当前: Lv.{current_level}) -> {'满足' if is_satisfied else '不满足'}")
                else:
                    logger.error(f"  错误: 未知的 VoltageLevel 运算符 '{condition_id}'。 -> 不满足")

            case CenterSkillConditionType.MentalRate:
                # 血量百分比，condition_value 例如 5000 代表 50.00%
                current_value = player_attrs.mental.get_rate()
                required_rate = condition_value / 100.0  # 将5000转换为50.00%

                if operator_or_flag == SkillComparisonOperator.ABOVE_OR_EQUAL:  # >=
                    is_satisfied = (current_value >= required_rate)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"  条件: HP >= {required_rate:.2f}% (当前: {current_value:.2f}%) -> {'满足' if is_satisfied else '不满足'}")
                elif operator_or_flag == SkillComparisonOperator.BELOW_OR_EQUAL:  # <
                    is_satisfied = (current_value <= required_rate)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"  条件: HP <= {required_rate:.2f}% (当前: {current_value:.2f}%) -> {'满足' if is_satisfied else '不满足'}")
                else:
                    logger.error(f"  错误: 未知的 MentalRate 运算符 '{operator_or_flag}'。 -> 不满足")

            case CenterSkillConditionType.AfterUsedAllSkillCount:
                # 合计打出技能次数
                current_value = player_attrs.deck.used_all_skill_calc()

                if operator_or_flag == SkillComparisonOperator.ABOVE_OR_EQUAL:  # >=
                    is_satisfied = (current_value >= condition_value)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"  条件: 合计技能次数 >= {condition_value} (当前: {current_value}) -> {'满足' if is_satisfied else '不满足'}")
                elif operator_or_flag == SkillComparisonOperator.BELOW_OR_EQUAL:  # <
                    is_satisfied = (current_value <= condition_value)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"  条件: 合计技能次数 <= {condition_value} (当前: {current_value}) -> {'满足' if is_satisfied else '不满足'}")
                else:
                    logger.error(f"  错误: 未知的 UsedAllSkillCount 运算符 '{operator_or_flag}'。 -> 不满足")

            case _:
                logger.error(f"  未知条件类型: {condition_type.name} ({condition_id})。 -> 不满足")
        result = result and is_satisfied

    return result


class CenterSkillEffectType(Enum):
    """
    卡牌C位技能效果类型枚举。
    """
    APChange = 1
    ScoreGain = 2
    VoltagePointChange = 3
    MentalRateChange = 4


def ApplyCenterSkillEffect(player_attrs: PlayerAttributes, effect_id: int):
    """
    根据EffectID解析并应用技能。

    Args:
        player_attrs (PlayerAttributes): 要修改的玩家属性实例。
        effect_id (int): 技能效果的ID编号。
    """

    id_str = str(effect_id)

    # All provided rhythm game skill IDs are 9 digits long.
    # The EnumBaseValue seems to be 1 digit for types 1,2,3,4,5,6,7,8
    # The change direction is *always* the second digit from the left.

    if len(id_str) != 9:
        if logger.isEnabledFor(logging.DEBUG):
            logger.error(f"错误: 效果ID '{effect_id}' 长度不符合已知规则 (应为9位)。")
        return

    try:
        # For rhythm game skills, the EnumBaseValue is always the first digit.
        effect_type = CenterSkillEffectType(int(id_str[0]))
        # The ChangeDirection is always the second digit.
        change_direction = int(id_str[1])
        value_data = int(id_str[2:])
    except ValueError:
        logger.error(f"错误: 无法解析效果ID '{effect_id}' 的类型、方向或数值部分。")
        return

    # 0 indicates an increase/positive effect, 1 indicates a decrease/negative effect
    change_factor = 1 if change_direction == 0 else -1

    match effect_type:
        case CenterSkillEffectType.APChange:
            # AP change, value is in 1/10000 units (e.g., 30000 -> 3.0000, 100000 -> 10.0000)
            ap_rate = player_attrs.ap_rate * player_attrs.ap_gain_rate / 100
            if change_factor == 1:
                ap_amount = value_data * change_factor * ap_rate / 10000.0
            else:
                ap_amount = value_data * change_factor / 10000.0
            player_attrs.ap = max(0, player_attrs.ap + ap_amount)
            if logger.isEnabledFor(logging.DEBUG):
                action = "恢复" if change_direction == 0 else "消耗"  # AP is typically recovered
                logger.debug(f"  应用效果: AP {action} {ap_amount:.1f} 点")

        case CenterSkillEffectType.ScoreGain:
            # Direct score gain, value is a percentage (e.g., 122.85% -> 12285). Divide by 100.0
            score_rate = 100

            if player_attrs.next_score_gain_rate:
                score_rate += player_attrs.next_score_gain_rate.pop(0)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"分加成: * {score_rate:.2f}%")
            result = value_data * score_rate / 1000000
            player_attrs.score_add(result)
            if logger.isEnabledFor(logging.DEBUG):
                action = "获得" if change_direction == 0 else "减少"
                logger.debug(f"  应用效果: {action} Appeal值 {value_data / 100:.2f}% 的分数")

        case CenterSkillEffectType.VoltagePointChange:
            # Voltage point change, value is direct points
            voltage_rate = player_attrs.voltage_gain_rate
            if change_factor == 1:
                if player_attrs.next_voltage_gain_rate:
                    voltage_rate += player_attrs.next_voltage_gain_rate.pop(0)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"电加成: * {voltage_rate:.2f}%")
                result = ceil(value_data * voltage_rate / 100)
            else:
                result = -1 * value_data
            player_attrs.voltage.add_points(result)
            if logger.isEnabledFor(logging.DEBUG):
                action = "增加" if change_direction == 0 else "减少"
                logger.debug(f"  应用效果: Voltage Points {action} {value_data} 点")

        case CenterSkillEffectType.MentalRateChange:
            # MentalRateChange here is HP change, value is a percentage (e.g., 20.00% -> 2000). Divide by 100.0
            hp_percent = value_data / 100.0
            player_attrs.mental.skill_add(hp_percent * change_factor)
            if logger.isEnabledFor(logging.DEBUG):
                action = "恢复" if change_direction == 0 else "扣除"
                logger.debug(f"  应用效果: HP {action} {hp_percent:.2f}%")

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(player_attrs)


if __name__ == "__main__":
    # 实例化玩家属性，用于模拟变化
    player_attrs = PlayerAttributes()
    logger.debug("--- 初始玩家属性 ---")
    logger.debug(player_attrs)
    logger.debug("-" * 20)

    # 模拟应用C位特性效果 (被动技能)
    logger.debug("--- 应用C位特性效果 (被动技能) ---")
    ApplyCenterAttribute(player_attrs, 10020000)  # Smile增加 200.00%
    ApplyCenterAttribute(player_attrs, 91000002)  # AP减费 2费 (即AP增加2)
    logger.debug("-" * 20)

    # 模拟应用卡牌技能效果 (主动技能)
    logger.debug("\n--- 应用卡牌技能效果 (主动技能) ---")
    ApplySkillEffect(player_attrs, 100030000)  # AP恢复 3.0000费
    ApplySkillEffect(player_attrs, 200012285)  # 得分增加 122.85%
    ApplySkillEffect(player_attrs, 300000068)  # 加电 68电
    ApplySkillEffect(player_attrs, 310000050)  # 扣电 50电
    ApplySkillEffect(player_attrs, 400002000)  # 回血 20.00%
    ApplySkillEffect(player_attrs, 410005000)  # 扣血 50.00%
    ApplySkillEffect(player_attrs, 500000000)  # 重置牌库
    ApplySkillEffect(player_attrs, 600000000)  # 卡牌除外
    ApplySkillEffect(player_attrs, 701007962)  # 单次分加成 79.62%
    ApplySkillEffect(player_attrs, 801010237)  # 单次电加成 102.37%

# --- 测试技能触发条件 ---
    logger.debug("\n--- 测试技能触发条件 ---")

    # 无条件
    CheckSkillCondition(player_attrs, 0)

    # FeverTime
    CheckSkillCondition(player_attrs, 1000000)  # 1=Fever中 (True)
    player_attrs.is_in_fever_time = False  # 改变状态
    CheckSkillCondition(player_attrs, 1000000)  # 1=Fever中 (False)
    player_attrs.is_in_fever_time = True  # 恢复状态

    # VoltageLevel
    # 设置一个精确点数来测试等级边界
    player_attrs.voltage.set_points(29)  # 29点，仍在Lv.1
    CheckSkillCondition(player_attrs, 2100001)  # Voltage Lv. >= 1 (True)
    CheckSkillCondition(player_attrs, 2100002)  # Voltage Lv. >= 2 (False, 29 < 30)
    player_attrs.voltage.add_points(1)  # 变成30点，升到Lv.2
    CheckSkillCondition(player_attrs, 2100002)  # Voltage Lv. >= 2 (True)
    CheckSkillCondition(player_attrs, 2200003)  # Voltage Lv. < 3 (True)
    CheckSkillCondition(player_attrs, 2200002)  # Voltage Lv. < 2 (False)

    player_attrs.voltage.set_points(50000)  # 恢复状态，方便测试其他条件

    # MentalRate (HP百分比)
    CheckSkillCondition(player_attrs, 3110000)
    CheckSkillCondition(player_attrs, 3205000)
    player_attrs.current_hp_rate = 40.0
    CheckSkillCondition(player_attrs, 3205000)
    player_attrs.current_hp_rate = 75.0

    # UsedAllSkillCount (合计打出次数)
    CheckSkillCondition(player_attrs, 4100010)
    CheckSkillCondition(player_attrs, 4200006)
    CheckSkillCondition(player_attrs, 4200006)

    # UsedSkillCount (单卡打出次数，假设检查卡牌ID 1001)
    CheckSkillCondition(player_attrs, 5100003, card_id_to_check=1001)
    CheckSkillCondition(player_attrs, 5200002, card_id_to_check=1001)
    # player_attrs.current_card_used_count[1001] = 1
    CheckSkillCondition(player_attrs, 5200002, card_id_to_check=1001)
    # player_attrs.current_card_used_count[1001] = 4

    logger.debug("\n--- 最终玩家属性 ---")
    logger.debug(player_attrs)
