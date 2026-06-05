import google.generativeai as genai
import os
import sys



try:
    genai.configure(api_key="AIzaSyDlhWzD8UPeUGpKqHvH7g4x4Yl_44-h4rQ")
except KeyError:
    print("错误：请设置'GOOGLE_API_KEY'环境变量。")
    exit()

# 初始化模型
try:
    model = genai.GenerativeModel('gemini-2.5-pro')
except Exception as e:
    print(f"模型初始化失败，请检查API密钥或网络连接: {e}")
    exit()

chat = model.start_chat(history=[])

print("您现在可以开始与Gemini 2.5 Pro聊天了。输入 '退出' 来结束对话。")

while True:
    try:
        user_input = input("您: ")
        if user_input.lower() in ['退出', 'exit', 'quit']:
            print("再见！")
            break
        print("Gemini 正在思考中...", end="", flush=True)

        response = chat.send_message(user_input)
        print("\r" + " " * 20 + "\r", end="")

        print(f"Gemini: {response.text}")

    except KeyboardInterrupt:
        print("\n再见！")
        break
    except Exception as e:
        print("\r" + " " * 20 + "\r", end="")
        print(f"\n发生错误: {e}")
        break