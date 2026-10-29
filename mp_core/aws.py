"""Implementaciones AWS de las interfaces del core (ADR 0004 y 0009).

- DynamoStore: caché y contador de cupo en DynamoDB (TTL en el atributo `expira`).
- S3BlobStore: índice de procesos en S3.
- leer_parametro: ticket y token desde SSM Parameter Store.

boto3 viene incluido en el runtime de Lambda; en local se instala con el extra `aws`.
"""

import json
import time
from typing import Any


class DynamoStore:
    """Tabla con clave de partición `k` (string). Valores guardados como JSON en `v`."""

    def __init__(self, tabla: str, recurso=None):
        if recurso is None:
            import boto3

            recurso = boto3.resource("dynamodb")
        self.t = recurso.Table(tabla)

    @staticmethod
    def _expira(ttl_s: int | None) -> int | None:
        return int(time.time()) + ttl_s if ttl_s else None

    def get(self, key: str) -> Any | None:
        item = self.t.get_item(Key={"k": key}).get("Item")
        if not item:
            return None
        exp = item.get("expira")
        if exp is not None and int(exp) <= time.time():  # DynamoDB borra el TTL con atraso
            return None
        if "n" in item:
            return int(item["n"])
        return json.loads(item["v"])

    def put(self, key: str, value: Any, ttl_s: int | None = None) -> None:
        item: dict[str, Any] = {"k": key, "v": json.dumps(value, ensure_ascii=False)}
        if (exp := self._expira(ttl_s)) is not None:
            item["expira"] = exp
        self.t.put_item(Item=item)

    def incr(self, key: str, amount: int = 1, ttl_s: int | None = None) -> int:
        expr, valores = "ADD n :a", {":a": amount}
        if (exp := self._expira(ttl_s)) is not None:
            expr += " SET expira = if_not_exists(expira, :e)"
            valores[":e"] = exp
        r = self.t.update_item(
            Key={"k": key},
            UpdateExpression=expr,
            ExpressionAttributeValues=valores,
            ReturnValues="UPDATED_NEW",
        )
        return int(r["Attributes"]["n"])

    def delete(self, key: str) -> None:
        self.t.delete_item(Key={"k": key})


class S3BlobStore:
    def __init__(self, bucket: str, cliente=None):
        if cliente is None:
            import boto3

            cliente = boto3.client("s3")
        self.bucket = bucket
        self.s3 = cliente

    def leer(self, clave: str) -> bytes | None:
        try:
            return self.s3.get_object(Bucket=self.bucket, Key=clave)["Body"].read()
        except self.s3.exceptions.NoSuchKey:
            return None

    def escribir(self, clave: str, data: bytes) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=clave, Body=data)

    def version(self, clave: str) -> str | None:
        try:
            return self.s3.head_object(Bucket=self.bucket, Key=clave)["ETag"]
        except Exception:  # noqa: BLE001 - no existe aún
            return None


def leer_parametro(nombre: str, cliente=None) -> str:
    if cliente is None:
        import boto3

        cliente = boto3.client("ssm")
    return cliente.get_parameter(Name=nombre, WithDecryption=True)["Parameter"]["Value"]
