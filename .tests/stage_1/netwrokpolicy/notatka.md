
# 🛡️ NetworkPolicy – Notatka wdrożeniowa  
*wersja folderowa, label: `native-security`*

---

## ❗️ Wymagania krytyczne  
> **UWAGA:**  
> Polityki NetworkPolicy w Kubernetes **DZIAŁAJĄ**, ponieważ **Calico został zainstalowany wraz z klastrem w Rancherze**.  
---

## 🎯 Cel  
- Zbudować “zero trust” – blokować wszystko domyślnie, otwierać tylko to, co wymagane.
- Folderowa organizacja per-namespace.
- `native-only` = tylko czyste NetworkPolicy (bez Calico CRD).
- `full-security` = rozszerzenia i CRD dozwolone.

---

## 📐 Założenia  

Namespace: `dev`, `prod`, `monitoring`  
- Domyślny `deny-all` (ingress+egress) w każdym namespace  
- Wyjątki:
  - DNS tylko w `dev`
  - egress `dev → monitoring` dla logów
  - ingress `monitoring` z `dev` i `prod`
  - `dev → dev` dozwolone
  - `monitoring` nie ma egress – tylko odbiera

---

## ✅ Kroki wdrożeniowe

1. Sprawdź, czy polityki są zdefiniowane dla każdego namespace:
   - default-deny
   - allow-egress/ingress (jeśli potrzebne)
   - allow-dns tylko tam, gdzie wymagane
2. Upewnij się, że każdy namespace ma label `name: <ns>`.
3. Commit + push → ArgoCD zaktualizuje stan.
4. Przetestuj (poniżej wyniki ostatniego testu).

---

## 🧾 Pliki konfiguracyjne (opis)

### `dev/`
- `default-deny.yaml`: blokuje cały ruch
- `allow-dns.yaml`: umożliwia zapytania DNS do kube-dns
- `allow-egress-to-monitoring.yaml`: zezwala na egress do monitoring
- `allow-egress-to-dev.yaml`: zezwala na egress do własnego namespace
- `allow-dev-to-self.yaml`: pozwala na komunikację pomiędzy podami w `dev`
- `kustomization.yaml`: łączy powyższe pliki

### `monitoring/`
- `default-deny.yaml`: blokuje cały ruch
- `allow-from-prod-and-dev.yaml`: zezwala na połączenia przychodzące z `dev` i `prod`
- `kustomization.yaml`: łączy polityki monitoringu

### `prod/`
- `default-deny.yaml`: blokuje cały ruch
- `allow-egress-to-monitoring.yaml`: zezwala na egress z `prod` do `monitoring`
- `kustomization.yaml`: łączy polityki `prod`

---

## 🧪 Wyniki testów (ostatnie uruchomienie)

### DNS Summary
```
dev/test-pod-1-dev:          DNS ALLOWED  
dev/test-pod-2-dev:          DNS ALLOWED  
prod/test-pod-1-prod:        DNS BLOCKED  
prod/test-pod-2-prod:        DNS BLOCKED  
monitoring/test-pod-1:       DNS BLOCKED  
monitoring/test-pod-2:       DNS BLOCKED  
```

### Network Policy Matrix (ping)
```
                dev-1   dev-2   prod-1  prod-2  monitoring-1  monitoring-2
dev-1           ✅       ✅       ❌       ❌       ✅             ✅
dev-2           ✅       ✅       ❌       ❌       ✅             ✅
prod-1          ❌       ❌       ✅       ❌       ✅             ✅
prod-2          ❌       ❌       ❌       ✅       ✅             ✅
monitoring-1    ❌       ❌       ❌       ❌       ✅             ❌
monitoring-2    ❌       ❌       ❌       ❌       ❌             ✅
```

### Podsumowanie testu
```
Total connections tested: 36  
BLOCKED: 20  
ALLOWED: 16
```

### Unexpectedly ALLOWED connections:
```
- prod-2 → monitoring-1  
- dev-1 → dev-2  
- prod-1 → monitoring-2  
- dev-2 → monitoring-1  
- dev-1 → monitoring-1  
- prod-2 → monitoring-2  
- dev-1 → monitoring-2  
- dev-2 → dev-1  
- prod-1 → monitoring-1  
- dev-2 → monitoring-2  
```

> ❗️ **Uwaga:** Powyższe wyniki są zgodne z aktualnie wdrożonymi politykami – wszystkie połączenia są świadomie dozwolone na tym etapie.

---

