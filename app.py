# -*- coding: utf-8 -*-
"""
微带八木天线设计与分析工具 - Web 交互界面
Microstrip Yagi Antenna Design Toolkit (Streamlit App)

基于 Streamlit 框架构建的交互式 Web 应用，
支持天线参数自动计算、方向图可视化、S11 分析等功能。

运行方式: streamlit run app.py

Author: Li Renqin
Date: 2026
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from src.antenna_calculator import (
    calculate_yagi_antenna,
    calculate_frequency_bandwidth,
    microstrip_line_impedance,
    generate_s11_curve,
    Substrate,
)
from src.radiation_pattern import (
    generate_cardioid_pattern,
    plot_polar_pattern,
    plot_rectangular_pattern,
    plot_s11_curve,
)

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="微带八木天线设计工具",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 样式注入
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1a237e, #0d47a1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa, #e8ecf1);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)


def render_sidebar():
    """渲染侧边栏参数面板"""
    st.sidebar.header("⚙️ 设计参数")

    # 频率参数
    st.sidebar.subheader("📻 频率设置")
    freq = st.sidebar.slider(
        "中心工作频率 (MHz)",
        min_value=400, max_value=2400, value=900, step=10,
        help="GSM-R 频段典型值: 850~930 MHz"
    )

    # 天线结构参数
    st.sidebar.subheader("🏗️ 天线结构")
    num_directors = st.sidebar.selectbox(
        "引向器数量", [1, 2, 3, 4, 5], index=2,
        help="更多引向器 → 更高增益但尺寸更大"
    )

    scale = st.sidebar.slider(
        "尺寸缩放因子",
        min_value=0.90, max_value=1.10, value=1.00, step=0.01,
        help="用于微调整体尺寸（<1 缩小，>1 放大）"
    )

    # 介质基板参数
    st.sidebar.subheader("📋 介质基板")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        er = st.number_input("介电常数 εᵣ", value=4.4, step=0.1,
                             help="FR-4 ≈ 4.4, Rogers ≈ 2.2~10.2")
    with col2:
        h = st.number_input("厚度 h (mm)", value=1.6, step=0.1)

    return {
        "frequency": freq,
        "num_directors": num_directors,
        "scale": scale,
        "substrate": Substrate(epsilon_r=er, thickness=h),
    }


def main():
    """主应用入口"""

    # ---- 页头 ----
    st.markdown('<div class="main-header">📡 微带八木天线设计工具</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Microstrip Yagi-Uda Antenna Design & Analysis Toolkit | '
        '面向 GSM-R 铁路移动通信场景</div>', unsafe_allow_html=True
    )
    st.divider()

    params = render_sidebar()

    # ---- 计算设计结果 ----
    design = calculate_yagi_antenna(
        frequency_mhz=params["frequency"],
        num_directors=params["num_directors"],
        substrate=params["substrate"],
        custom_scale=params["scale"],
    )

    fl, fh, bw = calculate_frequency_bandwidth(params["frequency"])

    # ---- 结果概览卡片 ----
    st.subheader("📊 设计结果总览")
    c1, c2, c3, c4, c5 = st.columns(5)
    
    c1.metric("中心频率", f"{design.frequency} MHz", delta="工作频段")
    c2.metric("自由空间波长", f"{design.free_space_wavelength:.1f} mm")
    c3.metric("预估增益", f"{design.estimated_gain:.1f} dBi", delta="↑ 高定向性")
    c4.metric("前后比", f"{design.estimated_fbr:.1f} dB", delta="↑ 良好的前后抑制")
    c5.metric("工作带宽", f"{bw:.1f} MHz", f"{fl:.0f} ~ {fh:.0f} MHz")

    # ---- 详细参数表格 ----
    st.subheader("📐 几何参数详情")

    tab1, tab2, tab3 = st.tabs(["振子参数表", "文本报告", "S₁₁ 阻抗匹配"])

    with tab1:
        # 振子数据表格
        element_data = []
        element_data.append({
            "元件": "激励单元 (Driven)", 
            "长度(mm)": f"{design.driven_element.length:.2f}",
            "宽度(mm)": f"{design.driven_element.width:.2f}",
            "位置(mm)": "参考原点",
            "类型": "λ/2 谐振"
        })
        if design.reflector:
            element_data.append({
                "元件": "反射器 (Reflector)",
                "长度(mm)": f"{design.reflector.length:.2f}",
                "宽度(mm)": "-",
                "位置(mm)": f"后 {design.reflector.position:.2f}",
                "类型": "~1.05λ/2"
            })
        for i, d in enumerate(design.directors):
            element_data.append({
                "元件": f"引向器 D{i+1} (Director)",
                "长度(mm)": f"{d.length:.2f}",
                "宽度(mm)": f"{d.width:.2f}",
                "位置(mm)": f"前 {d.position:.2f}",
                "类型": "递减长度"
            })

        st.dataframe(element_data, use_container_width=True, hide_index=True)

    with tab2:
        st.code(design.summary(), language="text")

    with tab3:
        # S11 分析
        s11_freq, s11_val = generate_s11_curve(
            center_freq_mhz=params["frequency"],
            bandwidth_mhz=bw,
            min_s11_db=-28 + params["num_directors"] * 2,
        )

        fig_s11 = plot_s11_curve(s11_freq, s11_val, threshold_db=-10,
                                  center_freq=params["frequency"])
        st.pyplot(fig_s11)
        
        # 微带线阻抗
        z0 = microstrip_line_impedance(
            width_mm=design.driven_element.width,
            substrate_thickness_mm=params["substrate"].thickness,
            epsilon_r=params["substrate"].epsilon_r,
        )
        st.info(f"💡 馈线特性阻抗 Z₀ ≈ {z0} Ω | "
                f"目标匹配阻抗: 50 Ω | 匹配偏差: {abs(z0-50)/50*100:.1f}%")

    # ---- 方向图可视化 ----
    st.subheader("🎯 辐射方向图")

    theta, gain = generate_cardioid_pattern(
        directivity_db=design.estimated_gain,
        backlobe_db=-design.estimated_fbr,
    )

    fig_polar, ax_polar = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})
    plot_polar_pattern(ax_polar, theta, gain,
                       title=f"E-Plane 极坐标方向图",
                       color="#1565C0", freq_mhz=params["frequency"])

    fig_rect, ax_rect = plt.subplots(figsize=(9, 4))
    plot_rectangular_pattern(ax_rect, theta, gain,
                             title=f"H-Plane 直角坐标方向图 ({params['frequency']} MHz)")

    col_left, col_right = st.columns(2)
    with col_left:
        st.pyplot(fig_polar)
    with col_right:
        st.pyplot(fig_rect)

    # ---- 多频点对比 ----
    st.subheader("🔄 多频点性能对比")

    freqs_to_compare = [
        max(400, params["frequency"] - 50),
        params["frequency"],
        min(2400, params["frequency"] + 50),
    ]

    cols_compare = st.columns(len(freqs_to_compare))
    colors_compare = ["#E53935", "#43A047", "#1E88E5"]

    for i, (freq_col, freq_val, color) in enumerate(zip(cols_compare, freqs_to_compare, colors_compare)):
        with freq_col:
            t_i, g_i = generate_cardioid_pattern(directivity_db=design.estimated_gain - abs(i-1)*0.8)
            fi, _ = plt.subplots(figsize=(4, 4), subplot_kw={"projection": "polar"})
            plot_polar_pattern(fi, t_i, g_i,
                               title="", color=color, freq_mhz=freq_val)
            st.pyplot(fi)

    # ---- 技术说明 ----
    with st.expander("ℹ️ 技术原理与使用说明"):
        st.markdown("""
        ### 🔬 设计原理
        
        本工具基于**经典八木-宇田天线理论**，结合微带天线的特点进行建模：
        
        1. **驱动元件 (Driven Element)**：采用半波偶极子结构，通过微带线馈电，
           长度约为 λ₀/2 的 94%（考虑末端效应）
        
        2. **反射器 (Reflector)**：位于驱动元件后方约 λ/4 处，长度略长于驱动元件，
           通过寄生耦合产生反向辐射，增强前向增益
        
        3. **引向器 (Director)**：位于驱动元件前方，逐个缩短并递增间距，
           引导电磁波向前传播，形成高方向性波束
        
        ### 📐 关键公式
        - 自由空间波长：`λ₀ = c / f`
        - 基板有效波长：`λg = λ₀ / √εeff`
        - 微带线特性阻抗（Hammerstad-Jensen 公式）
        - 增益估算：`G ≈ 4.5 + 2.0 × log₁₀(N)`，N 为振子总数
        
        ### ⚠️ 使用建议
        - GSM-R 频段推荐：850 / 900 / 930 MHz 三频点优化
        - 基板选择：FR-4（低成本）或 Rogers（高性能）
        - 实际加工时需预留 ±2% 尺寸公差
        - 最终参数应以 HFSS/CST 仿真验证为准
        """)
    
    # ---- 页脚 ----
    st.divider()
    st.markdown("""
    <div style='text-align:center; color:#999; font-size:0.85rem;'>
        📡 Microstrip Yagi Antenna Design Toolkit &nbsp;|&nbsp; 
        Built with ❤️ by Li Renqin &nbsp;|&nbsp; 
        南信大 · 电子信息工程 &nbsp;|&nbsp; 2026
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
