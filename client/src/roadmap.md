一个完整的反应流程应该包括：

输入（来自 `graphic` 游戏画面的点击或来自 `network` 对方的数据包） -> `game` 处理 -> `graphic` 更新画面 -> `network` 传出（如果需要）



### 1. 核心架构 (Core Architecture)

卡牌游戏不仅需要处理图形，还需要管理复杂的规则状态。请避免将所有逻辑写在一个巨大的 `while` 循环中。

#### 推荐架构：状态机 (State Machine)
你需要一个状态管理器来切换游戏的不同阶段（如：菜单、发牌、玩家回合、结算）。

*   **GameState (游戏状态枚举)**: 定义状态，例如 `MENU` (菜单), `DEALING` (发牌中), `PLAYER_TURN` (玩家回合), `ENEMY_TURN` (敌人回合), `ANIMATION_PLAYING` (动画播放中)。
*   **GameManager (游戏管理器)**: 一个持有当前状态并分发事件的类。

#### 类结构设计 (Class Structure)

*   **Card (卡牌精灵)**:
    *   继承自 `pygame.sprite.Sprite`。
    *   **数据**: `suit` (花色), `rank` (点数), `face_up` (是否正面朝上)。
    *   **视觉**: `self.image` (当前纹理), `self.rect` (碰撞箱)。
    *   **层级**: 使用 `layer` 属性。当玩家拖动卡牌时，将其层级调至最高，确保它显示在所有其他卡牌之上 。[10][11]

*   **CardGroup (手牌/牌堆)**:
    *   不要只用普通的列表 (List)。使用自定义容器类来管理逻辑。
    *   **Hand (手牌)**: 自动排列卡牌。当一张卡被添加时，重新计算所有卡牌的 `rect.x` 坐标以呈扇形展开。
    *   **Deck (牌堆)**: 处理洗牌 (`shuffle`) 和抽牌 (`pop`)。

***

### 2. 项目文件结构 (Project File Structure)

建议将“纯逻辑”与“界面代码”完全分开。这意味着 `src/core` 里的代码**绝对不能**包含 `import pygame` 或 `print()`。

```text
my_card_game/
│
├── src/
│   ├── core/                 # 纯逻辑层 (PURE LOGIC)
│   │   ├── __init__.py
│   │   ├── cards.py          # Card 和 Deck 数据类
│   │   ├── player.py         # Player 状态 (手牌, 分数)
│   │   └── game.py           # 游戏核心控制器 (规则裁判)
│   │
│   ├── interfaces/           # 显示层 (DISPLAY LAYERS)
│   │   ├── cli/              # 命令行界面 (用于前期测试逻辑)
│   │   │   ├── __init__.py
│   │   │   └── renderer.py
│   │   └── gui/              # Pygame 图形界面
│   │       ├── __init__.py
│   │       ├── sprites.py    # Pygame Sprite 类
│   │       └── main_pygame.py
│   │
│   └── main.py               # 程序入口
```

***

### 3. 职责划分：谁负责什么？ (Responsibility Separation)

初学者常犯的错误是将“出牌逻辑”写在“玩家类”里。请遵循以下原则：

| 功能场景 | 负责模块 | 示例代码逻辑 |
| :--- | :--- | :--- |
| **Input Handling**<br>(输入处理) | **UI / Main Loop**<br>(界面层) | **"用户点击了第3张牌"**<br>检测鼠标点击，获取卡牌索引，然后调用 GameState。不要在这里判断规则。<br>`if click: game.attempt_play(card_idx)` |
| **Game Logic**<br>(游戏逻辑) | **GameState**<br>(核心层) | **"这张牌能出吗？"**<br>它是裁判。检查费用是否足够？是否轮到该玩家？如果合法，指挥 Player 和 Board 改变状态。<br>`if card.cost <= player.mana: ...` |
| **Data Container**<br>(数据容器) | **Player Class**<br>(数据层) | **"从手中移除这张牌"**<br>它只管自己的数据，不知道游戏规则，也不知道敌人的存在。<br>`self.hand.pop(index)` |

***

