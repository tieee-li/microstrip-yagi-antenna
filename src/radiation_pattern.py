# -*- coding: utf-8 -*-
"""
天线方向图生成与可视化模块
Radiation Pattern Generator & Visualizer

支持 E 面和 H 面方向图的数学建模与绘制，
包含极坐标和直角坐标系两种展示方式。

Author: Li Renqin
Date: 2026
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from typing import Optional

# 设置中文字体支持
rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False


def generate_cardioid_pattern(
    num_points: int = 360,
    directivity_db: float = 8.0,
    backlobe_db: float = -15.0,
) -> tuple:
    """
    生成类心形方向图（典型八木天线辐射模式）。

    使用修正的心形函数 + 高阶谐波模拟八木天线的定向辐射特性。

    Parameters
    ----------
    num_points : int
        角度采样点数
    directivity_db : float
        主瓣增益 (dB)，影响方向图尖锐程度
    backlobe_db : float
        后瓣电平 (dB)

    Returns
    -------
    (theta, gain_linear) : tuple of ndarray
        角度 (度) 和归一化线性增益值
    """
    theta = np.linspace(0, 2 * np.pi, num_points)
    
    # 基础心形 + 二次谐波叠加，形成更真实的八木方向图
    # directivity_db 越大，主瓣越窄
    n = max(1.0, directivity_db / 6.0)  # 方向性系数
    
    # 核心模型：心形函数的幂次形式
    cardioid = (1 - np.cos(theta)) ** n / (2 ** n)
    
    # 添加高次谐波以细化波瓣形状
    harmonic = 0.15 * np.cos(2 * theta) * np.exp(-0.5 * ((theta - np.pi) / 0.5) ** 2)
    
    # 后瓣抑制
    back_lobe = 10 ** (backlobe_db / 20)
    
    pattern = cardioid + harmonic
    
    # 后瓣区域衰减
    mask = theta > np.pi * 0.7
    pattern[mask] *= back_lobe
    
    # 归一化
    pattern = pattern / np.max(pattern)
    
    return np.degrees(theta), pattern


def generate_3d_pattern(
    resolution: int = 100,
    directivity_db: float = 8.0,
    elevation_beamwidth: float = 60.0,
    azimuth_beamwidth: float = 80.0,
) -> tuple:
    """
    生成 3D 空间辐射方向图。

    采用乘积方向图法：E面 × H面

    Parameters
    ----------
    resolution : int
        球面网格分辨率
    directivity_db : float
        最大增益 (dBi)
    elevation_bw : float
        E面波束宽度 (°)
    azimuth_bw : float
        H面波束宽度 (°)

    Returns
    -------
    (theta, phi, gain) : tuple of ndarray
        极角、方位角、增益值
    """
    theta = np.linspace(0, np.pi, resolution)   # 极角 (0~180°)
    phi = np.linspace(0, 2 * np.pi, resolution)  # 方位角 (0~360°)
    THETA, PHI = np.meshgrid(theta, phi)

    # E面（俯仰面）方向图 - 高斯近似
    sigma_e = elevation_beamwidth / 2.355 / 180 * np.pi
    e_pattern = np.exp(-((THETA - np.pi/2)**2) / (2*sigma_e**2))

    # H面（方位面）方向图 - 心形近似
    n_a = max(1.0, directivity_db / 8.0)
    h_pattern = (1 - np.cos(PHI))**n_a / (2**n_a)

    # 组合 3D 方向图
    gain = e_pattern * h_pattern
    gain = gain / np.max(gain)  # 归一化

    return THETA, PHI, gain


def plot_polar_pattern(
    ax: plt.Axes,
    theta_deg: np.ndarray,
    gain: np.ndarray,
    title: str = "天线方向图",
    color: str = "#2196F3",
    fill_alpha: float = 0.25,
    freq_mhz: Optional[float] = None,
) -> plt.Axes:
    """
    在极坐标轴上绘制方向图。

    Parameters
    ----------
    ax : matplotlib.Axes
        极坐标子图对象
    theta_deg : ndarray
        角度数组 (度)
    gain : ndarray
        归一化增益
    title : str
        图标题
    color : str
        曲线颜色
    fill_alpha : float
        填充透明度
    freq_mhz : float, optional
        频率标注

    Returns
    -------
    ax : 修改后的 Axes 对象
    """
    # 转换为 dB
    gain_db = 10 * np.log10(gain + 1e-10)

    # 绘制填充区域
    ax.fill(theta_deg, gain_db, alpha=fill_alpha, color=color)
    ax.plot(theta_deg, gain_db, color=color, linewidth=2, label="主瓣")

    # 标注关键参数
    max_idx = np.argmax(gain)
    ax.annotate(
        f"Max\n{gain_db[max_idx]:.1f} dB",
        xy=(theta_deg[max_idx], gain_db[max_idx]),
        xytext=(20, -5),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="gray"),
    )

    # -3dB 线标注
    db_3 = gain_db.max() - 3
    ax.axhline(y=db_3, color="#FF5722", linestyle="--", linewidth=1, alpha=0.7, label="-3 dB")

    # 标题和标签
    if freq_mhz is not None:
        title = f"{title} ({freq_mhz:.0f} MHz)"
    ax.set_title(title, fontsize=12, fontweight="bold", pad=20)
    ax.set_theta_zero_location("N")   # 0° 在上方
    ax.set_theta_direction(-1)       # 顺时针
    ax.legend(loc="upper right", fontsize=8)

    return ax


def plot_rectangular_pattern(
    ax: plt.Axes,
    theta_deg: np.ndarray,
    gain: np.ndarray,
    title: str = "直角坐标方向图",
    color: str = "#4CAF50",
    show_hpbw: bool = True,
) -> plt.Axes:
    """
    绘制直角坐标方向图。

    Parameters
    ----------
    ax : matplotlib.Axes
        子图对象
    theta_deg : ndarray
        角度数组 (度)，只取 -180~180 范围
    gain : ndarray
        归一化增益
    title : str
        图标题
    color : str
        曲线颜色
    show_hpbw : bool
        是否标注半功率波束宽度

    Returns
    -------
    ax : 修改后的 Axes 对象
    """
    # 取 -180 到 180 度范围
    theta_norm = np.mod(theta_deg + 180, 360) - 180
    sort_idx = np.argsort(theta_norm)
    theta_sorted = theta_norm[sort_idx]
    gain_sorted = gain[sort_idx]

    gain_db = 10 * np.log10(gain_sorted + 1e-10)

    # 绘制
    ax.plot(theta_sorted, gain_db, color=color, linewidth=2)
    ax.fill_between(theta_sorted, gain_db, min(gain_db) - 5, alpha=0.15, color=color)

    # 半功率波束宽度计算与标注
    if show_hpbw:
        peak_val = gain_db.max()
        threshold = peak_val - 3
        
        # 寻找交叉点
        above = gain_db >= threshold
        crossings = np.where(np.diff(above.astype(int)))[0]
        
        if len(crossings) >= 2:
            hpbw_left = abs(theta_sorted[crossings[0]])
            hpbw_right = abs(theta_sorted[crossings[-1]])
            hpbw = hpbw_left + hpbw_right
            
            ax.axhline(y=threshold, color="#FF9800", linestyle="--", linewidth=1, alpha=0.7)
            ax.annotate(
                f"HPBW ≈ {hpbw:.1f}°",
                xy=(0, threshold),
                xytext=(30, threshold + 3),
                fontsize=9,
                color="#FF9800",
                arrowprops=dict(arrowstyle="->", color="#FF9800"),
            )

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("角度 (°)", fontsize=10)
    ax.set_ylabel("归一化增益 (dB)", fontsize=10)
    ax.set_xlim(-180, 180)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.axvline(x=0, color="black", linewidth=0.5)

    return ax


def plot_multi_freq_patterns(
    frequencies: list,
    gains_list: list,
    colors: list = None,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    多频率方向图对比（极坐标）。

    用于展示天线在不同频点的辐射特性变化，
    如 850/900/930 MHz 三频点对比。

    Parameters
    ----------
    frequencies : list of float
        频率列表 (MHz)
    gains_list : list of ndarray
        对应的方向图数据列表
    colors : list of str, optional
        颜色列表
    save_path : str, optional
        图片保存路径

    Returns
    -------
    fig : matplotlib Figure
    """
    n = len(frequencies)
    if colors is None:
        default_colors = ["#E53935", "#43A047", "#1E88E5", "#8E24AA", "#F4511E", "#00ACC1"]
        colors = default_colors[:n]

    fig, axes = plt.subplots(1, n, figsize=(5*n, 5), subplot_kw={"projection": "polar"})

    if n == 1:
        axes = [axes]

    for i, (freq, gain, color) in enumerate(zip(frequencies, gains_list, colors)):
        theta, _ = generate_cardioid_pattern(directivity_db=8.0 - i*0.5)
        plot_polar_pattern(
            axes[i], theta, gain,
            title=f"{'E' if i%2==0 else 'H'}-Plane",
            color=color,
            freq_mhz=freq,
        )

    fig.suptitle("微带八木天线多频点方向图对比", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"✅ 图像已保存: {save_path}")

    return fig


