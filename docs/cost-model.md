# Capacity and indicative AWS cost model

This is an order-of-magnitude sizing exercise, not an AWS quote. Prices are volatile and region dependent. It uses US East (N. Virginia) public examples/prices as a reference; confirm the deployment region, current price sheet, data residency, existing AWS commitments, and request mix in AWS Pricing Calculator before approval.

## Sizing inputs

| Input | Value | Source type / basis |
|---|---:|---|
| Normal daily events | 50,000,000 | [Assumed] challenge brief workload, not observed production telemetry |
| Peak multiplier | 10x | [Assumed] challenge design constraint |
| Average payload | 1 KiB/event | [Assumed] placeholder pending measured payload distribution |
| Month length | 30 days | [Assumed] normalization for estimate |
| Provisioned shards | 12 | [Estimated] gives ~12 MB/s and 12,000 records/s theoretical ingress; leaves ~2x over assumed 10x peak in the limiting dimension |
| Stream retention | 24h | [Assumed] short replay buffer; extended retention adds charges |
| Firehose billed record | 5 KB/event | [Estimated] AWS rounds each 1 KiB-or-smaller record up to a 5 KiB billing unit |

## Derived load

- [Estimated] Average rate = 50,000,000 / 86,400 = **579 events/s**.
- [Estimated] At 1 KiB/event, average bytes ≈ **0.58 MB/s**; 10x peak ≈ **5,790 events/s / 5.79 MB/s**.
- [Estimated] Six shards is the theoretical minimum at this assumed peak (Kinesis limits each shard to 1 MB/s **or** 1,000 records/s); [Estimated] twelve shards provide ~2x headroom, but skewed partition keys can still hotspot one shard. AWS lists the per-shard limits and the provisioned pricing model in its [Kinesis pricing guide](https://aws.amazon.com/kinesis/data-streams/pricing/).
- [Estimated] Monthly raw payload = 50M × 30 × 1 KiB = **1.5 TB decimal / ~1.40 TiB** before envelope overhead, compression, replication, indexes, or retention copies.
- [Estimated] 10x describes burst capacity, not the entire month's traffic. Costing all events at 10x would overstate a short peak; cost the steady event volume plus capacity left provisioned for planned spikes.

## Partial monthly cost illustration

| Component | Calculation | Approximate monthly cost |
|---|---|---:|
| Kinesis provisioned shard-hours | 12 × 730h × $0.015/shard-hour | $131.40 |
| Kinesis PUT units | 1.5B 1-KiB records × $0.014/million 25-KB units | $21.00 |
| Firehose S3 ingest | 1.5B × 5 KiB billing size / 1,048,576 KiB per GiB ≈ 7,152.56 GiB × $0.029/GiB | $207.42 |
| S3 first-month standard storage | ~1,430 GiB × $0.023/GiB-month | ~$32.89 |
| **Illustrative subtotal** | These four data-path line items only | **~$392.71/month** |

Kinesis shard-hour and PUT example rates are from [AWS Kinesis pricing](https://aws.amazon.com/kinesis/data-streams/pricing/); Firehose bills direct/Kinesis ingestion in 5 KB increments and publishes $0.029/GB for the first 500 TB in its [pricing examples](https://aws.amazon.com/firehose/pricing/); S3 Standard is illustrated at $0.023/GB-month in AWS examples ([AWS S3 pricing](https://aws.amazon.com/s3/pricing/)). The public pricing pages are the source; arithmetic above is our estimate. Firehose's example converts using 1,048,576 KiB/GiB while the S3 estimate is shown in GiB; figures are rounded to cents for planning.

This subtotal omits Lambda, DynamoDB reads/writes/storage/backup/transactions, API Gateway/ALB, WAF, CloudWatch logs/metrics/traces, KMS requests/keys, S3 request costs, data export egress, warehouse provider charges, support, tax, extended retention, optional Firehose format conversion/dynamic partitioning, and production redundancy. It is **not** evidence the whole architecture costs $403/month. Against the challenge's [Assumed] $50K/month ceiling, the stream + basic archive appear unlikely to dominate, but the serving tier, observability, exports, retention, and cross-region requirements need real usage inputs and a full calculator estimate. Put AWS Budgets and per-service alarms in the MVP before onboarding production traffic.

## Cost sensitivities to measure

1. Actual p50/p95/p99 payload sizes and 10x duration drive bytes and shard choices.
2. Tenant and subject-key skew determines whether a nominal shard count is usable.
3. Dashboard read pattern and materialized-view cardinality drive DynamoDB cost.
4. S3 object size, compression, retention, delete rewrites, and export frequency drive data-lake cost.
5. Enhanced fan-out, extended stream retention, multi-region replication, and warehouse egress can materially change the estimate.
