# ui_main.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import json
import threading
import queue
import urllib3
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import requests
from ui_components import create_main_analysis_tab, create_card_usage_tab
from data_handlers import CardDataHandler
# from ui_helpers import MenuHelper, UIHelper
from bs4 import BeautifulSoup

# 禁用不安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CardSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CEDH卡牌查询工具")
        self.root.geometry("1000x700")

        self.data_handler = CardDataHandler()

        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # 创建Notebook选项卡控件
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 创建不同的选项卡页面
        create_main_analysis_tab(self.notebook, self)
        create_card_usage_tab(self.notebook, self)

        # 创建菜单栏
        self.create_menu()



    def start_usage_search(self):
        """开始搜索卡牌使用率"""
        card_name = self.usage_card_name_var.get().strip()
        if not card_name:
            messagebox.showwarning("输入错误", "请输入要搜索的卡牌名称")
            return

        # 禁用按钮并启动进度条
        self.usage_search_button.config(state='disabled')
        self.usage_progress.start()

        # 清空现有表格数据
        for item in self.usage_result_table.get_children():
            self.usage_result_table.delete(item)
        self.usage_stats_var.set("")

        # 启动后台线程执行搜索
        search_thread = threading.Thread(target=self.search_card_usage_rate, args=(card_name,))
        search_thread.daemon = True
        search_thread.start()

        # 定期检查线程是否完成并更新UI
        self.check_usage_search_complete(search_thread)

    def check_usage_search_complete(self, thread):
        """检查使用率搜索是否完成"""
        if thread.is_alive():
            # 如果线程仍在运行，则继续等待
            self.root.after(100, lambda: self.check_usage_search_complete(thread))
        else:
            # 线程已完成，恢复按钮并停止进度条
            self.usage_progress.stop()
            self.usage_search_button.config(state='normal')

    def search_card_usage_rate(self, card_name):
        """搜索卡牌在各指挥官中的使用率（多线程优化版）"""
        try:
            # 获取所有指挥官列表
            commanders = self.fetch_commanders()
            if not commanders:
                # 如果无法获取完整列表，至少使用当前已知的指挥官
                current_commander = self.commander_var.get()
                commanders = [current_commander] if current_commander else []

            # 使用线程池并发处理指挥官数据获取
            commander_data_map = {}
            with ThreadPoolExecutor(max_workers=5) as executor:
                # 提交所有指挥官数据获取任务
                future_to_commander = {
                    executor.submit(
                        self.data_handler.get_commander_data,
                        commander,
                        self.usage_time_period_var.get(),
                        int(self.usage_min_event_size_var.get()),
                        int(self.usage_standing_var.get())
                    ): commander
                    for commander in commanders
                    if commander
                }

                # 收集结果
                completed = 0
                total_commanders = len(future_to_commander)
                for future in concurrent.futures.as_completed(future_to_commander):
                    commander = future_to_commander[future]
                    try:
                        commander_data = future.result()
                        if commander_data:
                            commander_data_map[commander] = commander_data

                        # 更新进度信息
                        completed += 1
                        self.root.after(0, lambda c=commander, pc=completed, tc=total_commanders:
                        self.usage_stats_var.set(f"正在获取数据 {c} ({pc}/{tc})..."))
                    except Exception as e:
                        print(f"获取 {commander} 数据时出错: {e}")
                        completed += 1

            # 使用线程池并发处理卡牌统计
            usage_results = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                # 提交所有统计任务
                future_to_commander = {
                    executor.submit(self.data_handler.count_card_in_decks, commander_data, card_name): commander
                    for commander, commander_data in commander_data_map.items()
                }

                # 收集统计结果
                completed = 0
                total_stats = len(future_to_commander)
                for future in concurrent.futures.as_completed(future_to_commander):
                    commander = future_to_commander[future]
                    try:
                        used_decks, total_decks = future.result()
                        if total_decks > 0:
                            usage_results.append((commander, used_decks, total_decks))

                        # 更新进度信息
                        completed += 1
                        self.root.after(0, lambda c=commander, pc=completed, tc=total_stats:
                        self.usage_stats_var.set(f"正在统计 {c} ({pc}/{tc})..."))
                    except Exception as e:
                        print(f"统计 {commander} 数据时出错: {e}")
                        completed += 1

            # 在主线程中更新表格
            def update_table():
                for commander, used_decks, total_decks in sorted(usage_results,
                                                                 key=lambda x: x[1] / x[2] if x[2] > 0 else 0,
                                                                 reverse=True):
                    usage_rate = (used_decks / total_decks) * 100 if total_decks > 0 else 0
                    self.usage_result_table.insert('', tk.END,
                                                   values=(commander, used_decks, total_decks, f"{usage_rate:.1f}%"))
                self.usage_stats_var.set(f"总共分析了 {len(usage_results)} 位指挥官的数据")

            self.root.after(0, update_table)

        except Exception as e:
            error_msg = f"搜索过程中出错: {str(e)}"
            self.root.after(0, lambda: self.usage_stats_var.set(error_msg))
            print(error_msg)



    def sort_usage_by_column(self, col):
        """根据指定列对使用率表格进行排序"""
        # 确定排序方向
        if self.usage_sort_column == col:
            self.usage_sort_reverse = not self.usage_sort_reverse
        else:
            self.usage_sort_reverse = False
            self.usage_sort_column = col

        # 获取所有数据
        data = []
        for item in self.usage_result_table.get_children():
            values = self.usage_result_table.item(item, 'values')
            data.append((values, item))

        # 定义排序键函数
        col_index = {'指挥官': 0, '使用套牌数': 1, '总套牌数': 2, '使用率': 3}[col]

        def sort_key(item):
            value = item[0][col_index]
            # 对数值列进行数值排序
            if col_index in [1, 2]:
                try:
                    return int(value)
                except ValueError:
                    return 0
            elif col_index == 3:  # 使用率
                try:
                    return float(value.rstrip('%'))
                except ValueError:
                    return 0.0
            else:  # 文本列
                return value

        # 排序数据
        data.sort(key=sort_key, reverse=self.usage_sort_reverse)

        # 重新插入数据到表格
        for index, (values, item) in enumerate(data):
            self.usage_result_table.move(item, '', index)

        # 更新表头显示
        self.update_usage_heading_display()

    def update_usage_heading_display(self):
        """更新使用率表格表头显示以指示排序方向"""
        # 重置所有表头
        columns = ['指挥官', '使用套牌数', '总套牌数', '使用率']
        for col in columns:
            if col == self.usage_sort_column:
                arrow = ' ↓' if self.usage_sort_reverse else ' ↑'
                self.usage_result_table.heading(col, text=col + arrow)
            else:
                self.usage_result_table.heading(col, text=col)

    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="更新日志", command=self.show_changelog)
        help_menu.add_command(label="关于", command=self.show_about)

    def show_changelog(self):
        """显示更新日志"""
        try:
            # 判断是否为打包环境
            if getattr(sys, 'frozen', False):
                # 打包后的环境，从临时目录获取资源
                bundle_dir = sys._MEIPASS
                changelog_path = os.path.join(bundle_dir, "changelog.md")
            else:
                # 开发环境，直接访问文件
                changelog_path = "changelog.md"

            with open(changelog_path, "r", encoding="utf-8") as f:
                changelog_content = f.read()
        except FileNotFoundError:
            changelog_content = "# 更新日志\n\n暂无更新日志文件"
        except Exception as e:
            changelog_content = f"# 更新日志\n\n读取更新日志时出错: {str(e)}"

        # 创建弹窗显示更新日志
        self.show_text_dialog("更新日志", changelog_content)

    def show_about(self):
        """显示关于对话框"""
        about_text = """CEDH卡牌查询工具

    版本: 2.0.1
    作者: @云玩家阿天
    github: https://github.com/FloatXD/cedhquery

    一个用于查询CEDH环境中卡牌使用情况的工具。"""

        self.show_text_dialog("关于", about_text)

    def show_text_dialog(self, title, content):
        """显示文本内容对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # 创建文本框和滚动条
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        # 布局
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 插入内容
        text_widget.insert(tk.END, content)

        # 如果是markdown格式，简单处理标题
        if content.startswith("#"):
            text_widget.tag_configure("title", font=("Arial", 16, "bold"))
            text_widget.tag_add("title", "1.0", "1.end")

        # 设置文本框为只读
        text_widget.config(state=tk.DISABLED)

        # 添加关闭按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=5)
        close_button = ttk.Button(button_frame, text="关闭", command=dialog.destroy)
        close_button.pack()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def sort_by_column(self, col):
        """根据指定列对表格进行排序"""
        # 确定排序方向
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse  # 切换排序方向
        else:
            self.sort_reverse = False  # 新列默认升序
            self.sort_column = col

        # 获取所有数据
        data = []
        for item in self.result_table.get_children():
            values = self.result_table.item(item, 'values')
            data.append((values, item))

        # 定义排序键函数
        col_index = {'卡牌名称': 0, '出现次数': 1, '总套牌数': 2, '出现率': 3}[col]

        def sort_key(item):
            value = item[0][col_index]
            # 对数值列进行数值排序
            if col_index in [1, 2]:  # 出现次数, 总套牌数
                try:
                    return int(value)
                except ValueError:
                    return 0
            elif col_index == 3:  # 出现率
                try:
                    return float(value.rstrip('%'))
                except ValueError:
                    return 0.0
            else:  # 文本列
                return value

        # 排序数据
        data.sort(key=sort_key, reverse=self.sort_reverse)

        # 重新插入数据到表格
        for index, (values, item) in enumerate(data):
            self.result_table.move(item, '', index)

        # 更新表头显示
        self.update_heading_display()

    def update_heading_display(self):
        """更新表头显示以指示排序方向"""
        # 重置所有表头
        columns = ['卡牌名称', '出现次数', '总套牌数', '出现率']
        for col in columns:
            if col == self.sort_column:
                arrow = ' ↓' if self.sort_reverse else ' ↑'
                self.result_table.heading(col, text=col + arrow)
            else:
                self.result_table.heading(col, text=col)

    def fetch_commanders(self):
        """从edhtop16网站抓取指挥官列表"""
        try:
            response = requests.get(
                "https://edhtop16.com/",
                verify=False,
                proxies={"http": None, "https": None},
                timeout=10
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # 查找目标CSS类元素
            target_class = "text-xl font-bold underline decoration-transparent transition-colors group-hover:decoration-inherit"
            elements = soup.find_all(class_=target_class)

            # 提取文本内容
            commanders = [element.get_text(strip=True) for element in elements]
            return commanders
        except Exception as e:
            print(f"获取指挥官列表失败: {e}")
            return []

    def load_commanders_async(self):
        """异步加载指挥官列表"""

        def load_commanders_task():
            commanders = self.fetch_commanders()
            if commanders:
                # 在主线程中更新UI
                self.root.after(0, lambda: self.update_commander_options(commanders))

        # 启动后台线程加载
        loader_thread = threading.Thread(target=load_commanders_task)
        loader_thread.daemon = True
        loader_thread.start()

    def update_commander_options(self, commanders):
        """更新指挥官选项"""
        self.commander_combo['values'] = commanders
        if commanders:
            self.commander_var.set(commanders[0])  # 设置默认值

    def start_search(self):
        card_name = self.card_name_var.get().strip()
        if not card_name:
            messagebox.showwarning("输入错误", "请输入要搜索的卡牌名称")
            return


        # 禁用按钮并启动进度条
        self.search_button.config(state='disabled')
        self.progress.start()
        self.result_text.delete(1.0, tk.END)
        self.stats_var.set("")

        # 启动后台线程执行搜索
        button_frame = ttk.Frame(self.main_frame)

        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        self.search

        # 定期检查线程是否完成并更新UI
        self.check_search_complete(search_thread)

    def check_search_complete(self, thread):
        if thread.is_alive():
            # 如果线程仍在运行，则继续等待
            self.root.after(100, lambda: self.check_search_complete(thread))
        else:
            # 线程已完成，恢复按钮并停止进度条
            self.progress.stop()
            self.collect_button.config(state='normal')  # 修复语法错误

    def update_result_text(self, text):
        """线程安全地更新结果文本"""
        self.root.after(0, lambda: self._update_result_text_safe(text))

    def _update_result_text_safe(self, text):
        """在主线程中安全更新文本"""
        self.result_text.insert(tk.END, text)
        self.result_text.see(tk.END)

    def update_stats_label(self, text):
        """线程安全地更新统计标签"""
        self.root.after(0, lambda: self.stats_var.set(text))

    def start_collect_all_cards(self):
        """开始统计所有卡牌"""
        # 禁用按钮并启动进度条
        self.collect_button.config(state='disabled')
        self.progress.start()
        # 清空现有表格数据
        for item in self.result_table.get_children():
            self.result_table.delete(item)
        self.stats_var.set("")

        # 启动后台线程执行统计
        collect_thread = threading.Thread(target=self.collect_all_cards, args=())
        collect_thread.daemon = True
        collect_thread.start()

        # 定期检查线程是否完成并更新UI
        self.check_search_complete(collect_thread)




    def collect_all_cards(self):
        # GraphQL查询数据
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        selected_time_period = self.time_period_var.get()
        selected_min_event_size = int(self.min_event_size_var.get())
        selected_commander = self.commander_var.get()

        try:
            max_standing = int(self.standing_var.get())
        except ValueError:
            max_standing = 4
            self.standing_var.set("4")  # 重置为默认值

        data = {
            "query": None,
            "variables": {
                "commander": selected_commander,
                "showStaples": False,
                "showEntries": True,
                "showCardDetail": False,
                "sortBy": "TOP",
                "timePeriod": selected_time_period,
                "minEventSize": selected_min_event_size
            },
            "extensions": {
                "pastoria-id": "ad8859e838edd29f99ce513dae32fc1a"
            }
        }

        try:
            response = requests.post(
                "https://edhtop16.com/api/graphql",
                headers=headers,
                data=json.dumps(data),
                verify=False,
                proxies={"http": None, "https": None},
                timeout=10
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            self.update_result_text(f"请求失败: {e}\n")
            return
        except json.JSONDecodeError as e:
            self.update_result_text(f"JSON解析失败: {e}\n")
            return

        # 处理响应数据
        try:
            edges = response_data['data']['commander']['entries']['edges']
            filtered_data = [
                edge['node']['decklist']
                for edge in edges
                if edge['node']['standing'] <= max_standing
            ]
        except KeyError as e:
            self.update_result_text(f"响应数据格式错误，缺少键: {e}\n")
            return

            # 初始化卡牌计数字典
        card_counts = {}
        total_count = len(filtered_data)

        # 创建线程池，最大并发数设为10
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 提交所有任务
            future_to_url = {
                executor.submit(self.process_decklist_for_all_cards, url): url
                for url in filtered_data if url
            }

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        # 合并卡牌计数
                        for card, count in result.items():
                            card_counts[card] = card_counts.get(card, 0) + count
                except Exception as e:
                    # 使用线程安全的方法更新错误信息
                    self.root.after(0, lambda e=e, url=url: self.result_table.insert('', tk.END, values=(
                    f"处理decklist时出错 {url}", str(e), "", "")))

        # 按出现次数排序并显示结果到表格
        sorted_cards = sorted(card_counts.items(), key=lambda x: x[1], reverse=True)

        # 在主线程中更新表格
        def update_table():
            for card, count in sorted_cards:
                usage_rate = (count / total_count) * 100
                self.result_table.insert('', tk.END, values=(card, count, total_count, f"{usage_rate:.1f}%"))
            self.stats_var.set(f"总计分析套牌数: {total_count}")

        self.root.after(0, update_table)

    def process_decklist_for_all_cards(self, url):
        """处理单个decklist链接并返回所有卡牌计数"""
        if not url:
            return {}

        try:
            # 处理moxfield链接
            if "moxfield.com" in url:
                api_url = url.replace(
                    "https://www.moxfield.com/decks/",
                    "https://api2.moxfield.com/v3/decks/all/"
                )
                deck_response = requests.get(api_url,verify=False,proxies={"http": None, "https": None})
                deck_response.raise_for_status()

                deck_data = deck_response.json()
                # 统计每张卡牌的数量
                card_counts = {}
                for card_info in deck_data.get('boards', {}).get('mainboard', {}).get('cards', {}).values():
                    card_name = card_info['card']['name']
                    card_quantity = card_info['quantity']
                    card_counts[card_name] = card_counts.get(card_name, 0) + card_quantity

                for card_info in deck_data.get('boards', {}).get('commanders', {}).get('cards', {}).values():
                    card_name = card_info['card']['name']
                    card_quantity = card_info['quantity']
                    card_counts[card_name] = card_counts.get(card_name, 0) + card_quantity

                return card_counts
            else:
                # 其他网站直接获取内容
                deck_response = requests.get(url,verify=False,proxies={"http": None, "https": None})
                deck_response.raise_for_status()
                # 只提取copyDecklist函数内的文本内容
                full_content = deck_response.text

                # 查找copyDecklist函数中的内容
                start_marker = "const decklistContent = `"
                end_marker = "`;"

                start_index = full_content.find(start_marker)
                if start_index != -1:
                    start_index += len(start_marker)
                    end_index = full_content.find(end_marker, start_index)
                    if end_index != -1:
                        content = full_content[start_index:end_index]
                    else:
                        content = ""
                else:
                    content = ""

                # 解析卡牌列表 (假定格式为 "数量 卡牌名")
                card_counts = {}
                for line in content.split('\n'):
                    parts = line.strip().split(' ', 1)
                    if len(parts) == 2 and parts[0].isdigit():
                        quantity = int(parts[0])
                        card_name = parts[1]
                        card_counts[card_name] = card_counts.get(card_name, 0) + quantity
                return card_counts

        except requests.exceptions.RequestException as e:
            self.update_result_text(f"获取decklist失败 {url}: {e}\n")
            return {}
        except Exception as e:
            self.update_result_text(f"处理decklist时出错 {url}: {e}\n")
            return {}


def main():
    root = tk.Tk()
    app = CardSearchApp(root)
    root.mainloop()


if __name__ == "__main__":

    main()
