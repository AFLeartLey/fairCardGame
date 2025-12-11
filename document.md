1. src/game/card.py  
   class Card

1.1 `__init__(self, item_power: int, pcarditem_type: str, ncarditem_type: str, card_effect: str) -> None`
用处：  
  把一张牌的所有“静态数值”一次性打包成只读对象，后续任何模块想判断牌面内容都调 getter，避免魔法字符串满天飞。  

参数意义：  
  - item_power：1~3 的整数，代表“强度档位”，对应 constants.py 里 CARD_ITEM_VALUES 的二级键。  
  - pcarditem_type：正面词条字符串，必须是 constants.PCARDITEMLIST 里的常量，如 "heal"/"damage"/"card_draw"/"cost_recover"。  
  - ncarditem_type：负面词条字符串，必须是 constants.NCARDITEMLIST 里的常量，如 "self_damage"/"card_discard"/"cost_usage"；可以为 "" 表示无负面。  
  - card_effect：状态字串，目前只留占位，填 constants.STATUS_CARD_NO_EFFECT 即可，将来做 Buff 系统再扩展。  

返回值：无（构造函数）。  

使用细节：  
  对象一旦生成，四个字段就不再变化；外部不要直接访问成员，统一走 getter，方便以后把成员改成 property 或加校验。

示例：  
```python
from src.game.card import Card
from src.game.constants import STATUS_CARD_NO_EFFECT
card = Card(2, "damage", "self_damage", STATUS_CARD_NO_EFFECT)
# 一张 Lv2 的“打对方 3 点但自己掉 2 点”的牌
```

---

1.2 `getNcarditem(self) -> str`
用处：返回负面词条，供 `match` 或 `if` 做分支。  
参数：无。  
返回值：构造时填的 ncarditem_type。  
细节：纯函数，无副作用。

1.3 `getPcarditem(self) -> str`
同上，对应正面词条。

1.4 `getItemPower(self) -> int`
同上，对应强度 1~3。

1.5 `getCardEffect(self) -> str`
同上，对应状态字；目前未参与计算，可留空。

---

2. src/game/player.py  
   class Player

2.1 `__init__(self) -> None`
用处：  
  生成一个“干净”玩家对象，供 GameState 持有；所有状态字段集中初始化，避免外部漏赋初值。  

参数：无。  
返回值：无。  

细节：  
  health  = PLAYER_MAX_HEALTH (25)  
  cost    = PLAYER_INIT_COST   (4)  
  hand    = []  
  后续任何修改都通过成员函数，方便加日志/断言。

---

2.2 `takeDamage(self, damage: int) -> None`
用处：  
  统一入口扣血，保证不会出现负数 HP。  

参数：  
  damage：非负整数，表示要扣除的生命值。  

返回值：无。  

细节：  
  self.health -= damage  
  if self.health < 0: self.health = 0  
  不抛异常，调用后如需判断死亡请再调 isDefeated()。

---

2.3 `takeHeal(self, heal: int) -> None`
用处：统一入口加血，封顶 MAX_HEALTH。  
参数：heal 非负。  
返回值：无。  
细节：超过上限直接截断，不会溢出。

---

2.4 `isDefeated(self) -> bool`
用处：快速判断角色是否已阵亡，供 GameState 每帧检查。  
参数：无。  
返回值：HP≤0 返回 True，否则 False。  
细节：只读，不修改任何字段。

---

2.5 `costUsage(self, cost: int) -> bool`
用处：  
  “支付费用”的唯一入口，避免外部直接修改 self.cost 导致负值。  

参数：  
  cost：要扣除的费用点数，必须 ≥0。  

返回值：  
  余额足够 → 真，同时立即扣费；  
  不足     → 假，不触动原值。  

细节：  
  常用于出牌前判断：  
  ```python
  if player.costUsage(card_cost):
      ...  # 真正打出
  ```

---

