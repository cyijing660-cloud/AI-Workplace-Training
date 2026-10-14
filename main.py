import streamlit as st
import yt_dlp
import os
import time
import re
import whisper
from openai import OpenAI
from dotenv import load_dotenv
import tempfile
import shutil

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(page_title="AI高情商职场对话训练｜真实老板", layout="wide")

# 自定义 CSS 样式
st.markdown("""
<style>
    /* 全局深色背景 */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding: 1.5rem 1rem;
    }
    
    /* 聊天气泡容器 - 居中并限制宽度 */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 1rem;
    }
    
    /* 老板气泡 - 深灰蓝色 */
    .chat-bubble-boss {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d4a6f 100%);
        border-radius: 18px 18px 18px 4px;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0;
        box-shadow: 0 4px 12px rgba(30, 58, 95, 0.4);
        max-width: 80%;
        color: #e2e8f0;
    }
    
    /* 用户气泡 - 明亮蓝色 */
    .chat-bubble-user {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        border-radius: 18px 18px 4px 18px;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
        max-width: 80%;
        color: white;
    }
    
    /* 气泡容器对齐 */
    .bubble-wrapper-boss {
        display: flex;
        justify-content: flex-start;
    }
    
    .bubble-wrapper-user {
        display: flex;
        justify-content: flex-end;
    }
    
    /* 头像样式 */
    .avatar {
        width: 40px;
        height: 40px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        margin: 0 0.75rem;
        flex-shrink: 0;
    }
    
    .avatar-boss {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    }
    
    .avatar-user {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    
    /* 正在输入动画 */
    .typing-indicator {
        display: flex;
        gap: 4px;
        padding: 1rem 1.25rem;
    }
    
    .typing-dot {
        width: 8px;
        height: 8px;
        background: #94a3b8;
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dot:nth-child(1) { animation-delay: 0s; }
    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }
    
    @keyframes typing {
        0%, 60%, 100% { transform: translateY(0); opacity: 0.6; }
        30% { transform: translateY(-8px); opacity: 1; }
    }
    
    /* 按钮样式优化 */
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
    }
    
    /* 输入框样式 */
    [data-testid="stChatInput"] textarea {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 16px !important;
        color: white !important;
    }
    
    [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(255, 255, 255, 0.4) !important;
    }
    
    /* 标题和文本颜色 */
    h1, h2, h3, h4, h5, h6 {
        color: #f1f5f9 !important;
    }
    
    p, div, span {
        color: #cbd5e1;
    }
    
    /* 侧边栏标题 */
    .sidebar-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* 场景信息栏 */
    .scene-header {
        background: rgba(30, 58, 95, 0.4);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 16px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
    }
    
    /* 评分面板 */
    .score-panel {
        background: rgba(30, 58, 95, 0.3);
        border: 1px solid rgba(251, 191, 36, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    
    /* 折叠面板优化 */
    [data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
    }
    
    /* 文件上传区域 */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 2px dashed rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
    }
    
    /* 文本区域 */
    textarea, input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: white !important;
    }
    
    textarea::placeholder, input::placeholder {
        color: rgba(255, 255, 255, 0.4) !important;
    }
    
    /* 单选按钮 */
    .stRadio > div {
        gap: 0.5rem;
    }
    
    .stRadio label {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stRadio label:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(59, 130, 246, 0.3);
    }
    
    /* 分割线 */
    hr {
        border-color: rgba(255, 255, 255, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# 初始化大模型客户端
@st.cache_resource
def get_llm_client():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        st.error("❌ 未找到DEEPSEEK_API_KEY！请检查.env文件")
        st.stop()
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

# 初始化Whisper语音转文字模型 - 懒加载
def get_whisper_model():
    @st.cache_resource
    def _load_model():
        return whisper.load_model("base")
    return _load_model()

client = get_llm_client()
whisper_model = None

# 初始化会话状态
if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = None
if 'cleaned_text' not in st.session_state:
    st.session_state.cleaned_text = None
if 'current_case' not in st.session_state:
    st.session_state.current_case = 0
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'training_started' not in st.session_state:
    st.session_state.training_started = False
if 'score_done' not in st.session_state:
    st.session_state.score_done = False
if 'score_result' not in st.session_state:
    st.session_state.score_result = ""
if 'temp_files' not in st.session_state:
    st.session_state.temp_files = []
if 'is_typing' not in st.session_state:
    st.session_state.is_typing = False

# ------------------------------
# 视频处理 + AI文字清洗
# ------------------------------
def download_douyin_video(url):
    temp_dir = tempfile.mkdtemp()
    st.session_state.temp_files.append(temp_dir)
    ydl_opts = {
        "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),
        "format": "bestaudio[ext=m4a]/best[ext=mp4]",
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return os.path.join(temp_dir, f"{info['id']}.{info['ext']}")

def video_to_text(video_path):
    global whisper_model
    if whisper_model is None:
        whisper_model = get_whisper_model()
    result = whisper_model.transcribe(video_path, language="zh")
    raw_text = result["text"]
    clean_prompt = f"""
    整理这段抖音职场教学文案：修正语序、删废话口头禅杂音，精简通顺，只保留对话案例与沟通技巧
    原文：{raw_text}
    """
    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": clean_prompt}],
                                         temperature=0.1)
    return res.choices[0].message.content

# ------------------------------
# AI解析案例
# ------------------------------
def parse_video_content(video_text):
    prompt = f"""
    严格JSON输出，字段固定：
    {{
      "total_cases": 案例数,
      "cases": [
        {{
          "scene":"一句话职场场景",
          "principles":["沟通原则1","原则2"],
          "wrong_reply":"错误回复",
          "correct_reply":"标准回复",
          "scoring_criteria":{{"态度得体":35,"逻辑清晰":35,"解决问题":30}}
        }}
      ]
    }}
    内容：{video_text}
    """
    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}],
                                         temperature=0.1, response_format={"type": "json_object"})
    import json
    raw = json.loads(res.choices[0].message.content)
    parsed_data = {"total_cases": raw.get("total_cases", len(raw.get("cases", []))), "cases": []}
    for c in raw.get("cases", []):
        safe_case = {
            "scene": c.get("scene", "职场沟通场景"),
            "principles": c.get("principles", ["礼貌得体，不卑不亢"]),
            "wrong_reply": c.get("wrong_reply", "直接拒绝、情绪化、顶撞上级"),
            "correct_reply": c.get("correct_reply", "兼顾情绪，积极应对，情商在线"),
            "scoring_criteria": c.get("scoring_criteria", {"态度得体": 35, "逻辑清晰": 35, "解决问题": 30})
        }
        parsed_data["cases"].append(safe_case)
    return parsed_data

# ------------------------------
# 真实老板对话（带情绪识别）+ 强制完整打分
# ------------------------------
def start_boss_chat(case):
    scene = case.get("scene", "职场日常对话")
    prompt = f"""
    你是现实公司真实老板，性格正常，有脾气、有威严，不是机器。
    场景：{scene}，自然口语开场，直接说一句老板会说的话。
    """
    return client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}],
                                          temperature=0.9).choices[0].message.content

def boss_reply(user_msg, chat_history, case):
    """核心：识别用户情绪，用户侮辱/顶撞/阴阳，老板立刻生气、严肃、施压"""
    scene = case["scene"]
    principles = case["principles"]
    history_str = "\n".join([f"{i['role']}:{i['content']}" for i in chat_history])
    prompt = f"""
    你是真实职场老板，有威严、会生气、会冷淡、会施压，**绝对不要一直温和客气**。
    场景：{scene}
    员工历史对话：{history_str}
    员工最新这句话：{user_msg}

    规则：
    1. 如果员工【顶撞、阴阳、嘲讽、侮辱、不尊重、怼老板】：你立刻**严肃、生气、冷淡、施压、反问、指出问题**，语气强硬
    2. 如果员工正常沟通：正常老板语气
    3. 简短口语，符合真实老板说话方式，不要书面化，直接输出一句话
    """
    return client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}],
                                          temperature=0.95).choices[0].message.content

def full_score_after_chat(chat_history, case):
    """强制完整打分，不漏项"""
    scene = case["scene"]
    correct = case["correct_reply"]
    criteria = case["scoring_criteria"]
    user_all_msgs = "\n".join([f"- {i['content']}" for i in chat_history if i["role"] == "user"])

    prompt = f"""
    严格综合打分，必须输出完整格式，不能省略！
    场景：{scene}
    标准高情商沟通方式：{correct}
    评分维度：{criteria}
    员工所有对话内容：
    {user_all_msgs}

    输出固定格式：
    总分：XX分
    优点：
    -
    不足：
    -
    改进建议：
    -
    """
    return client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}],
                                          temperature=0.2).choices[0].message.content

# ------------------------------
# 渲染自定义聊天气泡
# ------------------------------
def render_chat_bubble(role, content, is_typing=False):
    if is_typing:
        st.markdown(f"""
        <div class="bubble-wrapper-boss">
            <div class="avatar avatar-boss">👔</div>
            <div class="chat-bubble-boss">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        if role == "boss":
            st.markdown(f"""
            <div class="bubble-wrapper-boss">
                <div class="avatar avatar-boss">👔</div>
                <div class="chat-bubble-boss">{content}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="bubble-wrapper-user">
                <div class="chat-bubble-user">{content}</div>
                <div class="avatar avatar-user">👤</div>
            </div>
            """, unsafe_allow_html=True)

# ------------------------------
# 侧边栏
# ------------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-title">🎯 内容导入</div>', unsafe_allow_html=True)
    
    input_mode = st.radio("选择导入方式", ["本地视频文件", "抖音视频链接", "直接粘贴视频文案"], label_visibility="collapsed")
    
    uploaded_file = None
    video_url = ""
    video_text = None

    if input_mode == "抖音视频链接":
        video_url = st.text_input("输入抖音视频链接", placeholder="https://www.douyin.com/...")
    elif input_mode == "本地视频文件":
        uploaded_file = st.file_uploader("上传本地视频", type=["mp4", "mov", "avi"], label_visibility="collapsed")
    else:
        video_text = st.text_area("粘贴视频文案/字幕", height=180, placeholder="在此粘贴视频文案或字幕内容...")
        if video_text:
            st.session_state.extracted_text = video_text
            clean_prompt = f"整理通顺精简：{video_text}"
            st.session_state.cleaned_text = \
            client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": clean_prompt}],
                                           temperature=0.1).choices[0].message.content

    if st.button("✨ 提取文字+AI清洗", use_container_width=True, type="primary"):
        if input_mode == "本地视频文件" and uploaded_file:
            temp_dir = tempfile.mkdtemp()
            st.session_state.temp_files.append(temp_dir)
            path = os.path.join(temp_dir, uploaded_file.name)
            with open(path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            with st.spinner("正在提取并清洗文字..."):
                st.session_state.extracted_text = video_to_text(path)
                st.session_state.cleaned_text = st.session_state.extracted_text
            st.success("✅ 文字处理完成！")
        elif input_mode == "抖音视频链接" and video_url:
            with st.spinner("正在下载并处理视频..."):
                st.session_state.extracted_text = video_to_text(download_douyin_video(video_url))
                st.session_state.cleaned_text = st.session_state.extracted_text
            st.success("✅ 文字处理完成！")

    if st.session_state.cleaned_text:
        st.divider()
        with st.expander("📝 AI 清洗后文字", expanded=False):
            st.text_area("", st.session_state.cleaned_text, height=200, disabled=True, label_visibility="collapsed")
        if st.button("🚀 解析场景并开始训练", type="primary", use_container_width=True):
            video_text = st.session_state.cleaned_text
            with st.spinner("正在解析职场场景..."):
                st.session_state.parsed_data = parse_video_content(video_text)
                st.session_state.current_case = 0
                st.session_state.chat_history = []
                st.session_state.training_started = True
                st.session_state.score_done = False
                st.session_state.score_result = ""
                st.rerun()

# ------------------------------
# 主对话区域
# ------------------------------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

if st.session_state.training_started and st.session_state.parsed_data:
    case = st.session_state.parsed_data["cases"][st.session_state.current_case]
    
    # 场景信息头部
    st.markdown(f"""
    <div class="scene-header">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
            <div style="flex: 1;">
                <div style="font-size: 0.875rem; color: #64748b; margin-bottom: 0.25rem;">职场场景</div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #f1f5f9;">{case['scene']}</div>
            </div>
            <div style="text-align: right; flex-shrink: 0;">
                <div style="font-size: 0.875rem; color: #64748b;">对话进度</div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #3b82f6;">
                    {len([x for x in st.session_state.chat_history if x['role'] == 'user'])}/4 轮
                </div>
            </div>
        </div>
        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.1);">
            <span style="font-size: 0.875rem; color: #94a3b8;">💡 沟通原则：</span>
            <span style="color: #e2e8f0; font-size: 0.875rem;">{'、'.join(case['principles'])}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 老板开场
    if len(st.session_state.chat_history) == 0:
        boss_msg = start_boss_chat(case)
        st.session_state.chat_history.append({"role": "boss", "content": boss_msg})

    # 渲染聊天历史
    for msg in st.session_state.chat_history:
        render_chat_bubble(msg["role"], msg["content"])
    
    # 显示正在输入动画
    if st.session_state.is_typing:
        render_chat_bubble("boss", "", is_typing=True)
    
    # 显示评分结果
    if st.session_state.score_done and st.session_state.score_result:
        st.markdown(f"""
        <div class="score-panel">
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                <span style="font-size: 1.5rem;">🏆</span>
                <span style="font-size: 1.125rem; font-weight: 700; color: #fbbf24;">本轮对话完整综合评分</span>
            </div>
            <div style="white-space: pre-line; line-height: 1.8;">{st.session_state.score_result}</div>
        </div>
        """, unsafe_allow_html=True)

    # 用户输入
    user_input = st.chat_input("回复老板...")
    if user_input and not st.session_state.score_done and not st.session_state.is_typing:
        # 立刻添加用户消息
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.is_typing = True
        st.rerun()
    
    # 处理老板回复
    if st.session_state.is_typing and not st.session_state.score_done:
        # 先渲染聊天历史 + 正在输入
        for msg in st.session_state.chat_history:
            render_chat_bubble(msg["role"], msg["content"])
        render_chat_bubble("boss", "", is_typing=True)
        
        # 获取老板回复
        last_user_msg = st.session_state.chat_history[-1]["content"]
        boss_reply_msg = boss_reply(last_user_msg, st.session_state.chat_history[:-1], case)
        
        # 添加老板回复
        st.session_state.chat_history.append({"role": "boss", "content": boss_reply_msg})
        st.session_state.is_typing = False
        
        # 检查是否需要评分
        user_rounds = len([x for x in st.session_state.chat_history if x["role"] == "user"])
        if user_rounds >= 4:
            st.session_state.score_result = full_score_after_chat(st.session_state.chat_history, case)
            st.session_state.score_done = True
        
        st.rerun()

    # 操作按钮（仅在评分后显示）
    if st.session_state.score_done:
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 重置本轮对话", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.score_done = False
                st.session_state.score_result = ""
                st.session_state.is_typing = False
                st.rerun()
        with col2:
            if st.session_state.current_case + 1 < st.session_state.parsed_data["total_cases"]:
                if st.button("➡️ 下一个场景", use_container_width=True, type="primary"):
                    st.session_state.current_case += 1
                    st.session_state.chat_history = []
                    st.session_state.score_done = False
                    st.session_state.score_result = ""
                    st.session_state.is_typing = False
                    st.rerun()

else:
    # 欢迎界面
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <div style="font-size: 4rem; margin-bottom: 1.5rem;">💼</div>
        <h1 style="font-size: 2rem; font-weight: 700; margin-bottom: 0.75rem;">AI真实老板·多轮职场对话训练</h1>
        <p style="color: #94a3b8; font-size: 1rem; max-width: 500px; margin: 0 auto;">
            在左侧导入视频或文案，AI将解析职场场景并模拟真实老板与您对话
        </p>
        <div style="margin-top: 2rem; display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
            <div style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 12px; padding: 1rem 1.5rem;">
                <div style="font-weight: 600; color: #60a5fa;">📹 视频导入</div>
            </div>
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 12px; padding: 1rem 1.5rem;">
                <div style="font-weight: 600; color: #34d399;">🎭 真实对话</div>
            </div>
            <div style="background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.2); border-radius: 12px; padding: 1rem 1.5rem;">
                <div style="font-weight: 600; color: #fbbf24;">📊 AI 评分</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------
# 清理临时文件
# ------------------------------
def cleanup():
    for f in st.session_state.get("temp_files", []):
        try:
            if os.path.isdir(f):
                shutil.rmtree(f, ignore_errors=True)
            else:
                os.remove(f)
        except:
            pass

import atexit

atexit.register(cleanup)
