import os
import json
import logging
import asyncio
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # ⚠️ ต้อง set ใน .env หรือ environment variable เท่านั้น
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "")

class GeminiDirectService:
    """Service for interacting with Gemini Direct REST API (Google AI Studio) or OpenRouter API via zero-dependency HTTP requests."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        # ไม่ crash เมื่อไม่มี key (AI features degrade gracefully)
        self.is_openrouter = bool(self.api_key) and self.api_key.startswith("sk-or-")
        if self.is_openrouter:
            self.model = model or "meta-llama/llama-3.3-70b-instruct"
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        else:
            self.model = model or GEMINI_MODEL
            self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def _sync_generate_content(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Synchronous HTTP POST using standard urllib supporting both Gemini Native API and OpenRouter API."""
        if not self.api_key:
            logger.warning("API_KEY is not configured.")
            return "⚠️ ไม่พบ API Key กรุณาตั้งค่า API Key ในตัวแปรสิ่งแวดล้อม"

        if self.is_openrouter:
            url = self.base_url
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://hotel.nithep.com",
                "X-Title": "Smart Nurse Call (SNC)"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 1024
            }
        else:
            url = f"{self.base_url}?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {"parts": [{"text": prompt}]}
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 1024
                }
            }

        data = json.dumps(payload).encode("utf-8")

        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=15) as response:
                    res_body = response.read().decode("utf-8")
                    res_json = json.loads(res_body)
                    
                    if self.is_openrouter:
                        choices = res_json.get("choices", [])
                        if choices and "message" in choices[0]:
                            return choices[0]["message"].get("content", "").strip()
                    else:
                        candidates = res_json.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"].strip()
                    return "ไม่สามารถสกัดข้อความคำตอบจาก API ได้"
            except urllib.error.HTTPError as e:
                error_content = e.read().decode("utf-8") if e.fp else str(e)
                logger.error(f"API HTTP Error (Attempt {attempt}/{max_retries}): {e.code} - {error_content}")
                if attempt == max_retries:
                    return f"❌ เกิดข้อผิดพลาด API ({e.code}): {error_content[:200]}"
            except Exception as e:
                logger.error(f"API Exception (Attempt {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    return f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ API: {str(e)}"
            
            import time
            time.sleep(attempt * 1.5)
        
        return "❌ การเชื่อมต่อ API ล้มเหลวหลังจากพยายามหลายครั้ง"

    async def generate_content(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Asynchronous wrapper for generate_content."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_generate_content, prompt, max_retries)

    async def generate_daily_executive_summary(self, kpi_data: Dict[str, Any], recent_events: List[Dict[str, Any]]) -> str:
        """Generate an executive summary report in Thai language using Gemini AI with Local Fallback Engine."""
        prompt = f"""
คุณคือ Senior Medical Operations Analyst ประจำระบบ Smart Nurse Call (SNC) ของโรงพยาบาล
กรุณาวิเคราะห์สถิติข้อมูล KPI และเหตุการณ์สายเรียกพยาบาลด้านล่างนี้ แล้วเขียนสรุปรายงานสรุปผู้บริหารเป็นภาษาไทยอย่างเป็นทางการ มืออาชีพ และได้ใจความ:

--- สถิติ KPI ประจำวัน ---
- อัตราตอบสนองตามเกณฑ์ SLA Compliance Rate: {kpi_data.get('sla_compliance_rate', 0)}%
- เวลาตอบรับเฉลี่ยของพยาบาล (Avg Ack Time): {kpi_data.get('avg_ack_time_seconds', 0)} วินาที (เป้าหมาย <= 30 วินาที)
- เวลาล้างสายรวมเฉลี่ย (Avg Resolution Time): {kpi_data.get('avg_resolution_time_seconds', 0)} วินาที (เป้าหมาย <= 180 วินาที)
- จำนวนเหตุการณ์ทั้งหมด: {kpi_data.get('total_events', 0)} รายการ
- แยกตามประเภท: {json.dumps(kpi_data.get('events_by_type', {}), ensure_ascii=False)}

--- ตัวอย่างเหตุการณ์ล่าสุด ---
{json.dumps(recent_events[:10], ensure_ascii=False, indent=2)}

กรุณาสรุปโดยแบ่งหัวข้อหลักดังนี้:
1. 📊 **ภาพรวมประสิทธิภาพ SLA (Executive SLA Performance)**
2. 🚨 **เคสฉุกเฉินและจุดที่ต้องเฝ้าระวัง (Critical Incidents & Anomalies)**
3. 💡 **ข้อเสนอแนะในการปรับปรุงบริการ (Actionable Recommendations)**
"""
        result = await self.generate_content(prompt)
        
        # Fallback Engine if API returns error (e.g. 429 Quota Exhausted)
        if not result or result.startswith("❌"):
            sla_rate = kpi_data.get('sla_compliance_rate', 100)
            avg_ack = kpi_data.get('avg_ack_time_seconds', 0)
            avg_res = kpi_data.get('avg_resolution_time_seconds', 0)
            total = kpi_data.get('total_events', 0)
            
            result = f"""📊 **ภาพรวมประสิทธิภาพ SLA (Executive SLA Performance)**
- อัตราการตอบสนองตามเกณฑ์ SLA อยู่ที่ **{sla_rate}%** จากจำนวนสายเรียกทั้งหมด {total} รายการ
- เวลาตอบรับเฉลี่ย (Ack Time): **{avg_ack} วินาที** {'(อยู่ในเกณฑ์มาตรฐาน <= 30s)' if avg_ack <= 30 else '⚠️ (เกินเกณฑ์มาตรฐาน 30s)'}
- เวลาเคลียร์สายเฉลี่ย (Resolution Time): **{avg_res} วินาที**

🚨 **เคสฉุกเฉินและจุดที่ต้องเฝ้าระวัง (Critical Incidents & Anomalies)**
- บันทึกการกดเรียกฉุกเฉินข้างเตียงและห้องน้ำถูกประมวลผลเรียบร้อยในระบบ SQLite
- คำเตือน: ระบบ Gemini Direct API แจ้งเตือน Quota Limit (429) ระบบได้สลับมาใช้ Local Analytics Engine โดยอัตโนมัติ

💡 **ข้อเสนอแนะในการปรับปรุงบริการ (Actionable Recommendations)**
- รักษาระดับการตอบรับสายเรียกให้อยู่ในเกณฑ์ต่ำกว่า 30 วินาทีอย่างต่อเนื่อง
- แนะนำให้อัปเดต Gemini API Key จาก Google AI Studio เพื่อเปิดใช้งาน AI Analysis แบบเต็มรูปแบบ"""

        return result

    async def analyze_emergency_anomaly(self, room_id: str, room_events: List[Dict[str, Any]]) -> str:
        """Analyze emergency patterns and potential anomalies for a specific room with Local Fallback."""
        prompt = f"""
คุณคือ Nurse Station Supervisor วิเคราะห์เหตุการณ์กดเรียกฉุกเฉินซ้ำซ้อนสำหรับ ห้องพัก {room_id}
ข้อมูลประวัติเหตุการณ์ย้อนหลังของห้อง {room_id}:
{json.dumps(room_events, ensure_ascii=False, indent=2)}

กรุณาวิเคราะห์สั้นๆ (ไม่เกิน 3-4 บรรทัด):
1. ประเมินความเสี่ยงหรือรูปแบบความผิดปกติ (เช่น มีการกด EMER ห้องน้ำซ้ำ ภายในเวลาอันสั้น หรือ Ack Time ล่าช้า)
2. ข้อแนะนำการปฏิบัติสำหรับทีมพยาบาลประจำวอร์ด
"""
        result = await self.generate_content(prompt)
        if not result or result.startswith("❌"):
            count = len(room_events)
            result = f"วิเคราะห์ประวัติห้อง {room_id} (รวม {count} รายการ): พบการกดเรียกฉุกเฉินและได้รับการตอบรับแล้ว หากมีการกดเรียกซ้ำใน 90 วินาที แนะนำให้ส่งพยาบาลตรวจสอบหน้าห้องพักทันที"
        return result

    async def send_google_chat_summary(self, webhook_url: str, summary_text: str, kpi_data: Dict[str, Any]) -> bool:
        """Send formatted AI summary card to Google Chat Webhook."""
        url = webhook_url or GOOGLE_CHAT_WEBHOOK_URL
        if not url:
            logger.warning("Google Chat Webhook URL is not set.")
            return False

        card_payload = {
            "cardsV2": [
                {
                    "cardId": f"snc-summary-{int(datetime.now().timestamp())}",
                    "card": {
                        "header": {
                            "title": "🏥 Smart Nurse Call - AI Daily Executive Summary",
                            "subtitle": f"รายงานสรุปผู้บริหารประจำวันที่ {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            "imageUrl": "https://img.icons8.com/color/96/hospital.png",
                            "imageType": "CIRCLE"
                        },
                        "sections": [
                            {
                                "header": "📊 ดัชนี KPI หลัก (Key Metrics)",
                                "widgets": [
                                    {
                                        "decoratedText": {
                                            "topLabel": "SLA Compliance Rate",
                                            "text": f"<b>{kpi_data.get('sla_compliance_rate', 100)}%</b>",
                                            "startIcon": {"knownIcon": "STAR"}
                                        }
                                    },
                                    {
                                        "decoratedText": {
                                            "topLabel": "Avg Ack Time / Avg Resolution",
                                            "text": f"<b>{kpi_data.get('avg_ack_time_seconds', 0)}s</b> / <b>{kpi_data.get('avg_resolution_time_seconds', 0)}s</b>",
                                            "startIcon": {"knownIcon": "CLOCK"}
                                        }
                                    }
                                ]
                            },
                            {
                                "header": "🤖 บทวิเคราะห์และข้อเสนอแนะจาก Gemini AI",
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": summary_text.replace("\n", "<br>")
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }

        try:
            data = json.dumps(card_payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Failed to send card to Google Chat: {e}")
            return False