2.6 `costRegen(self, regen: int) -> None`
用处：统一回费，封顶 PLAYER_COST_LIMIT。  
参数：regen 非负。  
返回值：无。  
细节：常用于回合结束或卡牌效果“回复 2 费”。

---

2.7 `receiveCard(self, card: Card) -> bool`
用处：  
  抽牌/得牌的唯一入口，自动检测手牌上限，防止爆牌。  

参数：  
  card：Card 实例，允许是临时生成的随机牌。  

返回值：  
  手牌 < MAX_HAND_SIZE → 真，追加到 self.hand 尾部；  
  否则 → 假，不追加，由 UI 决定是弃掉还是动画丢弃。  

细节：  
  函数本身不做动画，只返回布尔标志。

---

2.8 `discardCard(self, card: Card) -> bool`
用处：  
  需要弃牌时（如负面效果“弃 2 张”）的统一入口。  

参数：  
  card：要弃的那张 Card 对象；按 == 比较，只删第一张匹配。  

返回值：  
  找到并移除 → 真；  
  未找到     → 假（通常说明逻辑错误）。  

细节：  
  不会触发任何动画；UI 层可在返回真后播放丢弃特效。

---

3. src/game/process.py  
   class GameState

3.1 `__init__(self, local_player: Player, remote_player: Player, NetworkManager: Network) -> None`
用处：  
  把“两个玩家 + 网络句柄”捆成一份上下文，供整局游戏反复读写；所有游戏规则都通过该类的成员函数落地。  

参数：  
  local_player：代表“我”的玩家对象，UI 只读它的状态。  
  remote_player：代表“对手”的玩家对象，UI 只读它的数量类信息（手牌数、HP、Cost）。  
  NetworkManager：已创建但尚未连接/启动的 Network 实例；GameState 会在 initNetwork 里再真正启动它。  

返回值：无。  

细节：  
  此时不立即开线程，UI 可先绑定回调，再调用 initNetwork。

---

3.2 一组 Getter（getLocalHand / getRemoteHandSize / getLocalHealth / getRemoteHealth / getLocalCost / getRemoteCost）
用处：  
  把内部 Player 对象的字段包装成只读快照，防止外部意外修改；UI 每帧刷新时高频调用。  

参数：全部无参。  
返回值：对应字段的副本或长度。  

细节：  
  - getLocalHand 返回 `list[Card]` 引用，外部只读即可；若必须修改请先拷贝。  
  - 其余都是不可变数值，直接显示。

---

3.3 `initNetwork(self, is_host: bool, ip: str, port: int) -> None`
用处：  
  一次性完成“监听 or 连接 + 注册回调 + 启动后台线程”，让 GameState 开始能收发网络消息。  

参数：  
  is_host：True 表示做房主，会 bind 并 listen；False 表示做客户端，会 connect。  
  ip：对于 Host 是本地绑定地址，通常 "0.0.0.0"；对于 Client 是目标主机地址。  
  port：TCP 端口，两端必须一致。  

返回值：无。  

细节：  
  - 内部把 `self.NetworkManager.on_message` 指向 `self.handle_network_message`；  
  - 异常（端口被占、连接超时）会 print 但不会向上抛，业务层若需要重试请自行 try/except 包一层。

---

3.4 `closeNetwork(self) -> None`
用处：  
  房间解散、返回主菜单、断线重连前调用；幂等安全，可多次调用。  

参数：无。  
返回值：无。  

细节：  
  会关闭所有 socket、清理心跳线程、取消未完成的 RPC Future；UI 应在调用后把“开始游戏”按钮置灰。

---

3.5 `sendData(self, data: dict) -> None`
用处：  
  高层业务想发任意事件（如自定义动画、表情）时，直接塞字典即可；无需关心 Host 广播还是 Client 单播。  

参数：  
  data：任何可 JSON 序列化的字典，必须带 `"type"` 字段方便对端分发。  

返回值：无。  

