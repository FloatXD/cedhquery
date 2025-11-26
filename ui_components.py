import tkinter as tk
from tkinter import ttk

def create_main_analysis_tab(notebook, app):
    """创建主分析页面（原功能）"""
    app.main_tab = ttk.Frame(app.notebook)
    app.notebook.add(app.main_tab, text="套牌统计分析")

    app.main_tab.columnconfigure(0, weight=1)
    app.main_tab.rowconfigure(4, weight=1)  # 表格所在行

    # 查询参数框架
    params_frame = ttk.LabelFrame(app.main_tab, text="查询参数", padding="5")
    params_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
    params_frame.columnconfigure(1, weight=1)

    # Commander选择部分
    ttk.Label(params_frame, text="指挥官:").grid(row=0, column=0, sticky=tk.W, pady=2)
    app.commander_var = tk.StringVar()
    app.commander_combo = ttk.Combobox(params_frame, textvariable=app.commander_var, width=50)
    app.commander_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)

    # 异步加载指挥官列表
    app.load_commanders_async()

    # Time Period选择
    ttk.Label(params_frame, text="时间范围:").grid(row=1, column=0, sticky=tk.W, pady=2)
    app.time_period_var = tk.StringVar(value="THREE_MONTHS")
    time_period_combo = ttk.Combobox(params_frame, textvariable=app.time_period_var,
                                     values=["ONE_MONTH", "THREE_MONTHS", "SIX_MONTHS", "ONE_YEAR"],
                                     state="readonly", width=20)
    time_period_combo.grid(row=1, column=1, sticky=tk.W, pady=2)

    # Min Event Size显示
    ttk.Label(params_frame, text="最小赛事规模:").grid(row=2, column=0, sticky=tk.W, pady=2)
    app.min_event_size_var = tk.StringVar(value="60")
    min_event_size_combo = ttk.Combobox(params_frame, textvariable=app.min_event_size_var,
                                        values=["32", "60", "100"],
                                        state="readonly", width=20)
    min_event_size_combo.grid(row=2, column=1, sticky=tk.W, pady=2)

    # Standing范围输入
    ttk.Label(params_frame, text="排名范围(≤):").grid(row=3, column=0, sticky=tk.W, pady=2)
    app.standing_var = tk.StringVar(value="4")
    standing_entry = ttk.Entry(params_frame, textvariable=app.standing_var, width=20)
    standing_entry.grid(row=3, column=1, sticky=tk.W, pady=2)

    # 统计所有卡牌按钮
    app.collect_button = ttk.Button(app.main_tab, text="统计所有卡牌", command=app.start_collect_all_cards)
    app.collect_button.grid(row=1, column=0, columnspan=2, pady=10)

    # 进度条
    app.progress = ttk.Progressbar(app.main_tab, mode='indeterminate')
    app.progress.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    # 结果显示区域 - 使用表格
    ttk.Label(app.main_tab, text="卡牌统计结果:").grid(row=3, column=0, sticky=tk.W, pady=(10, 5))

    # 创建表格框架
    table_frame = ttk.Frame(app.main_tab)
    table_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
    app.main_tab.rowconfigure(4, weight=1)

    # 创建Treeview表格
    columns = ('卡牌名称', '出现次数', '总套牌数', '出现率')
    app.result_table = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)

    app.sort_column = None
    app.sort_reverse = False

    # 定义表头
    for col in columns:
        app.result_table.heading(col, text=col, command=lambda c=col: app.sort_by_column(c))
        app.result_table.column(col, width=150, anchor='center')

    # 创建滚动条
    scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=app.result_table.yview)
    scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=app.result_table.xview)
    app.result_table.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

    # 布局表格和滚动条
    app.result_table.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
    scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))

    table_frame.columnconfigure(0, weight=1)
    table_frame.rowconfigure(0, weight=1)

    # 统计信息
    app.stats_var = tk.StringVar()
    app.stats_label = ttk.Label(app.main_tab, textvariable=app.stats_var)
    app.stats_label.grid(row=5, column=0, columnspan=2, pady=5)

    # 在统计信息标签下方添加作者信息
    app.author_label = ttk.Label(app.main_tab, text="@云玩家阿天", foreground="gray")
    app.author_label.grid(row=6, column=1, sticky=tk.E, pady=(5, 0))


