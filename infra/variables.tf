variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "stage" {
  type    = string
  default = "dev"
}

variable "dev_origins" {
  type        = list(string)
  default     = ["http://localhost:5173"]
  description = "Extra websites allowed to call the API (for running the frontend on your computer). Use [] in production."
}

variable "alert_email" {
  type        = string
  default     = ""
  description = "Email address for error alerts. Leave empty to skip."
}

variable "otp_delivery" {
  type        = string
  default     = "sms"
  description = "sms = send real text messages. log = write the code to CloudWatch Logs (testing only, blocked when stage is prod)."

  validation {
    condition     = contains(["sms", "log"], var.otp_delivery)
    error_message = "otp_delivery must be \"sms\" or \"log\"."
  }
}