细节：  
  - Host 若给 `to_socket` 传值则单播，否则广播；  
  - Client 的 `to_socket` 必须留空；  
  - 发送失败自动移除对端，业务层无感知。

---

3.6 `handle_network_message(self, msg: dict) -> None`
用处：  
  网络层收到一条完整 JSON 后，先给 GameState 做内部处理（如 RPC、心跳），再转发业务事件；集中处理避免 UI 写一堆 if/elif。  

参数：  
  msg：已反序列化的字典，一定含 `"type"`。  

返回值：无。  

细节：  
  目前硬编码分支：  
  - `"game_start"` → 调 `on_game_start_callback`  
  - `"card_played"` → 调 `parseRemotePlayedCard`  
  - `"turn_end"` → 预留，未实现  
  新增事件请继续扩分支。

---

3.7 `checkGameOver(self) -> str | None`
用处：  
  每帧或每次状态变动后调用，决定要不要切到结算页面。  

参数：无。  
返回值：  
  `"local"`  表示 local_player 胜利（remote_player 阵亡）；  
  `"remote"` 表示 remote_player 胜利（local_player 阵亡）；  
  `None`     游戏继续。  

细节：  
  只读两个 Player.health，无副作用；UI 得到非空值后即可跳 `EndPage`。

---

3.8 `get_ui_state(self) -> dict`
用处：  
  一次性打包所有需要显示的数据，避免 UI 层多次跨模块调用。  

参数：无。  
返回值：预定结构  
```python
{
  "player_status": {
      "self":   {"hp": int, "hand_count": int, "cost": int, "hand_cards": list[str]},
      "opponent": {"hp": int, "hand_count": int, "cost": int}
  }
}
```
细节：  
  hand_cards 是字符串列表，已格式化好可直接当按钮文字；格式在 `_card_to_str` 里写死，可随意改。

---

3.9 `checkCardPlayable(self, targetCard: Card) -> bool`
用处：  
  UI 高亮/灰化手牌按钮时，只判断“资源够不够支付负面成本”，不检查索引。  

参数：  
  targetCard：要打出的那张牌对象。  

返回值：  
  当前 local_player 的资源 ≥ 负面需求 → 真；否则假。  

细节：  
  对于 `"self_damage"` 会看 HP；  
  对于 `"card_discard"` 会看手牌数；  
  对于 `"cost_usage"` 会看费用；  
  无负面或等级为 0 的词条始终返回真。

---

3.10 `playCard(self, card_index: int) -> bool`
用处：  
  本地玩家试图打出第 idx 张牌的全部业务流程：合法性 → 负面效果 → 网络广播 → 正面效果 → 移除手牌。  

参数：  
  card_index：手牌列表下标，必须 ≥0 且 < len(hand)。  

返回值：  
  成功走完所有步骤 → 真；  
  任何一步失败（越界/不可支付）→ 假，且状态回滚到调用前。  

细节：  
  - 函数内部先调 `checkCardPlayable`；  
  - 负面效果立即生效（掉血/弃牌/扣费）；  
  - 通过 `Network.send({"type":EVENT_CARD_PLAYED, "card":card})` 广播给对手；  
  - 正面效果（伤害/治疗/抽牌/回费）再生效；  
  - 最后 `self.local_player.hand.pop(card_index)`。  
  因此调用成功后 UI 必须立即刷新，否则显示会少一张牌。

---

3.11 `parseRemotePlayedCard(self, card: Card) -> None`
用处：  
  当网络层收到对手出牌事件时，自动把这张牌的效果在“本地视角”重放一遍：给对手加血/自己掉血/对手回费 等。  

参数：  
  card：对手打出的那张牌对象（已反序列化）。  

返回值：无。  

细节：  
  逻辑与 `playCard` 的“效果部分”镜像对称：  
  - 负面效果作用在 **remote_player**；  
  - 正面效果作用在 **local_player**（例如对手打伤害牌，你就掉血）。  
  函数末尾无需移除手牌，因为对手自己会维护它的手牌列表。

