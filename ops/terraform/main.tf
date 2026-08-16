# ============================================================================
# SNC GCP Infrastructure — Terraform (ADR 0005)
# ครอบ: Cloud Run (backend + bridge), Firestore, Secret Manager,
#       uptime check + alerting policy (→ bridge → Telegram)
#
# หมายเหตุ: ต้อง import resource ที่สร้างด้วยมือก่อน (terraform import) —
# ดู ops/terraform/README.md
# ============================================================================
provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  backend_url = "https://${var.region}-${var.project_id}.cloudfunctions.net" # placeholder
  # ชื่อ Cloud Run URL ตาม format: https://<service>-<hash>.<region>.run.app
  # (hash คำนวณโดย GCP — ใช้ data google_cloud_run_service ด้านล่างแทน)
}

# ── Firestore (native mode) ───────────────────────────────────────────────
resource "google_firestore_database" "snc" {
  project                           = var.project_id
  name                              = "(default)"
  location_id                       = var.region
  type                              = "FIRESTORE_NATIVE"
  deletion_protection               = true
}

# ── Secret Manager ───────────────────────────────────────────────────────
# SNC_API_KEY ก็ผ่าน Secret Manager (ไม่ส่ง plain env) — ห้ามมี secret ใน env
resource "google_secret_manager_secret" "snc_api_key" {
  project   = var.project_id
  secret_id = "snc-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "snc_api_key" {
  secret      = google_secret_manager_secret.snc_api_key.id
  secret_data = var.snc_api_key
}

resource "google_secret_manager_secret" "telegram_bot_token" {
  project   = var.project_id
  secret_id = "snc-telegram-bot-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "telegram_bot_token" {
  secret      = google_secret_manager_secret.telegram_bot_token.id
  secret_data = var.telegram_bot_token
}

resource "google_secret_manager_secret" "monitor_webhook_token" {
  project   = var.project_id
  secret_id = "snc-monitor-webhook-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "monitor_webhook_token" {
  secret      = google_secret_manager_secret.monitor_webhook_token.id
  secret_data = var.monitor_webhook_token
}

# ── Cloud Run: snc-cloud-backend ──────────────────────────────────────────
resource "google_cloud_run_v2_service" "backend" {
  project  = var.project_id
  location = var.region
  name     = "snc-cloud-backend"

  template {
    service_account = google_service_account.run_sa.email
    containers {
      image = var.backend_image
      env {
        name  = "SNC_DB_BACKEND"
        value = "firestore"
      }
      env {
        name  = "SNC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.snc_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_version.snc_api_key,
    google_secret_manager_secret_version.telegram_bot_token,
    google_secret_manager_secret_version.monitor_webhook_token,
    google_firestore_database.snc,
  ]
}

# ── Cloud Run: snc-alert-bridge ───────────────────────────────────────────
resource "google_cloud_run_v2_service" "bridge" {
  project  = var.project_id
  location = var.region
  name     = "snc-alert-bridge"

  template {
    service_account = google_service_account.run_sa.email
    containers {
      image = var.bridge_image
      env {
        name  = "TELEGRAM_CHAT_ID"
        value = var.telegram_chat_id
      }
      env {
        name  = "TELEGRAM_BOT_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_bot_token.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "MONITOR_WEBHOOK_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.monitor_webhook_token.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_version.telegram_bot_token,
    google_secret_manager_secret_version.monitor_webhook_token,
  ]
}

# ── ให้ ingress แบบ public (--allow-unauthenticated) ──────────────────────
resource "google_cloud_run_v2_service_iam_member" "backend_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "bridge_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.bridge.location
  name     = google_cloud_run_v2_service.bridge.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Service Account + IAM ─────────────────────────────────────────────────
resource "google_service_account" "run_sa" {
  project      = var.project_id
  account_id   = "snc-run"
  display_name = "SNC Cloud Run service account"
}

resource "google_project_iam_member" "run_sa_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "bridge_bot_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.telegram_bot_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_apikey_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.snc_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "bridge_webhook_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.monitor_webhook_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run_sa.email}"
}

# ── Uptime check (ของ backend หลัก) ───────────────────────────────────────
# หา URL ของ Cloud Run ผ่าน data source (หลีกเลี่ยง hash ที่ไม่รู้ค่า)
data "google_cloud_run_v2_service" "backend" {
  name     = google_cloud_run_v2_service.backend.name
  location = google_cloud_run_v2_service.backend.location
  project  = var.project_id
}

data "google_cloud_run_v2_service" "bridge" {
  name     = google_cloud_run_v2_service.bridge.name
  location = google_cloud_run_v2_service.bridge.location
  project  = var.project_id
}

resource "google_monitoring_uptime_check_config" "snc" {
  project      = var.project_id
  display_name = "SNC Cloud Run /health"
  timeout      = "10s"
  period       = var.uptime_period

  http_check {
    path         = var.uptime_check_path
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      host       = data.google_cloud_run_v2_service.backend.uri
      project_id = var.project_id
    }
  }

  selected_regions = ["USA", "EUROPE", "ASIA_PACIFIC"]
}

# ── Notification channel (webhook → bridge) ──────────────────────────────
resource "google_monitoring_notification_channel" "telegram_bridge" {
  project      = var.project_id
  display_name = "SNC Telegram alert bridge"
  type         = "webhook_tokenauth"
  labels = {
    url = "${data.google_cloud_run_v2_service.bridge.uri}/webhook?token=${var.monitor_webhook_token}"
  }
  user_labels = {
    purpose = "telegram-alert"
  }
}

# ── Alerting policy (uptime fail → webhook → bridge → Telegram) ───────────
resource "google_monitoring_alert_policy" "snc_uptime" {
  project        = var.project_id
  display_name   = "SNC Cloud Run uptime alert"
  combiner       = "OR"
  notification_channels = [
    google_monitoring_notification_channel.telegram_bridge.name,
  ]

  alert_strategy {
    auto_close = "3600s"
  }

  conditions {
    display_name = "Uptime check /health failed"
    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
        "resource.type=\"uptime_url\"",
        "metric.label.\"check_id\"=\"${google_monitoring_uptime_check_config.snc.uptime_check_id}\"",
      ])
      comparison  = "COMPARISON_LT"
      threshold_value = 1
      duration    = var.alert_duration
      trigger {
        count = 1
      }
      aggregations {
        alignment_period     = var.alert_duration
        per_series_aligner   = "ALIGN_NEXT_OLDER"
      }
    }
  }
}