r"""FaceFusion V100 资产包：界面中文化运行时补丁。

随 venv 启动自动加载（sitecustomize），做两件事，均不修改 FaceFusion 上游文件：

1. translator.get 打补丁为「中文优先、缺失时回退英文」。
   中文语言包 = 本目录下的 zh_*.json（文件名映射到模块名，见 MODULE_MAP）。

2. 懒加载补丁 gradio：把 Dropdown/CheckboxGroup/Radio 的 choices 裸值包装成
   （中文标签, 原始值）二元组——界面显示中文（如「换脸」），程序收到的仍是
   原始英文值（如 face_swapper），功能零影响。在 CHOICE_LABELS 里登记的值才
   会被翻译，模型名等专有名词保持原样，缺失自动回退原文。
   gradio 很重（导入慢），因此不在 sitecustomize 时刻导入，而是挂一个
   meta_path finder，等 gradio 被程序真正 import 后再打补丁。

坑（见仓库 PITFALLS.md #10）：sitecustomize 在 site 初始化阶段执行，
Python 3.11+ 在 site 初始化之后才把脚本目录/cwd 加入 sys.path，
因此此刻直接 import facefusion 必然 ImportError。
解法：本文件固定部署在 <FaceFusion根>\.venv\Lib\site-packages，
从 __file__ 向上三级即 FaceFusion 根目录，自行插入 sys.path 再 import。
"""
import functools
import json
import os
import sys

# 简单语言包：值 = 模块的 locale 池；None = 文件本身是 {模块名: 池} 的嵌套结构
MODULE_MAP = {
    'zh_core.json': 'facefusion',
    'zh_face_swapper.json': 'facefusion.processors.modules.face_swapper',
    'zh_face_enhancer.json': 'facefusion.processors.modules.face_enhancer',
    'zh_processors.json': None,
}

# 选项值 → 中文显示标签（仅登记需要翻译的；模型名等专名不登记即保持原文）
CHOICE_LABELS = {
    # ---- 处理器（截图里的那一排） ----
    'face_swapper': '换脸',
    'face_enhancer': '脸部修复（提升清晰度）',
    'frame_enhancer': '画面增强（提升分辨率）',
    'age_modifier': '年龄修改',
    'background_remover': '背景移除',
    'deep_swapper': '深度换脸（名人模型）',
    'expression_restorer': '表情还原',
    'face_debugger': '人脸调试（开发用）',
    'face_editor': '人脸编辑（表情/头姿）',
    'frame_colorizer': '画面上色（黑白转彩色）',
    'lip_syncer': '口型同步',
    'voice_extractor': '人声分离',
    # ---- 执行后端 ----
    'cpu': 'CPU（不用显卡，慢）',
    'cuda': 'CUDA（NVIDIA 显卡，推荐）',
    'tensorrt': 'TensorRT（NVIDIA 极速）',
    'rocm': 'ROCm（AMD 显卡）',
    'migraphx': 'MIGraphX（AMD 显卡）',
    'coreml': 'CoreML（Apple 芯片）',
    'openvino': 'OpenVINO（Intel 核显/CPU）',
    'qnn': 'QNN（高通芯片）',
    'directml': 'DirectML（微软通用）',
    # ---- 模型下载源 ----
    'github': 'GitHub（国外源）',
    'huggingface': 'HuggingFace（含国内镜像，推荐）',
    # ---- 人脸检测 / 关键点 ----
    'many': '自动（推荐）',
    'retinaface': 'RetinaFace',
    'scrfd': 'SCRFD',
    'yolo_face': 'YoloFace',
    'yunet': 'YuNet',
    '2dfan4': '2DFAN4（68 点）',
    'hrffa': 'HrFFA（半脸）',
    'peppa_wutz': 'Peppa（68 点）',
    # ---- 人脸筛选 ----
    'auto': '自动',
    'none': '无',
    'female': '女性',
    'male': '男性',
    'white': '白人',
    'black': '黑人',
    'latino': '拉丁裔',
    'asian': '亚裔',
    'indian': '印度裔',
    'arabic': '阿拉伯裔',
    'one': '单张人脸',
    'reference': '参考人脸',
    'left-right': '从左到右',
    'right-left': '从右到左',
    'top-bottom': '从上到下',
    'bottom-top': '从下到上',
    'small-large': '从小到大',
    'large-small': '从大到小',
    'best-worst': '最清晰优先',
    'worst-best': '最模糊优先',
    # ---- 人脸蒙版 ----
    'box': '边框蒙版（基础）',
    'occlusion': '遮挡检测（推荐，手挡脸不穿帮）',
    'area': '区域蒙版',
    'region': '分区蒙版（精细）',
    'upper-face': '上半脸',
    'lower-face': '下半脸',
    'mouth': '嘴部',
    'skin': '皮肤',
    'left-eyebrow': '左眉',
    'right-eyebrow': '右眉',
    'left-eye': '左眼',
    'right-eye': '右眼',
    'glasses': '眼镜',
    'nose': '鼻子',
    'upper-lip': '上唇',
    'lower-lip': '下唇',
    # ---- 检测旋转角度 ----
    0: '不旋转',
    90: '旋转 90°',
    180: '旋转 180°',
    270: '旋转 270°',
    # ---- 显存 / 工作流策略 ----
    'strict': '严格（最稳，不爆显存）',
    'moderate': '适中（推荐）',
    'tolerant': '宽松（更快，吃显存）',
    'memory': '内存优先（更快）',
    'disk': '磁盘优先（更省内存）',
    # ---- 临时帧格式 ----
    'jpeg': 'JPEG（快，推荐）',
    'jpg': 'JPG（快）',
    'bmp': 'BMP（较快）',
    'png': 'PNG（无损，较慢）',
    'tiff': 'TIFF',
    # ---- 视频编码器 ----
    'libx264': 'H.264（兼容性最好，推荐）',
    'libx264rgb': 'H.264 RGB',
    'libx265': 'H.265（体积更小）',
    'libvpx-vp9': 'VP9（WebM）',
    'h264_nvenc': 'H.264 NVIDIA 硬件编码',
    'hevc_nvenc': 'H.265 NVIDIA 硬件编码',
    'h264_amf': 'H.264 AMD 硬件编码',
    'hevc_amf': 'H.265 AMD 硬件编码',
    'h264_qsv': 'H.264 Intel 硬件编码',
    'hevc_qsv': 'H.265 Intel 硬件编码',
    'h264_videotoolbox': 'H.264 Apple 硬件编码',
    'hevc_videotoolbox': 'H.265 Apple 硬件编码',
    'rawvideo': '原始视频（未压缩）',
    # ---- 音频编码器 ----
    'aac': 'AAC（通用，推荐）',
    'flac': 'FLAC（无损）',
    'libmp3lame': 'MP3',
    'libopus': 'Opus',
    'libvorbis': 'Vorbis',
    'pcm_s16le': 'PCM 16 位（无损）',
    'pcm_s32le': 'PCM 32 位（无损）',
    # ---- 视频质量/速度预设 ----
    'ultrafast': '最快（文件大）',
    'superfast': '超快',
    'veryfast': '很快',
    'faster': '较快',
    'fast': '快',
    'medium': '均衡（推荐）',
    'slow': '慢',
    'slower': '较慢',
    'veryslow': '最慢（文件小）',
    # ---- 日志级别 ----
    'error': '仅错误',
    'warn': '警告及以上',
    'info': '信息（推荐）',
    'debug': '调试（最详细）',
    # ---- 界面工作流 ----
    'instant_runner': '快速出片',
    'job_runner': '运行任务',
    'job_manager': '管理任务',
    # ---- 任务状态 ----
    'drafted': '草稿',
    'queued': '排队中',
    'completed': '已完成',
    'failed': '已失败',
    # ---- 任务操作 ----
    'job-create': '新建任务',
    'job-submit': '提交任务',
    'job-delete': '删除任务',
    'job-add-step': '添加步骤',
    'job-remix-step': '混编步骤',
    'job-insert-step': '插入步骤',
    'job-remove-step': '移除步骤',
    'job-run': '运行',
    'job-run-all': '运行全部',
    'job-retry': '重试',
    'job-retry-all': '重试全部',
    # ---- 预览模式 ----
    'default': '默认',
    'frame-by-frame': '逐帧查看',
    'face-by-face': '逐脸查看',
    # ---- 摄像头模式 ----
    'inline': '内联播放',
    'udp': 'UDP 串流',
    'v4l2': 'V4L2（Linux）',
}

