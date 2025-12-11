import tkinter as tk
from tkinter import messagebox
import os
import sys

import tkinter as tk
from tkinter import messagebox

from src.game.process import GameState

# 以下为各个界面的定义
class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="🌟 欢迎来到纸牌对战 🌟", font=('Arial', 24)).pack(pady=20)

        # IP/Port 输入
        input_frame = tk.Frame(self)
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="IP 地址:").grid(row=0, column=0, padx=5, pady=5)
        self.ip_entry = tk.Entry(input_frame)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(input_frame, text="端口:").grid(row=1, column=0, padx=5, pady=5)
        self.port_entry = tk.Entry(input_frame)
        self.port_entry.insert(0, "8888")
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)

        # 房间操作按钮
        action_frame = tk.Frame(self)
        action_frame.pack(pady=10)

        tk.Button(action_frame, text="创建房间",
                  command=lambda: self.controller.connect_or_create(self.ip_entry.get(), self.port_entry.get(),
                                                                    "create")).pack(side="left", padx=10)
        tk.Button(action_frame, text="加入房间",
                  command=lambda: self.controller.connect_or_create(self.ip_entry.get(), self.port_entry.get(),
                                                                    "join")).pack(side="left", padx=10)

        # 房间状态显示
        self.status_var = tk.StringVar(value="房间状态：未连接")
        self.status_label = tk.Label(self, textvariable=self.status_var, font=('Arial', 14))
        self.status_label.pack(pady=15)

        # 开始游戏按钮 (初始禁用)
        self.start_button = tk.Button(self, text="开始游戏",
                                      command=self.controller.start_game,
                                      state=tk.DISABLED,
                                      font=('Arial', 18, 'bold'),
                                      fg="white", bg="green")
        self.start_button.pack(pady=30)

    def update_room_status(self, status_message, enable_start=False):
        """更新房间状态显示，并控制开始按钮的可用性"""
        self.status_var.set(f"房间状态：{status_message}")
        if enable_start:
            self.start_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.DISABLED)


class GamePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.selected_card_index = None  # 记录玩家选择打出的牌索引
        self.selected_draw_index = None  # 记录玩家选择给对方的牌索引

        # --- 1. 顶部：对方状态 ---
        self.opp_status_frame = tk.Frame(self)
        self.opp_status_frame.pack(side="top", fill="x", pady=10)

        self.opp_hp_var = tk.StringVar(value="对方生命值: --")
        self.opp_hand_var = tk.StringVar(value="对方手牌数: --")
        self.opp_cost_var = tk.StringVar(value="对方Cost: --")

        tk.Label(self.opp_status_frame, textvariable=self.opp_hp_var).pack(side="left", padx=20)
        tk.Label(self.opp_status_frame, textvariable=self.opp_hand_var).pack(side="left", padx=20)
        tk.Label(self.opp_status_frame, textvariable=self.opp_cost_var).pack(side="left", padx=20)

        # --- 2. 中部：游戏区域 & 回合控制 ---
        mid_frame = tk.Frame(self)
        mid_frame.pack(expand=True, fill="both")

        # 2a. 提示/回合画面
        self.turn_message_var = tk.StringVar(value="")
        self.turn_message_label = tk.Label(mid_frame, textvariable=self.turn_message_var, font=('Arial', 36, 'bold'),
                                           fg='red')
        self.turn_message_label.pack(pady=50)  # 最初是空的，回合开始/结束时显示

        # 2b. 结束回合按钮
        tk.Button(mid_frame, text="➡️ 结束回合", command=self.end_turn_click,
                  font=('Arial', 16), bg="red", fg="white").pack(pady=20)
        self.turn_end_call = None

        # --- 3. 底部：己方状态 & 手牌 ---
        self.self_status_frame = tk.Frame(self)
        self.self_status_frame.pack(side="bottom", fill="x", pady=10)

        self.self_hp_var = tk.StringVar(value="己方生命值: --")
        self.self_hand_var = tk.StringVar(value="己方手牌数: --")
        self.self_cost_var = tk.StringVar(value="己方Cost: --")

        tk.Label(self.self_status_frame, textvariable=self.self_hp_var).pack(side="left", padx=20)
        tk.Label(self.self_status_frame, textvariable=self.self_hand_var).pack(side="left", padx=20)
        tk.Label(self.self_status_frame, textvariable=self.self_cost_var).pack(side="left", padx=20)

        # 己方手牌区域
        self.hand_frame = tk.Frame(self)
        self.hand_frame.pack(side="bottom", fill="x", pady=10)
        self.card_buttons = []

    # --- 状态更新函数 ---
    def StatusUpdate(self, game_data):
        """
        根据game端传来的数据包，更新显示的双方状态。
        :param game_data: 包含所有游戏状态的数据结构
        """
        player_data = game_data['player_status']['self']
        opponent_data = game_data['player_status']['opponent']

        # 更新己方状态
        self.self_hp_var.set(f"己方生命值: {player_data['hp']}")
        self.self_hand_var.set(f"己方手牌数: {player_data['hand_count']}")
        self.self_cost_var.set(f"己方Cost: {player_data['cost']}")

        # 更新对方状态
        self.opp_hp_var.set(f"对方生命值: {opponent_data['hp']}")
        self.opp_hand_var.set(f"对方手牌数: {opponent_data['hand_count']}")
        self.opp_cost_var.set(f"对方Cost: {opponent_data['cost']}")

        # 更新己方手牌显示
        self.update_hand_display(player_data['hand_cards'])

    def update_hand_display(self, hand_cards):
        """重新绘制己方手牌按钮"""
        # 清除旧的按钮
        for btn in self.card_buttons:
            btn.destroy()
        self.card_buttons = []

        # 绘制新的按钮
        for i, card_name in enumerate(hand_cards):
            btn = tk.Button(self.hand_frame, text=card_name,
                            command=lambda idx=i: self.card_click(idx),
                            width=10, height=5, relief=tk.RAISED)
            btn.pack(side="left", padx=5)
            self.card_buttons.append(btn)

    # --- 回合画面函数 ---
    def DrawTurnStart(self):
        """在UI界面绘出回合开始画面"""
        self.turn_message_var.set("己方回合开始!")
        self.after(1500, lambda: self.turn_message_var.set(""))  # 1.5秒后清空

    def DrawTurnEnd(self):
        """在UI界面绘出回合结束画面"""
        self.turn_message_var.set("回合结束!")
        self.after(1500, lambda: self.turn_message_var.set(""))  # 1.5秒后清空

    # --- 玩家出牌阶段 ---
    def card_click(self, index):
        """玩家点击手牌选择/打出"""
        if self.selected_card_index == index:
            # 再次点击：确认打出
            self.play_card(index)
        else:
            # 首次点击：选择该牌，改变颜色提示
            self.selected_card_index = index
            for i, btn in enumerate(self.card_buttons):
                if i == index:
                    btn.config(relief=tk.SUNKEN, bg="yellow")
                else:
                    btn.config(relief=tk.RAISED, bg="SystemButtonFace")

    def play_card(self, index: int):
        """执行打牌操作 -> 调用 GameState.playCard，并刷新 UI。"""
        gs: GameState = self.controller.game_state
        if gs is None:
            messagebox.showerror("错误", "GameState 未初始化")
            return

        success = gs.playCard(index)
        if not success:
            messagebox.showwarning("出牌失败", "该牌不可出（费用不足或索引无效）")
            return

        # 出牌成功，刷新 UI
        ui_state = gs.get_ui_state()
        self.StatusUpdate(ui_state)

        # 重置选择状态并清除选中颜色
        self.selected_card_index = None
        for btn in self.card_buttons:
            btn.config(relief=tk.RAISED, bg="SystemButtonFace")


    def end_turn_click(self):
        """点击“结束回合”按钮"""
        # **这里需要通知后端回合结束**
        self.DrawTurnEnd()
        # 模拟后端发送抽牌数据包
        self.turn_end_call()

        # --- 抽牌选择阶段 ---

    def show_draw_choice(self, three_cards_data):
        """
        回合结束后，显示三张牌供玩家选择一张给对方。
        :param three_cards_data: 三张牌的内容列表
        """
        # 弹出新窗口或在主界面上覆盖一个Frame
        self.draw_window = tk.Toplevel(self)
        self.draw_window.title("选择一张递给对手")
        self.draw_window.geometry("400x400")

        tk.Label(self.draw_window, text="请选择一张牌放入对手牌堆:").pack(pady=10)

        card_choice_frame = tk.Frame(self.draw_window)
        card_choice_frame.pack(pady=10)

        self.draw_choice_buttons = []
        for i, card_name in enumerate(three_cards_data):
            btn = tk.Button(card_choice_frame, text=card_name,
                            command=lambda idx=i: self.draw_card_select(idx, three_cards_data),
                            width=10)
            btn.pack(side="left", padx=5)
            self.draw_choice_buttons.append(btn)

        # 锁定主界面，直到选择完毕
        self.draw_window.grab_set()

    def draw_card_select(self, index, three_cards_data):
        """选择一张牌递给对手"""
        self.selected_draw_index = index

        # 改变选中牌的颜色提示
        for i, btn in enumerate(self.draw_choice_buttons):
            if i == index:
                btn.config(relief=tk.SUNKEN, bg="lightgreen")
            else:
                btn.config(relief=tk.RAISED, bg="SystemButtonFace")

        # 确认选择并关闭窗口
        selected_card = three_cards_data[index]
        # **这里需要发送选择这张牌给对手的网络数据包**
        messagebox.showinfo("递牌", f"选择将 {selected_card} 递给对手。")

        self.draw_window.destroy()

    # --- 通用API：实现抽牌功能（由后端调用） ---
    def DrawACard(self):
        gs: GameState = self.controller.game_state
        if gs is None:
            return
        ui_state = gs.get_ui_state()
        self.StatusUpdate(ui_state)

class EndPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.result_var = tk.StringVar(value="游戏结束...")
        self.result_label = tk.Label(self, textvariable=self.result_var, font=('Arial', 48, 'bold'))
        self.result_label.pack(pady=50)

        # 再来一局按钮
        tk.Button(self, text="再来一局",
                  command=self.restart_game,
                  font=('Arial', 20),
                  bg="blue", fg="white").pack(pady=30)

    def GameOver(self, is_winner):
        """
        显示游戏结果。
        :param is_winner: 布尔值，如果己方获胜则为 True
        """
        if is_winner:
            self.result_var.set("🏆 YOU WIN 🏆")
            self.result_label.config(fg="green")
        else:
            self.result_var.set("😭 YOU LOSE 😭")
            self.result_label.config(fg="red")

        self.controller.show_frame("EndPage")

    def restart_game(self):
        """点击“再来一局”，返回开始界面并准备新连接"""
        # **这里需要通知后端准备新局，并关闭当前的socket连接等**
        self.controller.show_frame("StartPage")
        self.controller.frames["StartPage"].update_room_status("未连接")

# UI.py

class MainApp(tk.Tk):
    """主应用窗口，用于管理不同界面的切换"""
    def __init__(self):
        super().__init__()
        self.title("纸牌对战游戏")
        self.geometry("800x600")

        self.game_state: GameState | None = None  # 由 main.py 注入

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (StartPage, GamePage, EndPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")
        
        self.game_started = False

    def setState(self, game_state: GameState):
        """绑定网络回调到 UI 更新"""
        self.game_state = game_state

        self.game_state.on_game_start_callback = self._on_game_start_from_network
        self.game_state.ui_draw_card_selection_callback = self.frames["GamePage"].show_draw_choice

        if self.game_state.NetworkManager:
            self.game_state.NetworkManager.on_connected = self._on_network_connected        
            self.game_state.NetworkManager.on_peer_connected = self._on_peer_connected

        self.frames["GamePage"].turn_end_call = self.game_state.turnEnd

    def _on_game_start_from_network(self):
        """当收到网络游戏开始消息时调用"""
        print("[UI] 收到网络游戏开始通知")
        # 在主线程中安全地切换
        self.after(0, self._do_start_game)

    def _on_network_connected(self):
        """网络连接成功时"""
        # 在主线程安全地更新 UI
        self.after(0, self._update_ui_after_connected)

    def _on_peer_connected(self, peer_count: int):
        """当有客户端连接时（主机端调用）"""
        print(f"[UI] 客户端连接，当前连接数: {peer_count}")
        self.after(0, lambda: self._update_ui_peer_connected(peer_count))

    def _update_ui_peer_connected(self, peer_count: int):
        """更新 UI 显示客户端已连接"""
        start_page = self.frames["StartPage"]
        start_page.update_room_status(
            "✅ 客户端已连接，准备开始游戏！",
            enable_start=True  # 启用"开始游戏"按钮
        )


    def _update_ui_after_connected(self):
        """更新 StartPage，允许开始游戏"""
        start_page = self.frames["StartPage"]
        start_page.update_room_status(
            "✅ 已连接，准备开始！",
            enable_start=True  # 启用"开始游戏"按钮
        )

    def show_frame(self, page_name: str):
        frame = self.frames[page_name]
        frame.tkraise()

    def connect_or_create(self, ip, port, action: str):
        """处理创建/加入房间的逻辑，真正调用 GameState.initNetwork。"""
        if self.game_state is None:
            messagebox.showerror("错误", "GameState 尚未初始化")
            return

        is_host = (action == "create")
        try:
            self.game_state.initNetwork(is_host, ip, int(port))
        except Exception as e:
            messagebox.showerror("连接失败", str(e))
            return

        start_page: StartPage = self.frames["StartPage"]
        if is_host:
            start_page.update_room_status("房主已创建房间，等待玩家加入", enable_start=True)
            self.game_state.is_my_turn = True  # 主机先手
        else:
            # 客户端通常等待房主开始游戏
            start_page.update_room_status("已加入房间，等待房主开始", enable_start=False)

    def _do_start_game(self):
        """【提取为公共方法】实际执行游戏开始"""
        self.show_frame("GamePage")
        game_page: GamePage = self.frames["GamePage"]
        ui_state = self.game_state.get_ui_state()
        game_page.StatusUpdate(ui_state)
        if self.game_state.is_my_turn:
            game_page.DrawTurnStart()   
        else:
            game_page.turn_message_var.set("等待对手回合...")

    def start_game(self):
        """从开始界面点击“开始游戏”."""
        if self.game_state is None:
            messagebox.showerror("错误", "GameState 尚未初始化")
            return
        
        if not self.game_state.NetworkManager.is_connected:
            messagebox.showwarning("连接未完成", "请先连接到房间")
            return
        
        if self.game_state.NetworkManager.is_host:
            print("[Host] 发送游戏开始通知...")
            self.game_state.NetworkManager.send({
                "type": "game_start",
                "message": "主机已开始游戏"
            })

        # 切到游戏界面
        self._do_start_game()


# 启动应用程序
if __name__ == "__main__":
    app = MainApp()
    app.mainloop()