import tkinter as tk
from tkinter import messagebox
import os
import sys
# 放在所有 tkinter 或相关库的导入之前！

# ----------------------------------------------------
# ** 重要步骤：手动设置 Tcl/Tk 路径 **
#
# 根据你在步骤 1 确认的路径进行修改。
# 假设你的 Tcl 库文件在 D:\PYTHON\Python\Lib\tcl8.6
# 假设你的 Tk 库文件在 D:\PYTHON\Python\Lib\tk8.6
# ----------------------------------------------------

# 设置 TCL_LIBRARY 环境变量
os.environ['TCL_LIBRARY'] = r'D:\PYTHON\Python\tcl\tcl8.6'

# 设置 TK_LIBRARY 环境变量 (虽然不总是必需，但以防万一)
os.environ['TK_LIBRARY'] = r'D:\PYTHON\Python\tcl\tk8.6'

# ----------------------------------------------------
# 导入 tkinter（现在应该能找到依赖文件了）
import tkinter as tk
from tkinter import messagebox
# ... 你的其他代码继续 ...
# 假设的常量，你需要根据实际游戏逻辑调整
PLAYER_HAND_SIZE = 5
MAX_COST = 10



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
        self.self_cost_var.set(f"己方Cost: {player_data['cost']}/{MAX_COST}")

        # 更新对方状态
        self.opp_hp_var.set(f"对方生命值: {opponent_data['hp']}")
        self.opp_hand_var.set(f"对方手牌数: {opponent_data['hand_count']}")
        self.opp_cost_var.set(f"对方Cost: {opponent_data['cost']}/{MAX_COST}")

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

    def play_card(self, index):
        """执行打牌操作（发送数据到后端）"""
        card_name = self.controller.game_state['player_status']['self']['hand_cards'][index]
        # **这里需要发送打出这张牌的网络数据包**
        messagebox.showinfo("出牌", f"打出了: {card_name}")

        # 重置选择状态并清除选中颜色
        self.selected_card_index = None
        for btn in self.card_buttons:
            btn.config(relief=tk.RAISED, bg="SystemButtonFace")

    def end_turn_click(self):
        """点击“结束回合”按钮"""
        # **这里需要通知后端回合结束**
        self.DrawTurnEnd()
        # 模拟后端发送抽牌数据包
        self.after(2000, lambda: self.show_draw_choice(["Card X", "Card Y", "Card Z"]))

        # --- 抽牌选择阶段 ---

    def show_draw_choice(self, three_cards_data):
        """
        回合结束后，显示三张牌供玩家选择一张给对方。
        :param three_cards_data: 三张牌的内容列表
        """
        # 弹出新窗口或在主界面上覆盖一个Frame
        self.draw_window = tk.Toplevel(self)
        self.draw_window.title("选择一张递给对手")
        self.draw_window.geometry("400x200")

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
        self.selected_draw_index = None

    # --- 通用API：实现抽牌功能（由后端调用） ---
    def DrawACard(self, num_cards, card_data_list):
        """
        从后端数据包中解析抽牌信息，并更新手牌显示。
        :param num_cards: 抽牌数量
        :param card_data_list: 抽到的牌的数据包列表
        """
        # 假设抽牌逻辑已经在后端处理，这里只更新UI
        self.controller.game_state['player_status']['self']['hand_cards'].extend(card_data_list)
        self.controller.game_state['player_status']['self']['hand_count'] += num_cards

        # 重新调用 StatusUpdate 来刷新 UI
        self.StatusUpdate(self.controller.game_state)


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

class MainApp(tk.Tk):
    """主应用窗口，用于管理不同界面的切换"""

    def __init__(self):
        super().__init__()
        self.title("纸牌对战游戏")
        self.geometry("800x600")

        # 容器 Frame，用于容纳当前显示的界面
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        # 初始化所有界面
        for F in (StartPage, GamePage, EndPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")  # 默认显示开始界面

        # 假设存储游戏状态
        self.game_state = {
            "is_host": False,
            "ip": "",
            "port": "",
            "player_status": {
                "self": {"hp": 30, "hand_count": 5, "cost": 3, "hand_cards": ["Card A", "Card B", "Card C"]},
                "opponent": {"hp": 30, "hand_count": 5, "cost": 3}
            }
        }

    def show_frame(self, page_name):
        """显示指定名称的界面"""
        frame = self.frames[page_name]
        frame.tkraise()

    # **重要：将网络/游戏逻辑放在这里或单独的类中，并通过这些方法与UI交互**
    def connect_or_create(self, ip, port, action):
        """处理创建/加入房间的逻辑"""
        self.game_state['ip'] = ip
        self.game_state['port'] = port
        self.game_state['is_host'] = (action == "create")

        # **这里需要添加你的网络连接代码（socket.connect/socket.bind等）**

        messagebox.showinfo("连接状态", f"尝试 {action} 房间 ({ip}:{port})...")

        # 假设连接成功，并更新开始界面的房间状态
        start_page = self.frames["StartPage"]
        start_page.update_room_status("等待另一名玩家...")

        # 假设两名玩家加入后
        # self.show_frame("GamePage")
        pass

    def start_game(self):
        """从开始界面点击“开始游戏”"""
        # 启动游戏逻辑...
        self.show_frame("GamePage")
        game_page = self.frames["GamePage"]
        # 初始化游戏界面的状态显示
        game_page.StatusUpdate(self.game_state)
        game_page.DrawTurnStart()


# 启动应用程序
if __name__ == "__main__":
    app = MainApp()
    app.mainloop()