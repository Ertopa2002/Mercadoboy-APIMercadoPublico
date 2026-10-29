output "conector_url" {
  description = "URL del conector MCP para Claude (contiene el token: no compartir)"
  value       = "${aws_lambda_function_url.conector.function_url}${random_password.token.result}/mcp"
  sensitive   = true
}

output "bucket_datos" {
  value = aws_s3_bucket.datos.id
}

output "tabla_cache" {
  value = aws_dynamodb_table.cache.name
}

output "funcion_precarga" {
  value = aws_lambda_function.precarga.function_name
}
