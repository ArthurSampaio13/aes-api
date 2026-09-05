resource "kubernetes_secret" "localstack" {
  metadata {
    name      = "localstack-credentials"
    namespace = kubernetes_namespace.app.metadata[0].name
  }

  data = {
    LOCALSTACK_AUTH_TOKEN = var.localstack_auth_token
  }
}

resource "kubernetes_config_map" "localstack_init" {
  metadata {
    name      = "localstack-init"
    namespace = kubernetes_namespace.app.metadata[0].name
  }

  data = {
    "01-provision.sh" = file("${path.module}/files/localstack-ready.sh")
  }
}

resource "kubernetes_deployment" "localstack" {
  metadata {
    name      = "localstack"
    namespace = kubernetes_namespace.app.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = { app = "localstack" }
    }

    template {
      metadata {
        labels = { app = "localstack" }
      }

      spec {
        container {
          name  = "localstack"
          image = "localstack/localstack:4"

          port {
            name           = "edge"
            container_port = 4566
          }

          env {
            name  = "SERVICES"
            value = "s3,sqs"
          }

          env {
            name = "LOCALSTACK_AUTH_TOKEN"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.localstack.metadata[0].name
                key  = "LOCALSTACK_AUTH_TOKEN"
              }
            }
          }

          env {
            name  = "AES_STORAGE_BUCKET"
            value = var.storage_bucket
          }

          env {
            name  = "AES_SQS_QUEUE_NAME"
            value = var.sqs_queue_name
          }

          volume_mount {
            name       = "init"
            mount_path = "/etc/localstack/init/ready.d"
          }

          readiness_probe {
            http_get {
              path = "/_localstack/health"
              port = 4566
            }
            initial_delay_seconds = 10
            period_seconds        = 5
            failure_threshold     = 30
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "512Mi"
            }
            limits = {
              memory = "1536Mi"
            }
          }
        }

        volume {
          name = "init"
          config_map {
            name         = kubernetes_config_map.localstack_init.metadata[0].name
            default_mode = "0755"
          }
        }
      }
    }
  }

  wait_for_rollout = true
}

resource "kubernetes_service" "localstack" {
  metadata {
    name      = "localstack"
    namespace = kubernetes_namespace.app.metadata[0].name
  }

  spec {
    selector = { app = "localstack" }

    port {
      name        = "edge"
      port        = 4566
      target_port = 4566
    }
  }
}

locals {
  localstack_endpoint = "http://localstack.${var.app_namespace}.svc.cluster.local:4566"
  sqs_queue_url       = "${local.localstack_endpoint}/000000000000/${var.sqs_queue_name}"
}
