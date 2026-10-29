locals {
  nombre       = "mp-${var.ambiente}"
  param_ticket = "/mp-poc/${var.ambiente}/ticket"
  param_token  = "/mp-poc/${var.ambiente}/token"
}

data "aws_caller_identity" "yo" {}

# --- Almacenamiento ---------------------------------------------------------

resource "aws_s3_bucket" "datos" {
  bucket = "${local.nombre}-datos-${data.aws_caller_identity.yo.account_id}"
}

resource "aws_s3_bucket_public_access_block" "datos" {
  bucket                  = aws_s3_bucket.datos.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "datos" {
  bucket = aws_s3_bucket.datos.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "datos" {
  bucket = aws_s3_bucket.datos.id
  rule {
    id     = "adjuntos-30-dias"
    status = "Enabled"
    filter { prefix = "adjuntos/" }
    expiration { days = 30 }
  }
}

resource "aws_dynamodb_table" "cache" {
  name         = "${local.nombre}-cache"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "k"
  attribute {
    name = "k"
    type = "S"
  }
  ttl {
    attribute_name = "expira"
    enabled        = true
  }
}

# --- Secretos -----------------------------------------------------------------
# El ticket de ChileCompra NO se crea aquí (no debe quedar en el estado de Terraform):
#   aws ssm put-parameter --name /mp-poc/pilot/ticket --type SecureString --value '...'

resource "random_password" "token" {
  length  = 40
  special = false
}

resource "aws_ssm_parameter" "token" {
  name  = local.param_token
  type  = "SecureString"
  value = random_password.token.result
}

# --- Permisos -----------------------------------------------------------------

data "aws_iam_policy_document" "asumir_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.nombre}-lambda"
  assume_role_policy = data.aws_iam_policy_document.asumir_lambda.json
}

data "aws_iam_policy_document" "lambda" {
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.yo.account_id}:log-group:/aws/lambda/${local.nombre}-*:*"]
  }
  statement {
    sid       = "Cache"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"]
    resources = [aws_dynamodb_table.cache.arn]
  }
  statement {
    sid       = "Datos"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.datos.arn}/indice/*", "${aws_s3_bucket.datos.arn}/adjuntos/*"]
  }
  statement {
    sid       = "ListarDatos"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.datos.arn]
  }
  statement {
    sid       = "Parametros"
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:${var.region}:${data.aws_caller_identity.yo.account_id}:parameter/mp-poc/${var.ambiente}/*"]
  }
  statement {
    sid       = "DescifrarParametros"
    actions   = ["kms:Decrypt"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${var.region}.amazonaws.com"]
    }
  }
  statement {
    sid       = "OCR"
    actions   = ["textract:DetectDocumentText"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda.json
}

# --- Paquete ------------------------------------------------------------------

resource "aws_s3_object" "paquete" {
  bucket      = aws_s3_bucket.datos.id
  key         = "artefactos/lambda.zip"
  source      = var.zip_lambda
  source_hash = filemd5(var.zip_lambda)
}

locals {
  entorno_comun = {
    MP_TABLA        = aws_dynamodb_table.cache.name
    MP_BUCKET       = aws_s3_bucket.datos.id
    MP_PARAM_TICKET = local.param_ticket
    MP_DAILY_BUDGET = "8000"
  }
}

resource "aws_cloudwatch_log_group" "conector" {
  name              = "/aws/lambda/${local.nombre}-conector"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "precarga" {
  name              = "/aws/lambda/${local.nombre}-precarga"
  retention_in_days = 7
}

# --- Conector MCP -------------------------------------------------------------

resource "aws_lambda_function" "conector" {
  function_name                  = "${local.nombre}-conector"
  role                           = aws_iam_role.lambda.arn
  runtime                        = "python3.12"
  architectures                  = ["arm64"]
  handler                        = "run.sh"
  s3_bucket                      = aws_s3_object.paquete.bucket
  s3_key                         = aws_s3_object.paquete.key
  source_code_hash               = filebase64sha256(var.zip_lambda)
  memory_size                    = 1024
  timeout                        = 120
  layers                         = [var.capa_web_adapter_arn]
  reserved_concurrent_executions = var.concurrencia_conector
  environment {
    variables = merge(local.entorno_comun, {
      MP_PARAM_TOKEN               = local.param_token
      AWS_LAMBDA_EXEC_WRAPPER      = "/opt/bootstrap"
      AWS_LWA_PORT                 = "8080"
      AWS_LWA_READINESS_CHECK_PATH = "/health"
    })
  }
  depends_on = [aws_cloudwatch_log_group.conector, aws_iam_role_policy.lambda]
}

resource "aws_lambda_function_url" "conector" {
  function_name      = aws_lambda_function.conector.function_name
  authorization_type = "NONE" # protegido por el token en la ruta (ADR 0003)
}

# Desde oct-2025 una URL pública exige ambos permisos en la política de recursos.
# InvokeFunction queda acotado a llamadas que entran por la URL.
resource "aws_lambda_permission" "url_publica" {
  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.conector.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "url_invoke" {
  statement_id             = "FunctionURLInvokeAllowPublicAccess"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.conector.function_name
  principal                = "*"
  invoked_via_function_url = true
}

# --- Precarga -----------------------------------------------------------------

resource "aws_lambda_function" "precarga" {
  function_name    = "${local.nombre}-precarga"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = "aws_lambda.precarga.handler"
  s3_bucket        = aws_s3_object.paquete.bucket
  s3_key           = aws_s3_object.paquete.key
  source_code_hash = filebase64sha256(var.zip_lambda)
  memory_size      = 1024
  timeout          = 900
  environment { variables = local.entorno_comun }
  depends_on = [aws_cloudwatch_log_group.precarga, aws_iam_role_policy.lambda]
}

data "aws_iam_policy_document" "asumir_scheduler" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.nombre}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.asumir_scheduler.json
}

resource "aws_iam_role_policy" "scheduler" {
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "lambda:InvokeFunction", Resource = aws_lambda_function.precarga.arn }]
  })
}

resource "aws_scheduler_schedule" "licitaciones" {
  name                = "${local.nombre}-precarga-licitaciones"
  schedule_expression = var.frecuencia_licitaciones
  flexible_time_window { mode = "OFF" }
  target {
    arn      = aws_lambda_function.precarga.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ tarea = "licitaciones" })
    retry_policy { maximum_retry_attempts = 0 }
  }
}

resource "aws_scheduler_schedule" "compras_agiles" {
  name                = "${local.nombre}-precarga-compras-agiles"
  schedule_expression = var.frecuencia_compras_agiles
  flexible_time_window { mode = "OFF" }
  target {
    arn      = aws_lambda_function.precarga.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ tarea = "compras_agiles" })
    retry_policy { maximum_retry_attempts = 0 }
  }
}

# --- Costos -------------------------------------------------------------------
# Requiere activar la etiqueta de costos "proyecto" en Billing > Cost allocation tags.

resource "aws_budgets_budget" "poc" {
  name         = "${local.nombre}-mensual"
  budget_type  = "COST"
  limit_amount = tostring(var.presupuesto_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  cost_filter {
    name   = "TagKeyValue"
    values = ["user:proyecto$mp-poc"]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.correo_alertas]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.correo_alertas]
  }
}
