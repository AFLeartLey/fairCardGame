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

        tk.Label(self, text="🌟 欢迎来到 Project FairCard 🌟", font=("Arial", 24)).pack(pady=20)

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

        tk.Button(
            action_frame,
            text="创建房间",
            command=lambda: self.controller.connect_or_create(
                self.ip_entry.get(), self.port_entry.get(), "create"
            ),
        ).pack(side="left", padx=10)
        tk.Button(
            action_frame,
            text="加入房间",
            command=lambda: self.controller.connect_or_create(
                self.ip_entry.get(), self.port_entry.get(), "join"
            ),
        ).pack(side="left", padx=10)

        # 房间状态显示
        self.status_var = tk.StringVar(value="房间状态：未连接")
        self.status_label = tk.Label(
            self, textvariable=self.status_var, font=("Arial", 14)
        )
        self.status_label.pack(pady=15)

        # 开始游戏按钮 (初始禁用)
        self.start_button = tk.Button(
            self,
            text="开始游戏",
            command=self.controller.start_game,
            state=tk.DISABLED,
            font=("Arial", 18, "bold"),
            fg="white",
            bg="green",
        )
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
        self.turn_end_callback = None  # 结束回合的回调函数

        # --- 1. 顶部：对方状态 ---
        self.opp_status_frame = tk.Frame(self)
        self.opp_status_frame.pack(side="top", fill="x", pady=10)

        self.opp_hp_var = tk.StringVar(value="对方生命值: --")
        self.opp_hand_var = tk.StringVar(value="对方手牌数: --")
        self.opp_cost_var = tk.StringVar(value="对方Cost: --")

        tk.Label(self.opp_status_frame, textvariable=self.opp_hp_var).pack(
            side="left", padx=20
        )
        tk.Label(self.opp_status_frame, textvariable=self.opp_hand_var).pack(
            side="left", padx=20
        )
        tk.Label(self.opp_status_frame, textvariable=self.opp_cost_var).pack(
            side="left", padx=20
        )

        # --- 2. 中部：游戏区域 & 回合控制 ---
        mid_frame = tk.Frame(self)
        mid_frame.pack(expand=True, fill="both")

        # 2a. 提示/回合画面
        self.turn_message_var = tk.StringVar(value="")
        self.turn_message_label = tk.Label(
            mid_frame,
            textvariable=self.turn_message_var,
            font=("Arial", 36, "bold"),
            fg="red",
        )
        self.turn_message_label.pack(pady=50)

        # 2b. 结束回合按钮
        # 【新增】回合状态指示器框架
        turn_indicator_frame = tk.Frame(mid_frame, bg="lightgray", padx=20, pady=10)
        turn_indicator_frame.pack(pady=10)

        # 回合指示器标签
        self.turn_indicator_var = tk.StringVar(value="⏳ 等待游戏开始...")
        self.turn_indicator_label = tk.Label(
            turn_indicator_frame,
            textvariable=self.turn_indicator_var,
            font=("Arial", 18, "bold"),
            fg="blue",
            bg="lightgray",
            padx=20,
            pady=10
        )
        self.turn_indicator_label.pack()

        # 2b. 结束回合按钮（存储引用以便后续禁用）
        self.turn_end_button = tk.Button(
            mid_frame,
            text="➡️ 结束回合",
            command=self.end_turn_click,
            font=("Arial", 16),
            bg="red",
            fg="white",
        )
        self.turn_end_button.pack(pady=20)

        self.turn_end_call = None


        # --- 3. 底部：己方状态 & 手牌 ---
        self.self_status_frame = tk.Frame(self)
        self.self_status_frame.pack(side="bottom", fill="x", pady=10)

        self.self_hp_var = tk.StringVar(value="己方生命值: --")
        self.self_hand_var = tk.StringVar(value="己方手牌数: --")
        self.self_cost_var = tk.StringVar(value="己方Cost: --")

        tk.Label(self.self_status_frame, textvariable=self.self_hp_var).pack(
            side="left", padx=20
        )
        tk.Label(self.self_status_frame, textvariable=self.self_hand_var).pack(
            side="left", padx=20
        )
        tk.Label(self.self_status_frame, textvariable=self.self_cost_var).pack(
            side="left", padx=20
        )

        # 己方手牌区域
        self.hand_frame = tk.Frame(self)
        self.hand_frame.pack(side="bottom", fill="x", pady=10)
        self.card_buttons = []  # 存储手牌按钮

    # --- 状态更新函数 ---
    def StatusUpdate(self, game_data):
        """
        根据game端传来的数据包，更新显示的双方状态。
        :param game_data: 包含所有游戏状态的数据结构
        """
        player_data = game_data["player_status"]["self"]
        opponent_data = game_data["player_status"]["opponent"]
        
        # 更新己方状态
        self.self_hp_var.set(f"己方生命值: {player_data['hp']}")
        self.self_hand_var.set(f"己方手牌数: {player_data['hand_count']}")
        self.self_cost_var.set(f"己方Cost: {player_data['cost']}")
        
        # 更新对方状态
        self.opp_hp_var.set(f"对方生命值: {opponent_data['hp']}")
        self.opp_hand_var.set(f"对方手牌数: {opponent_data['hand_count']}")
        self.opp_cost_var.set(f"对方Cost: {opponent_data['cost']}")
        
        # 更新己方手牌显示
        self.update_hand_display(player_data["hand_cards"])
        
        # 【新增】获取回合状态并更新 UI
        is_my_turn = game_data["player_status"].get("is_my_turn", False)
        self.update_turn_state(is_my_turn)


    def update_hand_display(self, hand_cards):
        """重新绘制己方手牌为竖着的长方形，显示详细信息"""
        # 清除旧的按钮
        for btn in self.card_buttons:
            btn.destroy()
        self.card_buttons = []

        # 绘制新的手牌按钮
        for i, card in enumerate(hand_cards):
            # 获取卡牌信息
            try:
                p_effect = card["pcarditem_type"]
                n_effect = card["ncarditem_type"]
                power = card["item_power"]
                card_name = f"卡牌 {i + 1}"
                print(f"[UI] 卡牌 {i + 1}: {card_name}，正面: {p_effect}，负面: {n_effect}，等级: Lv{power}")
                # 格式化卡牌信息，显示在多行
                card_text = f"{card_name}\n━━━━━━━━━━━━━━━\n正面: {p_effect}\n负面: {n_effect}\n等级: Lv{power}"

            except Exception as e:
                # 如果卡牌对象没有这些属性，显示备用信息
                print(f"[UI] ⚠️ 卡牌 {i + 1} 未找到详细信息，使用 str(card)：{str(card)}")
                card_text = str(card)

            # 创建手牌按钮（竖着的长方形）
            btn = tk.Button(
                self.hand_frame,
                text=card_text,
                command=lambda idx=i: self.card_click(idx),
                width=12,  # 较小宽度，形成竖着长方形
                height=8,  # 较大高度
                relief=tk.RAISED,
                font=("Arial", 9),
                anchor="nw",  # 文本左对齐，从上开始
                justify="left",
                bg="#f0f0f0",  # 浅灰色背景
                activebackground="#e0e0e0"
            )
            btn.pack(side="left", padx=5, pady=5)
            self.card_buttons.append(btn)

    def update_turn_state(self, is_my_turn: bool) -> None:
        """
        【新方法】根据回合状态更新 UI
        
        :param is_my_turn: True 表示自己的回合，False 表示对方的回合
        """
        print(f"[UI] 更新回合状态: is_my_turn={is_my_turn}")
        
        if is_my_turn:
            # 【自己的回合】
            self.turn_indicator_var.set("✅ 己方回合 - 可以出牌！")
            self.turn_indicator_label.config(fg="green", bg="#e6ffe6")  # 绿色背景
            
            # 启用结束回合按钮
            self.turn_end_button.config(state=tk.NORMAL)
            
            # 启用所有手牌按钮
            for btn in self.card_buttons:
                btn.config(state=tk.NORMAL)
            
            print("[UI] ✅ 启用了所有操作按钮")
            
        else:
            # 【对方的回合】
            self.turn_indicator_var.set("⏳ 对方回合 - 等待中...")
            self.turn_indicator_label.config(fg="red", bg="#ffe6e6")   # 红色背景
            
            # 禁用结束回合按钮
            self.turn_end_button.config(state=tk.DISABLED)
            
            # 禁用所有手牌按钮
            for btn in self.card_buttons:
                btn.config(state=tk.DISABLED)
            
            print("[UI] 🔒 禁用了所有操作按钮")


    # --- 回合画面函数 ---
    def DrawTurnStart(self):
        """在UI界面绘出回合开始画面"""
        self.turn_message_var.set("己方回合开始!")
        self.update_turn_state(True)
        self.after(1500, lambda: self.turn_message_var.set(""))

    def DrawRemoteTurnStart(self):
        self.turn_message_var.set("对方回合开始!")
        self.update_turn_state(False)
        self.after(1500, lambda: self.turn_message_var.set(""))

    def DrawTurnEnd(self):
        """在UI界面绘出回合结束画面"""
        self.turn_message_var.set("回合结束!")
        self.after(1500, lambda: self.turn_message_var.set(""))

    # --- 抽牌选择弹窗（保持"单击选择，点击按钮递出"的形式）---
    def draw_card_selection(self, three_cards: list) -> object:
        """
        显示卡牌选择弹窗，并返回用户选择的卡牌
        """
        print(f"[UI] 显示卡牌选择窗口，共 {len(three_cards)} 张卡牌")

        # 【关键】初始化选择结果容器
        self.selected_card = None
        self.draw_choice_buttons = []  # 清空之前的按钮列表

        # 创建模态窗口
        self.draw_window = tk.Toplevel(self)
        self.draw_window.title("选择一张卡牌")
        self.draw_window.geometry("700x500")  # 调大窗口以适应更多内容
        self.draw_window.resizable(False, False)

        # 绑定窗口关闭事件
        self.draw_window.protocol("WM_DELETE_WINDOW", self._on_draw_window_close)

        # 【美化】添加标题
        title_label = tk.Label(self.draw_window, text="请选择一张卡牌递给对手：",
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=15)

        # 【改进】卡牌显示框架 - 保持居中
        card_display_frame = tk.LabelFrame(self.draw_window, text="可选卡牌",
                                           font=('Arial', 12), padx=10, pady=10)
        card_display_frame.pack(pady=10, padx=20, fill="x")

        # 【新增】卡牌按钮容器，用于更精细地控制按钮的居中
        button_container = tk.Frame(card_display_frame)
        button_container.pack(pady=10)

        # 【关键】为每张卡牌创建选择按钮
        BUTTON_WIDTH = 15
        BUTTON_HEIGHT = 6  # 增加高度以显示更多信息

        for i, card in enumerate(three_cards):
            # 格式化卡牌信息
            card_str = self._format_card_for_display(card)

            btn = tk.Button(
                button_container,
                text=card_str,
                # 单击时调用 _on_card_selected
                command=lambda idx=i, c=card: self._on_card_selected(idx, c),
                width=BUTTON_WIDTH,
                height=BUTTON_HEIGHT,
                relief=tk.RAISED,
                font=('Arial', 10),
                bg="lightblue",
                activebackground="lightyellow",
                anchor="nw",  # 文本左对齐，从上开始
                justify="left"
            )
            btn.pack(side="left", padx=15)
            self.draw_choice_buttons.append(btn)

        # 【新增】操作提示框架
        info_frame = tk.Frame(self.draw_window)
        info_frame.pack(pady=15)

        tk.Label(info_frame, text="提示：单击卡牌选择，选中的卡牌会高亮显示",
                 font=('Arial', 10), fg="gray").pack()

        # 确认按钮框架
        confirm_frame = tk.Frame(self.draw_window)
        confirm_frame.pack(pady=10)

        # 确认按钮
        confirm_btn = tk.Button(confirm_frame, text="✅ 确认选择并递给对手",
                                command=self._confirm_draw_selection_wrapper,
                                font=('Arial', 12, 'bold'),
                                bg="lightgreen",
                                padx=20,
                                pady=10)
        confirm_btn.pack()

        # 【关键】使窗口成为模态窗口
        self.draw_window.transient(self.master)
        self.draw_window.grab_set()
        self.draw_window.focus_set()

        # 【关键】阻塞等待用户选择
        self.wait_window(self.draw_window)

        # 【关键返回值】用户选择完成后返回选中的卡牌
        if self.selected_card is not None:
            print(f"[UI] 用户选择了卡牌: {self._format_card_for_display(self.selected_card)}")
            return self.selected_card
        else:
            print("[UI] ⚠️ 用户未完成选择或取消，返回 None")
            return None

    def _on_draw_window_close(self):
        """处理窗口关闭事件"""
        print("[UI] 窗口被关闭或取消")
        self.selected_card = None
        if self.draw_window:
            self.draw_window.destroy()

    def _format_card_for_display(self, card: object) -> str:
        """
        将卡牌对象格式化为显示字符串
        """
        try:
            if hasattr(card, 'getPcarditem') and hasattr(card, 'getNcarditem'):
                return (f"正面: {card.getPcarditem()}\n"
                        f"负面: {card.getNcarditem()}\n"
                        f"等级: Lv{card.getItemPower()}")
            else:
                return str(card)
        except Exception as e:
            print(f"[UI] 格式化卡牌失败: {e}")
            return str(card)

    def _on_card_selected(self, index: int, card: object) -> None:
        """
        【回调方法】当玩家单击卡牌时调用 - 仅高亮显示并保存选择
        """
        print(f"[UI] 玩家单击了第 {index} 张卡牌 (仅选中)")

        # 【改进】高亮选中的按钮
        for i, btn in enumerate(self.draw_choice_buttons):
            if i == index:
                # 高亮
                btn.config(relief=tk.SUNKEN, bg="lightgreen", fg="black",
                           font=('Arial', 10, 'bold'))
            else:
                # 恢复默认
                btn.config(relief=tk.RAISED, bg="lightblue", fg="black",
                           font=('Arial', 10))

        # 【关键】保存用户的选择
        self.selected_card = card

    def _confirm_draw_selection_wrapper(self):
        """确认选择按钮的回调"""
        if self.selected_card:
            # 显示确认消息
            self.draw_window.destroy()
        else:
            messagebox.showwarning("提示", "请先选择一张卡牌！")

    # --- 玩家出牌阶段 ---
    def card_click(self, index):
        """玩家点击手牌选择/打出"""
        if index >= len(self.card_buttons):
            return

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
        gs = self.controller.game_state if hasattr(self.controller, 'game_state') else None
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
        """点击"结束回合"按钮 - 触发回合结束流程"""
        gs = self.controller.game_state if hasattr(self.controller, 'game_state') else None
        if gs is None:
            return

        print("[UI] 玩家点击了结束回合按钮")

        # 【步骤 1】显示回合结束提示
        self.DrawTurnEnd()

        # 【步骤 2】禁用卡牌操作（玩家已结束回合）
        gs.is_my_turn = False

        # 【步骤 3】2秒后启动回合结束处理
        if hasattr(self, 'turn_end_callback') and self.turn_end_callback:
            print("[UI] 启动回合结束处理")
            self.after(1000, self.turn_end_callback)
        else:
            print("[UI] ⚠️ 警告: turn_end_callback 未设置！")

    # --- 通用API：实现抽牌功能（由后端调用） ---
    def DrawACard(self):
        gs = self.controller.game_state if hasattr(self.controller, 'game_state') else None
        if gs is None:
            return
        ui_state = gs.get_ui_state()
        self.StatusUpdate(ui_state)


class EndPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.result_var = tk.StringVar(value="游戏结束...")
        self.result_label = tk.Label(
            self, textvariable=self.result_var, font=("Arial", 48, "bold")
        )
        self.result_label.pack(pady=50)

        # 再来一局按钮
        tk.Button(
            self,
            text="再来一局",
            command=self.restart_game,
            font=("Arial", 20),
            bg="blue",
            fg="white",
        ).pack(pady=30)

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
        print("[UI] 点击了'再来一局'按钮")
    
    # 关闭网络连接
        try:
            if self.controller.game_state and self.controller.game_state.NetworkManager:
                self.controller.game_state.NetworkManager.close()
        except:
            pass
        
        # 关键：结束 mainloop
        self.controller.should_restart = True
        self.controller.quit()


# UI.py


class MainApp(tk.Tk):
    """主应用窗口，用于管理不同界面的切换"""

    def __init__(self):
        super().__init__()
        self.title("Project FairCard")
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
        self.should_restart = False
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self.game_started = False

    def on_window_close(self):
        """处理用户关闭窗口"""
        print("[UI] 窗口关闭事件")
        
        try:
            if self.game_state and self.game_state.NetworkManager:
                self.game_state.NetworkManager.close()
        except:
            pass
        
        # 【关键】标记不重启
        self.should_restart = False
        self.quit()

    def destroy_app(self):
        """彻底销毁应用及所有资源"""
        print("[UI] 开始销毁应用...")
        
        try:
            # 关闭网络连接
            if self.game_state and self.game_state.NetworkManager:
                self.game_state.NetworkManager.close()
        except:
            pass
        
        try:
            # 销毁所有框架
            for frame_name, frame in self.frames.items():
                frame.destroy()
        except:
            pass
        
        try:
            # 销毁主窗口
            self.destroy()
            print("[UI] ✅ 主窗口已销毁")
        except:
            pass



    def setState(self, game_state: GameState):
        """绑定网络回调到 UI 更新"""
        self.game_state = game_state

        self.game_state.on_game_start_callback = self._on_game_start_from_network
        self.game_state.ui_draw_card_selection_callback = self.frames[
            "GamePage"
        ].draw_card_selection

        if self.game_state.NetworkManager:
            self.game_state.NetworkManager.on_connected = self._on_network_connected
            self.game_state.NetworkManager.on_peer_connected = self._on_peer_connected

        self.frames["GamePage"].turn_end_callback = self.game_state.turnEnd
        self.game_state.ui_update = self.frames["GamePage"].StatusUpdate
        self.game_state.game_over_callback = self.frames["EndPage"].GameOver

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
            "✅ 客户端已连接，准备开始游戏！", enable_start=True  # 启用"开始游戏"按钮
        )

    def _update_ui_after_connected(self):
        """更新 StartPage，允许开始游戏"""
        start_page = self.frames["StartPage"]
        start_page.update_room_status(
            "✅ 已连接，准备开始！", enable_start=True  # 启用"开始游戏"按钮
        )

    def show_frame(self, page_name: str):
        frame = self.frames[page_name]
        frame.tkraise()

    def connect_or_create(self, ip, port, action: str):
        """处理创建/加入房间的逻辑，真正调用 GameState.initNetwork。"""
        if self.game_state is None:
            messagebox.showerror("错误", "GameState 尚未初始化")
            return

        is_host = action == "create"
        try:
            self.game_state.initNetwork(is_host, ip, int(port))
        except Exception as e:
            messagebox.showerror("连接失败", str(e))
            return

        start_page: StartPage = self.frames["StartPage"]
        if is_host:
            start_page.update_room_status(
                "房主已创建房间，等待玩家加入", enable_start=True
            )
            self.game_state.is_my_turn = True  # 主机先手
        else:
            # 客户端通常等待房主开始游戏
            start_page.update_room_status(
                "已加入房间，等待房主开始", enable_start=False
            )

    def _do_start_game(self):
        """【提取为公共方法】实际执行游戏开始"""
        self.show_frame("GamePage")
        self.game_state.showframe = self.show_frame
        self.game_state.drawTurnstart = self.frames["GamePage"].DrawTurnStart
        game_page: GamePage = self.frames["GamePage"]
        ui_state = self.game_state.get_ui_state()
        for _ in range(3):
            self.game_state.chooseCard()
        game_page.StatusUpdate(ui_state)
        if self.game_state.is_my_turn:
            game_page.DrawTurnStart()
            self.game_state.ui_update(self.game_state.get_ui_state())
        else:
            game_page.DrawRemoteTurnStart()
            self.game_state.ui_update(self.game_state.get_ui_state())

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
            self.game_state.NetworkManager.send(
                {"type": "game_start", "message": "主机已开始游戏"}
            )

        # 切到游戏界面
        self._do_start_game()


# 启动应用程序
if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
