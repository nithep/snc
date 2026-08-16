terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0, < 7.0"
    }
  }
  # state เก็บไว้ที่ GCS bucket (remote) — สร้าง bucket ก่อนแล้วชี้มาที่นี่
  backend "gcs" {
    bucket = "snc-tfstate-nithep"
    prefix = "snc"
  }
}