"""流式增量里的控制标记。上游改写整段时不能再拼到已有正文后面。"""

FULL_REPLACE_PREFIX = "\x00FULL\x00"
