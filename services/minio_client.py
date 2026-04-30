"""
Cliente MinIO para almacenar PDFs de sentencias
"""

from minio import Minio
from minio.error import S3Error
import os
from io import BytesIO
from datetime import datetime
import json

class MinIOClient:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket = os.getenv("MINIO_BUCKET", "jurisprudencia")
        self.use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

        # Crear cliente
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.use_ssl
        )

        # Asegurar que el bucket existe
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Crear bucket si no existe y configurar como público"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                print(f"✅ Bucket '{self.bucket}' creado")

                # Política pública para lectura
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket}/*"]
                    }]
                }
                self.client.set_bucket_policy(self.bucket, json.dumps(policy))
                print(f"✅ Bucket configurado como público")
            else:
                print(f"ℹ️  Bucket '{self.bucket}' ya existe")
        except S3Error as e:
            print(f"⚠️  Error con bucket: {e}")

    def upload_pdf(self, file_obj, file_hash, original_filename):
        """
        Sube un PDF a MinIO

        Args:
            file_obj: Objeto de archivo (BytesIO o FileStorage)
            file_hash: Hash SHA256 del archivo
            original_filename: Nombre original del archivo

        Returns:
            tuple: (url_publica, object_name)
        """
        # Estructura: jurisprudencia/AB/CD/ABCD1234.pdf
        prefix = f"{file_hash[:2]}/{file_hash[2:4]}"
        object_name = f"{prefix}/{file_hash}.pdf"

        # Obtener tamaño del archivo
        file_obj.seek(0)
        file_size = len(file_obj.read())
        file_obj.seek(0)

        try:
            # Subir archivo
            self.client.put_object(
                self.bucket,
                object_name,
                file_obj,
                file_size,
                content_type='application/pdf',
                metadata={
                    'original_filename': original_filename,
                    'uploaded_at': datetime.now().isoformat(),
                    'file_hash': file_hash
                }
            )

            # Construir URL pública
            protocol = "https" if self.use_ssl else "http"
            url = f"{protocol}://{self.endpoint}/{self.bucket}/{object_name}"

            print(f"✅ PDF subido a MinIO: {object_name}")
            return url, object_name

        except S3Error as e:
            print(f"❌ Error subiendo a MinIO: {e}")
            raise

    def delete_pdf(self, object_name):
        """Elimina un PDF de MinIO"""
        try:
            self.client.remove_object(self.bucket, object_name)
            print(f"✅ PDF eliminado de MinIO: {object_name}")
            return True
        except S3Error as e:
            print(f"❌ Error eliminando de MinIO: {e}")
            return False

    def get_presigned_url(self, object_name, expires=3600):
        """Genera URL pre-firmada (para archivos privados)"""
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            print(f"❌ Error generando URL: {e}")
            return None

    def test_connection(self):
        """Probar conexión a MinIO"""
        try:
            # Listar buckets
            buckets = self.client.list_buckets()
            print(f"✅ Conectado a MinIO")
            print(f"   Endpoint: {self.endpoint}")
            print(f"   Buckets: {[b.name for b in buckets]}")
            return True
        except Exception as e:
            print(f"❌ Error conectando a MinIO: {e}")
            return False

# Singleton
minio_client = MinIOClient()

if __name__ == "__main__":
    print("🔍 Testeando conexión a MinIO...\n")
    minio_client.test_connection()