_ERR_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sitecustomize_err.log')


def _zh_choice_label(value):
    if value in CHOICE_LABELS:
        return CHOICE_LABELS[value]
    text = str(value)
    return CHOICE_LABELS.get(text, text)


def _wrap_choices(choices):
    if not isinstance(choices, (list, tuple)):
        return choices
    wrapped = []
    for item in choices:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            # 已是 (标签, 值) 形式：只翻译标签
            wrapped.append((_zh_choice_label(item[1]), item[1]))
        else:
            wrapped.append((_zh_choice_label(item), item))
    return wrapped


def _patch_gradio_module(gr_module):
    for cls_name in ('Dropdown', 'CheckboxGroup', 'Radio'):
        cls = getattr(gr_module, cls_name, None)
        if cls is None or getattr(cls, '_ff_zh_patched', False):
            continue
        original_init = cls.__init__

        def make_patched(original_init):
            # functools.wraps 至关重要：gradio 的 Block.get_config 用
            # inspect.signature(cls.__init__) 的参数名决定哪些属性进 /config，
            # 包装函数必须对外呈现原始签名，否则 label/choices 会从界面消失
            @functools.wraps(original_init)
            def patched_init(instance, *args, **kwargs):
                if 'choices' in kwargs:
                    kwargs['choices'] = _wrap_choices(kwargs['choices'])
                original_init(instance, *args, **kwargs)
            return patched_init

        cls.__init__ = make_patched(original_init)
        cls._ff_zh_patched = True


def _install_gradio_patch():
    if 'gradio' in sys.modules:
        _patch_gradio_module(sys.modules['gradio'])
        return
    import importlib.util

    class _GradioPatchFinder:
        _resolving = False

        def find_spec(self, fullname, path=None, target=None):
            if fullname != 'gradio' or self._resolving:
                return None
            self._resolving = True
            try:
                spec = importlib.util.find_spec('gradio')
            finally:
                self._resolving = False
            if spec is None or spec.loader is None:
                return None
            original_exec_module = spec.loader.exec_module

            def exec_module(module):
                original_exec_module(module)
                _patch_gradio_module(module)

            spec.loader.exec_module = exec_module
            return spec

    sys.meta_path.insert(0, _GradioPatchFinder())


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
            if not os.path.isfile(path):
                continue
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            if module_name is None:
                # 嵌套格式：{模块名: 池}
                for mod, pool in data.items():
                    _POOLS[mod] = pool
            else:
                _POOLS[module_name] = data

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
    _install_gradio_patch()

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