---

3.12 `turnEnd(self) -> None`
用处：  
  本地玩家点击“结束回合”后触发：回费、抽牌、通知对手“我回合结束”。  

参数：无。  
返回值：无。  

细节：  
  - 回费 +2（可改 constants）；  
  - 随机生成 3 张牌，默认取第 0 张加入自己手牌（UI 选牌逻辑留空）；  
  - 发送 `EVENT_TURN_END` 给对手，附带“我抽的这张牌”数据，方便对手 UI 做动画；  
  - 函数不处理“回合开始”阶段，因为开始阶段由对手发来的 `EVENT_TURN_END` 驱动。

---

4. src/network/utils.py

4.1 `pack(data: dict) -> bytes`
用处：把业务字典变成带分隔符的网络报文，确保一对消息一次 `recv` 就能切分。  
参数：任意可 JSON 序列化的字典。  
返回值：UTF-8 编码的字节流，末尾强制加 `\n`。  
细节：`ensure_ascii=False` 支持中文；`\n` 是 Network 层切分依据，不要去掉。

4.2 `unpack(raw: str) -> dict`
用处：对端收到字节后 `decode -> split('\n') -> unpack(line)` 得到字典。  
参数：单条完整字符串（不含 `\n`）。  
返回值：字典；若 JSON 非法抛 `json.JSONDecodeError`。  
细节：网络层已 try/except 打印，业务层一般不用直接调。

---

5. src/network/core.py  
   class Network

5.1 `__init__(self, is_host: bool = False, host_ip: str = "0.0.0.0", port: int = 5555) -> None`
用处：生成一个“既可当 Host 也可当 Client”的双模对象，后续统一用 `send`/`request` 通信。  
参数：  
  - is_host：True 表示将来调 `start()` 做监听；False 表示将来调 `connect()` 做客户端。  
  - host_ip：对于 Host 是绑定地址；对于 Client 是目标地址（可在 `connect` 时再次覆盖）。  
  - port：TCP 端口，两端必须一致。  
返回值：无。  
细节：此时不占用任何端口，仅保存配置；所有回调属性初始为 None。

---

5.2 `start(self) -> None`
用处：Host 角色开始监听，进入可接受客户端连接状态。  
参数：无。  
返回值：无。  
细节：  
  - 内部 bind → listen → spawn 接收线程 & 心跳线程；  
  - 端口被占用或权限不足抛 `NetError`；  
  - 成功后 `self.is_connected` 置 True，并触发 `on_connected` 回调。

---

5.3 `connect(self, target_ip: str = "127.0.0.1") -> None`
用处：Client 角色向远端发起 TCP 连接。  
参数：target_ip 为 Host 的 IPv4 地址。  
返回值：无。  
细节：  
  - 10 s 连接超时，失败抛 `NetError`；  
  - 成功后启动接收线程 & 心跳线程，并触发 `on_connected`。

---

5.4 `close(self) -> None`
用处：优雅关闭，释放所有线程与 socket；支持重复调用。  
参数：无。  
返回值：无。  
细节：  
  - 先 shutdown 再 close，防止 TIME_WAIT 堆积；  
  - 取消所有 pending 的 RPC Future，防止客户端永远阻塞；  
  - 线程安全，可在 UI 主线程直接调用。

---

5.5 `send(self, data: dict, to_socket: socket.socket | None = None) -> None`
用处：高层业务想发消息时，一句话搞定，无需关心自己是 Host 还是 Client。  
参数：  
  - data：必须含 `"type"` 字段，供对端分发；其余字段随意。  
  - to_socket：Host 单播时指定客户端 socket；Client 必须留 None。  
返回值：无。  
细节：  
  - 内部自动 `pack`；发送异常会移除失效对端，业务层无感知。

---

