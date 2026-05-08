# -*- coding: utf-8 -*-
"""
演示脚本：生成示例图表并保存
Demo Script: Generate sample plots for preview
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from src.antenna_calculator import (
    calculate_yagi_antenna,
    calculate_frequency_bandwidth,
    generate_s11_curve,
)
from src.radiation_pattern import (
    generate_cardioid_pattern,
    plot_polar_pattern,
    plot_rectangular_pattern,
    plot_s11_curve,
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(output_dir, exist_ok=True)

    print("📡 正在生成示例图表...")

    # 1. 900MHz 设计计算
    design = calculate_yagi_antenna(frequency_mhz=900, num_directors=3)
    print(design.summary())

    # 2. 极坐标方向图 (E-Plane)
    theta, gain = generate_cardioid_pattern(directivity_db=design.estimated_gain)
    fig_p, ax_p = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})
    plot_polar_pattern(ax_p, theta, gain, title="E-Plane Polar Pattern", freq_mhz=900)
    fig_p.savefig(os.path.join(output_dir, "polar_pattern.png"), dpi=150, bbox_inches="tight")
    plt.close(fig_p)
    print("  ✅ polar_pattern.png")

    # 3. 直角坐标方向图 (H-Plane)
    fig_r, ax_r = plt.subplots(figsize=(9, 4))
    plot_rectangular_pattern(ax_r, theta, gain, title="H-Plane Rectangular (900 MHz)")
    fig_r.savefig(os.path.join(output_dir, "rectangular_pattern.png"), dpi=150, bbox_inches="tight")
    plt.close(fig_r)
    print("  ✅ rectangular_pattern.png")

    # 4. S11 曲线
    fl, fh, bw = calculate_frequency_bandwidth(900)
    freq, s11 = generate_s11_curve(center_freq_mhz=900, bandwidth_mhz=bw, min_s11_db=-28)
    fig_s11 = plot_s11_curve(freq, s11, center_freq=900)
    fig_s11.savefig(os.path.join(output_dir, "s11_curve.png"), dpi=150, bbox_inches="tight")
    plt.close(fig_s11)
    print("  ✅ s11_curve.png")

    # 5. 多频点对比图
    fig_multi, axes = plt.subplots(
        1, 3, figsize=(15, 5), subplot_kw={"projection": "polar"}
    )
    colors = ["#E53935", "#43A047", "#1E88E5"]
    for i, (f, c) in enumerate(zip([850, 900, 930], colors)):
        t, g = generate_cardioid_pattern(directivity_db=8.0 - i*0.3)
        plot_polar_pattern(axes[i], t, g, title=f"{f} MHz", color=c)

    fig_multi.suptitle("Multi-Frequency Radiation Pattern Comparison", fontsize=14, fontweight="bold")
    fig_multi.savefig(os.path.join(output_dir, "multi_freq_compare.png"),
                      dpi=150, bbox_inches="tight")
    plt.close(fig_multi)
    print("  ✅ multi_freq_compare.png")

    # 6. 组合预览图（用于 README）
    fig_preview, ax_preview = plt.subplots(figsize=(12, 6), subplot_kw={"projection": "polar"})
    t_final, g_final = generate_cardioid_pattern(directivity_db=design.estimated_gain)
    plot_polar_pattern(
        ax_preview, t_final, g_final,
        title="Microstrip Yagi Antenna\n900 MHz | G≈7.6 dBi",
        color="#1565C0",
    )
    fig_preview.savefig(os.path.join(output_dir, "preview.png"),
                        dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig_preview)
    print("  ✅ preview.png")

    print("\n🎉 所有图表已生成到 assets/ 目录！")


if __name__ == "__main__":
    main()
