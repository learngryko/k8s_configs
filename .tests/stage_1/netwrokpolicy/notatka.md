# 🛡️ NetworkPolicy – Notatka wdrożeniowa

## 🎯 Cel
Wdrożyć politykę sieciową, która:
- Domyślnie blokuje cały ruch między podami (zero trust).
- Pozwala tylko niezbędne wyjątki (DNS, monitoring, ingress, ArgoCD itp.).
- Zgodna z obecnym podziałem namespace (`dev`, `prod`, `monitoring`).
- Zgodna z overlay `native-only`.

---

## 📐 Założenia

- `dev`, `prod`, `monitoring` są osobnymi namespace’ami.
- W każdej przestrzeni mają działać tylko jasno określone przepływy.
- Monitoring działa centralnie (np. Prometheus/Loki w `monitoring`).
- Aplikacje w `dev` mogą wysyłać dane do `monitoring`.
- Każdy namespace ma dostać:
  - politykę `deny all ingress`
  - politykę `deny all egress`
  - wyjątek DNS (UDP/53 do CoreDNS)
  - ewentualne otwarcia na monitoring, ingress, ArgoCD

---

## 📁 Struktura repo

Utwórz:

```
k8s_configs/
└── overlays/
    └── native-only/
        └── networkpolicy/
            ├── default-deny.yaml
            ├── allow-dns.yaml
            ├── allow-monitoring.yaml
            └── allow-egress-to-monitoring.yaml
```

---

## 🧩 Pliki `.yaml`

### 1. `default-deny.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: <ns>
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### 2. `allow-dns.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: <ns>
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

### 3. `allow-monitoring.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-ingress
  namespace: <ns>
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

### 4. `allow-egress-to-monitoring.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-egress-to-monitoring
  namespace: dev
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

## ✅ Kroki wdrożeniowe

1. Stwórz `networkpolicy/` folder w overlay `native-only`.
2. Dodaj powyższe YAML-e z odpowiednimi namespace.
3. Uzupełnij `overlays/native-only/kustomization.yaml`:
```yaml
resources:
  - networkpolicy/default-deny.yaml
  - networkpolicy/allow-dns.yaml
  - networkpolicy/allow-monitoring.yaml
  - networkpolicy/allow-egress-to-monitoring.yaml
```
1. Commit + push – ArgoCD zdeployuje i zsynchronizuje.
2. Zweryfikuj działanie poprzez np. `kubectl exec` i `ping`, `nc`.

---

## 🧪 Testy

- brak połączenia `podA → podB` w tym samym namespace = OK
- `nslookup` działa = OK
- `dev → monitoring` (np. Loki push) = OK
- `monitoring → dev` (Prometheus scrape) = OK

---

# 🧠 Dodatkowe uwagi

- jeśli ArgoCD działa w osobnym namespace, dodaj mu wyjątek
- analogicznie: jeśli masz ingress controller (nginx/istio), trzeba go dopuścić
- opcjonalnie: dodaj label `name: <ns>` do każdego namespace, żeby działały `namespaceSelector`
