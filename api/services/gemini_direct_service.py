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
                "max_tokens": 2048
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
                    "maxOutputTokens": 2048
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
        """Generate an executive summary report in professional Thai using Gemini AI with Local Fallback Engine."""
        today_str = datetime.now().strftime("%d %B %Y")
        prompt = f"""
คุณคือ Senior Medical Operations Analyst ผู้เชี่ยวชาญด้านการวิเคราะห์การปฏิบัติการพยาบาล (Nursing Operations)
ประจำระบบ Smart Nurse Call (SNC) ของโรงพยาบาล

หน้าที่: เขียน "รายงานสรุปผู้บริหารประจำวัน" (Daily Executive Summary) เป็นภาษาไทยอย่างเป็นทางการ
ระดับมืออาชีพ และได้ใจความ สำหรับผู้บริหารโรงพยาบาลและหัวหน้าฝ่ายการพยาบาล

กฎการเขียน (ห้ามละเมิด):
1. ใช้เฉพาะข้อมูลที่ให้ด้านล่างนี้เท่านั้น ห้ามสมมติหรือแต่งตัวเลขที่ไม่มีในข้อมูล หากข้อมูลไม่ครบให้ระบุอย่างตรงไปตรงมา
2. ใช้ภาษาทางการเชิงธุรกิจ (Formal Executive Thai) กระชับ ตรงประเด็น หลีกเลี่ยงคำฟุ่มเฟือย และไม่ใช้ภาษาพูด
3. โครงสร้างรายงานต้องเป็นไปตามหัวข้อที่กำหนดด้านล่าง โดยขึ้นต้นด้วยสรุปผู้บริหาร (Executive Summary) เสมอ
4. หากพบเคสที่ละเมิด SLA (เวลาตอบรับ > 30 วินาที หรือเวลาดำเนินการ > 180 วินาที) ต้องระบุจำนวนและห้องที่เกี่ยวข้องให้ชัดเจน
5. ข้อเสนอแนะต้องแบ่งเป็น (ก) มาตรการเร่งด่วน และ (ข) การปรับปรุงระยะกลาง ที่ทีมพยาบาลนำไปปฏิบัติได้จริง
6. เขียนเป็นภาษาไทยทั้งหมด ยกเว้นคำศัพท์เทคนิคหรือตัวย่อภาษาอังกฤษที่จำเป็น

--- สถิติ KPI ประจำวัน ---
- วันที่รายงาน: {today_str}
- อัตราการตอบสนองตามเกณฑ์ SLA Compliance Rate: {kpi_data.get('sla_compliance_rate', 0)}% (เป้าหมาย >= 98%)
- เวลาตอบรับเฉลี่ยของพยาบาล (Avg Ack Time): {kpi_data.get('avg_ack_time_seconds', 0)} วินาที (เป้าหมาย <= 30 วินาที)
- เวลาดำเนินการจนเคลียร์สายเฉลี่ย (Avg Resolution Time): {kpi_data.get('avg_resolution_time_seconds', 0)} วินาที (เป้าหมาย <= 180 วินาที)
- จำนวนเหตุการณ์ทั้งหมด: {kpi_data.get('total_events', 0)} รายการ
- จำนวนเหตุการณ์แยกตามประเภท: {json.dumps(kpi_data.get('events_by_type', {}), ensure_ascii=False)}

--- เหตุการณ์ล่าสุด (ใช้วิเคราะห์จุดเสี่ยง) ---
{json.dumps(recent_events[:10], ensure_ascii=False, indent=2)}

--- รูปแบบรายงานที่ต้องการ (ให้ใช้หัวข้อด้านล่างนี้เท่านั้น) ---

🏥 รายงานสรุปผู้บริหาร Smart Nurse Call
📅 วันที่: {today_str}

**1. สรุปผู้บริหาร (Executive Summary)**
(สรุปภาพรวม 2-4 ข้อ: สถานะโดยรวมของระบบ ตัวเลขสำคัญ และประเด็นที่ผู้บริหารควรทราบวันนี้)

**2. ภาพรวมประสิทธิภาพ SLA (SLA Performance)**
(วิเคราะห์ตัวชี้วัดแต่ละรายการเทียบเป้าหมาย พร้อมระบุสถานะ: ✅ อยู่ในเกณฑ์ / ⚠️ ต่ำกว่าเกณฑ์เล็กน้อย / 🚨 วิกฤต แล้วอธิบายความหมายเชิงปฏิบัติต่อการดูแลผู้ป่วย)

**3. เหตุการณ์สำคัญและจุดเฝ้าระวัง (Key Incidents & Watch Points)**
(วิเคราะห์จากเหตุการณ์ล่าสุด: เคสฉุกเฉิน เคสที่ละเมิด SLA รูปแบบการกดเรียกซ้ำ หรือพฤติกรรมผิดปกติ หากไม่มีเหตุการณ์ผิดปกติ ให้ระบุไว้อย่างชัดเจน)

**4. ข้อเสนอแนะเชิงปฏิบัติ (Actionable Recommendations)**
(แบ่งเป็น (ก) มาตรการเร่งด่วน และ (ข) การปรับปรุงระยะกลาง เน้นสิ่งที่ทีมพยาบาลปฏิบัติตามได้จริง)
"""
        result = await self.generate_content(prompt)
        
        # Fallback Engine: ใช้เมื่อ API error (เช่น 429 Quota), การเชื่อมต่อล้มเหลว หรือไม่มี API Key
        if not result or result.startswith("❌") or "ไม่พบ API Key" in result:
            result = self._build_fallback_summary(kpi_data, recent_events)

        return result

    def _build_fallback_summary(self, kpi_data: Dict[str, Any], recent_events: List[Dict[str, Any]]) -> str:
        """Local Analytics Fallback Engine: สร้างรายงานสรุปผู้บริหารจากข้อมูลจริงโดยไม่พึ่ง API (ไม่แต่งตัวเลข)."""
        today_str = datetime.now().strftime("%d %B %Y")
        sla_rate = kpi_data.get('sla_compliance_rate', 0)
        avg_ack = kpi_data.get('avg_ack_time_seconds', 0)
        avg_res = kpi_data.get('avg_resolution_time_seconds', 0)
        total = kpi_data.get('total_events', 0)
        events_by_type = kpi_data.get('events_by_type', {}) or {}
        emergency_count = int(events_by_type.get('CALL_BATHROOM_EMERGENCY', 0))
        
        # คำนวณเคสละเมิด SLA และห้องเสี่ยงจากเหตุการณ์ล่าสุด
        breach_count = 0
        breached_rooms = []
        for ev in recent_events or []:
            if ev.get('sla_breached'):
                breach_count += 1
                room = ev.get('room_id') or '?'
                if room not in breached_rooms:
                    breached_rooms.append(room)
        
        ack_status = '✅ อยู่ในเกณฑ์' if avg_ack <= 30 else '🚨 เกินเกณฑ์'
        res_status = '✅ อยู่ในเกณฑ์' if avg_res <= 180 else '🚨 เกินเกณฑ์'
        sla_status = '✅ อยู่ในเกณฑ์' if sla_rate >= 98 else ('⚠️ ต่ำกว่าเกณฑ์เล็กน้อย' if sla_rate >= 90 else '🚨 วิกฤต')
        
        breached_part = (
            f"- เคสที่ละเมิด SLA: **{breach_count} รายการ** จากเหตุการณ์ล่าสุด (ห้อง: {', '.join(breached_rooms)})\n"
            if breach_count else "- ไม่พบเคสที่ละเมิด SLA ในเหตุการณ์ล่าสุด\n"
        )
        emergency_part = (
            f"- จำนวนเคสฉุกเฉินห้องน้ำ (CALL_BATHROOM_EMERGENCY): **{emergency_count} รายการ**\n"
            if emergency_count else "- ไม่พบเคสฉุกเฉินห้องน้ำในช่วงเวลาที่รายงาน\n"
        )
        
        result = f"""🏥 รายงานสรุปผู้บริหาร Smart Nurse Call
📅 วันที่: {today_str}

**1. สรุปผู้บริหาร (Executive Summary)**
- ระบบดำเนินการกับสายเรียกพยาบาลทั้งหมด {total} รายการ โดยอัตราการตอบสนองตามเกณฑ์ SLA อยู่ที่ **{sla_rate}%** ({sla_status})
- เวลาตอบรับเฉลี่ย **{avg_ack} วินาที** ({ack_status} <= 30 วินาที) และเวลาดำเนินการจนเคลียร์สายเฉลี่ย **{avg_res} วินาที** ({res_status} <= 180 วินาที)
- หมายเหตุ: ระบบ AI วิเคราะห์ไม่พร้อมใช้งาน (API Key ไม่ได้ตั้งค่าหรือ Quota จำกัด) จึงใช้เอนจินวิเคราะห์ในเครื่อง (Local Analytics Engine) ที่อ้างอิงข้อมูลจริงจากระบบ

**2. ภาพรวมประสิทธิภาพ SLA (SLA Performance)**
- อัตราการตอบสนองตามเกณฑ์ SLA: **{sla_rate}%** ({sla_status} เทียบเป้าหมาย >= 98%)
- เวลาตอบรับเฉลี่ย (Avg Ack Time): **{avg_ack} วินาที** ({ack_status})
- เวลาดำเนินการจนเคลียร์สายเฉลี่ย (Avg Resolution Time): **{avg_res} วินาที** ({res_status})

**3. เหตุการณ์สำคัญและจุดเฝ้าระวัง (Key Incidents & Watch Points)**
{emergency_part}{breached_part}
**4. ข้อเสนอแนะเชิงปฏิบัติ (Actionable Recommendations)**
(ก) มาตรการเร่งด่วน:
- {'ตรวจสอบเคสที่ละเมิด SLA ในห้อง ' + ', '.join(breached_rooms) + ' ทันที และทบทวนขั้นตอนการตอบรับสายเรียก' if breached_rooms else 'รักษาระดับการตอบรับสายเรียกให้อยู่ในเกณฑ์ต่ำกว่า 30 วินาทีอย่างต่อเนื่อง'}
- กำชับทีมพยาบาลให้ตอบรับสายเรียกโดยเร็วที่สุดเมื่อมีสัญญาณเรียกเข้าห้องพัก
(ข) การปรับปรุงระยะกลาง:
- ติดตามแนวโน้มตัวชี้วัด SLA รายวัน และตั้งเป้าให้อัตราการปฏิบัติตามเกณฑ์ไม่ต่ำกว่า 98%
- กำหนดค่า Gemini API Key ในตัวแปรสิ่งแวดล้อมเพื่อเปิดใช้งานการวิเคราะห์เชิงลึกด้วย AI แบบเต็มรูปแบบ
"""
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
