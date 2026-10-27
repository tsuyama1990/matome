from collections.abc import Mapping
from types import MappingProxyType

READINGS: Mapping[str, str] = MappingProxyType(
    {
        "km/h": "キロメートル毎時",
        "m/s": "メートル毎秒",
        "CO2": "シーオーツー",
        "pH": "ペーハー",
        "kg": "キログラム",
        "%": "パーセント",
        "％": "パーセント",
        "℃": "度",
        "㎞": "キロメートル",
        "㎝": "センチメートル",
        "㎜": "ミリメートル",
        "㎏": "キログラム",
        "㎡": "平方メートル",
        "㎥": "立方メートル",
    }
)
