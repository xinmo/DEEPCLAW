"""
测试 Claw API 路由

运行前确保：
1. 后端服务已启动: python src/main.py
2. 数据库已初始化

测试命令：
python tests/test_claw_api.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_validate_directory():
    """测试目录验证"""
    print("\n=== 测试目录验证 ===")

    # 测试有效目录
    response = requests.post(
        f"{BASE_URL}/api/claw/validate-directory",
        json={"path": "/tmp"}
    )
    print(f"验证 /tmp: {response.json()}")

    # 测试无效目录
    response = requests.post(
        f"{BASE_URL}/api/claw/validate-directory",
        json={"path": "/nonexistent"}
    )
    print(f"验证 /nonexistent: {response.json()}")


def test_list_models():
    """测试获取模型列表"""
    print("\n=== 测试获取模型列表 ===")
    response = requests.get(f"{BASE_URL}/api/claw/models")
    data = response.json()
    print(f"可用模型数量: {len(data['models'])}")
    for model in data['models']:
        print(f"  - {model['name']} ({model['model_id']}) by {model['provider']}")


def test_conversation_crud():
    """测试对话 CRUD 操作"""
    print("\n=== 测试对话 CRUD ===")

    # 1. 创建对话
    print("\n1. 创建对话")
    response = requests.post(
        f"{BASE_URL}/api/claw/conversations",
        json={
            "working_directory": "/tmp",
            "title": "测试对话",
            "llm_model": "claude-opus-4-6"
        }
    )
    if response.status_code != 200:
        print(f"创建失败: {response.text}")
        return

    conversation = response.json()
    conv_id = conversation['id']
    print(f"创建成功: ID={conv_id}, Title={conversation['title']}")

    # 2. 获取对话列表
    print("\n2. 获取对话列表")
    response = requests.get(f"{BASE_URL}/api/claw/conversations")
    conversations = response.json()
    print(f"对话总数: {len(conversations)}")

    # 3. 获取对话详情
    print("\n3. 获取对话详情")
    response = requests.get(f"{BASE_URL}/api/claw/conversations/{conv_id}")
    conversation = response.json()
    print(f"对话详情: {conversation['title']} - {conversation['working_directory']}")

    # 4. 更新对话
    print("\n4. 更新对话")
    response = requests.put(
        f"{BASE_URL}/api/claw/conversations/{conv_id}",
        json={"title": "更新后的标题"}
    )
    conversation = response.json()
    print(f"更新成功: {conversation['title']}")

    # 5. 删除对话
    print("\n5. 删除对话")
    response = requests.delete(f"{BASE_URL}/api/claw/conversations/{conv_id}")
    print(f"删除结果: {response.json()}")

    # 6. 验证删除
    print("\n6. 验证删除")
    response = requests.get(f"{BASE_URL}/api/claw/conversations/{conv_id}")
    if response.status_code == 404:
        print("删除成功，对话不存在")
    else:
        print("删除失败，对话仍然存在")


def test_invalid_directory():
    """测试无效目录创建对话"""
    print("\n=== 测试无效目录 ===")
    response = requests.post(
        f"{BASE_URL}/api/claw/conversations",
        json={
            "working_directory": "/nonexistent",
            "title": "无效对话"
        }
    )
    print(f"状态码: {response.status_code}")
    print(f"错误信息: {response.json()}")


if __name__ == "__main__":
    try:
        print("开始测试 Claw API...")

        test_validate_directory()
        test_list_models()
        test_conversation_crud()
        test_invalid_directory()

        print("\n\n✅ 所有测试完成！")

    except requests.exceptions.ConnectionError:
        print("\n❌ 错误：无法连接到服务器")
        print("请确保后端服务已启动: python src/main.py")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
