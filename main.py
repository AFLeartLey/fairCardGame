import random

# 基础配置
MAX_HP = 20

# 词条库
good_effects = ["抽卡", "造成伤害", "回复血量"]
bad_effects = ["对自己造成伤害", "弃牌", "减少下回合抽卡数"]

# 倍率组定义（倍率: 数值范围）
multipliers = {
    "小": (1, 3),
    "中": (3, 5),
    "大": (5, 7)
}

class Card:
    def __init__(self, good, bad, multiplier_name, multiplier_value):
        self.good = good
        self.bad = bad
        self.multiplier_name = multiplier_name
        self.multiplier_value = multiplier_value

    def __str__(self):
        return f"[好:{self.good}+{self.multiplier_value} | 坏:{self.bad}+{self.multiplier_value}]"

class Player:
    def __init__(self, name, is_human=True):
        self.name = name
        self.hp = MAX_HP
        self.hand = []
        self.is_human = is_human

    def draw_card(self, card):
        self.hand.append(card)

    def play_card(self):
        if not self.hand:
            print(f"{self.name} 没有牌可以打。")
            return None
        card = self.hand[0]
        if not self.is_human:
            card = random.choice(self.hand)
        else:
            for i, card in enumerate(self.hand):
                print(f"{i}: {card}")
            while True:
                try:
                    choice = int(input(f"{self.name} 选择出牌。"))
                    if 0 <= choice < len(self.hand):
                        card = self.hand[choice]
                        break
                    else:
                        print("无效编号，请重新输入")
                except ValueError:
                    print("请输入数字编号")
        self.hand.remove(card)
        print(f"{self.name} 打出了 {card}")
        return card

    def generate_card_for_enemy(self):
        # 候选三张牌
        candidates = []
        for _ in range(3):
            good = random.choice(good_effects)
            bad = random.choice(bad_effects)
            multiplier_name, (low, high) = random.choice(list(multipliers.items()))
            multiplier_value = random.randint(low, high)
            candidates.append(Card(good, bad, multiplier_name, multiplier_value))

        # 玩家手动选择 / 敌人自动选择
        if self.is_human:
            print(f"{self.name} 生成卡牌候选：")
            for i, c in enumerate(candidates):
                print(f"{i+1}: {c}")
            choice = int(input(f"{self.name} 选择一个卡牌编号送给对方：")) - 1
            return candidates[choice]
        else:
            choice = random.choice(candidates)
            print(f"{self.name} 随机选择了一张牌送给对方：{choice}")
            return choice

def apply_card_effects(player, enemy, card):
    # 处理好词条
    if "造成伤害" in card.good:
        enemy.hp -= card.multiplier_value
    if "回复血量" in card.good:
        player.hp = min(MAX_HP, player.hp + card.multiplier_value)
    if "抽卡" in card.good:
        # 抽卡时由敌人生成
        new_card = enemy.generate_card_for_enemy()
        player.draw_card(new_card)
        print(f"{player.name} 抽到了一张牌：{new_card}")

    # 处理坏词条
    if "对自己造成伤害" in card.bad:
        player.hp -= card.multiplier_value
    if "弃牌" in card.bad and player.hand:
        discarded = random.choice(player.hand)
        player.hand.remove(discarded)
        print(f"{player.name} 被迫弃掉了 {discarded}")
    if "减少下回合抽卡数" in card.bad:
        print(f"{player.name} 下回合的抽卡数将减少（暂未实现具体逻辑）")

def game_round(player, enemy):
    print(f"\n---- {player.name} 的回合开始 ----")

    # 出牌
    card = player.play_card()
    if card:
        apply_card_effects(player, enemy, card)

    # 回合结束 -> 生成一张牌送给敌人
    new_card = player.generate_card_for_enemy()
    enemy.draw_card(new_card)
    print(f"{player.name} 为 {enemy.name} 打造了一张牌：{new_card}")

    # 状态展示
    print(f"{player.name} HP: {player.hp}, 手牌数: {len(player.hand)}")
    print(f"{enemy.name} HP: {enemy.hp}, 手牌数: {len(enemy.hand)}")

def main():
    p1 = Player("玩家", is_human=True)
    p2 = Player("敌人", is_human=False)

    # 开始时各抽三张牌（互相生成）
    for _ in range(3):
        p1.draw_card(p2.generate_card_for_enemy())
        p2.draw_card(p2.generate_card_for_enemy())

    # 回合循环
    while p1.hp > 0 and p2.hp > 0:
        game_round(p1, p2)
        if p2.hp <= 0:
            print("敌人被击败！玩家胜利！")
            break
        game_round(p2, p1)
        if p1.hp <= 0:
            print("玩家被击败！敌人胜利！")
            break

if __name__ == "__main__":
    main()