def plot_s11_curve(
    freq_array: np.ndarray,
    s11_array: np.ndarray,
    threshold_db: float = -10,
    center_freq: Optional[float] = None,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    绘制 S11 回波损耗曲线。

    Parameters
    ----------
    freq_array : ndarray
        频率数组 (MHz)
    s11_array : ndarray
        S11 值数组 (dB)
    threshold_db : float
        匹配阈值线 (dB)
    center_freq : float, optional
        中心频率标注
    save_path : str, optional
        保存路径

    Returns
    -------
    fig : matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    # 主曲线
    ax.plot(freq_array, s11_array, color="#1565C0", linewidth=2, label="S₁₁ (回波损耗)")
    ax.fill_between(freq_array, s11_array, 0, where=s11_array <= threshold_db,
                     alpha=0.3, color="#4CAF50", label=f"匹配区 (<{threshold_db}dB)")

    # 阈值线
    ax.axhline(y=threshold_db, color="#F44336", linestyle="--", linewidth=1.5,
               label=f"阈值 ({threshold_db} dB)")
    ax.axhline(y=0, color="gray", linewidth=0.5)

    # 标注带宽
    below_threshold = s11_array <= threshold_db
    if np.any(below_threshold):
        idx_below = np.where(below_threshold)[0]
        f_low = freq_array[idx_below[0]]
        f_high = freq_array[idx_below[-1]]
        bw = f_high - f_low
        ax.annotate(
            f"工作带宽: {bw:.1f} MHz\n({f_low:.0f} ~ {f_high:.0f} MHz)",
            xy=((f_low+f_high)/2, threshold_db - 2),
            fontsize=10, ha="center", color="#2E7D32", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8F5E9", edgecolor="#4CAF50"),
        )
        ax.scatter([f_low, f_high], [threshold_db, threshold_db],
                    color="#F44336", zorder=5, s=60)

    # 中心频率标记
    if center_freq is not None:
        idx_center = np.argmin(np.abs(freq_array - center_freq))
        s11_at_center = s11_array[idx_center]
        ax.scatter([center_freq], [s11_at_center], color="#FF9800", zorder=6, s=80, marker="*")
        ax.annotate(
            f"f₀={center_freq:.0f}MHz\nS₁₁={s11_at_center:.1f}dB",
            xy=(center_freq, s11_at_center), xytext=(center_freq+15, s11_at_center+5),
            fontsize=9, color="#E65100",
            arrowprops=dict(arrowstyle="->", color="#FF9800"),
        )

    ax.set_xlabel("频率 (MHz)", fontsize=11)
    ax.set_ylabel("S₁₁ 回波损耗 (dB)", fontsize=11)
    ax.set_title("微带八木天线阻抗匹配特性曲线", fontsize=13, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.invert_yaxis()  # S11 向下为好

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"✅ S11 曲线已保存: {save_path}")

    return fig




if __name__ == "__main__":
    print("\n📊 天线方向图可视化演示\n")

    # 生成示例方向图
    theta, gain = generate_cardioid_pattern(directivity_db=8.0)

    # 极坐标图
    fig_polar, ax_polar = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})
    plot_polar_pattern(ax_polar, theta, gain, title="900MHz E-Plane 方向图", freq_mhz=900)

    # S11 曲线
    freq, s11 = generate_s11_curve(center_freq_mhz=900, bandwidth_mhz=70, min_s11_db=-28)
    fig_s11 = plot_s11_curve(freq, s11, center_freq=900)

    plt.show()
