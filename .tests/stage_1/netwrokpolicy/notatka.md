# 🛡️ NetworkPolicy – Notatka wdrożeniowa (wersja folderowa, label: native-security)

## 🎯 Cel  
Wdrożyć politykę sieciową, która:
- Domyślnie blokuje cały ruch między podami (zero trust).
- Pozwala tylko niezbędne wyjątki (DNS, monitoring, ingress, ArgoCD itp.).
- Zgodna z obecnym podziałem namespace (`dev`, `prod`, `monitoring`).
- Zgodna z overlay `native-only`.

---

## 📐 Założenia

- `dev`, `prod`, `monitoring` to osobne namespace’y.
- Monitoring centralny (`monitoring`), aplikacje z `dev` i `prod` mogą być scrapowane przez Prometheusa/Loki.
- Aplikacje w `dev` i `prod` mogą wysyłać dane do `monitoring` (jeśli potrzebujesz).
- Każdy namespace:
  - polityka deny all (ingress+egress)
  - wyjątek DNS
  - wyjątek na monitoring
  - opcjonalnie egress do monitoring
  - ewentualne inne wyjątki (ArgoCD, ingress)

---

## 📁 Struktura repo (per-namespace!)

```
k8s_configs/
└── overlays/
    └── native-only/
        └── networkpolicy/
            ├── dev/
            │   ├── default-deny.yaml
            │   ├── allow-dns.yaml
            │   ├── allow-monitoring.yaml
            │   └── allow-egress-to-monitoring.yaml
            ├── prod/
            │   ├── default-deny.yaml
            │   ├── allow-dns.yaml
            │   ├── allow-monitoring.yaml
            │   └── allow-egress-to-monitoring.yaml # jeśli potrzebujesz z prod do monitoring
            └── monitoring/
                ├── default-deny.yaml
                ├── allow-dns.yaml
                └── allow-monitoring.yaml
```

---

## 🧩 Pliki `.yaml` (przykład: dev)

**Wszystkie pliki mają label:**
```yaml
metadata:
  labels:
    app.kubernetes.io/managed-by: argocd
    app.kubernetes.io/component: networkpolicy
    app.kubernetes.io/name: networkpolicy-<ns>
    app.kubernetes.io/part-of: native-security
```

---

### `default-deny.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: dev
  labels:
    app.kubernetes.io/managed-by: argocd
    app.kubernetes.io/component: networkpolicy
    app.kubernetes.io/name: networkpolicy-dev
    app.kubernetes.io/part-of: native-security
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

---

### `allow-dns.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: dev
  labels:
    app.kubernetes.io/managed-by: argocd
    app.kubernetes.io/component: networkpolicy
    app.kubernetes.io/name: networkpolicy-dev
    app.kubernetes.io/part-of: native-security
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

---

### `allow-monitoring.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-ingress
  namespace: dev
  labels:
    app.kubernetes.io/managed-by: argocd
    app.kubernetes.io/component: networkpolicy
    app.kubernetes.io/name: networkpolicy-dev
    app.kubernetes.io/part-of: native-security
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
```

---

### `allow-egress-to-monitoring.yaml` *(jeśli potrzebujesz push z dev/prod do monitoring, np. Loki)*

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-egress-to-monitoring
  namespace: dev
  labels:
    app.kubernetes.io/managed-by: argocd
    app.kubernetes.io/component: networkpolicy
    app.kubernetes.io/name: networkpolicy-dev
    app.kubernetes.io/part-of: native-security
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: monitoring
```

---

**Analogicznie dla prod/monitoring – tylko zmień `namespace:` i `networkpolicy-prod`/`networkpolicy-monitoring` w labelach.**

---

## 🛠️ Kustomization.yaml

W `overlays/native-only/kustomization.yaml`:
```yaml
resources:
  - networkpolicy/dev/
  - networkpolicy/prod/
  - networkpolicy/monitoring/
```
Dzięki temu ładuje wszystkie pliki per-namespace.

---

## 🏷️ Labele na Namespace

W plikach Namespace (`base/namespaces/dev.yaml` itd.):

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dev
  labels:
    name: dev
    app.kubernetes.io/part-of: native-security
```

---

## ✅ Kroki wdrożeniowe

1. Utwórz foldery jak powyżej, każdy namespace osobno.
2. Wklej YAML-e z odpowiednimi labelami.
3. Uzupełnij kustomization.yaml.
4. Dodaj label do Namespace.
5. Commit + push (ArgoCD zrobi resztę).
6. Przetestuj connectivity (kubectl exec, ping, nslookup, monitoring, etc).

---

## 🧪 Testy

- brak połączenia `podA → podB` w tym samym namespace = OK
- `nslookup` działa = OK
- `dev → monitoring` (np. Loki push) = OK
- `monitoring → dev` oraz `monitoring → prod` (Prometheus scrape) = OK

---

## 🧠 Dodatkowe uwagi

- Jeśli ArgoCD działa w osobnym namespace – dodaj wyjątek.
- Analogicznie dla ingress controller (np. nginx/istio).
- Każdy namespace musi mieć label `name: <ns>`, żeby działał namespaceSelector.

---

**TL;DR:**  
Foldery per namespace, wszystkie YAML-e z labelami  
`app.kubernetes.io/part-of: native-security`.  
Kustomization na foldery, label na Namespace.  
Pełny zero trust, tylko potrzebne wyjątki.  