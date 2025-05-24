
# 🛡️ NetworkPolicy – Notatka wdrożeniowa  
*wersja folderowa, label: `native-security`*

---

## ❗️ Wymagania krytyczne  
> **UWAGA:**  
> Polityki NetworkPolicy w Kubernetes **NIE DZIAŁAJĄ bez zainstalowanego CNI obsługującego policy**, np. Calico, Cilium, Antrea.  
> Sam “czysty” klaster (np. z kube-proxy/flannel bez policy) *ignoruje* te polityki – sieć pozostaje otwarta!  
>  
> **Aby wyegzekwować polityki sieciowe, MUSISZ zainstalować Calico lub podobny plugin!**

---

## 🎯 Cel  

- Zbudować “zero trust” – blokować ruch domyślnie wszędzie (ingress/egress), otwierać tylko to, co konieczne.
- Trzymać całość NetworkPolicy w czytelnych folderach, per-namespace.
- W overlay `native-only` **aktywować wyłącznie to, co jest zadeklarowane w plikach YAML (nie używać custom resource'ów Calico!)** – masz kontrolę tylko przez NetworkPolicy K8s.
- Overlay `full-security` może zawierać dodatkowe reguły (np. globalne, zaawansowane CRD Calico itd.).

---

## 📐 Założenia

- Namespace: `dev`, `prod`, `monitoring`
- Monitoring scentralizowany (Prometheus/Loki/… w `monitoring`)
- Ruch cross-namespace: tylko tam, gdzie NetworkPolicy na to pozwala
- **Każdy namespace**:
  - polityka deny-all (ingress+egress)
  - wyjątek DNS
  - wyjątek monitoring
  - opcjonalnie egress na monitoring (np. do pushowania logów)
  - dodatkowe wyjątki (np. ArgoCD, ingress) jeśli trzeba

---

## 📁 Struktura repozytorium (każdy ns = osobny folder)

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
            │   └── allow-egress-to-monitoring.yaml # jeśli potrzebujesz
            └── monitoring/
                ├── default-deny.yaml
                ├── allow-dns.yaml
                └── allow-monitoring.yaml # jeśli potrzebujesz
```

---

## 🧩 Przykładowe pliki `.yaml` (na przykładzie `dev`)

Wszystkie pliki mają labele:

```yaml
metadata:
  labels:
    app.kubernetes.io/managed-by: argocd
    app.kubernetes.io/component: networkpolicy
    app.kubernetes.io/name: networkpolicy-dev
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

### `allow-egress-to-monitoring.yaml` *(opcjonalnie)*

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

Analogiczne pliki dla `prod`, `monitoring` — zmieniasz tylko namespace i nazwę.

---

## 🛠️ Kustomization.yaml

W `overlays/native-only/kustomization.yaml`:

```yaml
resources:
  - networkpolicy/dev/
  - networkpolicy/prod/
  - networkpolicy/monitoring/
```

---

## 🏷️ Labele namespace

W plikach Namespace (`base/namespaces/dev.yaml`):

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

1. Utwórz strukturę folderów (per namespace).
2. Wklej powyższe pliki z odpowiednimi labelami.
3. Uzupełnij kustomization.yaml.
4. Dodaj/uzupełnij labele do Namespace.
5. Commit + push (ArgoCD zrobi resztę).
6. Przetestuj connectivity testerem i poleceniami kubectl.

---

## 🧪 Testy

- Brak połączenia `podA → podB` w tym samym namespace (zero trust).
- `nslookup` działa tylko tam, gdzie jest allow-dns.
- `dev → monitoring` (Loki push) = OK, jeśli masz allow-egress-to-monitoring.
- `monitoring → dev` oraz `monitoring → prod` (Prometheus scrape) = OK, jeśli masz allow-monitoring.

---

## 🧠 Dodatkowe uwagi

- Jeśli ArgoCD lub ingress działa w osobnym namespace, dodaj wyjątek.
- Każdy namespace musi mieć label `name: <ns>`, żeby działały namespaceSelector.
- Overlay “full-security” może mieć własne, dodatkowe polityki (np. custom resource Calico), ale overlay “native-only” korzysta wyłącznie z czystego NetworkPolicy.

---

**PAMIĘTAJ:**
> **NetworkPolicy NIE DZIAŁA bez Calico, Cilium, Antrea lub innego CNI obsługującego polityki!**
> 
> Po zainstalowaniu Calico polityki zaczną działać natychmiast, tylko w ramach tego co zadeklarujesz w YAML (overlay native-only = tylko K8s NetworkPolicy, bez custom CRD Calico).

---

## 🔁 Full-security vs native-only (quick summary)

- **native-only**:  
  - tylko standardowe NetworkPolicy K8s (to, co jest w plikach powyżej)
  - działa tylko na CNI z obsługą policy (np. Calico, ale bez użycia zaawansowanych CRD)
- **full-security**:  
  - możesz dodać zaawansowane polityki, np. Calico GlobalNetworkPolicy, custom labels itd.
  - możesz integrować OPA Gatekeeper, Falco, Trivy, itp.
