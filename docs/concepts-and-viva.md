# Concepts and viva notes

Plain-language explanations of everything used in this experiment, followed by likely evaluation questions.

---

## 1. The experiment in one paragraph

A local Kubernetes cluster (minikube) was started, Metrics Server and the Dashboard were enabled so resource usage
could be seen, a sample app (`php-apache`) was deployed with a CPU request but **no CPU limit**, usage was recorded at
idle, load was generated with a second pod, and usage was recorded again. The pod's CPU rose from 1m to about 970m
(roughly one core) and held steady there, the node's CPU rose from 229m (1%) to 1230m (10%), and memory stayed small
(8Mi to 12Mi for the pod).

A restaurant analogy: the cluster is the kitchen, the app is the cook, the load is customers ordering, and
Metrics Server is the manager with a clipboard. `kubectl top` and the Dashboard are two ways of reading that same clipboard.

---

## 2. Concepts

**Kubernetes cluster / node.** A cluster is a set of machines (nodes) that run containers. minikube creates a
one-node cluster on your laptop.

**Pod.** The smallest deployable unit - a wrapper around one or more containers. `php-apache` and
`load-generator` are each one pod.

**Deployment.** Keeps a desired number of identical pods running and replaces them if they fail. `php-apache` is
a Deployment with 1 replica.

**Service.** A stable network name and address in front of pods. The load generator calls `http://php-apache`,
which the Service routes to the pod.

**Metrics Server.** A cluster add-on that collects current CPU and memory usage from each node's kubelet and serves
it through the Metrics API (`metrics.k8s.io`). It keeps no history and only tracks CPU and memory. `kubectl top`,
the Dashboard's usage figures, and the Horizontal Pod Autoscaler all rely on it.

**Kubernetes Dashboard.** A web UI for viewing and managing cluster resources. With Metrics Server running it
shows CPU and memory per pod and node.

**Millicores (m).** CPU units: 1000m = 1 core. 970m is a little under one core.

**Mi (mebibyte).** Memory units. `kubectl top` reports the working-set memory of the container.

**Requests vs limits.**
- *Request*: the amount the scheduler reserves; used to decide where a pod can run.
- *Limit*: the maximum the container may use.
- Exceeding a **CPU limit** causes **throttling** (the container is slowed, usage plateaus at the limit).
- Exceeding the **memory limit** causes an **OOM kill** (the container is terminated and restarted).
- In this experiment `php-apache` has a 100m CPU request, **no CPU limit**, and a 128Mi memory limit.

**Load generator.** A `busybox` pod running `while true; do wget -q -O- http://php-apache; done`. It sends
requests back to back. The `OK!` it receives is the application's reply; the real work happens in the app pod.

---

## 3. How `kubectl top` and the Dashboard get their numbers

```
container -> kubelet (cAdvisor) -> Metrics Server -> Metrics API -> kubectl top
                                                              └──-> Dashboard
```

Because both read from the same source, their values are expected to match. Small differences can appear when they
sample at slightly different moments, which is most noticeable at idle where values are tiny.

---

## 4. Likely evaluation questions

**What did you do?**
Set up a minikube cluster with Metrics Server and the Dashboard, deployed a CPU-intensive sample app with no CPU limit,
recorded pod and node usage with `kubectl top` at idle, generated load, and recorded usage again.

**Why do you need Metrics Server?**
Without it, `kubectl top` fails and the Dashboard has no CPU or memory data. It provides the resource metrics API.

**Where does Metrics Server get its data?**
From the kubelet on each node, which reads container statistics via cAdvisor.

**Does Metrics Server store history?**
No, only the latest values. Long-term history needs something like Prometheus.

**Why did you not write your own application?**
The lab asks to deploy "a sample application". `php-apache` is the standard Kubernetes example for resource and
autoscaling demos; it is CPU-bound by design, so load shows up clearly in the metrics.

**Why does a stream of `OK!` count as load?**
`OK!` is just the response. Each request makes the app run a CPU-heavy loop, which is why pod CPU went from 1m to 970m.

**Why did you not set a CPU limit?**
So the pod's CPU is set by the load instead of being capped by the configuration, which shows how much CPU the app
actually uses under this load. It is not a recommended production setting (see below).

**How did you confirm there is no CPU limit?**
`kubectl get deploy php-apache -o jsonpath='{.spec.template.spec.containers[0].resources}'` returned a memory limit of
128Mi and requests of 100m CPU and 64Mi memory, with no CPU limit.

**Why did CPU level off at about 970m?**
Nothing in the configuration capped it. Most likely the load generator sends one request at a time and the app serves it
on a single worker, so it can keep about one core busy. This was not tested; a heavier load or more replicas would show
whether usage can go higher.

**Why did memory barely change?**
The app does not retain data between requests, so memory does not accumulate (8Mi to 12Mi, far below the 128Mi limit).

**Why did node CPU rise so much?**
The pod used about 970m and the load generator about 24m, which together account for about 993m of the node's 1001m
increase (229m to 1230m). The remaining few millicores are other node processes, sampling time and rounding.

**Why did node memory barely change?**
The app's memory use is tiny (12Mi) compared with the node's memory, so the node figure only moved from 844Mi to 863Mi.

**Why are `kubectl top` and the Dashboard sometimes slightly different?**
They can sample at slightly different moments and Metrics Server refreshes only periodically. Both are backed by the
same Metrics Server data.

**What happens if a pod exceeds its CPU limit? Its memory limit?**
CPU: throttled. Memory: OOM-killed and restarted.

**Is running without a CPU limit a good idea in production?**
Not by default. Without a limit one busy pod can take CPU away from other workloads on the node. Limits are a
trade-off; here the aim was to understand the app's behaviour under load.

**Why is the CPU request (100m) a problem here?**
The app used about 9.7 times that (970m). Requests drive scheduling, so a request far below real usage can lead to
overcommitted nodes. Monitoring data like this is used to right-size requests and limits.

**Why did the Helm install of the Dashboard fail?**
The upstream Dashboard project was archived and the chart repo URL returned 404. The Dashboard bundled with minikube
(`minikube dashboard`) was used instead.

**Why does the pod name in the measurements differ from the one in the setup output?**
The Deployment was applied again from the no-CPU-limit manifest before the measurements. Changing a pod's resources makes
the Deployment create a new ReplicaSet and pod (`php-apache-bdf6ddcf8-bx4xb`) and terminate the old one.

**Why a single-node cluster? Would multi-node help?**
One node is enough because the goal is to observe usage change under load. A multi-node cluster would be useful for
studying scheduling and scaling across nodes, which is a different experiment.

**Is a GPU needed?**
No. Metrics Server reports only CPU and memory. GPU metrics need a separate exporter (for example NVIDIA DCGM).

**What would you do next?**
Add a Horizontal Pod Autoscaler (`manifests/optional/hpa.yaml`) so the cluster adds replicas when CPU is high, and add
Prometheus and Grafana for history and alerting.

**What are the limitations of your results?**
Values were sampled manually in a single run on a single node, the load was a single sequential loop, and the data
set contains `kubectl top` readings only (no Dashboard captures). See the README's limitations section.
