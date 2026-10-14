import os
import tempfile
import shutil
import json
import base64
from typing import List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

vl_client = None
llm_client = None
temp_files = []

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEEPSEEK_BASE = "https://api.deepseek.com"
MODEL_VL = "qwen-vl-max"
MODEL_TEXT = "deepseek-chat"

def get_vl_client():
    global vl_client
    if vl_client is None:
        dashscope_key = os.getenv("DASHSCOPE_API_KEY")
        if not dashscope_key:
            raise HTTPException(status_code=500, detail="未找到 DASHSCOPE_API_KEY，请检查环境变量")
        vl_client = OpenAI(api_key=dashscope_key, base_url=DASHSCOPE_BASE)
    return vl_client

def get_llm_client():
    global llm_client
    if llm_client is None:
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_key:
            raise HTTPException(status_code=500, detail="未找到 DEEPSEEK_API_KEY，请检查环境变量")
        llm_client = OpenAI(api_key=deepseek_key, base_url=DEEPSEEK_BASE)
    return llm_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    
    for f in temp_files:
        try:
            if os.path.isdir(f):
                shutil.rmtree(f, ignore_errors=True)
            else:
                os.remove(f)
        except:
            pass

app = FastAPI(lifespan=lifespan)

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

class Case(BaseModel):
    scene: str
    principles: List[str]
    wrong_reply: str
    correct_reply: str
    scoring_criteria: Dict[str, int]

class ParsedData(BaseModel):
    total_cases: int
    cases: List[Case]

class ChatMessage(BaseModel):
    role: str
    content: str

class BossStartRequest(BaseModel):
    case: Case
    analysis: str = ""

class BossReplyRequest(BaseModel):
    user_msg: str
    chat_history: List[ChatMessage]
    case: Case
    analysis: str = ""

class ScoreRequest(BaseModel):
    chat_history: List[ChatMessage]
    case: Case
    analysis: str = ""

class VideoAnalyzeRequest(BaseModel):
    text: str

class VideoParseRequest(BaseModel):
    text: str
    analysis: str = ""

def download_video(url: str) -> str:
    temp_dir = tempfile.mkdtemp()
    temp_files.append(temp_dir)
    ydl_opts = {
        "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),
        "format": "bestaudio[ext=m4a]/best[ext=mp4]",
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return os.path.join(temp_dir, f"{info['id']}.{info['ext']}")

def video_to_text(video_path: str) -> str:
    client = get_vl_client()
    with open(video_path, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    ext = os.path.splitext(video_path)[1].lower()
    mime_map = {
        ".mp4": "video/mp4", ".avi": "video/avi", ".mov": "video/quicktime",
        ".mkv": "video/x-matroska", ".webm": "video/webm",
        ".m4a": "audio/mp4", ".mp3": "audio/mpeg"
    }
    mime_type = mime_map.get(ext, "video/mp4")
    
    response = client.chat.completions.create(
        model=MODEL_VL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "video_url", "video_url": {"url": f"data:{mime_type};base64,{video_b64}"}},
                {"type": "text", "text": """请仔细分析这个职场教学视频，用自然口语的方式整理内容：
1. 视频里的角色关系（谁是老板/上级，谁是员工/下属，谁是客户）
2. 注意观察画面中人物的表情和动作，这些对理解场景很重要
3. 整理对话内容，标注角色
4. 总结职场沟通技巧要点
用接地气的语言输出："""}
            ]
        }]
    )
    return response.choices[0].message.content

