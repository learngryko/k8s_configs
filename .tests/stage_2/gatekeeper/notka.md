# 🔐 Gatekeeper – reguły bezpieczeństwa (Maj 2025 – aktualizacja)

### ✅ Stan wdrożenia:

- Gatekeeper w pełni zainstalowany w overlay `full-security`
- Synchronizacja przez Argo CD z katalogów:
  - `gatekeeper-core/` – instaluje CRD + ConstraintTemplates
  - `gatekeeper-policies/` – zawiera Constraints
- ConstraintTemplates i Constraints są **wersjonowane w repo i zarządzane przez Argo CD**
- Synchronizacja oparta o **`sync-waves`** (ApplicationSet)
```
elements:
  - name: gatekeeper-core
    path: overlays/full-security/gatekeeper-core
    wave: "0"
  - name: gatekeeper-policies
    path: overlays/full-security/gatekeeper-policies
    wave: "1"
  - name: namespace-patches
    path: overlays/full-security/namespace-patches
    wave: "3"
```

---

## 🛡️ Wdrożone reguły (Gatekeeper-only – unikalne względem PSA/RBAC)

### ✅ 1. Zakaz `hostPath` – `K8sPSPHostFilesystem`
**Opis:** Blokuje możliwość użycia wolumenów typu `hostPath` w podach.  
**Cel:** Ograniczenie dostępu do systemu plików hosta i powierzchni ataku.  
**Status:** Synced ✅

### ✅ 2. Tylko zatwierdzone rejestry obrazów – `K8sAllowedRepos`
**Opis:** Pozwala używać tylko obrazów z określonych rejestrów ( docker.io/library, docker.io).  
**Cel:** Blokada przypadkowych/publicznych obrazów z poza dockerhub.  
**Źródło Template:** [OPA Gatekeeper Library – allowedrepos](https://github.com/open-policy-agent/gatekeeper-library/tree/master/library/general/allowedrepos)  
**Status:** Synced ✅

### ✅ 3. Wymagane `resources.requests` i `resources.limits` – `K8sRequiredResources`
**Opis:** Wymusza zdefiniowanie limitów CPU i pamięci dla wszystkich kontenerów.  
**Cel:** Zapobieganie OOM, crashom, starvacji zasobów.  
**Źródło Template:** [OPA Gatekeeper Library – requiredresources](https://open-policy-agent.github.io/gatekeeper-library/website/validation/containerresources)  
**Status:** Synced ✅

### ✅ 4. Read-only root filesystem – `K8sPSPReadOnlyRootFilesystem`
**Opis:** Wymusza `readOnlyRootFilesystem: true` we wszystkich kontenerach.  
**Cel:** Redukcja powierzchni ataku i trwałości exploita.  
**Źródło Template:** [OPA Gatekeeper Library – readonlyrootfilesystem](https://github.com/open-policy-agent/gatekeeper-library/tree/master/library/pod-security-policy/readonlyrootfilesystem)  
**Status:** Synced ✅

### ✅ 5. Zakaz automountowania tokenów – `K8sPSPAutomountServiceAccountTokenPod`
**Opis:** Blokuje `automountServiceAccountToken: true` w definicji Poda.  
**Cel:** Ochrona przed eksfiltracją tokenów i eskalacją uprawnień.  
**Źródło Template:** [OPA Gatekeeper Library – automount-serviceaccount-token](https://github.com/open-policy-agent/gatekeeper-library/tree/master/library/pod-security-policy/automountserviceaccounttoken)  
**Status:** Synced ✅

---

## 🛠️ Struktura katalogów w repo

```
overlays/full-security/
├── kustomization.yaml
│
├── gatekeeper-core/
│   ├── gatekeeper.yaml
│   ├── constraint-template.yaml                            ← szablon deny-hostpath
│   ├── constraint-template-k8sallowedrepos.yaml            ← allowed image registries
│   ├── constraint-template-k8srequiredresources.yaml       ← wymagane CPU/RAM
│   ├── constraint-template-k8spspreadonlyrootfilesystem.yaml
│   ├── constraint-template-k8spspautomountserviceaccounttokenpod.yaml
│   └── kustomization.yaml
│
├── gatekeeper-policies/
│   ├── kustomization.yaml
│   └── constraints/
│       ├── deny-hostpath.yaml
│       ├── allowed-registries.yaml
│       ├── require-resources.yaml
│       ├── readonly-rootfs.yaml
│       ├── no-serviceaccount-token.yaml
│       └── kustomization.yaml
│
└── namespace-patches/
    └── calico-system.yaml
```

---

## ✨ Techniczne szczegóły

- ✅ Wszystkie ConstraintTemplates pochodzą z oficjalnego [OPA Gatekeeper Library](https://github.com/open-policy-agent/gatekeeper-library)
- ✅ Argo CD automatycznie synchronizuje zmiany (`automated`, `selfHeal`, `prune`)
- ✅ Wszystkie Constraints mają poprawne `kind` oraz `metadata.name`
- ✅ Obsługiwane namespace’e można precyzować przez `match.namespaces:` lub `namespaceSelector`

---

📅 **Status na Maj 2025: Gatekeeper aktywnie egzekwuje 5 reguł bezpieczeństwa. Instalacja stabilna, konfiguracja zgodna z Argo CD i GitOps. Gotowe na przyszłe rozszerzenia.**
