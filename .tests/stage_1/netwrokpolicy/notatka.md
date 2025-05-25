
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
- Ruch cross-namespace: tylko tam, gdzie NetworkPolicy na to pozwala
- **Każdy namespace**:
  - polityka deny-all (ingress+egress)
  - wyjątek DNS
  - wyjątek monitoring
  - opcjonalnie egress na monitoring (np. do pushowania logów)
  - dodatkowe wyjątki (np. ArgoCD, ingress) jeśli trzeba


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