5.6 `request(self, data: dict, timeout: float | None = None, request_type: str = "rpc_request", send_request: bool = True, to_socket: socket.socket | None = None) -> dict`
用处：同步 RPC 调用，像写本地函数一样写网络请求。  
参数：  
  - data：业务负载字典，会原样传给远端 handler。  
  - timeout：秒；None 表示用实例默认值（5 s）。  
  - request_type：与远端 `register_handler` 的键对应。  
  - send_request：内部调试用，正常保持 True。  
  - to_socket：Host 多客户端时必须指定；Client 留 None。  
返回值：远端 handler 返回的字典；若对端抛异常，则收到 `{"status":"error", "error":"..."}`。  
细节：  
  - 内部生成 uuid 作为 `request_id`，阻塞等待响应；  
  - 超时抛 `TimeoutError`；网络断开抛 `NetError`；  
  - 函数线程安全，可在 UI 线程直接调用（但建议放后台线程，防止界面卡死）。

---

5.7 `request_to_peer(self, data: dict, peer_index: int = 0, timeout: float | None = None, request_type: str = "rpc_request") -> dict`
用处：Host 端想对第 N 个客户端发 RPC 的快捷封装，避免自己维护 socket 列表。  
参数：  
  - data / timeout / request_type：同 `request`。  
  - peer_index：在 `self._peers` 列表中的下标，从 0 开始。  
返回值：同 `request`。  
细节：  
  - 若索引越界抛 `ValueError`；  
  - 内部转调 `request(..., to_socket=peers[peer_index])`。

---

5.8 `register_handler(self, request_type: str, handler: Callable[[dict], dict]) -> None`
用处：给远端提供“远程函数”，实现双向 RPC。  
参数：  
  - request_type：字符串键，如 `"add"`、`"fetch_card"`。  
  - handler：签名为 `dict -> dict`；若 handler 抛异常，框架自动回包 `{"status":"error", "error":str}`。  
返回值：无。  
细节：  
  - 重复注册会覆盖旧 handler；  
  - handler 里可以访问全局变量、数据库，甚至再调反向 RPC，形成链式调用。

---

5.9 `set_default_timeout(self, timeout: float) -> None`
用处：全局调整 RPC 默认超时，避免每次 request 都写秒数。  
参数：timeout > 0 的秒数。  
返回值：无。  
细节：只影响后续未显式传 timeout 的 request。

---

5.10 `get_peer_count(self) -> int`
用处：Host 想知道当前有几个人坐在房间里，方便“满 3 人再开始”之类的逻辑。  
参数：无。  
返回值：已连接客户端数量。  
细节：Client 调用会抛 `NetError`；返回值为 0 表示人已走光，可做自动返回大厅逻辑。

---

6. client/UI.py  
   由于 UI 类方法较多，按类继续逐函数说明。

6.1 MainApp

6.1.1 `setState(self, game_state: GameState) -> None`
用处：  
  把后端 GameState 实例注入到 UI，同时把网络回调（游戏开始、连接成功、客户端加入）绑定到 UI 方法，实现“后台线程驱动界面”的安全切换。  

参数：  
  game_state：已创建但未开始网络的 GameState 对象。  

返回值：无。  

细节：  
  - 必须在 `show_frame` 前调用，否则回调为空；  
  - 内部用 `after(0, ...)` 保证 UI 切换发生在主线程。

示例：  
```python
app = MainApp()
gs = GameState(local, remote, Network())
app.setState(gs)  # 先绑定
app.mainloop()
```

---

6.1.2 `connect_or_create(self, ip: str, port: int, action: Literal["create", "join"]) -> None`
用处：  
  界面点击“创建房间/加入房间”后，真正调用 `GameState.initNetwork`；失败弹窗，成功更新 StartPage 标签。  

参数：  
  ip：IPv4 字符串，如 "127.0.0.1"。  
  port：端口字符串（内部转 int）。  
  action："create" 做 Host；"join" 做 Client。  

返回值：无。  

