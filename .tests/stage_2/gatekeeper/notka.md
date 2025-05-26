
# 🔐 Gatekeeper – reguły bezpieczeństwa (Maj 2025)

### ✅ Stan wdrożenia:

- Gatekeeper zainstalowany w overlay `full-security`
- Synchronizacja przez ArgoCD z `gatekeeper-core/` i `gatekeeper-policies/`
- Włączona 1 reguła (`no-hostpath`) – **działa poprawnie**
- ConstraintTemplates i Constraints wersjonowane w repo
- Synchronizacja reguł przez ArgoCD (`sync-wave: 0` dla templatek, `1` dla constraints)

---

## 📌 Wybrane 4 reguły (Gatekeeper-only – unikalne, nie dublują PSA/RBAC)

### ✅ 1. Approved container registries

**Opis:** Blokuje obrazy z niezaufanych źródeł – dopuszcza tylko konkretne rejestry (np. `registry.mycorp.local`, `ghcr.io/org/`).

**Cel:** Eliminacja pullowania publicznych/losowych obrazów z DockerHub.

---

### ✅ 2. Wymagane `resources.requests` i `resources.limits`

**Opis:** Każdy kontener musi mieć określone limity CPU i RAM.

**Cel:** Zapobieganie awariom, crashom, nadmiernemu zużyciu zasobów (OOM, starving).

---

### ✅ 3. Read-only root filesystem

**Opis:** Kontener nie może mieć zapisu do systemu plików (`readOnlyRootFilesystem: true`).

**Cel:** Zmniejszenie powierzchni ataku, utrudnienie exploitów.

---

### ✅ 4. Zakaz `automountServiceAccountToken: true`

**Opis:** Blokuje automatyczne mountowanie tokena SA do kontenera.

**Cel:** Ochrona przed eksfiltracją tokenów serwisowych i eskalacją uprawnień.

---

## 🛠️ Struktura YAML w repo

```
overlays/
  full-security/
    gatekeeper-core/
      kustomization.yaml
      gatekeeper.yaml
    gatekeeper-policies/
      constraint-templates/
        approved-registries.yaml
        resources-required.yaml
        readonly-fs.yaml
        no-sa-token.yaml
        kustomization.yaml
      constraints/
        enforce-approved-registries.yaml
        enforce-resources.yaml
        enforce-readonly-fs.yaml
        deny-sa-token.yaml
        kustomization.yaml
```

---

## ✨ Dodatki

- `argocd.argoproj.io/sync-wave` ustawiony poprawnie (`0` dla szablonów, `1` dla reguł)
- Wszystkie reguły kompatybilne z PSA restricted
- Pełna historia reguł w Git

---

## 🧪 Kolejne kroki

- [ ] Testy reguł na aplikacjach dev/prod
- [ ] Zrobienie dashboardu audit + deny w Gatekeeperze
- [ ] Integracja z Trivy/Falco (feedback loop)

---

📅 **Status na Maj 2025: reguły Gatekeepera wdrożone i unikalnie domykają to, czego nie obejmuje PSA ani RBAC.**
