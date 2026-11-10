r"""FaceFusion V100 资产包：界面中文化运行时补丁。

随 venv 启动自动加载（sitecustomize），把 translator.get 打补丁为
「中文优先、缺失时回退英文」，不修改 FaceFusion 上游任何文件。
中文语言包 = 本目录下的 zh_*.json（文件名映射到模块名，见 MODULE_MAP）。

坑（见仓库 PITFALLS.md #10）：sitecustomize 在 site 初始化阶段执行，
Python 3.11+ 在 site 初始化之后才把脚本目录/cwd 加入 sys.path，
因此此刻直接 import facefusion 必然 ImportError。
解法：本文件固定部署在 <FaceFusion根>\.venv\Lib\site-packages，
从 __file__ 向上三级即 FaceFusion 根目录，自行插入 sys.path 再 import。
"""
import json
import os
import sys

MODULE_MAP = {
    'zh_core.json': 'facefusion',
    'zh_face_swapper.json': 'facefusion.processors.modules.face_swapper',
    'zh_face_enhancer.json': 'facefusion.processors.modules.face_enhancer',
}

_ERR_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sitecustomize_err.log')

try:
    _sp_dir = os.path.dirname(os.path.abspath(__file__))

    def _find_ff_root():
        # 首选：site-packages → Lib → .venv → <FaceFusion根>（install.ps1 的部署位置）
        candidates = [os.path.dirname(os.path.dirname(os.path.dirname(_sp_dir)))]
        # 兜底：当前工作目录（StartFaceFusion.bat 启动时会 cd 到 FaceFusion 根）
        candidates.append(os.getcwd())
        for root in candidates:
            if os.path.isfile(os.path.join(root, 'facefusion', '__init__.py')):
                return root
        return None

    _ff_root = _find_ff_root()
    if _ff_root is None:
        raise ImportError('facefusion root not found from sitecustomize')
    if _ff_root not in sys.path:
        sys.path.insert(0, _ff_root)

    import facefusion.translator as _translator

    _POOLS = {}

    def _load_pools():
        for file_name, module_name in MODULE_MAP.items():
            path = os.path.join(_sp_dir, file_name)
            if os.path.isfile(path):
                with open(path, encoding='utf-8') as f:
                    _POOLS[module_name] = json.load(f)

    _load_pools()

    def _walk(pool, notation):
        current = pool
        for fragment in notation.split('.'):
            if isinstance(current, dict) and fragment in current:
                current = current[fragment]
            else:
                return None
        return current if isinstance(current, str) else None

    _original_get = _translator.get

    def _get(notation, module_name='facefusion'):
        pool = _POOLS.get(module_name)
        if pool is not None:
            value = _walk(pool, notation)
            if value is not None:
                return value
        return _original_get(notation, module_name)

    _translator.get = _get

    # 成功后清掉历史调试日志，避免误导
    if os.path.isfile(_ERR_LOG):
        try:
            os.remove(_ERR_LOG)
        except OSError:
            pass
except Exception:
    # 补丁失败不阻塞程序，界面退回英文；真实异常落盘便于排查
    import traceback
    try:
        with open(_ERR_LOG, 'w', encoding='utf-8') as _f:
            _f.write(traceback.format_exc())
    except Exception:
        pass
