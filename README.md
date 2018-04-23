# Overview

Telegraf is the Agent for Collecting & Reporting Metrics & Data.

It is part of the TICK stack and is a plugin-driven server agent for collecting and reporting metrics. Telegraf has plugins or integrations to source a variety of metrics directly from the system it’s running on, pull metrics from third-party APIs, or even listen for metrics via a StatsD and Kafka consumer services. It also has output plugins to send metrics to a variety of other datastores, services, and message queues, including InfluxDB, Graphite, OpenTSDB, Datadog, Librato, Kafka, MQTT, NSQ, and many others.

# Requirements

The interface has not been added to the layer-index yet.
Clone the opentsdb interface in your local interfaces directory.

```sh
git clone https://github.com/tengu-team/interface-opentsdb
```

# Usage

Telegraf collects metrics from one or more applications and stores them in a database of choice.
```sh
juju deploy cs:~tengu-team/telegraf-1
```
## Supported output applications
Output applications are destinations where Telegraf writes metrics to:
- InfluxDB

How to add the relation:
```sh
juju deploy cs:~chris.macnaughton/influxdb-7
juju add-relation telegraf:influxdb-output influxdb:query
```
 For the moment only InfluxDB is supported but in the future other databases (f.e. OpenTSDB) will be added to the charm.

## Supported input applications
When a relation is made with one of the applications listed below then Telegraf will collect specific metrics from this application:
- MongoDB (mongodb plugin)
- NGINX (nginx plugin)
- ArangoDB (http plugin)

How to add the relation:
```sh
juju add-relation telegraf mongodb
```
More applications will be added in the future.

## Other applications
If your application is not listed in the input or output plugin section then you will not be able to get detailed metrics for that service. It is still possible to get simple system metrics like cpu, memory, disk space, etc. To receive those you need to create a juju-info relation with the service.
```sh
juju add-relation telegraf:host-system application:juju-info
```

# Contact Information
- [Telegraf]
- [Telegraf Documentation]
- [Telegraf Charm Github]

## Authors
- Michiel Ghyselinck <michiel.ghyselinck@tengu.io>

[telegraf documentation]: https://docs.influxdata.com/telegraf/v1.5/
[telegraf charm github]: https://github.com/tengu-team/layer-telegraf
[telegraf]: https://www.influxdata.com/time-series-platform/telegraf/
[mongodb plugin]: https://github.com/influxdata/telegraf/tree/master/plugins/inputs/mongodb
[nginx plugin]: https://github.com/influxdata/telegraf/tree/master/plugins/inputs/nginx
[http plugin]: https://github.com/influxdata/telegraf/tree/master/plugins/inputs/http
