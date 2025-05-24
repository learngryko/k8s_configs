# 🔐 RBAC – Polityka i Wyniki Testów (Stage 1)

## 🎯 Polityka Dostępu

| Rola        | Namespace      | Dostęp |
|-------------|----------------|--------|
| `viewer`    | `dev`, `prod`, `monitoring` | tylko `get`, `list`, `watch` podstawowych zasobów |
| `dev`       | `dev`          | pełen dostęp do aplikacji, **bez ról/clusterroles** |
| `dev`       | `prod`, `monitoring` | ❌ brak dostępu |
| `ops`       | wszędzie       | pełen dostęp (`*`) |

---

## 🧪 Zakres testów

Zasoby: `pods`, `services`, `configmaps`, `secrets`, `deployments`, `jobs`, `pods/exec`, `rolebindings`, `roles`, `clusterroles`, `patch`, `delete`, `list`, `watch`.

---

## ✅ Wyniki Testów RBAC

| Użytkownik  | Namespace   | Akcja                        | Oczekiwany | Wynik testu |
|-------------|-------------|------------------------------|------------|-------------|
| viewer      | dev         | get pods                     | ✅         | ✅ PASS     |
| viewer      | dev         | list services                | ✅         | ✅ PASS     |
| viewer      | dev         | watch configmaps             | ✅         | ✅ PASS     |
| viewer      | dev         | create configmaps            | ❌         | ✅ PASS     |
| viewer      | dev         | delete pods                  | ❌         | ✅ PASS     |
| viewer      | dev         | get secrets                  | ❌         | ✅ PASS     |
| viewer      | prod        | get pods                     | ✅         | ✅ PASS     |
| viewer      | prod        | get secrets                  | ❌         | ✅ PASS     |
| viewer      | prod        | create rolebindings          | ❌         | ✅ PASS     |
| viewer      | monitoring  | list pods                    | ✅         | ✅ PASS     |
| viewer      | monitoring  | delete configmaps            | ❌         | ✅ PASS     |
| viewer      | monitoring  | create pods/exec             | ❌         | ✅ PASS     |
| dev         | dev         | get pods                     | ✅         | ✅ PASS     |
| dev         | dev         | create deployments           | ✅         | ✅ PASS     |
| dev         | dev         | create pods/exec             | ✅         | ✅ PASS     |
| dev         | dev         | delete secrets               | ✅         | ✅ PASS     |
| dev         | dev         | create jobs                  | ✅         | ✅ PASS     |
| dev         | dev         | patch pods                   | ✅         | ✅ PASS     |
| dev         | dev         | create role                  | ❌         | ✅ PASS     |
| dev         | dev         | create clusterrole           | ❌         | ✅ PASS     |
| dev         | prod        | get pods                     | ❌         | ✅ PASS     |
| dev         | prod        | create secrets               | ❌         | ✅ PASS     |
| dev         | monitoring  | list jobs                    | ❌         | ✅ PASS     |
| dev         | monitoring  | delete pods                  | ❌         | ✅ PASS     |
| ops         | dev         | delete pods                  | ✅         | ✅ PASS     |
| ops         | dev         | create rolebindings          | ✅         | ✅ PASS     |
| ops         | dev         | create pods/exec             | ✅         | ✅ PASS     |
| ops         | dev         | create clusterrole           | ✅         | ✅ PASS     |
| ops         | dev         | * *                          | ✅         | ✅ PASS     |
| ops         | prod        | delete secrets               | ✅         | ✅ PASS     |
| ops         | prod        | create jobs                  | ✅         | ✅ PASS     |
| ops         | prod        | patch pods                   | ✅         | ✅ PASS     |
| ops         | monitoring  | delete pods                  | ✅         | ✅ PASS     |
| ops         | monitoring  | get secrets                  | ✅         | ✅ PASS     |
| ops         | monitoring  | create pods/exec             | ✅         | ✅ PASS     |
| ops         | monitoring  | delete rolebindings          | ✅         | ✅ PASS     |
"""