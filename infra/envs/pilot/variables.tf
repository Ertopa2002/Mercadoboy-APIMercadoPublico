variable "region" {
  type    = string
  default = "us-east-1"
}

variable "perfil_aws" {
  description = "Perfil SSO de la CLI"
  type        = string
  default     = "vionexus-sandbox"
}

variable "ambiente" {
  type    = string
  default = "pilot"
}

variable "zip_lambda" {
  description = "Paquete generado por scripts/build_lambda.sh"
  type        = string
  default     = "../../../dist/lambda.zip"
}

variable "capa_web_adapter_arn" {
  description = "AWS Lambda Web Adapter (arm64). Verificar la última versión en github.com/awslabs/aws-lambda-web-adapter"
  type        = string
  default     = "arn:aws:lambda:us-east-1:753240598075:layer:LambdaAdapterLayerArm64:25"
}

variable "frecuencia_licitaciones" {
  description = "Precarga de licitaciones (incremental). Carga inicial completa: cada 3 h"
  type        = string
  default     = "rate(3 hours)"
}

variable "frecuencia_compras_agiles" {
  type    = string
  default = "rate(3 hours)"
}

variable "correo_alertas" {
  type    = string
  default = "pcisterna@gmail.com"
}

variable "presupuesto_usd" {
  type    = number
  default = 20
}

variable "concurrencia_conector" {
  description = "Concurrencia reservada del conector (null = sin reserva; cuentas nuevas con límite 10 no permiten reservar)"
  type        = number
  default     = null
}
