import os
import streamlit.components.v1 as components

_RELEASE = True

if not _RELEASE:
    # 适用开发环境：npm run start 启动
    _component_func = components.declare_component(
        "frontend_dashboard",
        url="http://localhost:3001",
    )
else:
    # 适用生产环境：使用打包好的静态文件库
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    _component_func = components.declare_component("frontend_dashboard", path=parent_dir)

def st_dashboard_grid(total_stats, files_data, key=None):
    """
    渲染首页的工作台卡片聚合仪表盘
    Args:
        total_stats: dict 包含全局总体的 {total, pass, fail, pending}
        files_data: list of dict [{"filename", "timestamp", "total", "pass", "fail", "pending"}]
    Returns:
        用户点击的 filename，如果没点则是 None
    """
    component_value = _component_func(
        total_stats=total_stats,
        files_data=files_data,
        key=key,
        default=None
    )
    return component_value