### 4. 关键实现细节 (Implementation Details)

#### A. 拖拽与重叠检测 (Z-Index Detection)
在 Pygame 中，当卡牌重叠时，`rect.collidepoint` 可能会同时选中多张牌。
*   **解决方案**: 使用 `get_sprites_at(mouse_pos)`。
*   **逻辑**: 遍历返回的精灵列表，选择 **layer (层级)** 最高或索引最大的那一张 。[12]

#### B. 平滑动画 (Tweening)
不要让卡牌“瞬间移动”。
*   **插值算法**: 给卡牌类添加 `target_pos` (目标坐标)。
*   **更新循环**:
    ```python
    # 简单的缓动效果 (Ease-Out)
    dx = self.target_x - self.rect.x
    dy = self.target_y - self.rect.y
    self.rect.x += dx * 0.2 # 每帧移动剩下距离的 20%
    self.rect.y += dy * 0.2
    ```

#### C. 开发工作流 (Workflow)
1.  先写 **src/core/game.py**，实现 `check_win_condition()` (胜利条件检测) 等纯逻辑。
2.  使用 **命令行 (CLI)** 测试这些逻辑，确保发牌、出牌、回合切换没有 Bug。
3.  逻辑跑通后，再编写 Pygame 界面，将 `print()` 替换为 `screen.blit()`。

---

Network todo:

把主机（被连接）作为 `server`，客机（连接）作为 `client`。

1. 客户端之间建立连接；结束时断开
    
    仅 `network`

2. 同步开始游戏进程；
    
    `server` 端的 `game` 开始游戏 -> 由 `server` 端 `network` 唤起 `client` 端的 `game` 开始游戏并接受初始状态

3. 游戏过程中传递游戏事件信息

    `game` 调用 `network` 发出信息

4. 收到事件信息之后正确调用游戏函数

    `network` 接受信息 -> `game` 处理


数据包格式：

```json
[
    "event" = event, // 事件类型
    "card" = card,  // 卡牌，如果不涉及就留空（给出空卡牌）
    "param" = param, // 参数，如果不涉及（ry
    "player" = player // 玩家，(ry
]
```




---
开始界面

选择主机/客机

`network` 选择怎么实例化（init参数：self, 主机/客机，ip，端口）

先init 然后再调用 start()/connect()

`game` 把这两个接起来

`UI` 选择怎么实例化 network 的界面

由 `UI` 输入信息后调用 `initNetwork(self, is_host, ip, port)` -> 调用 Network 构造函数并进行初始化


进入游戏

`network` 通过 send() 发送 json 格式的数据包来进行端对端的信息传递

--- 
一直存在的

胜负判定 game -> ui

game 调用 UI 侧：`drawGameEnd(stat)`
stat : win/lose，绘制对应的结束画面；

角色状态，资源状态 game -> ui

ui 调用 game 中 Player 的 `getT()` 来获取信息，其中 T 是需要被绘制的目标信息，包括

- 自己手牌具体内容
- 双方生命值
- 双方 cost
- 双方 手牌数量

手牌 game -> ui 同上

出牌后的状态处理（胜负判定等） game -> ui

game 调用 ui 的 `updateGameBoard()` 以重绘游戏版面

自己回合的

出牌 ui -> game -> network发包

ui 获取手牌；具体知道选择第几张手牌时调用

game：`playCard(id)`

做牌 game (生成可选词条) -> ui (返回操作结果) -> game -> network发包

ui 有一个回合结束按钮；按下后触发 game 的 `turnEnd()` 机制；

在 `turnEnd()` 中：

- 由 game 生成若干个词条用于挑选，并调用 ui 中 `drawCardSelection()` 来绘制选择做牌的画面；
- ui 获取最终的选择结果作为函数返回值返回，由 game 调用 network 发包

对手回合的

对手出牌 network -> （出牌状态处理） -> `updateGameBoard()`

对手结束回合 network -> game -> ui

- game 调用 ui 中 `drawGivenCard(Card)` 来展示从对手获得的牌；
- game 调用 ui : `drawTurnStart()`

