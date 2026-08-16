variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "hotel-ecs-nithep"
}

variable "region" {
  description = "GCP region สำหรับ Cloud Run / Firestore"
  type        = string
  default     = "asia-southeast1"
}

variable "backend_image" {
  description = "Image ของ snc-cloud-backend (เต็มที่รวม digest ได้) เช่น gcr.io/proj/snc-cloud-backend:latest"
  type        = string
}

variable "bridge_image" {
  description = "Image ของ snc-alert-bridge เช่น gcr.io/proj/snc-alert-bridge:latest"
  type        = string
}

variable "snc_api_key" {
  description = "SNC_API_KEY สำหรับ backend (ควรผ่าน secret — ดู main.tf)"
  type        = string
  sensitive   = true
}

variable "telegram_bot_token" {
  description = "Telegram bot token (secret)"
  type        = string
  sensitive   = true
}

variable "telegram_chat_id" {
  description = "Telegram chat_id ปลายทาง"
  type        = string
}

variable "monitor_webhook_token" {
  description = "token กันปลอมของ webhook bridge (secret)"
  type        = string
  sensitive   = true
}

variable "uptime_check_path" {
  description = "path ที่ uptime check ตรวจ (ของ backend หลัก)"
  type        = string
  default     = "/health"
}

variable "uptime_period" {
  description = "ช่วงตรวจ uptime (วินาที)"
  type        = string
  default     = "300s"
}

variable "alert_duration" {
  description = "duration ก่อน fire alert (วินาที)"
  type        = string
  default     = "120s"
}