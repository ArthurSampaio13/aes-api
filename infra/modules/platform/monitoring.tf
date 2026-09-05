resource "random_password" "grafana" {
  length  = 20
  special = false
}

resource "helm_release" "kube_prometheus_stack" {
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = var.kube_prometheus_stack_version
  namespace  = kubernetes_namespace.monitoring.metadata[0].name
  timeout    = 900

  values = [file("${path.module}/files/kps-values.yaml")]

  set_sensitive {
    name  = "grafana.adminPassword"
    value = random_password.grafana.result
  }
}
