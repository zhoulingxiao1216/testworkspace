import os
import streamlit.components.v1 as components

_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "frontend_tree",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    _component_func = components.declare_component("frontend_tree", path=parent_dir)


def st_execution_tree(tree_data, selected_id=None, stats_dict=None, key=None):
    """
    渲染执行页面左侧的原生树状折叠导航模块
    """
    component_value = _component_func(
        tree_data=tree_data,
        selected_id=selected_id,
        stats_dict=stats_dict,
        key=key,
        default=None
    )
    return component_value
