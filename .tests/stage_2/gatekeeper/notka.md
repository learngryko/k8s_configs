
# 🔐 Gatekeeper – reguły bezpieczeństwa (Maj 2025 – aktualizacja)

### ✅ Stan wdrożenia:

- Gatekeeper w pełni zainstalowany w overlay `full-security`
- Synchronizacja przez Argo CD z katalogów:
  - `gatekeeper-core/` – instaluje CRD + ConstraintTemplates
  - `gatekeeper-policies/` – zawiera Constraints
- **1 aktywna reguła `deny-hostpath`** (`K8sPSPHostFilesystem`) – **działa poprawnie**
- ConstraintTemplates i Constraints są **wersjonowane w repo i zarządzane przez Argo CD**

---

## 🛡️ Wdrożone reguły (Gatekeeper-only – unikalne względem PSA/RBAC)

### ✅ 1. Zakaz `hostPath` – `K8sPSPHostFilesystem`

**Opis:** Blokuje możliwość użycia wolumenów typu `hostPath` w podach.  
**Cel:** Ograniczenie dostępu do systemu plików hosta i powierzchni ataku.  
**Status:** Synced, Healthy ✅

```yaml
parameters:
  allowedHostPaths: []
```

Reguła w trybie **"deny all hostPath"**, bez wyjątków.

---

## 🛠️ Struktura katalogów w repo

```
overlays/full-security/
├── kustomization.yaml
│
├── gatekeeper-core/
│   ├── gatekeeper.yaml
│   ├── constraint-template.yaml       ← szablon K8sPSPHostFilesystem
│   └── kustomization.yaml
│
├── gatekeeper-policies/
│   ├── kustomization.yaml
│   └── constraints/
│       ├── deny-hostpath.yaml         ← Constraint zakazujący hostPath
│       └── kustomization.yaml
│
└── namespace-patches/
    └── calico-system.yaml             ← patch dla namespace Calico
```

---

## ✨ Techniczne szczegóły

- ✅ Template `K8sPSPHostFilesystem` zawiera oba silniki walidacji: `K8sNativeValidation` + `Rego`
- ✅ Constraints i Template są w pełni kompatybilne z PSA (PodSecurityAdmission)
- ✅ Synchronizacja działa w pełni automatycznie dzięki `syncPolicy.automated` i `sync-waves`

---


📅 **Status na Maj 2025: Gatekeeper działa stabilnie, reguły są wdrożone z Argo CD, kontrola hostPath aktywna. System gotowy na dalsze rozszerzenia.**
