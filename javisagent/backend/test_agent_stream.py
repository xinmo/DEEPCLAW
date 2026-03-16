import asyncio
import sys
sys.path.insert(0, 'src')

from src.services.claw import create_claw_agent

async def test():
    agent = create_claw_agent(
        working_directory=r'C:\Users\WLX\Desktop\testclaw',
        llm_model='deepseek-chat'
    )

    input_data = {'messages': [{'role': 'user', 'content': '你好'}]}

    print('Starting stream...')
    count = 0
    async for chunk in agent.astream(input_data, stream_mode=['messages']):
        count += 1
        print(f'\n=== Chunk {count} ===')
        print(f'Chunk type: {type(chunk)}')

        if isinstance(chunk, tuple) and len(chunk) >= 2:
            stream_mode, data = chunk[0], chunk[1]
            print(f'Stream mode: {stream_mode}')
            print(f'Data type: {type(data).__name__}')
            print(f'Data: {data}')

            # data 可能是 tuple (message,) 或直接是 message
            if isinstance(data, tuple) and len(data) > 0:
                message = data[0]
                print(f'Message type: {type(message).__name__}')

                if hasattr(message, 'content'):
                    print(f'Has content: {bool(message.content)}')
                    if message.content:
                        print(f'Content: {message.content[:200]}')

                if hasattr(message, 'tool_calls'):
                    print(f'Has tool_calls: {bool(message.tool_calls)}')
            else:
                if hasattr(data, 'content'):
                    print(f'Has content: {bool(data.content)}')
                    if data.content:
                        print(f'Content: {data.content[:200]}')

        if count >= 10:  # 看前10个 chunk
            break

    print(f'\nTotal chunks: {count}')

if __name__ == '__main__':
    asyncio.run(test())
