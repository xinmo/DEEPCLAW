"""测试 shell 工具输入显示修复"""
import sys
sys.path.insert(0, r'c:\Users\WLX\Desktop\JAVISAGENT\javisagent\backend\src')

from routes.claw.chat import _normalize_tool_call_args, _normalize_tool_name

# 测试用例
test_cases = [
    # (raw_args, tool_name, expected_result)
    ('{"command": "ls -la"}', "shell", {"command": "ls -la"}),  # 正常 JSON
    ('ls -la', "shell", {"command": "ls -la"}),  # 纯命令字符串
    ('python --version', "bash", {"command": "python --version"}),  # bash 工具
    ('', "shell", None),  # 空字符串
    (None, "shell", None),  # None
    ('ls -la', "read_file", None),  # 非 shell 工具
]

print("测试 _normalize_tool_call_args 函数修复：\n")
for i, (raw_args, tool_name, expected) in enumerate(test_cases, 1):
    result = _normalize_tool_call_args(raw_args, tool_name)
    status = "✓" if result == expected else "✗"
    print(f"测试 {i}: {status}")
    print(f"  输入: raw_args={repr(raw_args)}, tool_name={repr(tool_name)}")
    print(f"  期望: {expected}")
    print(f"  实际: {result}")
    print()
