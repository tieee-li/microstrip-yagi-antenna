# -*- coding: utf-8 -*-
"""
微带八木天线参数计算模块
Microstrip Yagi-Uda Antenna Parameter Calculator

基于经典天线理论，提供微带八木天线的核心物理参数计算。
适用于 GSM-R 频段 (850~930 MHz) 及其他 UHF 频段设计。

Author: Li Renqin
Date: 2026
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ============================================================
# 物理常数
# ============================================================
C = 299_792_458  # 光速 (m/s)


@dataclass
class Substrate:
    """介质基板参数"""
    epsilon_r: float = 4.4   # 相对介电常数 (FR-4 典型值)
    thickness: float = 1.6   # 厚度 (mm)
    loss_tangent: float = 0.02  # 损耗角正切

    @property
    def effective_permittivity(self) -> float:
        """有效介电常数（简化模型）"""
        er = self.epsilon_r
        return (er + 1) / 2 + ((er - 1) / 2) * (1 / np.sqrt(1 + 12 * self.thickness))

    def wavelength_in_substrate(self, freq_hz: float) -> float:
        """基板中的波长 (m)"""
        return C / (freq_hz * np.sqrt(self.effective_permittivity))


@dataclass
class YagiElement:
    """单个八木振子单元"""
    name: str           # 名称：driven(激励), director(引向器), reflector(反射器)
    length: float       # 长度 (mm)
    width: float        # 宽度/间距 (mm)
    position: float     # 到激励单元的距离 (mm)


@dataclass
class AntennaDesignResult:
    """天线设计结果数据类"""
    frequency: float                    # 工作频率 (MHz)
    free_space_wavelength: float        # 自由空间波长 (mm)
    substrate_wavelength: float         # 基板波长 (mm)
    driven_element: YagiElement         # 激励单元
    reflector: Optional[YagiElement]    # 反射器
    directors: List[YagiElement] = field(default_factory=list)  # 引向器列表
    estimated_gain: float = 0.0          # 预估增益 (dBi)
    estimated_fbr: float = 0.0           # 预估前后比 (dB)

    def summary(self) -> str:
        """生成设计摘要文本"""
        lines = [
            f"{'='*55}",
            f"  微带八木天线设计方案 | f = {self.frequency:.1f} MHz",
            f"{'='*55}",
            f"",
            f"  波长信息:",
            f"    自由空间波长 λ₀ = {self.free_space_wavelength:.1f} mm",
            f"    基板波长      λg ≈ {self.substrate_wavelength:.1f} mm",
            f"",
            f"  振子参数:",
            f"    ┌─ 激励单元: L={self.driven_element.length:.1f} mm, W={self.driven_element.width:.1f} mm",
        ]
        if self.reflector:
            lines.append(
                f"    ├─ 反 射 器: L={self.reflector.length:.1f} mm, d={self.reflector.position:.1f} mm"
            )
        for i, d in enumerate(self.directors):
            lines.append(
                f"    ├─ 引向器 {i+1}: L={d.length:.1f} mm, d={d.position:.1f} mm"
            )
        lines.extend([
            f"",
            f"  性能预估:",
            f"    增益 G ≈ {self.estimated_gain:.1f} dBi",
            f"    前后比 F/B ≈ {self.estimated_fbr:.1f} dB",
            f"{'='*55}",
        ])
        return "\n".join(lines)


def calculate_yagi_antenna(
    frequency_mhz: float,
    num_directors: int = 3,
    substrate: Optional[Substrate] = None,
    custom_scale: float = 1.0,
) -> AntennaDesignResult:
    """
    计算微带八木天线的全部几何参数。

    Parameters
    ----------
    frequency_mhz : float
        中心工作频率 (MHz)
    num_directors : int
        引向器数量 (默认 3)
    substrate : Substrate, optional
        介质基板参数，默认使用 FR-4
    custom_scale : float
        自定义缩放因子 (用于微调)

    Returns
    -------
    AntennaDesignResult
        完整的天线设计结果
    """
    if substrate is None:
        substrate = Substrate()

    freq_hz = frequency_mhz * 1e6

    # ---- 基本波长计算 ----
    lambda_0 = C / freq_hz * 1000  # 自由空间波长 (mm)
    lambda_g = substrate.wavelength_in_substrate(freq_hz) * 1000  # 基板波长 (mm)

    # 经典八木天线尺寸比例 (基于 λ/2 谐振原理 + 微带修正)
    # 这些比例来自文献中的经验公式和仿真优化结果

    scale = custom_scale

    # 驱动元件（半波偶极子等效）—— 微带结构需要缩短 ~5%
    driven_len = 0.47 * lambda_0 * scale
    driven_width = 0.02 * lambda_0 * scale  # 线宽

    # 反射器 —— 比驱动元件长约 5~10%，位于驱动元件后方约 λ/4
    reflector_len = 0.52 * lambda_0 * scale
    reflector_pos = 0.22 * lambda_0  # 距离驱动元件的距离

    # 引向器阵列 —— 逐个缩短，间距约 0.13λ~0.15λ
    directors = []
    for i in range(num_directors):
        # 引向器长度递减：从 0.44λ 逐渐减小到 0.40λ
        ratio = 0.44 - i * 0.012
        dir_len = max(ratio * lambda_0 * scale, 0.38 * lambda_0)

        # 间距：第一个较近，后续稍远
        if i == 0:
            dir_pos = 0.16 * lambda_0
        else:
            dir_pos = directors[-1].position + 0.14 * lambda_0

        directors.append(YagiElement(
            name=f"director_{i+1}",
            length=round(dir_len, 2),
            width=round(driven_width, 2),
            position=round(dir_pos, 2),
        ))

    # ---- 性能预估（经验公式）----
    # 增益与振子数量的近似关系: G ≈ 4.5 + 2.0 * log10(N)，其中 N 为总振子数
    total_elements = 2 + num_directors  # 驱动 + 反射 + 引向器
    estimated_gain = 4.5 + 2.0 * np.log10(total_elements)

    # 前后比：反射器和引向器的数量影响
    estimated_fbr = 8.0 + 1.5 * num_directors

    result = AntennaDesignResult(
        frequency=frequency_mhz,
        free_space_wavelength=round(lambda_0, 2),
        substrate_wavelength=round(lambda_g, 2),
        driven_element=YagiElement("driven", round(driven_len, 2), round(driven_width, 2), 0),
        reflector=YagiElement("reflector", round(reflector_len, 2), 0, round(reflector_pos, 2)),
        directors=directors,
        estimated_gain=round(estimated_gain, 1),
        estimated_fbr=round(estimated_fbr, 1),
    )

    return result


def calculate_frequency_bandwidth(
    center_freq_mhz: float,
    s11_threshold_db: float = -10.0,
    relative_bw_percent: float = 8.0,
) -> Tuple[float, float, float]:
    """
    根据中心频率估算工作带宽。

    Parameters
    ----------
    center_freq_mhz : float
        中心频率 (MHz)
    s11_threshold_db : float
        S11 阈值 (dB)，默认 -10 dB
    relative_bw_percent : float
        相对带宽百分比 (%)

    Returns
    -------
    tuple (f_low, f_high, bandwidth_mhz)
        带宽下限、上限、带宽大小
    """
    bw = center_freq_mhz * relative_bw_percent / 100
    f_low = center_freq_mhz - bw / 2
    f_high = center_freq_mhz + bw / 2
    return round(f_low, 1), round(f_high, 1), round(bw, 1)


def microstrip_line_impedance(
    width_mm: float,
    substrate_thickness_mm: float,
    epsilon_r: float,
) -> float:
    """
    计算微带线的特性阻抗（Hammerstad-Jensen 公式简化版）。

    Parameters
    ----------
    width_mm : float
        导体宽度 (mm)
    substrate_thickness_mm : float
        基板厚度 (mm)
    epsilon_r : float
        相对介电常数

    Returns
    -------
    float
        特性阻抗 (Ω)
    """
    w = width_mm
    h = substrate_thickness_mm
    er = epsilon_r
    u = w / h

    if u <= 1:
        z0 = (60 / np.sqrt((er + 1) / 2)) * np.log(8 / u + 0.25 * u)
    else:
        z0 = (120 * np.pi) / (
            np.sqrt(er) *
            (u + 1.393 + 0.667 * np.log(u + 1.444))
        )
    return round(z0, 2)


def generate_s11_curve(
    center_freq_mhz: float,
    bandwidth_mhz: float,
    min_s11_db: float = -25.0,
    num_points: int = 500,
    noise_level: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成模拟的 S11 回波损耗曲线。

    使用高斯型谐振曲线模拟天线的回波损耗特性，
    并叠加小幅随机噪声使曲线更真实。

    Parameters
    ----------
    center_freq_mhz : float
        中心频率 (MHz)
    bandwidth_mhz : float
        带宽 (MHz)
    min_s11_db : float
        最小回波损耗深度 (dB)
    num_points : int
        采样点数
    noise_level : float
        噪声幅度

    Returns
    -------
    (freq_array, s11_array) : tuple of ndarray
        频率数组 (MHz) 和 S11 值数组 (dB)
    """
    # 频率范围：中心频率 ±30%带宽
    span = bandwidth_mhz * 3
    freq = np.linspace(center_freq_mhz - span, center_freq_mhz + span, num_points)

    # 高斯型谐振曲线
    sigma = bandwidth_mhz / 2.355  # 将带宽转换为高斯标准差
    s11 = min_s11_db * np.exp(-0.5 * ((freq - center_freq_mhz) / sigma) ** 2)

    # 叠加噪声
    rng = np.random.default_rng(seed=42)
    s11 += rng.normal(0, noise_level, size=num_points)

    # 限制在合理范围内
    s11 = np.clip(s11, -40, 0)

    return freq, s11


if __name__ == "__main__":
    # 快速测试
    print("\n📡 微带八木天线设计工具 - 参数计算演示\n")

    design = calculate_yagi_antenna(frequency_mhz=900, num_directors=3)
    print(design.summary())

    # 带宽估算
    fl, fh, bw = calculate_frequency_bandwidth(900)
    print(f"\n  工作频段: {fl:.1f} ~ {fh:.1f} MHz (带宽 {bw:.1f} MHz)")

    # 微带线阻抗
    z0 = microstrip_line_impedance(width_mm=3.0, substrate_thickness_mm=1.6, epsilon_r=4.4)
    print(f"\n  微带线特性阻抗 Z₀ ≈ {z0} Ω")