细节：  
  - 端口转 int 失败或网络异常会弹 `messagebox.showerror`；  
  - Host 成功后 StartPage 会显示“等待玩家加入”并点亮“开始游戏”；  
  - Client 成功后显示“已加入，等待房主开始”，且“开始游戏”按钮保持禁用。

---

6.1.3 `start_game(self) -> None`
用处：  
  房主点击“开始游戏”后，发送 game_start 事件并切换到 GamePage；客户端虽无按钮，但收到网络通知也会走到同一套逻辑。  

参数：无。  
返回值：无。  

细节：  
  - 内部检查 `NetworkManager.is_connected`；  
  - Host 会广播 `{"type":"game_start"}`；  
  - 然后调 `_do_start_game()` 切界面并刷新状态。

---

6.1.4 `show_frame(self, page_name: str) -> None`
用处：  
  通用页面路由器，三行代码实现 Tk 多页面切换。  

参数：  
  page_name：字符串，必须是 "StartPage"、"GamePage"、"EndPage" 之一。  

返回值：无。  

细节：  
  内部用 `frame.tkraise()`；不会重新构造对象，页面实例一直存在。

---

6.1.5 `_do_start_game(self) -> None`
用处：  
  把“真正开始游戏”的公共逻辑抽出来，既给按钮调用，也给网络回调调用，保证单入口。  

参数：无。  
返回值：无。  

细节：  
  - 切到 GamePage；  
  - 调 `GameState.get_ui_state()` 刷新双方血条、手牌、Cost；  
  - 调 `GamePage.DrawTurnStart()` 播放 1.5 s 横幅；  
  - 通过 `after(0, ...)` 保证运行在主线程。

---

6.2 StartPage

6.2.1 `update_room_status(self, status_message: str, enable_start: bool = False) -> None`
用处：  
  动态更新底部状态文字，并控制“开始游戏”按钮是否可点；支持后台线程安全调用。  

参数：  
  status_message：任意描述文字，如“客户端已连接，准备开始”。  
  enable_start：真 → 按钮变绿可点；假 → 灰色禁用。  

返回值：无。  

细节：  
  内部用 `self.after(0, lambda: ...)` 转发到主线程，避免网络线程直接改 UI。

---

6.3 GamePage

6.3.1 `StatusUpdate(self, game_data: dict) -> None`
用处：  
  后端每次状态变化（出牌、掉血、抽牌）后，一次性刷新整个界面，避免多次跨模块调用。  

参数：  
  game_data：必须含 `player_status.self / opponent` 字段，结构与 `GameState.get_ui_state()` 完全一致。  

返回值：无。  

细节：  
  会先更新顶部标签（HP、手牌数、Cost），再调 `update_hand_display` 重绘手牌按钮；调用开销极低，可每帧执行。

---

6.3.2 `update_hand_display(self, hand_cards: list[str]) -> None`
用处：  
  根据后端给来的字符串列表，重新绘制手牌按钮行；支持动态增减牌。  

参数：  
  hand_cards：每张牌的展示文本，如 `["heal | self_damage (Lv2)", ...]`。  

返回值：无。  

细节：  
  - 先销毁旧按钮列表，再按顺序新建；  
  - 选中状态会被清空；  
  - 按钮宽度固定，窗口太窄时会自动换行（Tk Frame 特性）。

---

6.3.3 `DrawTurnStart(self) -> None`
用处：  
  在界面中央显示大字号“己方回合开始！”1.5 秒后自动消失，提供视觉反馈。  

参数：无。  
返回值：无。  

细节：  
  内部用 `after(1500, lambda: self.turn_message_var.set(""))` 自动清空，无需手动清理。

---

6.3.4 `DrawTurnEnd(self) -> None`
同上，文字换成“回合结束！”。

---

6.3.5 `card_click(self, index: int) -> None`
用处：  
  实现“第一次点击选中，再点击同一张打出”的交互；选中时有视觉凹陷+变黄。  

参数：  
  index：手牌按钮下标，与 hand_cards 列表对应。  

