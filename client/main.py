from src.game.process import GameState
from src.game.player import Player
from src.graphic.UI import MainApp
from src.network.core import Network
import gc, time
SCREEN_SIZE = (800, 600)

def main():    
    flag = False
    while True:
        try:
            localPlayer, remotePlayer = Player(), Player()
            gs = GameState(local_player= localPlayer, remote_player=remotePlayer, NetworkManager=Network())
            app = MainApp()
            app.setState(gs)
            app.mainloop()

            should_restart = app.should_restart if hasattr(app, 'should_restart') else False
            print(f"[Main] 保存标志: should_restart = {should_restart}")
                
                # 【关键】销毁旧窗口
            if app:
                print("[Main] 【关键】开始销毁旧窗口...")
                app.destroy_app()
                app = None
                
                # 垃圾回收和等待
            gc.collect()
            time.sleep(0.5)
            
            # 检查标志
            if should_restart:
                print("[Main] 检测到'再来一局'→ 重启")
                continue
            else:
                print("[Main] 检测到退出→ 结束")
                break        
        except KeyboardInterrupt:
            if app:
                try:
                    app.destroy_app()
                except:
                    pass
            break



if __name__ == "__main__":
    main()