def create_card_usage_tab(notebook, app):
    """创建卡牌使用率查询页面"""
    app.usage_tab = ttk.Frame(app.notebook)
    app.notebook.add(app.usage_tab, text="卡牌使用率查询")

    app.usage_tab.columnconfigure(0, weight=1)
    app.usage_tab.rowconfigure(4, weight=1)  # 表格所在行

    # 查询参数框架
    usage_params_frame = ttk.LabelFrame(app.usage_tab, text="查询设置", padding="5")
    usage_params_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
    usage_params_frame.columnconfigure(1, weight=1)

    # 卡牌名称输入
    ttk.Label(usage_params_frame, text="卡牌名称:").grid(row=0, column=0, sticky=tk.W, pady=2)
    app.usage_card_name_var = tk.StringVar()
    app.usage_card_name_entry = ttk.Entry(usage_params_frame, textvariable=app.usage_card_name_var, width=50)
    app.usage_card_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)

    # 时间范围选择
    ttk.Label(usage_params_frame, text="时间范围:").grid(row=1, column=0, sticky=tk.W, pady=2)
    app.usage_time_period_var = tk.StringVar(value="THREE_MONTHS")
    usage_time_period_combo = ttk.Combobox(usage_params_frame, textvariable=app.usage_time_period_var,
                                           values=["ONE_MONTH", "THREE_MONTHS", "SIX_MONTHS", "ONE_YEAR"],
                                           state="readonly", width=20)
    usage_time_period_combo.grid(row=1, column=1, sticky=tk.W, pady=2)

    # 最小赛事规模
    ttk.Label(usage_params_frame, text="最小赛事规模:").grid(row=2, column=0, sticky=tk.W, pady=2)
    app.usage_min_event_size_var = tk.StringVar(value="60")
    usage_min_event_size_combo = ttk.Combobox(usage_params_frame, textvariable=app.usage_min_event_size_var,
                                              values=["32", "60", "100"],
                                              state="readonly", width=20)
    usage_min_event_size_combo.grid(row=2, column=1, sticky=tk.W, pady=2)

    # 排名范围输入
    ttk.Label(usage_params_frame, text="排名范围(≤):").grid(row=3, column=0, sticky=tk.W, pady=2)
    app.usage_standing_var = tk.StringVar(value="4")
    usage_standing_entry = ttk.Entry(usage_params_frame, textvariable=app.usage_standing_var, width=20)
    usage_standing_entry.grid(row=3, column=1, sticky=tk.W, pady=2)

    # 查询按钮
    app.usage_search_button = ttk.Button(app.usage_tab, text="查询使用率", command=app.start_usage_search)
    app.usage_search_button.grid(row=1, column=0, columnspan=2, pady=10)

    # 进度条
    app.usage_progress = ttk.Progressbar(app.usage_tab, mode='indeterminate')
    app.usage_progress.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    # 结果显示区域 - 使用表格
    ttk.Label(app.usage_tab, text="使用率统计结果:").grid(row=3, column=0, sticky=tk.W, pady=(10, 5))

    # 创建表格框架
    usage_table_frame = ttk.Frame(app.usage_tab)
    usage_table_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
    app.usage_tab.rowconfigure(4, weight=1)

    # 创建Treeview表格（针对使用率查询优化列标题）
    usage_columns = ('指挥官', '使用套牌数', '总套牌数', '使用率')
    app.usage_result_table = ttk.Treeview(usage_table_frame, columns=usage_columns, show='headings', height=20)

    app.usage_sort_column = None
    app.usage_sort_reverse = False

    # 定义表头
    for col in usage_columns:
        app.usage_result_table.heading(col, text=col, command=lambda c=col: app.sort_usage_by_column(c))
        app.usage_result_table.column(col, width=150, anchor='center')

    # 创建滚动条
    usage_scrollbar_y = ttk.Scrollbar(usage_table_frame, orient=tk.VERTICAL, command=app.usage_result_table.yview)
    usage_scrollbar_x = ttk.Scrollbar(usage_table_frame, orient=tk.HORIZONTAL,
                                      command=app.usage_result_table.xview)
    app.usage_result_table.configure(yscrollcommand=usage_scrollbar_y.set, xscrollcommand=usage_scrollbar_x.set)

    # 布局表格和滚动条
    app.usage_result_table.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    usage_scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
    usage_scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))

    usage_table_frame.columnconfigure(0, weight=1)
    usage_table_frame.rowconfigure(0, weight=1)

    # 统计信息
    app.usage_stats_var = tk.StringVar()
    app.usage_stats_label = ttk.Label(app.usage_tab, textvariable=app.usage_stats_var)
    app.usage_stats_label.grid(row=5, column=0, columnspan=2, pady=5)