返回值：无。  

细节：  
  - 用 `self.selected_card_index` 记录选中状态；  
  - 如果第二次点同一张 → 直接调 `play_card(index)`；  
  - 如果点不同张 → 切换选中，不打出。

---

6.3.6 `play_card(self, index: int) -> None`
用处：  
  真正执行“打出一张牌”的业务：调后端 → 成功刷新界面 → 清除选中状态；失败弹 warning。  

参数：  
  index：手牌下标。  

返回值：无。  

细节：  
  - 内部调 `GameState.playCard(index)`；  
  - 失败原因会在 `messagebox.showwarning` 里显示（越界/费用不足/前提不符）；  
  - 成功后清除按钮凹陷与黄色背景。

---

6.3.7 `end_turn_click(self) -> None`
用处：  
  玩家点“结束回合”按钮的入口；会立即显示横幅，2 秒后弹出 3 选 1 递牌窗口。  

参数：无。  
返回值：无。  

细节：  
  - 先调 `DrawTurnEnd()`；  
  - 然后 `after(2000, ...)` 弹出模态窗口；目前写死假数据 `["Card X", "Card Y", "Card Z"]`，后续应把后端随机生成的 3 张牌传进来。

---

6.3.8 `show_draw_choice(self, three_cards_data: list[str]) -> None`
用处：  
  回合结束时，弹出三选一窗口，让玩家选一张递给对手；窗口关闭前主界面被 grab 锁定。  

参数：  
 three_cards_data：三张牌的展示文本，长度必须 =3。  

返回值：无。  

细节：  
  - 模态窗口顶部提示“请选择一张递给对手”；  
  - 按钮横向排列；  
  - 点击任意一张后调 `draw_card_select(index, ...)`。

---

6.3.9 `draw_card_select(self, index: int, three_cards_data: list[str]) -> None`
用处：  
  玩家在三选一窗口里点选后，记录选择、关闭窗口，并提示“你选择了 XXX 给对手”。  

参数：  
  index：选中的下标（0~2）。  
  three_cards_data：同展示列表，用于取文字做提示。  

返回值：无。  

细节：  
  - 关闭模态窗口后，主界面解锁；  
  - **网络发送代码目前留空**，需要开发者在这里补 `Network.send({"type":"give_card", "card": ...})`。

---

6.3.10 `DrawACard(self) -> None`
用处：  
  后端抽牌后，通知 UI 刷新手牌显示；单独抽离是为了支持“异步抽牌”动画。  

参数：无。  
返回值：无。  

细节：  
  内部只做 `StatusUpdate(gs.get_ui_state())`；可扩展成先播放抽牌动画再刷新。

---

6.4 EndPage

6.4.1 `GameOver(self, is_winner: bool) -> None`
用处：  
  后端检测到游戏结束时调用，显示大字号胜利/失败横幅。  

参数：  
  is_winner：True 显示绿色“YOU WIN”，False 显示红色“YOU LOSE”。  

返回值：无。  

细节：  
  - 文字用 48 号粗体；  
  - 2 秒后可通过“再来一局”按钮返回主菜单。

---

6.4.2 `restart_game(self) -> None`
用处：  
  玩家点击“再来一局”后，返回 StartPage 并重置房间状态。  

参数：无。  
返回值：无。  

细节：  
  - 内部调 `show_frame("StartPage")`；  
  - 需要开发者补充：关闭旧 Network、释放 GameState、创建新实例再 `setState()`。

---

7. 小结速查（给开发者贴墙）
- 任何“状态修改”都走 GameState，UI 只读快照。  
- 任何“网络发送”都走 Network.send / request，业务层不直接操作 socket。  
- UI 回调里若需要长时间阻塞（如 RPC）请用线程，主线程只负责 Tk 刷新。  
- 新增事件常量先在 constants.py 加字符串，再在 GameState.handle_network_message 扩分支，保持“单入口”维护。