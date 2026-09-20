# Backend Interview Knowledge

Use the relevant section as practical reference. Keep answers concise, specific,
and grounded in production trade-offs. When a section uses A1-A5, cover the
applicable points without turning the answer into a generic theory checklist.

## MongoDB / NoSQL / AgriTech schema

- A1: Chon MongoDB khi schema linh hoat (farm khac nhau khac sensor/thiet bi), can horizontal scaling, hoac document nested (crop cycles, sensor readings) hop hon mo hinh quan he.
- A2: Embed du lieu doc thuong (sensor snapshot) vao farm document de giam join; reference collection lon/luu lich su de tranh document bloat.
- A3: Index: compound `{farmId, timestamp}` cho time-series; geo index neu bao cao theo vi tri.
- A4: Aggregation pipeline cho xu ly scale, vi du trung binh do am dat theo region tren nhieu document; tranh nhieu query roi rac.
- A5: IoT real-time: can nhac MongoDB Time Series Collections (tu v5.0), toi uu write-heavy va compression.
- Neu chua lam MongoDB production: thanh that, lien he cong nghe tuong du nhu SQL/Redis, va neu cach onboarding nhanh.

## Spring Boot REST / scale

- A1: Controller-Service-Repository, HTTP status chuan, pagination moi list endpoint.
- A2: Stateless + JWT, Redis cache query nong, HikariCP connection pool.
- A3: `@Async` + thread pool cho task nang nhu IoT pipeline, khong block request thread.
- A4: API versioning `/v1`, `/v2` tu dau va giu backward compatibility.
- A5: Actuator + Prometheus/Grafana hoac cong cu tuong du; dung du lieu thuc te de tim bottleneck.

## Microservices / CI-CD / production failure

- Circuit breaker voi Resilience4j.
- CI flow: test -> Docker -> staging -> smoke test -> blue-green production.
- Health check va Kubernetes liveness/readiness.
- Distributed tracing voi Jaeger/Zipkin.
- Feature flags de rollback nhanh.

## Kafka / IoT pipeline

- Kafka lam event backbone; topic chia theo domain.
- Dung partition key nhu `farmId` de giu thu tu va traceability.
- Consumer group de scale ngang.
- Dead Letter Queue (DLQ) cho message loi de khong mat du lieu.
- Neu chua dung Kafka production: lien he RabbitMQ topic exchange + DLQ + acknowledgement pattern tuong tu, va noi ro cach onboarding Kafka/Confluent.

## MVP / product ownership / tribe

- Ship nho de validate.
- Hieu ly do kinh doanh truoc khi estimate.
- Technical debt la mot quyet dinh san pham, can can bang revenue va refactor.
- Uu tien bang usage data.
- Ownership la theo doi error rate va latency, chu dong de xuat, khong cho PM keo.
