"""
国际化翻译管理器
支持中/英文切换，提供 t() 函数获取翻译文本
"""
# 导入中英文翻译字典
from . import zh, en

# 当前语言，默认中文
_current_lang = "zh"

# 语言到翻译字典的映射
_lang_map = {"zh": zh.translations, "en": en.translations}


def set_language(lang: str):
    """
    切换当前语言
    :param lang: 语言代码，"zh" 或 "en"
    """
    global _current_lang  # 声明使用全局变量
    if lang in _lang_map:
        _current_lang = lang


def get_language() -> str:
    """获取当前语言代码"""  # 返回当前语言
    return _current_lang


def t(key: str, **kwargs) -> str:
    """
    获取翻译文本
    :param key: 翻译key
    :param kwargs: 格式化参数
    :return: 翻译后的文本
    """
    # 从当前语言字典中获取翻译，找不到则fallback到中文
    text = _lang_map.get(_current_lang, zh.translations).get(key)
    if text is None:
        text = zh.translations.get(key, key)  # 中文也没有就用key本身
    if kwargs:
        text = text.format(**kwargs)  # 格式化参数替换
    return text