def analyze_video_content(video_text: str) -> str:
    client = get_llm_client()
    prompt = f"""
请用自然口语的方式分析这段职场教学内容，像朋友聊天一样说说重点：

内容：{video_text}

用接地气的语言输出：
"""
    res = client.chat.completions.create(
        model=MODEL_TEXT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return res.choices[0].message.content

def parse_video_content(video_text: str, analysis: str = "") -> ParsedData:
    client = get_llm_client()
    analysis_note = f"\n\n特别参考以下分析总结的内容来设计训练要点：\n{analysis}" if analysis else ""
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

关键要求：
1. 仔细分析原文角色关系，明确谁是老板/上级，谁是员工/下属，谁是客户
2. 场景描述要准确，不要搞混角色
3. principles（沟通原则）要体现教学内容的核心要点
4. 老板是模拟的对话训练

内容：{video_text}{analysis_note}
"""
    res = client.chat.completions.create(
        model=MODEL_TEXT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    raw = json.loads(res.choices[0].message.content)
    cases = []
    for c in raw.get("cases", []):
        safe_case = {
            "scene": c.get("scene", "职场沟通场景"),
            "principles": c.get("principles", ["礼貌得体，不卑不亢"]),
            "wrong_reply": c.get("wrong_reply", "直接拒绝、情绪化、顶撞上级"),
            "correct_reply": c.get("correct_reply", "兼顾情绪，积极应对，情商在线"),
            "scoring_criteria": c.get("scoring_criteria", {"态度得体": 35, "逻辑清晰": 35, "解决问题": 30})
        }
        cases.append(safe_case)
    return ParsedData(
        total_cases=raw.get("total_cases", len(cases)),
        cases=cases
    )

def start_boss_chat(case: Case, analysis: str = "") -> str:
    client = get_llm_client()
    analysis_note = f"\n\n此场景训练基于以下教学内容要点：\n{analysis}" if analysis else ""
    prompt = f"""
你是现实公司真实老板，性格正常，有脾气、有威严，不是机器。
场景：{case.scene}
请你扮演这个场景中的老板/上级角色，而你的对象是你的下属，请自然口语开场，直接说一句老板会说的话。
注意：仔细理解场景，不要搞混自己的身份！{analysis_note}

重要：在你说的话前面，加一个表情来表达你此刻的情绪或动作，格式如下：
😤 你这方案怎么回事？
😐 行，说说看。
😏 哦？你倒是挺有想法。

表情参考：😤生气 😡暴怒 😐冷淡 😏嘲讽 😠不满 🤨质疑 👀审视 😌满意 🙂微笑 🤔思考 😤不耐烦 😒嫌弃 😳意外 😤施压
只输出一个表情+一句话，不要加括号或文字描述。
"""
    return client.chat.completions.create(
        model=MODEL_TEXT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9
    ).choices[0].message.content

def boss_reply(user_msg: str, chat_history: List[ChatMessage], case: Case, analysis: str = "") -> str:
    client = get_llm_client()
    history_str = "\n".join([f"{h.role}:{h.content}" for h in chat_history])
    analysis_note = f"\n\n此场景训练基于以下教学内容要点：\n{analysis}" if analysis else ""
    prompt = f"""
你是真实职场老板，有威严、会生气、会冷淡、会施压，绝对不要一直温和客气。
场景：{case.scene}
员工历史对话：{history_str}
员工最新这句话：{user_msg}{analysis_note}

重要提醒：你是老板/上级，不是客户！不要搞混角色！

规则：
1. 如果员工顶撞、阴阳、嘲讽、侮辱、不尊重、怼老板：你立刻严肃、生气、冷淡、施压、反问、指出问题，语气强硬
2. 如果员工正常沟通：正常老板语气
3. 简短口语，符合真实老板说话方式，不要书面化，直接输出一句话

重要：在你说的话前面，加一个表情来表达你此刻的情绪或动作，格式如下：
😤 你这方案怎么回事？
😐 行，说说看。
😏 哦？你倒是挺有想法。

表情参考：😤生气 😡暴怒 😐冷淡 😏嘲讽 😠不满 🤨质疑 👀审视 😌满意 🙂微笑 🤔思考 😤不耐烦 😒嫌弃 😳意外 😤施压
只输出一个表情+一句话，不要加括号或文字描述。
"""
    return client.chat.completions.create(
        model=MODEL_TEXT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.95
    ).choices[0].message.content

def full_score_after_chat(chat_history: List[ChatMessage], case: Case, analysis: str = "") -> str:
    client = get_llm_client()
    full_dialog = "\n".join([f"{'老板' if h.role == 'boss' else '员工'}: {h.content}" for h in chat_history])
    analysis_note = f"\n\n教学内容参考：\n{analysis}" if analysis else ""
    prompt = f"""
帮我也给这段对话打个分，用大白话点评一下，不要太官方，像朋友之间聊天那种感觉。

场景：{case.scene}

对话记录：
{full_dialog}
{analysis_note}

用口语化、有温度的方式输出，重点说清楚哪里做得好、哪里还需要改进。
"""
    try:
        result = client.chat.completions.create(
            model=MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return result.choices[0].message.content
    except Exception as e:
        return f"哎呀，评分出了点小问题...{str(e)}"

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.head("/")
async def read_root_head():
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/video/process")
async def process_video(
    type: str = Form(...),
    url: str = Form(None),
    text: str = Form(None),
    file: UploadFile = File(None)
):
    try:
        if type == "url" and url:
            video_path = download_video(url)
            cleaned_text = video_to_text(video_path)
            return {"extracted_text": cleaned_text, "cleaned_text": cleaned_text}
        elif type == "file" and file:
            temp_dir = tempfile.mkdtemp()
            temp_files.append(temp_dir)
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                f.write(await file.read())
            cleaned_text = video_to_text(file_path)
            return {"extracted_text": cleaned_text, "cleaned_text": cleaned_text}
        elif type == "text" and text:
            client = get_llm_client()
            clean_prompt = f"整理通顺精简：{text}"
            cleaned_text = client.chat.completions.create(
                model=MODEL_TEXT,
                messages=[{"role": "user", "content": clean_prompt}],
                temperature=0.1
            ).choices[0].message.content
            return {"extracted_text": text, "cleaned_text": cleaned_text}
        else:
            raise HTTPException(status_code=400, detail="无效的输入")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/video/analyze")
async def analyze_video(request: VideoAnalyzeRequest):
    try:
        analysis = analyze_video_content(request.text)
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/video/parse")
async def parse_video(request: VideoParseRequest):
    try:
        parsed_data = parse_video_content(request.text, request.analysis)
        return {"parsed_data": parsed_data.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/boss-start")
async def boss_start(request: BossStartRequest):
    try:
        message = start_boss_chat(request.case, request.analysis)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/boss-reply")
async def boss_reply_api(request: BossReplyRequest):
    try:
        message = boss_reply(request.user_msg, request.chat_history, request.case, request.analysis)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/score")
async def score_chat(request: ScoreRequest):
    try:
        result = full_score_after_chat(request.chat_history, request.case, request.analysis)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
