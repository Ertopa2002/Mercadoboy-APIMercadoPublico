# Despliegue en AWS (POC, ambiente pilot)

Cuenta vionexus-sandbox · us-east-1 · todo etiquetado `proyecto=mp-poc`.

## Una sola vez

```bash
aws sso login --profile vionexus-sandbox
# Ticket de ChileCompra en Parameter Store (no queda en Terraform ni en el repo)
aws ssm put-parameter --profile vionexus-sandbox --region us-east-1 \
  --name /mp-poc/pilot/ticket --type SecureString --value "$(grep ^MP_TICKET= .env | cut -d= -f2)"
```

Activar la etiqueta de costos `proyecto` en Billing → Cost allocation tags (para que el presupuesto filtre solo la POC).

## Cada despliegue

```bash
./scripts/build_lambda.sh                 # genera dist/lambda.zip
cd infra/envs/pilot
terraform init                            # solo la primera vez
terraform plan -out plan.tfplan
terraform apply plan.tfplan
terraform output -raw conector_url        # URL para Claude (contiene el token)
```

## Carga inicial del índice (opcional)

Subir el índice local para no repetir las llamadas ya hechas:

```bash
BUCKET=$(terraform output -raw bucket_datos)
aws s3 cp ../../../exploracion/blobs/indice/ "s3://$BUCKET/indice/" --recursive --profile vionexus-sandbox
```

## Verificar

```bash
aws lambda invoke --profile vionexus-sandbox --function-name mp-pilot-precarga \
  --payload '{"tarea":"compras_agiles"}' --cli-binary-format raw-in-base64-out /dev/stdout
curl "$(terraform output -raw conector_url | sed 's#/[^/]*/mcp$##')/health"
```

## Conectar a Claude

Configuración → Conectores → Agregar conector personalizado → pegar la URL de `conector_url`.
