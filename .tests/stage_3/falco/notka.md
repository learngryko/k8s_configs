
# 🔒 Falco – Wdrożenie bezpieczeństwa w Kubernetes

## 🎯 Cel
Monitorowanie zdarzeń bezpieczeństwa w klastrze Kubernetes przy pomocy Falco z dodatkową konfiguracją niestandardowych reguł i pluginów.

---

## 📦 Komponenty

### Namespace
- `falco` z etykietami `pod-security` ustawionymi na `privileged`.

### RBAC
- Falco ma konto serwisowe z przypisaną rolą umożliwiającą dostęp do `ConfigMap`.
- ArgoCD ma `RoleBinding` do `ClusterRole admin` w namespace `falco`.

### ConfigMaps
- `falco`: główny config Falco.
- `falco-falcoctl`: konfiguracja narzędzia `falcoctl`.
- `falco-rules-custom`: zawiera niestandardowe reguły (`known.yaml`).

### DaemonSet
- Falco działa jako `DaemonSet`, więc **każdy węzeł ma swój pod**, który **zbiera podejrzane akcje lokalnie**.
- Używany obraz: `falcosecurity/falco:0.40.0`.
- Mounty obejmują `/proc`, `/dev`, `/etc`, `/lib/modules`, itp.
- Webserver Falco działa na porcie `8765`.

### InitContainers
- `falco-driver-loader`: ładuje sterownik BPF.
- `falcoctl-artifact-install`: instaluje pluginy i rules.

### Pluginy
- `k8saudit`, `cloudtrail`, `json`.

### Reguły
- Niestandardowa reguła `Unexpected K8s API Connection (custom)` wykrywa nieautoryzowane połączenia do API serwera K8s.

---

## ⚙️ Parametry konfiguracyjne

- Silnik: `modern_ebpf`.
- Uprawnienia: kontener Falco działa z `privileged`.
- `falcoctl` automatycznie śledzi nowe reguły i pluginy co 6 godzin.

---

## ✅ Dodatkowe informacje

- Logowanie aktywne do `stdout` i `syslog`.
- `known.yaml` zawiera dozwolone procesy i obrazy dla połączeń do API serwera.
