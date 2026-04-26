"""
可视化模块：车辆路径图 + 排班甘特图
用法：
    from visualize import plot_routes, plot_schedule, plot_all
    plot_all(solution, customer_pool)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def _minutes_to_hhmm(minutes):
    """将分钟数转换为 HH:MM 字符串"""
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h:02d}:{m:02d}"


def plot_routes(solution, customer_pool, ax=None, show=True):
    """
    绘制车辆路径地图。
    每条路径用不同颜色的箭头线段表示，配送中心用红色五角星标注。
    
    :param solution: Solution 对象
    :param customer_pool: dict {customer_id: Customer}
    :param ax: matplotlib Axes，若为 None 则自动创建
    :param show: 是否立即显示
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 12))

    # 配色：按路径数均匀分配颜色
    n_routes = len(solution.routes)
    colors = cm.tab20(np.linspace(0, 1, max(n_routes, 1)))

    # 画所有客户点（灰色小圆）
    for cid, cust in customer_pool.items():
        if cid == 0:
            continue
        ax.plot(cust.x, cust.y, 'o', color='#cccccc', markersize=4, zorder=1)
        ax.text(cust.x + 0.3, cust.y + 0.3, str(cid),
                fontsize=5, color='#999999', zorder=2)

    # 画配送中心（红色五角星）
    depot = customer_pool.get(0)
    if depot:
        ax.plot(depot.x, depot.y, '*', color='red', markersize=18, zorder=10,
                label='配送中心')
        ax.text(depot.x + 0.5, depot.y + 0.5, '配送中心',
                fontsize=9, color='red', fontweight='bold', zorder=11)

    # 画每条路径
    for r_idx, route in enumerate(solution.routes):
        color = colors[r_idx % len(colors)]
        nodes = route.nodes
        xs = [customer_pool[n].x for n in nodes if n in customer_pool]
        ys = [customer_pool[n].y for n in nodes if n in customer_pool]

        # 画路径线段（带箭头）
        for i in range(len(xs) - 1):
            ax.annotate(
                '', xy=(xs[i+1], ys[i+1]), xytext=(xs[i], ys[i]),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.2),
                zorder=5
            )

        # 画途经客户点（彩色）
        for j, n in enumerate(nodes[1:-1], 1):
            if n in customer_pool:
                c = customer_pool[n]
                ax.plot(c.x, c.y, 'o', color=color, markersize=6, zorder=6)

        # 标注路径序号（在第一个客户旁）
        if len(xs) > 2:
            mid_x = xs[1]
            mid_y = ys[1]
            v_label = f"V{route.vehicle.vehicle_id}"
            ax.text(mid_x, mid_y + 0.8, v_label, fontsize=6,
                    color=color, fontweight='bold', zorder=7)

    ax.set_title(f'车辆路径图  (共 {n_routes} 条路径，总费用={solution.total_cost:.1f})',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('X (km)', fontsize=10)
    ax.set_ylabel('Y (km)', fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.set_aspect('equal', adjustable='box')

    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_schedule(solution, ax=None, show=True):
    """
    绘制车辆排班甘特图。
    横轴：时间（分钟 → HH:MM），纵轴：车辆 ID。
    每段任务用彩色矩形块表示，颜色区分电车/油车。
    
    :param solution: Solution 对象
    :param ax: matplotlib Axes，若为 None 则自动创建
    :param show: 是否立即显示
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(16, max(6, len(solution.vehiclesTimeTable) * 0.35 + 2)))

    # 收集所有有任务的车辆
    used_vehicle_ids = sorted(solution.vehiclesTimeTable.keys())
    if not used_vehicle_ids:
        ax.text(0.5, 0.5, '没有排班数据', ha='center', va='center',
                transform=ax.transAxes, fontsize=14)
        if show:
            plt.show()
        return ax

    # 车辆 ID → 车型（从 solution.routes 反查）
    vid_to_type = {}
    for route in solution.routes:
        vid_to_type[route.vehicle.vehicle_id] = route.vehicle.type_id

    # 颜色：电车（type 4,5）蓝色系，油车（type 1,2,3）橙色系
    def get_color(type_id):
        palette_ev = ['#4e9af1', '#7ec8e3', '#0d47a1']
        palette_fv = ['#f4a261', '#e76f51', '#c0392b']
        if type_id in [4, 5]:
            return palette_ev[(type_id - 4) % len(palette_ev)]
        return palette_fv[(type_id - 1) % len(palette_fv)]

    y_positions = {vid: i for i, vid in enumerate(used_vehicle_ids)}
    bar_height = 0.6

    for vid in used_vehicle_ids:
        tasks = solution.vehiclesTimeTable[vid]
        t_id = vid_to_type.get(vid, 1)
        color = get_color(t_id)
        y = y_positions[vid]

        for (t_start, t_end) in tasks:
            duration = max(t_end - t_start, 1)  # 防止时长为 0
            ax.barh(y, duration, left=t_start, height=bar_height,
                    color=color, edgecolor='white', linewidth=0.5, alpha=0.85)
            # 在矩形上标注时间（若宽度足够）
            if duration > 30:
                ax.text(t_start + duration / 2, y,
                        f"{_minutes_to_hhmm(t_start)}-{_minutes_to_hhmm(t_end)}",
                        ha='center', va='center', fontsize=5.5, color='white',
                        fontweight='bold')

    # 纵轴标注
    ax.set_yticks(list(y_positions.values()))
    ax.set_yticklabels([f"车辆{vid}" for vid in used_vehicle_ids], fontsize=7)
    ax.invert_yaxis()

    # 横轴：按时间段打刻度
    tick_minutes = list(range(0, 1441, 60))
    ax.set_xticks(tick_minutes)
    ax.set_xticklabels([_minutes_to_hhmm(m) for m in tick_minutes],
                       rotation=45, fontsize=7)
    ax.set_xlim(420, 1440)  # 显示 7:00 ~ 24:00

    # 标注高峰时段背景色
    for (s, e, label) in [(420, 540, '早高峰'), (1020, 1140, '晚高峰')]:
        ax.axvspan(s, e, alpha=0.08, color='red', label=label)

    ax.set_xlabel('时间', fontsize=10)
    ax.set_ylabel('车辆', fontsize=10)
    ax.set_title(f'车辆排班甘特图  (共使用 {len(used_vehicle_ids)} 辆车)',
                 fontsize=13, fontweight='bold')
    ax.grid(axis='x', linestyle='--', alpha=0.4)

    # 图例
    ev_patch = mpatches.Patch(color='#4e9af1', label='新能源车 (type4/5)')
    fv_patch = mpatches.Patch(color='#f4a261', label='燃油车 (type1/2/3)')
    peak_patch = mpatches.Patch(color='red', alpha=0.15, label='高峰时段')
    ax.legend(handles=[ev_patch, fv_patch, peak_patch],
              loc='upper right', fontsize=8)

    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_all(solution, customer_pool, save_path=None):
    """
    一次性绘制路径图 + 排班甘特图（上下布局）。
    
    :param solution: Solution 对象
    :param customer_pool: dict {customer_id: Customer}
    :param save_path: 若指定则保存为图片，否则直接弹窗显示
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 22))

    plot_routes(solution, customer_pool, ax=ax1, show=False)
    plot_schedule(solution, ax=ax2, show=False)

    fig.suptitle('ALNS 优化结果可视化', fontsize=16, fontweight='bold', y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.99])

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
    else:
        plt.show()


def plot_from_txt(path='solution_output.txt'):
    """
    直接从 txt 文件读取解数据并弹出交互窗口，无需 Solution 对象或 Excel 文件。
    """
    from save_solution import load_solution_txt
    data = load_solution_txt(path)

    meta = data['meta']
    customers_dict = data['customers']   # {cid: {'x', 'y', 'tw'}}
    routes_list = data['routes']         # list of route dicts

    print(f"[读取成功] 路径数={len(routes_list)}, 总费用={meta.get('total_cost', 'N/A'):.2f}")

    fig1, ax1 = plt.subplots(figsize=(14, 12))
    fig1.canvas.manager.set_window_title('车辆路径图')

    # ── 路径图 ──────────────────────────────────────────────────
    n_routes = len(routes_list)
    colors = cm.tab20(np.linspace(0, 1, max(n_routes, 1)))

    # 画所有客户点（灰色）
    for cid, c in customers_dict.items():
        if cid == 0:
            continue
        ax1.plot(c['x'], c['y'], 'o', color='#cccccc', markersize=4, zorder=1)
        ax1.text(c['x'] + 0.3, c['y'] + 0.3, str(cid), fontsize=5, color='#aaaaaa', zorder=2)

    # 画配送中心
    depot = customers_dict.get(0)
    if depot:
        ax1.plot(depot['x'], depot['y'], '*', color='red', markersize=18, zorder=10, label='配送中心')
        ax1.text(depot['x'] + 0.5, depot['y'] + 0.5, '配送中心',
                 fontsize=9, color='red', fontweight='bold', zorder=11)

    # 画每条路径
    for r_idx, route in enumerate(routes_list):
        color = colors[r_idx % len(colors)]
        nodes = route.get('nodes', [])
        xs = [customers_dict[n]['x'] for n in nodes if n in customers_dict]
        ys = [customers_dict[n]['y'] for n in nodes if n in customers_dict]
        for i in range(len(xs) - 1):
            ax1.annotate('', xy=(xs[i+1], ys[i+1]), xytext=(xs[i], ys[i]),
                         arrowprops=dict(arrowstyle='->', color=color, lw=1.0), zorder=5)
        for n in nodes[1:-1]:
            if n in customers_dict:
                ax1.plot(customers_dict[n]['x'], customers_dict[n]['y'],
                         'o', color=color, markersize=5, zorder=6)
        if len(xs) > 2:
            ax1.text(xs[1], ys[1] + 0.8, f"V{route.get('vehicle_id', r_idx)}",
                     fontsize=5.5, color=color, fontweight='bold', zorder=7)

    ax1.set_title(f"车辆路径图  (共 {n_routes} 条路径，总费用={meta.get('total_cost', 0):.1f})",
                  fontsize=13, fontweight='bold')
    ax1.set_xlabel('X (km)'); ax1.set_ylabel('Y (km)')
    ax1.grid(True, linestyle='--', alpha=0.4)
    ax1.set_aspect('equal', adjustable='box')
    fig1.tight_layout()

    # ── 排班甘特图（第二个独立窗口）───────────────────────────────
    # 从路径数据重建车辆时间段
    vid_tasks = {}   # {vehicle_id: [(start, end), ...]}
    vid_type  = {}   # {vehicle_id: type_id}
    for route in routes_list:
        vid = route.get('vehicle_id')
        t_id = route.get('vehicle_type', 1)
        times = route.get('times', [])
        if vid is None or len(times) < 2:
            continue
        vid_tasks.setdefault(vid, []).append((times[0], times[-1]))
        vid_type[vid] = t_id

    used_vids = sorted(vid_tasks.keys())
    fig2, ax2 = plt.subplots(figsize=(16, max(6, len(used_vids) * 0.3 + 2)))
    fig2.canvas.manager.set_window_title('车辆排班甘特图')
    if not used_vids:
        ax2.text(0.5, 0.5, '没有排班数据', ha='center', va='center',
                 transform=ax2.transAxes, fontsize=14)
    else:
        def get_color(type_id):
            return '#4e9af1' if type_id in [4, 5] else '#f4a261'

        y_pos = {vid: i for i, vid in enumerate(used_vids)}
        for vid in used_vids:
            color = get_color(vid_type.get(vid, 1))
            for (t_start, t_end) in vid_tasks[vid]:
                dur = max(t_end - t_start, 1)
                ax2.barh(y_pos[vid], dur, left=t_start, height=0.6,
                         color=color, edgecolor='white', linewidth=0.5, alpha=0.85)
                if dur > 30:
                    ax2.text(t_start + dur / 2, y_pos[vid],
                             f"{_minutes_to_hhmm(t_start)}-{_minutes_to_hhmm(t_end)}",
                             ha='center', va='center', fontsize=5, color='white', fontweight='bold')

        ax2.set_yticks(list(y_pos.values()))
        ax2.set_yticklabels([f"车辆{v}" for v in used_vids], fontsize=6)
        ax2.invert_yaxis()
        ticks = list(range(0, 1441, 60))
        ax2.set_xticks(ticks)
        ax2.set_xticklabels([_minutes_to_hhmm(m) for m in ticks], rotation=45, fontsize=7)
        ax2.set_xlim(420, 1440)
        for s, e in [(420, 540), (1020, 1140)]:
            ax2.axvspan(s, e, alpha=0.07, color='red')
        ax2.grid(axis='x', linestyle='--', alpha=0.4)
        ax2.set_xlabel('时间'); ax2.set_ylabel('车辆')
        ax2.set_title(f'车辆排班甘特图  (共使用 {len(used_vids)} 辆车)', fontsize=13, fontweight='bold')

        import matplotlib.patches as mpatches
        ax2.legend(handles=[
            mpatches.Patch(color='#4e9af1', label='新能源车'),
            mpatches.Patch(color='#f4a261', label='燃油车'),
            mpatches.Patch(color='red', alpha=0.15, label='高峰时段'),
        ], loc='upper right', fontsize=8)

    fig2.suptitle('ALNS 优化结果可视化', fontsize=14, fontweight='bold')
    fig2.tight_layout()
    plt.show()  # 两个窗口同时阻塞显示


# ── 独立运行入口 ────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    txt_path = sys.argv[1] if len(sys.argv) > 1 else 'solution_output.txt'
    plot_from_txt(txt_path)

